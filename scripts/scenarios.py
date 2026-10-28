"""Три сценарных расчёта двойника с параметрами по умолчанию со страницы:
ASIF для поездок первого пояса, возврат прироста у второй линии метро, пилотный город."""
import csv, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = json.load(open(ROOT/'data/scenario_params.json', encoding='utf-8'))
FL = {r['district_id']: (int(r['flow_now']), int(r['flow_planned'])) for r in csv.DictReader(open(ROOT/'data/flows_mayor_scheme.csv', encoding='utf-8'))}
# 1. ASIF: тыс. т CO2 в год
a = P['asif']
def em(i, cs): return sum(FL[k][i] * 2 * a['km'][k] * a['working_days'] * (cs / a['occupancy'] * a['car_kg_per_km'] + (1 - cs) * a['pt_kg_per_pkm']) for k in FL) / 1e6
c, sh = a['car_share_default'], a['shift_pp_default'] / 100
now, plan, plan_s = em(0, c), em(1, c), em(1, max(0, c - sh))
print(f"ASIF: now {now:.0f}k t, plan {plan:.0f}k t, plan with shift {plan_s:.0f}k t ({(plan_s - plan) / plan * 100:.0f}%)")
# 2. Возврат прироста у второй линии метро
u = P['uplift']; A = {}
for r in csv.DictReader(open(ROOT/'data/nspd_line2_cadastre_aggregates.csv', encoding='utf-8')):
    A[(r['object'], r['class'])] = A.get((r['object'], r['class']), 0) + float(r['cadastral_value_rub']) / 1e9
res = (A[('building', 'mkd')], A[('land', 'mkd')]); biz = (A[('building', 'comm')], A[('land', 'comm')], A[('land', 'garage')])
p, lag, rt = u['premium_point'], u['lag_years_default'], u['rates']
tax = (res[0] * rt['flat'] + res[1] * rt['land_housing'] + biz[0] * rt['commercial_building'] + (biz[1] + biz[2]) * rt['other_land']) * p * 1000
yrs = max(0, u['end'] - (u['open'] + lag)); bud = tax * yrs / 1000
nb = u['new_builds']; dev = nb['flats'] * nb['m2_per_flat'] * nb['rub_per_m2'] * (1 - 1 / (1 + p)) / 1e9
print(f"Uplift: taxes {tax:.0f} mn/yr, {bud:.2f} bn by {u['end']} = {bud / u['cost_bn'] * 100:.1f}% of {u['cost_bn']} bn; developers {dev:.1f} bn; owners {sum(res) * p:.1f} bn; commercial {sum(biz) * p:.1f} bn")
print(f"  inputs: MKD buildings {res[0]:.2f}, MKD land {res[1]:.2f}, commercial buildings {biz[0]:.2f}, commercial land {biz[1]:.2f}, garage land {biz[2]:.2f} bn")
# 3. Пилотный город
e = P['pilot_city']; pk, loc = e['residents_k_default'], e['local_jobs_share_default'] / 100
emp = pk * e['employment_rate']; jobs = emp * loc; com = emp - jobs; tr = com * e['peak_share'] / e['people_per_train'] * 1000
z = FL['зеленодольский']
print(f"Pilot city {pk}k: {pk / e['plan_growth_k'] * 100:.0f}% of planned growth; local jobs {jobs:.0f}k; commuters {com:.0f}k; peak trains {tr:.0f}; Zelenodolsky flow {z[1]} -> {z[1] + com * 1000:.0f}")
