"""
Input validation and sanitization utilities for GITTE system.
Provides comprehensive input validation, sanitization, and security checks.
"""

import logging
import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

# import bleach  # Would be used for HTML sanitization in production
# from markupsafe import Markup  # Would be used for safe HTML handling
from src.exceptions import ValidationError

logger = logging.getLogger(__name__)


class InputValidationError(ValidationError):
    """Input validation specific error."""

    def __init__(self, field: str, value: Any, reason: str, **kwargs):
        super().__init__(f"Invalid input for field '{field}': {reason}", field=field, **kwargs)
        self.user_message = f"Invalid {field}: {reason}"
        self.details.update({"field": field, "value": str(value), "reason": reason})


class InputSanitizer:
    """Input sanitization utilities."""

    # HTML tags allowed in user content
    ALLOWED_HTML_TAGS = [
        "p",
        "br",
        "strong",
        "em",
        "u",
        "ol",
        "ul",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "blockquote",
    ]

    # HTML attributes allowed
    ALLOWED_HTML_ATTRIBUTES = {
        "*": ["class"],
        "a": ["href", "title"],
        "img": ["src", "alt", "width", "height"],
    }

    @staticmethod
    def sanitize_html(content: str, allowed_tags: list[str] | None = None) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.

        Args:
            content: HTML content to sanitize
            allowed_tags: List of allowed HTML tags (uses default if None)

        Returns:
            Sanitized HTML content
        """
        if not content:
            return ""

        if allowed_tags is None:
            allowed_tags = InputSanitizer.ALLOWED_HTML_TAGS

        # Simple HTML sanitization (in production, use bleach library)
        # Remove script tags and other dangerous elements
        dangerous_tags = ["script", "iframe", "object", "embed", "link", "meta", "style"]
        sanitized = content

        for tag in dangerous_tags:
            # Remove opening and closing tags
            sanitized = re.sub(
                f"<{tag}[^>]*>.*?</{tag}>", "", sanitized, flags=re.IGNORECASE | re.DOTALL
            )
            sanitized = re.sub(f"<{tag}[^>]*/?>", "", sanitized, flags=re.IGNORECASE)

        # Remove javascript: URLs and event handlers
        sanitized = re.sub(r'javascript:[^"\']*', "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', "", sanitized, flags=re.IGNORECASE)

        return sanitized

    @staticmethod
    def sanitize_text(text: str, max_length: int | None = None) -> str:
        """
        Sanitize plain text input.

        Args:
            text: Text to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove null bytes and control characters
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Normalize whitespace
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        # Truncate if necessary
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal and other attacks.

        Args:
            filename: Filename to sanitize

        Returns:
            Sanitized filename
        """
        if not filename:
            return "unnamed_file"

        # Remove path separators and dangerous characters
        sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", filename)

        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip(". ")

        # Prevent reserved names on Windows
        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]

        name_without_ext = sanitized.split(".")[0].upper()
        if name_without_ext in reserved_names:
            sanitized = f"file_{sanitized}"

        # Ensure we have a valid filename
        if not sanitized or sanitized == ".":
            sanitized = "unnamed_file"

        return sanitized

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        Sanitize URL to prevent malicious redirects.

        Args:
            url: URL to sanitize

        Returns:
            Sanitized URL
        """
        if not url:
            return ""

        try:
            parsed = urlparse(url)

            # Only allow http and https schemes
            if parsed.scheme not in ["http", "https"]:
                return ""

            # Reconstruct URL with sanitized components
            sanitized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

            if parsed.query:
                sanitized_url += f"?{parsed.query}"

            return sanitized_url

        except Exception:
            return ""


class InputValidator:
    """Input validation utilities."""

    # Common regex patterns
    PATTERNS = {
        "username": re.compile(r"^[a-zA-Z0-9_-]{3,30}$"),
        "password": re.compile(r"^.{8,128}$"),
        "phone": re.compile(r"^\+?[1-9]\d{1,14}$"),
        "alphanumeric": re.compile(r"^[a-zA-Z0-9]+$"),
        "alpha": re.compile(r"^[a-zA-Z]+$"),
        "numeric": re.compile(r"^[0-9]+$"),
        "uuid": re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
        ),
        "slug": re.compile(r"^[a-z0-9-]+$"),
        "hex_color": re.compile(r"^#[0-9a-fA-F]{6}$"),
    }

    @staticmethod
    def validate_required(value: Any, field_name: str) -> Any:
        """
        Validate that a field is not empty.

        Args:
            value: Value to validate
            field_name: Name of the field

        Returns:
            The value if valid

        Raises:
            InputValidationError: If value is empty
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            raise InputValidationError(field_name, value, "is required")

        return value

    @staticmethod
    def validate_string(
        value: str,
        field_name: str,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: re.Pattern | None = None,
        allowed_values: list[str] | None = None,
    ) -> str:
        """
        Validate string input.

        Args:
            value: String to validate
            field_name: Name of the field
            min_length: Minimum length
            max_length: Maximum length
            pattern: Regex pattern to match
            allowed_values: List of allowed values

        Returns:
            Validated string
        """
        if not isinstance(value, str):
            raise InputValidationError(field_name, value, "must be a string")

        # Length validation
        if min_length is not None and len(value) < min_length:
            raise InputValidationError(
                field_name, value, f"must be at least {min_length} characters long"
            )

        if max_length is not None and len(value) > max_length:
            raise InputValidationError(
                field_name, value, f"must be no more than {max_length} characters long"
            )

        # Pattern validation
        if pattern and not pattern.match(value):
            raise InputValidationError(field_name, value, "format is invalid")

        # Allowed values validation
        if allowed_values and value not in allowed_values:
            raise InputValidationError(
                field_name, value, f"must be one of: {', '.join(allowed_values)}"
            )

        return value

    @staticmethod
    def validate_email(email: str, field_name: str = "email") -> str:
        """
        Validate email address.

        Args:
            email: Email to validate
            field_name: Name of the field

        Returns:
            Validated email address
        """
        if not isinstance(email, str):
            raise InputValidationError(field_name, email, "must be a string")

        # Simple email validation (in production, use email-validator library)
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

        if not email_pattern.match(email):
            raise InputValidationError(field_name, email, "invalid email format")

        return email.lower()

    @staticmethod
    def validate_username(username: str, field_name: str = "username") -> str:
        """
        Validate username.

        Args:
            username: Username to validate
            field_name: Name of the field

        Returns:
            Validated username
        """
        return InputValidator.validate_string(
            username,
            field_name,
            min_length=3,
            max_length=30,
            pattern=InputValidator.PATTERNS["username"],
        )

    @staticmethod
    def validate_password(password: str, field_name: str = "password") -> str:
        """
        Validate password strength.

        Args:
            password: Password to validate
            field_name: Name of the field

        Returns:
            Validated password
        """
        if not isinstance(password, str):
            raise InputValidationError(field_name, password, "must be a string")

        if len(password) < 8:
            raise InputValidationError(field_name, password, "must be at least 8 characters long")

        if len(password) > 128:
            raise InputValidationError(
                field_name, password, "must be no more than 128 characters long"
            )

        # Check for at least one uppercase, lowercase, digit, and special character
        if not re.search(r"[A-Z]", password):
            raise InputValidationError(
                field_name, password, "must contain at least one uppercase letter"
            )

        if not re.search(r"[a-z]", password):
            raise InputValidationError(
                field_name, password, "must contain at least one lowercase letter"
            )

        if not re.search(r"\d", password):
            raise InputValidationError(field_name, password, "must contain at least one digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise InputValidationError(
                field_name, password, "must contain at least one special character"
            )

        return password

    @staticmethod
    def validate_integer(
        value: int | str,
        field_name: str,
        min_value: int | None = None,
        max_value: int | None = None,
    ) -> int:
        """
        Validate integer input.

        Args:
            value: Value to validate
            field_name: Name of the field
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Validated integer
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise InputValidationError(field_name, value, "must be a valid integer")

        if min_value is not None and int_value < min_value:
            raise InputValidationError(field_name, value, f"must be at least {min_value}")

        if max_value is not None and int_value > max_value:
            raise InputValidationError(field_name, value, f"must be no more than {max_value}")

        return int_value

    @staticmethod
    def validate_float(
        value: float | str,
        field_name: str,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> float:
        """
        Validate float input.

        Args:
            value: Value to validate
            field_name: Name of the field
            min_value: Minimum allowed value
            max_value: Maximum allowed value

        Returns:
            Validated float
        """
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            raise InputValidationError(field_name, value, "must be a valid number")

        if min_value is not None and float_value < min_value:
            raise InputValidationError(field_name, value, f"must be at least {min_value}")

        if max_value is not None and float_value > max_value:
            raise InputValidationError(field_name, value, f"must be no more than {max_value}")

        return float_value

    @staticmethod
    def validate_boolean(value: bool | str, field_name: str) -> bool:
        """
        Validate boolean input.

        Args:
            value: Value to validate
            field_name: Name of the field

        Returns:
            Validated boolean
        """
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            lower_value = value.lower()
            if lower_value in ["true", "1", "yes", "on"]:
                return True
            elif lower_value in ["false", "0", "no", "off"]:
                return False

        raise InputValidationError(field_name, value, "must be a valid boolean value")

    @staticmethod
    def validate_url(url: str, field_name: str = "url") -> str:
        """
        Validate URL format.

        Args:
            url: URL to validate
            field_name: Name of the field

        Returns:
            Validated URL
        """
        if not isinstance(url, str):
            raise InputValidationError(field_name, url, "must be a string")

        try:
            parsed = urlparse(url)

            if not parsed.scheme:
                raise InputValidationError(field_name, url, "must include a scheme (http/https)")

            if parsed.scheme not in ["http", "https"]:
                raise InputValidationError(field_name, url, "must use http or https scheme")

            if not parsed.netloc:
                raise InputValidationError(field_name, url, "must include a valid domain")

            return url

        except Exception as e:
            raise InputValidationError(field_name, url, f"invalid URL format: {e}")

    @staticmethod
    def validate_uuid(uuid_str: str, field_name: str = "uuid") -> str:
        """
        Validate UUID format.

        Args:
            uuid_str: UUID string to validate
            field_name: Name of the field

        Returns:
            Validated UUID string
        """
        return InputValidator.validate_string(
            uuid_str, field_name, pattern=InputValidator.PATTERNS["uuid"]
        )

    @staticmethod
    def validate_file_upload(
        file_data: bytes,
        filename: str,
        field_name: str = "file",
        max_size_mb: int = 10,
        allowed_extensions: list[str] | None = None,
        allowed_mime_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Validate file upload.

        Args:
            file_data: File content as bytes
            filename: Original filename
            field_name: Name of the field
            max_size_mb: Maximum file size in MB
            allowed_extensions: List of allowed file extensions
            allowed_mime_types: List of allowed MIME types

        Returns:
            Dict with validated file information
        """
        if not file_data:
            raise InputValidationError(field_name, filename, "file is empty")

        # Size validation
        file_size_mb = len(file_data) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise InputValidationError(
                field_name,
                filename,
                f"file size ({file_size_mb:.1f}MB) exceeds limit of {max_size_mb}MB",
            )

        # Filename validation
        sanitized_filename = InputSanitizer.sanitize_filename(filename)

        # Extension validation
        if allowed_extensions:
            file_ext = (
                sanitized_filename.split(".")[-1].lower() if "." in sanitized_filename else ""
            )
            if file_ext not in [ext.lower() for ext in allowed_extensions]:
                raise InputValidationError(
                    field_name,
                    filename,
                    f"file type not allowed. Allowed types: {', '.join(allowed_extensions)}",
                )

        # MIME type validation (basic check based on file signature)
        if allowed_mime_types:
            detected_mime = _detect_mime_type(file_data)
            if detected_mime not in allowed_mime_types:
                raise InputValidationError(
                    field_name, filename, f"file type not allowed. Detected type: {detected_mime}"
                )

        return {
            "filename": sanitized_filename,
            "size_bytes": len(file_data),
            "size_mb": file_size_mb,
            "mime_type": _detect_mime_type(file_data) if allowed_mime_types else None,
        }


def _detect_mime_type(file_data: bytes) -> str:
    """
    Detect MIME type from file signature.

    Args:
        file_data: File content as bytes

    Returns:
        Detected MIME type
    """
    # Simple file signature detection
    if file_data.startswith(b"\x89PNG"):
        return "image/png"
    elif file_data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    elif file_data.startswith(b"GIF8"):
        return "image/gif"
    elif file_data.startswith(b"%PDF"):
        return "application/pdf"
    elif file_data.startswith(b"PK"):
        return "application/zip"
    else:
        return "application/octet-stream"


class FormValidator:
    """Form validation utilities."""

    def __init__(self):
        self.errors: dict[str, list[str]] = {}
        self.validated_data: dict[str, Any] = {}

    def validate_field(
        self, field_name: str, value: Any, validator: Callable[[Any, str], Any]
    ) -> "FormValidator":
        """
        Validate a single field.

        Args:
            field_name: Name of the field
            value: Value to validate
            validator: Validation function

        Returns:
            Self for method chaining
        """
        try:
            validated_value = validator(value, field_name)
            self.validated_data[field_name] = validated_value
        except InputValidationError as e:
            if field_name not in self.errors:
                self.errors[field_name] = []
            self.errors[field_name].append(e.user_message)

        return self

    def is_valid(self) -> bool:
        """Check if all validations passed."""
        return len(self.errors) == 0

    def get_errors(self) -> dict[str, list[str]]:
        """Get validation errors."""
        return self.errors

    def get_validated_data(self) -> dict[str, Any]:
        """Get validated data."""
        if not self.is_valid():
            raise ValidationError("Cannot get validated data when validation errors exist")
        return self.validated_data

    def add_error(self, field_name: str, error_message: str) -> None:
        """Add custom error."""
        if field_name not in self.errors:
            self.errors[field_name] = []
        self.errors[field_name].append(error_message)


# Security utilities
def check_sql_injection(input_string: str) -> bool:
    """
    Check for potential SQL injection patterns.

    Args:
        input_string: String to check

    Returns:
        True if potential SQL injection detected
    """
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
        r"(\'\s*(OR|AND)\s*\'\w*\'\s*=\s*\'\w*\')",
        r"(\bUNION\s+SELECT\b)",
    ]

    return any(re.search(pattern, input_string, re.IGNORECASE) for pattern in sql_patterns)


def check_xss_patterns(input_string: str) -> bool:
    """
    Check for potential XSS patterns.

    Args:
        input_string: String to check

    Returns:
        True if potential XSS detected
    """
    xss_patterns = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
    ]

    return any(re.search(pattern, input_string, re.IGNORECASE) for pattern in xss_patterns)


def validate_and_sanitize_input(
    data: dict[str, Any], validation_rules: dict[str, Callable], sanitize: bool = True
) -> dict[str, Any]:
    """
    Validate and sanitize a dictionary of input data.

    Args:
        data: Input data to validate
        validation_rules: Dict mapping field names to validation functions
        sanitize: Whether to sanitize string inputs

    Returns:
        Validated and sanitized data
    """
    validator = FormValidator()

    for field_name, validation_func in validation_rules.items():
        if field_name in data:
            value = data[field_name]

            # Sanitize string inputs if requested
            if sanitize and isinstance(value, str):
                value = InputSanitizer.sanitize_text(value)

                # Check for security threats
                if check_sql_injection(value):
                    validator.add_error(field_name, "contains potentially malicious content")
                    continue

                if check_xss_patterns(value):
                    validator.add_error(field_name, "contains potentially malicious content")
                    continue

            validator.validate_field(field_name, value, validation_func)

    if not validator.is_valid():
        errors = validator.get_errors()
        first_error = next(iter(errors.values()))[0]
        first_field = next(iter(errors.keys()))
        raise InputValidationError(first_field, data.get(first_field), first_error)

    return validator.get_validated_data()
