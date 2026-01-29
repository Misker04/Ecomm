from __future__ import annotations

import secrets
from typing import Dict, Any


def new_session_id() -> str:
    # 24 bytes -> 32-ish chars urlsafe
    return "sess_" + secrets.token_urlsafe(24)


def item_id_to_str(item_id: Dict[str, Any]) -> str:
    # item_id is {"category": int, "id": int}
    return f'{int(item_id["category"])}:{int(item_id["id"])}'


def str_to_item_id(s: str) -> Dict[str, int]:
    cat, iid = s.split(":")
    return {"category": int(cat), "id": int(iid)}
