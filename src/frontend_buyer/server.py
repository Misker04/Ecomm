from __future__ import annotations

import argparse
import socket
import threading
from typing import Tuple

from ..common.config import load_config, get_endpoint, get_nested_endpoint
from ..common.logging_utils import setup_logging
from ..common.protocol import recv_json, send_json, safe_handle
from .handlers import BuyerFrontendHandlers


logger = setup_logging("buyer_frontend")


def client_thread(conn: socket.socket, addr: Tuple[str, int], handlers: BuyerFrontendHandlers) -> None:
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


def serve(host: str, port: int, handlers: BuyerFrontendHandlers) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(512)
        logger.info(f"Buyer Frontend listening on {host}:{port}")
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

    ep = get_endpoint(cfg.buyer_frontend)
    cdb = get_nested_endpoint(cfg.buyer_frontend, "customer_db")
    pdb = get_nested_endpoint(cfg.buyer_frontend, "product_db")

    handlers = BuyerFrontendHandlers(cdb.host, cdb.port, pdb.host, pdb.port)
    serve(ep.host, ep.port, handlers)


if __name__ == "__main__":
    main()
