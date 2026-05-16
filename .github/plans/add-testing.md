# Goal

Add a behavior-first test suite for `session_view.py` that guards the user-visible invariants described in `CONTEXT.md` and the supported CLI modes.

## Definition of done

The suite is considered comprehensive when it covers these behavior groups:

1. CLI modes and validation
2. Event ingest and turn reconstruction
3. Per-session rendering
4. Sessions-overview generation
5. Search contracts owned by Python
6. Story generation, caching, and failure handling
7. `--a11y` rendering mode
8. Summary merge behavior in `generate_overview()`

This is **not** a line-by-line helper coverage goal, and it does **not** require a numeric coverage threshold.

## Testing strategy

- Use `pytest`.
- Keep setup minimal: `requirements-dev.txt` plus `pytest.ini`.
- Prefer small, synthetic `events.jsonl` fixtures that isolate one behavior at a time.
- Use plain fixture files and normal `pytest` assertions for golden-style checks.
- Lean on behavior-level golden tests, backed by focused unit tests for tricky transforms.
- Assert meaningful HTML fragments and normalized snippets, not entire full-page documents byte-for-byte.
- Test CLI behavior by calling `main()` in-process with patched `sys.argv`, not by spawning subprocesses.
- Keep the suite at renderer/output level; do not introduce browser automation.

## Allowed production changes

Surgical refactors are allowed when they improve testability, especially:

- isolating filesystem path resolution so tests run entirely in temp directories
- isolating subprocess seams used by story generation
- extracting a few pure helpers where that makes behavior tests simpler and clearer

Do not turn this into a large multi-file rewrite before writing tests.

## Scope details

### Include

- single-session mode, including bare session IDs
- batch mode regeneration behavior
- `events.html` session rendering
- `sessions-overview.html` generation
- overview search corpus assembly and query-propagation contracts
- story cache hits, successful story generation, and story timeout/failure handling
- a11y stylesheet injection
- summary merge behavior from JSON and SQLite sources

### Exclude

- browser-driven testing of `overview.js` / `events.js`
- exact byte-for-byte snapshots of full generated HTML pages
- CI setup in this phase
- blanket tests for every internal helper just because it exists

## Execution order

1. Add the minimal test harness and repo-local test configuration.
2. Create the path/subprocess seams needed for temp-dir and mocked-story testing.
3. Add a thin smoke layer that touches every required behavior group.
4. Deepen coverage with focused synthetic fixtures for edge cases and fragile rendering logic.

## Failure-path policy

Cover failure paths selectively where they matter most to users:

- CLI/input-validation failures
- story subprocess failure and timeout behavior

Do not try to exhaustively test every defensive branch in the file.
