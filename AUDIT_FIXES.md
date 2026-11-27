# RU/EN audit fixes · v0.3.2 · 27.11.2026

| ID | Correction |
| --- | --- |
| F01 | Flat rate 0.1% → 0.2%, explicitly ordinary individually owned flats in Kazan. The residential aggregate uses this rate illustratively. Other rates remain scenario assumptions. About RUB 66.6 mn/year and 2.3% over 16 years are gross, before exemptions and deductions; not a revenue forecast. |
| F02 | Wage/spending ranks no longer establish household overspending or commuting. |
| F03 | The regional employee/population gap is conditional, not unemployment, employer demand or a gap proven to be filled by commuting. |
| F04 | One shared 45-municipality UI supports RU/EN, parent language changes, controls, dynamic content, source notes, search, labels and CSV headers. Original vacancy fields retain source language with an explicit note. |
| F05 | Train heading and navigation use arrivals by 9:30, consistent with the historical 29.10.2026 snapshot. This is not workplace arrival by 9. |
| F06 | Rosstat employees exclude small businesses, not all SMEs. Numerical observations preserved; the CSV field is renamed. |
| F07 | Metro premium 95% interval −5.3% to +19.8% includes zero; clustered regression does not establish causality. Positive scenarios are not the full uncertainty interval. |
| F08 | RU/EN version labels agree in static markup; post-render version patch removed. Metadata supplied in site/tilda_metadata.json. |
| F09 | Historical 48 km / 17 stops are dated to the ministry’s 2022 concept. Incommensurate stage lengths are no longer added. |
| F10 | 2024 baseline and housing snapshot 27.10.2026 labelled explicitly. Station usage is the 2018 dataset used, without an unverified “latest” claim. |
| F11 | Parent and module ARIA labels, placeholders and titles change with locale. Source-language vacancy fields are identified. |
| F12 | Historical 2023 route funding is not full operating cost; no common price year or discounting with assumed 2028 tax flows. The comparison does not establish funding adequacy. WP10 reference added. |

## Sources and reproducibility

- [Kazan City Duma act, FNS tax-rate register](https://www.nalog.gov.ru/rn16/service/tax/d1478708/).
- [Kazan official explanation of the 0.2% flat rate](https://kzn.ru/meriya/press-tsentr/novosti/46094_s_1_yanvarya_stavka_naloga_na_kvartiry_v_kazani_sostavit_0_2_ot_kadastrovoy_stoimosti/).
- [Rosstat municipal indicators](https://rosstat.gov.ru/storage/mediabank/MUNST.htm), indicator Y48423005: average payroll employees excluding small businesses.
- [Tatarstan Transport Ministry presentation, 2022](https://mindortrans.tatarstan.ru/file/mindortrans/File/Презентация%20коллегия%202022%20(1)(1).pdf).
- Hedonic result independently reproduced from `data/hedonic_sample.csv`: 129 houses, 86 complexes, log coefficient 0.0628910, clustered standard error 0.0600014; transformed 95% interval −0.0532399…0.1978061. No new observations collected.

Run `python scripts/build_republic.py`, `python scripts/test_republic.py`, `node scripts/test_republic_ui.cjs`, `python scripts/scenarios.py`, `node --test tests/laishevo.test.mjs` and `node tests/site_syntax.cjs`. The immutable data commit, SHA256 and byte length are embedded by `scripts/build_republic_embed.py --data-ref <commit>`.

The preserved observations cover 45 municipalities, 4,003,016 residents, 958,116 organisation employees, 314 housing objects / 67,291 flats, and 10,401 portal postings (10,302 assigned, 99 unresolved). Mathematical conservation is an arithmetic check, not empirical model validation.

Publication status is recorded separately in PUBLICATION.md. Files prepared for v0.3.2 do not imply it has been published on Tilda or Zenodo.
