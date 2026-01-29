from __future__ import annotations

import json
import os
import threading
from typing import Dict, Any, List, Tuple, Optional, Literal

from .models import Item, Feedback, Cart
from ..common.ids import item_id_to_str

import uuid
import time
from pathlib import Path


class ProductStore:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self._lock = threading.RLock()

        # items_by_key: "cat:id" -> Item
        self.items_by_key: Dict[str, Item] = {}
        self.next_item_seq_by_cat: Dict[int, int] = {}  # category -> next int id

        # carts by buyer_id
        self.carts: Dict[int, Cart] = {}

        self._load()

    def _load(self) -> None:
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            return

        with self._lock:
            self.next_item_seq_by_cat = {int(k): int(v) for k, v in raw.get("next_item_seq_by_cat", {}).items()}
            for it in raw.get("items", []):
                fb = it.get("feedback", {})
                item_id = it["item_id"]
                key = item_id_to_str(item_id)
                self.items_by_key[key] = Item(
                    category=int(item_id["category"]),
                    id=int(item_id["id"]),
                    item_name=str(it["item_name"]),
                    keywords=[str(x) for x in it.get("keywords", [])],
                    condition=str(it["condition"]),
                    sale_price=float(it["sale_price"]),
                    quantity=int(it["quantity"]),
                    seller_id=int(it["seller_id"]),
                    feedback=Feedback(int(fb.get("thumbs_up", 0)), int(fb.get("thumbs_down", 0))),
                )
            for c in raw.get("carts", []):
                cart = Cart(
                    buyer_id=int(c["buyer_id"]),
                    items={str(k): int(v) for k, v in c.get("items", {}).items()},
                    saved=bool(c.get("saved", False)),
                )
                self.carts[cart.buyer_id] = cart
                
    def _replace_with_retry(self, src_tmp: str, dst: str, retries: int = 30, delay_s: float = 0.02) -> None:
        # Force types in case something passed as string
        retries = int(retries)
        delay_s = float(delay_s)

        last_err: Exception | None = None
        for _ in range(retries):
            try:
                os.replace(src_tmp, dst)
                return
            except PermissionError as e:
                last_err = e
                time.sleep(delay_s)
        if last_err:
            raise last_err


    def _save(self) -> None:
        with self._lock:
            raw = {
                "next_item_seq_by_cat": {str(k): int(v) for k, v in self.next_item_seq_by_cat.items()},
                "items": [it.to_dict() for it in self.items_by_key.values()],
                "carts": [c.to_dict() for c in self.carts.values()],
            }

            tmp = f"{self.data_path}.{uuid.uuid4().hex}.tmp"
            os.makedirs(os.path.dirname(self.data_path) or ".", exist_ok=True)

            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)
                
            self._replace_with_retry(tmp, self.data_path)

            # os.replace(tmp, self.data_path)


    def register_item(
        self,
        seller_id: int,
        item_name: str,
        category: int,
        keywords: List[str],
        condition: Literal["New", "Used"],
        sale_price: float,
        quantity: int,
    ) -> Dict[str, int]:
        if len(item_name) > 32:
            raise ValueError("item_name exceeds 32 characters")
        if len(keywords) > 5:
            raise ValueError("at most 5 keywords allowed")
        for kw in keywords:
            if len(kw) > 8:
                raise ValueError("keyword exceeds 8 characters")
        if condition not in ("New", "Used"):
            raise ValueError("condition must be New or Used")
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        with self._lock:
            seq = self.next_item_seq_by_cat.get(category, 1)
            self.next_item_seq_by_cat[category] = seq + 1
            item = Item(
                category=category,
                id=seq,
                item_name=item_name,
                keywords=keywords,
                condition=condition,
                sale_price=float(sale_price),
                quantity=int(quantity),
                seller_id=int(seller_id),
                feedback=Feedback(0, 0),
            )
            self.items_by_key[item_id_to_str(item.item_id())] = item
            self._save()
            return item.item_id()

    def get_item(self, item_id: Dict[str, int]) -> Item:
        key = item_id_to_str(item_id)
        with self._lock:
            it = self.items_by_key.get(key)
            if not it:
                raise ValueError("item not found")
            return it

    def change_price(self, seller_id: int, item_id: Dict[str, int], new_price: float) -> None:
        key = item_id_to_str(item_id)
        with self._lock:
            it = self.items_by_key.get(key)
            if not it:
                raise ValueError("item not found")
            if it.seller_id != seller_id:
                raise ValueError("forbidden: not item owner")
            it.sale_price = float(new_price)
            self._save()

    def update_units_remove(self, seller_id: int, item_id: Dict[str, int], remove_qty: int) -> int:
        key = item_id_to_str(item_id)
        with self._lock:
            it = self.items_by_key.get(key)
            if not it:
                raise ValueError("item not found")
            if it.seller_id != seller_id:
                raise ValueError("forbidden: not item owner")
            if remove_qty < 0:
                raise ValueError("remove_quantity must be non-negative")
            if remove_qty > it.quantity:
                raise ValueError("cannot remove more than available quantity")
            it.quantity -= int(remove_qty)
            self._save()
            return it.quantity

    def display_items_for_seller(self, seller_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            items = [it.to_dict() for it in self.items_by_key.values() if it.seller_id == seller_id]
            items.sort(key=lambda x: (x["item_id"]["category"], x["item_id"]["id"]))
            return items

    def search(self, category: int, keywords: List[str]) -> Tuple[List[Dict[str, Any]], str]:
        """
        Semantics:
        - category must match, quantity>0
        - score = count of query keywords that exactly match an item keyword (case-insensitive)
        - if no keywords, score is 0 and all items in category returned
        - sort by score desc, net_feedback desc, price asc, item_id asc
        """
        q = [k.strip() for k in keywords if k.strip()]
        q_lower = [k.lower() for k in q]
        with self._lock:
            candidates = []
            for it in self.items_by_key.values():
                if it.category != category or it.quantity <= 0:
                    continue
                it_kw = [kw.lower() for kw in it.keywords]
                score = 0
                if q_lower:
                    score = sum(1 for k in q_lower if k in it_kw)
                    if score == 0:
                        continue
                net_fb = it.feedback.thumbs_up - it.feedback.thumbs_down
                candidates.append((score, net_fb, it.sale_price, it.category, it.id, it))

            candidates.sort(key=lambda t: (-t[0], -t[1], t[2], t[3], t[4]))
            items = []
            for score, _, _, _, _, it in candidates:
                d = it.to_dict()
                d["score"] = score
                items.append(d)

        semantics = "category match + score=#keyword exact matches (case-insensitive); quantity>0; sorted by score desc then net_feedback desc then price asc then item_id asc; if no keywords, returns all in category"
        return items, semantics

    def provide_item_feedback(self, item_id: Dict[str, int], vote: Literal["up", "down"]) -> Tuple[int, int, int]:
        key = item_id_to_str(item_id)
        with self._lock:
            it = self.items_by_key.get(key)
            if not it:
                raise ValueError("item not found")
            if vote == "up":
                it.feedback.thumbs_up += 1
            else:
                it.feedback.thumbs_down += 1
            self._save()
            return it.feedback.thumbs_up, it.feedback.thumbs_down, it.seller_id

    def _get_or_create_cart(self, buyer_id: int) -> Cart:
        c = self.carts.get(buyer_id)
        if not c:
            c = Cart(buyer_id=buyer_id, items={}, saved=False)
            self.carts[buyer_id] = c
        return c

    def add_to_cart(self, buyer_id: int, item_id: Dict[str, int], qty: int) -> int:
        if qty <= 0:
            raise ValueError("quantity must be > 0")
        key = item_id_to_str(item_id)
        with self._lock:
            it = self.items_by_key.get(key)
            if not it:
                raise ValueError("item not found")
            if it.quantity <= 0:
                raise ValueError("item unavailable")
            cart = self._get_or_create_cart(buyer_id)
            cart.saved = False  # modifying cart makes it unsaved until SaveCart
            cart.items[key] = cart.items.get(key, 0) + int(qty)
            self._save()
            return len(cart.items)

    def remove_from_cart(self, buyer_id: int, item_id: Dict[str, int], qty: int) -> int:
        if qty <= 0:
            raise ValueError("quantity must be > 0")
        key = item_id_to_str(item_id)
        with self._lock:
            cart = self._get_or_create_cart(buyer_id)
            if key not in cart.items:
                raise ValueError("item not in cart")
            if qty > cart.items[key]:
                raise ValueError("cannot remove more than in cart")
            cart.saved = False
            cart.items[key] -= int(qty)
            if cart.items[key] == 0:
                del cart.items[key]
            self._save()
            return len(cart.items)

    def save_cart(self, buyer_id: int) -> None:
        with self._lock:
            cart = self._get_or_create_cart(buyer_id)
            cart.saved = True
            self._save()

    def clear_cart(self, buyer_id: int) -> None:
        with self._lock:
            cart = self._get_or_create_cart(buyer_id)
            cart.items = {}
            cart.saved = False
            self._save()

    def display_cart(self, buyer_id: int) -> List[Dict[str, Any]]:
        with self._lock:
            cart = self._get_or_create_cart(buyer_id)
            out = []
            for key, qty in cart.items.items():
                cat, iid = key.split(":")
                out.append({"item_id": {"category": int(cat), "id": int(iid)}, "quantity": int(qty)})
            out.sort(key=lambda x: (x["item_id"]["category"], x["item_id"]["id"]))
            return out

    def logout_cleanup(self, buyer_id: int) -> None:
        """
        Clears cart on logout unless saved.
        Called by Buyer Frontend on Logout.
        """
        with self._lock:
            cart = self._get_or_create_cart(buyer_id)
            if not cart.saved:
                cart.items = {}
                cart.saved = False
                self._save()
