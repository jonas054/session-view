# session-view context

## Purpose

`session-view` is a local CLI for turning GitHub Copilot CLI session logs into self-contained HTML pages that are easy to browse afterward.

It reads `~/.copilot/session-state/*/events.jsonl` and produces:

- per-session `events.html`
- a shared `sessions-overview.html`
- optional cached story artifacts (`events.txt`, `story.txt`) for a Story tab

## Product boundary

- This is a local developer tool, not a web service.
- There is no build step, backend, or database owned by this repo.
- Generated output is written next to session logs under `~/.copilot/session-state/`.
- The UI must work as static `file://` HTML with inline CSS/JS and no external dependencies.

## Source of truth

- `session_view.py` is the behavioral source of truth.
- `~/bin/session_view` is expected to be a thin wrapper around this repo's Python script.
- `static/css/*`, `static/js/*`, and `static/icons/copilot.svg` are embedded into generated HTML.
- `SKILL.md` is working guidance for agents; this file is the higher-level product/context document.

## Core domain concepts

| Concept | Meaning |
| --- | --- |
| Session directory | One `~/.copilot/session-state/<session-id>/` directory. |
| Event log | The raw `events.jsonl` file for a session. |
| Session overview | Metadata derived from events: cwd, branch, timings, model usage, code changes, tools, intents, prompts. |
| Turn | A logical conversation unit: one user message plus the assistant steps that follow. |
| Assistant step | One rendered item inside a turn: text, reasoning, tool call, or sub-agent activity. |
| Story | A cached, text-to-speech-friendly narrative generated from parsed session events. |
| Search text | Flattened text collected from prompts, replies, reasoning, and intents for overview filtering. |

## Architecture

### 1. Ingest

- `load_events` reads JSONL into Python dicts.
- `build_overview` extracts session metadata from event types such as `session.start`, `user.message`, `tool.execution_start`, `subagent.started`, and `session.shutdown`.
- `build_turns` reconstructs human-readable turns from raw events and pairs tool/sub-agent start and completion events.

### 2. Session rendering

- `render_overview` builds the Overview tab for one session.
- `render_turns` and `render_steps` build the Conversation tab.
- `render_raw_events` builds the Raw Events tab.
- `render_html` wraps those tabs and injects inline CSS/JS.

### 3. Sessions overview rendering

- `read_session` scans each session directory and extracts the first prompt, search corpus, model, intent count, premium usage, and story availability.
- `build_overview_html` creates the all-sessions page data model and embeds it into `static/js/overview.js`.
- `generate_overview` discovers rendered sessions by scanning for `events.html`, merges persisted summaries, and writes `sessions-overview.html`.

### 4. Story pipeline

- `_parse_json_events` produces an intermediate `events.txt`.
- `generate_story` asks Copilot CLI for a plain-text story and caches it in `story.txt`.
- `read_story` reuses cached stories when available.

## Important invariants

1. Batch mode skips regeneration when `events.html` is newer than the source `events.jsonl`, `session_view.py`, and the static assets.
2. Single-session mode accepts either a direct `events.jsonl` path or a bare session ID.
3. `--story` is only valid in single-session mode and writes `story.txt` next to the session log.
4. Generated story output must be plain text returned directly by the model, with no file writes or tool use inside the story-generation prompt.
5. Overview search should cover more than the first prompt: prompts, assistant text, reasoning, and intent/tool-summary text are part of the searchable corpus.
6. Search context should survive navigation from the sessions overview into an individual session page.
7. `report_intent` contributes to intent tracking but is excluded from the "tools used" counts.
8. Internal story-generation sessions are hidden from the overview when their first prompt starts with `Read the Copilot session`.
9. Tool output rendering is type-aware: diffs, SQL, grep-style results, line-numbered `view` output, and markdown-capable agent output each have custom presentation rules.
10. Assistant reasoning may contain markdown and should keep rich formatting.
11. Multiline tool arguments must stay readable; bash, SQL, edit diffs, and `apply_patch` get special handling.
12. The accessible mode (`--a11y`) is a palette override, not a separate rendering pipeline.

## File map

- `session_view.py`: CLI, parsing, transformation, rendering, overview generation, story generation
- `static/js/events.js`: tab switching, raw-event navigation, search highlighting in session pages
- `static/js/overview.js`: overview sorting, grouping, filtering, snippet generation, query propagation
- `static/js/common.js`: shared JS escaping helpers
- `static/css/events.css`: session page styling
- `static/css/events.a11y.css`: colorblind-friendly overrides
- `static/css/overview.css`: all-sessions overview styling
- `static/css/common.css`: shared styling

## Change guidance

- Start in `session_view.py`; most behavior lives there.
- Assume features may need updates in both the per-session page and the sessions-overview page.
- Preserve the self-contained static HTML approach unless there is a strong reason not to.
- Favor explicit rendering rules over generic black-box formatting, because the tool exists to make session data readable.
- Keep generated artifacts compatible with local browsing and lightweight enough for large session histories.

## Current documentation state

- `README.md` is intentionally minimal and not enough to explain the domain.
- There is no `docs/adr/` directory yet.
- There is no repo-local automated test suite today; validation is currently command-driven/manual.
