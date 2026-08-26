const test = require("node:test");
const assert = require("node:assert/strict");

const {
  SEARCH_FIELDS,
  normalizeSearchText,
  parseSearchQuery,
  searchQueryOperatorPositions,
  parseSearchFields,
  searchFieldsParam,
  searchFieldMatches,
  searchQueryMatchesParsed,
  searchQueryMatches,
} = require("../static/js/common.js");

const term = text => ({ text, phrase: false });
const phrase = text => ({ text, phrase: true });

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
    {
      positive: [term("foo")],
      exclusions: [[term("bar"), term("baz")], [term("qux")]],
    },
  );
  assert.deepEqual(
    parseSearchQuery("NOT draft"),
    { positive: [], exclusions: [[term("draft")]] },
  );
  assert.deepEqual(
    parseSearchQuery("foo not bar"),
    { positive: [term("foo"), term("not"), term("bar")], exclusions: [] },
  );
  assert.deepEqual(
    parseSearchQuery("foo NOT"),
    { positive: [term("foo"), term("not")], exclusions: [] },
  );
  assert.deepEqual(
    parseSearchQuery("foo NOT NOT bar"),
    { positive: [term("foo")], exclusions: [[term("bar")]] },
  );
});

test("quoted phrases and unquoted terms form ANDed clauses", () => {
  assert.deepEqual(
    parseSearchQuery('foo "bar  baz" qux NOT "draft notes" pending'),
    {
      positive: [term("foo"), phrase("bar baz"), term("qux")],
      exclusions: [[phrase("draft notes"), term("pending")]],
    },
  );
  assert.deepEqual(
    parseSearchQuery('"foo NOT bar" NOT baz'),
    {
      positive: [phrase("foo not bar")],
      exclusions: [[term("baz")]],
    },
  );
});

test("NOT operators are recognized only outside complete phrases", () => {
  assert.deepEqual(
    searchQueryOperatorPositions('"foo NOT bar" NOT baz NOT'),
    [{ start: 14, end: 17 }],
  );
});

test("unmatched or adjacent quotes stay ordinary unquoted terms", () => {
  assert.deepEqual(
    parseSearchQuery('"foo bar'),
    { positive: [term('"foo'), term("bar")], exclusions: [] },
  );
  assert.deepEqual(
    parseSearchQuery('foo"bar baz"'),
    { positive: [term('foo"bar'), term('baz"')], exclusions: [] },
  );
  assert.deepEqual(
    parseSearchQuery('"" foo'),
    { positive: [term("foo")], exclusions: [] },
  );
});

test("unquoted terms match all selected fields in any order", () => {
  const fields = new Set(SEARCH_FIELDS);
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "Render", replies: "output" } },
      fields,
      "render output",
    ),
    true,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "output", replies: "render" } },
      fields,
      "render output",
    ),
    true,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "Render", replies: "output" } },
      new Set(["prompts"]),
      "render output",
    ),
    false,
  );
});

test("quoted phrases require a contiguous match in one field", () => {
  const fields = new Set(SEARCH_FIELDS);
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "Render\n\toutput carefully" } },
      fields,
      '"render output"',
    ),
    true,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "Render the output" } },
      fields,
      '"render output"',
    ),
    false,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "Render", replies: "output" } },
      fields,
      '"render output"',
    ),
    false,
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
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "foo bar" } },
      fields,
      "foo NOT bar baz",
    ),
    true,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "foo bar baz" } },
      fields,
      "foo NOT bar baz",
    ),
    false,
  );
  assert.equal(
    searchQueryMatches(
      { search_fields: { prompts: "foo bar" } },
      fields,
      "foo NOT bar NOT baz",
    ),
    false,
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
