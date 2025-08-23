"""
Property-based tests for data privacy functionality.
Tests invariants and properties that should hold for all data privacy operations.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock

from src.logic.data_privacy_logic import DataPrivacyLogic
from src.data.schemas import DataDeletionRequest, DataExportRequest


class TestDataPrivacyProperties:
    """Property-based tests for data privacy operations."""

    @pytest.fixture
    def mock_repositories(self):
        """Create mock repositories for property testing."""
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

    def test_deletion_request_id_resolution_property(self, data_privacy_logic, mock_repositories):
        """Property: ID resolution should always return a valid UUID or None."""
        # Test cases for different request types
        test_cases = [
            # Direct pseudonym_id
            DataDeletionRequest(pseudonym_id=uuid4(), requested_by="admin"),
            # User_id with mapping
            DataDeletionRequest(user_id=uuid4(), requested_by="admin"),
            # Both provided (should prefer pseudonym_id)
            DataDeletionRequest(pseudonym_id=uuid4(), user_id=uuid4(), requested_by="admin"),
        ]
        
        for deletion_request in test_cases:
            # Arrange
            if deletion_request.user_id and not deletion_request.pseudonym_id:
                # Mock mapping exists
                mock_mapping = Mock(pseudonym_id=uuid4())
                mock_repositories['pseudonym_mapping_repository'].get_by_user_id.return_value = mock_mapping
            else:
                mock_repositories['pseudonym_mapping_repository'].get_by_user_id.return_value = None

            # Act
            resolved_id = data_privacy_logic._resolve_pseudonym_id(deletion_request)

            # Assert
            if resolved_id is not None:
                assert isinstance(resolved_id, UUID)
            
            # Property: If pseudonym_id is provided directly, it should be returned
            if deletion_request.pseudonym_id:
                assert resolved_id == deletion_request.pseudonym_id

    def test_cleanup_cutoff_date_property(self, data_privacy_logic, mock_repositories):
        """Property: Cleanup cutoff date should always be in the past and correctly calculated."""
        # Test different retention periods
        retention_periods = [1, 30, 90, 365, 1095]  # 1 day to 3 years
        
        for retention_days in retention_periods:
            # Arrange
            mock_repositories['interaction_repository'].delete_older_than.return_value = 0
            mock_repositories['feedback_repository'].delete_older_than.return_value = 0
            mock_repositories['image_repository'].delete_older_than.return_value = 0
            
            start_time = datetime.utcnow()

            # Act
            data_privacy_logic.cleanup_expired_data(retention_days)

            # Assert
            # Verify that delete_older_than was called with a datetime in the past
            for repo_name in ['interaction_repository', 'feedback_repository', 'image_repository']:
                call_args = mock_repositories[repo_name].delete_older_than.call_args[0]
                cutoff_date = call_args[0]
                
                # Property: Cutoff date should be in the past
                assert cutoff_date < start_time
                
                # Property: Cutoff date should be approximately retention_days ago
                expected_cutoff = start_time - timedelta(days=retention_days)
                time_diff = abs((cutoff_date - expected_cutoff).total_seconds())
                assert time_diff < 60  # Within 1 minute tolerance

    def test_pseudonymization_validation_consistency_property(self, data_privacy_logic):
        """Property: Pseudonymization validation should be consistent and deterministic."""
        # Test with various data structures
        test_data_sets = [
            # Valid pseudonymized data
            {
                "participant_data": {
                    "pseudonym": {
                        "pseudonym_id": str(uuid4()),
                        "pseudonym_text": "M03s2001AJ13"
                    },
                    "consents": [
                        {
                            "consent_id": str(uuid4()),
                            "pseudonym_id": str(uuid4()),
                            "consent_type": "data_protection",
                            "granted": True
                        }
                    ]
                }
            },
            # Invalid data with user_id
            {
                "participant_data": {
                    "user_info": {
                        "user_id": str(uuid4()),
                        "pseudonym_id": str(uuid4())
                    }
                }
            }
        ]
        
        for participant_data in test_data_sets:
            # Act
            result1 = data_privacy_logic.validate_pseudonymization(participant_data)
            result2 = data_privacy_logic.validate_pseudonymization(participant_data)

            # Assert
            # Property: Validation should be deterministic
            assert result1.is_valid == result2.is_valid
            assert result1.violations == result2.violations
            
            # Property: If data is valid, there should be no violations
            if result1.is_valid:
                assert len(result1.violations) == 0
            else:
                assert len(result1.violations) > 0

    def test_user_id_detection_property(self, data_privacy_logic):
        """Property: User ID detection should find all user_id fields regardless of nesting."""
        # Test various data structures with user_id fields
        test_cases = [
            # Direct user_id
            {"user_id": "12345"},
            # Nested user_id
            {"level1": {"level2": {"user_id": "12345"}}},
            # user_id in list
            {"users": [{"pseudonym_id": "123"}, {"user_id": "456"}]},
            # Multiple user_id variants
            {"user_id": "123", "userid": "456", "user_identifier": "789"},
            # No user_id (should have no violations)
            {"pseudonym_id": "123", "data": "safe"}
        ]
        
        for test_data in test_cases:
            # Act
            violations = data_privacy_logic._check_user_id_exposure(test_data, "")

            # Assert
            # Property: If test_data contains 'user_id' key, it should be detected
            def contains_user_id(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_path = f"{path}.{key}" if path else key
                        if key.lower() in ['user_id', 'userid', 'user_identifier']:
                            return True
                        if contains_user_id(value, current_path):
                            return True
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        if contains_user_id(item, f"{path}[{i}]"):
                            return True
                return False

            has_user_id = contains_user_id(test_data)
            has_violations = len(violations) > 0

            # Property: If user_id exists in data, violations should be found
            if has_user_id:
                assert has_violations
            
            # Property: All violations should mention user ID exposure
            for violation in violations:
                assert "User ID exposure" in violation

    def test_deletion_count_aggregation_property(self, data_privacy_logic, mock_repositories):
        """Property: Total deletion count should equal sum of individual counts."""
        # Test with different deletion count combinations
        deletion_count_sets = [
            [5, 3, 2, 4, 10, 1, 3],  # Normal case
            [0, 0, 0, 0, 0, 0, 0],   # No data case
            [100, 50, 25, 75, 200, 10, 30],  # Large numbers
        ]
        
        for deletion_counts in deletion_count_sets:
            # Arrange
            pseudonym_id = uuid4()
            request = DataDeletionRequest(
                pseudonym_id=pseudonym_id,
                reason="Test",
                requested_by="admin"
            )
            
            mock_pseudonym = Mock(
                pseudonym_id=pseudonym_id,
                pseudonym_text="TEST123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            mock_repositories['pseudonym_repository'].get_by_id.return_value = mock_pseudonym
            
            # Assign deletion counts to repositories
            repo_names = ['interaction_repository', 'feedback_repository', 'image_repository',
                         'pald_repository', 'chat_repository', 'survey_repository', 'consent_repository']
            
            for i, repo_name in enumerate(repo_names):
                count = deletion_counts[i]
                mock_repositories[repo_name].delete_by_pseudonym.return_value = count
            
            mock_repositories['pseudonym_mapping_repository'].delete_by_pseudonym.return_value = True
            mock_repositories['pseudonym_repository'].delete.return_value = True

            # Act
            result = data_privacy_logic.delete_participant_data(request)

            # Assert
            # Property: Total should equal sum of individual counts plus pseudonym (1) and mapping (1)
            expected_total = sum(deletion_counts) + 2  # +2 for pseudonym and mapping
            assert result.total_records_deleted == expected_total

    def test_pseudonym_text_preservation_property(self, data_privacy_logic, mock_repositories):
        """Property: Pseudonym text should be preserved in export operations."""
        # Test with different pseudonym texts
        pseudonym_texts = ["M03s2001AJ13", "A12z1995BC42", "X01a2000DE99"]
        
        for pseudonym_text in pseudonym_texts:
            # Arrange
            pseudonym_id = uuid4()
            request = DataExportRequest(
                pseudonym_id=pseudonym_id,
                format="json",
                requested_by="admin"
            )
            
            mock_pseudonym = Mock(
                pseudonym_id=pseudonym_id,
                pseudonym_text=pseudonym_text,
                pseudonym_hash="hash123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            mock_repositories['pseudonym_repository'].get_by_id.return_value = mock_pseudonym
            
            # Mock all other repositories return empty
            for repo_name in ['consent_repository', 'survey_repository', 'chat_repository',
                             'pald_repository', 'image_repository', 'feedback_repository', 'interaction_repository']:
                mock_repositories[repo_name].get_by_pseudonym.return_value = []

            # Act
            result = data_privacy_logic.export_participant_data(request)

            # Assert
            # Property: Original pseudonym text should be preserved in export
            exported_pseudonym = result.export_data["participant_data"]["pseudonym"]
            assert exported_pseudonym["pseudonym_text"] == pseudonym_text
            assert exported_pseudonym["pseudonym_id"] == str(pseudonym_id)

    def test_pii_detection_completeness_property(self, data_privacy_logic):
        """Property: PII detection should find all configured PII fields."""
        # Test with different combinations of PII fields
        pii_field_names = ['email', 'phone', 'address', 'name', 'username', 'real_name']
        
        test_cases = [
            # Only PII fields
            ['email', 'phone'],
            # Mix of PII and safe fields
            ['email', 'safe_field', 'name'],
            # No PII fields
            ['safe_field1', 'safe_field2'],
            # All PII fields
            pii_field_names,
        ]
        
        for pii_fields in test_cases:
            # Arrange
            # Create test data with some PII fields
            test_data = {}
            expected_violations = 0
            
            for field in pii_fields:
                if field in pii_field_names:
                    test_data[field] = "sensitive_data"
                    expected_violations += 1
                else:
                    test_data[field] = "safe_data"

            # Act
            violations = data_privacy_logic._check_pii_exposure(test_data, "")

            # Assert
            # Property: Number of violations should match number of PII fields
            assert len(violations) == expected_violations
            
            # Property: Each violation should reference the correct field
            for violation in violations:
                assert "PII exposure" in violation
                # Extract field name from violation message
                field_mentioned = any(f"({field})" in violation for field in pii_field_names if field in pii_fields)
                assert field_mentioned

    def test_data_summary_record_count_property(self, data_privacy_logic):
        """Property: Data summary should accurately count records."""
        # Test with different record counts
        record_counts = [0, 1, 5, 10, 50]
        
        for record_count in record_counts:
            # Arrange
            test_data = {
                "participant_data": {
                    "consents": [{"id": i} for i in range(record_count)],
                    "surveys": []
                }
            }

            # Act
            summary = data_privacy_logic._generate_data_summary(test_data)

            # Assert
            # Property: Record counts should be accurate
            assert summary["record_types"]["consents"] == record_count
            assert summary["record_types"]["surveys"] == 0
            assert summary["total_records"] == record_count

    def test_export_data_structure_property(self, data_privacy_logic, mock_repositories):
        """Property: Export data should always have consistent structure."""
        # Test with different export request configurations
        export_requests = [
            DataExportRequest(pseudonym_id=uuid4(), format="json", include_metadata=True, requested_by="admin"),
            DataExportRequest(pseudonym_id=uuid4(), format="csv", include_metadata=False, requested_by="user"),
            DataExportRequest(user_id=uuid4(), format="xml", include_metadata=True, requested_by="system"),
        ]
        
        for export_request in export_requests:
            # Arrange
            pseudonym_id = export_request.pseudonym_id or uuid4()
            if not export_request.pseudonym_id:
                # Mock user_id mapping
                mock_mapping = Mock(pseudonym_id=pseudonym_id)
                mock_repositories['pseudonym_mapping_repository'].get_by_user_id.return_value = mock_mapping
            
            mock_pseudonym = Mock(
                pseudonym_id=pseudonym_id,
                pseudonym_text="TEST123",
                pseudonym_hash="hash123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            mock_repositories['pseudonym_repository'].get_by_id.return_value = mock_pseudonym
            
            # Mock all repositories return empty
            for repo_name in ['consent_repository', 'survey_repository', 'chat_repository',
                             'pald_repository', 'image_repository', 'feedback_repository', 'interaction_repository']:
                mock_repositories[repo_name].get_by_pseudonym.return_value = []

            # Act
            result = data_privacy_logic.export_participant_data(export_request)

            # Assert
            # Property: Export data should have consistent structure
            assert "export_metadata" in result.export_data
            assert "participant_data" in result.export_data
            
            participant_data = result.export_data["participant_data"]
            required_sections = ["pseudonym", "consents", "survey_responses", "chat_messages", 
                               "pald_data", "generated_images", "feedback_records"]
            
            for section in required_sections:
                assert section in participant_data
            
            # Property: Metadata should include request parameters
            metadata = result.export_data["export_metadata"]
            assert metadata["export_format"] == export_request.format
            assert metadata["include_metadata"] == export_request.include_metadata