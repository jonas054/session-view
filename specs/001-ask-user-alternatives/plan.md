---
kind: sdd-plan
spec: 001-ask-user-alternatives
change: bugfix
status: approved
---

# Plan: Display all alternatives for ask_user items

## Intent

Correct ask_user interaction rendering for the current Copilot argument and
response schemas while preserving legacy sessions, so every predefined
alternative is visible, the selected alternative is identified by its display
label, and unmatched answers remain custom answers.

## Scope

- In: Normalize current and legacy ask_user arguments and responses in
  `session_view.py`; derive alternatives from `requestedSchema` properties,
  including `oneOf` and applicable `enum` values; preserve submitted values
  for matching and use option titles as labels; add focused rendering tests.
- Out: Changes to generated HTML structure or styling, unrelated tool
  rendering, event ingestion, external dependencies, or raw session data.

## Current and expected behavior

The renderer currently reads only legacy `question`, `choices`, and
`allow_freeform` arguments. Current sessions provide `message` and
`requestedSchema.properties.<field>.oneOf` alternatives, so no choices are
rendered and a selected internal value is incorrectly shown as a custom
answer. The renderer should use `message` as the question fallback, show all
schema alternatives with their titles, match submitted values from
`content` or `detailedContent`, and show a custom answer only when no
predefined option matches.

## Behavior

### BUG-SV-0001: Rendering current ask_user alternatives

WHEN an ask_user tool call uses the current message/requestedSchema schema,
THE SYSTEM SHALL render every extracted alternative and mark only the
alternative whose submitted value matches the response.

Acceptance criteria:

- AC-001: Given a `message` and a schema property with `oneOf` entries, when
  the interaction is rendered, then the question and every alternative are
  shown, using each entry's `title` when present and retaining its `const` for
  matching.
- AC-002: Given a response such as `User responded:
  double_horizontal_render` or a `field: value` response in `content` or
  `detailedContent`, when the interaction is rendered, then only the matching
  alternative is marked selected and its visible title is shown in the
  summary.
- AC-003: Given applicable schema `enum` values, when the interaction is
  rendered, then those values are available as predefined alternatives and
  matching values are selected.
- AC-004: Given legacy `question`/`choices` arguments, when the interaction is
  rendered, then the existing question, alternatives, selection matching, and
  custom-answer fallback remain unchanged.
- AC-005: Given an answer that matches no predefined alternative, when the
  interaction is rendered, then it is shown as a custom answer and no
  predefined alternative is marked selected.

## Approach

Extend the existing ask_user normalization path in `session_view.py` rather
than changing the HTML structure. Represent extracted alternatives with their
submitted values and display labels, normalize legacy and current arguments,
parse both supported response fields and response prefixes, and reuse the
normalized state for the panel, summary, and searchable prompt content.

Optional implementation checklist:

- [x] Update ask_user state normalization for current and legacy schemas.
- [x] Match response values and render labels, selection state, and custom
  answers through the existing interaction panel.
- [x] Add behavior tests for the current `oneOf` schema and preserve legacy
  rendering/custom-answer coverage.

## Validation

- Run the focused ask_user rendering tests in `tests/test_rendering.py`.
- Run the complete `pytest` suite.
- Render the reported session or an equivalent current-schema fixture and
  verify that all alternatives appear and only the chosen alternative is
  selected.

## Evidence

- Result: Implemented current and legacy ask_user normalization, schema
  alternative extraction, response matching, selected-label summaries, and
  custom-answer fallback without changing the HTML structure.
- Tests: `.venv/bin/python -m pytest tests/test_rendering.py -q` (27 passed);
  `.venv/bin/python -m pytest tests/test_rendering.py -k ask_user -q`
  (6 passed, 21 deselected).
- Changed files: `session_view.py`, `tests/test_rendering.py`.
- Validation: `python3 /Users/jarv/.copilot/sdd-support/sdd/scripts/validate.py --root /Users/jarv/dev/session-view specs/001-ask-user-alternatives` passed, including the configured complete `pytest` suite.
- Reported-session rendering check: rendered the target session's current-schema
  `ask_user` step in memory; both oneOf titles were visible and only
  `Yes — render each logical cell two terminal columns wide (recommended)` had
  the selected marker. The generated session artifact was unchanged.
