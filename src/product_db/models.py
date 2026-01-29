from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List, Literal


@dataclass
class Feedback:
    thumbs_up: int = 0
    thumbs_down: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {"thumbs_up": self.thumbs_up, "thumbs_down": self.thumbs_down}


@dataclass
class Item:
    category: int
    id: int
    item_name: str
    keywords: List[str]
    condition: Literal["New", "Used"]
    sale_price: float
    quantity: int
    seller_id: int
    feedback: Feedback

    def item_id(self) -> Dict[str, int]:
        return {"category": self.category, "id": self.id}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id(),
            "item_name": self.item_name,
            "item_category": self.category,
            "keywords": list(self.keywords),
            "condition": self.condition,
            "sale_price": self.sale_price,
            "quantity": self.quantity,
            "seller_id": self.seller_id,
            "feedback": self.feedback.to_dict(),
        }


@dataclass
class Cart:
    buyer_id: int
    items: Dict[str, int]  # item_id_str -> qty
    saved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"buyer_id": self.buyer_id, "items": dict(self.items), "saved": self.saved}
