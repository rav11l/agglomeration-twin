#!/usr/bin/env sh
# Воспроизводит все расчёты двойника из data/ в outputs/ и печатает ключевые числа.
set -e
cd "$(dirname "$0")"
python scripts/balance.py
python scripts/clusters.py
python scripts/hedonic.py
python scripts/scenarios.py
