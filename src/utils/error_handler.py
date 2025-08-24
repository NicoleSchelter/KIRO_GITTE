# optional – verhindert, dass Typnamen in Annotationen zur Laufzeit aufgelöst werden
from __future__ import annotations

from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional
from uuid import uuid4
import logging
import re
import sys
import traceback
from collections.abc import Callable

# importiere die tatsächlich verwendeten Fehlerklassen/Enums
from src.exceptions import (
    GITTEError,
    NetworkError,
    DatabaseError,
    AuthorizationError,
    SystemError,
    ErrorSeverity,
)

# Logger definieren 
logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling and logging."""

    def __init__(self):
        self.error_counts: dict[str, int] = {}
        self.recent_errors: list[dict[str, Any]] = []
        self.max_recent_errors = 100

    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
        show_user_message: bool = True,
        *,                              # ab hier nur noch keyword-args für neue Felder
        component: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Vereinheitlichte Fehlerbehandlung:
        - Rückwärtskompatibel zu bestehenden Aufrufen (ux_error_handler nutzt: error, context, show_user_message).
        - Ergänzt optional 'component' (neue .rej-Logik).
        - Generiert/übernimmt request_id.
        - Fügt, wenn möglich, 'user_message' und 'severity' hinzu (ohne harte PALD-Abhängigkeit).
        """
        # Robust: request_id festlegen (Param > vorhandenes Attribut > neu generieren)
        rid = request_id or getattr(self, "request_id", None) or str(uuid4())
        self.request_id = rid

        # In dein bestehendes Schema konvertieren
        gitte_error = self._convert_to_gitte_error(error)

        # Basis-Record nach deinem bisherigen Format
        record = self._create_error_record(
            gitte_error,
            context=context or {},
            user_id=user_id,
            request_id=rid,
        )

        # Additive Felder aus der .rej-Variante
        record["component"] = component or (context or {}).get("component") or "unknown"

        # Optionale Severity (kein PALD-Import nötig – wir lesen ab, wenn vorhanden)
        sev = getattr(gitte_error, "severity", None) or getattr(error, "severity", None)
        if sev is not None and "severity" not in record:
            # Enum? -> .value; sonst String/Objekt repräsentieren
            record["severity"] = getattr(sev, "value", str(sev))

        # Optionale User-Message (nur wenn deine Helper-Methode existiert)
        if hasattr(self, "_get_user_message") and "user_message" not in record:
            try:
                record["user_message"] = self._get_user_message(gitte_error)
            except Exception:
                # defensiv – Logging nicht gefährden
                pass

        # Logging & Statistiken wie gehabt
        self._log_error(record)
        self._track_error(record)

        # Benutzerhinweis (rückwärtskompatibel)
        if show_user_message and self._is_streamlit_context():
            self._show_user_message(gitte_error)

        return record


    def _convert_to_gitte_error(self, error: Exception) -> GITTEError:
        """Convert generic exception to GITTEError."""
        error_type = type(error).__name__

        # Map common exceptions to GITTE errors
        if "connection" in str(error).lower() or "timeout" in str(error).lower():
            return NetworkError(str(error), cause=error)
        elif "database" in str(error).lower() or "sql" in str(error).lower():
            return DatabaseError(str(error), cause=error)
        elif "permission" in str(error).lower() or "access" in str(error).lower():
            return AuthorizationError(str(error), cause=error)
        else:
            return SystemError(
                f"Unexpected {error_type}: {str(error)}",
                cause=error,
                details={"original_type": error_type},
            )

    def _create_error_record(
        self,
        error: GITTEError,
        context: dict[str, Any] | None,
        user_id: str | None,
        request_id: str,
    ) -> dict[str, Any]:
        """Create comprehensive error record."""
        # Nutze den Original-Fehler, falls vorhanden, sonst den GITTEError
        exc_for_tb = error.cause if getattr(error, "cause", None) else error
        tb = "".join(traceback.TracebackException.from_exception(exc_for_tb).format())

        return {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "user_id": user_id,
            "error": error.to_dict(),  # -> in exceptions.py als Strings serialisiert
            "context": context or {},
            "traceback": tb,
            "system_info": {"python_version": sys.version, "platform": sys.platform},
        }



    def _log_error(self, error_record: dict[str, Any]) -> None:
        """Log error with appropriate level."""
        error_info = error_record["error"]

        # Severity robust normalisieren (String -> Enum)
        sev = error_info.get("severity")
        if isinstance(sev, ErrorSeverity):
            severity = sev
        elif isinstance(sev, str):
            try:
                severity = ErrorSeverity[sev]   # "MEDIUM"
            except KeyError:
                try:
                    severity = ErrorSeverity(sev)  # "medium"
                except Exception:
                    severity = ErrorSeverity.MEDIUM
        else:
            severity = ErrorSeverity.MEDIUM

        # Category sauber serialisieren (in to_dict meist String)
        category = error_info.get("category")
        if hasattr(category, "value"):
            category = category.value

        log_data = {
            "request_id": error_record["request_id"],
            "user_id": error_record["user_id"],
            "error_code": error_info.get("error_code"),
            "category": category,
            "error_message": error_info.get("message"),
            "details": error_info.get("details"),
        }

        # Komponente immer mitloggen
        log_data["component"] = error_record.get("component", "unknown")

        # --- PII-Redaktion: immer aktiv, bevor geloggt wird ---
        def _redact_obj(obj):
            if isinstance(obj, dict):
                return {k: _redact_obj(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_redact_obj(v) for v in obj]
            if isinstance(obj, str):
                return PIIRedactor.redact(obj)
            return obj

        try:
            log_data["error_message"] = PIIRedactor.redact(str(log_data.get("error_message")))
            log_data["details"] = _redact_obj(log_data.get("details"))
        except Exception:
            # Redaktionsfehler sollen das Logging nicht verhindern
            pass
        # --- Ende PII-Redaktion ---

        if severity == ErrorSeverity.CRITICAL:
            logger.critical("Critical error occurred", extra=log_data)
        elif severity == ErrorSeverity.HIGH:
            logger.error("High severity error occurred", extra=log_data)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning("Medium severity error occurred", extra=log_data)
        else:
            logger.info("Low severity error occurred", extra=log_data)

        if severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL):
            logger.debug(
                "Full traceback for %s: %s",
                error_record["request_id"],
                error_record["traceback"],
            )



    def _track_error(self, error_record: dict[str, Any]) -> None:
        """Track error statistics."""
        error_code = error_record["error"]["error_code"]

        # Update error counts
        self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1

        # Add to recent errors
        self.recent_errors.append(error_record)

        # Maintain recent errors list size
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[-self.max_recent_errors :]

    def _show_user_message(self, error: GITTEError) -> None:
        """Show user-friendly error message in Streamlit."""
        try:
            import streamlit as st
            if error.severity == ErrorSeverity.CRITICAL:
                st.error(f"🚨 {error.user_message}")
            elif error.severity == ErrorSeverity.HIGH:
                st.error(f"❌ {error.user_message}")
            elif error.severity == ErrorSeverity.MEDIUM:
                st.warning(f"⚠️ {error.user_message}")
            else:
                st.info(f"ℹ️ {error.user_message}")
        except ImportError:
            # Fallback to logging if streamlit not available
            logger.error(f"UI Error: {error.user_message}")

    def _is_streamlit_context(self) -> bool:
        """Check if running in Streamlit context."""
        try:
            import streamlit as st
            # Try to access session state to check if in Streamlit context
            _ = st.session_state
            return True
        except:
            return False

    def get_error_stats(self) -> dict[str, Any]:
        """Get error statistics."""
        total_errors = sum(self.error_counts.values())

        return {
            "total_errors": total_errors,
            "error_counts": self.error_counts.copy(),
            "recent_errors_count": len(self.recent_errors),
            "most_common_errors": sorted(
                self.error_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def get_recent_errors(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent errors."""
        return self.recent_errors[-limit:]

    def clear_stats(self) -> None:
        """Clear error statistics."""
        self.error_counts.clear()
        self.recent_errors.clear()


# Global error handler instance
error_handler = ErrorHandler()

class ErrorBoundary:
    """Context manager for error boundary functionality."""

    def __init__(
        self,
        fallback_message: str = "An error occurred in this section.",
        show_details: bool = False,
        context: dict[str, Any] | None = None,
    ):
        self.fallback_message = fallback_message
        self.show_details = show_details
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Handle the error
            error_handler.handle_error(
                error=exc_val,
                context=self.context,
                show_user_message=False,
                component="ux/error_boundary",
            )
            # Show fallback message
            try:
                import streamlit as st
                st.error(self.fallback_message)

                if self.show_details and isinstance(exc_val, GITTEError):
                    with st.expander("Error Details"):
                        st.write(f"**Error Code:** {exc_val.error_code}")
                        st.write(f"**Category:** {exc_val.category.value}")
                        st.write(f"**Severity:** {exc_val.severity.value}")
                        if exc_val.details:
                            st.json(exc_val.details)
            except:
                pass

            # Suppress the exception
            return True

        return False

# --- merged new class from .rej ---
class PIIRedactor:
    """Helper class to redact PII from log messages."""

    # robuster & einfacher
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', re.IGNORECASE)
    UUID_PATTERN = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE)
    # 2 Gruppen: (Prefix) (Wert) → wir behalten Prefix, ersetzen nur den Wert
    TOKEN_PATTERN = re.compile(r'(\b(?:token|key|secret|password)["\']?\s*[:=]\s*["\']?)([^\s"\']+)', re.IGNORECASE)

    @classmethod
    def redact(cls, text: str) -> str:
        """Redact PII from text."""
        if not isinstance(text, str):
            text = str(text)

        text = cls.EMAIL_PATTERN.sub('[EMAIL_REDACTED]', text)
        text = cls.UUID_PATTERN.sub('[UUID_REDACTED]', text)
        text = cls.TOKEN_PATTERN.sub(r'\1[TOKEN_REDACTED]', text)
        return text

def handle_errors(
    show_user_message: bool = True, context: dict[str, Any] | None = None, reraise: bool = True
) -> Callable:
    """
    Decorator to handle errors in functions.

    Args:
        show_user_message: Whether to show user-friendly message
        context: Additional context to include in error record
        reraise: Whether to reraise the exception after handling
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get user ID from session state if available
                user_id = None
                try:
                    import streamlit as st
                    user_id = st.session_state.get("user_id")
                except:
                    pass

                # Handle the error
                error_handler.handle_error(
                    error=e, context=context, user_id=user_id, show_user_message=show_user_message
                )

                if reraise:
                    raise

                return None

        return wrapper

    return decorator

def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    context: dict[str, Any] | None = None,
    show_user_message: bool = True,
    **kwargs,
) -> Any:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        *args: Function arguments
        default_return: Value to return if function fails
        context: Additional context for error handling
        show_user_message: Whether to show user message
        **kwargs: Function keyword arguments

    Returns:
        Function result or default_return if error occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        # Get user ID from session state if available
        user_id = None
        try:
            import streamlit as st
            user_id = st.session_state.get("user_id")
        except:
            pass

        # Handle the error
        error_handler.handle_error(
            error=e, context=context, user_id=user_id, show_user_message=show_user_message
        )

        return default_return

def graceful_degradation(
    primary_func: Callable,
    fallback_func: Callable | None = None,
    fallback_message: str = "Using simplified functionality due to service issues.",
    context: dict[str, Any] | None = None,
) -> Callable:
    """
    Decorator to provide graceful degradation when primary function fails.

    Args:
        primary_func: Primary function to try
        fallback_func: Fallback function if primary fails
        fallback_message: Message to show when using fallback
        context: Additional context for error handling
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return primary_func(*args, **kwargs)
            except Exception as e:
                # Handle the error
                error_handler.handle_error(
                    error=e,
                    context=context,
                    show_user_message=False,  # Don't show error, show fallback message instead
                )

                # Show fallback message
                try:
                    import streamlit as st
                    st.info(f"ℹ️ {fallback_message}")
                except:
                    pass

                # Use fallback function if available
                if fallback_func:
                    try:
                        return fallback_func(*args, **kwargs)
                    except Exception as fallback_error:
                        error_handler.handle_error(
                            error=fallback_error,
                            context={**(context or {}), "fallback_failed": True},
                            show_user_message=True,
                        )
                        raise

                # No fallback available
                raise

        return wrapper

    return decorator

def get_error_stats() -> dict[str, Any]:
    """Get global error statistics."""
    return error_handler.get_error_stats()

def get_recent_errors(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent errors."""
    return error_handler.get_recent_errors(limit)

def clear_error_stats() -> None:
    """Clear error statistics."""
    error_handler.clear_stats()

def render_error_dashboard() -> None:
    """Render error monitoring dashboard in Streamlit."""
    try:
        import streamlit as st
        
        st.subheader("🚨 Error Monitoring Dashboard")

        # Get error statistics
        stats = get_error_stats()

        # Display summary metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Errors", stats["total_errors"])

        with col2:
            st.metric("Recent Errors", stats["recent_errors_count"])

        with col3:
            unique_error_types = len(stats["error_counts"])
            st.metric("Error Types", unique_error_types)

        # Most common errors
        if stats["most_common_errors"]:
            st.subheader("Most Common Errors")
            for error_code, count in stats["most_common_errors"]:
                st.write(f"**{error_code}**: {count} occurrences")

        # Recent errors
        def _fmt_enum(v):
            return getattr(v, "value", v)
        recent_errors = get_recent_errors(10)
        if recent_errors:
            st.subheader("Recent Errors")
            for error_record in recent_errors:
                with st.expander(
                    f"{error_record['error']['error_code']} - {error_record['timestamp']}"
                ):
                    st.write(f"**Message:** {error_record['error']['message']}")
                    st.write(f"**Category:** {_fmt_enum(error_record['error']['category'])}")
                    st.write(f"**Severity:** {_fmt_enum(error_record['error']['severity'])}")
                    st.write(f"**User ID:** {error_record['user_id'] or 'Anonymous'}")
                    st.write(f"**Request ID:** {error_record['request_id']}")

                    if error_record["error"]["details"]:
                        st.write("**Details:**")
                        st.json(error_record["error"]["details"])

        # Clear stats button
        if st.button("Clear Error Statistics"):
            clear_error_stats()
            st.success("Error statistics cleared!")
            st.rerun()

    except Exception as e:
        try:
            import streamlit as st
            st.error(f"Error rendering dashboard: {e}")
        except ImportError:
            logger.error(f"Error rendering dashboard: {e}")

