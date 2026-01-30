from __future__ import annotations

import random
from typing import List, Dict, Any, Tuple
import time

from ...common.protocol import RpcClient


def _seller_username(i: int) -> str:
    return f"seller{i}"


def _buyer_username(i: int) -> str:
    return f"buyer{i}"


def setup_sellers(seller_client: RpcClient, n: int, items_per_seller: int, category: int = 1) -> List[Dict[str, Any]]:
    """
    Returns list of dicts: {"seller_id": int, "session_id": str, "item_ids": [item_id,...]}
    """
    sellers = []
    for i in range(n):
        if i % 20 == 0 and i > 0:
            time.sleep(0.05)
        seller_name = f"Seller{i}"
        username = _seller_username(i)
        password = "pw"
        # create (ignore if already exists)
        _ = seller_client.call("CreateAccount", {"seller_name": seller_name, "username": username, "password": password}, role="seller")
        login = seller_client.call("Login", {"username": username, "password": password}, role="seller")
        if not login.get("ok"):
            raise RuntimeError(f"Seller login failed: {login}")
        sess = login["data"]["session_id"]
        sid = login["data"]["seller_id"]

        item_ids = []
        for j in range(items_per_seller):
            name = f"item{i}_{j}"[:32]
            kws = [f"s{sid}"[:8], "common"[:8], f"it{j}"[:8]]
            reg = seller_client.call(
                "RegisterItemForSale",
                {"item_name": name, "item_category": category, "condition": "New", "sale_price": 10.0, "quantity": 100, "keywords": kws},
                session_id=sess,
                role="seller",
            )
            if reg.get("ok"):
                item_ids.append(reg["data"]["item_id"])
        sellers.append({"seller_id": sid, "session_id": sess, "item_ids": item_ids})
    return sellers


def setup_buyers(buyer_client: RpcClient, n: int) -> List[Dict[str, Any]]:
    buyers = []
    for i in range(n):
        if i % 20 == 0 and i > 0:
            time.sleep(0.05)
        buyer_name = f"Buyer{i}"
        username = _buyer_username(i)
        password = "pw"
        _ = buyer_client.call("CreateAccount", {"buyer_name": buyer_name, "username": username, "password": password}, role="buyer")
        login = buyer_client.call("Login", {"username": username, "password": password}, role="buyer")
        if not login.get("ok"):
            raise RuntimeError(f"Buyer login failed: {login}")
        buyers.append({"buyer_id": login["data"]["buyer_id"], "session_id": login["data"]["session_id"]})
    return buyers


def seller_1000_ops(client: RpcClient, session_id: str, item_ids: List[Dict[str, int]]) -> None:
    # 250 * 4 = 1000 ops
    if not item_ids:
        # still do rating + display
        for _ in range(500):
            client.call("GetSellerRating", {}, session_id=session_id, role="seller")
            client.call("DisplayItemsForSale", {}, session_id=session_id, role="seller")
        return
    for t in range(250):
        client.call("GetSellerRating", {}, session_id=session_id, role="seller")
        client.call("DisplayItemsForSale", {}, session_id=session_id, role="seller")
        it1 = item_ids[t % len(item_ids)]
        it2 = item_ids[(t + 1) % len(item_ids)]
        price1 = 9.99 if (t % 2 == 0) else 10.99
        price2 = 10.49 if (t % 2 == 0) else 9.49
        client.call("ChangeItemPrice", {"item_id": it1, "new_price": price1}, session_id=session_id, role="seller")
        client.call("ChangeItemPrice", {"item_id": it2, "new_price": price2}, session_id=session_id, role="seller")


def buyer_1000_ops(client: RpcClient, session_id: str, category: int = 1, pick_index: int = 0) -> None:
    # 200 * 5 = 1000 ops
    for t in range(200):
        sr = client.call("SearchItemsForSale", {"item_category": category, "keywords": ["common"]}, session_id=session_id, role="buyer")
        if not sr.get("ok") or not sr["data"]["items"]:
            continue
        items = sr["data"]["items"]
        it = items[pick_index % len(items)]["item_id"]
        client.call("GetItem", {"item_id": it}, session_id=session_id, role="buyer")
        client.call("AddItemToCart", {"item_id": it, "quantity": 1}, session_id=session_id, role="buyer")
        client.call("RemoveItemFromCart", {"item_id": it, "quantity": 1}, session_id=session_id, role="buyer")
        vote = "up" if (t % 2 == 0) else "down"
        client.call("ProvideFeedback", {"item_id": it, "vote": vote}, session_id=session_id, role="buyer")
