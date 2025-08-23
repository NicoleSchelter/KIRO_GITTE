"""
Unit tests for data privacy service.
Tests service layer operations for data deletion, export, and validation.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

from src.services.data_privacy_service import DataPrivacyService
from src.data.schemas import (
    DataDeletionRequest,
    DataDeletionResult,
    DataExportRequest,
    DataExportResult,
    PseudonymizationValidationResult,
    DataCleanupResult,
)
from src.logic.data_privacy_logic import (
    DataDeletionError,
    DataExportError,
    PseudonymizationValidationError,
)


class TestDataPrivacyService:
    """Test cases for DataPrivacyService."""

    @pytest.fixture
    def data_privacy_service(self):
        """Create DataPrivacyService instance."""
        return DataPrivacyService()

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session

    @pytest.fixture
    def sample_deletion_request(self):
        """Create sample data deletion request."""
        return DataDeletionRequest(
            pseudonym_id=uuid4(),
            reason="User request",
            requested_by="admin"
        )

    @pytest.fixture
    def sample_export_request(self):
        """Create sample data export request."""
        return DataExportRequest(
            pseudonym_id=uuid4(),
            format="json",
            include_metadata=True,
            requested_by="admin"
        )

    @pytest.fixture
    def sample_deletion_result(self):
        """Create sample deletion result."""
        return DataDeletionResult(
            success=True,
            pseudonym_id=uuid4(),
            deletion_summary={"consents": 2, "surveys": 1},
            total_records_deleted=3,
            deletion_timestamp=datetime.utcnow(),
            message="Successfully deleted data"
        )

    @pytest.fixture
    def sample_export_result(self):
        """Create sample export result."""
        return DataExportResult(
            success=True,
            pseudonym_id=uuid4(),
            export_data={"participant_data": {"pseudonym": {"pseudonym_id": str(uuid4())}}},
            export_timestamp=datetime.utcnow(),
            record_counts={"consents": 2, "surveys": 1},
            message="Successfully exported data"
        )

    @patch('src.services.data_privacy_service.get_session')
    def test_delete_participant_data_success(self, mock_get_session, data_privacy_service, 
                                           mock_session, sample_deletion_request, sample_deletion_result):
        """Test successful participant data deletion."""
        # Arrange
        mock_get_session.return_value = mock_session
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.delete_participant_data.return_value = sample_deletion_result
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.delete_participant_data(sample_deletion_request)

            # Assert
            assert result == sample_deletion_result
            mock_logic.delete_participant_data.assert_called_once_with(sample_deletion_request)
            mock_session.commit.assert_called_once()

    @patch('src.services.data_privacy_service.get_session')
    def test_delete_participant_data_failure(self, mock_get_session, data_privacy_service, 
                                           mock_session, sample_deletion_request):
        """Test participant data deletion failure with rollback."""
        # Arrange
        mock_get_session.return_value = mock_session
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.delete_participant_data.side_effect = DataDeletionError("Deletion failed")
            mock_get_logic.return_value = mock_logic

            # Act & Assert
            with pytest.raises(DataDeletionError):
                data_privacy_service.delete_participant_data(sample_deletion_request)
            
            mock_session.rollback.assert_called_once()

    @patch('src.services.data_privacy_service.get_session')
    def test_export_participant_data_success(self, mock_get_session, data_privacy_service, 
                                           mock_session, sample_export_request, sample_export_result):
        """Test successful participant data export."""
        # Arrange
        mock_get_session.return_value = mock_session
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.export_participant_data.return_value = sample_export_result
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.export_participant_data(sample_export_request)

            # Assert
            assert result == sample_export_result
            mock_logic.export_participant_data.assert_called_once_with(sample_export_request)

    @patch('src.services.data_privacy_service.get_session')
    def test_validate_pseudonymization_success(self, mock_get_session, data_privacy_service, mock_session):
        """Test successful pseudonymization validation."""
        # Arrange
        mock_get_session.return_value = mock_session
        test_data = {"participant_data": {"pseudonym_id": str(uuid4())}}
        
        validation_result = PseudonymizationValidationResult(
            is_valid=True,
            violations=[],
            validation_timestamp=datetime.utcnow(),
            data_summary={"total_records": 1}
        )
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.validate_pseudonymization.return_value = validation_result
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.validate_pseudonymization(test_data)

            # Assert
            assert result == validation_result
            mock_logic.validate_pseudonymization.assert_called_once_with(test_data)

    @patch('src.services.data_privacy_service.get_session')
    def test_cleanup_expired_data_success(self, mock_get_session, data_privacy_service, mock_session):
        """Test successful expired data cleanup."""
        # Arrange
        mock_get_session.return_value = mock_session
        retention_days = 30
        cleanup_summary = {"interaction_logs": 10, "feedback_records": 5}
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.cleanup_expired_data.return_value = cleanup_summary
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.cleanup_expired_data(retention_days)

            # Assert
            assert result.success is True
            assert result.total_records_deleted == 15
            assert result.cleanup_summary == cleanup_summary
            assert result.retention_policy == "30_days"
            mock_logic.cleanup_expired_data.assert_called_once_with(retention_days)
            mock_session.commit.assert_called_once()

    @patch('src.services.data_privacy_service.get_session')
    def test_cleanup_expired_data_failure(self, mock_get_session, data_privacy_service, mock_session):
        """Test expired data cleanup failure."""
        # Arrange
        mock_get_session.return_value = mock_session
        retention_days = 30
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.cleanup_expired_data.side_effect = Exception("Cleanup failed")
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.cleanup_expired_data(retention_days)

            # Assert
            assert result.success is False
            assert result.total_records_deleted == 0
            assert result.error_message == "Cleanup failed"
            mock_session.rollback.assert_called_once()

    @patch('src.services.data_privacy_service.get_session')
    def test_verify_data_privacy_compliance_success(self, mock_get_session, data_privacy_service, mock_session):
        """Test successful data privacy compliance verification."""
        # Arrange
        mock_get_session.return_value = mock_session
        pseudonym_id = uuid4()
        
        export_result = DataExportResult(
            success=True,
            pseudonym_id=pseudonym_id,
            export_data={"participant_data": {"pseudonym_id": str(pseudonym_id)}},
            export_timestamp=datetime.utcnow(),
            record_counts={},
            message="Export successful"
        )
        
        validation_result = PseudonymizationValidationResult(
            is_valid=True,
            violations=[],
            validation_timestamp=datetime.utcnow(),
            data_summary={"total_records": 1}
        )
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.export_participant_data.return_value = export_result
            mock_logic.validate_pseudonymization.return_value = validation_result
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.verify_data_privacy_compliance(pseudonym_id)

            # Assert
            assert result["compliant"] is True
            assert result["violations"] == []
            assert "validation_timestamp" in result

    @patch('src.services.data_privacy_service.get_session')
    def test_verify_data_privacy_compliance_violations(self, mock_get_session, data_privacy_service, mock_session):
        """Test data privacy compliance verification with violations."""
        # Arrange
        mock_get_session.return_value = mock_session
        pseudonym_id = uuid4()
        
        export_result = DataExportResult(
            success=True,
            pseudonym_id=pseudonym_id,
            export_data={"participant_data": {"user_id": str(uuid4())}},  # Violation
            export_timestamp=datetime.utcnow(),
            record_counts={},
            message="Export successful"
        )
        
        validation_result = PseudonymizationValidationResult(
            is_valid=False,
            violations=["User ID exposure at participant_data.user_id"],
            validation_timestamp=datetime.utcnow(),
            data_summary={"total_records": 1}
        )
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.export_participant_data.return_value = export_result
            mock_logic.validate_pseudonymization.return_value = validation_result
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.verify_data_privacy_compliance(pseudonym_id)

            # Assert
            assert result["compliant"] is False
            assert len(result["violations"]) == 1
            assert "User ID exposure" in result["violations"][0]

    @patch('src.services.data_privacy_service.get_session')
    def test_verify_data_privacy_compliance_export_failure(self, mock_get_session, data_privacy_service, mock_session):
        """Test data privacy compliance verification when export fails."""
        # Arrange
        mock_get_session.return_value = mock_session
        pseudonym_id = uuid4()
        
        export_result = DataExportResult(
            success=False,
            pseudonym_id=pseudonym_id,
            export_data={},
            export_timestamp=datetime.utcnow(),
            record_counts={},
            message="Export failed",
            error_message="Database error"
        )
        
        with patch.object(data_privacy_service, '_get_data_privacy_logic') as mock_get_logic:
            mock_logic = Mock()
            mock_logic.export_participant_data.return_value = export_result
            mock_get_logic.return_value = mock_logic

            # Act
            result = data_privacy_service.verify_data_privacy_compliance(pseudonym_id)

            # Assert
            assert result["compliant"] is False
            assert "Failed to export data for compliance check" in result["error"]
            assert result["details"] == "Database error"

    @patch('src.services.data_privacy_service.get_session')
    @patch('src.services.data_privacy_service.PseudonymRepository')
    @patch('src.services.data_privacy_service.StudyConsentRepository')
    def test_get_participant_data_summary_success(self, mock_consent_repo_class, mock_pseudonym_repo_class,
                                                mock_get_session, data_privacy_service, mock_session):
        """Test successful participant data summary retrieval."""
        # Arrange
        mock_get_session.return_value = mock_session
        pseudonym_id = uuid4()
        
        # Mock pseudonym
        mock_pseudonym = Mock(
            pseudonym_id=pseudonym_id,
            pseudonym_text="M03s2001AJ13",
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        # Mock repositories
        mock_pseudonym_repo = Mock()
        mock_pseudonym_repo.get_by_id.return_value = mock_pseudonym
        mock_pseudonym_repo_class.return_value = mock_pseudonym_repo
        
        mock_consent_repo = Mock()
        mock_consent_repo.get_by_pseudonym.return_value = [Mock(), Mock()]  # 2 consents
        mock_consent_repo_class.return_value = mock_consent_repo
        
        # Mock other repositories to return empty lists
        with patch('src.services.data_privacy_service.StudySurveyResponseRepository') as mock_survey_repo_class, \
             patch('src.services.data_privacy_service.ChatMessageRepository') as mock_chat_repo_class, \
             patch('src.services.data_privacy_service.StudyPALDDataRepository') as mock_pald_repo_class, \
             patch('src.services.data_privacy_service.GeneratedImageRepository') as mock_image_repo_class, \
             patch('src.services.data_privacy_service.FeedbackRecordRepository') as mock_feedback_repo_class, \
             patch('src.services.data_privacy_service.InteractionLogRepository') as mock_interaction_repo_class:
            
            for mock_repo_class in [mock_survey_repo_class, mock_chat_repo_class, mock_pald_repo_class,
                                  mock_image_repo_class, mock_feedback_repo_class, mock_interaction_repo_class]:
                mock_repo = Mock()
                mock_repo.get_by_pseudonym.return_value = []
                mock_repo_class.return_value = mock_repo

            # Act
            result = data_privacy_service.get_participant_data_summary(pseudonym_id)

            # Assert
            assert result["pseudonym_id"] == str(pseudonym_id)
            assert result["pseudonym_text"] == "M03s2001AJ13"
            assert result["is_active"] is True
            assert result["record_counts"]["consents"] == 2
            assert result["total_records"] == 2

    @patch('src.services.data_privacy_service.get_session')
    @patch('src.services.data_privacy_service.PseudonymRepository')
    def test_get_participant_data_summary_pseudonym_not_found(self, mock_pseudonym_repo_class,
                                                            mock_get_session, data_privacy_service, mock_session):
        """Test participant data summary when pseudonym is not found."""
        # Arrange
        mock_get_session.return_value = mock_session
        pseudonym_id = uuid4()
        
        mock_pseudonym_repo = Mock()
        mock_pseudonym_repo.get_by_id.return_value = None
        mock_pseudonym_repo_class.return_value = mock_pseudonym_repo

        # Act
        result = data_privacy_service.get_participant_data_summary(pseudonym_id)

        # Assert
        assert "error" in result
        assert result["error"] == "Pseudonym not found"

    def test_get_data_privacy_logic_without_session(self, data_privacy_service):
        """Test getting data privacy logic without session raises error."""
        # Act & Assert
        with pytest.raises(RuntimeError, match="Service not properly initialized with session"):
            data_privacy_service._get_data_privacy_logic()

    @patch('src.services.data_privacy_service.get_session')
    def test_get_data_privacy_logic_initialization(self, mock_get_session, data_privacy_service, mock_session):
        """Test data privacy logic initialization with all repositories."""
        # Arrange
        mock_get_session.return_value = mock_session
        data_privacy_service._session = mock_session
        
        with patch('src.services.data_privacy_service.PseudonymRepository') as mock_pseudonym_repo, \
             patch('src.services.data_privacy_service.PseudonymMappingRepository') as mock_mapping_repo, \
             patch('src.services.data_privacy_service.StudyConsentRepository') as mock_consent_repo, \
             patch('src.services.data_privacy_service.StudySurveyResponseRepository') as mock_survey_repo, \
             patch('src.services.data_privacy_service.ChatMessageRepository') as mock_chat_repo, \
             patch('src.services.data_privacy_service.StudyPALDDataRepository') as mock_pald_repo, \
             patch('src.services.data_privacy_service.GeneratedImageRepository') as mock_image_repo, \
             patch('src.services.data_privacy_service.FeedbackRecordRepository') as mock_feedback_repo, \
             patch('src.services.data_privacy_service.InteractionLogRepository') as mock_interaction_repo, \
             patch('src.services.data_privacy_service.DataPrivacyLogic') as mock_logic_class:

            # Act
            logic = data_privacy_service._get_data_privacy_logic()

            # Assert
            # Verify all repository classes were instantiated with session
            mock_pseudonym_repo.assert_called_once_with(mock_session)
            mock_mapping_repo.assert_called_once_with(mock_session)
            mock_consent_repo.assert_called_once_with(mock_session)
            mock_survey_repo.assert_called_once_with(mock_session)
            mock_chat_repo.assert_called_once_with(mock_session)
            mock_pald_repo.assert_called_once_with(mock_session)
            mock_image_repo.assert_called_once_with(mock_session)
            mock_feedback_repo.assert_called_once_with(mock_session)
            mock_interaction_repo.assert_called_once_with(mock_session)
            
            # Verify DataPrivacyLogic was instantiated with all repositories
            mock_logic_class.assert_called_once()
            call_kwargs = mock_logic_class.call_args[1]
            assert 'pseudonym_repository' in call_kwargs
            assert 'pseudonym_mapping_repository' in call_kwargs
            assert 'consent_repository' in call_kwargs
            assert 'survey_repository' in call_kwargs
            assert 'chat_repository' in call_kwargs
            assert 'pald_repository' in call_kwargs
            assert 'image_repository' in call_kwargs
            assert 'feedback_repository' in call_kwargs
            assert 'interaction_repository' in call_kwargs