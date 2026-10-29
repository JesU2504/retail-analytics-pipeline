import { selectFacts, summarize, groupRevenue, dailyRevenue, presetRange, csv } from './model.mjs';

const $ = id => document.getElementById(id);
const money = cents => new Intl.NumberFormat('en-IE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(cents / 100);
const count = n => new Intl.NumberFormat('en-IE').format(n);
const escape = text => String(text).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
let snapshot;
let view = 'overview';
let page = 0;
let sort = 'date';
let direction = -1;
let request = 0;
const pageSize = 15;

function filters() {
  return { start: $('start').value, end: $('end').value, category: $('category').value,
    country: $('country').value, search: view === 'orders' ? $('search').value : '' };
}

function trend(rows, start, end) {
  const points = dailyRevenue(rows, start, end);
  if (!rows.length || !points.length) return '<div class="chart-empty">No sales match these filters.<br>Try a wider date range or reset filters.</div>';
  const w = 640, h = 235, left = 56, right = 20, top = 20, bottom = 34;
  const max = Math.max(...points.map(p => p.value), 100);
  const scale = Math.ceil(max / 10000) * 10000;
  const x = i => left + (points.length === 1 ? .5 : i / (points.length - 1)) * (w - left - right);
  const y = value => h - bottom - value / scale * (h - top - bottom);
  const path = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(2)},${y(p.value).toFixed(2)}`).join(' ');
  const grid = Array.from({ length: 5 }, (_, i) => {
    const value = scale * i / 4;
    return `<line x1="${left}" x2="${w - right}" y1="${y(value)}" y2="${y(value)}" stroke="#edf1f7"/><text x="${left - 11}" y="${y(value) + 3}" text-anchor="end" font-size="9" fill="#95a0b1">€${(value / 100).toLocaleString('en-IE', { maximumFractionDigits: 0 })}</text>`;
  }).join('');
  const tickCount = Math.min(points.length, 6);
  const ticks = [...new Set(Array.from({ length: tickCount }, (_, i) => Math.round(i / Math.max(1, tickCount - 1) * (points.length - 1))))];
  const labels = ticks.map(i => `<text x="${x(i)}" y="${h - 8}" text-anchor="middle" font-size="9" fill="#95a0b1">${new Date(points[i].label + 'T00:00:00Z').toLocaleDateString('en-IE', { day: 'numeric', month: 'short', timeZone: 'UTC' })}</text>`).join('');
  return `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="Daily net revenue from ${escape(start)} to ${escape(end)}. Total ${escape(money(summarize(rows).revenue))}."><defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#567bea" stop-opacity=".2"/><stop offset="1" stop-color="#567bea" stop-opacity=".01"/></linearGradient></defs>${grid}<path d="${path} L${x(points.length - 1)},${h - bottom} L${x(0)},${h - bottom} Z" fill="url(#area)"/><path d="${path}" fill="none" stroke="#426be2" stroke-width="2" stroke-linejoin="round"/>${points.length < 8 ? points.map((p, i) => `<circle cx="${x(i)}" cy="${y(p.value)}" r="3" fill="#426be2"><title>${p.label}: ${escape(money(p.value))}</title></circle>`).join('') : ''}${labels}</svg>`;
}

function render() {
  if (!snapshot) return;
  const f = filters();
  const invalid = f.start && f.end && f.start > f.end;
  $('date-error').hidden = !invalid;
  const rows = invalid ? [] : selectFacts(snapshot.facts, f);
  const stats = summarize(rows);
  $('filter-summary').textContent = `${count(rows.length)} of ${count(snapshot.facts.length)} order lines · EUR`;
  $('revenue').textContent = money(stats.revenue);
  $('orders').textContent = count(stats.orders);
  $('order-note').textContent = `${count(stats.lines)} current order lines selected`;
  $('aov').textContent = stats.orders ? money(stats.aov) : '—';
  $('completion').textContent = stats.lines ? `${stats.completion.toFixed(1)}%` : '—';
  $('completion-note').textContent = `${count(stats.completedLines)} completed / ${count(stats.lines)} selected lines`;
  const fullRange = presetRange(snapshot.facts);
  $('trend').innerHTML = trend(rows, f.start || fullRange.start, f.end || fullRange.end);
  const colors = ['#4169df', '#6387e7', '#7e9cec', '#99b0ee', '#b1c2f2', '#c9d4f4'];
  $('categories').innerHTML = groupRevenue(rows, 'category').sort((a, b) => b.value - a.value).map((r, i) => `<div class="category-row"><div class="category-label"><span>${escape(r.label)}</span><strong>${escape(money(r.value))}</strong></div><div class="bar-track" role="img" aria-label="${escape(r.label)}: ${stats.revenue ? (r.value / stats.revenue * 100).toFixed(1) : 0}% of revenue"><div class="bar-fill" style="width:${stats.revenue ? r.value / stats.revenue * 100 : 0}%;background:${colors[i % colors.length]}"></div></div></div>`).join('') || '<div class="chart-empty">No categories in this selection.</div>';
  $('markets').innerHTML = groupRevenue(rows, 'country').sort((a, b) => b.value - a.value).map(r => `<tr><td><span class="country-dot"></span>${escape(r.label)}</td><td>${escape(money(r.value))}</td><td>${count(summarize(rows.filter(row => row.country === r.label)).orders)}</td><td>${stats.revenue ? (r.value / stats.revenue * 100).toFixed(1) : '0'}%</td></tr>`).join('') || '<tr><td colspan="4">No markets match these filters.</td></tr>';
  const ordered = [...rows].sort((a, b) => (sort === 'date' ? a.date.localeCompare(b.date) : a.net_revenue_cents - b.net_revenue_cents) * direction || a.line_id.localeCompare(b.line_id));
  const pages = Math.max(1, Math.ceil(ordered.length / pageSize));
  page = Math.min(page, pages - 1);
  $('order-rows').innerHTML = ordered.slice(page * pageSize, (page + 1) * pageSize).map(r => `<tr><td>${escape(r.line_id)}<span class="order-id">${escape(r.order_id)}</span></td><td>${escape(r.date)}</td><td>${escape(r.product_name)}</td><td>${escape(r.country)}</td><td><span class="status ${r.status === 'cancelled' ? 'cancelled' : ''}">${escape(r.status)}</span></td><td>${escape(money(r.net_revenue_cents))}</td><td>v${r.revision}</td></tr>`).join('') || '<tr><td colspan="7">No order lines match these filters.</td></tr>';
  $('page-info').textContent = ordered.length ? `${page * pageSize + 1}–${Math.min((page + 1) * pageSize, ordered.length)} of ${count(ordered.length)} lines` : '0 order lines';
  $('previous').disabled = page === 0;
  $('next').disabled = page >= pages - 1;
  $('quality-count').textContent = `${snapshot.quality.length} / ${snapshot.quality.length} passed`;
  $('quality-meta').textContent = `Full snapshot · ${snapshot.quality.length} checks · independent of active filters`;
  $('quality-checks').innerHTML = snapshot.quality.map(check => `<li><span aria-hidden="true">✓</span>${escape(check.name.replaceAll('_', ' '))}</li>`).join('');
  $('batch-audit').innerHTML = snapshot.batches.map(batch => `<div class="batch"><strong>Batch ${batch.id.toString().padStart(2, '0')}</strong><p>${count(batch.changed_lines)} changed lines committed</p><p>${escape(batch.loaded_at)} · database time</p></div>`).join('');
  $('snapshot-info').textContent = `Exported ${new Date(snapshot.generated_at).toLocaleDateString('en-IE', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })} · ${snapshot.facts.length} synthetic lines · ${snapshot.batches.length} batches`;
}

function reset() {
  const range = presetRange(snapshot.facts);
  $('start').value = range.start;
  $('end').value = range.end;
  for (const id of ['category', 'country', 'search']) $(id).value = '';
  page = 0;
  document.querySelectorAll('[data-days]').forEach(button => button.classList.toggle('selected', button.dataset.days === '0'));
  render();
}

async function loadDataset() {
  const ticket = ++request;
  $('loading').hidden = false;
  $('content').hidden = true;
  $('error').hidden = true;
  $('download').disabled = true;
  try {
    const response = await fetch(`${$('dataset').value}.json`);
    if (!response.ok) throw new Error('Snapshot unavailable');
    const data = await response.json();
    if (ticket !== request) return;
    if (data.schema_version !== 1 || !data.synthetic || !Array.isArray(data.facts)
      || !data.quality?.length || data.quality.some(check => check.status !== 'pass')) throw new Error('Invalid snapshot');
    snapshot = data;
    for (const field of ['category', 'country']) {
      const values = [...new Set(snapshot.facts.map(row => row[field]))].sort();
      $(field).innerHTML = `<option value="">All ${field === 'category' ? 'categories' : 'countries'}</option>` + values.map(value => `<option value="${escape(value)}">${escape(value)}</option>`).join('');
    }
    const range = presetRange(snapshot.facts);
    for (const id of ['start', 'end']) { $(id).min = range.start; $(id).max = range.end; }
    reset();
    $('content').hidden = false;
  } catch {
    if (ticket !== request) return;
    snapshot = null;
    $('error').textContent = 'The warehouse snapshot could not be loaded. Please refresh the page.';
    $('error').hidden = false;
  } finally { if (ticket === request) { $('loading').hidden = true; $('download').disabled = !snapshot; } }
}

function changeView(nextView) {
  view = ['overview', 'orders', 'pipeline'].includes(nextView) ? nextView : 'overview';
  const headings = { overview: ['Retail performance', 'From validated source batches to business insights.'], orders: ['Order explorer', 'Inspect the records behind every metric.'], pipeline: ['Pipeline & data quality', 'Trace the journey from source batches to trusted reporting.'] };
  [$('page-title').textContent, $('page-description').textContent] = headings[view];
  for (const name of Object.keys(headings)) $(`${name}-view`).hidden = name !== view;
  document.querySelectorAll('nav [data-view]').forEach(button => {
    button.classList.toggle('active', button.dataset.view === view);
    if (button.dataset.view === view) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
  $('download').hidden = view === 'pipeline';
  page = 0;
  render();
}

document.querySelectorAll('[data-view]').forEach(button => button.addEventListener('click', () => changeView(button.dataset.view)));
document.querySelector('.brand').addEventListener('click', () => changeView('overview'));
$('dataset').addEventListener('change', loadDataset);
for (const field of ['start', 'end', 'category', 'country', 'search']) $(field).addEventListener(field === 'search' ? 'input' : 'change', () => { page = 0; if (['start', 'end'].includes(field)) document.querySelectorAll('[data-days]').forEach(b => b.classList.remove('selected')); render(); });
$('reset').addEventListener('click', reset);
document.querySelectorAll('[data-days]').forEach(button => button.addEventListener('click', () => {
  const range = presetRange(snapshot.facts, Number(button.dataset.days));
  $('start').value = range.start; $('end').value = range.end; page = 0;
  document.querySelectorAll('[data-days]').forEach(b => b.classList.toggle('selected', b === button)); render();
}));
$('previous').addEventListener('click', () => { page--; render(); });
$('next').addEventListener('click', () => { page++; render(); });
for (const field of ['date', 'revenue']) $(`sort-${field}`).addEventListener('click', () => { direction = sort === field ? -direction : -1; sort = field; page = 0; render(); });
$('download').addEventListener('click', () => {
  if (!snapshot) return;
  const blob = new Blob([csv(selectFacts(snapshot.facts, filters()))], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = `retail-${$('dataset').value}-filtered.csv`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
});
loadDataset();
