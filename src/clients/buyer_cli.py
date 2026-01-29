from __future__ import annotations

import argparse
import json

from ..common.config import load_config, get_endpoint, get_nested_endpoint
from ..common.protocol import RpcClient


HELP = """
Buyer CLI commands:
  help
  create_account <buyer_name> <username> <password>
  login <username> <password>
  logout
  search <category> [kw1 ... kw5]
  get_item <category:id>
  add_to_cart <category:id> <qty>
  remove_from_cart <category:id> <qty>
  save_cart
  clear_cart
  display_cart
  provide_feedback <category:id> up|down
  get_seller_rating <seller_id>
  get_buyer_purchases
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
    bf = get_endpoint(cfg.buyer_frontend)
    client = RpcClient(bf.host, bf.port, timeout_s=10.0)

    session_id = None

    print(HELP.strip())
    while True:
        try:
            line = input("buyer> ").strip()
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
                buyer_name, username, password = parts[1], parts[2], parts[3]
                resp = client.call("CreateAccount", {"buyer_name": buyer_name, "username": username, "password": password}, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "login":
                username, password = parts[1], parts[2]
                resp = client.call("Login", {"username": username, "password": password}, role="buyer")
                print(json.dumps(resp, indent=2))
                if resp.get("ok"):
                    session_id = resp["data"]["session_id"]
                continue

            if cmd == "logout":
                resp = client.call("Logout", {"session_id": session_id}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                session_id = None
                continue

            if cmd == "search":
                category = int(parts[1])
                kws = parts[2:][:5]
                resp = client.call("SearchItemsForSale", {"item_category": category, "keywords": kws}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "get_item":
                item_id = parse_item_id(parts[1])
                resp = client.call("GetItem", {"item_id": item_id}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "add_to_cart":
                item_id = parse_item_id(parts[1])
                qty = int(parts[2])
                resp = client.call("AddItemToCart", {"item_id": item_id, "quantity": qty}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "remove_from_cart":
                item_id = parse_item_id(parts[1])
                qty = int(parts[2])
                resp = client.call("RemoveItemFromCart", {"item_id": item_id, "quantity": qty}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "save_cart":
                resp = client.call("SaveCart", {}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "clear_cart":
                resp = client.call("ClearCart", {}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "display_cart":
                resp = client.call("DisplayCart", {}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "provide_feedback":
                item_id = parse_item_id(parts[1])
                vote = parts[2]
                resp = client.call("ProvideFeedback", {"item_id": item_id, "vote": vote}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "get_seller_rating":
                seller_id = int(parts[1])
                resp = client.call("GetSellerRating", {"seller_id": seller_id}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            if cmd == "get_buyer_purchases":
                resp = client.call("GetBuyerPurchases", {}, session_id=session_id, role="buyer")
                print(json.dumps(resp, indent=2))
                continue

            print("Unknown command. Type 'help'.")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
