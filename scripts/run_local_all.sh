#!/usr/bin/env bash
set -euo pipefail

mkdir -p data reports

# Start DBs
python -m src.customer_db.server --config config/local.yaml > reports/customer_db.log 2>&1 &
CDB_PID=$!
python -m src.product_db.server --config config/local.yaml > reports/product_db.log 2>&1 &
PDB_PID=$!

sleep 0.5

# Start frontends
python -m src.frontend_buyer.server --config config/local.yaml > reports/buyer_frontend.log 2>&1 &
BF_PID=$!
python -m src.frontend_seller.server --config config/local.yaml > reports/seller_frontend.log 2>&1 &
SF_PID=$!

echo "Running. PIDs: CDB=$CDB_PID PDB=$PDB_PID BF=$BF_PID SF=$SF_PID"
echo "Stop with: kill $CDB_PID $PDB_PID $BF_PID $SF_PID"
wait
