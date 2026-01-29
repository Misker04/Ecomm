from __future__ import annotations

import time


def now_s() -> float:
    """Wall clock time in seconds."""
    return time.time()


def monotonic_s() -> float:
    """Monotonic time in seconds for measuring durations."""
    return time.monotonic()
