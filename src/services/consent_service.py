"""
Consent service for study participation in GITTE system.
Provides service layer abstraction for consent management operations using pseudonyms.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID

from src.data.database import get_session
from src.data.models import StudyConsentType, StudyConsentRecord
from src.data.repositories import StudyConsentRepository
from src.logic.consent_logic import ConsentLogic

logger = logging.getLogger(__name__)


class ConsentService:
    """
    Service layer for study participation consent management.
    Handles database sessions and provides high-level consent operations using pseudonyms.
    """

    def __init__(self):
        self.consent_logic = None  # Will be initialized per request

    def _get_consent_logic(self) -> ConsentLogic:
        """Get consent logic with database session."""
        if not hasattr(self, "_session") or not self._session:
            raise RuntimeError("Service not properly initialized with session")

        if not self.consent_logic:
            consent_repository = StudyConsentRepository(self._session)
            self.consent_logic = ConsentLogic(consent_repository)

        return self.consent_logic

    def record_consent(
        self,
        pseudonym_id: UUID,
        consent_type: StudyConsentType,
        granted: bool,
        metadata: Dict[str, Any] | None = None,
    ) -> StudyConsentRecord:
        """
        Record participant consent for a specific type with proper transaction handling.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consent_type: Type of consent being recorded
            granted: Whether consent is granted or denied
            metadata: Additional consent metadata

        Returns:
            StudyConsentRecord: Created consent record

        Raises:
            ConsentError: If consent recording fails
            MissingPseudonymError: If pseudonym does not exist
        """
        try:
            with get_session() as session:
                # Begin explicit transaction
                with session.begin():
                    self._session = session
                    consent_logic = self._get_consent_logic()
                    result = consent_logic.record_consent(pseudonym_id, consent_type, granted, metadata)
                    # Transaction commits automatically on successful exit
                    return result
        except Exception as e:
            logger.error(f"Service error recording consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def withdraw_consent(
        self, 
        pseudonym_id: UUID, 
        consent_type: StudyConsentType, 
        reason: str | None = None
    ) -> bool:
        """
        Withdraw participant consent for a specific type.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
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
                return consent_logic.withdraw_consent(pseudonym_id, consent_type, reason)
        except Exception as e:
            logger.error(f"Service error withdrawing consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def check_consent(self, pseudonym_id: UUID, consent_type: StudyConsentType) -> bool:
        """
        Check if participant has given valid consent for a specific type.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consent_type: Type of consent to check

        Returns:
            bool: True if participant has valid consent
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.check_consent(pseudonym_id, consent_type)
        except Exception as e:
            logger.error(f"Service error checking consent: {e}")
            return False
        finally:
            self._session = None
            self.consent_logic = None

    def require_consent(self, pseudonym_id: UUID, consent_type: StudyConsentType) -> None:
        """
        Require consent for a specific type, raise exception if not given.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consent_type: Type of consent required

        Raises:
            ConsentRequiredError: If consent is not given
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                consent_logic.require_consent(pseudonym_id, consent_type)
        except Exception as e:
            logger.error(f"Service error requiring consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def get_consent_status(self, pseudonym_id: UUID) -> Dict[str, bool]:
        """
        Get current consent status for all consent types for a participant.

        Args:
            pseudonym_id: Pseudonym identifier for the participant

        Returns:
            Dict mapping consent types to their current status
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.get_consent_status(pseudonym_id)
        except Exception as e:
            logger.error(f"Service error getting consent status: {e}")
            return {}
        finally:
            self._session = None
            self.consent_logic = None

    def validate_consent_completeness(self, consents: List[StudyConsentType]) -> Dict[str, Any]:
        """
        Validate that all required consents are present.

        Args:
            consents: List of consent types to validate

        Returns:
            Dict containing validation results
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.validate_consent_completeness(consents)
        except Exception as e:
            logger.error(f"Service error validating consent completeness: {e}")
            return {"is_complete": False, "missing_consents": [], "error": str(e)}
        finally:
            self._session = None
            self.consent_logic = None

    def process_consent_collection(
        self, 
        pseudonym_id: UUID, 
        consents: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        Process multi-step consent collection for study participation with proper transaction handling.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consents: Dict mapping consent type strings to boolean values

        Returns:
            Dict containing processing results

        Raises:
            ConsentError: If consent processing fails
            MissingPseudonymError: If pseudonym does not exist
        """
        try:
            with get_session() as session:
                # Begin explicit transaction for bulk consent operations
                with session.begin():
                    self._session = session
                    consent_logic = self._get_consent_logic()
                    result = consent_logic.process_consent_collection(pseudonym_id, consents)
                    # Transaction commits automatically on successful exit
                    return result
        except Exception as e:
            logger.error(f"Service error processing consent collection: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None

    def check_consent_status(self, pseudonym_id: UUID) -> Dict[str, Any]:
        """
        Check comprehensive consent status for a participant.

        Args:
            pseudonym_id: Pseudonym identifier for the participant

        Returns:
            Dict containing consent status information
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.check_consent_status(pseudonym_id)
        except Exception as e:
            logger.error(f"Service error checking consent status: {e}")
            return {
                "pseudonym_id": pseudonym_id,
                "consent_status": {},
                "all_required_granted": False,
                "can_proceed_to_study": False
            }
        finally:
            self._session = None
            self.consent_logic = None

    def get_participant_consents(self, pseudonym_id: UUID) -> List[StudyConsentRecord]:
        """
        Get all consent records for a participant.

        Args:
            pseudonym_id: Pseudonym identifier for the participant

        Returns:
            List of consent records for the participant
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                return consent_logic.get_participant_consents(pseudonym_id)
        except Exception as e:
            logger.error(f"Service error getting participant consents: {e}")
            return []
        finally:
            self._session = None
            self.consent_logic = None

    def record_bulk_consent(
        self,
        pseudonym_id: UUID,
        consents: Dict[StudyConsentType, bool],
        metadata: Dict[str, Any] | None = None,
    ) -> List[StudyConsentRecord]:
        """
        Record multiple consents at once (useful for onboarding flow).

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consents: Dict mapping consent types to their values
            metadata: Additional metadata for all consents

        Returns:
            List of created consent records
        """
        try:
            with get_session() as session:
                self._session = session
                consent_logic = self._get_consent_logic()
                
                # Use transaction for bulk operations
                session.begin()
                try:
                    result = consent_logic.record_bulk_consent(pseudonym_id, consents, metadata)
                    session.commit()
                    return result
                except Exception:
                    session.rollback()
                    raise
                    
        except Exception as e:
            logger.error(f"Service error recording bulk consent: {e}")
            raise
        finally:
            self._session = None
            self.consent_logic = None


# Global consent service instance for study participation
study_consent_service = ConsentService()


def get_consent_service() -> ConsentService:
    """Get consent service instance."""
    return ConsentService()


def get_study_consent_service() -> ConsentService:
    """Get the global study consent service instance."""
    return study_consent_service


# Convenience functions for common operations
def record_consent(
    pseudonym_id: UUID,
    consent_type: StudyConsentType,
    granted: bool,
    metadata: Dict[str, Any] | None = None,
) -> StudyConsentRecord:
    """Record participant consent."""
    return study_consent_service.record_consent(pseudonym_id, consent_type, granted, metadata)


def withdraw_consent(
    pseudonym_id: UUID, 
    consent_type: StudyConsentType, 
    reason: str | None = None
) -> bool:
    """Withdraw participant consent."""
    return study_consent_service.withdraw_consent(pseudonym_id, consent_type, reason)


def check_consent(pseudonym_id: UUID, consent_type: StudyConsentType) -> bool:
    """Check if participant has given consent."""
    return study_consent_service.check_consent(pseudonym_id, consent_type)


def require_consent(pseudonym_id: UUID, consent_type: StudyConsentType) -> None:
    """Require consent, raise exception if not given."""
    study_consent_service.require_consent(pseudonym_id, consent_type)


def get_consent_status(pseudonym_id: UUID) -> Dict[str, bool]:
    """Get current consent status for all types."""
    return study_consent_service.get_consent_status(pseudonym_id)


def process_consent_collection(pseudonym_id: UUID, consents: Dict[str, bool]) -> Dict[str, Any]:
    """Process multi-step consent collection."""
    return study_consent_service.process_consent_collection(pseudonym_id, consents)


def check_consent_status(pseudonym_id: UUID) -> Dict[str, Any]:
    """Check comprehensive consent status."""
    return study_consent_service.check_consent_status(pseudonym_id)