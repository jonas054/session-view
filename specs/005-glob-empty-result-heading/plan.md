---
kind: sdd-plan
spec: 005-glob-empty-result-heading
change: feature
status: approved
---

# Plan: Indicate empty glob results in tool headings

## Intent

Collapsed `glob` tool headings do not make empty searches apparent. Show a “No files found” indicator when a successful glob result contains no matches.

## Scope

- In: the collapsed heading for successful `glob` tool calls that found no files.
- Out: failed glob calls, other tools, and existing argument/result-body rendering.

## Behavior

### REQ-SV-0006: Indicate empty glob results

WHEN a `glob` tool call completes successfully with no files found, THE SYSTEM SHALL show “No files found” in its heading while preserving any existing intent summary.

Acceptance criteria:

- AC-001: Given a successful `glob` call with no matches, when rendered, then its heading includes “No files found.”
- AC-002: Given a `glob` call with matches or an unsuccessful result, when rendered, then its heading does not include the indicator.
- AC-003: Other tool headings and the existing result body remain unchanged.

## Approach

- Detect an explicit empty result for `glob` calls and add the indicator alongside the existing heading summary.
- Add focused rendering tests for empty, non-empty, and unsuccessful glob results.

## Validation

- Run `python -m pytest tests/test_rendering.py`.

## Evidence

- Result: Successful empty `glob` headings now include “No files found,” preserving the existing summary and result body.
- Tests: The focused glob-heading test passes. The full rendering module has one unrelated apply-patch path-order failure; live browser preview was skipped after user approval because Playwright is unavailable.
- Validation: The SDD validator passed for `specs/005-glob-empty-result-heading`.
- Changed files: `session_view.py`, `tests/test_rendering.py`.
