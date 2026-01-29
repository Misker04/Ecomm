from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import yaml


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int


@dataclass(frozen=True)
class AppConfig:
    session_timeout_seconds: int
    customer_db: Dict[str, Any]
    product_db: Dict[str, Any]
    buyer_frontend: Dict[str, Any]
    seller_frontend: Dict[str, Any]


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return AppConfig(
        session_timeout_seconds=int(raw.get("session_timeout_seconds", 300)),
        customer_db=dict(raw["customer_db"]),
        product_db=dict(raw["product_db"]),
        buyer_frontend=dict(raw["buyer_frontend"]),
        seller_frontend=dict(raw["seller_frontend"]),
    )


def get_endpoint(obj: Dict[str, Any]) -> Endpoint:
    return Endpoint(host=str(obj["host"]), port=int(obj["port"]))


def get_nested_endpoint(obj: Dict[str, Any], key: str) -> Endpoint:
    return get_endpoint(obj[key])


def opt_nested_endpoint(obj: Dict[str, Any], key: str) -> Optional[Endpoint]:
    if key not in obj:
        return None
    return get_endpoint(obj[key])
