"""Десять опорных кластеров периферии: жадное покрытие районов дальше 65 мин от ядер агломераций
районами-опорами в радиусе 50 мин. Вход: outputs/districts_balance.csv (после balance.py)."""
import csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
R = list(csv.DictReader(open(ROOT/'outputs/districts_balance.csv', encoding='utf-8')))
M = list(csv.reader(open(ROOT/'data/osrm_minutes.csv', encoding='utf-8')))
D = [[float(x) for x in row[1:]] for row in M[1:]]; n = len(D)
t = [[(D[i][j] + D[j][i]) / 2 for j in range(n)] for i in range(n)]
idx = {r['id']: i for i, r in enumerate(R)}; P = {r['id']: int(r['population_2024']) for r in R}
FAR, RADIUS, K = 65, 50, 10
far = [r['id'] for r in R if int(r['tcore']) > FAR]
unc = set(far); out = []
for _ in range(K):
    best = None
    for h in far:
        if h not in unc: continue
        m = sorted(x for x in unc if x != h and t[idx[h]][idx[x]] <= RADIUS)
        p = P[h] + sum(P[x] for x in m)
        if best is None or p > best[0]: best = (p, h, m)
    p, h, m = best; out.append((h, m, p)); unc -= {h, *m}
with open(ROOT/'outputs/clusters.csv', 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['hub', 'members', 'population'])
    for h, m, p in out: w.writerow([h, ';'.join(m), p])
print(f"periphery {len(far)} districts, {sum(P[x] for x in far)} residents; covered {sum(o[2] for o in out)}; uncovered {sorted(unc)}")
