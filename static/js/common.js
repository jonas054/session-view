function escapeRegExp(s) {
  const specials = "*+?^${}()|[]\\/.";
  let out = "";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    out += (specials.indexOf(ch) >= 0) ? String.fromCharCode(92) + ch : ch;
  }
  return out;
}

const SEARCH_FIELDS = Object.freeze([
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

const SEARCH_FIELD_LABELS = Object.freeze({
  prompts: "Prompts",
  replies: "Replies",
  reasoning: "Reasoning",
  intents: "Intents",
  tools: "Tools",
  directory: "Directory",
  model: "Model",
  summary: "Summary",
  story: "Story",
});

function normalizeSearchText(value) {
  return String(value || "").replace(/\s+/g, " ").trim().toLowerCase();
}

function parseSearchFields(url) {
  if (!url.searchParams.has("match")) return null;
  const raw = url.searchParams.get("match") || "";
  return new Set(
    raw.split(",").map(value => value.trim()).filter(value => SEARCH_FIELDS.includes(value))
  );
}

function searchFieldsParam(fields) {
  if (fields === null || SEARCH_FIELDS.every(field => fields.has(field))) return "";
  return SEARCH_FIELDS.filter(field => fields.has(field)).join(",");
}

function searchFieldText(item, field) {
  if (!item || !item.search_fields) return "";
  return String(item.search_fields[field] || "");
}

function searchFieldMatches(item, field, query) {
  const normalizedQuery = normalizeSearchText(query);
  return Boolean(normalizedQuery) &&
    normalizeSearchText(searchFieldText(item, field)).includes(normalizedQuery);
}

if (typeof module !== "undefined") {
  module.exports = {
    SEARCH_FIELDS,
    SEARCH_FIELD_LABELS,
    normalizeSearchText,
    parseSearchFields,
    searchFieldsParam,
    searchFieldText,
    searchFieldMatches,
  };
}
