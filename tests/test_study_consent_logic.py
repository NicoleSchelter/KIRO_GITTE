"""
Unit tests for study participation consent management system.
Tests consent logic, service layer, and repository functionality for pseudonym-based consent.
"""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.data.models import StudyConsentRecord, StudyConsentType
from src.data.repositories import StudyConsentRepository
from src.exceptions import ConsentError, ConsentRequiredError, ConsentWithdrawalError
from src.logic.consent_logic import ConsentLogic


class TestStudyConsentLogic:
    """Test study participation consent business logic."""

    @pytest.fixture
    def mock_consent_repository(self):
        """Mock study consent repository."""
        return Mock(spec=StudyConsentRepository)

    @pytest.fixture
    def consent_logic(self, mock_consent_repository):
        """Consent logic instance with mocked repository."""
        return ConsentLogic(mock_consent_repository)

    @pytest.fixture
    def pseudonym_id(self):
        """Test pseudonym ID."""
        return uuid4()

    def test_record_consent_success(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test successful consent recording."""
        # Arrange
        consent_type = StudyConsentType.DATA_PROTECTION
        granted = True
        metadata = {"source": "test"}

        mock_record = StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,
            consent_type=consent_type.value,
            granted=granted,
            version="1.0",
            granted_at=datetime.utcnow(),
        )
        mock_consent_repository.create_consent.return_value = mock_record

        # Act
        result = consent_logic.record_consent(pseudonym_id, consent_type, granted, metadata)

        # Assert
        assert isinstance(result, StudyConsentRecord)
        assert result.consent_type == consent_type.value
        assert result.granted == granted
        assert result.pseudonym_id == pseudonym_id
        mock_consent_repository.create_consent.assert_called_once_with(
            pseudonym_id=pseudonym_id,
            consent_type=consent_type,
            granted=granted,
            version="1.0",
            metadata=metadata
        )

    def test_record_consent_failure(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test consent recording failure."""
        # Arrange
        mock_consent_repository.create_consent.return_value = None

        # Act & Assert
        with pytest.raises(ConsentError, match="Failed to record consent"):
            consent_logic.record_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION, True)

    def test_withdraw_consent_success(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test successful consent withdrawal."""
        # Arrange
        consent_type = StudyConsentType.DATA_PROTECTION

        mock_existing_consent = StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,
            consent_type=consent_type.value,
            granted=True,
            version="1.0",
            granted_at=datetime.utcnow(),
        )
        mock_consent_repository.get_by_pseudonym_and_type.return_value = mock_existing_consent
        mock_consent_repository.withdraw_consent.return_value = True

        # Act
        result = consent_logic.withdraw_consent(pseudonym_id, consent_type, "test reason")

        # Assert
        assert result is True
        mock_consent_repository.withdraw_consent.assert_called_once_with(
            pseudonym_id, consent_type, "test reason"
        )

    def test_withdraw_consent_no_existing_consent(
        self, consent_logic, mock_consent_repository, pseudonym_id
    ):
        """Test withdrawing consent when none exists."""
        # Arrange
        mock_consent_repository.get_by_pseudonym_and_type.return_value = None

        # Act
        result = consent_logic.withdraw_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is True  # Should succeed even if no consent exists
        mock_consent_repository.withdraw_consent.assert_not_called()

    def test_check_consent_valid(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test checking valid consent."""
        # Arrange
        mock_consent_repository.check_consent.return_value = True

        # Act
        result = consent_logic.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is True
        mock_consent_repository.check_consent.assert_called_once_with(
            pseudonym_id, StudyConsentType.DATA_PROTECTION
        )

    def test_check_consent_invalid(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test checking invalid consent."""
        # Arrange
        mock_consent_repository.check_consent.return_value = False

        # Act
        result = consent_logic.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is False

    def test_require_consent_valid(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test requiring consent when valid."""
        # Arrange
        mock_consent_repository.check_consent.return_value = True

        # Act & Assert (should not raise)
        consent_logic.require_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

    def test_require_consent_invalid(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test requiring consent when invalid."""
        # Arrange
        mock_consent_repository.check_consent.return_value = False

        # Act & Assert
        with pytest.raises(ConsentRequiredError, match="Consent required for data_protection"):
            consent_logic.require_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

    def test_get_consent_status(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test getting consent status for all types."""
        # Arrange
        mock_consent_repository.check_consent.side_effect = (
            lambda pid, ct: ct == StudyConsentType.DATA_PROTECTION
        )

        # Act
        result = consent_logic.get_consent_status(pseudonym_id)

        # Assert
        assert isinstance(result, dict)
        assert result[StudyConsentType.DATA_PROTECTION.value] is True
        assert result[StudyConsentType.AI_INTERACTION.value] is False
        assert result[StudyConsentType.STUDY_PARTICIPATION.value] is False
        assert len(result) == len(StudyConsentType)

    def test_validate_consent_completeness_complete(self, consent_logic):
        """Test consent completeness validation when all required consents are present."""
        # Arrange
        consents = [
            StudyConsentType.DATA_PROTECTION,
            StudyConsentType.AI_INTERACTION,
            StudyConsentType.STUDY_PARTICIPATION
        ]

        # Act
        result = consent_logic.validate_consent_completeness(consents)

        # Assert
        assert result["is_complete"] is True
        assert len(result["missing_consents"]) == 0
        assert len(result["required_consents"]) == 3
        assert len(result["provided_consents"]) == 3

    def test_validate_consent_completeness_incomplete(self, consent_logic):
        """Test consent completeness validation when some consents are missing."""
        # Arrange
        consents = [StudyConsentType.DATA_PROTECTION]  # Missing AI_INTERACTION and STUDY_PARTICIPATION

        # Act
        result = consent_logic.validate_consent_completeness(consents)

        # Assert
        assert result["is_complete"] is False
        assert "ai_interaction" in result["missing_consents"]
        assert "study_participation" in result["missing_consents"]
        assert len(result["missing_consents"]) == 2

    def test_process_consent_collection_success(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test successful consent collection processing."""
        # Arrange
        consents = {
            "data_protection": True,
            "ai_interaction": True,
            "study_participation": True
        }

        mock_records = []
        for consent_type_str, granted in consents.items():
            mock_record = StudyConsentRecord(
                consent_id=uuid4(),
                pseudonym_id=pseudonym_id,
                consent_type=consent_type_str,
                granted=granted,
                version="1.0",
                granted_at=datetime.utcnow(),
            )
            mock_records.append(mock_record)

        mock_consent_repository.create_consent.side_effect = mock_records

        # Act
        result = consent_logic.process_consent_collection(pseudonym_id, consents)

        # Assert
        assert result["success"] is True
        assert result["can_proceed"] is True
        assert len(result["consent_records"]) == 3
        assert len(result["failed_consents"]) == 0
        assert result["validation"]["is_complete"] is True

    def test_process_consent_collection_partial_failure(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test consent collection processing with some failures."""
        # Arrange
        consents = {
            "data_protection": True,
            "invalid_consent_type": True,  # This should fail
            "study_participation": True
        }

        # Mock successful creation for valid consent types
        def mock_create_consent(pseudonym_id, consent_type, granted, version, metadata):
            if consent_type in [StudyConsentType.DATA_PROTECTION, StudyConsentType.STUDY_PARTICIPATION]:
                return StudyConsentRecord(
                    consent_id=uuid4(),
                    pseudonym_id=pseudonym_id,
                    consent_type=consent_type.value,
                    granted=granted,
                    version=version,
                    granted_at=datetime.utcnow(),
                )
            return None

        mock_consent_repository.create_consent.side_effect = mock_create_consent

        # Act
        result = consent_logic.process_consent_collection(pseudonym_id, consents)

        # Assert
        assert result["success"] is False  # Due to invalid consent type
        assert "invalid_consent_type" in result["failed_consents"]
        assert len(result["consent_records"]) == 2  # Only valid ones recorded

    def test_check_consent_status_all_granted(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test checking consent status when all required consents are granted."""
        # Arrange
        mock_consent_repository.check_consent.return_value = True

        # Act
        result = consent_logic.check_consent_status(pseudonym_id)

        # Assert
        assert result["pseudonym_id"] == pseudonym_id
        assert result["all_required_granted"] is True
        assert result["can_proceed_to_study"] is True
        assert result["granted_count"] == len(StudyConsentType)
        assert result["completion_rate"] == 1.0

    def test_check_consent_status_partial_granted(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test checking consent status when only some consents are granted."""
        # Arrange
        mock_consent_repository.check_consent.side_effect = (
            lambda pid, ct: ct == StudyConsentType.DATA_PROTECTION
        )

        # Act
        result = consent_logic.check_consent_status(pseudonym_id)

        # Assert
        assert result["pseudonym_id"] == pseudonym_id
        assert result["all_required_granted"] is False
        assert result["can_proceed_to_study"] is False
        assert result["granted_count"] == 1
        assert result["completion_rate"] == 1.0 / len(StudyConsentType)

    def test_get_participant_consents(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test getting all consent records for a participant."""
        # Arrange
        mock_records = [
            StudyConsentRecord(
                consent_id=uuid4(),
                pseudonym_id=pseudonym_id,
                consent_type=StudyConsentType.DATA_PROTECTION.value,
                granted=True,
                version="1.0",
                granted_at=datetime.utcnow(),
            ),
            StudyConsentRecord(
                consent_id=uuid4(),
                pseudonym_id=pseudonym_id,
                consent_type=StudyConsentType.AI_INTERACTION.value,
                granted=False,
                version="1.0",
                granted_at=datetime.utcnow(),
            )
        ]
        mock_consent_repository.get_by_pseudonym.return_value = mock_records

        # Act
        result = consent_logic.get_participant_consents(pseudonym_id)

        # Assert
        assert len(result) == 2
        assert result[0].consent_type == StudyConsentType.DATA_PROTECTION.value
        assert result[1].consent_type == StudyConsentType.AI_INTERACTION.value
        mock_consent_repository.get_by_pseudonym.assert_called_once_with(pseudonym_id)

    def test_record_bulk_consent(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test recording bulk consent."""
        # Arrange
        consents = {
            StudyConsentType.DATA_PROTECTION: True,
            StudyConsentType.AI_INTERACTION: False,
            StudyConsentType.STUDY_PARTICIPATION: True
        }

        mock_records = []
        for consent_type, granted in consents.items():
            mock_record = StudyConsentRecord(
                consent_id=uuid4(),
                pseudonym_id=pseudonym_id,
                consent_type=consent_type.value,
                granted=granted,
                version="1.0",
                granted_at=datetime.utcnow(),
            )
            mock_records.append(mock_record)

        mock_consent_repository.create_consent.side_effect = mock_records

        # Act
        result = consent_logic.record_bulk_consent(pseudonym_id, consents)

        # Assert
        assert len(result) == 3
        assert mock_consent_repository.create_consent.call_count == 3

    def test_record_consent_exception_handling(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test consent recording with repository exception."""
        # Arrange
        mock_consent_repository.create_consent.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ConsentError, match="Consent recording failed"):
            consent_logic.record_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION, True)

    def test_withdraw_consent_exception_handling(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test consent withdrawal with repository exception."""
        # Arrange
        mock_existing_consent = StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,
            consent_type=StudyConsentType.DATA_PROTECTION.value,
            granted=True,
            version="1.0",
            granted_at=datetime.utcnow(),
        )
        mock_consent_repository.get_by_pseudonym_and_type.return_value = mock_existing_consent
        mock_consent_repository.withdraw_consent.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(ConsentWithdrawalError, match="Consent withdrawal failed"):
            consent_logic.withdraw_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

    def test_check_consent_exception_handling(self, consent_logic, mock_consent_repository, pseudonym_id):
        """Test consent checking with repository exception."""
        # Arrange
        mock_consent_repository.check_consent.side_effect = Exception("Database error")

        # Act
        result = consent_logic.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is False  # Should return False on exception


if __name__ == "__main__":
    pytest.main([__file__])