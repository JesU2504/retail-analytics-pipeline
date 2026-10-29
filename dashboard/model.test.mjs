import test from 'node:test';
import assert from 'node:assert/strict';
import { selectFacts, summarize, groupRevenue, dailyRevenue, presetRange, csv } from './model.mjs';

const facts = [
  { line_id: 'L1', order_id: 'O1', date: '2026-10-01', country: 'Ireland', category: 'Audio', product_name: 'Mic', status: 'completed', quantity: 1, net_revenue_cents: 9000 },
  { line_id: 'L2', order_id: 'O1', date: '2026-10-01', country: 'Ireland', category: 'Displays', product_name: 'Monitor', status: 'completed', quantity: 1, net_revenue_cents: 18000 },
  { line_id: 'L3', order_id: 'O2', date: '2026-10-03', country: 'Japan', category: 'Displays', product_name: 'Monitor', status: 'cancelled', quantity: 1, net_revenue_cents: 0 },
];

test('date boundaries are inclusive and filters combine', () => {
  assert.deepEqual(selectFacts(facts, { start: '2026-10-01', end: '2026-10-01', category: 'Audio', country: 'Ireland' }), [facts[0]]);
  assert.equal(selectFacts(facts, { country: 'Germany' }).length, 0);
});
test('orders are distinct and cancellations do not inflate revenue or AOV', () => {
  assert.deepEqual(summarize(facts), { revenue: 27000, orders: 1, lines: 3, completedLines: 2, aov: 27000, completion: 2 / 3 * 100 });
});
test('empty and cancelled-only selections avoid division by zero', () => {
  assert.equal(summarize([]).aov, 0);
  assert.equal(summarize([facts[2]]).completion, 0);
  assert.equal(summarize([facts[2]]).orders, 0);
});
test('daily trend includes zero-sale dates and reconciles to selected facts', () => {
  const daily = dailyRevenue(facts, '2026-10-01', '2026-10-03');
  assert.deepEqual(daily.map(r => r.value), [27000, 0, 0]);
  assert.equal(daily.reduce((sum, r) => sum + r.value, 0), summarize(facts).revenue);
});
test('category groups reconcile to the total', () => {
  assert.deepEqual(groupRevenue(facts, 'category'), [{ label: 'Audio', value: 9000 }, { label: 'Displays', value: 18000 }]);
});
test('date presets use the latest data date, independent of today', () => {
  assert.deepEqual(presetRange(facts, 2), { start: '2026-10-02', end: '2026-10-03' });
  assert.deepEqual(presetRange(facts), { start: '2026-10-01', end: '2026-10-03' });
  assert.deepEqual(presetRange([]), { start: '', end: '' });
});
test('search matches product and source IDs without case sensitivity', () => {
  assert.equal(selectFacts(facts, { search: 'MONITOR' }).length, 2);
  assert.deepEqual(selectFacts(facts, { search: 'l1' }), [facts[0]]);
});
test('CSV preserves cents and escapes quotes and commas', () => {
  const result = csv([{ ...facts[0], product_name: 'Mic, "Studio"' }]);
  assert.ok(result.includes('"Mic, ""Studio"""'));
  assert.ok(result.includes('"9000"'));
  assert.equal(csv([]).split('\r\n').length, 1);
});
