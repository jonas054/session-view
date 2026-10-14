---
kind: sdd-plan
spec: 003-apply-patch-tool-paths
change: feature
status: approved
---

# Plan: Show file paths in apply_patch tool summaries

## Intent

Show affected file paths at a glance in `apply_patch` tool summaries without changing existing summary metadata or summaries for other tools.

## Scope

- In: Extract paths from `*** Update File:`, `*** Add File:`, `*** Delete File:`, and `*** Move to:` directives in raw `apply_patch` arguments and display every path, comma-separated, in the tool-summary heading with HTML escaping. Leave the existing summary unchanged when no recognized path is present.
- Out: Changes to non-`apply_patch` summaries, existing intent/status/timestamp content, or patch processing beyond displaying paths.

## Behavior

### REQ-SV-0003: Show affected paths in apply_patch summaries

WHEN an `apply_patch` tool call contains one or more recognized file directives, THE SYSTEM SHALL display their paths, comma-separated in directive order, in that call's tool-summary heading, HTML-escaped, while preserving existing intent, status, and timestamp content.

Acceptance criteria:

- AC-001: Given raw `apply_patch` arguments containing `Update File`, `Add File`, `Delete File`, or `Move to` directives, when the tool summary is rendered, then every declared path appears comma-separated and HTML-escaped in the heading.
- AC-002: Given `apply_patch` arguments with no recognized file path, when the tool summary is rendered, then the existing summary remains unchanged.
- AC-003: Given an `apply_patch` summary with existing intent, status, or timestamps, when paths are displayed, then that content remains unchanged; summaries for all other tools also remain unchanged.

## Approach

Use the stored raw arguments on tool steps and the existing file-directive recognition in `render_args` to extract paths for `apply_patch` summaries in `render_steps`. Add the escaped paths only to the `apply_patch` heading, and cover directive extraction, escaping, fallback, and compatibility in `tests/test_rendering.py`.

## Validation

- Run `pytest tests/test_rendering.py`, including focused checks for each recognized directive, HTML escaping, no-path fallback, and preservation of existing summary content and other tool summaries.

## Evidence

- Result: Apply-patch summaries display HTML-escaped paths from all four directive types in order; no-path, tool metadata, and other-tool summaries remain unchanged.
- Tests: `.venv/bin/python -m pytest tests/test_rendering.py` — 35 passed.
- Changed files: `session_view.py`, `tests/test_rendering.py`.
- Validation: `python3 "$SUPPORT_ROOT/sdd/scripts/validate.py" --root "$PWD" specs/003-apply-patch-tool-paths` — SDD validation passed.
