/** Reproduce the Laishevo sensitivity scenarios without a browser or network. */
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
export const parameters = JSON.parse(fs.readFileSync(path.join(root, 'data/laishevo_scenarios.json'), 'utf8'));

export function calculate(overrides = {}) {
  const v = { ...parameters.defaults, ...overrides };
  for (const [key, [min, max]] of Object.entries(parameters.ranges)) {
    if (!Number.isFinite(v[key]) || v[key] < min || v[key] > max) throw new RangeError(`Invalid ${key}`);
  }
  if (!Object.hasOwn(parameters.alternatives, v.alt)) throw new RangeError('Unknown alternative');
  if (![70, 100, 130].includes(v.stress)) throw new RangeError('Stress must be 70, 100 or 130 percent');
  const base = parameters.population_reference;
  const share = parameters.alternatives[v.alt].car_share_pct / 100;
  const newResidents = v.units * v.occupied / 100 * v.household;
  const workers = newResidents * v.employed / 100;
  const peak = v.visitors * v.stress / 100;
  const cars = Math.ceil(peak * share / v.carOccupancy);
  const travel = v.walk + v.feeder + v.wait + v.ride + v.last;
  return {
    newResidents, total: base.current_city_population + newResidents, workers,
    outbound: workers * (1 - v.localJobs / 100), local: workers * v.localJobs / 100,
    needed: v.occupied > 0 ? Math.ceil((base.target_city_population - base.current_city_population) / (v.occupied / 100 * v.household)) : null,
    peak, cars, other: peak * (1 - share), travel,
    parkingShortfall: Math.max(0, cars - v.parking), parkingSpare: Math.max(0, v.parking - cars),
    excess: Math.max(0, travel - v.limit), roundTrip: 2 * travel, thresholdMet: travel <= v.limit
  };
}

export function scenarioRows() {
  return Object.keys(parameters.alternatives).flatMap(alt => [70, 100, 130].map(stress => ({
    alternative: alt, stress_pct: stress, ...calculate({ alt, stress })
  })));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const rows = scenarioRows();
  fs.mkdirSync(path.join(root, 'outputs'), { recursive: true });
  const keys = Object.keys(rows[0]);
  const format = value => typeof value === 'number' ? Number(value.toFixed(6)) : value ?? '';
  const csv = [keys.join(','), ...rows.map(row => keys.map(key => format(row[key])).join(','))].join('\n') + '\n';
  fs.writeFileSync(path.join(root, 'outputs/laishevo_scenarios.csv'), csv);
  console.log(JSON.stringify({ default: calculate(), scenarios: rows.length }, null, 2));
}
