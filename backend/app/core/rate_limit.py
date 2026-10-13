"""Sliding-window rate limiter.

Kept in process memory: correct for the single API process this project runs. When the API is
scaled to several processes, swap `_store` for a shared store (Redis) — the interface stays the same."""

import threading
import time
from collections import defaultdict, deque

from app.core.errors import RateLimitError


class RateLimiter:
    def __init__(self) -> None:
        self._store: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._store[key]
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                raise RateLimitError("Te veel pogingen. Wacht even en probeer het opnieuw.")
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._store.clear()


rate_limiter = RateLimiter()
