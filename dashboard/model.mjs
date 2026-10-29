export function selectFacts(facts, filters) {
  return facts.filter(row => (!filters.start || row.date >= filters.start)
    && (!filters.end || row.date <= filters.end)
    && (!filters.category || row.category === filters.category)
    && (!filters.country || row.country === filters.country)
    && (!filters.search || `${row.order_id} ${row.line_id} ${row.product_name}`
      .toLowerCase().includes(filters.search.toLowerCase())));
}

export function summarize(facts) {
  const completed = facts.filter(row => row.status === 'completed');
  const orders = new Set(completed.map(row => row.order_id)).size;
  const revenue = facts.reduce((sum, row) => sum + row.net_revenue_cents, 0);
  return { revenue, orders, lines: facts.length, completedLines: completed.length,
    aov: orders ? revenue / orders : 0,
    completion: facts.length ? completed.length / facts.length * 100 : 0 };
}

export function groupRevenue(facts, field) {
  const map = new Map();
  for (const row of facts) {
    const key = row[field];
    map.set(key, (map.get(key) || 0) + row.net_revenue_cents);
  }
  return [...map].map(([label, value]) => ({ label, value }));
}

export function dailyRevenue(facts, start, end) {
  if (!start || !end || start > end) return [];
  const values = new Map(groupRevenue(facts, 'date').map(row => [row.label, row.value]));
  const result = [];
  for (let cursor = new Date(`${start}T00:00:00Z`), stop = new Date(`${end}T00:00:00Z`);
    cursor <= stop; cursor.setUTCDate(cursor.getUTCDate() + 1)) {
    const label = cursor.toISOString().slice(0, 10);
    result.push({ label, value: values.get(label) || 0 });
  }
  return result;
}

export function presetRange(facts, days = 0) {
  const dates = facts.map(row => row.date).sort();
  if (!dates.length) return { start: '', end: '' };
  const end = dates.at(-1);
  const cursor = new Date(`${end}T00:00:00Z`);
  cursor.setUTCDate(cursor.getUTCDate() - Math.max(0, days - 1));
  return { start: days ? (cursor.toISOString().slice(0, 10) < dates[0]
    ? dates[0] : cursor.toISOString().slice(0, 10)) : dates[0], end };
}

export function csv(facts) {
  const columns = ['line_id', 'order_id', 'date', 'country', 'category', 'product_name',
    'status', 'quantity', 'net_revenue_cents', 'revision', 'batch_id'];
  const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  return [columns.join(','), ...facts.map(row => columns.map(key => quote(row[key])).join(','))]
    .join('\r\n');
}
