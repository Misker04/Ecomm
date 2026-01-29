from __future__ import annotations

import argparse
import socket
import threading
from typing import Tuple

from ..common.config import load_config, get_endpoint
from ..common.logging_utils import setup_logging
from ..common.protocol import recv_json, send_json, safe_handle
from .store import ProductStore
from .handlers import ProductHandlers


logger = setup_logging("product_db")


def client_thread(conn: socket.socket, addr: Tuple[str, int], handlers: ProductHandlers) -> None:
    try:
        while True:
            req = recv_json(conn)
            resp = safe_handle(handlers.handle, req)
            send_json(conn, resp)
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def serve(host: str, port: int, store: ProductStore) -> None:
    handlers = ProductHandlers(store)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(512)
        logger.info(f"Product DB listening on {host}:{port}")
        while True:
            conn, addr = s.accept()
            conn.settimeout(None)
            t = threading.Thread(target=client_thread, args=(conn, addr, handlers), daemon=True)
            t.start()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    ep = get_endpoint(cfg.product_db)
    store = ProductStore(data_path=str(cfg.product_db["data_path"]))
    serve(ep.host, ep.port, store)


if __name__ == "__main__":
    main()
