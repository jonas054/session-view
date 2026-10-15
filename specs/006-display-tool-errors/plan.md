---
kind: sdd-plan
spec: 006-display-tool-errors
change: bugfix
status: approved
---

# Plan: Display tool errors in conversation

## Intent

Failed tool calls currently show a red cross without their recorded error
details. Make failures understandable in the Conversation tab at a glance and
show the complete error when a tool row is expanded.

## Scope

- In: Render failed tool status, a concise error preview, and full recorded
  error details in Conversation tool rows.
- Out: Changing tool execution, retry behavior, or Raw Events rendering.

## Current and expected behavior

Current: Tool completion events store failures under `data.error`, but
conversation rendering carries only the result and success flag. Failed rows
show a cross, and the expanded body does not show the error.

Expected: Failed rows show an explicit “Failed” status and a concise error
preview. Expanding a row shows a labeled, readable error message and code when
present, separately from the normal tool result.

## Behavior

### BUG-SV-0002: Display failed tool errors

WHEN a tool completion reports `success: false`, THE SYSTEM SHALL show an
explicit failure status and concise error preview in the conversation summary,
and show the full recorded error details when expanded.

Acceptance criteria:

- AC-001: Given a failed tool completion with an error message, when its
  conversation row is rendered, then the collapsed summary identifies the
  failure and previews the message, and the expanded row shows the full
  message and error code when present.
- AC-002: Given missing error details, when a failed row is expanded, then it
  says that no error details were recorded.
- AC-003: Given error text containing markup or line breaks, when rendered,
  then markup is escaped and the message remains readable.
- AC-004: Given a successful tool completion, when rendered, then no error
  panel is shown and its existing result display is preserved.

## Approach

Carry the completion error through the existing tool-result helper, use the
existing abbreviation and escaping helpers for the summary and full message,
and add a small error panel style in the Conversation tool body.

## Validation

- Add focused rendering tests for failure summaries, full details, escaping,
  missing error details, and unchanged successful results.
- Run the Python test suite and inspect the specified session in the local
  browser at desktop and narrow widths.

## Evidence

- Result: Failed tool rows show a labeled status and short preview; expanded
  rows show escaped, wrapped error text, error code, or a missing-details
  fallback.
- Tests: Four focused rendering tests passed. The specified session showed all
  five failed tool rows; desktop and narrow layouts had no horizontal
  overflow, and the browser console was clean.
- Validation: SDD artifact validation passed; Node tests passed (12/12).
  Pytest reported 70 passed and 2 pre-existing failures:
  `test_render_steps_displays_apply_patch_paths_in_order_and_escapes_them`,
  `test_render_steps_marks_empty_glob_results_in_heading`. The validation
  phase remains blocked on those failures.
- Changed files: `session_view.py`, `static/css/events.css`,
  `static/css/events.a11y.css`, and `tests/test_rendering.py`.
- Docs: Reviewed `README.md`, `CONTEXT.md`, and `SKILL.md`; no corrections
  were needed.
