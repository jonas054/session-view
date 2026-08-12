const test = require("node:test");
const assert = require("node:assert/strict");

const {
  SEARCH_FIELDS,
  normalizeSearchText,
  parseSearchQuery,
  parseSearchFields,
  searchFieldsParam,
  searchFieldMatches,
  searchQueryMatchesParsed,
  searchQueryMatches,
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

test("uppercase standalone NOT splits positive and exclusion clauses", () => {
  assert.deepEqual(
    parseSearchQuery("  Foo NOT bar baz NOT Qux "),
    { positive: "foo", exclusions: ["bar baz", "qux"] },
  );
  assert.deepEqual(
    parseSearchQuery("NOT draft"),
    { positive: "", exclusions: ["draft"] },
  );
  assert.deepEqual(
    parseSearchQuery("foo not bar"),
    { positive: "foo not bar", exclusions: [] },
  );
  assert.deepEqual(
    parseSearchQuery("foo NOT"),
    { positive: "foo not", exclusions: [] },
  );
  assert.deepEqual(
    parseSearchQuery("foo NOT NOT bar"),
    { positive: "foo", exclusions: ["bar"] },
  );
});

test("query matching applies each exclusion across selected fields", () => {
  const fields = new Set(SEARCH_FIELDS);
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "foo only" } },
      fields,
      "foo NOT bar",
    ),
    true,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "foo", replies: "bar" } },
      fields,
      "foo NOT bar",
    ),
    false,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "foo", replies: "bar" } },
      new Set(["prompts"]),
      "foo NOT bar",
    ),
    true,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "draft notes" } },
      fields,
      "NOT draft",
    ),
    false,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "published notes" } },
      fields,
      "NOT draft",
    ),
    true,
  );
});

test("parsed query matching keeps normalized clauses reusable", () => {
  const fields = new Set(SEARCH_FIELDS);
  const parsed = parseSearchQuery("  Foo NOT bar ");
  assert.equal(
    searchQueryMatchesParsed(
      { search_fields: { prompts: "foo only" } },
      fields,
      parsed,
    ),
    true,
  );
  assert.equal(
    searchQueryMatchesParsed(
      { search_fields: { prompts: "foo", replies: "bar" } },
      fields,
      parsed,
    ),
    false,
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
