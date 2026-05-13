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
import re
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

TOKEN_KEY_RE = re.compile(r"(?i)(?:total|input|output|prompt|completion|response|used)?.*token")

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


def extract_usage_from_obj(obj: Any) -> Dict[str, Any]:
    """Recursively scan object for token counts and model.
    Returns dict with keys: model, input_tokens, output_tokens, total_tokens, timestamp
    """
    result = {"model": None, "input_tokens": None, "output_tokens": None, "total_tokens": None, "timestamp": None}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                lk = str(k).lower()
                if lk == 'model' and isinstance(v, str):
                    result['model'] = v
                if isinstance(v, (int, float)) and TOKEN_KEY_RE.search(k):
                    # prefer explicit keys
                    keyname = k.lower()
                    if 'input' in keyname or 'prompt' in keyname:
                        result['input_tokens'] = int(v)
                    elif 'output' in keyname or 'completion' in keyname or 'response' in keyname:
                        result['output_tokens'] = int(v)
                    elif 'total' in keyname:
                        result['total_tokens'] = int(v)
                # special-case nested usage objects
                if k.lower() in ('usage', 'token_usage', 'tokens') and isinstance(v, dict):
                    for kk, vv in v.items():
                        if isinstance(vv, (int, float)):
                            if 'prompt' in kk.lower() or 'input' in kk.lower():
                                result['input_tokens'] = int(vv)
                            elif 'completion' in kk.lower() or 'output' in kk.lower():
                                result['output_tokens'] = int(vv)
                            elif 'total' in kk.lower() or 'used' in kk.lower():
                                result['total_tokens'] = int(vv)
                walk(v)
        elif isinstance(o, list):
            for item in o:
                walk(item)

    walk(obj)
    # derive total if possible
    if result['total_tokens'] is None:
        vals = [v for k,v in result.items() if k.endswith('_tokens') and v is not None]
        if vals:
            result['total_tokens'] = sum(vals)
    return result


def write_status_file(snapshot: Dict[str, Any]):
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_FILE.with_suffix('.tmp')
    with tmp.open('w') as f:
        json.dump(snapshot, f)
    tmp.replace(STATUS_FILE)


def process_line(line: str, last_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    try:
        obj = json.loads(line)
    except Exception:
        return last_snapshot
    ts = obj.get('timestamp') or obj.get('data', {}).get('timestamp') or obj.get('data', {}).get('time')
    usage = extract_usage_from_obj(obj)
    if usage['model'] is None and isinstance(obj.get('data'), dict):
        usage['model'] = obj['data'].get('model') or usage['model']
    # merge with last
    snap = last_snapshot.copy()
    snap_updated = False
    for key in ('model','input_tokens','output_tokens','total_tokens'):
        if usage.get(key) is not None and usage.get(key) != snap.get(key):
            snap[key] = usage[key]
            snap_updated = True
    if ts:
        snap['timestamp'] = ts
    # enrich with percentage if model known and max available
    model = snap.get('model')
    max_tokens = MODEL_MAX_TOKENS.get(model)
    if max_tokens and snap.get('total_tokens') is not None:
        snap['percent_used'] = round(100.0 * snap['total_tokens'] / max_tokens, 2)
    else:
        snap['percent_used'] = None
    if snap_updated:
        snap['updated_at'] = time.time()
    return snap


def scan_events_for_initial_snapshot(events_path: Path) -> Dict[str, Any]:
    snap = {'model': None, 'input_tokens': None, 'output_tokens': None, 'total_tokens': None, 'percent_used': None, 'timestamp': None}
    try:
        st = events_path.stat()
        _dprint(f"Scanning initial snapshot from {events_path} (size={st.st_size} mtime={st.st_mtime})")
    except Exception as e:
        _dprint(f"Could not stat events file {events_path}: {e}")

    try:
        # read last chunk and scan recent lines for usage-like fields
        with events_path.open('rb') as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block_size = 8192
            data = b''
            blocks = 0
            while size > 0 and blocks < 64 and len(data) < 200 * 2000:
                seek = max(0, size - block_size)
                f.seek(seek)
                data = f.read(min(size, block_size)) + data
                size = seek
                blocks += 1

            try:
                text = data.decode('utf-8', errors='replace')
            except Exception as e:
                _dprint(f"Decode error reading {events_path}: {e}")
                text = ''

        lines = text.splitlines()[-1000:]
        _dprint(f"Initial scan: read {len(lines)} lines")

        for idx, line in enumerate(lines):
            snap = process_line(line, snap)
            if _debug_enabled() and idx == len(lines) - 1:
                _dprint(f"Initial scan last-line snapshot: {snap}")

        return snap
    except Exception as e:
        _dprint(f"Failed initial scan of {events_path}: {e}")
        return snap


def follow_events(events_path: Path, poll_interval: float = 1.0):
    # initial snapshot
    snapshot = scan_events_for_initial_snapshot(events_path)
    write_status_file(snapshot)
    with events_path.open('r', encoding='utf-8', errors='replace') as f:
        # go to end
        f.seek(0, os.SEEK_END)
        line = f.readline()
        if not line:
            time.sleep(poll_interval)
            return
        new_snap = process_line(line, snapshot)
        if new_snap.get('updated_at') != snapshot.get('updated_at'):
            snapshot = new_snap
            write_status_file(snapshot)
            print('Updated:', snapshot)


def print_once(events_path: Path):
    snap = scan_events_for_initial_snapshot(events_path)
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
        while True:
            session_dir = find_active_session_dir(COPILOT_STATE)
            if not session_dir:
                print('No copilot session-state directory found under', COPILOT_STATE)
                return 2

            _dprint(f"Selected session_dir={session_dir}")

            events = find_events_file(session_dir)
            if not events:
                print('No events.jsonl in', session_dir)
                return 3

            if once:
                print_once(events)
                return 0

            follow_events(events, poll_interval=interval)
    except FileNotFoundError:
        print('events.jsonl not found:', events_path)
    except KeyboardInterrupt:
        print('Stopping...')

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
