# Двойник агломераций Татарстана

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23725482.svg)](https://doi.org/10.5281/zenodo.23725482)

Данные и код открытого цифрового двойника трёх агломераций Республики Татарстан — Казанской, Камской и Альметьевской. Страница двойника: [digitaleconomylab.ru/agglomeration-twin](https://digitaleconomylab.ru/agglomeration-twin).

Автор — Равиль Ахтямов, Digital Economy Lab. Принцип — только открытые данные: каждое число страницы можно пересчитать из таблиц этого репозитория.

## Результаты в шести строках

1. **Работа далеко от периферии.** 27 районов из 45 лежат дальше 65 минут на машине от ядра агломерации; в них живут 752 тыс. человек.
2. **Локальные центры есть.** По отношению работников к населению относительно пяти ближайших соседей выделяются Сабинский (1,91), Верхнеуслонский (1,88), Елабужский (1,73), Альметьевский (1,52), Зеленодольский (1,36) и Тюлячинский (1,23) районы.
3. **Десять кластеров покрывают 639 тыс. жителей периферии** — 85 % при радиусе 50 минут; шесть районов остаются вне кластеров.
4. **Метро и стройка.** 18 % строящихся квартир Казани находятся в километре от действующего метро; с первым участком второй линии — 28 % (+4 758 квартир, в основном у станции «Тулпар»).
5. **Премия за метро измерена неточно**: +6,5 % к цене м² в километре от станции, 95 %-й интервал от −5 до +20 % (129 домов, 86 ЖК, ошибки кластеризованы по ЖК).
6. **Налоги вернут малую долю прироста.** При премии 6,5 % налоги на имущество и землю в километре от новых станций дадут около 56 млн руб. в год — около 2 % стоимости участка (47 млрд) к 2046 году.

## Быстрый старт

```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
sh run_all.sh                                        # или четыре скрипта из scripts/ по очереди
```

Скрипты пишут таблицы в `outputs/` и печатают ключевые числа страницы. Сеть не нужна.

## Что внутри

| Путь | Содержимое |
|---|---|
| `data/districts_input.csv` | 45 МО: ОКТМО, население и работники 2024, площадь, пояс агломерации |
| `data/osrm_minutes.csv` | матрица времени в пути на машине между центрами МО, мин (OSRM) |
| `data/agglomerations.json` | ядра и пояса трёх агломераций |
| `data/eisgs_rt_under_construction_2026-10-27.csv` | строящиеся дома РТ по ЕИСЖС с расстояниями до метро и второй линии |
| `data/metro_stations.csv` | станции действующей линии и первого участка второй |
| `data/hedonic_sample.csv` | выборка для регрессии премии за метро |
| `data/nspd_line2_cadastre_aggregates.csv` | кадастровая стоимость участков и зданий в километре от станций второй линии |
| `data/flows_mayor_scheme.csv` | потоки в Казань: «сейчас» — ИПП РТ (2022), «по плану» — схема мэрии |
| `data/complex_scheme_224_targets.csv` | целевые показатели Комплексной схемы (КМ РТ № 224) к 2030 и 2050 годам |
| `data/od_ipp_2022.csv` | матрица ежедневных поездок ИПП РТ, 2022 (опубликована в статье Юсуповой и соавт., 2024) |
| `data/rail_to_kazan_by_0930.csv` | электрички, приходящие в Казань к 9:30, время в пути |
| `data/scenario_params.json` | параметры сценариев по умолчанию — те же, что у ползунков страницы |
| `scripts/balance.py` | доступность рабочих мест, насыщенность, локальные центры, дефицит |
| `scripts/clusters.py` | десять опорных кластеров периферии |
| `scripts/hedonic.py` | премия за близость к метро |
| `scripts/scenarios.py` | ASIF, возврат прироста у второй линии, пилотный город |
| `scripts/nspd_classify.js` | правило классификации объектов НСПД |
| `site/agglomeration-twin_page.html` | снимок кода страницы на дату выпуска |
| `DATA.md` | паспорт данных: источник, дата и способ получения каждого файла |

## Чего здесь нет

- Помесячных расходов СберИндекса, которые страница показывает по районам: их условия распространения не проверены, поэтому в депозит не кладутся (страница берёт их из отдельного блока данных).
- Сырых ответов НСПД и Яндекс Расписаний — только производные таблицы; способ повторного сбора описан в `DATA.md`.
- Геометрии границ МО (© участники OpenStreetMap, ODbL): площади районов приведены готовыми числами.

## Границы

Это лёгкие модели, а не транспортная модель с матрицами корреспонденций. Время в пути — по пустой дорожной сети без пробок. Работники — по крупным и средним организациям, без МСП. Премия за метро оценена на одном срезе цен строящегося жилья, а не на изменении цен после открытия станций. Налоговые ставки — потолки Налогового кодекса без казанских ставок и вычетов, без дисконтирования. Оценки прироста — порядок величины.

## Лицензия и цитирование

Код — MIT (`LICENSE`), данные — CC BY 4.0 (`LICENSE-DATA.md`).

Как ссылаться: Ахтямов Р. Двойник агломераций Татарстана: данные и код. Версия 0.1.2. Digital Economy Lab, 2026. DOI: [10.5281/zenodo.23725482](https://doi.org/10.5281/zenodo.23725482). DOI всех версий ведёт на последнюю; DOI версии 0.1.0 — 10.5281/zenodo.23725483.

---

## Tatarstan Agglomeration Twin (English summary)

Data and code behind the open digital twin of Tatarstan's three agglomerations at [digitaleconomylab.ru/agglomeration-twin](https://digitaleconomylab.ru/agglomeration-twin). Author: Ravil Akhtyamov, Digital Economy Lab. Open data only.

Contents: balance models for 45 municipalities (Rosstat population and employees for 2024, OSRM car travel times); ten peripheral clusters covering 639k of 752k residents beyond 65 minutes from a core; housing under construction from the EISZhS register (18% of Kazan's flats under construction lie within 1 km of the metro, 28% with the second line); a hedonic metro premium of +6.5% (95% CI −5% to +20%); NSPD cadastral aggregates within 1 km of the new stations, with property and land taxes recovering about RUB 56 mn a year, roughly 2% of the RUB 47 bn section cost by 2046; planned commuter flows, morning trains, an ASIF CO₂ estimate and a pilot-city scenario. Run `sh run_all.sh` after `pip install -r requirements.txt`. Code MIT, data CC BY 4.0. Cite as: Akhtyamov R. Tatarstan Agglomeration Twin: data and code, v0.1.2. Digital Economy Lab, 2026. DOI 10.5281/zenodo.23725482.
