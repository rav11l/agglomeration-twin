"""Meaningful checks for complete municipal scope and non-fabricated data coverage."""
import json
import csv
import math
import unittest

from build_republic import ROOT, ALIASES, read_csv, read_json, resolve_address, inside, rings, model, classify_vacancies, validate_vacancy_snapshot


class RepublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'outputs/republic/enrichment.json').read_text(encoding='utf-8'))
        cls.rows = cls.data['profiles']

    def test_every_municipality_has_a_profile_and_geometry(self):
        canonical = read_csv(ROOT / 'data/districts_input.csv')
        self.assertEqual(len(self.rows), 45)
        self.assertEqual({r['oktmo'] for r in canonical}, {r['oktmo'] for r in self.rows})
        self.assertEqual({r['slug'] for r in self.rows}, set(ALIASES))
        self.assertEqual({r['slug'] for r in self.rows}, {r['id'] for r in self.data['geometry']})
        self.assertEqual(sum(r['name'].endswith('район') for r in self.rows), 43)
        for r in self.rows:
            for field in ['population', 'employees', 'wage', 'access']:
                self.assertTrue(math.isfinite(r[field]) and r[field] > 0)

    def test_cities_and_street_names_are_not_confused(self):
        locate = lambda s: (self.rows[i]['slug'] if (i := resolve_address(s, self.rows)) is not None else None)
        self.assertEqual(locate('РТ, г. Казань, улица Азнакаевская, 1'), 'казань')
        self.assertEqual(locate('Тукаевский район, село Биклянь'), 'тукаевский')
        self.assertEqual(locate('г Набережные Челны, проспект Мира'), 'набережные челны')
        self.assertEqual(locate('Лаишевский район, улица Казанская'), 'лаишевский')
        self.assertIsNone(locate('г. Октябрьский, Башкортостан'))

    def test_polygon_holes_and_multipart(self):
        shape = rings('M0,0L10,0L10,10L0,10ZM2,2L4,2L4,4L2,4ZM20,20L22,20L22,22L20,22Z')
        self.assertTrue(inside((1, 1), shape))
        self.assertFalse(inside((3, 3), shape))
        self.assertTrue(inside((21, 21), shape))
        self.assertFalse(inside((15, 15), shape))

    def test_all_housing_is_accounted_for(self):
        houses = read_csv(ROOT / 'data/eisgs_rt_under_construction_2026-10-27.csv')
        self.assertEqual(sum(r['housing']['buildings'] for r in self.rows), len(houses))
        self.assertEqual(sum(r['housing']['flats'] for r in self.rows),
                         sum(int(float(r['flats'] or 0)) for r in houses))
        audit = json.loads((ROOT / 'outputs/republic/housing_assignment_audit.json').read_text(encoding='utf-8'))
        self.assertEqual(len({r['objId'] for r in audit}), len(houses))
        self.assertEqual(sum(r['method'] == 'verified_locality' for r in audit), 1)
        osinovo = next(r for r in audit if r['objId'] == '73243')
        self.assertEqual(osinovo['assigned_oktmo'], '92628000')
        self.assertTrue(osinovo['override_source'].startswith('https://zelenodolsk.tatarstan.ru/'))

    def test_missing_vacancies_stay_missing(self):
        empty_partial, _, _ = classify_vacancies({'complete': False, 'records': []}, self.rows)
        self.assertTrue(all(r['postings'] is None for r in empty_partial))
        empty_complete, _, _ = classify_vacancies({'complete': True, 'records': []}, self.rows)
        self.assertTrue(all(r['postings'] == 0 for r in empty_complete))
        self.assertEqual(sum(len(r['vacancies']['records']) for r in self.rows),
                         self.data['checks']['vacancy_audit']['assigned'])
        audit = self.data['checks']['vacancy_audit']
        self.assertEqual(audit['assigned'] + audit['unmatched'] + audit['multi_municipality'] + audit['duplicate'],
                         self.data['vacancy_collection']['unique_records'])
        if self.data['checks']['vacancy_region_complete']:
            self.assertEqual(self.data['checks']['vacancy_unique_collected'], self.data['checks']['vacancy_portal_total'])
            self.assertTrue(all(r['vacancies']['state'] == 'regional_snapshot' for r in self.rows))

    def test_false_completeness_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_vacancy_snapshot({'complete': True, 'region_total': 2, 'unique_records': 1,
                                      'scope': 'regional_snapshot', 'records': [{'id': 'x'}]})

    def test_complete_portal_registry_and_style(self):
        if not self.data['checks']['vacancy_region_complete']:
            self.skipTest('This check applies to a complete regional snapshot.')
        snapshot = read_json(ROOT / 'data/republic/vacancies_2026-11-26.json')
        self.assertTrue(validate_vacancy_snapshot(snapshot))
        self.assertEqual(len(snapshot['records']), 10401)
        self.assertEqual(sum(p['returned'] for p in snapshot['page_audit']), snapshot['fetched_records'])
        self.assertEqual(len(snapshot['page_audit']), 111)
        self.assertTrue(all(r['vacancies']['postings'] > 0 for r in self.rows))
        self.assertEqual(self.data['checks']['vacancy_audit'],
                         {'duplicate': 0, 'unmatched': 10, 'multi_municipality': 89, 'assigned': 10302})
        for r in snapshot['records']:
            self.assertTrue(set(r).isdisjoint({'contact_person', 'contact_list', 'email', 'phone', 'duty', 'requirements'}))
        with (ROOT / 'outputs/republic/vacancies_registry_2026-11-26.csv').open(encoding='utf-8-sig', newline='') as f:
            registry = list(csv.DictReader(f))
        self.assertEqual(len(registry), 10401)
        self.assertEqual(sum(r['mapping_status'] == 'assigned' for r in registry), 10302)
        css = (ROOT / 'site/republic.css').read_text(encoding='utf-8')
        for token in ['#FBFAF7', '#1D3C5C', '#15181C', '#E2DED6', 'Source Serif 4', 'Inter', '1080px']:
            self.assertIn(token, css)
        fonts = (ROOT / 'site/republic_fonts.css').read_text(encoding='utf-8')
        self.assertIn('base64,', fonts)
        self.assertIn('SIL OPEN FONT LICENSE', fonts.upper())

    def test_population_and_job_totals_and_accounting(self):
        self.assertEqual(sum(r['population'] for r in self.rows), 4003016)
        self.assertEqual(sum(r['employees'] for r in self.rows), 958116)
        for tau in (20, 30, 45, 60):
            w, demand, access, error = model(self.rows, self.data['times'], tau)
            self.assertLess(error, 1e-7)
            for j in range(45):
                allocated = sum(r['population'] * w[i][j] * self.rows[j]['employees'] / demand[j]
                                for i, r in enumerate(self.rows))
                self.assertAlmostEqual(allocated, self.rows[j]['employees'], places=7)


if __name__ == '__main__':
    unittest.main()
