"""Балансовые модели: доступность рабочих мест, насыщенность, локальные центры, дефицит.
Вход: data/districts_input.csv, data/osrm_minutes.csv, data/agglomerations.json.
Выход: outputs/districts_balance.csv."""
import csv, json, math, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
R = list(csv.DictReader(open(ROOT/'data/districts_input.csv', encoding='utf-8')))
for r in R: r['P'] = int(r['population_2024']); r['J'] = int(r['employees_2024']); r['A'] = float(r['area_km2'])
M = list(csv.reader(open(ROOT/'data/osrm_minutes.csv', encoding='utf-8')))
k = M[0][1:]; D = [[float(x) for x in row[1:]] for row in M[1:]]
assert k == [r['oktmo'] for r in R]
n = len(k)
t = [[(D[i][j] + D[j][i]) / 2 for j in range(n)] for i in range(n)]   # симметризованное время, мин
ag = json.load(open(ROOT/'data/agglomerations.json', encoding='utf-8'))
ids = [r['id'] for r in R]
core_idx = {a: ids.index(c) for a, c in ag['cores'].items()}
TAU, T60, NB = 45, 60, 5
rt = sum(r['J'] for r in R) / sum(r['P'] for r in R)
for i, r in enumerate(R):
    r['acc60'] = sum(R[j]['J'] for j in range(n) if t[i][j] <= T60)
    r['accP60'] = sum(R[j]['P'] for j in range(n) if t[i][j] <= T60)
    r['dens'] = (r['P'] + r['J']) / r['A']
    r['rat'] = r['J'] / r['P']
    tc = {a: round(t[i][ci]) for a, ci in core_idx.items()}
    a = min(tc, key=tc.get); r['core'] = a; r['tcore'] = tc[a]
    tt = [(t[i][j] if j != i else 10) for j in range(n)]           # внутрирайонная поездка — 10 мин
    r['g'] = sum(R[j]['J'] * math.exp(-tt[j] / TAU) for j in range(n))
    nn = sorted([j for j in range(n) if j != i], key=lambda j: t[i][j])[:NB]
    r['nbrat5'] = sum(R[j]['J'] for j in nn) / sum(R[j]['P'] for j in nn)
    r['x'] = r['rat'] / r['nbrat5']                                  # >1 — локальный центр
    r['gap'] = max(0, round(rt * r['accP60'] - r['acc60']))          # дефицит мест в часовой доступности
def terc(v):
    s = sorted(v); return s[n // 3], s[2 * n // 3]
g1, g2 = terc([r['g'] for r in R]); d1, d2 = terc([r['dens'] for r in R])
for r in R:
    r['conn'] = 0 if r['g'] < g1 else (1 if r['g'] < g2 else 2)
    r['sat'] = 0 if r['dens'] < d1 else (1 if r['dens'] < d2 else 2)
cols = ['oktmo','id','name','population_2024','employees_2024','area_km2','rat','acc60','accP60','g','dens','nbrat5','x','gap','core','tcore','conn','sat']
(ROOT/'outputs').mkdir(exist_ok=True)
with open(ROOT/'outputs/districts_balance.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(cols)
    for r in R: w.writerow([round(r[c], 4) if isinstance(r[c], float) else r[c] for c in cols])
far = [r for r in R if r['tcore'] > 65]
print(f"RT jobs/pop {rt:.3f}; tertiles g {g1:.0f}/{g2:.0f}, dens {d1:.1f}/{d2:.1f}")
print('local centres (x>=1.2):', [(r['id'], round(r['x'], 2)) for r in sorted(R, key=lambda r: -r['x']) if r['x'] >= 1.2])
deficit = [r for r in far if r['gap'] > 0]
print(f"districts >65 min from a core: {len(far)}, residents {sum(r['P'] for r in far)}")
