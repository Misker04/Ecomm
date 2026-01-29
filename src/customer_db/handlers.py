from __future__ import annotations

from typing import Dict, Any

from .store import CustomerStore
from ..common.protocol import make_ok, make_err
from ..common.errors import Err, BAD_REQUEST, UNAUTHORIZED, SESSION_EXPIRED


class CustomerHandlers:
    def __init__(self, store: CustomerStore):
        self.store = store

    def handle(self, req: Dict[str, Any]) -> Dict[str, Any]:
        api = req.get("api")
        request_id = str(req.get("request_id", "req"))
        payload = req.get("payload") or {}

        if api == "CreateAccount":
            role = req.get("role")
            if role == "seller":
                seller_id = self.store.create_seller(
                    seller_name=str(payload.get("seller_name", "")),
                    username=str(payload.get("username", "")),
                    password=str(payload.get("password", "")),
                )
                return make_ok(request_id, {"seller_id": seller_id})
            elif role == "buyer":
                buyer_id = self.store.create_buyer(
                    buyer_name=str(payload.get("buyer_name", "")),
                    username=str(payload.get("username", "")),
                    password=str(payload.get("password", "")),
                )
                return make_ok(request_id, {"buyer_id": buyer_id})
            return make_err(request_id, Err(BAD_REQUEST, "role must be buyer or seller"))

        if api == "Login":
            role = req.get("role")
            if role not in ("buyer", "seller"):
                return make_err(request_id, Err(BAD_REQUEST, "role must be buyer or seller"))
            session_id, user_id = self.store.login(role, str(payload.get("username", "")), str(payload.get("password", "")))
            key = "buyer_id" if role == "buyer" else "seller_id"
            return make_ok(request_id, {"session_id": session_id, key: user_id})

        if api == "Logout":
            session_id = str(req.get("session_id") or payload.get("session_id") or "")
            if not session_id:
                return make_err(request_id, Err(BAD_REQUEST, "session_id required"))
            ok = self.store.logout(session_id)
            return make_ok(request_id, {"logged_out": ok})

        if api == "ValidateAndTouchSession":
            session_id = str(payload.get("session_id") or "")
            if not session_id:
                return make_err(request_id, Err(BAD_REQUEST, "session_id required"))
            valid, user_type, user_id, expires_in = self.store.validate_and_touch(session_id)
            if not valid:
                # if we know it expired, tell caller so
                if user_type and user_id is not None:
                    return make_err(request_id, Err(SESSION_EXPIRED, "Session expired after 5 minutes of inactivity.", {"user_type": user_type, "user_id": user_id}))
                return make_err(request_id, Err(UNAUTHORIZED, "Invalid session."))
            return make_ok(request_id, {"valid": True, "user_type": user_type, "user_id": user_id, "expires_in_seconds": expires_in})

        if api == "GetSellerRating":
            # can be by session or by seller_id
            if "seller_id" in payload:
                seller_id = int(payload["seller_id"])
            else:
                session_id = str(payload.get("session_id") or req.get("session_id") or "")
                if not session_id:
                    return make_err(request_id, Err(BAD_REQUEST, "session_id required"))
                try:
                    seller_id = self.store.get_user_id_from_session(session_id, "seller")
                except ValueError:
                    return make_err(request_id, Err(UNAUTHORIZED, "Invalid session"))
            up, down = self.store.get_seller_rating(seller_id)
            return make_ok(request_id, {"seller_id": seller_id, "thumbs_up": up, "thumbs_down": down})

        if api == "UpdateSellerFeedback":
            seller_id = int(payload.get("seller_id", -1))
            vote = str(payload.get("vote", ""))
            if vote not in ("up", "down"):
                return make_err(request_id, Err(BAD_REQUEST, "vote must be up or down"))
            up, down = self.store.update_seller_feedback(seller_id, vote)
            return make_ok(request_id, {"seller_id": seller_id, "thumbs_up": up, "thumbs_down": down})

        if api == "GetBuyerPurchases":
            # MakePurchase not required, so purchases are empty in PA1
            session_id = str(req.get("session_id") or payload.get("session_id") or "")
            if not session_id:
                return make_err(request_id, Err(BAD_REQUEST, "session_id required"))
            try:
                _ = self.store.get_user_id_from_session(session_id, "buyer")
            except ValueError:
                return make_err(request_id, Err(UNAUTHORIZED, "Invalid session"))
            return make_ok(request_id, {"purchases": [], "note": "MakePurchase not implemented in assignment 1, so purchase history remains empty."})

        return make_err(request_id, Err(BAD_REQUEST, f"Unknown API: {api}"))
