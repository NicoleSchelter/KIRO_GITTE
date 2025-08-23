"""
Unit tests for study participation consent repository.
Tests database operations for pseudonym-based consent management.
"""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.data.models import StudyConsentRecord, StudyConsentType
from src.data.repositories import StudyConsentRepository


class TestStudyConsentRepository:
    """Test study participation consent repository."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def consent_repository(self, mock_session):
        """Consent repository instance with mocked session."""
        return StudyConsentRepository(mock_session)

    @pytest.fixture
    def pseudonym_id(self):
        """Test pseudonym ID."""
        return uuid4()

    @pytest.fixture
    def sample_consent_record(self, pseudonym_id):
        """Sample consent record for testing."""
        return StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,
            consent_type=StudyConsentType.DATA_PROTECTION.value,
            granted=True,
            version="1.0",
            granted_at=datetime.utcnow(),
        )

    def test_create_consent_success(self, consent_repository, mock_session, pseudonym_id):
        """Test successful consent record creation."""
        # Arrange
        consent_type = StudyConsentType.DATA_PROTECTION
        granted = True
        version = "1.0"

        # Act
        result = consent_repository.create_consent(pseudonym_id, consent_type, granted, version)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        # The result should be a StudyConsentRecord (mocked by the actual implementation)

    def test_create_consent_exception(self, consent_repository, mock_session, pseudonym_id):
        """Test consent creation with database exception."""
        # Arrange
        mock_session.add.side_effect = Exception("Database error")

        # Act
        result = consent_repository.create_consent(
            pseudonym_id, StudyConsentType.DATA_PROTECTION, True, "1.0"
        )

        # Assert
        assert result is None

    def test_get_by_pseudonym_and_type_found(self, consent_repository, mock_session, pseudonym_id, sample_consent_record):
        """Test getting consent record by pseudonym and type when found."""
        # Arrange
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sample_consent_record

        # Act
        result = consent_repository.get_by_pseudonym_and_type(
            pseudonym_id, StudyConsentType.DATA_PROTECTION
        )

        # Assert
        assert result == sample_consent_record
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.first.assert_called_once()

    def test_get_by_pseudonym_and_type_not_found(self, consent_repository, mock_session, pseudonym_id):
        """Test getting consent record by pseudonym and type when not found."""
        # Arrange
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = consent_repository.get_by_pseudonym_and_type(
            pseudonym_id, StudyConsentType.DATA_PROTECTION
        )

        # Assert
        assert result is None

    def test_get_by_pseudonym_and_type_exception(self, consent_repository, mock_session, pseudonym_id):
        """Test getting consent record with database exception."""
        # Arrange
        mock_session.query.side_effect = Exception("Database error")

        # Act
        result = consent_repository.get_by_pseudonym_and_type(
            pseudonym_id, StudyConsentType.DATA_PROTECTION
        )

        # Assert
        assert result is None

    def test_get_by_pseudonym_success(self, consent_repository, mock_session, pseudonym_id):
        """Test getting all consent records for a pseudonym."""
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

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = mock_records

        # Act
        result = consent_repository.get_by_pseudonym(pseudonym_id)

        # Assert
        assert len(result) == 2
        assert result == mock_records
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.order_by.assert_called_once()
        mock_query.all.assert_called_once()

    def test_get_by_pseudonym_exception(self, consent_repository, mock_session, pseudonym_id):
        """Test getting consent records with database exception."""
        # Arrange
        mock_session.query.side_effect = Exception("Database error")

        # Act
        result = consent_repository.get_by_pseudonym(pseudonym_id)

        # Assert
        assert result == []

    def test_withdraw_consent_success(self, consent_repository, mock_session, pseudonym_id):
        """Test successful consent withdrawal."""
        # Arrange
        consent_type = StudyConsentType.DATA_PROTECTION
        reason = "User requested withdrawal"

        # Act
        result = consent_repository.withdraw_consent(pseudonym_id, consent_type, reason)

        # Assert
        assert result is True
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_withdraw_consent_exception(self, consent_repository, mock_session, pseudonym_id):
        """Test consent withdrawal with database exception."""
        # Arrange
        mock_session.add.side_effect = Exception("Database error")

        # Act
        result = consent_repository.withdraw_consent(
            pseudonym_id, StudyConsentType.DATA_PROTECTION, "test reason"
        )

        # Assert
        assert result is False

    def test_check_consent_valid(self, consent_repository, mock_session, pseudonym_id, sample_consent_record):
        """Test checking consent when valid consent exists."""
        # Arrange
        sample_consent_record.granted = True
        sample_consent_record.revoked_at = None

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sample_consent_record

        # Act
        result = consent_repository.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is True

    def test_check_consent_not_granted(self, consent_repository, mock_session, pseudonym_id, sample_consent_record):
        """Test checking consent when consent is not granted."""
        # Arrange
        sample_consent_record.granted = False
        sample_consent_record.revoked_at = None

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sample_consent_record

        # Act
        result = consent_repository.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is False

    def test_check_consent_revoked(self, consent_repository, mock_session, pseudonym_id, sample_consent_record):
        """Test checking consent when consent is revoked."""
        # Arrange
        sample_consent_record.granted = True
        sample_consent_record.revoked_at = datetime.utcnow()

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = sample_consent_record

        # Act
        result = consent_repository.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is False

    def test_check_consent_no_record(self, consent_repository, mock_session, pseudonym_id):
        """Test checking consent when no record exists."""
        # Arrange
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = consent_repository.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is False

    def test_check_consent_exception(self, consent_repository, mock_session, pseudonym_id):
        """Test checking consent with database exception."""
        # Arrange
        mock_session.query.side_effect = Exception("Database error")

        # Act
        result = consent_repository.check_consent(pseudonym_id, StudyConsentType.DATA_PROTECTION)

        # Assert
        assert result is False

    def test_get_by_id_found(self, consent_repository, mock_session, sample_consent_record):
        """Test getting consent record by ID when found."""
        # Arrange
        consent_id = sample_consent_record.consent_id

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = sample_consent_record

        # Act
        result = consent_repository.get_by_id(consent_id)

        # Assert
        assert result == sample_consent_record
        mock_session.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_query.first.assert_called_once()

    def test_get_by_id_not_found(self, consent_repository, mock_session):
        """Test getting consent record by ID when not found."""
        # Arrange
        consent_id = uuid4()

        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        # Act
        result = consent_repository.get_by_id(consent_id)

        # Assert
        assert result is None

    def test_get_by_id_exception(self, consent_repository, mock_session):
        """Test getting consent record by ID with database exception."""
        # Arrange
        consent_id = uuid4()
        mock_session.query.side_effect = Exception("Database error")

        # Act
        result = consent_repository.get_by_id(consent_id)

        # Assert
        assert result is None

    def test_repository_inheritance(self, consent_repository):
        """Test that StudyConsentRepository properly inherits from BaseRepository."""
        from src.data.repositories import BaseRepository

        assert isinstance(consent_repository, BaseRepository)
        assert hasattr(consent_repository, 'session')
        assert hasattr(consent_repository, 'model_class')

    def test_consent_type_enum_handling(self, consent_repository, mock_session, pseudonym_id):
        """Test that repository properly handles StudyConsentType enum values."""
        # Test with enum value
        consent_repository.create_consent(
            pseudonym_id, StudyConsentType.DATA_PROTECTION, True, "1.0"
        )

        # Verify that the enum value is properly converted
        mock_session.add.assert_called_once()
        
        # Get the added object
        added_consent = mock_session.add.call_args[0][0]
        assert added_consent.consent_type == StudyConsentType.DATA_PROTECTION.value


if __name__ == "__main__":
    pytest.main([__file__])