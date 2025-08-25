"""
Consent middleware for GITTE system.
Provides decorators and middleware functions for consent checking across operations.
"""

import logging
from collections.abc import Callable
from functools import wraps
from uuid import UUID

from config.config import config
from src.data.models import ConsentType
from src.services.consent_service import get_consent_service

logger = logging.getLogger(__name__)


class ConsentMiddleware:
    """Middleware for consent checking and enforcement."""

    def __init__(self):
        self.consent_service = get_consent_service()

    def require_consent_decorator(self, consent_type: ConsentType):
        """
        Decorator to require specific consent type for a function.

        Args:
            consent_type: Required consent type

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user_id from function arguments
                user_id = self._extract_user_id(args, kwargs)
                if user_id:
                    self.consent_service.require_consent(user_id, consent_type)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def require_operation_consent_decorator(self, operation: str):
        """
        Decorator to require all consents for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user_id from function arguments
                user_id = self._extract_user_id(args, kwargs)
                if user_id:
                    self.consent_service.require_operation_consent(user_id, operation)
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def check_consent_gate(self, user_id: UUID, operation: str) -> bool:
        """
        Check if user can perform operation based on consent gate.

        Args:
            user_id: User identifier
            operation: Operation name

        Returns:
            bool: True if user can perform operation
        """
        try:
            if not self.consent_service.is_consent_gate_enabled():
                return True  # Consent gate disabled

            return self.consent_service.check_operation_consent(user_id, operation)
        except Exception as e:
            logger.error(
                f"Error checking consent gate for user {user_id}, operation {operation}: {e}"
            )
            return False

    def enforce_consent_gate(self, user_id: UUID, operation: str) -> None:
        """
        Enforce consent gate for an operation.

        Args:
            user_id: User identifier
            operation: Operation name

        Raises:
            ConsentRequiredError: If required consent is missing
        """
        if not self.consent_service.is_consent_gate_enabled():
            return  # Consent gate disabled

        self.consent_service.require_operation_consent(user_id, operation)

    def get_missing_consents(self, user_id: UUID, operation: str) -> list[ConsentType]:
        """
        Get list of missing consents for an operation.

        Args:
            user_id: User identifier
            operation: Operation name

        Returns:
            List of missing consent types
        """
        try:
            required_consents = self.consent_service.get_required_consents_for_operation(operation)
            missing_consents = []

            for consent_type in required_consents:
                if not self.consent_service.check_consent(user_id, consent_type):
                    missing_consents.append(consent_type)

            return missing_consents
        except Exception as e:
            logger.error(
                f"Error getting missing consents for user {user_id}, operation {operation}: {e}"
            )
            return required_consents  # Assume all are missing on error

    def _extract_user_id(self, args: tuple, kwargs: dict) -> UUID | None:
        """
        Extract user_id from function arguments.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            UUID: User ID if found, None otherwise
        """
        # Check kwargs first
        if "user_id" in kwargs:
            return kwargs["user_id"]

        # Check positional arguments (common patterns)
        if args:
            # First argument is often user_id
            if isinstance(args[0], UUID):
                return args[0]

            # Check if first argument has user_id attribute (like user object)
            if hasattr(args[0], "user_id"):
                return args[0].user_id

            # Check if first argument has id attribute and looks like a user
            if hasattr(args[0], "id") and hasattr(args[0], "username"):
                return args[0].id

        return None


# Global middleware instance
consent_middleware = ConsentMiddleware()


# Decorator functions for easy use
def require_consent(consent_type: ConsentType):
    """Decorator to require specific consent type."""
    return consent_middleware.require_consent_decorator(consent_type)


def require_operation_consent(operation: str):
    """Decorator to require all consents for an operation."""
    return consent_middleware.require_operation_consent_decorator(operation)


def require_data_processing_consent(func: Callable) -> Callable:
    """Decorator to require data processing consent."""
    return require_consent(ConsentType.DATA_PROCESSING)(func)


def require_ai_interaction_consent(func: Callable) -> Callable:
    """Decorator to require AI interaction consent."""
    return require_consent(ConsentType.AI_INTERACTION)(func)


def require_federated_learning_consent(func: Callable) -> Callable:
    """Decorator to require federated learning consent."""
    return require_consent(ConsentType.FEDERATED_LEARNING)(func)


def require_analytics_consent(func: Callable) -> Callable:
    """Decorator to require analytics consent."""
    return require_consent(ConsentType.ANALYTICS)(func)


def require_chat_consent(func: Callable) -> Callable:
    """Decorator to require chat operation consent."""
    return require_operation_consent("chat")(func)


def require_image_gen_consent(func: Callable) -> Callable:
    """Decorator to require image generation operation consent."""
    return require_operation_consent("image_generation")(func)


def require_survey_consent(func: Callable) -> Callable:
    """Decorator to require survey operation consent."""
    return require_operation_consent("survey")(func)


# Utility functions
def check_consent_gate(user_id: UUID, operation: str) -> bool:
    """Check if user can perform operation based on consent gate."""
    return consent_middleware.check_consent_gate(user_id, operation)


def enforce_consent_gate(user_id: UUID, operation: str) -> None:
    """Enforce consent gate for an operation."""
    consent_middleware.enforce_consent_gate(user_id, operation)


def get_missing_consents(user_id: UUID, operation: str) -> list[ConsentType]:
    """Get list of missing consents for an operation."""
    return consent_middleware.get_missing_consents(user_id, operation)


def is_consent_gate_enabled() -> bool:
    """Check if consent gate is enabled."""
    return config.get_feature_flag("enable_consent_gate")


# Context manager for consent checking
class ConsentContext:
    """Context manager for consent checking within a block of code."""

    def __init__(self, user_id: UUID, operation: str):
        self.user_id = user_id
        self.operation = operation

    def __enter__(self):
        enforce_consent_gate(self.user_id, self.operation)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Could add logging or cleanup here if needed
        pass


def with_consent_check(user_id: UUID, operation: str):
    """Context manager for consent checking."""
    return ConsentContext(user_id, operation)
