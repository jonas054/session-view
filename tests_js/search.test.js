const test = require("node:test");
const assert = require("node:assert/strict");

const {
  SEARCH_FIELDS,
  normalizeSearchText,
  parseSearchFields,
  searchFieldsParam,
  searchFieldMatches,
} = require("../static/js/common.js");

test("search fields have the stable nine-field order", () => {
  assert.deepEqual(SEARCH_FIELDS, [
    "prompts",
    "replies",
    "reasoning",
    "intents",
    "tools",
    "directory",
    "model",
    "summary",
    "story",
  ]);
});

test("matching is case-insensitive and collapses whitespace", () => {
  assert.equal(normalizeSearchText("  Plan\n  the\toutput "), "plan the output");
  assert.equal(
    searchFieldMatches(
      { search_fields: { replies: "Plan\n\tthe output carefully" } },
      "replies",
      "plan the output",
    ),
    true,
  );
});

test("URL field state distinguishes absent, selected, and empty values", () => {
  assert.equal(parseSearchFields(new URL("file:///tmp/sessions-overview.html")), null);
  assert.deepEqual(
    [...parseSearchFields(new URL("file:///tmp/sessions-overview.html?match=prompts,story"))],
    ["prompts", "story"],
  );
  assert.equal(parseSearchFields(new URL("file:///tmp/sessions-overview.html?match=")).size, 0);
  assert.equal(
    searchFieldsParam(new Set(SEARCH_FIELDS)),
    "",
  );
  assert.equal(
    searchFieldsParam(new Set(["prompts", "story"])),
    "prompts,story",
  );
});
