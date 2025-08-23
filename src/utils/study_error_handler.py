"""
Comprehensive error handling and recovery system for study participation components.

This module provides:
- Centralized error handling for all study participation flows
- Retry logic with exponential backoff and circuit breakers
- Fallback strategies for critical operations
- User-friendly error messages and recovery options
- Comprehensive error logging and monitoring
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from uuid import UUID

from src.exceptions import (
    ConsentError,
    ConsentRequiredError,
    DatabaseError,
    ExternalServiceError,
    GITTEError,
    ValidationError,
)
from src.utils.ux_error_handler import RetryConfig, UXErrorHandler, record_ux_error

logger = logging.getLogger(__name__)


class StudyErrorCategory(str, Enum):
    """Error categories specific to study participation."""
    
    PSEUDONYM_CREATION = "pseudonym_creation"
    CONSENT_COLLECTION = "consent_collection"
    SURVEY_LOADING = "survey_loading"
    SURVEY_SUBMISSION = "survey_submission"
    PALD_PROCESSING = "pald_processing"
    IMAGE_GENERATION = "image_generation"
    CHAT_PROCESSING = "chat_processing"
    DATABASE_OPERATION = "database_operation"
    EXTERNAL_SERVICE = "external_service"
    VALIDATION = "validation"


class RecoveryStrategy(str, Enum):
    """Recovery strategies for different error scenarios."""
    
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK_TO_DEFAULT = "fallback_to_default"
    SKIP_OPTIONAL_STEP = "skip_optional_step"
    PROMPT_USER_RETRY = "prompt_user_retry"
    ESCALATE_TO_ADMIN = "escalate_to_admin"
    GRACEFUL_DEGRADATION = "graceful_degradation"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    
    user_id: Optional[UUID] = None
    pseudonym_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryResult:
    """Result of an error recovery attempt."""
    
    success: bool
    strategy_used: RecoveryStrategy
    result_data: Any = None
    error_message: Optional[str] = None
    retry_count: int = 0
    fallback_used: bool = False
    user_action_required: bool = False
    recovery_suggestions: List[str] = field(default_factory=list)


@dataclass
class StudyRetryConfig:
    """Retry configuration for study operations."""
    
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (DatabaseError, ExternalServiceError, ConnectionError)
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0


class StudyErrorHandler:
    """Centralized error handler for study participation components."""
    
    def __init__(self):
        self.ux_handler = UXErrorHandler(logger)
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        self.error_counts: Dict[str, int] = {}
        self.recovery_stats: Dict[str, Dict[str, int]] = {}
        
    def handle_pseudonym_error(
        self,
        error: Exception,
        context: ErrorContext,
        retry_config: Optional[StudyRetryConfig] = None
    ) -> RecoveryResult:
        """Handle pseudonym creation and validation errors."""
        
        record_ux_error("pseudonym_creation", {
            "error_type": type(error).__name__,
            "user_id": str(context.user_id) if context.user_id else None
        })
        
        if isinstance(error, ValidationError):
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                error_message="Invalid pseudonym format. Please check the requirements and try again.",
                user_action_required=True,
                recovery_suggestions=[
                    "Ensure your pseudonym follows the required format",
                    "Check that all required components are included",
                    "Try a different combination if the pseudonym already exists"
                ]
            )
        
        elif "unique" in str(error).lower() or "duplicate" in str(error).lower():
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                error_message="This pseudonym is already taken. Please choose a different one.",
                user_action_required=True,
                recovery_suggestions=[
                    "Modify one or more components of your pseudonym",
                    "Add additional numbers or characters to make it unique"
                ]
            )
        
        elif isinstance(error, DatabaseError):
            return self._handle_database_error(error, context, "pseudonym creation")
        
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.ESCALATE_TO_ADMIN,
                error_message="An unexpected error occurred during pseudonym creation. Please contact support.",
                recovery_suggestions=[
                    "Try refreshing the page and attempting again",
                    "Contact technical support if the problem persists"
                ]
            )
    
    def handle_consent_error(
        self,
        error: Exception,
        context: ErrorContext,
        retry_config: Optional[StudyRetryConfig] = None
    ) -> RecoveryResult:
        """Handle consent collection and validation errors."""
        
        record_ux_error("consent_collection", {
            "error_type": type(error).__name__,
            "pseudonym_id": str(context.pseudonym_id) if context.pseudonym_id else None
        })
        
        if isinstance(error, ConsentRequiredError):
            required_consents = getattr(error, 'details', {}).get('required_consents', [])
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                error_message="Required consents are missing. Please review and accept all required consents.",
                user_action_required=True,
                recovery_suggestions=[
                    f"Please accept consent for: {', '.join(required_consents)}" if required_consents else "Please review all consent requirements",
                    "All required consents must be accepted to continue"
                ]
            )
        
        elif isinstance(error, ConsentError):
            if "withdrawal" in str(error).lower():
                return RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategy.ESCALATE_TO_ADMIN,
                    error_message="Unable to process consent withdrawal. Please contact support.",
                    recovery_suggestions=[
                        "Contact support to manually process your consent withdrawal",
                        "Your request has been logged for manual review"
                    ]
                )
            else:
                return self._retry_with_fallback(
                    error, context, "consent collection",
                    fallback_message="Consent collection temporarily unavailable. Please try again later."
                )
        
        elif isinstance(error, DatabaseError):
            return self._handle_database_error(error, context, "consent storage")
        
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                error_message="An error occurred while processing your consent. Please try again.",
                user_action_required=True,
                recovery_suggestions=[
                    "Refresh the page and try submitting your consent again",
                    "Ensure all required fields are properly selected"
                ]
            )
    
    def handle_survey_error(
        self,
        error: Exception,
        context: ErrorContext,
        retry_config: Optional[StudyRetryConfig] = None
    ) -> RecoveryResult:
        """Handle survey loading and submission errors."""
        
        record_ux_error("survey_loading", {
            "error_type": type(error).__name__,
            "operation": context.operation
        })
        
        if isinstance(error, FileNotFoundError):
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_TO_DEFAULT,
                error_message="Survey configuration is temporarily unavailable. Using default survey.",
                fallback_used=True,
                recovery_suggestions=[
                    "A default survey will be used instead",
                    "Contact support if you need access to specific survey questions"
                ]
            )
        
        elif isinstance(error, ValidationError):
            if "response" in str(error).lower():
                return RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                    error_message="Invalid survey responses. Please check your answers and try again.",
                    user_action_required=True,
                    recovery_suggestions=[
                        "Ensure all required questions are answered",
                        "Check that numeric fields contain valid numbers",
                        "Verify that selections are made for choice questions"
                    ]
                )
            else:
                return RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategy.ESCALATE_TO_ADMIN,
                    error_message="Survey configuration error. Please contact support.",
                    recovery_suggestions=[
                        "The survey configuration needs to be updated",
                        "Contact technical support for assistance"
                    ]
                )
        
        elif isinstance(error, DatabaseError):
            return self._handle_database_error(error, context, "survey submission")
        
        else:
            return self._retry_with_fallback(
                error, context, "survey processing",
                fallback_message="Survey temporarily unavailable. Please try again later."
            )
    
    def handle_pald_error(
        self,
        error: Exception,
        context: ErrorContext,
        retry_config: Optional[StudyRetryConfig] = None
    ) -> RecoveryResult:
        """Handle PALD processing errors."""
        
        record_ux_error("pald_processing", {
            "error_type": type(error).__name__,
            "operation": context.operation
        })
        
        if "timeout" in str(error).lower():
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
                error_message="PALD processing is taking longer than expected. Continuing with simplified analysis.",
                fallback_used=True,
                recovery_suggestions=[
                    "The system will continue with basic processing",
                    "Full PALD analysis may be available later"
                ]
            )
        
        elif isinstance(error, ExternalServiceError):
            return self._retry_with_circuit_breaker(
                error, context, "pald_service",
                fallback_message="PALD service temporarily unavailable. Using cached results."
            )
        
        elif isinstance(error, ValidationError):
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.GRACEFUL_DEGRADATION,
                error_message="PALD data validation failed. Continuing with available data.",
                fallback_used=True,
                recovery_suggestions=[
                    "The system will use previously validated PALD data",
                    "Some advanced features may be temporarily unavailable"
                ]
            )
        
        else:
            return self._retry_with_fallback(
                error, context, "PALD processing",
                fallback_message="PALD processing temporarily unavailable. Basic functionality will continue."
            )
    
    def handle_image_generation_error(
        self,
        error: Exception,
        context: ErrorContext,
        retry_config: Optional[StudyRetryConfig] = None
    ) -> RecoveryResult:
        """Handle image generation errors."""
        
        record_ux_error("image_processing", {
            "error_type": type(error).__name__,
            "operation": context.operation
        })
        
        if "timeout" in str(error).lower():
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_WITH_BACKOFF,
                error_message="Image generation timed out. Retrying with reduced parameters.",
                retry_count=1,
                recovery_suggestions=[
                    "The system will retry with simpler parameters",
                    "This may result in a less detailed image"
                ]
            )
        
        elif isinstance(error, ExternalServiceError):
            return self._retry_with_circuit_breaker(
                error, context, "image_generation",
                fallback_message="Image generation service unavailable. Using placeholder image."
            )
        
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_TO_DEFAULT,
                error_message="Unable to generate custom image. Using default placeholder.",
                fallback_used=True,
                recovery_suggestions=[
                    "A default image will be used instead",
                    "You can try generating a custom image again later"
                ]
            )
    
    def handle_chat_error(
        self,
        error: Exception,
        context: ErrorContext,
        retry_config: Optional[StudyRetryConfig] = None
    ) -> RecoveryResult:
        """Handle chat processing errors."""
        
        record_ux_error("chat_processing", {
            "error_type": type(error).__name__,
            "session_id": str(context.session_id) if context.session_id else None
        })
        
        if isinstance(error, ExternalServiceError):
            return self._retry_with_circuit_breaker(
                error, context, "chat_service",
                fallback_message="Chat service temporarily unavailable. Please try again in a moment."
            )
        
        elif "rate limit" in str(error).lower():
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                error_message="Too many requests. Please wait a moment before sending another message.",
                user_action_required=True,
                recovery_suggestions=[
                    "Wait 30 seconds before sending another message",
                    "The system will be available again shortly"
                ]
            )
        
        elif isinstance(error, ValidationError):
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                error_message="Invalid message format. Please check your input and try again.",
                user_action_required=True,
                recovery_suggestions=[
                    "Ensure your message is not empty",
                    "Check for any special characters that might cause issues"
                ]
            )
        
        else:
            return self._retry_with_fallback(
                error, context, "chat processing",
                fallback_message="Chat temporarily unavailable. Please try again later."
            )
    
    def _handle_database_error(
        self,
        error: Exception,
        context: ErrorContext,
        operation: str
    ) -> RecoveryResult:
        """Handle database-specific errors with appropriate recovery strategies."""
        
        error_msg = str(error).lower()
        
        if "connection" in error_msg or "timeout" in error_msg:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_WITH_BACKOFF,
                error_message=f"Database connection issue during {operation}. Retrying...",
                retry_count=1,
                recovery_suggestions=[
                    "The system will automatically retry the operation",
                    "Please wait a moment for the connection to be restored"
                ]
            )
        
        elif "constraint" in error_msg or "unique" in error_msg:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.PROMPT_USER_RETRY,
                error_message=f"Data conflict during {operation}. Please modify your input and try again.",
                user_action_required=True,
                recovery_suggestions=[
                    "The data you're trying to save conflicts with existing records",
                    "Please modify your input to resolve the conflict"
                ]
            )
        
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.ESCALATE_TO_ADMIN,
                error_message=f"Database error during {operation}. Please contact support.",
                recovery_suggestions=[
                    "A technical issue has occurred with data storage",
                    "Contact support for assistance with this operation"
                ]
            )
    
    def _retry_with_fallback(
        self,
        error: Exception,
        context: ErrorContext,
        operation: str,
        fallback_message: str
    ) -> RecoveryResult:
        """Implement retry logic with fallback strategy."""
        
        retry_count = context.metadata.get("retry_count", 0)
        max_retries = 3
        
        if retry_count < max_retries:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_WITH_BACKOFF,
                error_message=f"Retrying {operation}... (attempt {retry_count + 1}/{max_retries})",
                retry_count=retry_count + 1,
                recovery_suggestions=[
                    f"Automatically retrying the operation",
                    f"Will fallback to alternative if retries fail"
                ]
            )
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_TO_DEFAULT,
                error_message=fallback_message,
                fallback_used=True,
                recovery_suggestions=[
                    "Maximum retries reached, using fallback option",
                    "You can try the operation again later"
                ]
            )
    
    def _retry_with_circuit_breaker(
        self,
        error: Exception,
        context: ErrorContext,
        service_name: str,
        fallback_message: str
    ) -> RecoveryResult:
        """Implement circuit breaker pattern for external services."""
        
        if service_name not in self.circuit_breakers:
            self.circuit_breakers[service_name] = {
                "failure_count": 0,
                "last_failure": 0,
                "state": "closed"  # closed, open, half-open
            }
        
        cb = self.circuit_breakers[service_name]
        current_time = time.time()
        
        # Check if circuit breaker should be opened
        cb["failure_count"] += 1
        cb["last_failure"] = current_time
        
        if cb["failure_count"] >= 5 and cb["state"] == "closed":
            cb["state"] = "open"
            logger.warning(f"Circuit breaker opened for {service_name}")
        
        # Check if circuit breaker should be half-opened
        elif cb["state"] == "open" and (current_time - cb["last_failure"]) > 60:
            cb["state"] = "half-open"
            logger.info(f"Circuit breaker half-opened for {service_name}")
        
        if cb["state"] == "open":
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.FALLBACK_TO_DEFAULT,
                error_message=fallback_message,
                fallback_used=True,
                recovery_suggestions=[
                    f"The {service_name} service is temporarily unavailable",
                    "Using fallback functionality until service is restored"
                ]
            )
        else:
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.RETRY_WITH_BACKOFF,
                error_message=f"Service temporarily unavailable. Retrying...",
                retry_count=1,
                recovery_suggestions=[
                    "The system will automatically retry the operation",
                    "Service should be available again shortly"
                ]
            )
    
    @contextmanager
    def error_boundary(
        self,
        category: StudyErrorCategory,
        context: ErrorContext,
        retry_config: Optional[StudyRetryConfig] = None
    ):
        """Context manager for comprehensive error handling."""
        
        try:
            yield
        except Exception as error:
            logger.error(f"Error in {category.value}: {error}", exc_info=True)
            
            # Route to appropriate error handler
            if category == StudyErrorCategory.PSEUDONYM_CREATION:
                recovery_result = self.handle_pseudonym_error(error, context, retry_config)
            elif category == StudyErrorCategory.CONSENT_COLLECTION:
                recovery_result = self.handle_consent_error(error, context, retry_config)
            elif category in [StudyErrorCategory.SURVEY_LOADING, StudyErrorCategory.SURVEY_SUBMISSION]:
                recovery_result = self.handle_survey_error(error, context, retry_config)
            elif category == StudyErrorCategory.PALD_PROCESSING:
                recovery_result = self.handle_pald_error(error, context, retry_config)
            elif category == StudyErrorCategory.IMAGE_GENERATION:
                recovery_result = self.handle_image_generation_error(error, context, retry_config)
            elif category == StudyErrorCategory.CHAT_PROCESSING:
                recovery_result = self.handle_chat_error(error, context, retry_config)
            else:
                # Generic error handling
                recovery_result = RecoveryResult(
                    success=False,
                    strategy_used=RecoveryStrategy.ESCALATE_TO_ADMIN,
                    error_message="An unexpected error occurred. Please contact support.",
                    recovery_suggestions=[
                        "Try refreshing the page and attempting the operation again",
                        "Contact technical support if the problem persists"
                    ]
                )
            
            # Update recovery statistics
            self._update_recovery_stats(category.value, recovery_result.strategy_used.value)
            
            # Re-raise with recovery information attached
            if hasattr(error, 'recovery_result'):
                error.recovery_result = recovery_result
            else:
                # Create a new exception with recovery information
                enhanced_error = GITTEError(
                    str(error),
                    user_message=recovery_result.error_message,
                    details={"recovery_result": recovery_result}
                )
                enhanced_error.__cause__ = error
                raise enhanced_error from error
    
    def _update_recovery_stats(self, category: str, strategy: str):
        """Update recovery statistics for monitoring."""
        
        if category not in self.recovery_stats:
            self.recovery_stats[category] = {}
        
        if strategy not in self.recovery_stats[category]:
            self.recovery_stats[category][strategy] = 0
        
        self.recovery_stats[category][strategy] += 1
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics for monitoring and analysis."""
        
        return {
            "recovery_stats": dict(self.recovery_stats),
            "circuit_breakers": {
                name: {
                    "state": cb["state"],
                    "failure_count": cb["failure_count"],
                    "last_failure": cb["last_failure"]
                }
                for name, cb in self.circuit_breakers.items()
            },
            "error_counts": dict(self.error_counts)
        }


# Decorators for easy error handling
def with_study_error_handling(
    category: StudyErrorCategory,
    context_factory: Optional[Callable[..., ErrorContext]] = None,
    retry_config: Optional[StudyRetryConfig] = None
):
    """Decorator for adding comprehensive error handling to study functions."""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = StudyErrorHandler()
            
            # Create context from factory or use default
            if context_factory:
                context = context_factory(*args, **kwargs)
            else:
                context = ErrorContext(
                    operation=func.__name__,
                    component=func.__module__
                )
            
            with handler.error_boundary(category, context, retry_config):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Module-level instance for convenience
study_error_handler = StudyErrorHandler()