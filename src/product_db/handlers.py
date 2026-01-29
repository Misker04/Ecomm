from __future__ import annotations

from typing import Dict, Any

from .store import ProductStore
from ..common.protocol import make_ok, make_err
from ..common.errors import Err, BAD_REQUEST


class ProductHandlers:
    def __init__(self, store: ProductStore):
        self.store = store

    def handle(self, req: Dict[str, Any]) -> Dict[str, Any]:
        api = req.get("api")
        request_id = str(req.get("request_id", "req"))
        payload = req.get("payload") or {}

        if api == "RegisterItemForSale":
            item_id = self.store.register_item(
                seller_id=int(payload["seller_id"]),
                item_name=str(payload["item_name"]),
                category=int(payload["item_category"]),
                keywords=[str(k) for k in payload.get("keywords", [])],
                condition=str(payload["condition"]),
                sale_price=float(payload["sale_price"]),
                quantity=int(payload["quantity"]),
            )
            return make_ok(request_id, {"item_id": item_id})

        if api == "ChangeItemPrice":
            self.store.change_price(
                seller_id=int(payload["seller_id"]),
                item_id=dict(payload["item_id"]),
                new_price=float(payload["new_price"]),
            )
            return make_ok(request_id, {"updated": True})

        if api == "UpdateUnitsForSale":
            remaining = self.store.update_units_remove(
                seller_id=int(payload["seller_id"]),
                item_id=dict(payload["item_id"]),
                remove_qty=int(payload["remove_quantity"]),
            )
            return make_ok(request_id, {"updated": True, "remaining_quantity": remaining})

        if api == "DisplayItemsForSale":
            items = self.store.display_items_for_seller(int(payload["seller_id"]))
            return make_ok(request_id, {"items": items})

        if api == "SearchItemsForSale":
            items, semantics = self.store.search(int(payload["item_category"]), [str(k) for k in payload.get("keywords", [])])
            return make_ok(request_id, {"items": items, "semantics": semantics})

        if api == "GetItem":
            it = self.store.get_item(dict(payload["item_id"]))
            return make_ok(request_id, it.to_dict())

        if api == "AddItemToCart":
            sz = self.store.add_to_cart(int(payload["buyer_id"]), dict(payload["item_id"]), int(payload["quantity"]))
            return make_ok(request_id, {"added": True, "cart_size": sz})

        if api == "RemoveItemFromCart":
            sz = self.store.remove_from_cart(int(payload["buyer_id"]), dict(payload["item_id"]), int(payload["quantity"]))
            return make_ok(request_id, {"removed": True, "cart_size": sz})

        if api == "SaveCart":
            self.store.save_cart(int(payload["buyer_id"]))
            return make_ok(request_id, {"saved": True})

        if api == "ClearCart":
            self.store.clear_cart(int(payload["buyer_id"]))
            return make_ok(request_id, {"cleared": True})

        if api == "DisplayCart":
            items = self.store.display_cart(int(payload["buyer_id"]))
            return make_ok(request_id, {"items": items})

        if api == "ProvideFeedback":
            vote = str(payload.get("vote", ""))
            if vote not in ("up", "down"):
                return make_err(request_id, Err(BAD_REQUEST, "vote must be up or down"))
            up, down, seller_id = self.store.provide_item_feedback(dict(payload["item_id"]), vote)
            return make_ok(request_id, {"updated": True, "thumbs_up": up, "thumbs_down": down, "seller_id": seller_id})

        if api == "LogoutCleanup":
            self.store.logout_cleanup(int(payload["buyer_id"]))
            return make_ok(request_id, {"ok": True})

        return make_err(request_id, Err(BAD_REQUEST, f"Unknown API: {api}"))
