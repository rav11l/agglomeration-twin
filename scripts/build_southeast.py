"""Build a self-contained preview from pinned, attributable public-data extracts.

python scripts/build_southeast.py
No network is used. Vacancy collection is a separate, explicitly audited input.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'southeast'
OUT = ROOT / 'outputs' / 'southeast'
CENTERS = [
    ('92608000', 'Альметьевск', 'альметьевский', ('альметьев',)),
    ('92602000', 'Азнакаево', 'азнакаевский', ('азнакаев',)),
    ('92617000', 'Бугульма', 'бугульминский', ('бугульм',)),
    ('92636000', 'Лениногорск', 'лениногорский', ('лениногор',)),
    ('92614000', 'Бавлы', 'бавлинский', ('бавлы', 'бавлин')),
    ('92654000', 'Уруссу', 'ютазинский', ('уруссу', 'ютазин')),
]


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def locality(address):
    """Match workplace addresses, never a title or employer registration address."""
    s = (address or '').lower().replace('ё', 'е')
    matches = [i for i, (_, _, _, stems) in enumerate(CENTERS)
               if any(stem in s for stem in stems)]
    return matches[0] if len(matches) == 1 else None


def model(rows, times, tau=45, intrazonal=10):
    p = [r['population'] for r in rows]
    jobs = [r['employees'] for r in rows]
    n = len(rows)
    w = [[math.exp(-(intrazonal if i == j else
                    (times[i][j] + times[j][i]) / 2) / tau)
          for j in range(n)] for i in range(n)]
    demand = [sum(p[k] * w[k][j] for k in range(n)) for j in range(n)]
    access = [sum(jobs[j] * w[i][j] / demand[j] for j in range(n))
              for i in range(n)]
    # Conservation is a property of the allocation, not evidence of observed trips.
    error = abs(sum(p[i] * access[i] for i in range(n)) - sum(jobs))
    if error > 1e-7:
        raise ValueError(f'Allocation conservation failed: {error}')
    return w, demand, access, error


def summarize_vacancies(snapshot):
    records = snapshot.get('records', [])
    seen = set()
    groups = [[] for _ in CENTERS]
    rejected = {'duplicate': 0, 'unmatched': 0, 'multilocality': 0}
    for v in records:
        key = v['id']
        if key in seen:
            rejected['duplicate'] += 1
            continue
        seen.add(key)
        addresses = v.get('addresses', [])
        matched = {locality(a.get('location', '')) for a in addresses}
        matched.discard(None)
        if not matched:
            rejected['unmatched'] += 1
            continue
        if len(matched) != 1:
            rejected['multilocality'] += 1
            continue  # do not arbitrarily duplicate a multi-city posting
        i = matched.pop()
        clean = {k: v.get(k) for k in (
            'id', 'url', 'title', 'employer', 'salary_min', 'salary_max',
            'work_places', 'schedule', 'employment', 'education',
            'specialisation', 'creation_date', 'modification_date')}
        clean['addresses'] = addresses
        groups[i].append(clean)
    summaries = []
    for group in groups:
        salaries = [float(v['salary_min']) for v in group
                    if v.get('salary_min') and 0 < float(v['salary_min']) < 1e7]
        cats = {}
        employers = {}
        for v in group:
            k = v.get('specialisation') or 'Не указана'
            cats[k] = cats.get(k, 0) + 1
            k = v.get('employer') or 'Не указан'
            employers[k] = employers.get(k, 0) + 1
        summaries.append({
            'postings': len(group),
            'work_places_reported': sum(float(v.get('work_places') or 0) for v in group),
            'salary_floor_median': median(salaries) if salaries else None,
            'salary_floor_n': len(salaries),
            'categories': sorted(cats.items(), key=lambda x: (-x[1], x[0])),
            'employers': sorted(employers.items(), key=lambda x: (-x[1], x[0])),
            'records': group,
        })
    return summaries, rejected


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = read_csv(DATA / 'baseline_2024.csv')
    order = [c[0] for c in CENTERS]
    rows.sort(key=lambda r: order.index(r['oktmo']) if r['oktmo'] in order else 6)
    for r in rows:
        for k in ('population', 'employees', 'population_2023'):
            r[k] = int(r[k])
        r['wage'] = float(r['wage'])
    ids = [r['oktmo'] for r in rows]
    assert len(ids) == len(set(ids)) == 45 and ids[:6] == order
    matrix = read_csv(ROOT / 'data' / 'osrm_minutes.csv')
    matrix = {r['from_oktmo']: r for r in matrix}
    times = [[float(matrix[a][b]) for b in ids] for a in ids]
    w, demand, access, error = model(rows, times)
    snapshot = json.loads((DATA / 'vacancies_2026-11-26.json').read_text(encoding='utf-8'))
    vacancy_summary, vacancy_rejected = summarize_vacancies(snapshot)
    housing = [[] for _ in CENTERS]
    for r in read_csv(ROOT / 'data' / 'eisgs_rt_under_construction_2026-10-27.csv'):
        i = locality(r['address'])
        if i is None:
            continue
        housing[i].append({**r, 'flats': int(float(r['flats'] or 0)),
                           'lat': float(r['lat']), 'lon': float(r['lon'])})
    geo = json.loads((DATA / 'boundaries.json').read_text(encoding='utf-8'))
    crossborder = json.loads((DATA / 'crossborder_context.json').read_text(encoding='utf-8'))
    profiles = []
    for i, (code, name, slug, _) in enumerate(CENTERS):
        r = rows[i]
        alternatives = sorted((j for j in range(45) if i != j),
                              key=lambda j: -(rows[j]['employees'] * w[i][j]))[:5]
        profiles.append({
            **r, 'name': name, 'slug': slug, 'access': access[i],
            'outside_pilot_weight': 1 - sum(rows[j]['employees'] * w[i][j]
                                           for j in range(6)) /
                                      sum(rows[j]['employees'] * w[i][j] for j in range(45)),
            'alternatives': [{'oktmo': rows[j]['oktmo'], 'name': rows[j]['district'],
                              'minutes': (times[i][j] + times[j][i]) / 2,
                              'wage': rows[j]['wage']} for j in alternatives],
            'housing': {'buildings': len(housing[i]),
                        'flats': sum(h['flats'] for h in housing[i]), 'records': housing[i]},
            'vacancies': vacancy_summary[i],
        })
    source_list = [
        {'name': 'Росстат · население', 'vintage': '01.01.2024',
         'url': rows[0]['population_source'].split('#')[0], 'type': 'Наблюдение',
         'note': 'БД ПМО, Y48112027. Население всего муниципального района, включая город.'},
        {'name': 'Росстат · работники', 'vintage': '2024',
         'url': 'https://rosstat.gov.ru/storage/mediabank/MUNST.htm', 'type': 'Наблюдение',
         'note': 'БД ПМО, Y48423005. Среднесписочные работники организаций без МСП; не все рабочие места.'},
        {'name': 'Росстат · зарплата', 'vintage': '2024',
         'url': rows[0]['wage_source'].split('#')[0], 'type': 'Наблюдение',
         'note': 'БД ПМО, Y48423007. Средняя начисленная зарплата по месту работы; отличается от зарплаты в объявлениях.'},
        {'name': 'OSRM / OpenStreetMap', 'vintage': '10.2026',
         'url': 'https://project-osrm.org/', 'type': 'Расчёт маршрута',
         'note': 'Направленная матрица между центрами 45 МО; автомобиль, без пробок и расписаний. Не поездки от каждого дома.'},
        {'name': 'Работа России · вакансии', 'vintage': snapshot.get('collection_timestamp', '26.11.2026'),
         'url': 'https://trudvsem.ru/opendata/api', 'type': 'Наблюдение',
         'note': 'Объявления портала, не структура всей занятости. Отбор по адресу работы; полнота выгрузки указана отдельно.'},
        {'name': 'ЕИСЖС · строящиеся дома', 'vintage': '27.10.2026',
         'url': 'https://наш.дом.рф/', 'type': 'Наблюдение',
         'note': 'Существующий снимок реестра. Квартиры в строящихся домах, не всё жильё; пропуски не заменены нулями.'},
        {'name': 'Границы муниципалитетов', 'vintage': 'Снимок исходного двойника',
         'url': 'https://github.com/timurkanaz/Russia_geojson_OSM', 'type': 'Картография',
         'note': '© участники OpenStreetMap, ODbL. Упрощённые контуры; подписи размещены внутри районов.'},
    ]
    payload = {
        'version': '0.2.0-preview', 'date': '2026-11-26', 'profiles': profiles,
        'districts': rows, 'times': times, 'geometry': geo, 'crossborder': crossborder,
        'vacancy_collection': {k: v for k, v in snapshot.items() if k != 'records'},
        'sources': source_list,
        'checks': {'districts': 45, 'pilot_centers': 6, 'directed_routes': 2025,
                   'allocation_conservation_error': error, 'vacancy_rejected': vacancy_rejected},
        'missing': ['Наблюдаемая матрица трудовых поездок юго-востока',
                    'Распределение расходов жителей по местам покупки',
                    'Полные расписания автобусов и служебных перевозок',
                    'Работники МСП и размещение всех рабочих мест',
                    'Полная сопоставимая матрица для внешних центров'],
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    (OUT / 'enrichment.json').write_text(text, encoding='utf-8')
    safe_json = text.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (ROOT / 'site' / 'southeast_template.html').read_text(encoding='utf-8')
    page = template.replace('__TWIN_DATA__', safe_json)
    target = ROOT / 'site' / 'southeast_preview_2026-11-26.html'
    target.write_text(page, encoding='utf-8')
    hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(DATA.glob('*')) if p.is_file()}
    (OUT / 'input_hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    flat = []
    for p in profiles:
        flat.append({'oktmo': p['oktmo'], 'center': p['name'], 'population_2024': p['population'],
                     'employees_without_sme_2024': p['employees'], 'wage_2024': p['wage'],
                     'model_access_tau45': p['access'],
                     'vacancy_postings': p['vacancies']['postings'],
                     'vacancy_salary_floor_median': p['vacancies']['salary_floor_median'],
                     'housing_buildings_2026_10_27': p['housing']['buildings'],
                     'housing_flats_2026_10_27': p['housing']['flats']})
    with (OUT / 'centers_enriched.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=flat[0].keys())
        writer.writeheader(); writer.writerows(flat)
    print(json.dumps({'html': str(target), 'profiles': flat, 'checks': payload['checks'],
                      'vacancy_complete': snapshot.get('complete')}, ensure_ascii=False, indent=2))
    return payload


if __name__ == '__main__':
    build()
