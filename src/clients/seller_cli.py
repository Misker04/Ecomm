from __future__ import annotations

import argparse
import json

from ..common.config import load_config, get_endpoint
from ..common.protocol import RpcClient


HELP = """
Seller CLI commands:
  help
  create_account <seller_name> <username> <password>
  login <username> <password>
  logout
  get_seller_rating
  register_item <name> <category> <condition(New|Used)> <price> <qty> [kw1 ... kw5]
  change_price <category:id> <new_price>
  update_units <category:id> <remove_qty>
  display_items
  exit
"""


def parse_item_id(s: str):
    cat, iid = s.split(":")
    return {"category": int(cat), "id": int(iid)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    sf = get_endpoint(cfg.seller_frontend)
    client = RpcClient(sf.host, sf.port, timeout_s=10.0)

    session_id = None

    print(HELP.strip())
    while True:
        try:
            line = input("seller> ").strip()
        except EOFError:
            break
        if not line:
            continue
        parts = line.split()
        cmd = parts[0].lower()

        try:
            if cmd in ("exit", "quit"):
                break
            if cmd == "help":
                print(HELP.strip())
                continue

            if cmd == "create_account":
                seller_name, username, password = parts[1], parts[2], parts[3]
                resp = client.call("CreateAccount", {"seller_name": seller_name, "username": username, "password": password}, role="seller")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "login":
                username, password = parts[1], parts[2]
                resp = client.call("Login", {"username": username, "password": password}, role="seller")
                print(json.dumps(resp, indent=2))
                if resp.get("ok"):
                    session_id = resp["data"]["session_id"]
                continue

            if cmd == "logout":
                resp = client.call("Logout", {"session_id": session_id}, session_id=session_id, role="seller")
                print(json.dumps(resp, indent=2))
                session_id = None
                continue

            if cmd == "get_seller_rating":
                resp = client.call("GetSellerRating", {}, session_id=session_id, role="seller")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "register_item":
                name = parts[1]
                cat = int(parts[2])
                cond = parts[3]
                price = float(parts[4])
                qty = int(parts[5])
                kws = parts[6:][:5]
                resp = client.call(
                    "RegisterItemForSale",
                    {"item_name": name, "item_category": cat, "condition": cond, "sale_price": price, "quantity": qty, "keywords": kws},
                    session_id=session_id,
                    role="seller",
                )
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "change_price":
                item_id = parse_item_id(parts[1])
                new_price = float(parts[2])
                resp = client.call("ChangeItemPrice", {"item_id": item_id, "new_price": new_price}, session_id=session_id, role="seller")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "update_units":
                item_id = parse_item_id(parts[1])
                remove_qty = int(parts[2])
                resp = client.call("UpdateUnitsForSale", {"item_id": item_id, "remove_quantity": remove_qty}, session_id=session_id, role="seller")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "display_items":
                resp = client.call("DisplayItemsForSale", {}, session_id=session_id, role="seller")
                print(json.dumps(resp, indent=2))
                continue

            print("Unknown command. Type 'help'.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
