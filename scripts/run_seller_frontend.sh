#!/usr/bin/env bash
set -euo pipefail
python -m src.frontend_seller.server --config config/local.yaml
