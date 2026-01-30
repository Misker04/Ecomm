from __future__ import annotations

import json
import socket
import struct
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .errors import Err, INTERNAL, BAD_REQUEST


MAX_MSG_BYTES = 8 * 1024 * 1024  # 8MB safety cap


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks = []
    got = 0
    while got < n:
        chunk = sock.recv(n - got)
        if not chunk:
            raise ConnectionError("socket closed")
        chunks.append(chunk)
        got += len(chunk)
    return b"".join(chunks)


def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_MSG_BYTES:
        raise ValueError("message too large")
    header = struct.pack("!I", len(data))
    sock.sendall(header + data)


def recv_json(sock: socket.socket) -> Dict[str, Any]:
    header = _recv_exact(sock, 4)
    (n,) = struct.unpack("!I", header)
    if n <= 0 or n > MAX_MSG_BYTES:
        raise ValueError("invalid message length")
    data = _recv_exact(sock, n)
    return json.loads(data.decode("utf-8"))


def make_ok(request_id: str, data: Any) -> Dict[str, Any]:
    return {"v": 1, "request_id": request_id, "ok": True, "error": None, "data": data}


def make_err(request_id: str, err: Err) -> Dict[str, Any]:
    return {"v": 1, "request_id": request_id, "ok": False, "error": err.to_dict(), "data": None}


def require_fields(payload: Dict[str, Any], fields: Tuple[str, ...]) -> Optional[str]:
    for f in fields:
        if f not in payload:
            return f
    return None


@dataclass
class RpcClient:
    host: str
    port: int
    timeout_s: float = 5.0

    def call(self, api: str, payload: Dict[str, Any], session_id: Optional[str] = None, role: Optional[str] = None) -> Dict[str, Any]:
        req_id = payload.get("request_id", None)  # allow callers to pass, but not required
        request_id = req_id if isinstance(req_id, str) else "req"
        req = {
            "v": 1,
            "request_id": request_id,
            "service": "internal",
            "api": api,
            "role": role,
            "session_id": session_id,
            "payload": payload,
        }
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.settimeout(self.timeout_s)

            # reduce Windows port pain
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # IMPORTANT: avoid TIME_WAIT explosion on Windows for short-lived connections
            # (abortive close)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))

            sock.connect((self.host, self.port))
            send_json(sock, req)
            resp = recv_json(sock)
            return resp
        finally:
            try:
                sock.close()
            except Exception:
                pass

@dataclass
class PersistentRpcClient:
    host: str
    port: int
    timeout_s: float = 30.0

    def __post_init__(self) -> None:
        self._sock: Optional[socket.socket] = None
        self._lock = None  # not needed if used by a single thread

    def connect(self) -> None:
        if self._sock is not None:
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout_s)

        # Client-side options to reduce Windows port pain
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        sock.connect((self.host, self.port))
        self._sock = sock


    def close(self) -> None:
        if self._sock is None:
            return
        try:
            self._sock.close()
        finally:
            self._sock = None

    def call(self, api: str, payload: Dict[str, Any], session_id: Optional[str] = None, role: Optional[str] = None) -> Dict[str, Any]:
        req_id = payload.get("request_id", None)
        request_id = req_id if isinstance(req_id, str) else "req"
        req = {
            "v": 1,
            "request_id": request_id,
            "service": "internal",
            "api": api,
            "role": role,
            "session_id": session_id,
            "payload": payload,
        }
        if self._sock is None:
            self.connect()
        assert self._sock is not None

        try:
            send_json(self._sock, req)
            return recv_json(self._sock)
        except (OSError, ConnectionError):
            # one retry with a fresh socket
            self.close()
            self.connect()
            assert self._sock is not None
            send_json(self._sock, req)
            return recv_json(self._sock)



def safe_handle(handler_fn, req: Dict[str, Any]) -> Dict[str, Any]:
    request_id = str(req.get("request_id", "req"))
    try:
        return handler_fn(req)
    except KeyError as e:
        return make_err(request_id, Err(BAD_REQUEST, f"Missing key: {e}"))
    except ValueError as e:
        return make_err(request_id, Err(BAD_REQUEST, str(e)))
    except Exception as e:
        return make_err(request_id, Err(INTERNAL, f"Internal error: {type(e).__name__}: {e}"))
