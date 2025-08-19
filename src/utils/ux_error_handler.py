"""UX error utilities for GITTE.

- Provides lightweight counters and helpers to track UX-related failures.
- Exposes `get_ux_error_stats()` consumed by the monitoring service.
- Provides a tiny, dependency-free `retry_call` utility (with `RetryConfig`).
- Layering: this module lives in utils and MUST NOT import UI modules.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Deque, Dict, Optional, Tuple, Type, Callable

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Centralized retry defaults (prefer config/config.py, then src/config.py)
# -----------------------------------------------------------------------------
try:
    from config.config import RETRY_DEFAULTS  # preferred location
except Exception:
    try:
        from src.config import RETRY_DEFAULTS  # legacy fallback
    except Exception:
        RETRY_DEFAULTS = {
            "max_retries": 3,
            "initial_backoff": 0.5,
            "max_backoff": 8.0,
            "jitter": 0.1,
            "retry_on": (Exception,),  # narrow in callers where possible
        }

# -----------------------------------------------------------------------------
# Retry helpers
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry/backoff logic."""
    max_retries: int = RETRY_DEFAULTS["max_retries"]
    initial_backoff: float = RETRY_DEFAULTS["initial_backoff"]
    max_backoff: float = RETRY_DEFAULTS["max_backoff"]
    jitter: float = RETRY_DEFAULTS["jitter"]
    retry_on: Tuple[Type[BaseException], ...] = RETRY_DEFAULTS["retry_on"]  # type: ignore[assignment]


def retry_call(fn: Callable[..., Any], *args: Any, cfg: Optional[RetryConfig] = None, **kwargs: Any) -> Any:
    """Execute `fn(*args, **kwargs)` with exponential backoff.

    Keep dependencies minimal to be safe across layers.
    Callers SHOULD pass a narrower `retry_on` tailored to the operation.
    """
    cfg = cfg or RetryConfig()
    attempt = 0
    backoff = cfg.initial_backoff

    while True:
        try:
            return fn(*args, **kwargs)
        except cfg.retry_on as exc:  # type: ignore[misc]
            attempt += 1
            if attempt > cfg.max_retries:
                raise
            sleep_for = min(backoff, cfg.max_backoff) + random.uniform(0, cfg.jitter)
            logger.debug("retry_call attempt=%d sleep=%.2fs exc=%s", attempt, sleep_for, type(exc).__name__)
            time.sleep(sleep_for)
            backoff *= 2

# -----------------------------------------------------------------------------
# Lightweight in-memory UX error tracking
# -----------------------------------------------------------------------------
# NOTE: This is NOT a replacement for structured logging or DB persistence.
# It only provides a low-cost signal used by the monitoring service.
_ux_error_counts: Counter[str] = Counter()
_recent_ux_errors: Deque[Dict[str, Any]] = deque(maxlen=200)
_lock = threading.Lock()

def record_ux_error(kind: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Record a UX-related failure, e.g., 'image_processing', 'prerequisite', 'retry_exhaustion'."""
    ts = datetime.utcnow().isoformat()
    payload = {"kind": kind, "ts": ts, "meta": (metadata or {})}
    with _lock:
        _ux_error_counts[kind] += 1
        _ux_error_counts["total_failures"] += 1
        _recent_ux_errors.append(payload)
    logger.debug("Recorded UX error: %s", payload)

def get_ux_error_stats() -> Dict[str, Any]:
    """Return aggregated counters used by the monitoring service (no heavy computation)."""
    with _lock:
        counts = dict(_ux_error_counts)
        recent = list(_recent_ux_errors)[-10:]
    return {
        "total_failures": counts.get("total_failures", 0),
        "image_processing_failures": counts.get("image_processing", 0),
        "prerequisite_failures": counts.get("prerequisite", 0),
        "retry_exhaustions": counts.get("retry_exhaustion", 0),
        "by_type": {k: v for k, v in counts.items() if k != "total_failures"},
        "recent": recent,
    }

def reset_ux_error_stats() -> None:
    """Reset counters and recent buffer (primarily for tests)."""
    with _lock:
        _ux_error_counts.clear()
        _recent_ux_errors.clear()

__all__ = [
    "RetryConfig", "retry_call",
    "record_ux_error", "get_ux_error_stats", "reset_ux_error_stats",
]
