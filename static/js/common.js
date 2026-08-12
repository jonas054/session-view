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

function parseSearchQuery(query) {
  const rawQuery = String(query || "");
  const parts = rawQuery.split(/(?:^|\s)NOT(?=\s|$)/);
  const exclusions = parts.slice(1)
    .map(normalizeSearchText)
    .filter(Boolean);

  if (!exclusions.length) {
    return {
      positive: normalizeSearchText(rawQuery),
      exclusions: [],
    };
  }

  return {
    positive: normalizeSearchText(parts[0]),
    exclusions,
  };
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

const normalizedSearchFieldsCache = new WeakMap();

function normalizedSearchFieldText(item, field) {
  if (!item || (typeof item !== "object" && typeof item !== "function")) return "";

  let normalizedFields = normalizedSearchFieldsCache.get(item);
  if (!normalizedFields) {
    normalizedFields = Object.create(null);
    normalizedSearchFieldsCache.set(item, normalizedFields);
  }

  if (!Object.prototype.hasOwnProperty.call(normalizedFields, field)) {
    normalizedFields[field] = normalizeSearchText(searchFieldText(item, field));
  }
  return normalizedFields[field];
}

function searchFieldMatchesNormalized(item, field, normalizedQuery) {
  return Boolean(normalizedQuery) &&
    normalizedSearchFieldText(item, field).includes(normalizedQuery);
}

function searchFieldMatches(item, field, query) {
  return searchFieldMatchesNormalized(item, field, normalizeSearchText(query));
}

function searchQueryMatchesParsed(item, fields, parsed) {
  if (!parsed.positive && !parsed.exclusions.length) return true;
  if (!fields || !fields.size) return false;

  const matchesClause = clause => SEARCH_FIELDS.some(
    field => fields.has(field) && searchFieldMatchesNormalized(item, field, clause)
  );

  if (parsed.positive && !matchesClause(parsed.positive)) return false;
  return parsed.exclusions.every(clause => !matchesClause(clause));
}

function searchQueryMatches(item, fields, query) {
  return searchQueryMatchesParsed(item, fields, parseSearchQuery(query));
}

if (typeof module !== "undefined") {
  module.exports = {
    SEARCH_FIELDS,
    SEARCH_FIELD_LABELS,
    normalizeSearchText,
    parseSearchQuery,
    parseSearchFields,
    searchFieldsParam,
    searchFieldText,
    searchFieldMatches,
    searchQueryMatchesParsed,
    searchQueryMatches,
  };
}
