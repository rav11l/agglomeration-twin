import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { calculate, parameters, scenarioRows } from '../scripts/laishevo.mjs';

test('default phased scenario: settlement, capacity and complete trip', () => {
  const m = calculate();
  assert.equal(parameters.defaults.alt, 'phased');
  assert.equal(m.newResidents, 3500);
  assert.equal(m.total, 14200);
  assert.equal(m.needed, 3600);
  assert.equal(m.cars, 500);
  assert.equal(m.parkingShortfall, 0);
  assert.equal(m.other, 1500);
  assert.equal(m.travel, 110);
  assert.equal(m.excess, 20);
  assert.equal(m.roundTrip, 220);
});
test('zero occupancy does not invent a finite housing requirement', () => {
  const m = calculate({ occupied: 0 });
  assert.equal(m.newResidents, 0);
  assert.equal(m.total, 10700);
  assert.equal(m.needed, null);
  assert.equal(m.workers, 0);
});
test('jobs add up to employed residents, not all residents', () => {
  const m = calculate({ units: 4000, employed: 50, localJobs: 40 });
  assert.equal(m.newResidents, 7000);
  assert.equal(m.workers, 3500);
  assert.equal(m.local, 1400);
  assert.equal(m.outbound, 2100);
  assert.equal(m.local + m.outbound, m.workers);
});
test('all three alternatives use their own stated car shares', () => {
  for (const [alt, cars, gap] of [['bus', 700, 200], ['phased', 500, 0], ['rail', 350, 0]]) {
    const m = calculate({ alt });
    assert.equal(m.cars, cars);
    assert.equal(m.parkingShortfall, gap);
    assert.equal(m.newResidents, 3500);
  }
});
test('30 percent summer stress changes both car and non-car demand', () => {
  const high = calculate({ stress: 130 });
  assert.equal(high.cars, 650);
  assert.equal(high.parkingShortfall, 150);
  assert.equal(high.other, 1950);
  assert.equal(calculate({ alt: 'bus', stress: 70 }).cars, 490);
});
test('zero visitors and fractional car counts remain physically meaningful', () => {
  const empty = calculate({ visitors: 0, parking: 0 });
  assert.equal(empty.cars, 0);
  assert.equal(empty.other, 0);
  assert.equal(empty.parkingShortfall, 0);
  assert.equal(calculate({ visitors: 100, carOccupancy: 3 }).cars, 17);
});
test('last mile and transfers count; a direct bus can have no feeder leg', () => {
  assert.equal(calculate({ last: 20 }).travel, 120);
  assert.equal(calculate({ wait: 20 }).travel, 115);
  const direct = calculate({ feeder: 0 });
  assert.equal(direct.travel, 80);
  assert.equal(direct.thresholdMet, true);
  assert.equal(direct.excess, 0);
  assert.equal(calculate({ limit: 110 }).thresholdMet, true);
});
test('reject impossible occupancy, zero vehicle capacity and unknown alternatives', () => {
  for (const input of [{ occupied: 101 }, { carOccupancy: 0 }, { household: 0 }, { alt: 'unknown' }, { stress: 0 }, { units: NaN }]) {
    assert.throws(() => calculate(input), RangeError);
  }
});
test('archived browser model and command-line model agree on defaults and edge cases', () => {
  const source = fs.readFileSync(new URL('../site/laishevo-extension.html', import.meta.url), 'utf8');
  const defaultMatch = source.match(/const defaults=(\{[^;]+\});/);
  assert.ok(defaultMatch);
  const browserDefaults = JSON.parse(JSON.stringify(vm.runInNewContext(`(${defaultMatch[1]})`)));
  assert.deepEqual(browserDefaults, parameters.defaults);
  const match = source.match(/function model\(v\)\{[^\n]+\}/);
  assert.ok(match);
  const alternatives = Object.fromEntries(Object.entries(parameters.alternatives).map(([key, value]) => [key, { share: value.car_share_pct }]));
  const browserModel = vm.runInNewContext(`(${match[0]})`, { alternatives });
  const inputs = [{}, { occupied: 0 }, { visitors: 0 }, { feeder: 0 }, { units: 4000 }, ...scenarioRows().map(r => ({ alt: r.alternative, stress: r.stress_pct }))];
  for (const input of inputs) {
    const expected = browserModel({ ...parameters.defaults, ...input });
    const actual = calculate(input);
    for (const key of Object.keys(expected)) {
      if (typeof expected[key] === 'number') assert.ok(Math.abs(actual[key] - expected[key]) < 1e-8, `${key}: ${JSON.stringify(input)}`);
      else assert.equal(actual[key], expected[key]);
    }
  }
});
test('the second-belt classification agrees with the existing twin', () => {
  const belts = JSON.parse(fs.readFileSync(new URL('../data/agglomerations.json', import.meta.url), 'utf8')).aggs;
  assert.ok(belts['Казанская'].ring1.includes('лаишевский'));
  for (const id of ['алексеевский', 'рыбно-слободский', 'спасский']) assert.ok(belts['Казанская'].ring2.includes(id));
  assert.ok(belts['Камская'].ring2.includes('чистопольский'));
  assert.ok(!belts['Казанская'].ring2.includes('чистопольский'));
});
