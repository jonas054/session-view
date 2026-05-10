#!/usr/bin/env python3
"""
session_view - Render Copilot session events.jsonl file(s) as HTML,
               and generate a sessions overview index.

Usage:
    session_view                                      # batch: render all sessions, then regenerate overview
    session_view <session-id or path-to-events.jsonl> # single file, no overview
    session_view --story <path>                       # render with a Story tab (calls storyteller agent)
    session_view --story -f [-l <language>] <path>    # force-regenerate the story even if cached

When processing multiple files (no argument), each events.jsonl is rendered in-place
as events.html in its own directory; existing files are skipped unless events.jsonl
or session_view itself is newer than events.html.
After the batch pass, sessions-overview.html is regenerated automatically.

Flags:
    --story     Generate a Story tab by calling `Copilot CLI`.
                The story is cached as story.txt next to events.jsonl.
    --force     Re-generate story even if story.txt exists.
    --language  Language for the generated story (e.g. "Swedish" or "Frnch").
    --a11y      Use a colorblind-friendly (deuteranopia/protanopia) colour palette.
"""

import argparse
import base64
import difflib
import glob as _glob
import html
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# GitHub Copilot icon — used as favicon and inline image throughout
# ─────────────────────────────────────────────────────────────────────────────

_FAVICON_SVG = '''
<svg viewBox="0 0 512 416"
     xmlns="http://www.w3.org/2000/svg"
     fill-rule="evenodd"
     clip-rule="evenodd"
     stroke-linejoin="round"
     stroke-miterlimit="2">
  <path d="M181.33 266.143c0-11.497 9.32-20.818 20.818-20.818 11.498 0 20.819 9.321
           20.819 20.818v38.373c0 11.497-9.321 20.818-20.819 20.818-11.497
           0-20.818-9.32-20.818-20.818v-38.373zM308.807 245.325c-11.477 0-20.798
           9.321-20.798 20.818v38.373c0 11.497 9.32 20.818 20.798 20.818 11.497 0
           20.818-9.32 20.818-20.818v-38.373c0-11.497-9.32-20.818-20.818-20.818z"
        fill-rule="nonzero"/>
  <path d="M512.002 246.393v57.384c-.02 7.411-3.696 14.638-9.67 19.011C431.767 374.444
           344.695 416 256 416c-98.138
           0-196.379-56.542-246.33-93.21-5.975-4.374-9.65-11.6-9.671-19.012v-57.384a35.347
           35.347 0 016.857-20.922l15.583-21.085c8.336-11.312 20.757-14.31 33.98-14.31
           4.988-56.953 16.794-97.604 45.024-127.354C155.194 5.77 226.56 0 256 0c29.441 0
           100.807 5.77 154.557 62.722 28.19 29.75 40.036 70.401 45.025 127.354 13.263 0
           25.602 2.936 33.958 14.31l15.583 21.127c4.476 6.077 6.878 13.345 6.878
           20.88zm-97.666-26.075c-.677-13.058-11.292-18.19-22.338-21.824-11.64
           7.309-25.848 10.183-39.46 10.183-14.454
           0-41.432-3.47-63.872-25.869-5.667-5.625-9.527-14.454-12.155-24.247a212.902
           212.902 0 00-20.469-1.088c-6.098 0-13.099.349-20.551 1.088-2.628 9.793-6.509
           18.622-12.155 24.247-22.4 22.4-49.418 25.87-63.872 25.87-13.612
           0-27.86-2.855-39.501-10.184-11.005 3.613-21.558 8.828-22.277 21.824-1.17
           24.555-1.272 49.11-1.375 73.645-.041 12.318-.082 24.658-.288 36.976.062 7.166
           4.374 13.818 10.882 16.774 52.97 24.124 103.045 36.278 149.137 36.278 46.01 0
           96.085-12.154 149.014-36.278 6.508-2.956 10.84-9.608
           10.881-16.774.637-36.832.124-73.809-1.642-110.62h.041zM107.521 168.97c8.643
           8.623 24.966 14.392 42.56 14.392 13.448 0 39.03-2.874 60.156-24.329 9.28-8.951
           15.05-31.35
           14.413-54.079-.657-18.231-5.769-33.28-13.448-39.665-8.315-7.371-27.203-10.574-48.33-8.644-22.399
           2.238-41.267 9.588-50.875 19.833-20.798 22.728-16.323 80.317-4.476
           92.492zm130.556-56.008c.637 3.51.965 7.35 1.273 11.517 0 2.875 0 5.77-.308
           8.952 6.406-.636 11.847-.636 16.959-.636s10.553 0
           16.959.636c-.329-3.182-.329-6.077-.329-8.952.329-4.167.657-8.007
           1.294-11.517-6.735-.637-12.812-.965-17.924-.965s-11.21.328-17.924.965zm49.275-8.008c-.637
           22.728 5.133 45.128 14.413 54.08 21.105 21.454 46.708 24.328 60.155 24.328
           17.596 0 33.918-5.769 42.561-14.392 11.847-12.175
           16.322-69.764-4.476-92.492-9.608-10.245-28.476-17.595-50.875-19.833-21.127-1.93-40.015
           1.273-48.33 8.644-7.679 6.385-12.791 21.434-13.448 39.665z"/>
</svg>
'''
_FAVICON_URI = f"data:image/svg+xml;base64,{base64.b64encode(_FAVICON_SVG.encode()).decode()}"
_COPILOT_IMG = f'<img src="{_FAVICON_URI}" style="height:1.5em;vertical-align:middle;margin-right:6px;">'


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def parse_ts(ts_str: str) -> datetime:
    if not ts_str:
        return None
    ts_str = ts_str.rstrip("Z")
    try:
        return datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def fmt_ts(ts_str: str) -> str:
    dt = parse_ts(ts_str)
    return dt.strftime("%H:%M:%S") if dt else ts_str


def fmt_ts_long(ts_str: str) -> str:
    dt = parse_ts(ts_str)
    return dt.strftime("%Y-%m-%d %H:%M") if dt else (ts_str or "")


def fmt_duration(ms: int) -> str:
    if ms is None:
        return "?"
    s = ms / 1000
    if s < 60:
        return f"{s:.1f}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{int(m)}m {int(s)}s"
    h, m = divmod(m, 60)
    return f"{int(h)}h {int(m)}m {int(s)}s"


def fmt_number(n) -> str:
    if n is None:
        return "0"
    return f"{n:,}"


def escape(text: str) -> str:
    return html.escape(str(text)) if text is not None else ""


ABBREV_LEN = 200


def abbreviate(text: str, max_len: int = ABBREV_LEN) -> str:
    text = text.strip().replace("\n", " ").replace("\r", "")
    while "  " in text:
        text = text.replace("  ", " ")
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


def json_html(obj) -> str:
    """Return syntax-highlighted JSON as HTML."""
    text = json.dumps(obj, indent=2, ensure_ascii=False)
    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        # strings
        if ch == '"':
            j = i + 1
            while j < len(text):
                if text[j] == '\\':
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            token = text[i:j]
            # key or value?
            rest = text[j:].lstrip()
            if rest.startswith(':'):
                result.append(f'<span class="jk">{escape(token)}</span>')
            else:
                result.append(f'<span class="js">{escape(token)}</span>')
            i = j
        elif ch in '0123456789-':
            j = i + 1
            while j < len(text) and text[j] in '0123456789.eE+-':
                j += 1
            result.append(f'<span class="jn">{escape(text[i:j])}</span>')
            i = j
        elif text[i:i+4] == 'true':
            result.append('<span class="jb">true</span>')
            i += 4
        elif text[i:i+5] == 'false':
            result.append('<span class="jb">false</span>')
            i += 5
        elif text[i:i+4] == 'null':
            result.append('<span class="jnull">null</span>')
            i += 4
        elif ch in '{}[],:':
            result.append(f'<span class="jp">{escape(ch)}</span>')
            i += 1
        else:
            result.append(escape(ch))
            i += 1
    return ''.join(result)


# ─────────────────────────────────────────────────────────────────────────────
# Summarise what happened in the session
# ─────────────────────────────────────────────────────────────────────────────

def build_overview(events: list) -> dict:
    overview = {
        "session_id": None,
        "copilot_version": None,
        "start_time": None,
        "end_time": None,
        "duration_ms": None,
        "cwd": None,
        "branch": None,
        "head_commit": None,
        "shutdown_type": None,
        "total_premium_requests": 0,
        "total_api_duration_ms": None,
        "files_modified": [],
        "lines_added": 0,
        "lines_removed": 0,
        "model_metrics": {},
        "event_counts": {},
        "user_messages": [],
        "tools_used": {},
        "intents": [],
        "subagents": [],
    }

    for ev in events:
        t = ev.get("type", "")
        d = ev.get("data", {})
        overview["event_counts"][t] = overview["event_counts"].get(t, 0) + 1

        if t == "session.start":
            overview["session_id"] = d.get("sessionId")
            overview["copilot_version"] = d.get("copilotVersion")
            overview["start_time"] = ev.get("timestamp")
            ctx = d.get("context", {})
            overview["cwd"] = ctx.get("cwd")
            overview["branch"] = ctx.get("branch")
            overview["head_commit"] = ctx.get("headCommit")

        elif t == "user.message":
            overview["user_messages"].append(d.get("content", ""))

        elif t == "session.shutdown":
            overview["end_time"] = ev.get("timestamp")
            overview["shutdown_type"] = d.get("shutdownType")
            overview["total_premium_requests"] = d.get("totalPremiumRequests", 0)
            overview["total_api_duration_ms"] = d.get("totalApiDurationMs")
            code = d.get("codeChanges", {})
            overview["files_modified"] = code.get("filesModified", [])
            overview["lines_added"] = code.get("linesAdded", 0)
            overview["lines_removed"] = code.get("linesRemoved", 0)
            overview["model_metrics"] = d.get("modelMetrics", {})

        elif t == "tool.execution_start":
            name = d.get("toolName", "")
            if name and name != "report_intent":
                overview["tools_used"][name] = overview["tools_used"].get(name, 0) + 1
            if name == "report_intent":
                intent = d.get("arguments", {}).get("intent")
                if intent:
                    overview["intents"].append(intent)

        elif t == "subagent.started":
            overview["subagents"].append({
                "name": d.get("agentDisplayName", d.get("agentName", "")),
                "ts": ev.get("timestamp"),
            })

    # Calculate duration
    if overview["start_time"] and overview["end_time"]:
        s = parse_ts(overview["start_time"])
        e = parse_ts(overview["end_time"])
        if s and e:
            overview["duration_ms"] = int((e - s).total_seconds() * 1000)

    return overview


# ─────────────────────────────────────────────────────────────────────────────
# Build conversation turns
# ─────────────────────────────────────────────────────────────────────────────

def build_turns(events: list) -> list:
    """
    Return a list of logical conversation turns.  Each turn is a dict:
        {user_message, assistant_steps}
    An assistant_step is one of:
        {kind:'text', content}
        {kind:'tool', name, args, result, success, ts_start, ts_end, intentSummary}
        {kind:'subagent', name, ts_start, ts_end}
    """
    # Index executions by toolCallId
    exec_starts = {}   # toolCallId -> event
    exec_ends = {}     # toolCallId -> event
    subagent_starts = {}  # toolCallId -> event
    subagent_ends = {}    # toolCallId -> event

    for ev in events:
        t = ev.get("type", "")
        d = ev.get("data", {})
        cid = d.get("toolCallId")
        if t == "tool.execution_start" and cid:
            exec_starts[cid] = ev
        elif t == "tool.execution_complete" and cid:
            exec_ends[cid] = ev
        elif t == "subagent.started" and cid:
            subagent_starts[cid] = ev
        elif t == "subagent.completed" and cid:
            subagent_ends[cid] = ev

    turns = []
    current_user_msg = None
    current_steps = []
    current_text_parts = []
    current_text_event_id = None  # event id of first assistant.message in current text batch

    def flush_text():
        nonlocal current_text_parts, current_text_event_id
        if current_text_parts:
            text = "\n".join(current_text_parts).strip()
            if text:
                current_steps.append({"kind": "text", "content": text, "event_id": current_text_event_id or ""})
        current_text_parts = []
        current_text_event_id = None

    def flush_turn():
        nonlocal current_user_msg, current_steps, current_text_parts, current_text_event_id
        flush_text()
        if current_user_msg is not None or current_steps:
            turns.append({
                "user_message": current_user_msg,
                "steps": current_steps,
            })
        current_user_msg = None
        current_steps = []
        current_text_parts = []
        current_text_event_id = None

    for ev in events:
        t = ev.get("type", "")
        d = ev.get("data", {})

        if t == "user.message":
            flush_turn()
            current_user_msg = {
                "content": d.get("content", ""),
                "timestamp": ev.get("timestamp"),
                "interaction_id": d.get("interactionId"),
                "event_id": ev.get("id", ""),
            }

        elif t == "assistant.message":
            reasoning = d.get("reasoningText", "").strip()
            if reasoning:
                flush_text()
                current_steps.append({"kind": "reasoning", "content": reasoning, "event_id": ev.get("id", "")})

            text = d.get("content", "").strip()
            if text:
                if current_text_event_id is None:
                    current_text_event_id = ev.get("id", "")
                current_text_parts.append(text)

            # Tool requests embedded in the message
            for tr in d.get("toolRequests", []):
                if tr.get("name") == "report_intent":
                    intent_text = tr.get("arguments", {}).get("intent", "").strip()
                    if intent_text:
                        flush_text()
                        current_steps.append({"kind": "intent", "content": intent_text, "event_id": ev.get("id", "")})
                    continue
                flush_text()
                cid = tr.get("toolCallId")
                end_ev = exec_ends.get(cid, {})
                end_d = end_ev.get("data", {})
                start_ev = exec_starts.get(cid, {})

                # subagent?
                sub_start = subagent_starts.get(cid)
                sub_end = subagent_ends.get(cid)
                if sub_start:
                    current_steps.append({
                        "kind": "subagent",
                        "name": sub_start.get("data", {}).get("agentDisplayName", tr.get("name")),
                        "arguments": tr.get("arguments", {}),
                        "ts_start": sub_start.get("timestamp"),
                        "ts_end": sub_end.get("timestamp") if sub_end else None,
                        "result": end_d.get("result"),
                        "success": end_d.get("success", True),
                        "event_id": sub_start.get("id", ""),
                    })
                else:
                    current_steps.append({
                        "kind": "tool",
                        "name": tr.get("name", ""),
                        "arguments": tr.get("arguments", {}),
                        "intent_summary": tr.get("intentionSummary"),
                        "ts_start": start_ev.get("timestamp"),
                        "ts_end": end_ev.get("timestamp"),
                        "result": end_d.get("result"),
                        "success": end_d.get("success", True),
                        "event_id": start_ev.get("id", "") or end_ev.get("id", ""),
                    })

    flush_turn()
    return turns


# ─────────────────────────────────────────────────────────────────────────────
# HTML generation
# ─────────────────────────────────────────────────────────────────────────────

TOOL_ICONS = {
    "bash": "🖥️",
    "view": "👀",
    "edit": "✏️",
    "create": "🆕",
    "grep": "🔍",
    "glob": "🗂️",
    "task": "🤖",
    "sql": "🗃️",
    "ask_user": "💬",
    "web_search": "🌐",
    "web_fetch": "🌐",
    "report_intent": "🎯",
    "read_bash": "🖥️👀",
    "write_bash": "🖥️✏️",
    "stop_bash": "🛑",
    "list_bash": "📋",
    "read_agent": "📡",
    "list_agents": "📡",
}

SUBAGENT_ICONS = {
    "Explore Agent": "🕵️‍♀️",
    "Code Review Agent": "✅",
}

TOOL_COLORS = {
    "bash": "#e8f4fd",
    "view": "#f0fdf4",
    "edit": "#fff7ed",
    "create": "#fdf4ff",
    "grep": "#fefce8",
    "glob": "#fefce8",
    "task": "#f0f9ff",
    "sql": "#f5f3ff",
    "ask_user": "#fff1f2",
    "web_search": "#f0fdf4",
    "web_fetch": "#f0fdf4",
    "default": "#f8fafc",
}

TOOL_BORDER_COLORS = {
    "bash": "#3b82f6",
    "view": "#22c55e",
    "edit": "#f97316",
    "create": "#a855f7",
    "grep": "#eab308",
    "glob": "#eab308",
    "task": "#0ea5e9",
    "sql": "#8b5cf6",
    "ask_user": "#f43f5e",
    "web_search": "#10b981",
    "web_fetch": "#10b981",
    "default": "#94a3b8",
}


def tool_icon(name: str) -> str:
    return TOOL_ICONS.get(name, "🔧")


def subagent_icon(name: str) -> str:
    return SUBAGENT_ICONS.get(name, "🤖")


def tool_bg(name: str) -> str:
    return TOOL_COLORS.get(name, TOOL_COLORS["default"])


def tool_border(name: str) -> str:
    return TOOL_BORDER_COLORS.get(name, TOOL_BORDER_COLORS["default"])


def _highlight_grep_match(text: str, pattern: str) -> str:
    """Highlight regex matches within a grep result line."""
    if not pattern:
        return escape(text)
    try:
        parts = re.split(f"({pattern})", text, flags=re.IGNORECASE)
        out = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                out.append(f'<mark class="grep-match">{escape(part)}</mark>')
            else:
                out.append(escape(part))
        return "".join(out)
    except re.error:
        return escape(text)


def _render_grep_result(content: str, args) -> str:
    """Colorize ripgrep output based on output mode."""
    if not content or content.strip() in ("No matches found.", ""):
        return f'<pre class="result-pre">{escape(content)}</pre>'

    mode = (args.get("output_mode", "files_with_matches") if isinstance(args, dict) else "files_with_matches")
    has_linenum = bool(args.get("-n")) if isinstance(args, dict) else False
    pattern = (args.get("pattern", "") if isinstance(args, dict) else "")

    rows = []
    for line in content.splitlines():
        if not line:
            rows.append("")
            continue
        if mode == "files_with_matches":
            rows.append(f'<span class="grep-file">{escape(line)}</span>')
        elif mode == "count":
            idx = line.rfind(":")
            if idx > 0:
                rows.append(
                    f'<span class="grep-file">{escape(line[:idx])}</span>'
                    f'<span class="grep-sep">:</span>'
                    f'<span class="grep-count">{escape(line[idx+1:])}</span>'
                )
            else:
                rows.append(escape(line))
        else:  # content
            if has_linenum:
                # filepath:linenum:text
                first = line.index(":") if ":" in line else -1
                second = line.index(":", first + 1) if first >= 0 and ":" in line[first+1:] else -1
                if second > 0:
                    fpath = line[:first]
                    lnum  = line[first+1:second]
                    text  = line[second+1:]
                    rows.append(
                        f'<span class="grep-file">{escape(fpath)}</span>'
                        f'<span class="grep-sep">:</span>'
                        f'<span class="grep-lnum">{escape(lnum)}</span>'
                        f'<span class="grep-sep">:</span>'
                        f'{_highlight_grep_match(text, pattern)}'
                    )
                else:
                    rows.append(escape(line))
            else:
                # filepath:text
                idx = line.index(":") if ":" in line else -1
                if idx > 0:
                    rows.append(
                        f'<span class="grep-file">{escape(line[:idx])}</span>'
                        f'<span class="grep-sep">:</span>'
                        f'{_highlight_grep_match(line[idx+1:], pattern)}'
                    )
                else:
                    rows.append(escape(line))

    return f'<pre class="grep-block">{"".join(r + chr(10) for r in rows)}</pre>'


_MARKDOWN_AGENT_NAMES = {"Explore Agent", "General Purpose Agent", "Code Review Agent"}

def _looks_like_unified_diff(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    head = lines[:8]
    return (
        any(ln.startswith("diff --git ") for ln in head)
        or (any(ln.startswith("--- ") for ln in head) and any(ln.startswith("+++ ") for ln in head))
        or any(ln.startswith("@@") for ln in head)
    )


def _render_unified_diff_text(text: str) -> str:
    rows = []
    for line in text.splitlines(keepends=True):
        if line.startswith(("diff --git ", "index ", "--- ", "+++ ")):
            rows.append(f'<span class="diff-meta">{escape(line)}</span>')
        elif line.startswith("@@"):
            rows.append(f'<span class="diff-hunk">{escape(line)}</span>')
        elif line.startswith("+"):
            rows.append(f'<span class="diff-add">{escape(line)}</span>')
        elif line.startswith("-"):
            rows.append(f'<span class="diff-del">{escape(line)}</span>')
        else:
            rows.append(escape(line))
    return f'<pre class="diff-block">{"".join(rows)}</pre>'


def _render_result_text(content: str, tool_name: str = "", args=None) -> str:
    if tool_name == "grep":
        return _render_grep_result(content, args)
    if tool_name == "sql":
        return f'<div class="sql-result md-body">{markdown_to_html(content)}</div>'
    if tool_name in _MARKDOWN_AGENT_NAMES:
        return f'<div class="agent-result md-body">{markdown_to_html(content)}</div>'
    if tool_name == "bash" and _looks_like_unified_diff(content):
        return _render_unified_diff_text(content)
    return f'<pre class="result-pre">{escape(content[:4000])}{"..." if len(content) > 4000 else ""}</pre>'


def render_tool_result(result, tool_name: str = "", args=None) -> str:
    if result is None:
        return "<em>No result</em>"
    if isinstance(result, dict):
        text = result.get("content") or result.get("detailedContent")
        if text:
            return _render_result_text(text, tool_name, args)
        return f'<div class="json-block">{json_html(result)}</div>'
    return f'<pre class="result-pre">{escape(str(result)[:4000])}</pre>'


def _render_edit_diff(old: str, new: str) -> str:
    """Render a unified diff of old_str vs new_str with syntax highlighting."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="old_str", tofile="new_str", lineterm=""))
    if not diff:
        return '<pre class="arg-pretty-val" style="color:#94a3b8">  (no changes)</pre>'
    rows = []
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            pass # Not useful information - skip the file headers
        elif line.startswith("@@"):
            pass # Also not useful, since it's not real line numbers
        elif line.startswith("+"):
            rows.append(f'<span class="diff-add">{escape(line)}</span>')
        elif line.startswith("-"):
            rows.append(f'<span class="diff-del">{escape(line)}</span>')
        else:
            rows.append(escape(line))
    return f'<pre class="diff-block">{"".join(rows)}</pre>'


def _render_apply_patch_diff(patch: str) -> str:
    """Render apply_patch input with diff-like highlighting."""
    rows = []
    for line in patch.splitlines(keepends=True):
        if (
            line.startswith("*** Begin Patch")
            or line.startswith("*** End Patch")
            or line.startswith("*** Update File:")
            or line.startswith("*** Add File:")
            or line.startswith("*** Delete File:")
            or line.startswith("*** Move to:")
            or line.startswith("*** End of File")
        ):
            rows.append(f'<span class="diff-meta">{escape(line)}</span>')
        elif line.startswith("@@"):
            rows.append(f'<span class="diff-hunk">{escape(line)}</span>')
        elif line.startswith("+"):
            rows.append(f'<span class="diff-add">{escape(line)}</span>')
        elif line.startswith("-"):
            rows.append(f'<span class="diff-del">{escape(line)}</span>')
        else:
            rows.append(escape(line))
    return f'<pre class="diff-block">{"".join(rows)}</pre>'


def _render_sql_query(query: str) -> str:
    """Render SQL with lightweight highlighting for uppercase words and strings."""
    token_re = re.compile(r"""'(?:''|[^'])*'|"(?:\"\"|[^"])*"|\b[A-Z][A-Z0-9_]*\b""")
    out = []
    pos = 0
    for m in token_re.finditer(query):
        out.append(escape(query[pos:m.start()]))
        token = m.group(0)
        if token.startswith(("'", '"')):
            out.append(f'<span class="sql-str">{escape(token)}</span>')
        else:
            out.append(f'<span class="sql-kw">{escape(token)}</span>')
        pos = m.end()
    out.append(escape(query[pos:]))
    return f'<div class="code-block sql-block">{"".join(out)}</div>'


def _has_multiline_str(args: dict) -> bool:
    """True if any value is a string containing a newline."""
    return any(isinstance(v, str) and "\n" in v for v in args.values())


def _render_args_pretty(args: dict) -> str:
    """Render args with multiline string values shown as readable text blocks."""
    parts = []
    for k, v in args.items():
        key_html = f'<div class="arg-pretty-key">{escape(k)}</div>'
        if isinstance(v, str) and "\n" in v:
            parts.append(f'{key_html}<pre class="arg-pretty-val">{escape(v)}</pre>')
        elif isinstance(v, str):
            parts.append(f'{key_html}<pre class="arg-pretty-val">{escape(v)}</pre>')
        else:
            parts.append(f'{key_html}<div class="json-block">{json_html(v)}</div>')
    return "\n".join(parts)


def render_args(args, tool_name: str = "") -> str:
    if not args:
        return ""
    if tool_name == "bash" and isinstance(args, dict) and "command" in args and "description" in args:
        return f'<div class="code-block">{escape(args["command"])}</div>'
    if tool_name == "sql" and isinstance(args, dict) and len(args) == 2 and "description" in args and "query" in args:
        return _render_sql_query(args["query"])
    if tool_name == "edit" and isinstance(args, dict) and "old_str" in args and "new_str" in args:
        return _render_edit_diff(args.get("old_str", ""), args.get("new_str", ""))
    if tool_name == "apply_patch" and isinstance(args, str):
        return _render_apply_patch_diff(args)
    if isinstance(args, str):
        if "\n" in args:
            return f'<pre class="arg-pretty-val">{escape(args)}</pre>'
        return f'<div class="json-block">{json_html(args)}</div>'
    if not isinstance(args, dict):
        return f'<div class="json-block">{json_html(args)}</div>'
    # For simple one-key dicts with a short value, show inline
    if len(args) == 1:
        k, v = next(iter(args.items()))
        if isinstance(v, str) and len(v) < 100 and "\n" not in v:
            return f'<span class="arg-inline"><span class="arg-key">{escape(k)}</span>: <span class="arg-val">{escape(v)}</span></span>'
    if _has_multiline_str(args):
        return _render_args_pretty(args)
    return f'<div class="json-block">{json_html(args)}</div>'


def _md_inline(text: str) -> str:
    """Apply inline markdown: code, links, bold, italic, strikethrough."""
    placeholder_map: dict = {}
    counter = [0]

    def protect(repl: str) -> str:
        key = f"\x00P{counter[0]}\x00"
        counter[0] += 1
        placeholder_map[key] = repl
        return key

    def save_code(m: "re.Match") -> str:
        return protect(f'<code class="md-code">{html.escape(m.group(2))}</code>')

    def save_link(m: "re.Match") -> str:
        label = html.escape(m.group(1))
        url = html.escape(m.group(2))
        return protect(f'<a href="{url}" target="_blank" rel="noopener">{label}</a>')

    # Protect code spans and links before HTML-escaping
    text = re.sub(r"(`+)(.+?)\1", save_code, text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]\n]+)\]\(([^)\n]+)\)", save_link, text)

    # HTML-escape everything else
    text = html.escape(text)

    # Bold / italic / strikethrough (order: bold before italic)
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text, flags=re.DOTALL)
    text = re.sub(r"\*\*(.+?)\*\*",     r"<strong>\1</strong>",          text, flags=re.DOTALL)
    text = re.sub(r"__(.+?)__",         r"<strong>\1</strong>",          text, flags=re.DOTALL)
    text = re.sub(r"\*([^*\s][^*\n]*?[^*\s]|\S)\*", r"<em>\1</em>",     text)
    text = re.sub(r"(?<!\w)_([^_\s][^_\n]*?[^_\s]|\S)_(?!\w)",   r"<em>\1</em>",     text)
    text = re.sub(r"~~(.+?)~~",         r"<del>\1</del>",                text, flags=re.DOTALL)

    # Restore protected spans
    for key, val in placeholder_map.items():
        text = text.replace(key, val)

    return text


def _md_table(lines: list) -> str:
    """Render a list of pipe-table lines as an HTML table."""
    def split_row(line: str) -> list:
        line = line.strip().strip("|")
        return [c.strip() for c in line.split("|")]

    rows = [split_row(ln) for ln in lines]
    if len(rows) < 2:
        return "<p>" + _md_inline(" ".join(lines)) + "</p>"

    # Detect alignment row (row index 1: cells contain only -, :, space)
    sep_idx = None
    for idx, row in enumerate(rows[1:], 1):
        if all(re.fullmatch(r":?-+:?", c.strip()) for c in row if c.strip()):
            sep_idx = idx
            break

    aligns = []
    if sep_idx is not None:
        for cell in rows[sep_idx]:
            c = cell.strip()
            if c.startswith(":") and c.endswith(":"):
                aligns.append('style="text-align:center"')
            elif c.endswith(":"):
                aligns.append('style="text-align:right"')
            else:
                aligns.append("")

    def cell_attr(i: int) -> str:
        return f" {aligns[i]}" if i < len(aligns) and aligns[i] else ""

    header_row = rows[0]
    data_rows = [r for i, r in enumerate(rows) if i != 0 and i != sep_idx]

    thead = "<tr>" + "".join(
        f'<th{cell_attr(i)}>{_md_inline(c)}</th>'
        for i, c in enumerate(header_row)
    ) + "</tr>"

    tbody_rows = []
    for row in data_rows:
        cells = "".join(
            f'<td{cell_attr(i)}>{_md_inline(c)}</td>'
            for i, c in enumerate(row)
        )
        tbody_rows.append(f"<tr>{cells}</tr>")

    return (
        '<div class="md-table-wrap">'
        f'<table class="md-table"><thead>{thead}</thead>'
        f'<tbody>{"".join(tbody_rows)}</tbody></table>'
        '</div>'
    )


def _is_block_starter(line: str) -> bool:
    return bool(
        line.startswith("```")
        or re.match(r"^#{1,6}\s", line)
        or re.match(r"^[-*_]{3,}\s*$", line)
        or line.startswith(">")
        or re.match(r"^[-*+]\s", line)
        or re.match(r"^\d+\.\s", line)
        or not line.strip()
    )


def _md_list_items(lines: list, ordered: bool) -> str:
    """Parse flat/indented list lines into <li> elements."""
    tag = "ol" if ordered else "ul"
    css = "md-ol" if ordered else "md-ul"
    item_re = re.compile(r"^(\d+\.\s+|[-*+]\s+)")
    items_html = []
    current: list = []
    sub: list = []

    def flush_item():
        if current:
            body = _md_inline(" ".join(current))
            if sub:
                nested = _md_list_items(sub, ordered=bool(re.match(r"^\d+\.\s", sub[0]) if sub else False))
                body += nested
            items_html.append(f"<li class='md-li'>{body}</li>")
        current.clear()
        sub.clear()

    for line in lines:
        m = item_re.match(line)
        if m:
            flush_item()
            current.append(line[m.end():].rstrip())
        elif line.startswith("  ") or line.startswith("\t"):
            stripped = line[2:] if line.startswith("  ") else line[1:]
            if current:
                sub.append(stripped)
        else:
            if current:
                current.append(line.strip())

    flush_item()
    return f'<{tag} class="{css}">{"".join(items_html)}</{tag}>'


def markdown_to_html(text: str) -> str:
    """Convert Markdown text to HTML. Handles: headings, bold, italic,
    inline code, fenced code blocks, ordered/unordered lists, tables,
    blockquotes, horizontal rules, links, strikethrough."""
    lines = text.split("\n")
    out: list = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # ── Fenced code block ──────────────────────────────────────────
        if re.match(r"^```", line):
            lang = line[3:].strip()
            lang_class = f"lang-{html.escape(lang)}" if lang else "lang-text"
            i += 1
            code_lines = []
            while i < n and not re.match(r"^```\s*$", lines[i]):
                code_lines.append(lines[i])
                i += 1
            i += 1  # consume closing ```
            out.append(
                f'<pre class="code-block {lang_class}">'
                f'{html.escape(chr(10).join(code_lines))}</pre>'
            )
            continue

        # ── Heading ────────────────────────────────────────────────────
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            lvl = len(m.group(1))
            out.append(f'<h{lvl} class="md-h{lvl}">{_md_inline(m.group(2))}</h{lvl}>')
            i += 1
            continue

        # ── Horizontal rule ────────────────────────────────────────────
        if re.match(r"^([-*_])\1{2,}\s*$", line):
            out.append('<hr class="md-hr">')
            i += 1
            continue

        # ── Blockquote ─────────────────────────────────────────────────
        if line.startswith(">"):
            bq: list = []
            while i < n and lines[i].startswith(">"):
                bq.append(lines[i][1:].lstrip())
                i += 1
            out.append(f'<blockquote class="md-blockquote">{markdown_to_html(chr(10).join(bq))}</blockquote>')
            continue

        # ── Unordered list ─────────────────────────────────────────────
        if re.match(r"^[-*+]\s", line):
            lst: list = []
            while i < n and (re.match(r"^[-*+]\s", lines[i]) or
                              (lst and (lines[i].startswith("  ") or lines[i].startswith("\t")))):
                lst.append(lines[i])
                i += 1
            out.append(_md_list_items(lst, ordered=False))
            continue

        # ── Ordered list ───────────────────────────────────────────────
        if re.match(r"^\d+\.\s", line):
            lst = []
            while i < n and (re.match(r"^\d+\.\s", lines[i]) or
                              (lst and (lines[i].startswith("  ") or lines[i].startswith("\t")))):
                lst.append(lines[i])
                i += 1
            out.append(_md_list_items(lst, ordered=True))
            continue

        # ── Table (current line has | and next line is separator) ──────
        if "|" in line and i + 1 < n and re.match(r"^\|?[\s:|-]+\|?\s*$", lines[i + 1]):
            tbl: list = []
            while i < n and "|" in lines[i]:
                tbl.append(lines[i])
                i += 1
            out.append(_md_table(tbl))
            continue

        # ── Blank line ─────────────────────────────────────────────────
        if not line.strip():
            i += 1
            continue

        # ── Paragraph (collect until blank or block starter) ───────────
        para: list = []
        while i < n and lines[i].strip() and not _is_block_starter(lines[i]):
            para.append(lines[i])
            i += 1
        if para:
            out.append(f'<p class="md-p">{_md_inline(" ".join(para))}</p>')
        else:
            i += 1

    return "\n".join(out)


def render_overview(ov: dict) -> str:
    dt_start = parse_ts(ov["start_time"])
    date_str = dt_start.strftime("%A, %B %-d %Y at %H:%M UTC") if dt_start else "unknown"

    # Model metrics table
    metrics_html = ""
    if ov["model_metrics"]:
        rows = []
        for model, m in ov["model_metrics"].items():
            req_count = m.get("requests", {}).get("count", 0)
            premium = m.get("requests", {}).get("cost", 0)
            input_tok = m.get("usage", {}).get("inputTokens", 0)
            output_tok = m.get("usage", {}).get("outputTokens", 0)
            rows.append(f"""
            <tr>
              <td>{escape(model)}</td>
              <td class="num">{fmt_number(req_count)}</td>
              <td class="num metrics-premium">{fmt_number(premium)}</td>
              <td class="num">{fmt_number(input_tok)}</td>
              <td class="num">{fmt_number(output_tok)}</td>
            </tr>""")
        metrics_html = f"""
        <table class="metrics-table">
          <thead><tr><th style="text-align: left">Model</th><th>Requests</th><th>Premium</th><th>Input tokens</th><th>Output tokens</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>"""

    # Files modified
    files_html = ""
    if ov["files_modified"]:
        items = "".join(f'<li><code>{escape(f)}</code></li>' for f in ov["files_modified"])
        files_html = f"""
        <div class="overview-block">
          <div class="overview-block-title">📝 Code changes</div>
          <div class="code-changes">
            <span class="added">+{fmt_number(ov["lines_added"])} lines</span>
            <span class="removed">−{fmt_number(ov["lines_removed"])} lines</span>
            <span class="files">{len(ov["files_modified"])} file(s)</span>
          </div>
          <ul class="file-list">{items}</ul>
        </div>"""

    # Tools used
    tools_sorted = sorted(ov["tools_used"].items(), key=lambda x: -x[1])
    tools_html = "".join(
        f'<span class="tool-badge" style="border-color:{tool_border(n)};background:{tool_bg(n)}">'
        f'{tool_icon(n)} {escape(n)} <strong>{c}</strong></span>'
        for n, c in tools_sorted
    )

    # Intents timeline
    intents_html = ""
    if ov["intents"]:
        items = "".join(f'<li class="intent-item">{escape(i)}</li>' for i in ov["intents"])
        intents_html = f'<ol class="intent-list">{items}</ol>'

    # User messages summary
    msgs_html = ""
    if ov["user_messages"]:
        items = "".join(
            f'<li class="user-msg-summary">{escape(m[:200])}{"…" if len(m) > 200 else ""}</li>'
            for m in ov["user_messages"]
        )
        msgs_html = f'<ol class="user-msg-list">{items}</ol>'

    event_count_items = "".join(
        f'<tr><td>{escape(k)}</td><td class="num">{v}</td></tr>'
        for k, v in sorted(ov["event_counts"].items())
    )

    resume_command = 'cd ' + escape(ov["cwd"] or "") + '; copilot --resume ' + escape(ov["session_id"])
    story_command = 'session_view --story ' + escape(ov["session_id"])
    return f"""
    <section class="overview-section">
      <h1 class="page-title">{_COPILOT_IMG} Copilot Session</h1>
      <div class="overview-meta">
        <span>📅 {date_str}</span>
        <span>⏱ Duration: <strong>{fmt_duration(ov["duration_ms"])}</strong></span>
        {'<span>✨ Premium requests: <strong>' + fmt_number(ov["total_premium_requests"]) + '</strong></span>' if ov["total_premium_requests"] else ''}
        {'<span>🔄 Shutdown: <strong>' + escape(ov["shutdown_type"]) + '</strong></span>' if ov["shutdown_type"] else ''}
        {'<span>🔖 Version: <strong>' + escape(ov["copilot_version"]) + '</strong></span>' if ov["copilot_version"] else ''}
      </div>

      <div class="overview-grid">
        <div class="overview-block overview-block-full">
          <div class="overview-block-title">📍 Context</div>
          <table class="kv-table">
            <tr><td>Working directory</td><td><code>{escape(ov["cwd"] or "—")}</code></td></tr>
            <tr><td>Branch</td><td><code>{escape(ov["branch"] or "—")}</code></td></tr>
            <tr><td>Commit</td><td><code>{escape((ov["head_commit"] or "—")[:12])}</code></td></tr>
            <tr><td>Session ID</td><td><code>{escape(ov["session_id"] or "—")}</code></td></tr>
            <tr>
              <td>Resume</td>
              <td>
                <span class="resume-cmd">
                  <code>
                    {resume_command}
                  </code>
                  <button class="copy-btn" onclick="copyCmd(this, '{resume_command}')" title="Copy">⎘</button>
                </span>
              </td>
            </tr>
            <tr>
              <td>Generate story</td>
              <td>
                <span class="resume-cmd">
                  <code>
                    {story_command}
                  </code>
                  <button class="copy-btn" onclick="copyCmd(this, '{story_command}')" title="Copy">⎘</button>
                </span>
              </td>
            </tr>
          </table>
        </div>

        {'<div class="overview-block overview-block-full"><div class="overview-block-title">💬 User messages</div>' + msgs_html + '</div>' if msgs_html else ''}

        <div class="overview-block">
          <div class="overview-block-title">📊 Event summary</div>
          <table class="kv-table">
            {event_count_items}
          </table>
        </div>

        {'<div class="overview-block"><div class="overview-block-title">🎯 Agent intents</div>' + intents_html + '</div>' if intents_html else ''}

        {files_html}

        {'<div class="overview-block"><div class="overview-block-title">🧮 Model usage</div>' + metrics_html + '</div>' if metrics_html else ''}

        {'<div class="overview-block"><div class="overview-block-title">🛠 Tools used</div><div class="tool-badges">' + tools_html + '</div></div>' if tools_html else ''}
      </div>
    </section>
    """


def render_turns(turns: list) -> str:
    parts = []
    for i, turn in enumerate(turns):
        um = turn.get("user_message")
        steps = turn.get("steps", [])

        turn_html = f'<div class="turn" id="turn-{i}">'

        if um:
            ts_str = fmt_ts(um.get("timestamp", ""))
            ev_id = um.get("event_id", "")
            raw_link = f'<a class="raw-link" href="#" onclick="goToRaw(\'ev-{escape(ev_id)}\');return false;" title="View raw event">⌗</a>' if ev_id else ""
            content = um["content"]
            skill_match = re.match(r'\s*<skill-context\s+name=["\']?([^"\'>\s]+)["\']?', content, re.IGNORECASE)
            if skill_match:
                skill_name = skill_match.group(1)
                turn_html += f"""
            <details class="tool-step skill-context-step" id="turn-{i}-skill">
              <summary class="tool-summary" style="background:#fffbeb;border-left:3px solid #f59e0b">
                <span class="tool-icon">🎯</span>
                <span class="tool-name">skill: {escape(skill_name)}</span>
                <span class="bubble-ts">{ts_str}</span>
                {raw_link}
              </summary>
              <div class="tool-body">
                <pre class="result-pre">{escape(content)}</pre>
              </div>
            </details>"""
            else:
                turn_html += f"""
            <div class="user-bubble">
              <div class="bubble-header">
                <span class="bubble-role user-role">👤 User</span>
                <span class="bubble-ts">{ts_str}</span>
                {raw_link}
              </div>
              <div class="bubble-content md-body">{markdown_to_html(content)}</div>
            </div>"""

        if steps:
            steps_html = render_steps(steps, i)
            turn_html += f"""
            <div class="assistant-turn">
              <div class="turn-header">
                <span class="bubble-role assistant-role">{_COPILOT_IMG} Copilot</span>
                <span class="turn-label">Turn {i + 1} — {len(steps)} step(s)</span>
              </div>
              {steps_html}
            </div>"""

        turn_html += "</div>"
        parts.append(turn_html)

    return "\n".join(parts)


def render_steps(steps: list, turn_idx: int) -> str:
    parts = []
    for j, step in enumerate(steps):
        kind = step.get("kind")
        step_id = f"step-{turn_idx}-{j}"
        ev_id = step.get("event_id", "")
        raw_link = f'<a class="raw-link" href="#" onclick="goToRaw(\'ev-{escape(ev_id)}\');return false;" title="View raw event">⌗</a>' if ev_id else ""

        if kind == "reasoning":
            preview = abbreviate(step["content"], 140)
            preview_html = f'<span class="tool-intent">{escape(preview)}</span>' if preview else ""
            parts.append(f"""
            <details class="tool-step reasoning-step" id="{step_id}">
              <summary class="tool-summary" style="background:#f5f3ff;border-left:3px solid #8b5cf6">
                <span class="tool-icon">🧠</span>
                <span class="tool-name">reasoning</span>
                {preview_html}
                {raw_link}
              </summary>
              <div class="tool-body reasoning-body">
                <div class="reasoning-content">{markdown_to_html(step["content"])}</div>
              </div>
            </details>""")

        elif kind == "intent":
            parts.append(f'<div class="intent-step">🎯 <span class="intent-text">{escape(step["content"])}</span></div>')

        elif kind == "text":
            parts.append(f'<div class="text-step md-body">{markdown_to_html(step["content"])}{raw_link}</div>')

        elif kind == "subagent":
            name = step.get("name", "Sub-agent")
            ts_s = fmt_ts(step.get("ts_start"))
            ts_e = fmt_ts(step.get("ts_end"))
            duration = ""
            if step.get("ts_start") and step.get("ts_end"):
                s = parse_ts(step["ts_start"])
                e = parse_ts(step["ts_end"])
                if s and e:
                    duration = fmt_duration(int((e - s).total_seconds() * 1000))

            args = step.get("arguments", {})
            result = step.get("result")

            parts.append(f"""
            <details class="tool-step subagent-step" id="{step_id}">
              <summary class="tool-summary" style="background:#f0f9ff;border-left:3px solid #0ea5e9">
                <span class="tool-icon">{subagent_icon(name)}</span>
                <span class="tool-name">{escape(name)}</span>
                <span class="tool-meta">{ts_s} → {ts_e} {'(' + duration + ')' if duration else ''}</span>
                {raw_link}
              </summary>
              <div class="tool-body">
                <div class="tool-section-label">Arguments</div>
                {render_args(args, name)}
                {('<div class="tool-section-label">Result</div>' + render_tool_result(result, name, args)) if result is not None else ''}
              </div>
            </details>""")

        elif kind == "tool":
            name = step.get("name", "")
            summary = step.get("intent_summary") or ""
            ts_s = fmt_ts(step.get("ts_start"))
            ts_e = fmt_ts(step.get("ts_end"))
            success = step.get("success", True)
            bg = tool_bg(name)
            border = tool_border(name)
            icon = tool_icon(name)
            args = step.get("arguments", {})
            result = step.get("result")

            status_badge = (
                '<span class="badge-success">✓</span>' if success
                else '<span class="badge-fail">✗</span>'
            )
            summary_html = f'<span class="tool-intent">{escape(summary)}</span>' if summary else ""

            parts.append(f"""
            <details class="tool-step" id="{step_id}">
              <summary class="tool-summary" style="background:{bg};border-left:3px solid {border}">
                <span class="tool-icon">{icon}</span>
                <span class="tool-name">{escape(name)}</span>
                {summary_html}
                {status_badge}
                <span class="tool-meta">{ts_s} → {ts_e}</span>
                {raw_link}
              </summary>
              <div class="tool-body">
                <div class="tool-section-label">Arguments</div>
                {render_args(args, name)}
                {('<div class="tool-section-label">Result</div>' + render_tool_result(result, name, args)) if result is not None else ''}
              </div>
            </details>""")

    return "\n".join(parts)


def render_raw_events(events: list) -> str:
    rows = []
    for ev in events:
        t = ev.get("type", "")
        ts = fmt_ts(ev.get("timestamp", ""))
        eid = ev.get("id", "")
        eid_short = eid[:8]
        rows.append(f"""
        <details class="raw-event" id="ev-{escape(eid)}">
          <summary><span class="raw-ts">{ts}</span> <span class="raw-type">{escape(t)}</span> <span class="raw-id">{eid_short}…</span></summary>
          <div class="json-block">{json_html(ev)}</div>
        </details>""")
    return "\n".join(rows)

HERE = Path(__file__).parent

def _load_asset_text(relpath: str) -> str:
    p = HERE.joinpath(relpath)
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return ""


CSS = _load_asset_text("static/css/events.css")
COMMON_CSS = _load_asset_text("static/css/common.css")

# CSS overrides for red/green colorblindness (deuteranopia/protanopia).
# Swaps red→orange and green→blue throughout, and adds pattern cues to diffs.
CSS_A11Y = _load_asset_text("static/css/events.a11y.css")

JS = _load_asset_text("static/js/events.js")
COMMON_JS = _load_asset_text("static/js/common.js")

def render_html(overview: dict, turns: list, events: list, source_path: str, a11y: bool = False, story_text: str | None = None) -> str:
    ov_html = render_overview(overview)
    turns_html = render_turns(turns)
    raw_html = render_raw_events(events)

    filename = os.path.basename(source_path)
    overview_link = str(OVERVIEW_OUTPUT)
    extra_css = CSS_A11Y if a11y else ""

    # Story tab
    if story_text:
        paras = "\n".join(
            f'<p class="story-p">{escape(p.strip())}</p>'
            for p in story_text.split("\n\n") if p.strip()
        )
        story_html = f'<div class="story-body">{paras}</div>'
        story_tab_btn = '<button class="tab-btn" data-tab="story" onclick="showTab(\'story\')">📖 Story</button>'
        story_tab_panel = f'<div id="panel-story" class="tab-panel"><section class="story-section"><h2 class="section-title">📖 Story</h2>{story_html}</section></div>'
    else:
        story_tab_btn = ""
        story_tab_panel = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Copilot Session — {escape(filename)}</title>
  <link rel="icon" type="image/svg+xml" href="{_FAVICON_URI}">
  <style>{COMMON_CSS}</style>
  <style>{CSS}{extra_css}</style>
</head>
<body>
<div class="container">

  <a href="file://{escape(overview_link)}" class="back-link">← All sessions</a>

  <nav class="tab-nav">
    <button class="tab-btn active" data-tab="overview"  onclick="showTab('overview')">📊 Overview</button>
    <button class="tab-btn"        data-tab="turns"     onclick="showTab('turns')">💬 Conversation</button>
    <button class="tab-btn"        data-tab="raw"       onclick="showTab('raw')">📜 Raw Events</button>
    {story_tab_btn}
  </nav>

  <div id="panel-overview" class="tab-panel active">
    {ov_html}
  </div>

  <div id="panel-turns" class="tab-panel">
    <section class="turns-section">
      <h2 class="section-title">💬 Conversation</h2>
      {turns_html}
    </section>
  </div>

  <div id="panel-raw" class="tab-panel">
    <section class="raw-section">
      <h2 class="section-title">📜 Raw Events ({len(events)} total)</h2>
      {raw_html}
    </section>
  </div>

  {story_tab_panel}

</div>
<script>{COMMON_JS}</script>
<script>{JS}</script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Sessions overview
# ─────────────────────────────────────────────────────────────────────────────

OVERVIEW_OUTPUT = Path.home() / ".copilot" / "session-state" / "sessions-overview.html"
OVERVIEW_CSS = _load_asset_text("static/css/overview.css")
OVERVIEW_JS = _load_asset_text("static/js/overview.js")

def read_session(session_dir: Path) -> dict:
    """Extract metadata from a session directory."""
    info = {
        "id": session_dir.name,
        "events_html": session_dir / "events.html",
        "start_time": "",
        "cwd": "",
        "first_prompt": "",
        "search_text": "",
        "model": "",
        "user_prompt_count": 0,
        "intent_count": 0,
        "has_story": False,
        "total_premium_requests": 0,
        "model_metrics": {},
    }

    info["has_story"] = (session_dir / "story.txt").exists()

    parts = []

    jsonl_path = session_dir / "events.jsonl"
    if not jsonl_path.exists():
        return info

    try:
        with open(jsonl_path, encoding="utf-8") as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    event = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                etype = event.get("type", "")
                data = event.get("data", {})

                if etype == "session.start":
                    info["start_time"] = data.get("startTime", event.get("timestamp", ""))
                    info["cwd"] = data.get("context", {}).get("cwd", "")
                    info["model"] = data.get("selectedModel", "")

                elif etype == "user.message":
                    info["user_prompt_count"] += 1
                    content = data.get("content", "")
                    if content:
                        parts.append(content)
                        if not info["first_prompt"]:
                            info["first_prompt"] = abbreviate(content)

                elif etype == "assistant.message":
                    # Collect assistant reasoning and text for searching
                    reasoning = data.get("reasoningText", "").strip()
                    if reasoning:
                        parts.append(reasoning)
                    text = data.get("content", "").strip()
                    if text:
                        parts.append(text)
                    # embedded tool requests (e.g., report_intent) inside assistant messages
                    for tr in data.get("toolRequests", []):
                        if tr.get("name") == "report_intent":
                            intent_text = tr.get("arguments", {}).get("intent", "").strip()
                            if intent_text:
                                parts.append(intent_text)
                        else:
                            if tr.get("intentionSummary"):
                                parts.append(tr.get("intentionSummary"))

                elif not info["model"] and "model" in data:
                    info["model"] = data["model"]

                elif etype == "tool.execution_start":
                    if data.get("toolName") == "report_intent" and data.get("arguments", {}).get("intent"):
                        info["intent_count"] += 1

                elif etype == "session.shutdown":
                    info["total_premium_requests"] = data.get("totalPremiumRequests", 0)
                    info["model_metrics"] = data.get("modelMetrics", {})

    except OSError:
        pass

    # Concatenate collected text for searching; keep reasonably sized
    info["search_text"] = abbreviate(" ".join(parts), max_len=1000)

    return info


def build_overview_html(sessions: list) -> str:
    home = str(Path.home())
    data = []
    for s in sessions:
        if s["first_prompt"].startswith("Read the Copilot session"):
            continue # Internal session for story generation, not user-initiated

        cwd = s["cwd"]
        cwd_display = "/".join(cwd.replace(home, "~").split("/")[-2:]) if cwd else ""
        data.append({
            "ts": fmt_ts_long(s["start_time"]),
            "ts_raw": s["start_time"],
            "cwd": cwd,
            "cwd_display": cwd_display,
            "model": s["model"],
            "activity": f'{s["user_prompt_count"]}+{s["intent_count"]}',
            "activity_total": s["user_prompt_count"] + s["intent_count"],
            "premium_requests": s["total_premium_requests"] or 0,
            "has_story": s["has_story"],
            "prompt": s["first_prompt"],
            "search": s.get("search_text", ""),
            "link": str(s["events_html"]),
        })

    # Aggregate model metrics across all sessions
    agg: dict = {}  # model -> {requests, premium, input_tokens, output_tokens}
    for s in sessions:
        for model, m in s.get("model_metrics", {}).items():
            a = agg.setdefault(model, {"requests": 0, "premium": 0, "input_tokens": 0, "output_tokens": 0})
            a["requests"]     += m.get("requests", {}).get("count", 0)
            a["premium"]      += m.get("requests", {}).get("cost", 0)
            a["input_tokens"] += m.get("usage", {}).get("inputTokens", 0)
            a["output_tokens"]+= m.get("usage", {}).get("outputTokens", 0)

    model_usage_html = ""
    if agg:
        rows = "".join(
            f"<tr>"
            f"<td>{escape(model)}</td>"
            f'<td class="num">{fmt_number(a["requests"])}</td>'
            f'<td class="num mu-premium">{fmt_number(a["premium"])}</td>'
            f'<td class="num">{fmt_number(a["input_tokens"])}</td>'
            f'<td class="num">{fmt_number(a["output_tokens"])}</td>'
            f"</tr>"
            for model, a in sorted(agg.items())
        )
        totals = {k: sum(a[k] for a in agg.values()) for k in ("requests", "premium", "input_tokens", "output_tokens")}
        if len(agg) > 1:
            rows += (
                f'<tr class="mu-total">'
                f"<td>Total</td>"
                f'<td class="num">{fmt_number(totals["requests"])}</td>'
                f'<td class="num mu-premium">{fmt_number(totals["premium"])}</td>'
                f'<td class="num">{fmt_number(totals["input_tokens"])}</td>'
                f'<td class="num">{fmt_number(totals["output_tokens"])}</td>'
                f"</tr>"
            )
        model_usage_html = f"""
    <div class="overview-section mu-section" id="model-usage">
      <h2 class="mu-title">🧮 Model usage</h2>
      <table class="mu-table">
        <thead><tr>
          <th>Model</th>
          <th>Requests</th>
          <th>Premium</th>
          <th>Input tokens</th>
          <th>Output tokens</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

    data_json = json.dumps(data, ensure_ascii=False)
    js = COMMON_JS + OVERVIEW_JS.replace("__DATA__", data_json)
    count = len(sessions)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Copilot Sessions Overview</title>
  <link rel="icon" type="image/svg+xml" href="{_FAVICON_URI}">
  <style>{COMMON_CSS}</style>
  <style>{OVERVIEW_CSS}</style>
</head>
<body>
  <div class="container">
    <div class="overview-section">
      <h1 class="page-title"><img src="{_FAVICON_URI}" style="height:1.2em;vertical-align:middle;margin-right:8px;"> Copilot Sessions</h1>
      <p class="page-meta">{count} sessions &nbsp;·&nbsp; generated {generated}</p>
      <div class="toolbar">
        <input class="search-bar" type="search" placeholder="Filter by prompt, directory, model, or conversation text…" id="search" autofocus>
        <button class="btn" id="btn-expand">Expand all</button>
        <button class="btn" id="btn-collapse">Collapse all</button>
      </div>
      <table class="sessions-table" id="sessions-table">
        <thead>
          <tr>
            <th data-col="0">Started <span class="sort-ind"> ↓</span></th>
            <th data-col="1">Directory <span class="sort-ind"> ↕</span></th>
            <th data-col="2">Model <span class="sort-ind"> ↕</span></th>
            <th data-col="3" title="user prompts + agent intents">Prompts+Intents <span class="sort-ind"> ↕</span></th>
            <th data-col="4" title="premium requests used">✨ <span class="sort-ind"> ↕</span></th>
            <th data-col="5" title="story available">📖 <span class="sort-ind"> ↕</span></th>
            <th data-col="6">First prompt <span class="sort-ind"> ↕</span></th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
    {model_usage_html}
  </div>
  <script>{js}</script>
</body>
</html>
"""


def generate_overview() -> None:
    pattern = str(Path.home() / ".copilot" / "session-state" / "*" / "events.html")
    paths = sorted(_glob.glob(pattern))

    if not paths:
        print("No events.html files found.", file=sys.stderr)
        return

    print(f"Found {len(paths)} session(s) for overview…", file=sys.stderr)

    sessions = []
    for p in paths:
        session_dir = Path(p).parent
        info = read_session(session_dir)
        sessions.append(info)

    sessions.sort(key=lambda s: s["start_time"] or "", reverse=True)

    html_content = build_overview_html(sessions)

    OVERVIEW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OVERVIEW_OUTPUT.write_text(html_content, encoding="utf-8")
    print(OVERVIEW_OUTPUT)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_GLOB = "~/.copilot/session-state/*/events.jsonl"


import subprocess as _subprocess


def _story_path(jsonl_path: str) -> str:
    return os.path.join(os.path.dirname(jsonl_path), "story.txt")


def _parsed_json_path(jsonl_path: str) -> str:
    return os.path.join(os.path.dirname(jsonl_path), "events.txt")


def _parse_json_events(jsonl_path: str) -> None:
    with open(jsonl_path, 'r') as f:
        events = [json.loads(line) for line in f]

    with open(_parsed_json_path(jsonl_path), 'w', encoding='utf-8') as f:
        user_name = os.getlogin()
        heading = f"Session with user '{user_name}' and Copilot\n\n"
        f.write(heading)
        for i, event in enumerate(events):
            event_type = event.get('type', '')
            data = event.get('data', {})
            if event_type == 'session.start':
                context = data.get('context', '')
                cwd = context.get('cwd', '')
                repository = context.get('repository', '')
                f.write(f"Event {i}: SESSION START - Current Working Directory: {cwd}, Repository: {repository}\n")
            elif event_type == 'user.message':
                content = data.get('content', '')
                f.write(f"Event {i}: USER MESSAGE: {content}\n")
            elif event_type == 'assistant.message':
                content = data.get('content', '')
                tool_requests = data.get('toolRequests', [])
                tools = [tr.get('name') for tr in tool_requests]
                reasoning_text = data.get('reasoningText', {})
                f.write(f"Event {i}: ASSISTANT MESSAGE - "
                        f"<tools>{tools}</tools>"
                        f"<reasoning>{reasoning_text}</reasoning>"
                        f"<content>{content}</content>\n")
            elif event_type == 'assistant.turn_end' or event_type == 'assistant.turn_start':
                continue
            elif event_type == 'tool.execution_complete':
                result = data.get('result', {}).get('detailedContent', '')[:200]
                f.write(f"Event {i}: TOOL COMPLETE: {result}\n")


def read_story(jsonl_path: str) -> str | None:
    """Return cached story text if story.txt exists next to events.jsonl, else None."""
    p = _story_path(jsonl_path)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return fh.read()
    return None


def generate_story(jsonl_path: str, force: bool = False, language: str = None) -> str | None:
    """Run the storyteller agent and cache the result as story.txt.

    Returns the story text, or None if generation failed.
    Skips generation if story.txt already exists and force=False.
    """
    cache = _story_path(jsonl_path)
    if os.path.exists(cache) and not force:
        with open(cache, encoding="utf-8") as fh:
            return fh.read()

    # Some available models: gpt-4.1 (0x), gpt-5-mini (0x), gpt-5.4-mini (0.33x),
    # claude-haiku-4.5 (0x33x), claude-sonnet-4.5 (1x)
    model = "claude-haiku-4.5"
    language = language or "English"

    _parse_json_events(jsonl_path)  # ensure events.txt is up to date
    with open(_parsed_json_path(jsonl_path), encoding="utf-8") as fh:
        events_txt = fh.read()
    events_txt = events_txt.replace("\x00", "")  # strip null bytes from binary diffs

    prompt = (
        f"Read the Copilot session below and write a text in the {language} language "
        "suitable for text-to-speech. Describe the conversation between the user "
        "and Copilot: what the user asked, what problems were solved, what tools "
        "Copilot used, and how things progressed step by step. Include details from all the "
        "events. Do not include code blocks or markdown formatting. Keep technical details "
        "from the code, which are hard for a text-to-speech function to pronounce, to a "
        "minimum. Avoid esoteric characters like '→'. Start with the heading "
        f"'Story generated by {model}' (heading in English). Output the story directly as "
        "plain text in your response — do not write it to any file and do not use any tools.\n"
        "\n"
        "<session_events>\n"
        f"{events_txt}"
        "\n\n</session_events>\n"
    )
    cmd = ["copilot", "--yolo", f"--model={model}", "--prompt", prompt]
    print(f"  ✦ Generating story…", end=" ", flush=True)
    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            print(f"failed (exit {result.returncode})")
            if result.stderr:
                print(f"    {result.stderr.strip()}", file=sys.stderr)
            return None
        lines = result.stdout.strip().split("\n")
        # Extract the story text starting from the line that begins with "Story generated by"
        heading_seen = False
        text = []
        for line in lines:
            if line.startswith("Story generated by"):
                heading_seen = True
            if heading_seen:
                text.append(line)
        text = "\n".join(text).strip()
        if not text:
            print("failed (empty output)")
            return None
        with open(cache, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("done")
        return text
    except FileNotFoundError:
        print("failed (copilot not found)")
        return None
    except _subprocess.TimeoutExpired:
        print("failed (timeout)")
        return None


def load_events(input_path: str) -> list:
    events = []
    with open(input_path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"Warning: skipping malformed line {lineno} in {input_path}: {exc}", file=sys.stderr)
    return events


def process_file(input_path: str, output_path: str, a11y: bool = False, story: bool = False, force: bool = False, language: str = None) -> None:
    events = load_events(input_path)
    if not events:
        print(f"  ⚠ No events found, skipping: {input_path}", file=sys.stderr)
        return
    overview = build_overview(events)
    turns = build_turns(events)
    story_text = generate_story(input_path, force=force, language=language) if story else read_story(input_path)
    html_content = render_html(overview, turns, events, input_path, a11y=a11y, story_text=story_text)
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)
    print(f"  ✓ {output_path}  ({len(events)} events, {len(turns)} turn(s))")


def main():
    parser = argparse.ArgumentParser(
        description="Render Copilot session events.jsonl file(s) as HTML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input", nargs="?", default=None,
        help=f"Path to events.jsonl (default: glob {DEFAULT_GLOB})",
    )
    parser.add_argument(
        "--a11y", default=False, action="store_true",
        help="Use colorblind-friendly palette (red/green → orange/blue)",
    )
    parser.add_argument(
        "--story", default=False, action="store_true",
        help="Generate a Story tab using the storyteller agent (cached in story.txt; use --force to regenerate)",
    )
    parser.add_argument(
        "--force", default=False, action="store_true",
        help="Re-generate story even if story.txt exists.",
    )
    parser.add_argument(
        "-l", "--language", default=None,
        help="Language for the generated story (default is English).",
    )
    args = parser.parse_args()

    _self_mtime = os.path.getmtime(__file__)
    # Consider static assets' modification time so updates to static/*/ trigger re-generation
    assets_mtime = 0
    try:
        assets_root = HERE.joinpath('static')
        if assets_root.exists():
            for p in assets_root.rglob('*'):
                if p.is_file():
                    assets_mtime = max(assets_mtime, p.stat().st_mtime)
    except Exception:
        assets_mtime = 0
    _effective_self_mtime = max(_self_mtime, assets_mtime)

    if args.input:
        # ── Single file mode ──────────────────────────────────────────
        input_path = os.path.expanduser(args.input)
        # Accept a bare session ID: resolve to the canonical events.jsonl path
        if not os.path.exists(input_path):
            candidate = os.path.expanduser(
                f"~/.copilot/session-state/{args.input}/events.jsonl"
            )
            if os.path.isfile(candidate):
                input_path = candidate
        if not os.path.isfile(input_path):
            print(f"Error: file not found: {input_path}", file=sys.stderr)
            sys.exit(1)
        if args.language and not args.story:
            print("Error: -l/--language is not valid together with --story.", file=sys.stderr)
            sys.exit(1)
        if args.force and not args.story:
            print("Error: -f/--force is not valid together with --story.", file=sys.stderr)
            sys.exit(1)
        output_path = os.path.join(os.path.dirname(input_path), "events.html")
        if os.path.exists(output_path) and not args.story:
            out_mtime = os.path.getmtime(output_path)
            if os.path.getmtime(input_path) <= out_mtime and _effective_self_mtime <= out_mtime:
                print(f"Up to date: {output_path}")
                return
        process_file(input_path, output_path, a11y=args.a11y, story=args.story, force=args.force, language=args.language)
        if args.story:
            generate_overview()
    else:
        # ── Batch mode: glob all session events ───────────────────────
        if args.story:
            print("Error: --story is not valid in batch mode.", file=sys.stderr)
            sys.exit(1)
        pattern = os.path.expanduser(DEFAULT_GLOB)
        paths = sorted(_glob.glob(pattern))
        if not paths:
            print(f"No files matched: {DEFAULT_GLOB}", file=sys.stderr)
            sys.exit(1)
        print(f"Processing {len(paths)} session file(s)…")
        ok = skipped = generated = 0
        for p in paths:
            out = os.path.join(os.path.dirname(p), "events.html")
            if os.path.exists(out):
                out_mtime = os.path.getmtime(out)
                if os.path.getmtime(p) <= out_mtime and _effective_self_mtime <= out_mtime:
                    skipped += 1
                    continue
            try:
                process_file(p, out, a11y=args.a11y)
                ok += 1
                generated += 1
            except Exception as exc:
                print(f"  ✗ {p}: {exc}", file=sys.stderr)
                skipped += 1
        print(f"\nDone: {ok} written, {skipped} skipped.")
        if generated:
            generate_overview()


if __name__ == "__main__":
    main()
