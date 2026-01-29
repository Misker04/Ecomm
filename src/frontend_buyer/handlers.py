from __future__ import annotations

from typing import Dict, Any, Optional

from ..common.protocol import make_ok, make_err, RpcClient
from ..common.errors import Err, BAD_REQUEST, UNAUTHORIZED, SESSION_EXPIRED


class BuyerFrontendHandlers:
    """
    Stateless frontend: does NOT store session/cart/item state.
    Every request requiring auth is validated against CustomerDB (ValidateAndTouchSession).
    All persistent state lives in CustomerDB/ProductDB.
    """

    def __init__(self, customer_host: str, customer_port: int, product_host: str, product_port: int):
        self.customer = RpcClient(customer_host, customer_port)
        self.product = RpcClient(product_host, product_port)

    def _validate(self, request_id: str, session_id: str) -> Dict[str, Any]:
        resp = self.customer.call("ValidateAndTouchSession", {"request_id": request_id, "session_id": session_id}, role=None)
        return resp

    def handle(self, req: Dict[str, Any]) -> Dict[str, Any]:
        api = req.get("api")
        request_id = str(req.get("request_id", "req"))
        payload = req.get("payload") or {}

        # Unauthenticated
        if api == "CreateAccount":
            resp = self.customer.call("CreateAccount", {"request_id": request_id, **payload}, role="buyer")
            return resp
        if api == "Login":
            resp = self.customer.call("Login", {"request_id": request_id, **payload}, role="buyer")
            return resp

        # Auth required
        session_id = str(req.get("session_id") or payload.get("session_id") or "")
        if not session_id:
            return make_err(request_id, Err(BAD_REQUEST, "session_id required"))
        v = self._validate(request_id, session_id)
        if not v.get("ok", False):
            # propagate session errors
            return v
        user = v["data"]
        if user["user_type"] != "buyer":
            return make_err(request_id, Err(UNAUTHORIZED, "Session is not a buyer session."))
        buyer_id = int(user["user_id"])

        if api == "Logout":
            # First logout in CustomerDB
            out = self.customer.call("Logout", {"request_id": request_id, "session_id": session_id}, role=None)
            # Cleanup cart if not saved
            _ = self.product.call("LogoutCleanup", {"request_id": request_id, "buyer_id": buyer_id}, role=None)
            return out

        if api == "SearchItemsForSale":
            resp = self.product.call("SearchItemsForSale", {"request_id": request_id, **payload}, role=None)
            return resp

        if api == "GetItem":
            resp = self.product.call("GetItem", {"request_id": request_id, **payload}, role=None)
            return resp

        if api == "AddItemToCart":
            p = {"request_id": request_id, "buyer_id": buyer_id, **payload}
            resp = self.product.call("AddItemToCart", p, role=None)
            return resp

        if api == "RemoveItemFromCart":
            p = {"request_id": request_id, "buyer_id": buyer_id, **payload}
            resp = self.product.call("RemoveItemFromCart", p, role=None)
            return resp

        if api == "SaveCart":
            resp = self.product.call("SaveCart", {"request_id": request_id, "buyer_id": buyer_id}, role=None)
            return resp

        if api == "ClearCart":
            resp = self.product.call("ClearCart", {"request_id": request_id, "buyer_id": buyer_id}, role=None)
            return resp

        if api == "DisplayCart":
            resp = self.product.call("DisplayCart", {"request_id": request_id, "buyer_id": buyer_id}, role=None)
            return resp

        if api == "ProvideFeedback":
            vote = payload.get("vote")
            if vote not in ("up", "down"):
                return make_err(request_id, Err(BAD_REQUEST, "vote must be up or down"))
            # Update item feedback in ProductDB (returns seller_id)
            r1 = self.product.call("ProvideFeedback", {"request_id": request_id, **payload}, role=None)
            if not r1.get("ok", False):
                return r1
            seller_id = int(r1["data"]["seller_id"])
            # Update seller feedback in CustomerDB
            _ = self.customer.call("UpdateSellerFeedback", {"request_id": request_id, "seller_id": seller_id, "vote": vote}, role=None)
            return r1

        if api == "GetSellerRating":
            # by seller_id
            resp = self.customer.call("GetSellerRating", {"request_id": request_id, **payload}, role=None)
            return resp

        if api == "GetBuyerPurchases":
            resp = self.customer.call("GetBuyerPurchases", {"request_id": request_id, "session_id": session_id}, role=None)
            return resp

        if api == "MakePurchase":
            return make_err(request_id, Err(BAD_REQUEST, "MakePurchase is not implemented in assignment 1."))

        return make_err(request_id, Err(BAD_REQUEST, f"Unknown API: {api}"))
