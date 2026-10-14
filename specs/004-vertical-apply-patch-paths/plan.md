---
kind: sdd-plan
spec: 004-vertical-apply-patch-paths
change: feature
status: approved
---

# Plan: Show apply_patch paths vertically

## Intent

Tool summaries currently display extracted `apply_patch` paths in one comma-separated line, which makes multi-file changes harder to scan. Show each path on its own vertically stacked, left-aligned line while preserving the existing summary behavior.

## Scope

- In: Vertically display the paths extracted from `apply_patch` summaries, with focused rendering tests and narrowly scoped styling.
- Out: Changing patch handling or the summaries of tools other than `apply_patch`.

## Behavior

### REQ-SV-0004: Stack apply_patch paths vertically

WHEN an `apply_patch` summary contains one or more extracted file paths, THE SYSTEM SHALL display each path on its own vertically stacked, left-aligned line instead of joining paths with commas.

Acceptance criteria:

- AC-001: Given an `apply_patch` argument containing paths from the recognized `Update File`, `Add File`, `Delete File`, and `Move to` directives, when its summary is rendered, then non-empty paths appear in source order on separate lines.
- AC-002: Given an extracted path containing HTML-sensitive characters, when its summary is rendered, then the path remains HTML-escaped.
- AC-003: Given no extracted paths or a tool other than `apply_patch`, when a summary is rendered, then no path list is added and existing intent, status, timestamp, and other-tool summary behavior is preserved.

## Approach

Keep the existing apply_patch-only extraction, ordering, and escaping in `render_steps`; render each path separately and add scoped `.tool-file-paths` styling in `events.css` to make the list full-width, vertically stacked, and left-aligned. Update the focused tests in `tests/test_rendering.py` for layout markup, extraction, escaping, fallback, and preserved summary fields.

## Validation

- Run the focused apply_patch rendering tests in `tests/test_rendering.py` (including the path-order/escaping and no-path/other-tool cases).
- Browser preview, if desired, is subject to user approval; Playwright is unavailable, so this plan does not propose installing dependencies.

## Evidence

- Result: Rendered extracted apply_patch paths as individually escaped, vertically stacked summary lines after the summary metadata.
- Tests: `.venv/bin/python -m pytest tests/test_rendering.py` — 35 passed.
- Changed files: `session_view.py`, `static/css/events.css`, `tests/test_rendering.py`.
- Validation: `python3 "$SUPPORT_ROOT/sdd/scripts/validate.py" --root "$PWD" specs/004-vertical-apply-patch-paths` — passed.
