const DATA = __DATA__;
let sortCol = 0;   // 0=ts, 1=cwd, 2=model, 3=activity, 4=premium, 5=story, 6=summary, 7=prompt
let sortAsc = false;
let query = '';
let selectedFields = new Set(SEARCH_FIELDS);
const collapsed = new Set();
const snippetPriority = [
  "prompts",
  "replies",
  "reasoning",
  "intents",
  "tools",
  "story",
  "directory",
  "model",
  "summary",
];
const scopedSearchAvailable = DATA.every(
  item => item.search_fields && typeof item.search_fields === "object"
);

function getGroupKey(item, col) {
  if (col === 0) return item.ts.slice(0, 10);       // YYYY-MM-DD
  if (col === 1) return item.cwd || '(none)';
  if (col === 2) return item.model || '(unknown)';
  if (col === 3) return String(item.activity_total);
  if (col === 4) return String(item.premium_requests || 0);
  if (col === 5) return item.has_story ? 'yes' : 'no';
  if (col === 6) return item.summary || '-';
  const words = (item.prompt || '').trim().split(/\s+/);
  return words.slice(0, 6).join(' ') + (words.length > 6 ? '…' : '') || '(empty)';
}

function getSortVal(item, col) {
  if (col === 0) return item.ts_raw;
  if (col === 1) return (item.cwd || '').toLowerCase();
  if (col === 2) return (item.model || '').toLowerCase();
  if (col === 3) return item.activity_total;
  if (col === 4) return item.premium_requests || 0;
  if (col === 5) return item.has_story ? 1 : 0;
  if (col === 6) return (item.summary || '').toLowerCase();
  if (col === 7) return (item.prompt || '').toLowerCase();
  return '';
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function highlightSearchQuery(value) {
  const text = String(value || '');
  const re = /(^|\s)NOT(?=\s|$)/g;
  let html = '';
  let lastIndex = 0;
  let match;

  while ((match = re.exec(text))) {
    const operatorStart = match.index + match[1].length;
    html += escHtml(text.slice(lastIndex, operatorStart));
    html += '<span class="search-operator">NOT</span>';
    lastIndex = operatorStart + 3;
  }

  return html + escHtml(text.slice(lastIndex));
}

function syncSearchHighlightScroll() {
  const input = document.getElementById('search');
  const highlight = document.getElementById('search-highlight');
  if (input && highlight) highlight.scrollLeft = input.scrollLeft;
}

function updateSearchHighlight() {
  const input = document.getElementById('search');
  const highlight = document.getElementById('search-highlight');
  if (!input || !highlight) return;
  highlight.innerHTML = highlightSearchQuery(input.value);
  input.classList.toggle('has-query', Boolean(input.value));
  syncSearchHighlightScroll();
}

function makeSnippet(text, q, maxLen = 140) {
  if (!q || !text) return '';
  const t = String(text);
  const tl = t.toLowerCase();
  const tokens = q.trim().split(/\s+/).filter(Boolean);
  if (!tokens.length) return '';
  let firstIdx = -1;
  for (const tok of tokens) {
    const idx = tl.indexOf(tok.toLowerCase());
    if (idx >= 0 && (firstIdx === -1 || idx < firstIdx)) {
      firstIdx = idx;
    }
  }
  if (firstIdx === -1) return '';
  const half = Math.floor(maxLen / 2);
  let start = Math.max(0, firstIdx - Math.floor(half/2));
  let end = Math.min(t.length, firstIdx + half);
  if (end - start > maxLen) end = start + maxLen;
  let snippetText = t.slice(start, end);
  const prefix = start > 0 ? '…' : '';
  const suffix = end < t.length ? '…' : '';
  const re = new RegExp('(' + tokens.map(escapeRegExp).join('|') + ')', 'gi');
  const parts = snippetText.split(re);
  const out = parts.map((part, i) => (i % 2 === 1) ? '<mark class="search-match">' + escHtml(part) + '</mark>' : escHtml(part)).join('');
  return prefix + out + suffix;
}

function highlightText(text, q) {
  if (!q || !text) return escHtml(text);
  const t = String(text);
  const tokens = q.trim().split(/\s+/).filter(Boolean);
  if (!tokens.length) return escHtml(text);
  const re = new RegExp('(' + tokens.map(escapeRegExp).join('|') + ')', 'gi');
  const parts = t.split(re);
  return parts.map((part, i) => (i % 2 === 1) ? '<mark class="search-match">' + escHtml(part) + '</mark>' : escHtml(part)).join('');
}

function makeRowClickable(tr, href) {
  tr.addEventListener('click', e => {
    if (e.target.closest('a')) return;
    window.location.href = href;
  });
}

function allFieldsSelected() {
  return selectedFields.size === SEARCH_FIELDS.length;
}

function syncMatchParam(url) {
  if (allFieldsSelected()) {
    url.searchParams.delete('match');
  } else {
    url.searchParams.set('match', SEARCH_FIELDS.filter(field => selectedFields.has(field)).join(','));
  }
}

function buildSessionHref(path, hash) {
  const url = new URL(`file://${path}`);
  if (query) url.searchParams.set('q', query);
  syncMatchParam(url);
  if (hash) url.hash = hash;
  return url.toString();
}

function syncSearchUrl(value) {
  const url = new URL(window.location.href);
  if (value) url.searchParams.set('q', value);
  else url.searchParams.delete('q');
  syncMatchParam(url);
  history.replaceState(null, '', url);
}

function loadSearchStateFromUrl() {
  const url = new URL(window.location.href);
  query = url.searchParams.get('q') || '';
  const fields = parseSearchFields(url);
  selectedFields = fields === null ? new Set(SEARCH_FIELDS) : fields;
}

function fieldMatches(item, field, q) {
  return selectedFields.has(field) && searchFieldMatches(item, field, q);
}

function matchesQuery(item, q) {
  if (!q) return true;
  if (!scopedSearchAvailable || !selectedFields.size) return false;
  return searchQueryMatches(item, selectedFields, q);
}

function makeDirectorySnippet(item, q, maxLen) {
  return makeSnippet(searchFieldText(item, 'directory'), q, maxLen) || '';
}

function primaryMatchField(item, q) {
  const positiveQuery = parseSearchQuery(q).positive;
  if (!positiveQuery || !scopedSearchAvailable || !selectedFields.size) return '';
  return snippetPriority.find(field => fieldMatches(item, field, positiveQuery)) || '';
}

function makePrimarySnippet(item, q, promptMatched, snippetSize) {
  const field = primaryMatchField(item, q);
  if (!field || (field === 'prompts' && promptMatched)) return null;

  const positiveQuery = parseSearchQuery(q).positive;
  const text = searchFieldText(item, field);
  const snippet = field === 'directory'
    ? makeDirectorySnippet(item, positiveQuery, snippetSize)
    : makeSnippet(text, positiveQuery, field === 'story' ? 2 * snippetSize : 2 * snippetSize);
  if (!snippet) return null;
  return {
    field,
    html: `<span class="snippet-label">${escHtml(SEARCH_FIELD_LABELS[field])}:</span> ${snippet}`,
  };
}

function sessionHashFor(item, q) {
  const field = primaryMatchField(item, q);
  if (field === 'story') return 'story';
  if (["prompts", "replies", "reasoning", "intents", "tools"].includes(field)) return 'turns';
  if (field) return 'overview';
  return 'turns';
}

function updateSearchControls() {
  const fieldset = document.getElementById('search-fields');
  const disabled = !scopedSearchAvailable;
  if (fieldset) fieldset.classList.toggle('search-fields-unavailable', disabled);

  document.querySelectorAll('#search-fields input[data-search-field]').forEach(input => {
    input.checked = selectedFields.has(input.dataset.searchField);
    input.disabled = disabled;
  });
  document.querySelectorAll('#search-fields button').forEach(button => {
    button.disabled = disabled;
  });
}

function updateSearchStatus(count) {
  const status = document.getElementById('search-status');
  if (!status) return;
  const activeQuery = normalizeSearchText(query);
  if (!scopedSearchAvailable) {
    status.className = 'search-status search-status-error';
    status.textContent = 'Scoped search data is unavailable. Regenerate sessions-overview.html with session_view.';
  } else if (activeQuery && !selectedFields.size) {
    status.className = 'search-status search-status-warning';
    status.textContent = 'Select at least one field to search.';
  } else {
    status.className = 'search-status';
    status.textContent = activeQuery
      ? `${count} matching session${count === 1 ? '' : 's'}`
      : `${count} session${count === 1 ? '' : 's'}`;
  }
}

function toggleGroup(gk) {
  if (collapsed.has(gk)) collapsed.delete(gk); else collapsed.add(gk);
  render();
}

function render() {
  const q = String(query || '').trim();
  const positiveQuery = parseSearchQuery(q).positive;
  const filtered = DATA.filter(item => matchesQuery(item, q));

  filtered.sort((a, b) => {
    const av = getSortVal(a, sortCol), bv = getSortVal(b, sortCol);
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return sortAsc ? cmp : -cmp;
  });

  const useGroups = true;
  const groupCounts = {};
  if (useGroups) {
    filtered.forEach(item => {
      const gk = getGroupKey(item, sortCol);
      groupCounts[gk] = (groupCounts[gk] || 0) + 1;
    });
  }

  const frag = document.createDocumentFragment();
  let curGroup;

  filtered.forEach(item => {
    const gk = useGroups ? getGroupKey(item, sortCol) : null;

    if (gk !== null && gk !== curGroup) {
      curGroup = gk;
      const isCollapsed = collapsed.has(gk);
      const cnt = groupCounts[gk];
      const tr = document.createElement('tr');
      tr.className = 'group-header';
      tr.dataset.group = gk;
      tr.innerHTML =
        `<td colspan="8">` +
        `<span class="group-toggle">${isCollapsed ? '▶' : '▼'}</span> ` +
        `<strong>${escHtml(gk)}</strong>` +
        `<span class="group-count">${cnt} session${cnt === 1 ? '' : 's'}</span></td>`;
      tr.addEventListener('click', () => toggleGroup(gk));
      frag.appendChild(tr);
    }

    if (!useGroups || !collapsed.has(gk)) {
      const tr = document.createElement('tr');
      tr.className = 'data-row';
      if (gk !== null) tr.dataset.group = gk;
      const promptText = item.prompt || '';
      const promptMatched = Boolean(
        positiveQuery &&
        selectedFields.has('prompts') &&
        normalizeSearchText(promptText).includes(normalizeSearchText(positiveQuery))
      );
      const sessionHref = buildSessionHref(item.link, sessionHashFor(item, q));
      const storyHref = buildSessionHref(item.link, 'story');
      const promptHtml = promptText
        ? (promptMatched ? highlightText(promptText, positiveQuery) : escHtml(promptText))
        : '<em>—</em>';
      tr.innerHTML =
        `<td class="ts">${escHtml(item.ts)}</td>` +
        `<td class="cwd" title="${escHtml(item.cwd)}">${escHtml(item.cwd_display)}</td>` +
        `<td class="model">${escHtml(item.model)}</td>` +
        `<td class="activity" title="user prompts + agent intents">${escHtml(item.activity)}</td>` +
        `<td class="premium-requests num" title="premium requests">${item.premium_requests ? escHtml(String(item.premium_requests)) : ''}</td>` +
        `<td class="story-indicator" title="${item.has_story ? 'Story available' : 'No story'}"><a href="${escHtml(storyHref)}">${item.has_story ? '📖' : ''}</a></td>` +
        `<td class="summary">${item.summary ? escHtml(item.summary) : '<em>-</em>'}</td>` +
        `<td class="prompt"><a href="${escHtml(sessionHref)}">${promptHtml}</a></td>`;
      makeRowClickable(tr, sessionHref);
      frag.appendChild(tr);

      if (q && !promptMatched) {
        const snippet = makePrimarySnippet(item, q, promptMatched, 80);
        if (snippet) {
          const sTr = document.createElement('tr');
          sTr.className = 'snippet-row';
          sTr.innerHTML = `<td colspan="8">${snippet.html}</td>`;
          makeRowClickable(sTr, sessionHref);
          frag.appendChild(sTr);
        }
      }
    }
  });

  document.querySelector('#sessions-table tbody').replaceChildren(frag);
  updateSearchControls();
  updateSearchStatus(filtered.length);

  const modelUsage = document.getElementById('model-usage');
  if (modelUsage) {
    modelUsage.style.display = q ? 'none' : '';
  }

  document.querySelectorAll('#sessions-table th[data-col]').forEach(th => {
    const col = parseInt(th.dataset.col);
    th.classList.toggle('sort-active', col === sortCol);
    th.querySelector('.sort-ind').textContent =
      col !== sortCol ? ' ↕' : sortAsc ? ' ↑' : ' ↓';
  });
}

document.querySelectorAll('#sessions-table th[data-col]').forEach(th => {
  th.addEventListener('click', () => {
    const col = parseInt(th.dataset.col);
    if (col === sortCol) { sortAsc = !sortAsc; }
    else { sortCol = col; sortAsc = col !== 0; }
    render();
  });
});

document.getElementById('search').addEventListener('input', e => {
  query = e.target.value;
  updateSearchHighlight();
  syncSearchUrl(query);
  render();
});
document.getElementById('search').addEventListener('scroll', syncSearchHighlightScroll);

document.querySelectorAll('#search-fields input[data-search-field]').forEach(input => {
  input.addEventListener('change', () => {
    if (input.checked) selectedFields.add(input.dataset.searchField);
    else selectedFields.delete(input.dataset.searchField);
    syncSearchUrl(query);
    render();
  });
});

document.getElementById('btn-select-all').addEventListener('click', () => {
  selectedFields = new Set(SEARCH_FIELDS);
  syncSearchUrl(query);
  render();
});

document.getElementById('btn-select-none').addEventListener('click', () => {
  selectedFields.clear();
  syncSearchUrl(query);
  render();
});

window.addEventListener('popstate', () => {
  loadSearchStateFromUrl();
  document.getElementById('search').value = query;
  updateSearchHighlight();
  render();
});

document.getElementById('btn-expand').addEventListener('click', () => {
  collapsed.clear();
  render();
});

document.getElementById('btn-collapse').addEventListener('click', () => {
  const q = String(query || '').trim();
  DATA.filter(item => matchesQuery(item, q)).forEach(item => {
    const gk = getGroupKey(item, sortCol);
    if (gk !== null) collapsed.add(gk);
  });
  render();
});

loadSearchStateFromUrl();
document.getElementById('search').value = query;
updateSearchHighlight();
render();
