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

function tokenizeSearchQuery(query) {
  const rawQuery = String(query || "");
  const tokens = [];
  let index = 0;

  while (index < rawQuery.length) {
    while (index < rawQuery.length && /\s/.test(rawQuery[index])) index++;
    if (index >= rawQuery.length) break;

    if (rawQuery[index] === '"') {
      const end = rawQuery.indexOf('"', index + 1);
      if (end >= 0 && (end + 1 === rawQuery.length || /\s/.test(rawQuery[end + 1]))) {
        const text = normalizeSearchText(rawQuery.slice(index + 1, end));
        if (text) tokens.push({ text, phrase: true, start: index, end: end + 1 });
        index = end + 1;
        continue;
      }
    }

    const start = index;
    while (index < rawQuery.length && !/\s/.test(rawQuery[index])) index++;
    const rawToken = rawQuery.slice(start, index);
    if (rawToken === "NOT") {
      tokens.push({ operator: true, start, end: index });
      continue;
    }

    const text = normalizeSearchText(rawToken);
    if (text) tokens.push({ text, phrase: false, start, end: index });
  }

  return tokens;
}

function searchClauseFromToken(token) {
  return { text: token.text, phrase: token.phrase };
}

function parseSearchQuery(query) {
  const groups = [[]];
  const operators = [];

  for (const token of tokenizeSearchQuery(query)) {
    if (token.operator) {
      operators.push(token);
      if (groups[groups.length - 1].length) groups.push([]);
      else if (groups.length === 1) groups.push([]);
      continue;
    }
    groups[groups.length - 1].push(searchClauseFromToken(token));
  }

  const exclusions = groups.slice(1).filter(group => group.length);
  if (!exclusions.length) {
    return {
      positive: groups[0].concat(
        operators.map(() => ({ text: "not", phrase: false }))
      ),
      exclusions: [],
    };
  }

  return {
    positive: groups[0],
    exclusions,
  };
}

function searchQueryOperatorPositions(query) {
  const tokens = tokenizeSearchQuery(query);
  return tokens
    .map((token, index) => (
      token.operator && tokens.slice(index + 1).some(next => !next.operator)
        ? { start: token.start, end: token.end }
        : null
    ))
    .filter(Boolean);
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

function searchClausePattern(clause) {
  if (!clause || !clause.text) return "";
  return clause.phrase
    ? clause.text.split(" ").map(escapeRegExp).join("\\s+")
    : escapeRegExp(clause.text);
}

function searchClausesRegex(clauses, flags = "gi") {
  const patterns = (clauses || [])
    .filter(clause => clause && clause.text)
    .slice()
    .sort((a, b) => Number(b.phrase) - Number(a.phrase) || b.text.length - a.text.length)
    .map(searchClausePattern);
  return patterns.length ? new RegExp("(" + patterns.join("|") + ")", flags) : null;
}

function searchQueryMatchesParsed(item, fields, parsed) {
  if (!parsed.positive.length && !parsed.exclusions.length) return true;
  if (!fields || !fields.size) return false;

  const matchesClause = clause => SEARCH_FIELDS.some(
    field => fields.has(field) && searchFieldMatchesNormalized(item, field, clause.text)
  );

  if (!parsed.positive.every(matchesClause)) return false;
  return parsed.exclusions.every(group => !group.every(matchesClause));
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
    searchQueryOperatorPositions,
    parseSearchFields,
    searchFieldsParam,
    searchFieldText,
    searchFieldMatches,
    searchClausesRegex,
    searchQueryMatchesParsed,
    searchQueryMatches,
  };
}
