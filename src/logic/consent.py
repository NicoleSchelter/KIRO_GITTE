"""
Consent management logic for GITTE system.
Handles consent recording, withdrawal, checking, and GDPR compliance.
"""

import logging
from typing import Any
from uuid import UUID

from config.config import config
from src.data.models import ConsentType
from src.data.repositories import ConsentRepository
from src.data.schemas import ConsentRecordCreate, ConsentRecordResponse

logger = logging.getLogger(__name__)


class ConsentError(Exception):
    """Base exception for consent-related errors."""

    pass


class ConsentRequiredError(ConsentError):
    """Raised when consent is required but not provided."""

    pass


class ConsentWithdrawalError(ConsentError):
    """Raised when consent withdrawal fails."""

    pass


class ConsentLogic:
    """Consent management business logic."""

    def __init__(self, consent_repository: ConsentRepository):
        self.consent_repository = consent_repository
        self.current_consent_version = "1.0"  # Should be configurable

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
            # Create consent record data
            consent_data = ConsentRecordCreate(
                consent_type=consent_type,
                consent_given=consent_given,
                consent_version=self.current_consent_version,
                consent_metadata=metadata or {},
            )

            # Record consent in database
            consent_record = self.consent_repository.create(user_id, consent_data)
            if not consent_record:
                raise ConsentError("Failed to record consent")

            logger.info(
                f"Consent recorded for user {user_id}: {consent_type.value} = {consent_given}"
            )

            return ConsentRecordResponse.model_validate(consent_record)

        except Exception as e:
            logger.error(f"Failed to record consent for user {user_id}: {e}")
            raise ConsentError(f"Consent recording failed: {str(e)}")

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
            # Check if user has given consent for this type
            current_consent = self.consent_repository.get_by_user_and_type(user_id, consent_type)
            if not current_consent or not current_consent.consent_given:
                logger.warning(
                    f"No active consent to withdraw for user {user_id}, type {consent_type.value}"
                )
                return True  # Already withdrawn or never given

            # Record withdrawal
            success = self.consent_repository.withdraw_consent(user_id, consent_type, reason)
            if not success:
                raise ConsentWithdrawalError("Failed to record consent withdrawal")

            logger.info(f"Consent withdrawn for user {user_id}: {consent_type.value}")

            return True

        except ConsentWithdrawalError:
            raise
        except Exception as e:
            logger.error(f"Failed to withdraw consent for user {user_id}: {e}")
            raise ConsentWithdrawalError(f"Consent withdrawal failed: {str(e)}")

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
            return self.consent_repository.check_consent(user_id, consent_type)
        except Exception as e:
            logger.error(
                f"Failed to check consent for user {user_id}, type {consent_type.value}: {e}"
            )
            return False

    def require_consent(self, user_id: UUID, consent_type: ConsentType) -> None:
        """
        Require consent for a specific type, raise exception if not given.

        Args:
            user_id: User identifier
            consent_type: Type of consent required

        Raises:
            ConsentRequiredError: If consent is not given
        """
        if not self.check_consent(user_id, consent_type):
            raise ConsentRequiredError(f"Consent required for {consent_type.value}")

    def get_user_consents(self, user_id: UUID) -> list[ConsentRecordResponse]:
        """
        Get all consent records for a user.

        Args:
            user_id: User identifier

        Returns:
            List of consent records for the user
        """
        try:
            consent_records = self.consent_repository.get_by_user(user_id)
            return [ConsentRecordResponse.model_validate(record) for record in consent_records]
        except Exception as e:
            logger.error(f"Failed to get consent records for user {user_id}: {e}")
            return []

    def get_consent_status(self, user_id: UUID) -> dict[str, bool]:
        """
        Get current consent status for all consent types for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict mapping consent types to their current status
        """
        try:
            consent_status = {}

            for consent_type in ConsentType:
                consent_status[consent_type.value] = self.check_consent(user_id, consent_type)

            return consent_status

        except Exception as e:
            logger.error(f"Failed to get consent status for user {user_id}: {e}")
            return {}

    def check_multiple_consents(
        self, user_id: UUID, consent_types: list[ConsentType]
    ) -> dict[str, bool]:
        """
        Check multiple consent types at once.

        Args:
            user_id: User identifier
            consent_types: List of consent types to check

        Returns:
            Dict mapping consent types to their status
        """
        try:
            results = {}
            for consent_type in consent_types:
                results[consent_type.value] = self.check_consent(user_id, consent_type)
            return results
        except Exception as e:
            logger.error(f"Failed to check multiple consents for user {user_id}: {e}")
            return {ct.value: False for ct in consent_types}

    def require_multiple_consents(self, user_id: UUID, consent_types: list[ConsentType]) -> None:
        """
        Require multiple consent types, raise exception if any are missing.

        Args:
            user_id: User identifier
            consent_types: List of consent types required

        Raises:
            ConsentRequiredError: If any required consent is missing
        """
        missing_consents = []

        for consent_type in consent_types:
            if not self.check_consent(user_id, consent_type):
                missing_consents.append(consent_type.value)

        if missing_consents:
            raise ConsentRequiredError(f"Missing required consents: {', '.join(missing_consents)}")

    def is_consent_gate_enabled(self) -> bool:
        """
        Check if consent gate is enabled via feature flag.

        Returns:
            bool: True if consent gate is enabled
        """
        return config.get_feature_flag("enable_consent_gate")

    def get_required_consents_for_operation(self, operation: str) -> list[ConsentType]:
        """
        Get required consent types for a specific operation.

        Args:
            operation: Operation name (e.g., 'chat', 'image_generation', 'data_export')

        Returns:
            List of required consent types
        """
        # Define operation to consent mapping
        operation_consents = {
            "chat": [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            "image_generation": [
                ConsentType.DATA_PROCESSING,
                ConsentType.AI_INTERACTION,
                ConsentType.IMAGE_GENERATION,
            ],
            "data_export": [ConsentType.DATA_PROCESSING, ConsentType.ANALYTICS],
            "federated_learning": [ConsentType.DATA_PROCESSING, ConsentType.FEDERATED_LEARNING],
            "survey": [ConsentType.DATA_PROCESSING],
            "pald_update": [ConsentType.DATA_PROCESSING],
            "admin_export": [ConsentType.DATA_PROCESSING, ConsentType.ANALYTICS],
        }

        return operation_consents.get(operation, [ConsentType.DATA_PROCESSING])

    def check_operation_consent(self, user_id: UUID, operation: str) -> bool:
        """
        Check if user has all required consents for a specific operation.

        Args:
            user_id: User identifier
            operation: Operation name

        Returns:
            bool: True if user has all required consents
        """
        if not self.is_consent_gate_enabled():
            return True  # Consent gate disabled, allow all operations

        required_consents = self.get_required_consents_for_operation(operation)

        return all(self.check_consent(user_id, consent_type) for consent_type in required_consents)

    def require_operation_consent(self, user_id: UUID, operation: str) -> None:
        """
        Require all consents for a specific operation.

        Args:
            user_id: User identifier
            operation: Operation name

        Raises:
            ConsentRequiredError: If any required consent is missing
        """
        if not self.is_consent_gate_enabled():
            return  # Consent gate disabled, allow all operations

        required_consents = self.get_required_consents_for_operation(operation)
        self.require_multiple_consents(user_id, required_consents)

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
            consent_records = []

            for consent_type, consent_given in consents.items():
                record = self.record_consent(user_id, consent_type, consent_given, metadata)
                consent_records.append(record)

            logger.info(f"Bulk consent recorded for user {user_id}: {len(consent_records)} records")

            return consent_records

        except Exception as e:
            logger.error(f"Failed to record bulk consent for user {user_id}: {e}")
            raise ConsentError(f"Bulk consent recording failed: {str(e)}")

    def get_consent_summary(self, user_id: UUID) -> dict[str, Any]:
        """
        Get a comprehensive consent summary for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict containing consent summary information
        """
        try:
            consent_status = self.get_consent_status(user_id)
            consent_records = self.get_user_consents(user_id)

            # Calculate summary statistics
            total_consents = len(ConsentType)
            given_consents = sum(1 for status in consent_status.values() if status)

            # Find latest consent activity
            latest_activity = None
            if consent_records:
                latest_activity = max(record.timestamp for record in consent_records)

            return {
                "user_id": user_id,
                "consent_status": consent_status,
                "total_consent_types": total_consents,
                "consents_given": given_consents,
                "consent_completion_rate": (
                    given_consents / total_consents if total_consents > 0 else 0
                ),
                "latest_activity": latest_activity,
                "consent_gate_enabled": self.is_consent_gate_enabled(),
                "consent_version": self.current_consent_version,
            }

        except Exception as e:
            logger.error(f"Failed to get consent summary for user {user_id}: {e}")
            return {}
