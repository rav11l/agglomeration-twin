"""Build an offline twin for all 43 districts and two urban okrugs of Tatarstan.

python scripts/build_republic.py
All inputs are pinned in this repository; no network or private data is needed.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import median

from build_southeast import ROOT, read_csv, model

DATA = ROOT / 'data/republic'
OUT = ROOT / 'outputs/republic'


def read_json(path):
    """Read an ordinary JSON input or its losslessly compressed Git copy."""
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            return json.load(f)
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    with gzip.open(str(path) + '.gz', 'rt', encoding='utf-8') as f:
        return json.load(f)


ALIASES = {
    'агрызский': ['Агрыз'], 'азнакаевский': ['Азнакаево'],
    'аксубаевский': ['Аксубаево'], 'актанышский': ['Актаныш'],
    'алексеевский': ['Алексеевское'], 'алькеевский': ['Базарные Матаки'],
    'альметьевский': ['Альметьевск'], 'апастовский': ['Апастово'],
    'арский': ['Арск'], 'атнинский': ['Большая Атня'],
    'бавлинский': ['Бавлы'], 'балтасинский': ['Балтаси'],
    'бугульминский': ['Бугульма'], 'буинский': ['Буинск'],
    'верхнеуслонский': ['Верхний Услон'], 'высокогорский': ['Высокая Гора'],
    'дрожжановский': ['Старое Дрожжаное'], 'елабужский': ['Елабуга'],
    'заинский': ['Заинск'], 'зеленодольский': ['Зеленодольск'],
    'кайбицкий': ['Большие Кайбицы'], 'камско-устьинский': ['Камское Устье'],
    'кукморский': ['Кукмор'], 'лаишевский': ['Лаишево'],
    'лениногорский': ['Лениногорск'], 'мамадышский': ['Мамадыш'],
    'менделеевский': ['Менделеевск'], 'мензелинский': ['Мензелинск'],
    'муслюмовский': ['Муслюмово'], 'нижнекамский': ['Нижнекамск'],
    'новошешминский': ['Новошешминск'], 'нурлатский': ['Нурлат'],
    'пестречинский': ['Пестрецы'], 'рыбно-слободский': ['Рыбная Слобода'],
    'сабинский': ['Богатые Сабы'], 'сармановский': ['Сарманово'],
    'спасский': ['Болгар'], 'тетюшский': ['Тетюши'],
    'тукаевский': [],  # its administrative centre is outside its own district
    'тюлячинский': ['Тюлячи'], 'черемшанский': ['Черемшан'],
    'чистопольский': ['Чистополь'], 'ютазинский': ['Уруссу'],
    'казань': ['Казань'], 'набережные челны': ['Набережные Челны'],
}


def normalize(s):
    return str(s or '').lower().replace('ё', 'е').replace('–', '-').replace('—', '-')


def address_candidates(address, rows):
    """Explicit district first; standalone locality names only as a fallback.

    Never use a job title or employer's registered address to locate a workplace.
    Explicit municipal names win over a street named after a different city.
    """
    s = normalize(address)
    explicit = []
    for i, r in enumerate(rows):
        slug = r['slug']
        if slug in ('казань', 'набережные челны'):
            pattern = r'(?<!\w)(?:г\.?\s*|город\s+)' + re.escape(slug) + r'(?!\w)'
        else:
            stem = re.escape(slug[:-2])
            pattern = r'(?<!\w)' + stem + r'\w*\s+(?:муниципальн\w*\s+)?(?:район\w*|р-н)(?!\w)'
        if re.search(pattern, s):
            explicit.append(i)
    if explicit:
        return set(explicit)
    matches = set()
    for i, r in enumerate(rows):
        for name in ALIASES[r['slug']]:
            name = normalize(name)
            if re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', s):
                matches.add(i)
    return matches


def resolve_address(address, rows):
    hits = address_candidates(address, rows)
    return next(iter(hits)) if len(hits) == 1 else None


def validate_vacancy_snapshot(snapshot):
    if not snapshot.get('complete'):
        return False
    total = int(snapshot['region_total'])
    records = snapshot['records']
    keys = {(v.get('employer_code', ''), v['id']) for v in records}
    assert snapshot.get('scope') == 'regional_snapshot'
    assert len(records) == len(keys) == int(snapshot['unique_records']) == total
    assert int(snapshot['fetched_records']) >= total
    assert not snapshot.get('failed_pages')
    assert all(str(v.get('portal_region_code', '')).startswith('16') for v in records)
    assert snapshot.get('page_audit'), 'A complete snapshot requires a retrieval audit.'
    return True


def rings(path):
    return [[(float(x), float(y)) for x, y in re.findall(r'(-?[\d.]+),(-?[\d.]+)', part)]
            for part in path.split('M')[1:]]


def inside(point, polygons):
    """Even-odd polygon test, including multipart contours and holes."""
    x, y = point
    result = False
    for polygon in polygons:
        if len(polygon) < 3:
            continue
        for j, (x1, y1) in enumerate(polygon):
            x2, y2 = polygon[(j + 1) % len(polygon)]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                result = not result
    return result


def spatial_match(lat, lon, geometry, rows):
    x, y = lon * math.cos(math.radians(55.6)) * 100, -lat * 100
    hits = [i for i, r in enumerate(rows) if inside((x, y), geometry[r['slug']]['rings'])]
    return hits[0] if len(hits) == 1 else None


def classify_housing(houses, rows, geometry, overrides=None):
    groups = [[] for _ in rows]
    audit = []
    overrides = {r['objId']: r for r in (overrides or [])}
    for h in houses:
        a = resolve_address(h['address'], rows)
        try:
            lat, lon = float(h['lat']), float(h['lon'])
            g = spatial_match(lat, lon, geometry, rows)
        except (ValueError, TypeError):
            lat = lon = None
            g = None
        # A spatially assigned record is accompanied by a disagreement audit.
        i = g if g is not None else a
        method = 'geometry' if g is not None else 'address' if a is not None else 'unmatched'
        override = overrides.get(h['objId'])
        if override is not None:
            assert i is None, 'Verified overrides must not silently replace an existing assignment.'
            i = next(k for k, row in enumerate(rows) if row['oktmo'] == override['oktmo'])
            method = 'verified_locality'
        record = {'objId': h['objId'], 'address': h['address'], 'name': h.get('name', ''),
                  'flats': int(float(h['flats'] or 0)), 'ready': h.get('ready'),
                  'lat': lat, 'lon': lon, 'assignment': method}
        if i is not None:
            groups[i].append(record)
        audit.append({'objId': h['objId'], 'method': method,
                      'assigned_oktmo': rows[i]['oktmo'] if i is not None else None,
                      'address_oktmo': rows[a]['oktmo'] if a is not None else None,
                      'geometry_oktmo': rows[g]['oktmo'] if g is not None else None,
                      'disagreement': a is not None and g is not None and a != g,
                      'flats': record['flats'],
                      'override_source': override['source_url'] if override else None})
    return groups, audit


def classify_vacancies(snapshot, rows):
    groups = [[] for _ in rows]
    seen = set()
    audit = {'duplicate': 0, 'unmatched': 0, 'multi_municipality': 0, 'assigned': 0}
    unassigned = []
    complete = bool(snapshot.get('complete'))
    for v in snapshot.get('records', []):
        key = (v.get('employer_code', ''), v['id'])
        if key in seen:
            audit['duplicate'] += 1
            continue
        seen.add(key)
        hits = set().union(*(address_candidates(a.get('location', ''), rows)
                           for a in v.get('addresses', []))) if v.get('addresses') else set()
        if len(hits) != 1:
            reason = 'multi_municipality' if hits else 'unmatched'
            audit[reason] += 1
            unassigned.append({'id': v['id'], 'url': v.get('url'), 'title': v.get('title'),
                               'reason': reason, 'candidate_oktmo': [rows[i]['oktmo'] for i in sorted(hits)],
                               'addresses': v.get('addresses', [])})
            continue
        i = hits.pop()
        record = {k: v.get(k) for k in ('id', 'url', 'title', 'employer', 'employer_code', 'salary_min',
                  'salary_max', 'work_places', 'schedule', 'employment', 'education',
                  'specialisation', 'creation_date', 'modification_date', 'addresses')}
        if re.match(r'^(ИП\s|Индивидуальный предприниматель)', record.get('employer') or '', re.I):
            record['employer'] = 'Индивидуальный предприниматель'
        groups[i].append(record)
        audit['assigned'] += 1
    summaries = []
    for group in groups:
        wages = [float(v['salary_min']) for v in group if v.get('salary_min')
                 and 0 < float(v['salary_min']) < 1e7]
        categories = {}
        for v in group:
            category = v.get('specialisation') or 'Не указана'
            categories[category] = categories.get(category, 0) + 1
        summaries.append({'state': 'regional_snapshot' if complete else 'examples' if group else 'not_collected',
                          'postings': len(group) if complete or group else None,
                          'salary_floor_median': median(wages) if wages else None,
                          'salary_floor_n': len(wages),
                          'categories': sorted(categories.items(), key=lambda x: (-x[1], x[0])),
                          'records': group})
    return summaries, audit, unassigned


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = {r['oktmo']: r for r in read_csv(ROOT / 'data/southeast/baseline_2024.csv')}
    canonical = read_csv(ROOT / 'data/districts_input.csv')
    rows = []
    for r in canonical:
        b = raw[r['oktmo']]
        rows.append({**b, 'slug': r['id'], 'name': r['name'],
                     'short': r['name'].replace(' район', ''),
                     'population': int(b['population']), 'employees': int(b['employees']),
                     'population_2023': int(b['population_2023']), 'wage': float(b['wage'])})
    rows.sort(key=lambda r: (0 if r['slug'] == 'казань' else 1 if r['slug'] == 'набережные челны' else 2,
                             r['name']))
    assert len(rows) == len(set(r['oktmo'] for r in rows)) == 45
    geo_rows = json.loads((DATA / 'boundaries.json').read_text(encoding='utf-8'))
    geometry = {r['id']: {**r, 'rings': rings(r['path'])} for r in geo_rows}
    assert set(geometry) == {r['slug'] for r in rows} == set(ALIASES)
    matrix = {r['from_oktmo']: r for r in read_csv(ROOT / 'data/osrm_minutes.csv')}
    times = [[float(matrix[a['oktmo']][b['oktmo']]) for b in rows] for a in rows]
    w, demand, access, error = model(rows, times)
    aggs = json.loads((ROOT / 'data/agglomerations.json').read_text(encoding='utf-8'))
    houses = read_csv(ROOT / 'data/eisgs_rt_under_construction_2026-10-27.csv')
    overrides = json.loads((DATA / 'housing_overrides.json').read_text(encoding='utf-8'))
    hgroups, haudit = classify_housing(houses, rows, geometry, overrides)
    vacancy_path = DATA / 'vacancies_2026-11-26.json'
    if Path(str(vacancy_path) + '.gz').exists():
        vacancy_path = Path(str(vacancy_path) + '.gz')
    if not vacancy_path.exists() and not Path(str(vacancy_path) + '.gz').exists():
        vacancy_path = ROOT / 'data/southeast/vacancies_2026-11-26.json'
    snapshot = read_json(vacancy_path)
    vacancy_complete = validate_vacancy_snapshot(snapshot)
    vgroups, vaudit, unassigned = classify_vacancies(snapshot, rows)
    profiles = []
    for i, r in enumerate(rows):
        memberships = [{'name': name, 'belt': 1 if r['slug'] in agg['ring1'] else 2}
                       for name, agg in aggs['aggs'].items()
                       if r['slug'] in agg['ring1'] or r['slug'] in agg['ring2']]
        own = r['employees'] * w[i][i]
        weighted_jobs = sum(rows[j]['employees'] * w[i][j] for j in range(45))
        profiles.append({**r, 'memberships': memberships, 'access': access[i],
                         'workers_per100': 100 * r['employees'] / r['population'],
                         'outside_weight': 1 - own / weighted_jobs,
                         'is_core': r['slug'] in aggs['cores'].values(),
                         'housing': {'buildings': len(hgroups[i]),
                                     'flats': sum(h['flats'] for h in hgroups[i]),
                                     'records': hgroups[i]},
                         'vacancies': vgroups[i]})
    checks = {
        'municipalities': 45, 'districts': 43, 'urban_okrugs': 2,
        'profiles': len(profiles), 'geometries': len(geometry), 'directed_routes': 2025,
        'population_total': sum(r['population'] for r in rows),
        'employees_total': sum(r['employees'] for r in rows),
        'allocation_conservation_error': error,
        'housing_input_buildings': len(houses),
        'housing_input_flats': sum(int(float(r['flats'] or 0)) for r in houses),
        'housing_assigned_buildings': sum(len(g) for g in hgroups),
        'housing_assigned_flats': sum(sum(h['flats'] for h in g) for g in hgroups),
        'housing_unmatched': sum(r['method'] == 'unmatched' for r in haudit),
        'housing_disagreements': sum(r['disagreement'] for r in haudit),
        'housing_verified_locality': sum(r['method'] == 'verified_locality' for r in haudit),
        'vacancy_audit': vaudit,
        'vacancy_municipalities_with_examples': sum(bool(g['records']) for g in vgroups),
        'vacancy_region_complete': vacancy_complete,
        'vacancy_portal_total': snapshot.get('region_total'),
        'vacancy_unique_collected': snapshot.get('unique_records'),
        'vacancy_unassigned': len(unassigned),
    }
    assert checks['housing_assigned_buildings'] + checks['housing_unmatched'] == len(houses)
    assert checks['housing_assigned_flats'] + sum(r['flats'] for r in haudit
            if r['method'] == 'unmatched') == checks['housing_input_flats']
    original_sources = read_json(DATA / 'sources.json')
    sources = [dict(s) for s in original_sources]
    sources[4]['note'] = ('Полный региональный срез портала «Работа России». '
                          'Не весь рынок труда. Адреса сопоставлены с муниципалитетами; '
                          'неоднозначные и неполные адреса вынесены в отдельный аудит.'
                          if vacancy_complete else
                         'Неполная поисковая подборка. Все адреса заново сопоставлены с 45 МО. '
                          'Отсутствие примеров означает «не собрано», а не ноль вакансий. '
                          'Полный региональный сбор завершился тайм-аутом.')
    sources[4]['vintage'] = snapshot.get('collection_timestamp', '26.11.2026')
    sources[5]['note'] = ('Снимок 314 объектов от 27.10.2026. Основная привязка по координатам '
                          'к муниципальным контурам; резервная — по адресу. '
                          'Один объект в Осиново проверен по официальному сайту поселения. '
                          'Сопоставления сохранены в аудите. Не весь жилищный фонд.')
    sources.append({'name': 'Осиново · проверка муниципальной принадлежности',
                    'vintage': 'Проверено 26.11.2026', 'type': 'Проверка адреса',
                    'url': overrides[0]['source_url'],
                    'note': 'Объект ЕИСЖС 73243 отнесён к Зеленодольскому району по адресу '
                            'Осиновского сельского поселения. Исходные координаты сохранены.'})
    payload = {
        'version': '0.3.1', 'date': '2026-11-26', 'profiles': profiles,
        'districts': rows, 'times': times, 'geometry': geo_rows, 'agglomerations': aggs,
        'sources': sources, 'checks': checks,
        'vacancy_collection': {k: v for k, v in snapshot.items() if k != 'records'},
        'vacancies_unassigned': unassigned,
        'scope_note': '43 муниципальных района и два городских округа; границы и данные исходного двойника.',
        'missing': ([] if vacancy_complete else ['Полный сопоставимый срез вакансий по всем 45 МО']) + [
                    'Наблюдаемая матрица трудовых поездок всей республики',
                    'Работники МСП и точное размещение всех рабочих мест',
                    'Полные расписания автобусов и служебных перевозок',
                    'Покупки жителей по месту назначения и бюджетный эффект',
                    'Сопоставимый рынок труда за границами Татарстана'],
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    (OUT / 'enrichment.json').write_text(text, encoding='utf-8')
    (OUT / 'enrichment.json.gz').write_bytes(gzip.compress(text.encode('utf-8'), mtime=0))
    (OUT / 'housing_assignment_audit.json').write_text(json.dumps(haudit, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'validation.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'vacancies_unassigned.json').write_text(json.dumps(unassigned, ensure_ascii=False, indent=2), encoding='utf-8')
    template = (ROOT / 'site/republic_template.html').read_text(encoding='utf-8')
    target = ROOT / 'site/tatarstan_twin_2026-11-26.html'
    fonts = ROOT / 'site/republic_fonts.css'
    css = (fonts.read_text(encoding='utf-8') if fonts.exists() else '') + (ROOT / 'site/republic.css').read_text(encoding='utf-8')
    target.write_text(template.replace('__TWIN_CSS__', css)
                     .replace('__TWIN_DATA__', text.replace('<', '\\u003c')
                     .replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')), encoding='utf-8')
    records = [{'oktmo': p['oktmo'], 'municipality': p['name'], 'population_2024': p['population'],
                'employees_without_sme_2024': p['employees'], 'wage_2024': p['wage'],
                'workers_per100_residents': p['workers_per100'], 'model_access_tau45': p['access'],
                'housing_buildings_in_snapshot': p['housing']['buildings'],
                'housing_flats_in_snapshot': p['housing']['flats'],
                'vacancy_collection_state': p['vacancies']['state'],
                'vacancy_postings_mapped': p['vacancies']['postings'],
                'vacancy_salary_floor_median': p['vacancies']['salary_floor_median']} for p in profiles]
    with (OUT / 'municipalities_enriched.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader(); writer.writerows(records)
    mapping = {(v.get('employer_code', ''), v['id']): p for p in profiles for v in p['vacancies']['records']}
    unresolved = {r['id']: r for r in unassigned}
    registry = []
    for v in snapshot['records']:
        p = mapping.get((v.get('employer_code', ''), v['id']))
        registry.append({'vacancy_id': v['id'], 'municipality_oktmo': p['oktmo'] if p else None,
                         'municipality': p['name'] if p else None,
                         'mapping_status': 'assigned' if p else unresolved.get(v['id'], {}).get('reason', 'unmatched'),
                         'title': v.get('title'), 'employer': v.get('employer'),
                         'salary_min': v.get('salary_min'), 'salary_max': v.get('salary_max'),
                         'work_places_reported': v.get('work_places'),
                         'specialisation': v.get('specialisation'),
                         'workplace_addresses': '; '.join(a.get('location', '') for a in v.get('addresses', [])),
                         'modified': v.get('modification_date'), 'source_url': v.get('url')})
    with (OUT / 'vacancies_registry_2026-11-26.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=registry[0].keys())
        writer.writeheader(); writer.writerows(registry)
    inputs = [ROOT / 'data/southeast/baseline_2024.csv', DATA / 'boundaries.json',
              ROOT / 'data/districts_input.csv', ROOT / 'data/osrm_minutes.csv',
              ROOT / 'data/agglomerations.json',
              ROOT / 'data/eisgs_rt_under_construction_2026-10-27.csv',
              vacancy_path, DATA / 'housing_overrides.json']
    inputs = [p if p.exists() else Path(str(p) + '.gz') for p in inputs]
    inputs.append(DATA / 'sources.json')
    (OUT / 'input_hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\', '/'):
                     hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}, indent=2), encoding='utf-8')
    print(json.dumps({'html': str(target), 'checks': checks}, ensure_ascii=False, indent=2))
    return payload


if __name__ == '__main__':
    build()
