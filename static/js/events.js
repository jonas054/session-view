function showTab(name, pushState) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelector('[data-tab="' + name + '"]').classList.add('active');
  document.getElementById('panel-' + name).classList.add('active');
  if (pushState !== false) location.hash = name;
}

function applyHash() {
  const name = location.hash.slice(1);
  if (name && document.querySelector('[data-tab="' + name + '"]')) showTab(name, false);
}

window.addEventListener('hashchange', applyHash);
applyHash();

function goToRaw(id) {
  showTab('raw', false);
  const el = document.getElementById(id);
  if (!el) return;
  el.open = true;
  el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  el.classList.add('raw-highlight');
  setTimeout(() => el.classList.remove('raw-highlight'), 2000);
}

function copyCmd(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const prev = btn.textContent;
    btn.textContent = '✓';
    btn.classList.add('copy-btn-ok');
    setTimeout(() => { btn.textContent = prev; btn.classList.remove('copy-btn-ok'); }, 1500);
  });
}

function getSearchQuery() {
  return new URL(window.location.href).searchParams.get('q') || '';
}

function getSearchFields() {
  return parseSearchFields(new URL(window.location.href));
}

function updateBackLink(query) {
  const backLink = document.querySelector('.back-link');
  if (!backLink) return;
  const url = new URL(backLink.href);
  if (query) url.searchParams.set('q', query);
  else url.searchParams.delete('q');

  const fields = getSearchFields();
  if (fields === null || fields.size === SEARCH_FIELDS.length) {
    url.searchParams.delete('match');
  } else {
    url.searchParams.set('match', searchFieldsParam(fields));
  }
  backLink.href = url.toString();
}

function closestSearchField(node) {
  let element = node.parentElement;
  while (element) {
    if (element.dataset && element.dataset.searchField) {
      return element.dataset.searchField;
    }
    element = element.parentElement;
  }
  return '';
}

function canHighlightNode(node, fields) {
  if (fields === null || fields.size === SEARCH_FIELDS.length) return true;
  const field = closestSearchField(node);
  return field ? fields.has(field) : false;
}

function highlightSearchInNode(root, query, fields) {
  const tokens = query.trim().split(/\s+/).filter(Boolean);
  if (!tokens.length || !root || (fields && !fields.size)) return 0;

  const re = new RegExp('(' + tokens.map(escapeRegExp).join('|') + ')', 'gi');
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (parent.closest('mark.search-hit')) return NodeFilter.FILTER_REJECT;
      if (['SCRIPT', 'STYLE', 'MARK'].includes(parent.tagName)) return NodeFilter.FILTER_REJECT;
      if (!canHighlightNode(node, fields)) return NodeFilter.FILTER_REJECT;
      re.lastIndex = 0;
      return re.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }
  });

  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);

  let hitCount = 0;
  for (const node of nodes) {
    const text = node.nodeValue;
    const parent = node.parentNode;
    if (!parent) continue;
    re.lastIndex = 0;
    const parts = text.split(re);
    if (parts.length === 1) continue;

    const frag = document.createDocumentFragment();
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (!part) continue;
      if (i % 2 === 1) {
        const mark = document.createElement('mark');
        mark.className = 'search-hit';
        mark.textContent = part;
        frag.appendChild(mark);
        hitCount += 1;
      } else {
        frag.appendChild(document.createTextNode(part));
      }
    }
    parent.replaceChild(frag, node);

    let details = parent.nodeType === Node.ELEMENT_NODE ? parent.closest('details') : null;
    while (details) {
      details.open = true;
      details = details.parentElement ? details.parentElement.closest('details') : null;
    }
  }

  return hitCount;
}

function applySearchQueryToTurns() {
  const query = getSearchQuery();
  updateBackLink(query);
  if (!query) return;

  const highlightQuery = parseSearchQuery(query).positive;
  if (!highlightQuery) return;

  const fields = getSearchFields();
  if (fields && !fields.size) return;

  const overviewPanel = document.getElementById('panel-overview');
  const turnsPanel = document.getElementById('panel-turns');
  const storyPanel = document.getElementById('panel-story');
  const overviewHits = highlightSearchInNode(overviewPanel, highlightQuery, fields);
  const turnHits = highlightSearchInNode(turnsPanel, highlightQuery, fields);
  const storyHits = highlightSearchInNode(storyPanel, highlightQuery, fields);

  if (storyHits > 0 && turnHits === 0) {
    showTab('story', false);
    const firstHit = storyPanel.querySelector('mark.search-hit');
    if (firstHit) firstHit.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (turnHits > 0) {
    showTab('turns', false);
    const firstHit = turnsPanel.querySelector('mark.search-hit');
    if (firstHit) firstHit.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else if (overviewHits > 0) {
    showTab('overview', false);
    const firstHit = overviewPanel.querySelector('mark.search-hit');
    if (firstHit) firstHit.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

applySearchQueryToTurns();
