"""
Unit tests for study participation consent service layer.
Tests service layer operations and database session management for pseudonym-based consent.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.data.models import StudyConsentRecord, StudyConsentType
from src.services.consent_service import ConsentService


class TestStudyConsentService:
    """Test study participation consent service layer."""

    @pytest.fixture
    def consent_service(self):
        """Consent service instance."""
        return ConsentService()

    @pytest.fixture
    def pseudonym_id(self):
        """Test pseudonym ID."""
        return uuid4()

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_record_consent(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer consent recording."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_record = StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,
            consent_type=StudyConsentType.DATA_PROTECTION.value,
            granted=True,
            version="1.0",
            granted_at=datetime.utcnow(),
        )
        mock_repo.create_consent.return_value = mock_record

        # Act
        result = consent_service.record_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION, True)

        # Assert
        assert isinstance(result, StudyConsentRecord)
        assert result.consent_type == StudyConsentType.DATA_PROTECTION.value
        assert result.granted is True
        assert result.pseudonym_id == pseudonym_id

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_check_consent(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer consent checking."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.check_consent.return_value = True

        # Act
        result = consent_service.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is True

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_withdraw_consent(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer consent withdrawal."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        mock_existing_consent = StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,
            consent_type=StudyConsentType.DATA_PROTECTION.value,
            granted=True,
            version="1.0",
            granted_at=datetime.utcnow(),
        )
        mock_repo.get_by_pseudonym_and_type.return_value = mock_existing_consent
        mock_repo.withdraw_consent.return_value = True

        # Act
        result = consent_service.withdraw_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION, "test reason")

        # Assert
        assert result is True

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_get_consent_status(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer consent status retrieval."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.check_consent.side_effect = (
            lambda pid, ct: ct == StudyConsentType.DATA_PROTECTION
        )

        # Act
        result = consent_service.get_consent_status(pseudonym_id)

        # Assert
        assert isinstance(result, dict)
        assert result[StudyConsentType.DATA_PROTECTION.value] is True
        assert result[StudyConsentType.AI_INTERACTION.value] is False
        assert result[StudyConsentType.STUDY_PARTICIPATION.value] is False

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_process_consent_collection(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer consent collection processing."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

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

        mock_repo.create_consent.side_effect = mock_records

        # Act
        result = consent_service.process_consent_collection(pseudonym_id, consents)

        # Assert
        assert result["success"] is True
        assert result["can_proceed"] is True
        assert len(result["consent_records"]) == 3

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_check_consent_status(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer comprehensive consent status checking."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.check_consent.return_value = True  # All consents granted

        # Act
        result = consent_service.check_consent_status(pseudonym_id)

        # Assert
        assert result["pseudonym_id"] == pseudonym_id
        assert result["all_required_granted"] is True
        assert result["can_proceed_to_study"] is True
        assert result["completion_rate"] == 1.0

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_get_participant_consents(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer participant consent retrieval."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

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
        mock_repo.get_by_pseudonym.return_value = mock_records

        # Act
        result = consent_service.get_participant_consents(pseudonym_id)

        # Assert
        assert len(result) == 2
        assert result[0].consent_type == StudyConsentType.DATA_PROTECTION.value
        assert result[1].consent_type == StudyConsentType.AI_INTERACTION.value

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_record_bulk_consent(self, mock_repo_class, mock_get_session, consent_service, pseudonym_id):
        """Test service layer bulk consent recording."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

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

        mock_repo.create_consent.side_effect = mock_records

        # Act
        result = consent_service.record_bulk_consent(pseudonym_id, consents)

        # Assert
        assert len(result) == 3
        assert all(isinstance(record, StudyConsentRecord) for record in result)

    @patch("src.services.consent_service.get_session")
    def test_service_session_cleanup_on_exception(self, mock_get_session, consent_service, pseudonym_id):
        """Test that service properly cleans up session on exception."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__enter__.side_effect = Exception("Database connection failed")

        # Act - check_consent catches exceptions and returns False
        result = consent_service.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert - should return False on exception
        assert result is False

        # Verify cleanup
        assert consent_service.consent_logic is None
        assert not hasattr(consent_service, "_session") or consent_service._session is None

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.StudyConsentRepository")
    def test_validate_consent_completeness(self, mock_repo_class, mock_get_session, consent_service):
        """Test service layer consent completeness validation."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        consents = [StudyConsentType.DATA_PROTECTION, StudyConsentType.AI_INTERACTION]

        # Act
        result = consent_service.validate_consent_completeness(consents)

        # Assert
        assert "is_complete" in result
        assert "missing_consents" in result
        assert "required_consents" in result
        assert "provided_consents" in result

    def test_convenience_functions(self, pseudonym_id):
        """Test convenience functions for common operations."""
        # Import convenience functions
        from src.services.consent_service import (
            check_consent,
            get_consent_status,
            record_consent,
            withdraw_consent,
        )

        # Test that functions exist and are callable
        assert callable(record_consent)
        assert callable(withdraw_consent)
        assert callable(check_consent)
        assert callable(get_consent_status)

    def test_get_study_consent_service(self):
        """Test getting the global service instance."""
        from src.services.consent_service import get_study_consent_service

        service1 = get_study_consent_service()
        service2 = get_study_consent_service()

        # Should return the same instance
        assert service1 is service2
        assert isinstance(service1, ConsentService)


if __name__ == "__main__":
    pytest.main([__file__])