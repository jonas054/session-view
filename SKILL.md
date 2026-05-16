---
name: session-view
description: Guidance for working on the session_view session-log renderer. Use this when asked to change session_view behavior, events.html rendering, sessions-overview.html, story generation, search, or events.jsonl parsing.
---

Use this skill for work on the personal `session_view` tooling. The command users run lives under `~/bin`, but the Python implementation is in `~/dev/session-view`.

## What to treat as the source of truth

- `~/bin/session_view` is a thin Bash wrapper that runs `python3 ~/dev/session-view/session_view.py`.
- `~/dev/session-view/session_view.py` is the main Python implementation and the source of truth for behavior changes.

## What the tool does

- Renders `~/.copilot/session-state/*/events.jsonl` into per-session `events.html`.
- Rebuilds `~/.copilot/session-state/sessions-overview.html`.
- Accepts either a full `events.jsonl` path or a bare session ID in single-session mode.
- Supports `--story` with cached `story.txt` and intermediate `events.txt`.
- Supports `--a11y` output.

## High-value entry points in `~/dev/session-view/session_view.py`

- `build_overview`: extracts session metadata, user messages, intents, tools, code changes, and model usage.
- `build_turns`: reconstructs readable conversation turns from raw events.
- `render_tool_result` and `render_args`: tool-card rendering, including diff, grep, SQL, and multiline argument handling.
- `markdown_to_html`: markdown rendering used for assistant text and reasoning blocks.
- `render_html`: wraps the session page tabs and shared UI.
- `read_session`, `build_overview_html`, `generate_overview`: overview-page generation and search data.
- `_parse_json_events`, `generate_story`, `read_story`: story pipeline.
- `load_events`, `process_file`, `main`: CLI behavior and batch/single-session flow.

## Existing behavior to preserve

1. Batch mode skips regenerating `events.html` when the output is newer than both `events.jsonl` and the Python implementation, and regenerates the overview after relevant changes.
2. Story generation must tell the model to return plain text directly and not write files or use tools. This avoids the previous `narrative.txt` failure mode seen in prior sessions.
3. Multiline string tool arguments should render with separate RAW and PRETTY views rather than a single collapsed dump.
4. Assistant reasoning text can contain markdown and should keep rich formatting.
5. Overview search is broader than the first prompt: it should cover prompts, replies, reasoning text, intents, and tool summaries/snippets.
6. When search matches come from a snippet row on the overview page, navigation should still link into the corresponding session page.

## Working style for changes

- Start from `~/dev/session-view/session_view.py`.
- Trace whether the change affects both the per-session page and the overview page; many features do.
- For story-related changes, inspect both story generation and Story-tab insertion.
- For search-related changes, inspect both overview indexing and per-session `?q=` highlighting behavior.
- Preserve the existing self-contained static HTML/CSS/JS approach.

## Useful commands

```bash
session_view <session-id-or-path>
session_view --story <session-id-or-path>
session_view --story --force -l English <session-id-or-path>
session_view
```

Outputs live under `~/.copilot/session-state/<session-id>/events.html` and `~/.copilot/session-state/sessions-overview.html`.

## Changes already made in prior sessions

- Merged the earlier `session_viewer` and overview flow into `session_view`.
- Added timestamp-based regeneration logic.
- Added support for bare session IDs as input.
- Hardened story generation.
- Improved reasoning markdown rendering.
- Improved overview search and row-link behavior.
