const DATA = __DATA__;
let sortCol = 0;   // 0=ts, 1=cwd, 2=model, 3=activity, 4=premium, 5=story, 6=prompt
let sortAsc = false;
let query = '';
const collapsed = new Set();

function getGroupKey(item, col) {
  if (col === 0) return item.ts.slice(0, 10);       // YYYY-MM-DD
  if (col === 1) return item.cwd || '(none)';
  if (col === 2) return item.model || '(unknown)';
  if (col === 3) return String(item.activity_total);
  if (col === 4) return String(item.premium_requests || 0);
  if (col === 5) return item.has_story ? 'yes' : 'no';
  const words = (item.prompt || '').trim().split(/\\s+/);
  return words.slice(0, 6).join(' ') + (words.length > 6 ? '…' : '') || '(empty)';
}

function getSortVal(item, col) {
  if (col === 0) return item.ts_raw;
  if (col === 1) return (item.cwd || '').toLowerCase();
  if (col === 2) return (item.model || '').toLowerCase();
  if (col === 3) return item.activity_total;
  if (col === 4) return item.premium_requests || 0;
  if (col === 5) return item.has_story ? 1 : 0;
  if (col === 6) return (item.prompt || '').toLowerCase();
  return '';
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function makeSnippet(text, q, maxLen = 140) {
  if (!q || !text) return '';
  const t = String(text);
  const tl = t.toLowerCase();
  const tokens = q.trim().split(/\\s+/).filter(Boolean);
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
  const tokens = q.trim().split(/\\s+/).filter(Boolean);
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

function buildSessionHref(path, hash) {
  const url = new URL(`file://${path}`);
  if (query) url.searchParams.set('q', query);
  if (hash) url.hash = hash;
  return url.toString();
}

function syncSearchUrl(value) {
  const url = new URL(window.location.href);
  if (value) url.searchParams.set('q', value);
  else url.searchParams.delete('q');
  history.replaceState(null, '', url);
}

function loadSearchFromUrl() {
  const url = new URL(window.location.href);
  return url.searchParams.get('q') || '';
}

function toggleGroup(gk) {
  if (collapsed.has(gk)) collapsed.delete(gk); else collapsed.add(gk);
  render();
}

function render() {
  const q = query.toLowerCase();
  const filtered = DATA.filter(item =>
    !q ||
    item.ts.includes(q) ||
    (item.cwd    || '').toLowerCase().includes(q) ||
    (item.model  || '').toLowerCase().includes(q) ||
    (item.prompt || '').toLowerCase().includes(q) ||
    (item.search || '').toLowerCase().includes(q)
  );

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
        `<td colspan="7">` +
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
      const promptMatched = q && promptText.toLowerCase().includes(q);
      const sessionHref = buildSessionHref(item.link, 'turns');
      const storyHref = buildSessionHref(item.link, 'story');
      const promptHtml = promptText ? (promptMatched ? highlightText(promptText, q) : escHtml(promptText)) : '<em>\u2014</em>';
      tr.innerHTML =
        `<td class="ts">${escHtml(item.ts)}</td>` +
        `<td class="cwd" title="${escHtml(item.cwd)}">${escHtml(item.cwd_display)}</td>` +
        `<td class="model">${escHtml(item.model)}</td>` +
        `<td class="activity" title="user prompts + agent intents">${escHtml(item.activity)}</td>` +
        `<td class="premium-requests num" title="premium requests">${item.premium_requests ? escHtml(String(item.premium_requests)) : ''}</td>` +
        `<td class="story-indicator" title="${item.has_story ? 'Story available' : 'No story'}"><a href="${escHtml(storyHref)}">${item.has_story ? '📖' : ''}</a></td>` +
        `<td class="prompt"><a href="${escHtml(sessionHref)}">${promptHtml}</a></td>`;
      makeRowClickable(tr, sessionHref);
      frag.appendChild(tr);

      if (q && !promptMatched) {
        let snippet = makeSnippet(item.search || '', q, 160) ||
                      makeSnippet(item.prompt || '', q, 120) ||
                      makeSnippet(item.cwd || '', q, 80) ||
                      makeSnippet(item.model || '', q, 80) ||
                      '';
        if (snippet) {
          const sTr = document.createElement('tr');
          sTr.className = 'snippet-row';
          sTr.innerHTML = `<td colspan="7">${snippet}</td>`;
          makeRowClickable(sTr, sessionHref);
          frag.appendChild(sTr);
        }
      }
    }
  });

  document.querySelector('#sessions-table tbody').replaceChildren(frag);

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
  syncSearchUrl(query);
  render();
});

window.addEventListener('popstate', () => {
  query = loadSearchFromUrl();
  document.getElementById('search').value = query;
  render();
});

document.getElementById('btn-expand').addEventListener('click', () => {
  collapsed.clear();
  render();
});

document.getElementById('btn-collapse').addEventListener('click', () => {
  const q = query.toLowerCase();
  DATA.filter(item =>
    !q ||
    item.ts.includes(q) ||
    (item.cwd    || '').toLowerCase().includes(q) ||
    (item.model  || '').toLowerCase().includes(q) ||
    (item.prompt || '').toLowerCase().includes(q) ||
    (item.search || '').toLowerCase().includes(q)
  ).forEach(item => {
    const gk = getGroupKey(item, sortCol);
    if (gk !== null) collapsed.add(gk);
  });
  render();
});

query = loadSearchFromUrl();
document.getElementById('search').value = query;
render();
