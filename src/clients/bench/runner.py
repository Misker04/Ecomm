from __future__ import annotations

import argparse
import statistics
import threading
from typing import List, Tuple

from ...common.config import load_config, get_endpoint
from ...common.protocol import PersistentRpcClient
from ...common.time_utils import monotonic_s
from .workload import setup_sellers, setup_buyers, seller_1000_ops, buyer_1000_ops


def run_once(n_sellers: int, n_buyers: int, items_per_seller: int, cfg_path: str) -> Tuple[float, float]:
    cfg = load_config(cfg_path)
    sf = get_endpoint(cfg.seller_frontend)
    bf = get_endpoint(cfg.buyer_frontend)

    # Setup phase (create accounts, login, register items)
    seller_setup = PersistentRpcClient(sf.host, sf.port, timeout_s=30.0)
    buyer_setup = PersistentRpcClient(bf.host, bf.port, timeout_s=30.0)
    seller_setup.connect()
    buyer_setup.connect()

    sellers = setup_sellers(seller_setup, n_sellers, items_per_seller, category=1)
    buyers = setup_buyers(buyer_setup, n_buyers)

    seller_setup.close()
    buyer_setup.close()

    # Measured phase: one persistent TCP connection per simulated client thread
    threads: List[threading.Thread] = []

    def seller_task(sess: str, item_ids):
        c = PersistentRpcClient(sf.host, sf.port, timeout_s=30.0)
        c.connect()
        try:
            seller_1000_ops(c, sess, item_ids)
        finally:
            c.close()

    def buyer_task(sess: str, pick: int):
        c = PersistentRpcClient(bf.host, bf.port, timeout_s=30.0)
        c.connect()
        try:
            buyer_1000_ops(c, sess, 1, pick)
        finally:
            c.close()

    for s in sellers:
        t = threading.Thread(target=seller_task, args=(s["session_id"], s["item_ids"]), daemon=True)
        threads.append(t)

    for i, b in enumerate(buyers):
        t = threading.Thread(target=buyer_task, args=(b["session_id"], i), daemon=True)
        threads.append(t)

    start = monotonic_s()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = monotonic_s() - start

    total_clients = n_sellers + n_buyers
    total_ops = total_clients * 1000
    throughput = total_ops / elapsed if elapsed > 0 else 0.0
    avg_resp = elapsed / total_ops if total_ops > 0 else 0.0
    return avg_resp, throughput


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--scenario", type=int, required=True, choices=[1, 2, 3])
    ap.add_argument("--runs", type=int, default=10)
    args = ap.parse_args()

    if args.scenario == 1:
        n_sellers, n_buyers = 1, 1
    elif args.scenario == 2:
        n_sellers, n_buyers = 10, 10
    else:
        n_sellers, n_buyers = 100, 100

    items_per_seller = 10
    avgs: List[float] = []
    thr: List[float] = []

    for r in range(args.runs):
        avg_resp, throughput = run_once(n_sellers, n_buyers, items_per_seller, args.config)
        avgs.append(avg_resp)
        thr.append(throughput)
        print(f"run {r+1}/{args.runs}: avg_resp={avg_resp:.6f}s, throughput={throughput:.2f} ops/s")

    print("\n=== Averages over runs ===")
    print(f"Scenario {args.scenario}: sellers={n_sellers}, buyers={n_buyers}")
    print(f"Average response time (s/op): {statistics.mean(avgs):.6f}")
    print(f"Average throughput (ops/s):    {statistics.mean(thr):.2f}")


if __name__ == "__main__":
    main()
