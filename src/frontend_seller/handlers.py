from __future__ import annotations

from typing import Dict, Any

from ..common.protocol import make_ok, make_err, RpcClient
from ..common.errors import Err, BAD_REQUEST, UNAUTHORIZED


class SellerFrontendHandlers:
    """
    Stateless frontend: validates session via CustomerDB on every authenticated request.
    """

    def __init__(self, customer_host: str, customer_port: int, product_host: str, product_port: int):
        self.customer = RpcClient(customer_host, customer_port)
        self.product = RpcClient(product_host, product_port)

    def _validate(self, request_id: str, session_id: str) -> Dict[str, Any]:
        return self.customer.call("ValidateAndTouchSession", {"request_id": request_id, "session_id": session_id}, role=None)

    def handle(self, req: Dict[str, Any]) -> Dict[str, Any]:
        api = req.get("api")
        request_id = str(req.get("request_id", "req"))
        payload = req.get("payload") or {}

        # Unauthenticated
        if api == "CreateAccount":
            return self.customer.call("CreateAccount", {"request_id": request_id, **payload}, role="seller")
        if api == "Login":
            return self.customer.call("Login", {"request_id": request_id, **payload}, role="seller")

        # Auth required
        session_id = str(req.get("session_id") or payload.get("session_id") or "")
        if not session_id:
            return make_err(request_id, Err(BAD_REQUEST, "session_id required"))
        v = self._validate(request_id, session_id)
        if not v.get("ok", False):
            return v
        data = v["data"]
        if data["user_type"] != "seller":
            return make_err(request_id, Err(UNAUTHORIZED, "Session is not a seller session."))
        seller_id = int(data["user_id"])

        if api == "Logout":
            return self.customer.call("Logout", {"request_id": request_id, "session_id": session_id}, role=None)

        if api == "GetSellerRating":
            return self.customer.call("GetSellerRating", {"request_id": request_id, "session_id": session_id}, role=None)

        if api == "RegisterItemForSale":
            p = {"request_id": request_id, "seller_id": seller_id, **payload}
            return self.product.call("RegisterItemForSale", p, role=None)

        if api == "ChangeItemPrice":
            p = {"request_id": request_id, "seller_id": seller_id, **payload}
            return self.product.call("ChangeItemPrice", p, role=None)

        if api == "UpdateUnitsForSale":
            p = {"request_id": request_id, "seller_id": seller_id, **payload}
            return self.product.call("UpdateUnitsForSale", p, role=None)

        if api == "DisplayItemsForSale":
            p = {"request_id": request_id, "seller_id": seller_id}
            return self.product.call("DisplayItemsForSale", p, role=None)

        return make_err(request_id, Err(BAD_REQUEST, f"Unknown API: {api}"))
