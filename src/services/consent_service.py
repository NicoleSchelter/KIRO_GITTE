"""
Consent service for GITTE system.
Provides service layer abstraction for consent management operations.
"""

import logging
from typing import Any
from uuid import UUID

from src.data.database import get_session
from src.data.models import ConsentType
from src.data.repositories import ConsentRepository
from src.data.schemas import ConsentRecordResponse
from src.logic.consent import ConsentLogic

logger = logging.getLogger(__name__)


class ConsentService:
    """
    Service layer for consent management.
    Handles database sessions and provides high-level consent operations.
    """

    def __init__(self):
        self.consent_logic = None  # Will be initialized per request

    def _get_consent_logic(self) -> ConsentLogic:
        """Get consent logic with database session."""
        if not hasattr(self, "_session") or not self._session:
            raise RuntimeError("Service not properly initialized with session")

        if not self.consent_logic:
            consent_repository = ConsentRepository(self._session)
            self.consent_logic = ConsentLogic(consent_repository)

        return self.consent_logic

    def record_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
        consent_given: bool,
        metadata: dict[str, Any] | None = None,
    ) -> ConsentRecordResponse:
        """
        Record user consent for a specific type.

        Args:
            user_id: User identifier
            consent_type: Type of consent being recorded
            consent_given: Whether consent is given or denied
            metadata: Additional consent metadata

        Returns:
            ConsentRecordResponse: Created consent record

        Raises:
            ConsentError: If consent recording fails
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.record_consent(user_id, consent_type, consent_given, metadata)
        except Exception as e:
            logger.error(f"Service error recording consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def withdraw_consent(
        self, user_id: UUID, consent_type: ConsentType, reason: str | None = None
    ) -> bool:
        """
        Withdraw user consent for a specific type.

        Args:
            user_id: User identifier
            consent_type: Type of consent to withdraw
            reason: Optional reason for withdrawal

        Returns:
            bool: True if withdrawal successful

        Raises:
            ConsentWithdrawalError: If withdrawal fails
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.withdraw_consent(user_id, consent_type, reason)
        except Exception as e:
            logger.error(f"Service error withdrawing consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def check_consent(self, user_id: UUID, consent_type: ConsentType) -> bool:
        """
        Check if user has given valid consent for a specific type.

        Args:
            user_id: User identifier
            consent_type: Type of consent to check

        Returns:
            bool: True if user has valid consent
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.check_consent(user_id, consent_type)
        except Exception as e:
            logger.error(f"Service error checking consent: {e}")
            return False
        finally:
            self._session = None
            self.consent_logic = None

    def require_consent(self, user_id: UUID, consent_type: ConsentType) -> None:
        """
        Require consent for a specific type, raise exception if not given.

        Args:
            user_id: User identifier
            consent_type: Type of consent required

        Raises:
            ConsentRequiredError: If consent is not given
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                consent_logic.require_consent(user_id, consent_type)
        except Exception as e:
            logger.error(f"Service error requiring consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def get_user_consents(self, user_id: UUID) -> list[ConsentRecordResponse]:
        """
        Get all consent records for a user.

        Args:
            user_id: User identifier

        Returns:
            List of consent records for the user
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.get_user_consents(user_id)
        except Exception as e:
            logger.error(f"Service error getting user consents: {e}")
            return []
        finally:
            self._session = None
            self.consent_logic = None

    def get_consent_status(self, user_id: UUID) -> dict[str, bool]:
        """
        Get current consent status for all consent types for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict mapping consent types to their current status
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.get_consent_status(user_id)
        except Exception as e:
            logger.error(f"Service error getting consent status: {e}")
            return {}
        finally:
            self._session = None
            self.consent_logic = None

    def check_operation_consent(self, user_id: UUID, operation: str) -> bool:
        """
        Check if user has all required consents for a specific operation.

        Args:
            user_id: User identifier
            operation: Operation name

        Returns:
            bool: True if user has all required consents
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.check_operation_consent(user_id, operation)
        except Exception as e:
            logger.error(f"Service error checking operation consent: {e}")
            return False
        finally:
            self._session = None
            self.consent_logic = None

    def require_operation_consent(self, user_id: UUID, operation: str) -> None:
        """
        Require all consents for a specific operation.

        Args:
            user_id: User identifier
            operation: Operation name

        Raises:
            ConsentRequiredError: If any required consent is missing
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                consent_logic.require_operation_consent(user_id, operation)
        except Exception as e:
            logger.error(f"Service error requiring operation consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def record_bulk_consent(
        self,
        user_id: UUID,
        consents: dict[ConsentType, bool],
        metadata: dict[str, Any] | None = None,
    ) -> list[ConsentRecordResponse]:
        """
        Record multiple consents at once (useful for onboarding flow).

        Args:
            user_id: User identifier
            consents: Dict mapping consent types to their values
            metadata: Additional metadata for all consents

        Returns:
            List of created consent records
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.record_bulk_consent(user_id, consents, metadata)
        except Exception as e:
            logger.error(f"Service error recording bulk consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def get_consent_summary(self, user_id: UUID) -> dict[str, Any]:
        """
        Get a comprehensive consent summary for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict containing consent summary information
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.get_consent_summary(user_id)
        except Exception as e:
            logger.error(f"Service error getting consent summary: {e}")
            return {}
        finally:
            self._session = None
            self.consent_logic = None

    def get_required_consents_for_operation(self, operation: str) -> list[ConsentType]:
        """
        Get required consent types for a specific operation.

        Args:
            operation: Operation name

        Returns:
            List of required consent types
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.get_required_consents_for_operation(operation)
        except Exception as e:
            logger.error(f"Service error getting required consents: {e}")
            return []
        finally:
            self._session = None
            self.consent_logic = None

    def is_consent_gate_enabled(self) -> bool:
        """
        Check if consent gate is enabled via feature flag.

        Returns:
            bool: True if consent gate is enabled
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.is_consent_gate_enabled()
        except Exception as e:
            logger.error(f"Service error checking consent gate status: {e}")
            return False
        finally:
            self._session = None
            self.consent_logic = None


# Global consent service instance
consent_service = ConsentService()


def get_consent_service() -> ConsentService:
    """Get the global consent service instance."""
    return consent_service


# Convenience functions for common operations
def record_consent(
    user_id: UUID,
    consent_type: ConsentType,
    consent_given: bool,
    metadata: dict[str, Any] | None = None,
) -> ConsentRecordResponse:
    """Record user consent."""
    return consent_service.record_consent(user_id, consent_type, consent_given, metadata)


def withdraw_consent(user_id: UUID, consent_type: ConsentType, reason: str | None = None) -> bool:
    """Withdraw user consent."""
    return consent_service.withdraw_consent(user_id, consent_type, reason)


def check_consent(user_id: UUID, consent_type: ConsentType) -> bool:
    """Check if user has given consent."""
    return consent_service.check_consent(user_id, consent_type)


def require_consent(user_id: UUID, consent_type: ConsentType) -> None:
    """Require consent, raise exception if not given."""
    consent_service.require_consent(user_id, consent_type)


def check_operation_consent(user_id: UUID, operation: str) -> bool:
    """Check if user has all required consents for an operation."""
    return consent_service.check_operation_consent(user_id, operation)


def require_operation_consent(user_id: UUID, operation: str) -> None:
    """Require all consents for an operation."""
    consent_service.require_operation_consent(user_id, operation)


def get_consent_status(user_id: UUID) -> dict[str, bool]:
    """Get current consent status for all types."""
    return consent_service.get_consent_status(user_id)


def get_consent_summary(user_id: UUID) -> dict[str, Any]:
    """Get comprehensive consent summary."""
    return consent_service.get_consent_summary(user_id)
