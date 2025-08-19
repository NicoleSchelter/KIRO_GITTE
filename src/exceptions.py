"""
Custom exception hierarchy for GITTE system.
Provides structured error handling with user-friendly messages and proper categorization.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, Dict

# --- helper to avoid duplicate kwargs for super().__init__ ---
def _filtered_kwargs(kwargs, *keys):
    """Return a copy of kwargs without the given keys (no-op if kwargs is None)."""
    if not kwargs:
        return {}
    return {k: v for k, v in kwargs.items() if k not in keys}

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
    """
    Basisfehler: nimmt optionale Felder entgegen und entfernt doppelte Keys,
    falls Subklassen dieselben Argumente noch einmal via **kwargs übergeben.
    """

    def __init__(
        self,
        message: str,
        *,
        user_message: Optional[str] = None,
        category: Optional["ErrorCategory"] = None,
        severity: Optional["ErrorSeverity"] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        # Duplikate defensiv wegpoppen:
        if user_message is None:
            user_message = kwargs.pop("user_message", None)
        else:
            kwargs.pop("user_message", None)

        if category is None:
            category = kwargs.pop("category", None)
        else:
            kwargs.pop("category", None)

        if severity is None:
            severity = kwargs.pop("severity", None)
        else:
            kwargs.pop("severity", None)

        if details is None:
            details = kwargs.pop("details", None)
        else:
            kwargs.pop("details", None)

        # Übrige kwargs ignorieren (oder bei Bedarf speichern)
        super().__init__(message)

        self.message = message
        self.user_message = user_message
        self.category = category
        self.severity = severity
        self.details = details or {}

    def __str__(self) -> str:
        return self.message
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


# --- Consent errors (single source of truth) ---
class ConsentError(BusinessLogicError):
    """Consent-related errors."""

    def __init__(self, message: str, **kwargs):
        # Kategorie Privacy ist konsistenter als Authorization für Consent-Themen
        super().__init__(message, category=ErrorCategory.PRIVACY, **kwargs)
        # Optional eine nutzerfreundliche Default-Message:
        self.user_message = kwargs.get(
            "user_message", "Consent is required to proceed with this action."
        )


class ConsentRequiredError(ConsentError):
    """
    Raised when one or more consents are missing.

    message: frei wählbar (Tests erwarten "Consent required for <type>")
    required: optionale Iterable[str] für Details.
    """

    def __init__(self, message: str, required: list[str] | tuple[str, ...] | None = None, **kwargs):
        details = {"required_consents": list(required) if required else []}
        # Details aus kwargs (falls vorhanden) beibehalten/ergänzen:
        details.update(kwargs.pop("details", {}))
        super().__init__(message, details=details, **kwargs)
        # leichte, generische User-Message:
        self.user_message = kwargs.get(
            "user_message", "Please review and accept the required consents to continue."
        )


class ConsentWithdrawalError(ConsentError):
    """Raised when consent withdrawal fails."""

    def __init__(self, message: str = "Failed to withdraw consent", **kwargs):
        super().__init__(message, **kwargs)


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


# UX Enhancement Specific Exceptions


# Image Processing Errors
class ImageProcessingError(GITTEError):
    """Base class for image processing errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Image processing failed. Please try again with a different image.",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class ImageIsolationError(ImageProcessingError):
    """Image isolation specific errors."""

    def __init__(self, message: str, isolation_method: str = "unknown", **kwargs):
        super().__init__(
            f"Image isolation failed using {isolation_method}: {message}",
            details={"isolation_method": isolation_method},
            **kwargs,
        )
        self.user_message = (
            "Unable to isolate person from background. The original image will be used instead."
        )


class BackgroundRemovalError(ImageIsolationError):
    """Background removal specific errors."""

    def __init__(self, message: str, method: str = "rembg", **kwargs):
        super().__init__(
            message,
            isolation_method=method,
            user_message="Background removal failed. Using original image instead.",
            **kwargs,
        )


class PersonDetectionError(ImageProcessingError):
    """Person detection specific errors."""

    def __init__(self, message: str, detection_method: str = "hog", **kwargs):
        super().__init__(
            f"Person detection failed using {detection_method}: {message}",
            user_message="Unable to detect person in image. Please ensure the image contains a clear person.",
            details={"detection_method": detection_method},
            **kwargs,
        )


class ImageQualityError(ImageProcessingError):
    """Image quality assessment errors."""

    def __init__(self, message: str, quality_issues: list[str] = None, **kwargs):
        super().__init__(
            f"Image quality assessment failed: {message}",
            user_message="Unable to assess image quality. The image may be corrupted or in an unsupported format.",
            details={"quality_issues": quality_issues or []},
            **kwargs,
        )


class ImageTimeoutError(ImageProcessingError):
    """Image processing timeout errors."""
    def __init__(self, operation: str, timeout_seconds: int, **kwargs):
        message = f"Image {operation} timed out after {timeout_seconds} seconds"
        kw = _filtered_kwargs(kwargs, "user_message", "details", "category", "severity")
        super().__init__(message, **kw)
        self.user_message = "Image processing is taking too long. Please try with a smaller image."
        self.severity = ErrorSeverity.HIGH
        self.details.update({"operation": operation, "timeout_seconds": timeout_seconds})
class UnsupportedImageFormatError(ImageProcessingError):
    """Unsupported image format errors."""

    def __init__(self, format_detected: str, supported_formats: list[str], **kwargs):
        super().__init__(
            f"Unsupported image format: {format_detected}",
            user_message=f"Please use a supported image format: {', '.join(supported_formats)}",
            severity=ErrorSeverity.LOW,
            details={"format_detected": format_detected, "supported_formats": supported_formats},
            **kwargs,
        )


class ImageCorruptionError(ImageProcessingError):
    """Image corruption or loading errors."""

    def __init__(self, image_path: str, **kwargs):
        kw = _filtered_kwargs(kwargs, "user_message", "details", "category", "severity")
        super().__init__(
            f"Image file is corrupted or cannot be loaded: {image_path}",
            user_message="The image file appears to be corrupted. Please try uploading a different image.",
            severity=ErrorSeverity.MEDIUM,
            details={"image_path": image_path},
            **kw,
        )
# Prerequisite Check Errors
class PrerequisiteError(GITTEError):
    """Base class for prerequisite check errors."""

    def __init__(self, message: str, **kwargs):
        # Defaults, aber Werte aus kwargs respektieren
        user_message = kwargs.pop(
            "user_message",
            "System prerequisites are not met. Please check system requirements.",
        )
        category = kwargs.pop("category", ErrorCategory.SYSTEM)
        severity = kwargs.pop("severity", ErrorSeverity.HIGH)
        details = kwargs.pop("details", None)

        super().__init__(
            message,
            user_message=user_message,
            category=category,
            severity=severity,
            details=details,
            **kwargs,  # hier sind die o.g. Keys bereits gepoppt
        )


class PrerequisiteCheckFailedError(PrerequisiteError):
    """Prerequisite check execution failed."""

    def __init__(self, checker_name: str, error_details: str, **kwargs):
        kw = _filtered_kwargs(kwargs, "user_message", "details", "category", "severity")
        super().__init__(
            f"Prerequisite check failed for {checker_name}: {error_details}",
            user_message=f"Unable to verify {checker_name}. Some features may be unavailable.",
            details={"checker_name": checker_name, "error_details": error_details},
            **kw,
        )


class RequiredPrerequisiteError(PrerequisiteError):
    """Required prerequisite not met."""

    def __init__(
        self,
        prerequisite_name: str,
        resolution_steps: list[str] = None,
        **kwargs,
    ):
        kw = _filtered_kwargs(kwargs, "user_message", "details", "category", "severity")
        super().__init__(
            f"Required prerequisite not met: {prerequisite_name}",
            user_message=f"Please resolve the {prerequisite_name} requirement to continue.",
            severity=ErrorSeverity.CRITICAL,
            details={
                "prerequisite_name": prerequisite_name,
                "resolution_steps": resolution_steps or [],
            },
            **kw,
        )


class ServiceUnavailableError(PrerequisiteError):
    """External service unavailable."""

    def __init__(self, service_name: str, connection_details: str = "", **kwargs):
        kw = _filtered_kwargs(kwargs, "user_message", "details", "category", "severity")
        super().__init__(
            f"Service unavailable: {service_name}",
            user_message=f"The {service_name} service is currently unavailable. Please try again later.",
            category=ErrorCategory.EXTERNAL_SERVICE,
            details={"service_name": service_name, "connection_details": connection_details},
            **kw,
        )


# Tooltip System Errors
class TooltipError(GITTEError):
    """Base class for tooltip system errors."""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            user_message="Help system temporarily unavailable.",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )


# Batch Processing Errors
class BatchProcessingError(GITTEError):
    """Batch image processing errors."""

    def __init__(
        self,
        message: str,
        failed_images: list[str] = None,
        total_images: int = 0,
        **kwargs,
    ):
        super().__init__(
            f"Batch processing failed: {message}",
            user_message="Multiple images failed processing. Please check individual images.",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            details={
                "failed_images": failed_images or [],
                "total_images": total_images,
                "failure_rate": len(failed_images or []) / max(1, total_images),
            },
            **kwargs,
        )


class CircuitBreakerOpenError(ExternalServiceError):
    """Circuit breaker is open for service."""

    def __init__(
        self,
        service_name: str,
        failure_count: int,
        recovery_time_seconds: int,
        **kwargs,
    ):
        super().__init__(
            service_name,
            f"Circuit breaker is open after {failure_count} failures. Recovery in {recovery_time_seconds}s.",
            user_message=f"The {service_name} service is temporarily unavailable due to repeated failures. Please try again in {recovery_time_seconds} seconds.",
            severity=ErrorSeverity.HIGH,
            details={
                "failure_count": failure_count,
                "recovery_time_seconds": recovery_time_seconds,
                "circuit_state": "open",
            },
            **kwargs,
        )


class RetryExhaustedError(GITTEError):
    """All retry attempts exhausted."""

    def __init__(
        self,
        operation: str,
        max_retries: int,
        last_error: str,
        **kwargs,
    ):
        super().__init__(
            f"Operation {operation} failed after {max_retries} retries. Last error: {last_error}",
            user_message=f"Unable to complete {operation} after multiple attempts. Please try again later.",
            category=ErrorCategory.EXTERNAL_SERVICE,
            severity=ErrorSeverity.HIGH,
            details={
                "operation": operation,
                "max_retries": max_retries,
                "last_error": last_error,
            },
            **kwargs,
        )


# === PALD Exceptions & Recovery (merged) ===
# This section integrates PALD-specific exceptions while reusing the project's ErrorSeverity enum.
# It is self-contained and does not redefine ErrorSeverity.


class RecoveryStrategy(Enum):
    """Recovery strategies for error handling."""

    RETRY = "retry"
    FALLBACK_TO_DEFAULT = "fallback_to_default"
    DEFER = "defer"
    NOOP = "noop"


@dataclass
class RecoveryResult:
    """Result of a recovery operation."""

    success: bool
    strategy_used: RecoveryStrategy
    fallback_value: Any | None = None
    error_message: str | None = None


class PALDBaseException(Exception):
    """Base exception for all PALD-related errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_strategy: RecoveryStrategy = RecoveryStrategy.NOOP,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.severity = severity
        self.recovery_strategy = recovery_strategy
        self.context = context or {}


class PALDValidationError(PALDBaseException):
    """Validation errors in PALD processing."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        super().__init__(message, severity=ErrorSeverity.MEDIUM, **kwargs)
        self.field = field


class PALDProcessingError(PALDBaseException):
    """Processing errors during PALD operations."""

    def __init__(self, message: str, operation: str | None = None, **kwargs):
        super().__init__(message, severity=ErrorSeverity.HIGH, **kwargs)
        self.operation = operation


class PALDResourceError(PALDBaseException):
    """Resource-related errors (memory, disk, network)."""

    def __init__(self, message: str, resource_type: str | None = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.RETRY,
            **kwargs,
        )
        self.resource_type = resource_type


class PALDConfigurationError(PALDBaseException):
    """Configuration and setup errors."""

    def __init__(self, message: str, config_key: str | None = None, **kwargs):
        super().__init__(message, severity=ErrorSeverity.CRITICAL, **kwargs)
        self.config_key = config_key


class BiasAnalysisError(PALDBaseException):
    """Bias analysis specific errors."""

    def __init__(self, message: str, analysis_type: str | None = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.MEDIUM,
            recovery_strategy=RecoveryStrategy.FALLBACK_TO_DEFAULT,
            **kwargs,
        )
        self.analysis_type = analysis_type


class SchemaEvolutionError(PALDBaseException):
    """Schema evolution and migration errors."""

    def __init__(self, message: str, schema_version: str | None = None, **kwargs):
        super().__init__(
            message,
            severity=ErrorSeverity.HIGH,
            recovery_strategy=RecoveryStrategy.DEFER,
            **kwargs,
        )
        self.schema_version = schema_version


class RecoveryManager:
    """Manages error recovery strategies with graceful degradation."""

    @staticmethod
    def execute_recovery(error: PALDBaseException, fallback_value: Any = None) -> RecoveryResult:
        """Execute recovery strategy based on error type and configuration."""
        strategy = error.recovery_strategy

        if strategy == RecoveryStrategy.RETRY:
            # In a real implementation, this would include retry logic
            return RecoveryResult(
                success=False,
                strategy_used=strategy,
                error_message="Retry not implemented in this context",
            )

        if strategy == RecoveryStrategy.FALLBACK_TO_DEFAULT:
            return RecoveryResult(
                success=True,
                strategy_used=strategy,
                fallback_value=fallback_value,
            )

        if strategy == RecoveryStrategy.DEFER:
            return RecoveryResult(success=True, strategy_used=strategy)

        # NOOP default
        return RecoveryResult(success=False, strategy_used=strategy)
