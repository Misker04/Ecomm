#!/usr/bin/env bash
set -euo pipefail
python -m src.clients.bench.runner --config config/local.yaml --scenario 1
python -m src.clients.bench.runner --config config/local.yaml --scenario 2
python -m src.clients.bench.runner --config config/local.yaml --scenario 3
