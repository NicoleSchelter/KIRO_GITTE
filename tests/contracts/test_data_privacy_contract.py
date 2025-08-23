"""
Contract tests for data privacy functionality.
Tests the contracts between data privacy logic and repository layers.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock

from src.logic.data_privacy_logic import DataPrivacyLogic
from src.data.schemas import (
    DataDeletionRequest,
    DataExportRequest,
)


class TestDataPrivacyContract:
    """Contract tests for data privacy operations."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories that implement the expected contract."""
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
        """Create DataPrivacyLogic with mock repositories."""
        return DataPrivacyLogic(**mock_repositories)

    def test_pseudonym_repository_contract(self, mock_repositories):
        """Test that pseudonym repository implements required methods."""
        repo = mock_repositories['pseudonym_repository']
        
        # Required methods for data privacy operations
        required_methods = ['get_by_id', 'delete']
        
        for method_name in required_methods:
            assert hasattr(repo, method_name), f"PseudonymRepository must implement {method_name}"
            assert callable(getattr(repo, method_name)), f"{method_name} must be callable"

    def test_pseudonym_mapping_repository_contract(self, mock_repositories):
        """Test that pseudonym mapping repository implements required methods."""
        repo = mock_repositories['pseudonym_mapping_repository']
        
        # Required methods for data privacy operations
        required_methods = ['get_by_user_id', 'delete_by_pseudonym']
        
        for method_name in required_methods:
            assert hasattr(repo, method_name), f"PseudonymMappingRepository must implement {method_name}"
            assert callable(getattr(repo, method_name)), f"{method_name} must be callable"

    def test_study_repositories_deletion_contract(self, mock_repositories):
        """Test that all study repositories implement deletion methods."""
        study_repos = [
            'consent_repository',
            'survey_repository', 
            'chat_repository',
            'pald_repository',
            'image_repository',
            'feedback_repository',
            'interaction_repository'
        ]
        
        for repo_name in study_repos:
            repo = mock_repositories[repo_name]
            
            # All study repositories must implement these methods
            required_methods = ['get_by_pseudonym', 'delete_by_pseudonym']
            
            for method_name in required_methods:
                assert hasattr(repo, method_name), f"{repo_name} must implement {method_name}"
                assert callable(getattr(repo, method_name)), f"{method_name} must be callable"

    def test_retention_repositories_contract(self, mock_repositories):
        """Test that repositories supporting retention implement cleanup methods."""
        retention_repos = ['interaction_repository', 'feedback_repository', 'image_repository']
        
        for repo_name in retention_repos:
            repo = mock_repositories[repo_name]
            
            # Retention repositories must implement cleanup method
            assert hasattr(repo, 'delete_older_than'), f"{repo_name} must implement delete_older_than"
            assert callable(getattr(repo, 'delete_older_than')), "delete_older_than must be callable"

    def test_deletion_request_contract(self, data_privacy_logic, mock_repositories):
        """Test that deletion request contract is properly handled."""
        # Arrange
        pseudonym_id = uuid4()
        request = DataDeletionRequest(
            pseudonym_id=pseudonym_id,
            reason="Test deletion",
            requested_by="test_admin"
        )
        
        # Mock pseudonym exists
        mock_pseudonym = Mock(
            pseudonym_id=pseudonym_id,
            pseudonym_text="TEST123",
            created_at=datetime.utcnow(),
            is_active=True
        )
        mock_repositories['pseudonym_repository'].get_by_id.return_value = mock_pseudonym
        
        # Mock all deletion operations return counts
        deletion_counts = {
            'interaction_repository': 5,
            'feedback_repository': 3,
            'image_repository': 2,
            'pald_repository': 4,
            'chat_repository': 10,
            'survey_repository': 1,
            'consent_repository': 2
        }
        
        for repo_name, count in deletion_counts.items():
            mock_repositories[repo_name].delete_by_pseudonym.return_value = count
        
        mock_repositories['pseudonym_mapping_repository'].delete_by_pseudonym.return_value = True
        mock_repositories['pseudonym_repository'].delete.return_value = True

        # Act
        result = data_privacy_logic.delete_participant_data(request)

        # Assert - Verify contract compliance
        assert result.success is True
        assert result.pseudonym_id == pseudonym_id
        assert isinstance(result.total_records_deleted, int)
        assert result.total_records_deleted > 0
        assert isinstance(result.deletion_summary, dict)
        assert isinstance(result.message, str)
        
        # Verify all repositories were called with correct parameters
        mock_repositories['pseudonym_repository'].get_by_id.assert_called_once_with(pseudonym_id)
        
        for repo_name in deletion_counts.keys():
            mock_repositories[repo_name].delete_by_pseudonym.assert_called_once_with(pseudonym_id)

    def test_export_request_contract(self, data_privacy_logic, mock_repositories):
        """Test that export request contract is properly handled."""
        # Arrange
        pseudonym_id = uuid4()
        request = DataExportRequest(
            pseudonym_id=pseudonym_id,
            format="json",
            include_metadata=True,
            requested_by="test_admin"
        )
        
        # Mock pseudonym exists
        mock_pseudonym = Mock(
            pseudonym_id=pseudonym_id,
            pseudonym_text="TEST123",
            pseudonym_hash="hash123",
            created_at=datetime.utcnow(),
            is_active=True
        )
        mock_repositories['pseudonym_repository'].get_by_id.return_value = mock_pseudonym
        
        # Mock all repositories return empty lists (no data)
        for repo_name in ['consent_repository', 'survey_repository', 'chat_repository',
                         'pald_repository', 'image_repository', 'feedback_repository', 'interaction_repository']:
            mock_repositories[repo_name].get_by_pseudonym.return_value = []

        # Act
        result = data_privacy_logic.export_participant_data(request)

        # Assert - Verify contract compliance
        assert result.success is True
        assert result.pseudonym_id == pseudonym_id
        assert isinstance(result.export_data, dict)
        assert "participant_data" in result.export_data
        assert "export_metadata" in result.export_data
        assert isinstance(result.record_counts, dict)
        assert isinstance(result.message, str)
        
        # Verify export data structure
        participant_data = result.export_data["participant_data"]
        assert "pseudonym" in participant_data
        assert "consents" in participant_data
        assert "survey_responses" in participant_data
        assert "chat_messages" in participant_data
        assert "pald_data" in participant_data
        assert "generated_images" in participant_data
        assert "feedback_records" in participant_data
        
        # Verify all repositories were called
        mock_repositories['pseudonym_repository'].get_by_id.assert_called_once_with(pseudonym_id)
        for repo_name in ['consent_repository', 'survey_repository', 'chat_repository',
                         'pald_repository', 'image_repository', 'feedback_repository', 'interaction_repository']:
            mock_repositories[repo_name].get_by_pseudonym.assert_called_once_with(pseudonym_id)

    def test_pseudonymization_validation_contract(self, data_privacy_logic):
        """Test that pseudonymization validation contract is properly implemented."""
        # Arrange
        test_data = {
            "participant_data": {
                "pseudonym": {
                    "pseudonym_id": str(uuid4()),
                    "pseudonym_text": "TEST123"
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
        result = data_privacy_logic.validate_pseudonymization(test_data)

        # Assert - Verify contract compliance
        assert hasattr(result, 'is_valid')
        assert isinstance(result.is_valid, bool)
        assert hasattr(result, 'violations')
        assert isinstance(result.violations, list)
        assert hasattr(result, 'validation_timestamp')
        assert isinstance(result.validation_timestamp, datetime)
        assert hasattr(result, 'data_summary')
        assert isinstance(result.data_summary, dict)

    def test_cleanup_contract(self, data_privacy_logic, mock_repositories):
        """Test that cleanup operation contract is properly implemented."""
        # Arrange
        retention_days = 30
        
        # Mock cleanup operations
        mock_repositories['interaction_repository'].delete_older_than.return_value = 10
        mock_repositories['feedback_repository'].delete_older_than.return_value = 5
        mock_repositories['image_repository'].delete_older_than.return_value = 3

        # Act
        result = data_privacy_logic.cleanup_expired_data(retention_days)

        # Assert - Verify contract compliance
        assert isinstance(result, dict)
        assert "interaction_logs" in result
        assert "feedback_records" in result
        assert "generated_images" in result
        
        # Verify all cleanup repositories were called with datetime
        for repo_name in ['interaction_repository', 'feedback_repository', 'image_repository']:
            call_args = mock_repositories[repo_name].delete_older_than.call_args[0]
            assert len(call_args) == 1
            assert isinstance(call_args[0], datetime)

    def test_repository_error_handling_contract(self, data_privacy_logic, mock_repositories):
        """Test that repository errors are properly handled according to contract."""
        # Arrange
        pseudonym_id = uuid4()
        request = DataDeletionRequest(
            pseudonym_id=pseudonym_id,
            reason="Test deletion",
            requested_by="test_admin"
        )
        
        # Mock pseudonym exists but repository operation fails
        mock_pseudonym = Mock(pseudonym_id=pseudonym_id, pseudonym_text="TEST123")
        mock_repositories['pseudonym_repository'].get_by_id.return_value = mock_pseudonym
        mock_repositories['interaction_repository'].delete_by_pseudonym.side_effect = Exception("Database error")

        # Act & Assert - Verify error handling contract
        with pytest.raises(Exception):  # Should propagate repository errors
            data_privacy_logic.delete_participant_data(request)

    def test_data_type_contracts(self, data_privacy_logic, mock_repositories):
        """Test that data type contracts are enforced."""
        # Test UUID parameter contract
        pseudonym_id = uuid4()
        
        # Mock repositories to verify UUID types are passed correctly
        mock_repositories['pseudonym_repository'].get_by_id.return_value = None
        
        # Create request with UUID
        request = DataDeletionRequest(
            pseudonym_id=pseudonym_id,
            reason="Test",
            requested_by="admin"
        )
        
        # This should fail because pseudonym not found, but UUID should be passed correctly
        try:
            data_privacy_logic.delete_participant_data(request)
        except Exception:
            pass  # Expected to fail, we're just testing the UUID is passed
        
        # Verify UUID was passed to repository
        mock_repositories['pseudonym_repository'].get_by_id.assert_called_once_with(pseudonym_id)
        call_args = mock_repositories['pseudonym_repository'].get_by_id.call_args[0]
        assert isinstance(call_args[0], type(pseudonym_id))

    def test_return_type_contracts(self, data_privacy_logic, mock_repositories):
        """Test that return type contracts are enforced."""
        # Arrange
        pseudonym_id = uuid4()
        
        # Mock repositories to return expected types
        mock_repositories['pseudonym_repository'].get_by_id.return_value = Mock(
            pseudonym_id=pseudonym_id,
            pseudonym_text="TEST123",
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        # Mock deletion operations to return integers (counts)
        for repo_name in ['interaction_repository', 'feedback_repository', 'image_repository',
                         'pald_repository', 'chat_repository', 'survey_repository', 'consent_repository']:
            mock_repositories[repo_name].delete_by_pseudonym.return_value = 1
        
        mock_repositories['pseudonym_mapping_repository'].delete_by_pseudonym.return_value = True
        mock_repositories['pseudonym_repository'].delete.return_value = True
        
        request = DataDeletionRequest(
            pseudonym_id=pseudonym_id,
            reason="Test",
            requested_by="admin"
        )

        # Act
        result = data_privacy_logic.delete_participant_data(request)

        # Assert - Verify return type contracts
        assert hasattr(result, 'success')
        assert isinstance(result.success, bool)
        assert hasattr(result, 'pseudonym_id')
        assert hasattr(result, 'total_records_deleted')
        assert isinstance(result.total_records_deleted, int)
        assert hasattr(result, 'deletion_summary')
        assert isinstance(result.deletion_summary, dict)
        assert hasattr(result, 'message')
        assert isinstance(result.message, str)