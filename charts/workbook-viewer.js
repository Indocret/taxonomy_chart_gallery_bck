const params = new URLSearchParams(window.location.search);
const workbookParam = params.get('workbook');
const titleParam = params.get('title') || 'selected sample';
const viewerTitle = document.getElementById('viewerTitle');
const viewerSubtitle = document.getElementById('viewerSubtitle');
const viewerMeta = document.getElementById('viewerMeta');
const sheetTabs = document.getElementById('sheetTabs');
const sheetPanel = document.getElementById('sheetPanel');
const workbookUrl = workbookParam ? new URL(workbookParam, window.location.href).href : '';
let workbook = null;
let activeSheetIndex = 0;

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function columnLabel(index) {
  let label = '';
  let n = index + 1;

  while (n > 0) {
    const remainder = (n - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    n = Math.floor((n - 1) / 26);
  }

  return label;
}

function renderTabs() {
  sheetTabs.innerHTML = '';

  workbook.SheetNames.forEach((name, index) => {
    const button = document.createElement('button');
    button.textContent = name;
    button.className = index === activeSheetIndex ? 'active' : '';
    button.onclick = () => renderSheet(index);
    sheetTabs.appendChild(button);
  });
}

function renderSheet(index) {
  activeSheetIndex = index;
  renderTabs();

  const sheetName = workbook.SheetNames[index];
  const sheet = workbook.Sheets[sheetName];
  const range = XLSX.utils.decode_range(sheet['!ref'] || 'A1:A1');
  const rows = XLSX.utils.sheet_to_json(sheet, {
    header: 1,
    defval: ''
  });

  let html = '<table class="sheet-table"><thead><tr><th class="corner"></th>';

  for (let col = range.s.c; col <= range.e.c; col += 1) {
    html += `<th>${columnLabel(col)}</th>`;
  }

  html += '</tr></thead><tbody>';

  for (let row = range.s.r; row <= range.e.r; row += 1) {
    html += `<tr><th class="row-header">${row + 1}</th>`;

    const rowData = rows[row] || [];
    for (let col = range.s.c; col <= range.e.c; col += 1) {
      const value = rowData[col] ?? '';
      html += `<td>${escapeHtml(value)}</td>`;
    }

    html += '</tr>';
  }

  html += '</tbody></table>';

  sheetPanel.innerHTML = html;
}

async function loadWorkbook() {
  if (!workbookParam) {
    throw new Error('Missing workbook query parameter.');
  }

  const response = await fetch(workbookUrl);

  if (!response.ok) {
    throw new Error(`Could not load workbook (${response.status})`);
  }

  const arrayBuffer = await response.arrayBuffer();
  workbook = XLSX.read(arrayBuffer, { type: 'array' });

  const pageTitle = `Entire taxonomy of ${titleParam}`;
  document.title = pageTitle;
  viewerTitle.textContent = pageTitle;
  viewerSubtitle.textContent = `Workbook file: ${workbookParam}`;
  viewerMeta.textContent = `${workbook.SheetNames.length} sheet${workbook.SheetNames.length === 1 ? '' : 's'} available`;

  renderTabs();
  renderSheet(0);
}

loadWorkbook().catch((error) => {
  sheetTabs.innerHTML = '';
  sheetPanel.innerHTML = `<div class="error">Failed to load workbook: ${escapeHtml(error.message)}</div>`;
  document.title = 'Entire Taxonomy';
  viewerTitle.textContent = 'Entire Taxonomy';
  viewerSubtitle.textContent = 'Unable to load the selected workbook.';
  viewerMeta.textContent = '';
});
