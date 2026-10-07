---
kind: sdd-plan
spec: 002-session-store-sql-tables
change: feature
status: approved
---

# Plan: Render session_store_sql results as HTML tables

## Intent

Render Markdown tables returned by `session_store_sql` as HTML tables in tool
result boxes, rather than displaying the pipe-delimited source.

## Scope

- In: Use the existing Markdown result rendering for `session_store_sql` output
  so its tables use the current table markup and styling.
- Out: Changing other tools' result rendering, the Markdown parser, query
  arguments, or adding dependencies.

## Behavior

### REQ-SV-0002: Rendering session_store_sql Markdown tables

WHEN a `session_store_sql` result contains a Markdown table, THE SYSTEM SHALL
render it as an HTML table in the result box instead of showing raw Markdown.

Acceptance criteria:

- AC-001: Given a `session_store_sql` result with a Markdown header, separator,
  and data rows, when rendered, then the result contains an HTML table with the
  corresponding header and cells, not the raw table separator.
- AC-002: Given a Markdown table returned by another tool, when rendered, then
  that tool keeps its existing result-rendering behavior.

## Approach

Extend the existing Markdown-rendered SQL result branch to include
`session_store_sql`, reusing `markdown_to_html` and the existing SQL-result
table styles. Add focused regression coverage for the new tool and unchanged
other-tool behavior.

Optional implementation checklist:

- [x] Render `session_store_sql` output through the existing Markdown path.
- [x] Add regression tests for table markup and other-tool fallback behavior.

## Validation

- Run the focused `session_store_sql` rendering tests in `tests/test_rendering.py`.
- Run the complete `pytest` suite.
- Generate a local session page and inspect the result box in a headed browser.

## Evidence

- Result: `session_store_sql` results use the existing Markdown renderer and
  SQL-result table styles; other tool rendering is unchanged.
- Tests: `.venv/bin/python -m pytest tests/test_rendering.py -k session_store_sql -q`
  (1 passed, 32 deselected).
- Validation: SDD validator passed; `.venv/bin/python -m pytest` (63 passed).
- Browser: Headed desktop and narrow previews showed HTML table headers and
  cells; no page overflow or console errors.
- Changed files: `session_view.py`, `tests/test_rendering.py`, `CONTEXT.md`.
