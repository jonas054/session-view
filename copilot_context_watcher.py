#!/usr/bin/env python3
"""
Copilot Context Watcher
- Detects active Copilot session under ~/.copilot/session-state
- Tails events.jsonl and extracts token usage + model
- Writes a compact JSON status to ~/.copilot/context_status.json

Usage:
  python3 copilot_context_watcher.py        # run follower (daemon)
  python3 copilot_context_watcher.py --once # print current snapshot and exit

This is a lightweight prototype for a macOS menubar app to read and display live token usage.
"""

import os
import sys
import time
import json

from pathlib import Path
from typing import Optional, Dict, Any


def _debug_enabled(argv=None) -> bool:
    argv = argv or sys.argv
    if '--debug' in argv:
        return True
    v = os.environ.get('COPILOT_CONTEXT_DEBUG', '').strip().lower()
    return v in ('1', 'true', 'yes', 'y', 'on')


def _dprint(msg: str, argv=None):
    if _debug_enabled(argv):
        print(f"[copilot_context_watcher][debug] {msg}", file=sys.stderr)

HOME = Path.home()
COPILOT_STATE = HOME / '.copilot' / 'session-state'
STATUS_FILE = HOME / '.copilot' / 'context_status.json'

MODEL_MAX_TOKENS = {
    # Prototype mappings — adjust as needed
    "gpt-5-mini": 128000,
    "gpt-5": 128000,
    "claude-sonnet-4.5": 200000,
    "gpt-4.1": 128000,
    # Not known:
    "gpt-5.4": 131072,
    "gpt-5.4-mini": 65536,
    "claude-sonnet-4.6": 131072,
}

def find_active_session_dir(state_dir: Path) -> Optional[Path]:
    """Find the session directory whose events.jsonl is newest AND has an inuse.*.lock file next to it.
    Fallbacks:
      1. If none found, pick the newest directory that contains events.jsonl (even without lock).
      2. If still none, pick the most-recently modified session directory.

    Debug output is controlled via --debug or COPILOT_CONTEXT_DEBUG=1.
    """
    if not state_dir.exists():
        _dprint(f"state_dir does not exist: {state_dir}")
        return None

    _dprint(f"Scanning session-state: {state_dir}")

    candidates_with_lock = []
    candidates_with_events = []
    scanned = 0

    try:
        entries = list(state_dir.iterdir())
    except Exception as e:
        _dprint(f"Failed to list {state_dir}: {e}")
        return None

    for p in entries:
        if not p.is_dir():
            continue
        scanned += 1
        events_path = p / 'events.jsonl'
        has_events = events_path.exists()

        lock_files = []
        try:
            lock_files = [f.name for f in p.iterdir() if f.name.startswith('inuse.') and f.name.endswith('.lock')]
        except Exception as e:
            _dprint(f"Failed to scan {p} for locks: {e}")

        has_inuse_lock = len(lock_files) > 0

        if _debug_enabled():
            ev_mtime = None
            if has_events:
                try:
                    ev_mtime = events_path.stat().st_mtime
                except Exception:
                    ev_mtime = None
            _dprint(
                f"dir={p.name} has_events={has_events} events_mtime={ev_mtime} locks={lock_files}")

        if has_events and has_inuse_lock:
            try:
                mtime = events_path.stat().st_mtime
            except Exception:
                mtime = p.stat().st_mtime
            candidates_with_lock.append((mtime, p))
        elif has_events:
            try:
                mtime = events_path.stat().st_mtime
            except Exception:
                mtime = p.stat().st_mtime
            candidates_with_events.append((mtime, p))

    _dprint(f"Scanned {scanned} session dirs; lock_candidates={len(candidates_with_lock)} events_candidates={len(candidates_with_events)}")

    if candidates_with_lock:
        chosen = sorted(candidates_with_lock, key=lambda x: x[0], reverse=True)[0][1]
        _dprint(f"Chose (lock+newest events): {chosen}")
        return chosen

    if candidates_with_events:
        chosen = sorted(candidates_with_events, key=lambda x: x[0], reverse=True)[0][1]
        _dprint(f"Chose (newest events, no lock): {chosen}")
        return chosen

    dirs = []
    for d in entries:
        if d.is_dir():
            try:
                dirs.append((d.stat().st_mtime, d))
            except Exception:
                pass

    if not dirs:
        _dprint("No session dirs found")
        return None

    chosen = sorted(dirs, key=lambda x: x[0], reverse=True)[0][1]
    _dprint(f"Chose (fallback newest dir): {chosen}")
    return chosen


def find_events_file(session_dir: Path) -> Optional[Path]:
    cand = session_dir / 'events.jsonl'
    if cand.exists():
        _dprint(f"Using events file: {cand}")
        return cand
    _dprint(f"No events.jsonl found in: {session_dir}")
    return None



def write_status_file(snapshot: Dict[str, Any]):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_FILE.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(snapshot, f)
    tmp.replace(STATUS_FILE)


def scan_events_for_snapshot(events_path: Path) -> Dict[str, Any]:
    """Read all assistant.message events and sum their token counts.

    Each event carries per-message token counts (not running totals), so we
    must accumulate them ourselves across the whole file.
    """
    input_tokens = 0
    output_tokens = 0
    model = None
    timestamp = None

    try:
        st = events_path.stat()
        _dprint(f"Scanning {events_path} (size={st.st_size} mtime={st.st_mtime})")
    except Exception as e:
        _dprint(f"Could not stat {events_path}: {e}")

    try:
        with events_path.open('r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get('type') != 'assistant.message':
                    continue
                data = obj.get('data', {})
                if isinstance(data.get('inputTokens'), (int, float)):
                    input_tokens += int(data['inputTokens'])
                if isinstance(data.get('outputTokens'), (int, float)):
                    output_tokens += int(data['outputTokens'])
                if data.get('model'):
                    model = data['model']
                if obj.get('timestamp'):
                    timestamp = obj['timestamp']
    except Exception as e:
        _dprint(f"Failed to scan {events_path}: {e}")

    total = input_tokens + output_tokens
    snap: Dict[str, Any] = {
        'model': model,
        'input_tokens': input_tokens or None,
        'output_tokens': output_tokens or None,
        'total_tokens': total or None,
        'timestamp': timestamp,
        'updated_at': time.time(),
    }
    max_tokens = MODEL_MAX_TOKENS.get(model or '')
    snap['percent_used'] = round(100.0 * total / max_tokens, 2) if max_tokens and total else None
    _dprint(f"Snapshot: {snap}")
    return snap


def collect_all_mtimes(state_dir: Path) -> Dict[Path, float]:
    """Return {events_path: mtime} for every events.jsonl found under state_dir."""
    result: Dict[Path, float] = {}
    try:
        for p in state_dir.iterdir():
            if not p.is_dir():
                continue
            ep = p / 'events.jsonl'
            try:
                result[ep] = ep.stat().st_mtime
            except FileNotFoundError:
                pass
            except Exception as e:
                _dprint(f"stat error {ep}: {e}")
    except Exception as e:
        _dprint(f"iterdir error {state_dir}: {e}")
    return result


def run_daemon(poll_interval: float = 1.0):
    """Poll all events.jsonl files in session-state for mtime changes.

    Whenever any file changes (or a new session dir appears), re-locate the
    active session, re-scan its events.jsonl, and write context_status.json.
    """
    # Seed initial mtime map without triggering updates
    known_mtimes = collect_all_mtimes(COPILOT_STATE)
    _dprint(f"Watching {len(known_mtimes)} events.jsonl files")

    # Build and write initial snapshot from the current active session
    session_dir = find_active_session_dir(COPILOT_STATE)
    snapshot = {'model': None, 'input_tokens': None, 'output_tokens': None,
                'total_tokens': None, 'percent_used': None, 'timestamp': None}
    if session_dir:
        events = find_events_file(session_dir)
        if events:
            snapshot = scan_events_for_snapshot(events)
            write_status_file(snapshot)
            print('Initial snapshot:', snapshot, flush=True)

    while True:
        time.sleep(poll_interval)

        current_mtimes = collect_all_mtimes(COPILOT_STATE)
        changed = False
        for path, mtime in current_mtimes.items():
            prev = known_mtimes.get(path)
            if prev is None:
                _dprint(f"New events file discovered: {path}")
                changed = True
            elif mtime != prev:
                _dprint(f"Changed: {path} ({prev} -> {mtime})")
                changed = True
        known_mtimes = current_mtimes

        if not changed:
            continue

        session_dir = find_active_session_dir(COPILOT_STATE)
        if not session_dir:
            _dprint("No active session dir found after change")
            continue
        events = find_events_file(session_dir)
        if not events:
            _dprint(f"No events.jsonl in {session_dir}")
            continue

        new_snap = scan_events_for_snapshot(events)
        if new_snap != snapshot:
            snapshot = new_snap
            write_status_file(snapshot)
            print('Updated:', snapshot, flush=True)


def print_once(events_path: Path, snap):
    # write a persistent status snapshot for external viewers
    try:
        write_status_file(snap)
    except Exception:
        pass
    print(json.dumps(snap, indent=2))


def main(argv):
    once = '--once' in argv
    interval = 1.0
    if '--interval' in argv:
        try:
            idx = argv.index('--interval')
            interval = float(argv[idx + 1])
        except Exception:
            pass

    if _debug_enabled(argv):
        _dprint(f"argv={argv}")
        _dprint(f"COPILOT_STATE={COPILOT_STATE}")
        _dprint(f"STATUS_FILE={STATUS_FILE}")

    try:
        if once:
            session_dir = find_active_session_dir(COPILOT_STATE)
            if not session_dir:
                print('No copilot session-state directory found under', COPILOT_STATE)
                return 2
            events = find_events_file(session_dir)
            if not events:
                print('No events.jsonl in', session_dir)
                return 3
            snapshot = scan_events_for_snapshot(events)
            print_once(events, snapshot)
            return 0

        run_daemon(poll_interval=interval)
    except KeyboardInterrupt:
        print('Stopping...')

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
