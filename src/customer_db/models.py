from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, Literal, Optional


@dataclass
class Feedback:
    thumbs_up: int = 0
    thumbs_down: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"thumbs_up": self.thumbs_up, "thumbs_down": self.thumbs_down}


@dataclass
class Seller:
    seller_id: int
    seller_name: str
    username: str
    password: str
    feedback: Feedback
    items_sold: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "seller_id": self.seller_id,
            "seller_name": self.seller_name,
            "username": self.username,
            "password": self.password,
            "feedback": self.feedback.to_dict(),
            "items_sold": self.items_sold,
        }


@dataclass
class Buyer:
    buyer_id: int
    buyer_name: str
    username: str
    password: str
    num_purchased: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_id": self.buyer_id,
            "buyer_name": self.buyer_name,
            "username": self.username,
            "password": self.password,
            "num_purchased": self.num_purchased,
        }


@dataclass
class Session:
    session_id: str
    user_type: Literal["buyer", "seller"]
    user_id: int
    last_activity_s: float
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_type": self.user_type,
            "user_id": self.user_id,
            "last_activity_s": self.last_activity_s,
            "active": self.active,
        }
