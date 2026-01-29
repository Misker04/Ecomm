#!/usr/bin/env bash
set -euo pipefail
python -m src.customer_db.server --config config/local.yaml
