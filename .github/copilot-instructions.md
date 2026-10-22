# Copilot instructions

## Commands

Set up the Python test environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Run the CLI in batch mode, for one session, or with Story generation:

```sh
python session_view.py
python session_view.py <session-id-or-events.jsonl>
python session_view.py --story <session-id-or-events.jsonl>
```

Run the Python suite or one test:

```sh
python -m pytest
python -m pytest tests/test_rendering.py::test_build_overview_tracks_metrics_and_excludes_report_intent_from_tools_used
```

Run the JavaScript suite or one test:

```sh
node --test tests_js/search.test.js
node --test --test-name-pattern='uppercase standalone NOT splits positive and exclusion clauses' tests_js/search.test.js
```

## Architecture

- This is a local Python CLI, not a web service. `session_view.py` is the
  behavioral source of truth: it reads
  `~/.copilot/session-state/<session-id>/events.jsonl` and writes standalone
  `events.html` pages plus `sessions-overview.html`.
- A session page is built by parsing events, extracting metadata and
  reconstructing turns, then rendering Overview, Conversation, and Raw Events
  tabs. `--story` optionally calls the local `copilot` CLI and caches
  `events.txt` and `story.txt` beside the source log.
- The overview scans rendered sessions, builds searchable session data, merges
  saved summaries, and embeds the data in its HTML. In the browser,
  `overview.js` handles list filtering, sorting, and snippets; `events.js`
  handles tabs and search highlighting within a session.
- Files under `static/` are read by the Python renderer and embedded into the
  generated pages. The pages must continue to work when opened directly as
  `file://` URLs.

## Repository-specific constraints

- Search is cross-layer: Python builds `search_fields`, `common.js` parses and
  matches queries, `overview.js` filters the list, and `events.js` highlights
  matches after navigation. Keep Python's `SEARCH_FIELD_ORDER` aligned with
  JavaScript's `SEARCH_FIELDS` and labels, and preserve the `q` and `match` URL
  parameters. `common.js` is shared by the browser and Node tests.
- Session logs are local user data. Tests that read or write session state
  should use the `isolated_home` fixture from `tests/conftest.py`, not the
  actual `~/.copilot` directory.
- Batch rendering is freshness-checked using source, renderer, asset, and
  story modification times. Keep those checks in mind when changing generated
  output or adding assets.
- Overview activity counts user prompts, not `report_intent` events. The
  overview hides internal story-generation sessions and lists at most the
  newest 1,000 sessions by start time.
- Story generation is an optional cached path. Keep its prompt's plain-text
  response contract and inspect both generation and Story-tab rendering when
  changing it.
- Use the existing HTML escaping and script-safe JSON embedding helpers when
  rendering event content into generated pages.

`CONTEXT.md` and `SKILL.md` contain additional domain and workflow context;
check behavior against `session_view.py` when details conflict.
