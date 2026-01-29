#!/usr/bin/env bash
set -euo pipefail
python -m src.product_db.server --config config/local.yaml
