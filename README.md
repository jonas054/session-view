# session-view
Creates web pages to view conversations with GitHub Copilot CLI

## Running the tests

Create a virtual environment, install the dev dependency, and run `pytest`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
node --test tests_js/search.test.js
```

## Overview search

The overview lists at most the 1,000 newest sessions, based on start time.

The sessions overview search matches prompts, replies, reasoning, intents, tools, directory, branch, model, summary, and Story text by default. Unquoted words are case-insensitive substrings; all words must match, in any order, and may be found in different selected fields. Surround a phrase with double quotes to require it as a contiguous substring within one selected field. Use the **Match in** checkboxes to narrow the fields, or use **All** and **None** for bulk changes. The query and selected fields are kept in the URL so filtered links can be shared and session-page highlighting preserves the same scope.

The overview's Model column lists models that account for at least 5% of the session's input and output tokens. If token metrics are unavailable, it falls back to the initially selected model, or the first observed model if none was recorded.

Use uppercase `NOT` to exclude matches, for example `foo NOT bar` keeps sessions matching `foo` but excludes sessions matching `bar`. Multiple unquoted words in one `NOT` clause must all match; use additional `NOT` clauses to exclude alternatives. Quoted phrases and unquoted words can be combined, and `NOT` inside quotes is literal.
