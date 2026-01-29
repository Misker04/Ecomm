from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class Err:
    code: str
    message: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


# Common error codes
BAD_REQUEST = "BAD_REQUEST"
UNAUTHORIZED = "UNAUTHORIZED"
SESSION_EXPIRED = "SESSION_EXPIRED"
NOT_FOUND = "NOT_FOUND"
CONFLICT = "CONFLICT"
FORBIDDEN = "FORBIDDEN"
INTERNAL = "INTERNAL"
