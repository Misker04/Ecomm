#!/usr/bin/env bash
set -euo pipefail
python -m src.frontend_buyer.server --config config/local.yaml
