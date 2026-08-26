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

The sessions overview search matches prompts, replies, reasoning, intents, tools, directory, model, summary, and Story text by default. Unquoted words are case-insensitive substrings; all words must match, in any order, and may be found in different selected fields. Surround a phrase with double quotes to require it as a contiguous substring within one selected field. Use the **Match in** checkboxes to narrow the fields, or use **All** and **None** for bulk changes. The query and selected fields are kept in the URL so filtered links can be shared and session-page highlighting preserves the same scope.

Use uppercase `NOT` to exclude matches, for example `foo NOT bar` keeps sessions matching `foo` but excludes sessions matching `bar`. Multiple unquoted words in one `NOT` clause must all match; use additional `NOT` clauses to exclude alternatives. Quoted phrases and unquoted words can be combined, and `NOT` inside quotes is literal.
