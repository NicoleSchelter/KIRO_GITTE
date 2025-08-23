"""
Unit tests for data privacy logic.
Tests data deletion, pseudonymization validation, and data export functionality.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, MagicMock

from src.logic.data_privacy_logic import (
    DataPrivacyLogic,
    DataPrivacyError,
    DataDeletionError,
    DataExportError,
    PseudonymizationValidationError,
)
from src.data.schemas import (
    DataDeletionRequest,
    DataExportRequest,
    PseudonymizationValidationResult,
)


class TestDataPrivacyLogic:
    """Test cases for DataPrivacyLogic."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for testing."""
        return {
            'pseudonym_repository': Mock(),
            'pseudonym_mapping_repository': Mock(),
            'consent_repository': Mock(),
            'survey_repository': Mock(),
            'chat_repository': Mock(),
            'pald_repository': Mock(),
            'image_repository': Mock(),
            'feedback_repository': Mock(),
            'interaction_repository': Mock(),
        }

    @pytest.fixture
    def data_privacy_logic(self, mock_repositories):
        """Create DataPrivacyLogic instance with mocked repositories."""
        return DataPrivacyLogic(**mock_repositories)

    @pytest.fixture
    def sample_pseudonym(self):
        """Create a sample pseudonym for testing."""
        return Mock(
            pseudonym_id=uuid4(),
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="hash123",
            created_at=datetime.utcnow(),
            is_active=True
        )

    def test_delete_participant_data_success(self, data_privacy_logic, mock_repositories, sample_pseudonym):
        """Test successful participant data deletion."""
        # Arrange
        pseudonym_id = sample_pseudonym.pseudonym_id
        request = DataDeletionRequest(
            pseudonym_id=pseudonym_id,
            reason="User request",
            requested_by="admin"
        )
        
        # Mock repository responses
        mock_repositories['pseudonym_repository'].get_by_id.return_value = sample_pseudonym
        mock_repositories['interaction_repository'].delete_by_pseudonym.return_value = 5
        mock_repositories['feedback_repository'].delete_by_pseudonym.return_value = 3
        mock_repositories['image_repository'].delete_by_pseudonym.return_value = 2
        mock_repositories['pald_repository'].delete_by_pseudonym.return_value = 4
        mock_repositories['chat_repository'].delete_by_pseudonym.return_value = 10
        mock_repositories['survey_repository'].delete_by_pseudonym.return_value = 1
        mock_repositories['consent_repository'].delete_by_pseudonym.return_value = 3
        mock_repositories['pseudonym_mapping_repository'].delete_by_pseudonym.return_value = True
        mock_repositories['pseudonym_repository'].delete.return_value = True

        # Act
        result = data_privacy_logic.delete_participant_data(request)

        # Assert
        assert result.success is True
        assert result.pseudonym_id == pseudonym_id
        assert result.total_records_deleted == 30  # Sum of all deleted records (5+3+2+4+10+1+3+1+1)
        assert "M03s2001AJ13" in result.message
        
        # Verify all repositories were called
        mock_repositories['pseudonym_repository'].get_by_id.assert_called_once_with(pseudonym_id)
        mock_repositories['interaction_repository'].delete_by_pseudonym.assert_called_once_with(pseudonym_id)
        mock_repositories['pseudonym_repository'].delete.assert_called_once_with(pseudonym_id)

    def test_delete_participant_data_pseudonym_not_found(self, data_privacy_logic, mock_repositories):
        """Test data deletion when pseudonym is not found."""
        # Arrange
        pseudonym_id = uuid4()
        request = DataDeletionRequest(
            pseudonym_id=pseudonym_id,
            reason="User request",
            requested_by="admin"
        )
        
        mock_repositories['pseudonym_repository'].get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(DataDeletionError, match="Pseudonym .* not found"):
            data_privacy_logic.delete_participant_data(request)

    def test_delete_participant_data_with_user_id(self, data_privacy_logic, mock_repositories, sample_pseudonym):
        """Test data deletion using user_id mapping."""
        # Arrange
        user_id = uuid4()
        pseudonym_id = sample_pseudonym.pseudonym_id
        request = DataDeletionRequest(
            user_id=user_id,
            reason="User request",
            requested_by="admin"
        )
        
        # Mock mapping resolution
        mapping_mock = Mock(pseudonym_id=pseudonym_id)
        mock_repositories['pseudonym_mapping_repository'].get_by_user_id.return_value = mapping_mock
        mock_repositories['pseudonym_repository'].get_by_id.return_value = sample_pseudonym
        
        # Mock deletion responses
        for repo_name in ['interaction_repository', 'feedback_repository', 'image_repository', 
                         'pald_repository', 'chat_repository', 'survey_repository', 'consent_repository']:
            mock_repositories[repo_name].delete_by_pseudonym.return_value = 1
        mock_repositories['pseudonym_mapping_repository'].delete_by_pseudonym.return_value = True
        mock_repositories['pseudonym_repository'].delete.return_value = True

        # Act
        result = data_privacy_logic.delete_participant_data(request)

        # Assert
        assert result.success is True
        assert result.pseudonym_id == pseudonym_id
        mock_repositories['pseudonym_mapping_repository'].get_by_user_id.assert_called_once_with(user_id)

    def test_export_participant_data_success(self, data_privacy_logic, mock_repositories, sample_pseudonym):
        """Test successful participant data export."""
        # Arrange
        pseudonym_id = sample_pseudonym.pseudonym_id
        request = DataExportRequest(
            pseudonym_id=pseudonym_id,
            format="json",
            include_metadata=True,
            requested_by="admin"
        )
        
        # Mock repository responses
        mock_repositories['pseudonym_repository'].get_by_id.return_value = sample_pseudonym
        mock_repositories['consent_repository'].get_by_pseudonym.return_value = [
            Mock(consent_id=uuid4(), pseudonym_id=pseudonym_id, consent_type="data_protection", 
                 granted=True, version="1.0", granted_at=datetime.utcnow(), revoked_at=None)
        ]
        mock_repositories['survey_repository'].get_by_pseudonym.return_value = []
        mock_repositories['chat_repository'].get_by_pseudonym.return_value = []
        mock_repositories['pald_repository'].get_by_pseudonym.return_value = []
        mock_repositories['image_repository'].get_by_pseudonym.return_value = []
        mock_repositories['feedback_repository'].get_by_pseudonym.return_value = []
        mock_repositories['interaction_repository'].get_by_pseudonym.return_value = []

        # Act
        result = data_privacy_logic.export_participant_data(request)

        # Assert
        assert result.success is True
        assert result.pseudonym_id == pseudonym_id
        assert "participant_data" in result.export_data
        assert "pseudonym" in result.export_data["participant_data"]
        assert result.export_data["participant_data"]["pseudonym"]["pseudonym_text"] == "M03s2001AJ13"
        assert result.record_counts["consents"] == 1

    def test_export_participant_data_pseudonym_not_found(self, data_privacy_logic, mock_repositories):
        """Test data export when pseudonym is not found."""
        # Arrange
        pseudonym_id = uuid4()
        request = DataExportRequest(
            pseudonym_id=pseudonym_id,
            format="json",
            requested_by="admin"
        )
        
        mock_repositories['pseudonym_repository'].get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(DataExportError, match="Pseudonym .* not found"):
            data_privacy_logic.export_participant_data(request)

    def test_validate_pseudonymization_valid_data(self, data_privacy_logic):
        """Test pseudonymization validation with valid data."""
        # Arrange
        valid_data = {
            "participant_data": {
                "pseudonym": {
                    "pseudonym_id": str(uuid4()),
                    "pseudonym_text": "M03s2001AJ13"
                },
                "consents": [
                    {
                        "consent_id": str(uuid4()),
                        "pseudonym_id": str(uuid4()),
                        "consent_type": "data_protection"
                    }
                ]
            }
        }

        # Act
        result = data_privacy_logic.validate_pseudonymization(valid_data)

        # Assert
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_validate_pseudonymization_user_id_exposure(self, data_privacy_logic):
        """Test pseudonymization validation with user_id exposure."""
        # Arrange
        invalid_data = {
            "participant_data": {
                "consents": [
                    {
                        "consent_id": str(uuid4()),
                        "user_id": str(uuid4()),  # This should be flagged
                        "consent_type": "data_protection"
                    }
                ]
            }
        }

        # Act
        result = data_privacy_logic.validate_pseudonymization(invalid_data)

        # Assert
        assert result.is_valid is False
        assert len(result.violations) > 0
        assert any("User ID exposure" in violation for violation in result.violations)

    def test_validate_pseudonymization_pii_exposure(self, data_privacy_logic):
        """Test pseudonymization validation with PII exposure."""
        # Arrange
        invalid_data = {
            "participant_data": {
                "user_info": {
                    "email": "user@example.com",  # This should be flagged
                    "name": "John Doe",  # This should be flagged
                    "pseudonym_id": str(uuid4())
                }
            }
        }

        # Act
        result = data_privacy_logic.validate_pseudonymization(invalid_data)

        # Assert
        assert result.is_valid is False
        assert len(result.violations) >= 2
        assert any("PII exposure (email)" in violation for violation in result.violations)
        assert any("PII exposure (name)" in violation for violation in result.violations)

    def test_cleanup_expired_data_success(self, data_privacy_logic, mock_repositories):
        """Test successful cleanup of expired data."""
        # Arrange
        retention_days = 30
        
        # Mock repository responses
        mock_repositories['interaction_repository'].delete_older_than.return_value = 10
        mock_repositories['feedback_repository'].delete_older_than.return_value = 5
        mock_repositories['image_repository'].delete_older_than.return_value = 3

        # Act
        result = data_privacy_logic.cleanup_expired_data(retention_days)

        # Assert
        assert result["interaction_logs"] == 10
        assert result["feedback_records"] == 5
        assert result["generated_images"] == 3
        
        # Verify repositories were called with correct cutoff date
        expected_cutoff = datetime.utcnow() - timedelta(days=retention_days)
        for repo_name in ['interaction_repository', 'feedback_repository', 'image_repository']:
            call_args = mock_repositories[repo_name].delete_older_than.call_args[0]
            # Check that the cutoff date is approximately correct (within 1 minute)
            assert abs((call_args[0] - expected_cutoff).total_seconds()) < 60

    def test_resolve_pseudonym_id_direct(self, data_privacy_logic):
        """Test resolving pseudonym_id when provided directly."""
        # Arrange
        pseudonym_id = uuid4()
        request = Mock(pseudonym_id=pseudonym_id, user_id=None)

        # Act
        result = data_privacy_logic._resolve_pseudonym_id(request)

        # Assert
        assert result == pseudonym_id

    def test_resolve_pseudonym_id_via_mapping(self, data_privacy_logic, mock_repositories):
        """Test resolving pseudonym_id via user_id mapping."""
        # Arrange
        user_id = uuid4()
        pseudonym_id = uuid4()
        request = Mock(pseudonym_id=None, user_id=user_id)
        
        mapping_mock = Mock(pseudonym_id=pseudonym_id)
        mock_repositories['pseudonym_mapping_repository'].get_by_user_id.return_value = mapping_mock

        # Act
        result = data_privacy_logic._resolve_pseudonym_id(request)

        # Assert
        assert result == pseudonym_id
        mock_repositories['pseudonym_mapping_repository'].get_by_user_id.assert_called_once_with(user_id)

    def test_resolve_pseudonym_id_no_mapping(self, data_privacy_logic, mock_repositories):
        """Test resolving pseudonym_id when no mapping exists."""
        # Arrange
        user_id = uuid4()
        request = Mock(pseudonym_id=None, user_id=user_id)
        
        mock_repositories['pseudonym_mapping_repository'].get_by_user_id.return_value = None

        # Act
        result = data_privacy_logic._resolve_pseudonym_id(request)

        # Assert
        assert result is None

    def test_pseudonymize_consent_record(self, data_privacy_logic):
        """Test pseudonymization of consent record."""
        # Arrange
        consent_id = uuid4()
        pseudonym_id = uuid4()
        granted_at = datetime.utcnow()
        
        consent_mock = Mock(
            consent_id=consent_id,
            pseudonym_id=pseudonym_id,
            consent_type="data_protection",
            granted=True,
            version="1.0",
            granted_at=granted_at,
            revoked_at=None
        )

        # Act
        result = data_privacy_logic._pseudonymize_consent_record(consent_mock)

        # Assert
        assert result["consent_id"] == str(consent_id)
        assert result["pseudonym_id"] == str(pseudonym_id)
        assert result["consent_type"] == "data_protection"
        assert result["granted"] is True
        assert result["version"] == "1.0"
        assert result["granted_at"] == granted_at.isoformat()
        assert result["revoked_at"] is None

    def test_check_user_id_exposure_nested(self, data_privacy_logic):
        """Test user_id exposure detection in nested data structures."""
        # Arrange
        data = {
            "level1": {
                "level2": {
                    "user_id": "12345",  # Should be detected
                    "pseudonym_id": "67890"
                }
            }
        }

        # Act
        violations = data_privacy_logic._check_user_id_exposure(data, "")

        # Assert
        assert len(violations) == 1
        assert "User ID exposure at level1.level2.user_id" in violations

    def test_check_pii_exposure_in_list(self, data_privacy_logic):
        """Test PII exposure detection in list structures."""
        # Arrange
        data = {
            "users": [
                {"pseudonym_id": "123"},
                {"email": "test@example.com", "pseudonym_id": "456"}  # Should be detected
            ]
        }

        # Act
        violations = data_privacy_logic._check_pii_exposure(data, "")

        # Assert
        assert len(violations) == 1
        assert "PII exposure (email) at users[1].email" in violations

    def test_generate_data_summary(self, data_privacy_logic):
        """Test generation of data summary for validation."""
        # Arrange
        data = {
            "participant_data": {
                "consents": [{"consent_id": "1"}, {"consent_id": "2"}],
                "surveys": [{"survey_id": "1"}],
                "chats": []
            }
        }

        # Act
        summary = data_privacy_logic._generate_data_summary(data)

        # Assert
        assert summary["total_records"] == 3
        assert summary["record_types"]["consents"] == 2
        assert summary["record_types"]["surveys"] == 1
        assert summary["record_types"]["chats"] == 0
        assert "validation_timestamp" in summary

    def test_delete_participant_data_repository_error(self, data_privacy_logic, mock_repositories, sample_pseudonym):
        """Test data deletion when repository operation fails."""
        # Arrange
        pseudonym_id = sample_pseudonym.pseudonym_id
        request = DataDeletionRequest(
            pseudonym_id=pseudonym_id,
            reason="User request",
            requested_by="admin"
        )
        
        mock_repositories['pseudonym_repository'].get_by_id.return_value = sample_pseudonym
        mock_repositories['interaction_repository'].delete_by_pseudonym.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(DataDeletionError, match="Data deletion failed"):
            data_privacy_logic.delete_participant_data(request)

    def test_export_participant_data_validation_failure(self, data_privacy_logic, mock_repositories, sample_pseudonym):
        """Test data export when pseudonymization validation fails."""
        # Arrange
        pseudonym_id = sample_pseudonym.pseudonym_id
        request = DataExportRequest(
            pseudonym_id=pseudonym_id,
            format="json",
            requested_by="admin"
        )
        
        # Mock repository to return data with user_id exposure
        mock_repositories['pseudonym_repository'].get_by_id.return_value = sample_pseudonym
        mock_repositories['consent_repository'].get_by_pseudonym.return_value = [
            Mock(consent_id=uuid4(), pseudonym_id=pseudonym_id, consent_type="data_protection", 
                 granted=True, version="1.0", granted_at=datetime.utcnow(), revoked_at=None)
        ]
        
        # Mock other repositories to return empty lists
        for repo_name in ['survey_repository', 'chat_repository', 'pald_repository', 
                         'image_repository', 'feedback_repository', 'interaction_repository']:
            mock_repositories[repo_name].get_by_pseudonym.return_value = []

        # Mock the validation to fail by patching the method
        original_validate = data_privacy_logic._validate_export_pseudonymization
        data_privacy_logic._validate_export_pseudonymization = Mock(
            return_value=PseudonymizationValidationResult(
                is_valid=False,
                violations=["Test violation"],
                validation_timestamp=datetime.utcnow(),
                data_summary={}
            )
        )

        # Act & Assert
        with pytest.raises(DataExportError, match="Export failed pseudonymization validation"):
            data_privacy_logic.export_participant_data(request)

        # Restore original method
        data_privacy_logic._validate_export_pseudonymization = original_validate