"""
middleware.py — Cross-cutting HTTP concerns for the API.

  * configure_logging   text or JSON logs, each line tagged with the request ID
  * RateLimiter         in-memory sliding-window limiter, keyed per client IP
  * client_ip           best-effort client address (honours X-Forwarded-For
                        only when uvicorn runs with --proxy-headers)
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import threading
import time
from collections import defaultdict, deque

from fastapi import Request

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestIdFilter())
    if fmt == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  [%(levelname)s]  %(name)s [%(request_id)s] — %(message)s",
            datefmt="%H:%M:%S",
        ))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "urllib3", "primp", "curl_cffi"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Sliding-window limiter. Per-process: with N workers the effective limit is N×.

    For multi-instance deployments put a shared limiter (e.g. Redis or the
    API gateway) in front instead.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._last_sweep = time.monotonic()

    def hit(self, key: str, limit: int) -> float | None:
        """Record a hit. Returns None if allowed, else seconds until retry."""
        if limit <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= limit:
                return max(0.0, self.window - (now - hits[0]))
            hits.append(now)
            self._sweep(now)
        return None

    def _sweep(self, now: float) -> None:
        # Drop idle keys every few minutes so memory stays bounded.
        if now - self._last_sweep < 300:
            return
        self._last_sweep = now
        for key in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]:
            del self._hits[key]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
