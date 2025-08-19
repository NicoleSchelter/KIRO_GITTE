"""UX error handling utilities (utils layer only).

Provides:
- RetryConfig (config-driven; supports initial_backoff/max_backoff & base_delay/max_delay)
- retry_call(fn, *args, cfg=...) helper
- with_retry decorator (exponential backoff)
- with_image_error_handling decorator (counts image pipeline failures; optional fallback)
- image_error_boundary context manager
- get_ux_error_stats() counters used by ErrorMonitoringService

Notes:
- No UI/Streamlit imports here (respect 4-layer architecture).
- Defaults are centralized in config/config.py (preferred) or src/config.py (fallback).
"""

from __future__ import annotations

import logging
import random
import time
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple, Type

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Load retry defaults from central config and normalize keys
# Supports both styles:
#   - {"initial_backoff", "max_backoff", "retry_on", "jitter"}
#   - {"base_delay", "max_delay", "retryable_exceptions", "jitter"}
# ------------------------------------------------------------------------------
def _load_retry_defaults() -> Dict[str, Any]:
    try:
        from config.config import RETRY_DEFAULTS  # preferred
    except Exception:
        try:
            from src.config import RETRY_DEFAULTS  # legacy fallback
        except Exception:
            RETRY_DEFAULTS = {
                "max_retries": 3,
                "initial_backoff": 0.5,
                "max_backoff": 8.0,
                "jitter": 0.1,  # float jitter in seconds
                "retry_on": (Exception,),  # narrow at call sites
            }

    d = dict(RETRY_DEFAULTS)

    # Normalize alternative keys if present
    if "base_delay" in d and "initial_backoff" not in d:
        d["initial_backoff"] = d["base_delay"]
    if "max_delay" in d and "max_backoff" not in d:
        d["max_backoff"] = d["max_delay"]
    if "retryable_exceptions" in d and "retry_on" not in d:
        d["retry_on"] = d["retryable_exceptions"]

    # Fill any missing keys with sensible defaults
    d.setdefault("max_retries", 3)
    d.setdefault("initial_backoff", 0.5)
    d.setdefault("max_backoff", 8.0)
    d.setdefault("jitter", 0.1)
    d.setdefault("retry_on", (Exception,))
    return d

_RETRY_DEFAULTS = _load_retry_defaults()

# ------------------------------------------------------------------------------
# Lightweight UX counters for monitoring
# ------------------------------------------------------------------------------
_ux_counters: Dict[str, int] = {
    "total_failures": 0,
    "image_processing_failures": 0,
    "prerequisite_failures": 0,
    "retry_exhaustions": 0,
}

def _inc(name: str, by: int = 1) -> None:
    _ux_counters[name] = _ux_counters.get(name, 0) + by
    if name != "total_failures":
        _ux_counters["total_failures"] = _ux_counters.get("total_failures", 0) + by

def record_ux_error(kind: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Increment counters for a given UX error kind (metadata is for future use)."""
    if kind == "image_processing":
        _inc("image_processing_failures")
    elif kind == "prerequisite":
        _inc("prerequisite_failures")
    elif kind == "retry_exhaustion":
        _inc("retry_exhaustions")
    else:
        _inc("total_failures")

def get_ux_error_stats() -> Dict[str, Any]:
    """Return a shallow copy of counters to avoid external mutation."""
    return dict(_ux_counters)

def reset_ux_error_stats() -> None:
    """Reset counters (mainly for tests)."""
    for k in list(_ux_counters.keys()):
        _ux_counters[k] = 0

# ------------------------------------------------------------------------------
# Project image exceptions (import defensively; provide fallbacks)
# ------------------------------------------------------------------------------
try:
    from src.exceptions import (  # type: ignore
        ImageProcessingError,
        PersonDetectionError,
        BackgroundRemovalError,
        PrerequisiteError,
    )
except Exception:
    class ImageProcessingError(Exception): ...
    class PersonDetectionError(ImageProcessingError): ...
    class BackgroundRemovalError(ImageProcessingError): ...
    class PrerequisiteError(Exception): ...

# ------------------------------------------------------------------------------
# Retry primitives (compatible with both key styles)
# ------------------------------------------------------------------------------

@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry/backoff logic.

    Accepts both modern and legacy field names:
      - initial_backoff / max_backoff / retry_on
      - base_delay / max_delay / retryable_exceptions
    """
    # Canonical fields
    max_retries: int = int(_RETRY_DEFAULTS["max_retries"])
    initial_backoff: float = float(_RETRY_DEFAULTS["initial_backoff"])
    max_backoff: float = float(_RETRY_DEFAULTS["max_backoff"])
    jitter: float = float(_RETRY_DEFAULTS["jitter"])
    retry_on: Tuple[Type[BaseException], ...] = _RETRY_DEFAULTS["retry_on"]  # type: ignore[assignment]

    # Compatibility synonyms (optional)
    base_delay: Optional[float] = None
    max_delay: Optional[float] = None
    retryable_exceptions: Optional[Tuple[Type[BaseException], ...]] = None

    def __post_init__(self):
        # Allow legacy synonyms to override canonical fields when provided
        if self.base_delay is not None:
            object.__setattr__(self, "initial_backoff", float(self.base_delay))
        if self.max_delay is not None:
            object.__setattr__(self, "max_backoff", float(self.max_delay))
        if self.retryable_exceptions is not None:
            object.__setattr__(self, "retry_on", tuple(self.retryable_exceptions))

def retry_call(fn: Callable[..., Any], *args: Any, cfg: Optional[RetryConfig] = None, **kwargs: Any) -> Any:
    """Call `fn(*args, **kwargs)` with exponential backoff based on `cfg`."""
    cfg = cfg or RetryConfig()
    attempt = 0
    backoff = max(0.0, cfg.initial_backoff)

    while True:
        try:
            return fn(*args, **kwargs)
        except cfg.retry_on as exc:  # type: ignore[misc]
            attempt += 1
            if attempt > cfg.max_retries:
                _inc("retry_exhaustions")
                logger.warning("retry_call: exhausted retries (attempts=%d) fn=%s exc=%s",
                               attempt - 1, getattr(fn, "__name__", repr(fn)), type(exc).__name__)
                raise
            # compute sleep with jitter (float seconds)
            sleep_for = min(backoff, cfg.max_backoff) + float(cfg.jitter or 0.0)
            logger.debug("retry_call: attempt=%d fn=%s exc=%s → sleeping %.2fs",
                         attempt, getattr(fn, "__name__", repr(fn)), type(exc).__name__, sleep_for)
            time.sleep(max(0.0, sleep_for))
            backoff = min(backoff * 2.0, cfg.max_backoff)

from functools import wraps

def with_retry(
    _fn: Optional[Callable[..., Any]] = None,
    *,
    cfg: Optional[RetryConfig] = None,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker_name: Optional[str] = None,    # accepted, currently a no-op (logged)
    fallback_func: Optional[Callable[..., Any]] = None,
) -> Callable[..., Any]:
    """Decorator adding retries.

    Supports:
      - @with_retry
      - @with_retry(cfg=RetryConfig(...))
      - @with_retry(retry_config=RetryConfig(...), circuit_breaker_name="...", fallback_func=...)

    Behavior:
      - Retries on exceptions in cfg.retry_on.
      - After exhausting retries, increments 'retry_exhaustions' and:
          * if fallback_func is provided -> call it and return result;
          * else re-raise the last retryable exception.
    """
    _cfg = retry_config or cfg or RetryConfig()

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            backoff = max(0.0, _cfg.initial_backoff)
            last_exc: Optional[BaseException] = None

            while attempt <= _cfg.max_retries:
                try:
                    return fn(*args, **kwargs)
                except _cfg.retry_on as exc:  # type: ignore[misc]
                    last_exc = exc
                    attempt += 1
                    if attempt > _cfg.max_retries:
                        _inc("retry_exhaustions")
                        logger.warning(
                            "with_retry: exhausted retries (attempts=%d) fn=%s cb=%s exc=%s",
                            attempt - 1, getattr(fn, "__name__", repr(fn)),
                            circuit_breaker_name, type(exc).__name__,
                        )
                        break
                    sleep_for = min(backoff, _cfg.max_backoff) + float(_cfg.jitter or 0.0)
                    logger.debug(
                        "with_retry: attempt=%d fn=%s exc=%s → sleeping %.2fs",
                        attempt, getattr(fn, "__name__", repr(fn)), type(exc).__name__, sleep_for
                    )
                    time.sleep(max(0.0, sleep_for))
                    backoff = min(backoff * 2.0, _cfg.max_backoff)
                except Exception:
                    # Non-retryable → sofort weiterreichen
                    raise

            # Retries ausgeschöpft
            if fallback_func is not None:
                try:
                    return fallback_func(*args, **kwargs)
                except Exception:
                    if last_exc:
                        raise last_exc
                    raise

            if last_exc:
                raise last_exc
            raise RuntimeError("with_retry: unexpected state without result")
        return _wrapped

    # @with_retry ohne Klammern
    if callable(_fn):
        return _decorator(_fn)
    return _decorator


# ------------------------------------------------------------------------------
# Image-specific error helpers
# ------------------------------------------------------------------------------

@contextmanager
def image_error_boundary(metadata: Optional[Dict[str, Any]] = None):
    """Context manager that records UX 'image_processing' and 'prerequisite' failures."""
    try:
        yield
    except PrerequisiteError as e:
        record_ux_error("prerequisite", {"exc": type(e).__name__, **(metadata or {})})
        logger.warning("image_error_boundary: prerequisite failed: %s (meta=%s)", e, metadata or {})
        raise
    except (ImageProcessingError, BackgroundRemovalError, PersonDetectionError) as e:
        record_ux_error("image_processing", {"exc": type(e).__name__, **(metadata or {})})
        logger.error("image_error_boundary: %s (meta=%s)", type(e).__name__, metadata or {})
        raise

def with_image_error_handling(
    *,
    operation: str = "processing",
    fallback_to_original: bool = True,
    timeout_seconds: Optional[float] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for image pipeline functions; counts failures & can fallback on timeout/errors."""
    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def _wrapped(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = fn(*args, **kwargs)
            except PrerequisiteError as e:
                record_ux_error("prerequisite", {"exc": type(e).__name__, "op": operation})
                logger.warning("with_image_error_handling(%s): prerequisite failed: %s", operation, e)
                raise
            except (ImageProcessingError, BackgroundRemovalError, PersonDetectionError) as e:
                record_ux_error("image_processing", {"exc": type(e).__name__, "op": operation})
                logger.error("with_image_error_handling(%s): %s", operation, type(e).__name__)
                if fallback_to_original:
                    return {
                        "ok": False,
                        "status": "failed",
                        "fallback_used": True,
                        "operation": operation,
                        "error_type": type(e).__name__,
                        "message": str(e),
                    }
                raise

            # soft timeout after successful call
            elapsed = time.time() - start
            if timeout_seconds is not None and elapsed > float(timeout_seconds):
                record_ux_error("image_processing", {"exc": "Timeout", "op": operation})
                logger.error("with_image_error_handling(%s): timeout after %.2fs (limit=%.2fs)", operation, elapsed, timeout_seconds)
                if fallback_to_original:
                    return {
                        "ok": False,
                        "status": "failed",
                        "fallback_used": True,
                        "operation": operation,
                        "error_type": "Timeout",
                        "message": f"Image processing timed out after {int(timeout_seconds)} seconds",
                    }

            return result
        return _wrapped
    return _decorator

# -----------------------------------------------------------------------------
# Append (consolidated): UXErrorHandler + decorators + tooltip-safe helpers
# -----------------------------------------------------------------------------
from functools import wraps
import traceback
from typing import Callable, Optional, Dict, Any, Union

class UXErrorHandler:
    """Centralized UX error handler (framework-agnostic).

    Provides:
      - format_user_message: minimal user-facing message mapping
      - capture_exception: logging + standardized error payload
      - wrap: decorator factory to guard call sites
      - execute_with_retry: convenience wrapper delegating to retry_call
    """

    def __init__(self, logger_=None) -> None:
        self._logger = logger_ or logger

    # ------------------------- user-message mapping -------------------------
    def format_user_message(self, exc: BaseException, context: str) -> str:
        """Return a user-friendly message based on exception type/context."""
        return "An unexpected error occurred."

    # ----------------------------- capture ----------------------------------
    def capture_exception(
        self,
        exc: BaseException,
        context: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Log the exception and return a standardized error payload (dict)."""
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        self._logger.error("[UX] Exception in context '%s': %r\n%s", context, exc, tb)

        # Feed counters for monitoring (best-effort)
        try:
            record_ux_error(context or "unknown", {"exc": type(exc).__name__, **(extra or {})})
        except Exception:
            pass

        payload: Dict[str, Any] = {
            "ok": False,
            "status": "failed",
            "context": context,
            "error_type": type(exc).__name__,
            "message": self.format_user_message(exc, context),
            "detail": str(exc),
        }
        if extra:
            payload["extra"] = extra
        return payload

    # ------------------------------ wrap ------------------------------------
    def wrap(
        self,
        context: str,
        default_fallback: Optional[Union[Dict[str, Any], Callable[[BaseException], Dict[str, Any]]]] = None,
        rethrow: bool = False,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator factory to add UX-safe error handling.

        Args:
            context: logical area (e.g., "prerequisite", "tooltip", "db").
            default_fallback: dict or callable(exc)->dict returned on failure (if not rethrow).
            rethrow: if True, re-raise after capture.
            meta: optional extra metadata to attach to the captured error payload.
        """
        def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(fn)
            def _inner(*args: Any, **kwargs: Any) -> Any:
                try:
                    return fn(*args, **kwargs)
                except BaseException as exc:
                    error_payload = self.capture_exception(exc, context, extra=meta)
                    if rethrow:
                        raise
                    if callable(default_fallback):
                        try:
                            return default_fallback(exc)
                        except Exception as fb_exc:
                            self._logger.warning("Fallback callable failed: %r", fb_exc)
                            return error_payload
                    return default_fallback if isinstance(default_fallback, dict) else error_payload
            return _inner
        return _decorator

    # -------------------------- retry helper --------------------------------
    def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args: Any,
        retry_config: Optional[RetryConfig] = None,
        **kwargs: Any,
    ) -> Any:
        """Convenience wrapper that delegates to retry_call with RetryConfig."""
        cfg = retry_config or RetryConfig()
        return retry_call(func, *args, cfg=cfg, **kwargs)

    # ---------------------- convenience handlers for tests -------------------
    def handle_image_processing_error(self, error: BaseException, image_path: str, operation: str) -> Dict[str, Any]:
        """Return a normalized payload for image errors (and count them)."""
        record_ux_error("image_processing", {"exc": type(error).__name__, "op": operation, "image_path": image_path})
        return {
            "ok": False,
            "status": "failed",
            "context": "image_processing",
            "operation": operation,
            "error_type": type(error).__name__,
            "message": str(error),
            "image_path": image_path,
        }

    def handle_tooltip_error(self, error: BaseException, element_id: str) -> Dict[str, Any]:
        """Return a normalized payload for tooltip errors."""
        record_ux_error("tooltip", {"exc": type(error).__name__, "element_id": element_id})
        return {
            "ok": False,
            "status": "failed",
            "context": "tooltip",
            "element_id": element_id,
            "error_type": type(error).__name__,
            "message": str(error),
        }

    def get_processing_stats(self) -> Dict[str, Any]:
        """Expose lightweight counters for tests/services."""
        return get_ux_error_stats()


# Module-level singleton expected by tests/services
ux_error_handler = UXErrorHandler(logger)

def with_prerequisite_error_handling(
    fn=None,
    *,
    fallback=None,
    rethrow: bool = True,
    allow_fallback: bool = False,
    required: bool | None = None,
    checker_name: str | None = None,
    **meta,
):
    def _decorator(func):
        def _wrapped(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Lazy-Import der Result-Klassen, um Zyklen zu vermeiden
                from src.services.prerequisite_checker import (
                    PrerequisiteResult,
                    PrerequisiteStatus,
                    PrerequisiteType,
                )

                is_required = True if required is None else bool(required)
                return PrerequisiteResult(
                    name=checker_name or getattr(args[0], "name", "prerequisite"),
                    status=PrerequisiteStatus.FAILED if is_required else PrerequisiteStatus.WARNING,
                    # ganz wichtig: Originaltext durchreichen (Tests suchen Substrings)
                    message=str(e),
                    details="",
                    resolution_steps=[],
                    check_time=0.0,
                    prerequisite_type=PrerequisiteType.REQUIRED if is_required else PrerequisiteType.RECOMMENDED,
                )
        return _wrapped

    if fn is None:
        return _decorator
    return _decorator(fn)


# ---------------------- tooltip-safe helpers & decorator ----------------------
from typing import Any

def safe_tooltip_execution(
    func: Optional[Callable[..., Any]] = None,
    *,
    element_id: Optional[str] = None,
    default: Any = None,
):
    """Decorator that safely executes a tooltip builder.

    Usage:
        @safe_tooltip_execution(element_id="btn_x")
        def build_tooltip(...): ...
    """
    def _decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def _inner(*args: Any, **kwargs: Any) -> Any:
            try:
                return f(*args, **kwargs)
            except BaseException as exc:
                payload = ux_error_handler.capture_exception(exc, context="tooltip", extra={"element_id": element_id})
                try:
                    record_ux_error("tooltip", {"exc": type(exc).__name__, "element_id": element_id})
                except Exception:
                    pass
                if default is not None:
                    return default
                return {
                    "ok": False,
                    "status": "failed",
                    "context": "tooltip",
                    "error_type": payload.get("error_type", type(exc).__name__),
                    "message": payload.get("message", "An unexpected error occurred."),
                    "detail": payload.get("detail", str(exc)),
                    "element_id": element_id,
                }
        return _inner

    if callable(func):
        return _decorator(func)
    return _decorator


def with_tooltip_error_handling(
    fn: Optional[Callable[..., Any]] = None,
    *,
    fallback: Optional[Union[Dict[str, Any], Callable[[BaseException], Dict[str, Any]]]] = None,
    rethrow: bool = False,
) -> Union[Callable[..., Any], Callable[[Callable[..., Any]], Callable[..., Any]]]:
    """Decorator (or factory) for tooltip generation sites."""
    decorator = ux_error_handler.wrap("tooltip", default_fallback=fallback, rethrow=rethrow)
    if fn is None:
        return decorator
    return decorator(fn)


# Extend public exports (without touching the original __all__)
try:
    __all__  # type: ignore[name-defined]
    __all__ += [
        "UXErrorHandler", "ux_error_handler", "with_prerequisite_error_handling",
        "safe_tooltip_execution", "with_tooltip_error_handling",
    ]
except NameError:
    __all__ = [
        "RetryConfig", "retry_call",
        "record_ux_error", "get_ux_error_stats", "reset_ux_error_stats",
        "UXErrorHandler", "ux_error_handler", "with_prerequisite_error_handling",
        "safe_tooltip_execution", "with_tooltip_error_handling",
    ]
