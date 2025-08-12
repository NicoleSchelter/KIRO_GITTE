"""
Custom exception hierarchy for GITTE system.
Provides structured error handling with user-friendly messages and proper categorization.
"""

from enum import Enum
from typing import Any


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""

    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    PRIVACY = "privacy"


class GITTEError(Exception):
    """Base exception for all GITTE system errors."""

    def __init__(
        self,
        message: str,
        user_message: str | None = None,
        error_code: str | None = None,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.user_message = user_message or self._get_default_user_message()
        self.error_code = error_code or self._generate_error_code()
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.cause = cause

    def _get_default_user_message(self) -> str:
        """Get default user-friendly message."""
        return "An error occurred. Please try again or contact support if the problem persists."

    def _generate_error_code(self) -> str:
        """Generate error code based on exception class."""
        return f"GITTE_{self.__class__.__name__.upper()}"

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None,
        }


# Authentication and Authorization Errors
class AuthenticationError(GITTEError):
    """Base class for authentication errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Authentication failed. Please check your credentials.",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password."""

    def __init__(self, **kwargs):
        super().__init__("Invalid username or password provided", **kwargs)
        self.user_message = "Invalid username or password. Please try again."


class SessionExpiredError(AuthenticationError):
    """User session has expired."""

    def __init__(self, **kwargs):
        super().__init__("User session has expired", **kwargs)
        self.user_message = "Your session has expired. Please log in again."


class InactiveUserError(AuthenticationError):
    """User account is inactive."""

    def __init__(self, **kwargs):
        super().__init__(
            "User account is inactive",
            user_message="Your account is inactive. Please contact support.",
            **kwargs,
        )


class AuthorizationError(GITTEError):
    """Base class for authorization errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="You don't have permission to perform this action.",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class InsufficientPermissionsError(AuthorizationError):
    """User lacks required permissions."""

    def __init__(self, required_permission: str, **kwargs):
        super().__init__(
            f"User lacks required permission: {required_permission}",
            details={"required_permission": required_permission},
            **kwargs,
        )


# Validation Errors
class ValidationError(GITTEError):
    """Base class for validation errors."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        super().__init__(
            message,
            user_message="Invalid input provided. Please check your data and try again.",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details={"field": field} if field else {},
            **kwargs,
        )


class InvalidInputError(ValidationError):
    """Invalid user input."""

    def __init__(self, field: str, value: Any, reason: str, **kwargs):
        super().__init__(f"Invalid value for field '{field}': {reason}", field=field, **kwargs)
        self.user_message = f"Invalid {field}: {reason}"
        self.details.update({"field": field, "value": str(value), "reason": reason})


class MissingRequiredFieldError(ValidationError):
    """Required field is missing."""

    def __init__(self, field: str, **kwargs):
        super().__init__(f"Required field '{field}' is missing", field=field, **kwargs)
        self.user_message = f"Please provide a value for {field}."
        self.details.update({"field": field})


# Business Logic Errors
class BusinessLogicError(GITTEError):
    """Base class for business logic errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.BUSINESS_LOGIC, severity=ErrorSeverity.MEDIUM, **kwargs
        )


class ConsentError(BusinessLogicError):
    """Consent-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Consent is required to proceed with this action.",
            category=ErrorCategory.PRIVACY,
            **kwargs,
        )


class ConsentRequiredError(ConsentError):
    """Required consent not provided."""

    def __init__(self, consent_type: str, **kwargs):
        super().__init__(
            f"Required consent not provided: {consent_type}",
            user_message=f"Please provide consent for {consent_type} to continue.",
            details={"consent_type": consent_type},
            **kwargs,
        )


class OnboardingError(BusinessLogicError):
    """Onboarding-related errors."""

    pass


class OnboardingFlowError(OnboardingError):
    """Onboarding flow errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="There was an issue with the onboarding process. Please try again.",
            **kwargs,
        )


class OnboardingStateError(OnboardingError):
    """Onboarding state errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Unable to determine onboarding status. Please refresh the page.",
            **kwargs,
        )


# External Service Errors
class ExternalServiceError(GITTEError):
    """Base class for external service errors."""

    def __init__(self, service_name: str, message: str, **kwargs):
        super().__init__(
            f"{service_name}: {message}",
            user_message="An external service is temporarily unavailable. Please try again later.",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            details={"service_name": service_name},
            **kwargs,
        )


class LLMProviderError(ExternalServiceError):
    """LLM provider errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__("LLM Provider", message, **kwargs)
        self.user_message = "The AI service is temporarily unavailable. Please try again later."


class LLMTimeoutError(LLMProviderError):
    """LLM request timeout."""

    def __init__(self, timeout_seconds: int, **kwargs):
        super().__init__(f"Request timed out after {timeout_seconds} seconds", **kwargs)
        self.user_message = "The AI service is taking too long to respond. Please try again."
        self.details.update({"timeout_seconds": timeout_seconds})


class LLMConnectionError(LLMProviderError):
    """LLM connection error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"Connection failed: {message}",
            user_message="Unable to connect to the AI service. Please check your connection and try again.",
            **kwargs,
        )


class LLMModelError(LLMProviderError):
    """LLM model error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(f"Model error: {message}", **kwargs)
        self.user_message = "The requested AI model is not available. Please try again later."


class ImageProviderError(ExternalServiceError):
    """Image provider errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            "Image Provider",
            message,
            user_message="The image generation service is temporarily unavailable. Please try again later.",
            **kwargs,
        )


class ImageGenerationError(ImageProviderError):
    """Image generation specific error."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            f"Image generation failed: {message}",
            user_message="Unable to generate image. Please try again with different settings.",
            **kwargs,
        )


# Database Errors
class DatabaseError(GITTEError):
    """Base class for database errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="A database error occurred. Please try again later.",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class DatabaseConnectionError(DatabaseError):
    """Database connection error."""

    def __init__(self, **kwargs):
        super().__init__("Unable to connect to database", **kwargs)
        self.severity = ErrorSeverity.CRITICAL
        self.user_message = "Database is temporarily unavailable. Please try again later."


class RecordNotFoundError(DatabaseError):
    """Database record not found."""

    def __init__(self, entity_type: str, identifier: str, **kwargs):
        super().__init__(
            f"{entity_type} with identifier '{identifier}' not found",
            user_message="The requested item was not found.",
            severity=ErrorSeverity.LOW,
            details={"entity_type": entity_type, "identifier": identifier},
            **kwargs,
        )


class DuplicateRecordError(DatabaseError):
    """Duplicate database record."""

    def __init__(self, entity_type: str, field: str, value: str, **kwargs):
        super().__init__(
            f"Duplicate {entity_type}: {field} '{value}' already exists",
            user_message=f"A {entity_type} with this {field} already exists.",
            severity=ErrorSeverity.LOW,
            details={"entity_type": entity_type, "field": field, "value": value},
            **kwargs,
        )


# Network Errors
class NetworkError(GITTEError):
    """Base class for network errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Network error occurred. Please check your connection and try again.",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class ConnectionTimeoutError(NetworkError):
    """Network connection timeout."""

    def __init__(self, timeout_seconds: int, **kwargs):
        super().__init__(
            f"Connection timed out after {timeout_seconds} seconds",
            details={"timeout_seconds": timeout_seconds},
            **kwargs,
        )


# System Errors
class SystemError(GITTEError):
    """Base class for system errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="A system error occurred. Please try again later.",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class ConfigurationError(SystemError):
    """System configuration error."""

    def __init__(self, setting: str, **kwargs):
        super().__init__(f"Invalid configuration for setting: {setting}", **kwargs)
        self.severity = ErrorSeverity.CRITICAL
        self.user_message = "System configuration error. Please contact support."
        self.details.update({"setting": setting})


class ResourceExhaustedError(SystemError):
    """System resources exhausted."""

    def __init__(self, resource: str, **kwargs):
        super().__init__(
            f"System resource exhausted: {resource}",
            user_message="System is temporarily overloaded. Please try again later.",
            severity=ErrorSeverity.CRITICAL,
            details={"resource": resource},
            **kwargs,
        )


# User Input Errors
class UserInputError(GITTEError):
    """Base class for user input errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, category=ErrorCategory.USER_INPUT, severity=ErrorSeverity.LOW, **kwargs
        )


class InvalidFileFormatError(UserInputError):
    """Invalid file format provided."""

    def __init__(self, expected_format: str, actual_format: str, **kwargs):
        super().__init__(
            f"Invalid file format. Expected {expected_format}, got {actual_format}",
            user_message=f"Please provide a {expected_format} file.",
            details={"expected_format": expected_format, "actual_format": actual_format},
            **kwargs,
        )


class FileSizeExceededError(UserInputError):
    """File size exceeds limit."""

    def __init__(self, max_size_mb: int, actual_size_mb: float, **kwargs):
        super().__init__(
            f"File size {actual_size_mb:.1f}MB exceeds limit of {max_size_mb}MB",
            user_message=f"File size must be less than {max_size_mb}MB.",
            details={"max_size_mb": max_size_mb, "actual_size_mb": actual_size_mb},
            **kwargs,
        )


# Privacy and Security Errors
class PrivacyError(GITTEError):
    """Base class for privacy-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Privacy policy violation. Please review your request.",
            category=ErrorCategory.PRIVACY,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class DataRetentionError(PrivacyError):
    """Data retention policy violation."""

    def __init__(self, data_type: str, retention_days: int, **kwargs):
        super().__init__(
            f"Data retention limit exceeded for {data_type} (limit: {retention_days} days)",
            user_message="Data retention limit exceeded. Some data may be automatically deleted.",
            details={"data_type": data_type, "retention_days": retention_days},
            **kwargs,
        )


class SecurityError(GITTEError):
    """Base class for security-related errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Security violation detected. Please contact support.",
            category=ErrorCategory.PRIVACY,
            severity=ErrorSeverity.CRITICAL,
            **kwargs,
        )


class RateLimitExceededError(SecurityError):
    """Rate limit exceeded."""

    def __init__(self, limit: int, window_seconds: int, **kwargs):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window_seconds} seconds",
            user_message=f"Too many requests. Please wait {window_seconds} seconds before trying again.",
            details={"limit": limit, "window_seconds": window_seconds},
            **kwargs,
        )


class SuspiciousActivityError(SecurityError):
    """Suspicious activity detected."""

    def __init__(self, activity_type: str, **kwargs):
        super().__init__(
            f"Suspicious activity detected: {activity_type}",
            user_message="Suspicious activity detected. Your account may be temporarily restricted.",
            details={"activity_type": activity_type},
            **kwargs,
        )
