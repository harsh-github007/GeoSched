import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { cop, cooling, parseCSV, week, jobCost } from '../assets/geo.js';

const temp = parseCSV(readFileSync('data/weekly_temp_f.csv', 'utf8'));
const price = parseCSV(readFileSync('data/weekly_price_usd_mwh.csv', 'utf8'));

test('cooling matches Table V and the COP formula', () => {
  assert.equal(cooling(20).overhead.toFixed(2), '0.05');
  assert.equal(cooling(62).overhead.toFixed(2), '0.17');
  assert.equal(cooling(80).overhead, 1 / cop(20));
});

test('53 weeks of data for all five sites', () => {
  for (const dc of ['Iowa', 'Oregon', 'Singapore', 'Chile', 'Finland']) { assert.equal(temp[dc].length, 53); assert.equal(price[dc].length, 53); }
});

test('Singapore is the most expensive site every week', () => {
  for (let w = 0; w < 53; w++) {
    const rows = week(temp, price, w);
    assert.equal(rows.reduce((a, b) => (b.effective > a.effective ? b : a)).dc, 'Singapore');
  }
});

test('job cost scales with hours', () => {
  const r = week(temp, price, 0), a = jobCost(r, 64, 0.5, 1), b = jobCost(r, 64, 0.5, 2);
  assert.ok(Math.abs(b[0].cost - 2 * a[0].cost) < 1e-12);
});

test('incremental cost excludes idle power and has correct MWh units', () => {
  const profile=[{dc:'example',effective:105,overhead:.05}];
  assert.equal(jobCost(profile,64,0,1)[0].cost,0);
  assert.ok(Math.abs(jobCost(profile,64,1,1)[0].cost-.084)<1e-12);
});
