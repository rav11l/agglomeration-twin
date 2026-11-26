/* Pure calculation and filter checks; no browser or network is used. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'site/tatarstan_twin_2026-11-26.html'), 'utf8');
const data = JSON.parse(html.match(/<script type="application\/json" id="twin-data">([\s\S]*?)<\/script>/)[1]);
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/\ninit\(\);\s*$/, '');
const box = {document: {getElementById: () => ({textContent: JSON.stringify(data)})}};
vm.createContext(box);
vm.runInContext(script + `
const populationAllocation=populationPlan(),equalAllocation=equalizePlan();
const base=computeModel(45,Array(N).fill(0));
const byMunicipality=computeModel(45,populationAllocation);
const byEqual=computeModel(45,equalAllocation);
const scopes={};for(const name of ['all','Казанская','Камская','Альметьевская','outside']){
 scope=name;scopes[name]=visibleIndices().length;
}
scope='all';
const original=potential(0);penalty=30;const delayed=potential(0);
globalThis.result={populationAllocation,equalAllocation,scopes,original,delayed,
 baseline:base.access,popMean:byMunicipality.mean,equalMin:byEqual.min,
 popWeightedMass:byMunicipality.gain.reduce((s,g,i)=>s+g*base.access[i]*D.profiles[i].population,0)};
`, box);
const r = JSON.parse(JSON.stringify(box.result));
assert.equal(r.populationAllocation.length, 45);
assert.equal(r.populationAllocation.reduce((a,b)=>a+b,0), 1000);
assert.equal(r.equalAllocation.reduce((a,b)=>a+b,0), 1000);
assert.ok(r.populationAllocation.every(v=>Number.isInteger(v)&&v>=0));
assert.ok(r.equalAllocation.every(v=>Number.isInteger(v)&&v>=0));
assert.deepEqual(r.scopes, {all:45,'Казанская':15,'Камская':18,'Альметьевская':9,outside:7});
assert.ok(r.delayed<=r.original);
assert.ok(r.popMean>0 && r.equalMin>0);
assert.ok(Math.abs(r.popWeightedMass-1000)<1e-7);
data.profiles.forEach((p,i)=>assert.ok(Math.abs(p.access-r.baseline[i])<1e-12));
assert.ok(!html.includes('__TWIN_DATA__')&&!html.includes('__TWIN_CSS__'));
assert.ok(!/<script[^>]+src=|<link[^>]+rel="stylesheet"/.test(html));
const summary={profiles:45,scopes:r.scopes,scenario_population_total:1000,
 scenario_equalize_total:1000,scenario_mass_error:Math.abs(r.popWeightedMass-1000),
 baseline_max_error:Math.max(...data.profiles.map((p,i)=>Math.abs(p.access-r.baseline[i]))),
 delayed_access_not_increased:r.delayed<=r.original,offline:true,browser_checked:false};
fs.writeFileSync(path.join(root,'outputs/republic/ui_math_validation.json'),JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary,null,2));
