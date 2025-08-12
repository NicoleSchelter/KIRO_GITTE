"""
Security middleware for GITTE system.
Provides security headers, CSRF protection, and request security validation.
"""

import logging
import secrets
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

import streamlit as st

from src.exceptions import RateLimitExceededError, SecurityError, SuspiciousActivityError

logger = logging.getLogger(__name__)


class CSRFError(SecurityError):
    """CSRF protection error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(f"CSRF protection error: {message}", **kwargs)
        self.user_message = "Security validation failed. Please refresh the page and try again."


class SecurityMiddleware:
    """Security middleware for request processing."""

    def __init__(self):
        self.csrf_tokens: dict[str, dict[str, Any]] = {}
        self.rate_limits: dict[str, list[float]] = {}
        self.suspicious_ips: set = set()

        # Security configuration
        self.csrf_token_lifetime = 3600  # 1 hour
        self.rate_limit_window = 60  # 1 minute
        self.rate_limit_max_requests = 100
        self.max_suspicious_requests = 10

    def get_security_headers(self) -> dict[str, str]:
        """
        Get security headers for HTTP responses.

        Returns:
            Dict of security headers
        """
        return {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Content Security Policy
            "Content-Security-Policy": self._get_csp_header(),
            # Strict Transport Security (HTTPS only)
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            # Permissions policy
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            # Cache control for sensitive pages
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

    def _get_csp_header(self) -> str:
        """Generate Content Security Policy header."""
        # Generate nonce for inline scripts
        nonce = secrets.token_urlsafe(16)

        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}' 'unsafe-eval'",  # unsafe-eval needed for Streamlit
            "style-src 'self' 'unsafe-inline'",  # unsafe-inline needed for Streamlit
            "img-src 'self' data: https:",
            "font-src 'self' https:",
            "connect-src 'self' https:",
            "media-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests",
        ]

        return "; ".join(csp_directives)

    def generate_csrf_token(self, user_id: str | None = None) -> str:
        """
        Generate CSRF token for user session.

        Args:
            user_id: User identifier

        Returns:
            CSRF token
        """
        token = secrets.token_urlsafe(32)

        # Store token with metadata
        self.csrf_tokens[token] = {"user_id": user_id, "created_at": time.time(), "used": False}

        # Clean up expired tokens
        self._cleanup_expired_tokens()

        logger.debug(f"Generated CSRF token for user {user_id}")
        return token

    def validate_csrf_token(self, token: str, user_id: str | None = None) -> bool:
        """
        Validate CSRF token.

        Args:
            token: CSRF token to validate
            user_id: User identifier

        Returns:
            True if token is valid
        """
        if not token or token not in self.csrf_tokens:
            logger.warning(f"Invalid CSRF token attempted: {token[:8]}...")
            return False

        token_data = self.csrf_tokens[token]

        # Check if token is expired
        if time.time() - token_data["created_at"] > self.csrf_token_lifetime:
            logger.warning(f"Expired CSRF token attempted: {token[:8]}...")
            del self.csrf_tokens[token]
            return False

        # Check if token belongs to the user
        if token_data["user_id"] != user_id:
            logger.warning(
                f"CSRF token user mismatch: expected {user_id}, got {token_data['user_id']}"
            )
            return False

        # Mark token as used (one-time use)
        if token_data["used"]:
            logger.warning(f"CSRF token reuse attempted: {token[:8]}...")
            return False

        token_data["used"] = True
        logger.debug(f"CSRF token validated for user {user_id}")
        return True

    def _cleanup_expired_tokens(self) -> None:
        """Clean up expired CSRF tokens."""
        current_time = time.time()
        expired_tokens = [
            token
            for token, data in self.csrf_tokens.items()
            if current_time - data["created_at"] > self.csrf_token_lifetime
        ]

        for token in expired_tokens:
            del self.csrf_tokens[token]

        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired CSRF tokens")

    def check_rate_limit(self, identifier: str, max_requests: int | None = None) -> bool:
        """
        Check rate limit for identifier (IP, user, etc.).

        Args:
            identifier: Unique identifier for rate limiting
            max_requests: Maximum requests allowed (uses default if None)

        Returns:
            True if within rate limit
        """
        if max_requests is None:
            max_requests = self.rate_limit_max_requests

        current_time = time.time()
        window_start = current_time - self.rate_limit_window

        # Initialize or get existing request times
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []

        request_times = self.rate_limits[identifier]

        # Remove old requests outside the window
        request_times[:] = [t for t in request_times if t > window_start]

        # Check if limit exceeded
        if len(request_times) >= max_requests:
            logger.warning(
                f"Rate limit exceeded for {identifier}: {len(request_times)} requests in {self.rate_limit_window}s"
            )
            return False

        # Add current request
        request_times.append(current_time)
        return True

    def detect_suspicious_activity(self, request_data: dict[str, Any]) -> bool:
        """
        Detect suspicious activity patterns.

        Args:
            request_data: Request information

        Returns:
            True if suspicious activity detected
        """
        suspicious_indicators = []

        # Check for common attack patterns in user agent
        user_agent = request_data.get("user_agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan", "zap"]
        if any(agent in user_agent for agent in suspicious_agents):
            suspicious_indicators.append("suspicious_user_agent")

        # Check for suspicious request patterns
        path = request_data.get("path", "")
        suspicious_paths = [
            "/admin",
            "/wp-admin",
            "/.env",
            "/config",
            "/backup",
            "/phpmyadmin",
            "/mysql",
            "/database",
            "/../",
            "/etc/passwd",
        ]
        if any(suspicious_path in path.lower() for suspicious_path in suspicious_paths):
            suspicious_indicators.append("suspicious_path")

        # Check for SQL injection patterns in parameters
        params = request_data.get("params", {})
        for param_value in params.values():
            if isinstance(param_value, str):
                sql_patterns = ["'", "union", "select", "drop", "insert", "delete", "--", "/*"]
                if any(pattern in param_value.lower() for pattern in sql_patterns):
                    suspicious_indicators.append("sql_injection_attempt")
                    break

        # Check request frequency from same IP
        ip_address = request_data.get("ip_address")
        if ip_address:
            if not self.check_rate_limit(f"ip_{ip_address}", self.max_suspicious_requests):
                suspicious_indicators.append("high_request_frequency")

        if suspicious_indicators:
            logger.warning(
                f"Suspicious activity detected: {suspicious_indicators} from {ip_address}"
            )
            if ip_address:
                self.suspicious_ips.add(ip_address)
            return True

        return False

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked."""
        return ip_address in self.suspicious_ips

    def block_ip(self, ip_address: str, reason: str) -> None:
        """Block an IP address."""
        self.suspicious_ips.add(ip_address)
        logger.warning(f"Blocked IP {ip_address}: {reason}")

    def unblock_ip(self, ip_address: str) -> None:
        """Unblock an IP address."""
        self.suspicious_ips.discard(ip_address)
        logger.info(f"Unblocked IP {ip_address}")


# Global security middleware instance
security_middleware = SecurityMiddleware()


def csrf_protect(func: Callable) -> Callable:
    """
    Decorator to add CSRF protection to functions.

    Args:
        func: Function to protect

    Returns:
        Protected function
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get user ID from session
        user_id = st.session_state.get("user_id")

        # Check if CSRF token is present and valid
        csrf_token = st.session_state.get("csrf_token")

        if not csrf_token:
            # Generate new token if none exists
            csrf_token = security_middleware.generate_csrf_token(user_id)
            st.session_state.csrf_token = csrf_token

        # For form submissions, validate the token
        if hasattr(st, "form_submit_button") and st.session_state.get("form_submitted"):
            submitted_token = st.session_state.get("submitted_csrf_token")

            if not security_middleware.validate_csrf_token(submitted_token, user_id):
                raise CSRFError("Invalid or missing CSRF token")

        return func(*args, **kwargs)

    return wrapper


def rate_limit(max_requests: int = 100, window_seconds: int = 60) -> Callable:
    """
    Decorator to add rate limiting to functions.

    Args:
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds

    Returns:
        Rate limited function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get identifier (user ID or IP)
            user_id = st.session_state.get("user_id")
            identifier = user_id or "anonymous"

            # Check rate limit
            if not security_middleware.check_rate_limit(identifier, max_requests):
                raise RateLimitExceededError(max_requests, window_seconds)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def security_check(func: Callable) -> Callable:
    """
    Decorator to add general security checks to functions.

    Args:
        func: Function to protect

    Returns:
        Protected function
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Mock request data (in real implementation, get from actual request)
        request_data = {
            "user_agent": "streamlit_app",
            "path": "/",
            "params": {},
            "ip_address": "127.0.0.1",  # Would get real IP
        }

        # Check for suspicious activity
        if security_middleware.detect_suspicious_activity(request_data):
            ip_address = request_data.get("ip_address")
            raise SuspiciousActivityError("suspicious_request_pattern")

        # Check if IP is blocked
        ip_address = request_data.get("ip_address")
        if ip_address and security_middleware.is_ip_blocked(ip_address):
            raise SecurityError("IP address is blocked due to suspicious activity")

        return func(*args, **kwargs)

    return wrapper


def secure_headers(func: Callable) -> Callable:
    """
    Decorator to add security headers (for non-Streamlit contexts).

    Args:
        func: Function to decorate

    Returns:
        Function with security headers
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # In a real web framework, you would set these headers on the response
        security_middleware.get_security_headers()

        # For Streamlit, we can't set HTTP headers directly,
        # but we can add security meta tags
        try:
            # This would be used in a custom Streamlit component

            # In a real implementation, inject these into the page head
            logger.debug("Security headers would be applied")

        except Exception as e:
            logger.warning(f"Could not apply security headers: {e}")

        return func(*args, **kwargs)

    return wrapper


class SecureForm:
    """Secure form helper for Streamlit forms."""

    def __init__(self, form_key: str):
        self.form_key = form_key
        self.csrf_token = security_middleware.generate_csrf_token(st.session_state.get("user_id"))

    def __enter__(self):
        """Enter form context."""
        # Store CSRF token in session
        st.session_state[f"csrf_token_{self.form_key}"] = self.csrf_token
        return st.form(self.form_key)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit form context."""
        pass

    def submit_button(self, label: str, **kwargs) -> bool:
        """Create secure submit button with CSRF protection."""
        submitted = st.form_submit_button(label, **kwargs)

        if submitted:
            # Validate CSRF token
            stored_token = st.session_state.get(f"csrf_token_{self.form_key}")
            user_id = st.session_state.get("user_id")

            if not security_middleware.validate_csrf_token(stored_token, user_id):
                st.error("Security validation failed. Please refresh the page and try again.")
                return False

        return submitted


def create_secure_form(form_key: str) -> SecureForm:
    """
    Create a secure form with CSRF protection.

    Args:
        form_key: Unique form identifier

    Returns:
        SecureForm instance
    """
    return SecureForm(form_key)


def get_security_headers() -> dict[str, str]:
    """Get security headers for HTTP responses."""
    return security_middleware.get_security_headers()


def generate_csrf_token(user_id: str | None = None) -> str:
    """Generate CSRF token."""
    return security_middleware.generate_csrf_token(user_id)


def validate_csrf_token(token: str, user_id: str | None = None) -> bool:
    """Validate CSRF token."""
    return security_middleware.validate_csrf_token(token, user_id)


def check_rate_limit(identifier: str, max_requests: int = 100) -> bool:
    """Check rate limit for identifier."""
    return security_middleware.check_rate_limit(identifier, max_requests)


def block_ip_address(ip_address: str, reason: str) -> None:
    """Block an IP address."""
    security_middleware.block_ip(ip_address, reason)


def unblock_ip_address(ip_address: str) -> None:
    """Unblock an IP address."""
    security_middleware.unblock_ip(ip_address)


def get_blocked_ips() -> set:
    """Get list of blocked IP addresses."""
    return security_middleware.suspicious_ips.copy()


def get_security_stats() -> dict[str, Any]:
    """Get security statistics."""
    return {
        "csrf_tokens_active": len(security_middleware.csrf_tokens),
        "rate_limited_identifiers": len(security_middleware.rate_limits),
        "blocked_ips": len(security_middleware.suspicious_ips),
        "suspicious_ips": list(security_middleware.suspicious_ips),
    }
