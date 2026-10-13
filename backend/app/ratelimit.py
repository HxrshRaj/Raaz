"""Rate limiting. Sliding window in-process by default; a Redis fixed-window counter when RAAZ_REDIS_URL is set."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from .config import get_settings
from .logging_setup import get_logger

log = get_logger("raaz.ratelimit")


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._redis = None
        url = get_settings().redis_url
        if url:
            try:  # pragma: no cover - needs a Redis server
                import redis

                client = redis.Redis.from_url(url, socket_timeout=0.25, socket_connect_timeout=0.25)
                client.ping()
                self._redis = client
            except Exception as e:  # noqa: BLE001
                log.warning("redis unavailable, using in-process rate limiter", extra={"error": str(e)})

    def hit(self, key: str, limit: int, window_s: int = 60) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""
        if self._redis is not None:  # pragma: no cover
            try:
                bucket = int(time.time() // window_s)
                k = f"rl:{key}:{bucket}"
                n = self._redis.incr(k)
                if n == 1:
                    self._redis.expire(k, window_s + 1)
                return (n <= limit, window_s - int(time.time()) % window_s)
            except Exception:  # noqa: BLE001 - fail open on infra error
                return True, 0
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                return False, max(1, int(window_s - (now - q[0])))
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter()
    return _limiter


def reset_limiter() -> None:
    global _limiter
    _limiter = None
