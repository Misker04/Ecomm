from __future__ import annotations

import json
import threading
from typing import Dict, Any, Optional, Tuple, Literal

from .models import Buyer, Seller, Session, Feedback
from ..common.ids import new_session_id
from ..common.time_utils import now_s

import os
import uuid
import time
from pathlib import Path



class CustomerStore:
    def __init__(self, data_path: str, session_timeout_s: int):
        self.data_path = data_path
        self.session_timeout_s = session_timeout_s

        self._lock = threading.RLock()
        self._next_seller_id = 1
        self._next_buyer_id = 1

        self.sellers_by_id: Dict[int, Seller] = {}
        self.buyers_by_id: Dict[int, Buyer] = {}
        self.seller_by_username: Dict[str, int] = {}
        self.buyer_by_username: Dict[str, int] = {}

        self.sessions: Dict[str, Session] = {}

        self._load()

    def _load(self) -> None:
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            return

        with self._lock:
            self._next_seller_id = int(raw.get("next_seller_id", 1))
            self._next_buyer_id = int(raw.get("next_buyer_id", 1))

            for s in raw.get("sellers", []):
                fb = s.get("feedback", {})
                seller = Seller(
                    seller_id=int(s["seller_id"]),
                    seller_name=str(s["seller_name"]),
                    username=str(s["username"]),
                    password=str(s["password"]),
                    feedback=Feedback(int(fb.get("thumbs_up", 0)), int(fb.get("thumbs_down", 0))),
                    items_sold=int(s.get("items_sold", 0)),
                )
                self.sellers_by_id[seller.seller_id] = seller
                self.seller_by_username[seller.username] = seller.seller_id

            for b in raw.get("buyers", []):
                buyer = Buyer(
                    buyer_id=int(b["buyer_id"]),
                    buyer_name=str(b["buyer_name"]),
                    username=str(b["username"]),
                    password=str(b["password"]),
                    num_purchased=int(b.get("num_purchased", 0)),
                )
                self.buyers_by_id[buyer.buyer_id] = buyer
                self.buyer_by_username[buyer.username] = buyer.buyer_id

            for ss in raw.get("sessions", []):
                sess = Session(
                    session_id=str(ss["session_id"]),
                    user_type=str(ss["user_type"]),
                    user_id=int(ss["user_id"]),
                    last_activity_s=float(ss["last_activity_s"]),
                    active=bool(ss.get("active", True)),
                )
                self.sessions[sess.session_id] = sess

    def _save(self) -> None:
        with self._lock:
            raw = {
                "next_seller_id": self._next_seller_id,
                "next_buyer_id": self._next_buyer_id,
                "sellers": [s.to_dict() for s in self.sellers_by_id.values()],
                "buyers": [b.to_dict() for b in self.buyers_by_id.values()],
                "sessions": [s.to_dict() for s in self.sessions.values()],
            }

            # Unique temp file avoids Windows collisions/locks
            tmp = f"{self.data_path}.{uuid.uuid4().hex}.tmp"
            os.makedirs(os.path.dirname(self.data_path) or ".", exist_ok=True)

            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)

            self._replace_with_retry(tmp, self.data_path)

            # Atomic-ish replace on same filesystem
            # os.replace(tmp, self.data_path)


    def create_seller(self, seller_name: str, username: str, password: str) -> int:
        if len(seller_name) > 32:
            raise ValueError("seller_name exceeds 32 characters")
        with self._lock:
            if username in self.seller_by_username or username in self.buyer_by_username:
                raise ValueError("username already exists")
            seller_id = self._next_seller_id
            self._next_seller_id += 1
            seller = Seller(seller_id, seller_name, username, password, Feedback(0, 0), items_sold=0)
            self.sellers_by_id[seller_id] = seller
            self.seller_by_username[username] = seller_id
            self._save()
            return seller_id

    def create_buyer(self, buyer_name: str, username: str, password: str) -> int:
        if len(buyer_name) > 32:
            raise ValueError("buyer_name exceeds 32 characters")
        with self._lock:
            if username in self.buyer_by_username or username in self.seller_by_username:
                raise ValueError("username already exists")
            buyer_id = self._next_buyer_id
            self._next_buyer_id += 1
            buyer = Buyer(buyer_id, buyer_name, username, password, num_purchased=0)
            self.buyers_by_id[buyer_id] = buyer
            self.buyer_by_username[username] = buyer_id
            self._save()
            return buyer_id

    def login(self, user_type: Literal["buyer", "seller"], username: str, password: str) -> Tuple[str, int]:
        with self._lock:
            if user_type == "seller":
                sid = self.seller_by_username.get(username)
                if sid is None:
                    raise ValueError("unknown username")
                seller = self.sellers_by_id[sid]
                if seller.password != password:
                    raise ValueError("invalid password")
                user_id = seller.seller_id
            else:
                bid = self.buyer_by_username.get(username)
                if bid is None:
                    raise ValueError("unknown username")
                buyer = self.buyers_by_id[bid]
                if buyer.password != password:
                    raise ValueError("invalid password")
                user_id = buyer.buyer_id

            session_id = new_session_id()
            sess = Session(session_id=session_id, user_type=user_type, user_id=user_id, last_activity_s=now_s(), active=True)
            self.sessions[session_id] = sess
            self._save()
            return session_id, user_id

    def logout(self, session_id: str) -> bool:
        with self._lock:
            sess = self.sessions.get(session_id)
            if not sess or not sess.active:
                return False
            sess.active = False
            self._save()
            return True
        
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


    def validate_and_touch(self, session_id: str) -> Tuple[bool, Optional[str], Optional[int], Optional[int]]:
        """
        Returns (valid, user_type, user_id, expires_in_seconds)
        If invalid/expired, valid=False and user_type/user_id may still be returned when known.
        """
        with self._lock:
            sess = self.sessions.get(session_id)
            if not sess or not sess.active:
                return False, None, None, None
            now = now_s()
            idle = now - sess.last_activity_s
            if idle >= self.session_timeout_s:
                # expire
                sess.active = False
                self._save()
                return False, sess.user_type, sess.user_id, 0
            sess.last_activity_s = now
            expires_in = int(self.session_timeout_s - idle)
            self._save()
            return True, sess.user_type, sess.user_id, expires_in

    def get_seller_rating(self, seller_id: int) -> Tuple[int, int]:
        with self._lock:
            seller = self.sellers_by_id.get(seller_id)
            if not seller:
                raise ValueError("seller not found")
            return seller.feedback.thumbs_up, seller.feedback.thumbs_down

    def update_seller_feedback(self, seller_id: int, vote: Literal["up", "down"]) -> Tuple[int, int]:
        with self._lock:
            seller = self.sellers_by_id.get(seller_id)
            if not seller:
                raise ValueError("seller not found")
            if vote == "up":
                seller.feedback.thumbs_up += 1
            else:
                seller.feedback.thumbs_down += 1
            self._save()
            return seller.feedback.thumbs_up, seller.feedback.thumbs_down

    def get_user_id_from_session(self, session_id: str, expected: Literal["buyer", "seller"]) -> int:
        valid, user_type, user_id, _ = self.validate_and_touch(session_id)
        if not valid or user_type != expected or user_id is None:
            raise ValueError("invalid session")
        return user_id
