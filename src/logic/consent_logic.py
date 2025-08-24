"""
Consent management logic for study participation in GITTE system.
Handles consent recording, withdrawal, checking, and GDPR compliance for pseudonymized study data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from uuid import UUID
from datetime import datetime

from src.data.models import StudyConsentType, StudyConsentRecord
from src.data.repositories import StudyConsentRepository
from src.exceptions import ConsentError, ConsentRequiredError, ConsentWithdrawalError, MissingPseudonymError

logger = logging.getLogger(__name__)


class InvalidConsentTypeError(ConsentError):
    """Raised when an invalid consent type is provided."""
    
    def __init__(self, invalid_type: str, valid_types: List[str]):
        valid_list = ", ".join(valid_types)
        message = f"Invalid consent type '{invalid_type}'. Valid types: {valid_list}"
        super().__init__(message)
        self.invalid_type = invalid_type
        self.valid_types = valid_types


class ConsentLogic:
    """
    Consent management business logic for study participation with comprehensive error handling.
    
    This class handles consent operations using pseudonym_id instead of user_id
    to maintain privacy separation for research data.
    """

    def __init__(self, consent_repository: StudyConsentRepository):
        self.consent_repository = consent_repository
        self.current_consent_version = "1.0"  # Should be configurable
        
        # Central alias mapping for consent key normalization
        self._consent_aliases = {
            # UI may use these keys, but we normalize to canonical enum values
            "data_processing": StudyConsentType.DATA_PROTECTION,
            "data_protection": StudyConsentType.DATA_PROTECTION,
            "ai_interaction": StudyConsentType.AI_INTERACTION,
            "study_participation": StudyConsentType.STUDY_PARTICIPATION,
        }

    def _normalize_consent_key(self, consent_key: str) -> StudyConsentType:
        """
        Normalize consent key string to canonical StudyConsentType enum.
        
        Args:
            consent_key: String key from UI or external source
            
        Returns:
            StudyConsentType: Canonical enum value
            
        Raises:
            InvalidConsentTypeError: If key cannot be normalized
        """
        # Try direct enum lookup first
        try:
            return StudyConsentType(consent_key)
        except ValueError:
            pass
            
        # Try alias mapping
        if consent_key in self._consent_aliases:
            canonical_type = self._consent_aliases[consent_key]
            logger.debug(f"Normalized consent key '{consent_key}' to '{canonical_type.value}'")
            return canonical_type
            
        # Invalid key
        valid_keys = list(self._consent_aliases.keys()) + [e.value for e in StudyConsentType]
        raise InvalidConsentTypeError(consent_key, valid_keys)

    def record_consent(
        self,
        pseudonym_id: UUID,
        consent_type: StudyConsentType,
        granted: bool,
        metadata: Dict[str, Any] | None = None,
    ) -> StudyConsentRecord:
        """
        Record consent for a study participant using their pseudonym.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consent_type: Type of consent being recorded
            granted: Whether consent is granted or denied
            metadata: Additional consent metadata

        Returns:
            StudyConsentRecord: Created consent record

        Raises:
            ConsentError: If consent recording fails
        """
        try:
            # Create consent record
            consent_record = self.consent_repository.create_consent(
                pseudonym_id=pseudonym_id,
                consent_type=consent_type,
                granted=granted,
                version=self.current_consent_version,
                metadata=metadata or {}
            )

            if not consent_record:
                raise ConsentError("Failed to record consent")

            logger.info(
                f"Consent recorded for pseudonym {pseudonym_id}: {consent_type.value} = {granted}"
            )

            return consent_record

        except Exception as e:
            logger.error(f"Failed to record consent for pseudonym {pseudonym_id}: {e}")
            raise ConsentError(f"Consent recording failed: {str(e)}")

    def withdraw_consent(
        self, 
        pseudonym_id: UUID, 
        consent_type: StudyConsentType, 
        reason: str | None = None
    ) -> bool:
        """
        Withdraw consent for a study participant.

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
            # Check if participant has given consent for this type
            current_consent = self.consent_repository.get_by_pseudonym_and_type(
                pseudonym_id, consent_type
            )
            
            if not current_consent or not current_consent.granted:
                logger.warning(
                    f"No active consent to withdraw for pseudonym {pseudonym_id}, "
                    f"type {consent_type.value}"
                )
                return True  # Already withdrawn or never given

            # Record withdrawal
            success = self.consent_repository.withdraw_consent(
                pseudonym_id, consent_type, reason
            )
            
            if not success:
                raise ConsentWithdrawalError("Failed to record consent withdrawal")

            logger.info(f"Consent withdrawn for pseudonym {pseudonym_id}: {consent_type.value}")

            return True

        except ConsentWithdrawalError:
            raise
        except Exception as e:
            logger.error(f"Failed to withdraw consent for pseudonym {pseudonym_id}: {e}")
            raise ConsentWithdrawalError(f"Consent withdrawal failed: {str(e)}")

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
            return self.consent_repository.check_consent(pseudonym_id, consent_type)
        except Exception as e:
            logger.error(
                f"Failed to check consent for pseudonym {pseudonym_id}, "
                f"type {consent_type.value}: {e}"
            )
            return False

    def require_consent(self, pseudonym_id: UUID, consent_type: StudyConsentType) -> None:
        """
        Require consent for a specific type, raise exception if not given.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consent_type: Type of consent required

        Raises:
            ConsentRequiredError: If consent is not given
        """
        if not self.check_consent(pseudonym_id, consent_type):
            raise ConsentRequiredError(
                f"Consent required for {consent_type.value}",
                required=[consent_type.value],
            )

    def get_consent_status(self, pseudonym_id: UUID) -> Dict[str, bool]:
        """
        Get current consent status for all consent types for a participant.

        Args:
            pseudonym_id: Pseudonym identifier for the participant

        Returns:
            Dict mapping consent types to their current status
        """
        try:
            consent_status = {}

            for consent_type in StudyConsentType:
                consent_status[consent_type.value] = self.check_consent(pseudonym_id, consent_type)

            return consent_status

        except Exception as e:
            logger.error(f"Failed to get consent status for pseudonym {pseudonym_id}: {e}")
            return {}

    def validate_consent_completeness(self, consents: List[StudyConsentType]) -> Dict[str, Any]:
        """
        Validate that all required consents are present.

        Args:
            consents: List of consent types to validate

        Returns:
            Dict containing validation results
        """
        required_consents = [
            StudyConsentType.DATA_PROTECTION,
            StudyConsentType.AI_INTERACTION,
            StudyConsentType.STUDY_PARTICIPATION
        ]

        missing_consents = []
        for required_consent in required_consents:
            if required_consent not in consents:
                missing_consents.append(required_consent.value)

        return {
            "is_complete": len(missing_consents) == 0,
            "missing_consents": missing_consents,
            "required_consents": [c.value for c in required_consents],
            "provided_consents": [c.value for c in consents]
        }

    def process_consent_collection(
        self, 
        pseudonym_id: UUID, 
        consents: Dict[str, bool]
    ) -> Dict[str, Any]:
        """
        Process multi-step consent collection for study participation with error handling.

        Args:
            pseudonym_id: Pseudonym identifier for the participant
            consents: Dict mapping consent type strings to boolean values

        Returns:
            Dict containing processing results

        Raises:
            ConsentError: If consent processing fails
        """
        try:
            consent_records = []
            failed_consents = []
            normalization_log = []

            for consent_type_str, granted in consents.items():
                try:
                    # Normalize consent key to canonical enum
                    consent_type = self._normalize_consent_key(consent_type_str)
                    normalization_log.append(f"{consent_type_str} -> {consent_type.value}")
                    
                    # Record consent with individual error handling
                    record = self._record_consent_with_retry(pseudonym_id, consent_type, granted)
                    consent_records.append(record)
                    
                except InvalidConsentTypeError as e:
                    logger.error(f"Invalid consent type: {consent_type_str} - {e}")
                    failed_consents.append(consent_type_str)
                except Exception as e:
                    logger.error(f"Failed to record consent {consent_type_str}: {e}")
                    failed_consents.append(consent_type_str)

            # Log normalization for debugging
            logger.debug(f"Consent key normalization: {normalization_log}")

            # Check if all required consents are granted using normalized types
            granted_consent_types = []
            for consent_type_str, granted in consents.items():
                if granted:
                    try:
                        normalized_type = self._normalize_consent_key(consent_type_str)
                        granted_consent_types.append(normalized_type)
                    except InvalidConsentTypeError:
                        continue  # Skip invalid types
                
            validation_result = self.validate_consent_completeness(granted_consent_types)

            result = {
                "success": len(failed_consents) == 0,
                "consent_records": consent_records,
                "failed_consents": failed_consents,
                "validation": validation_result,
                "can_proceed": validation_result["is_complete"] and len(failed_consents) == 0,
                "normalization_log": normalization_log
            }
            
            logger.info(f"Consent collection processed for pseudonym {pseudonym_id}: {len(consent_records)} successful, {len(failed_consents)} failed")
            return result

        except Exception as e:
            logger.error(f"Failed to process consent collection for pseudonym {pseudonym_id}: {e}")
            raise ConsentError(f"Consent collection processing failed: {str(e)}")
    
    def _record_consent_with_retry(
        self, 
        pseudonym_id: UUID, 
        consent_type: StudyConsentType, 
        granted: bool,
        max_retries: int = 3
    ) -> StudyConsentRecord:
        """Record consent with retry logic for database failures."""
        
        for attempt in range(max_retries):
            try:
                return self.record_consent(pseudonym_id, consent_type, granted)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to record consent after {max_retries} attempts: {e}")
                    raise ConsentError(f"Consent recording failed after {max_retries} attempts")
                else:
                    logger.warning(f"Consent recording attempt {attempt + 1} failed, retrying: {e}")
                    continue

    def check_consent_status(self, pseudonym_id: UUID) -> Dict[str, Any]:
        """
        Check comprehensive consent status for a participant.

        Args:
            pseudonym_id: Pseudonym identifier for the participant

        Returns:
            Dict containing consent status information
        """
        try:
            consent_status = self.get_consent_status(pseudonym_id)
            
            # Check if all required consents are granted
            required_consents = [
                StudyConsentType.DATA_PROTECTION,
                StudyConsentType.AI_INTERACTION,
                StudyConsentType.STUDY_PARTICIPATION
            ]
            
            all_granted = all(
                consent_status.get(ct.value, False) for ct in required_consents
            )
            
            granted_count = sum(1 for granted in consent_status.values() if granted)
            total_count = len(StudyConsentType)

            return {
                "pseudonym_id": pseudonym_id,
                "consent_status": consent_status,
                "all_required_granted": all_granted,
                "granted_count": granted_count,
                "total_count": total_count,
                "completion_rate": granted_count / total_count if total_count > 0 else 0,
                "can_proceed_to_study": all_granted
            }

        except Exception as e:
            logger.error(f"Failed to check consent status for pseudonym {pseudonym_id}: {e}")
            return {
                "pseudonym_id": pseudonym_id,
                "consent_status": {},
                "all_required_granted": False,
                "granted_count": 0,
                "total_count": len(StudyConsentType),
                "completion_rate": 0.0,
                "can_proceed_to_study": False
            }

    def get_participant_consents(self, pseudonym_id: UUID) -> List[StudyConsentRecord]:
        """
        Get all consent records for a participant.

        Args:
            pseudonym_id: Pseudonym identifier for the participant

        Returns:
            List of consent records for the participant
        """
        try:
            return self.consent_repository.get_by_pseudonym(pseudonym_id)
        except Exception as e:
            logger.error(f"Failed to get consent records for pseudonym {pseudonym_id}: {e}")
            return []

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
            consent_records = []

            for consent_type, granted in consents.items():
                # Ensure we have a proper enum instance
                if isinstance(consent_type, str):
                    consent_type = self._normalize_consent_key(consent_type)
                
                record = self.record_consent(pseudonym_id, consent_type, granted, metadata)
                consent_records.append(record)

            logger.info(
                f"Bulk consent recorded for pseudonym {pseudonym_id}: {len(consent_records)} records"
            )

            return consent_records

        except Exception as e:
            logger.error(f"Failed to record bulk consent for pseudonym {pseudonym_id}: {e}")
            raise ConsentError(f"Bulk consent recording failed: {str(e)}")