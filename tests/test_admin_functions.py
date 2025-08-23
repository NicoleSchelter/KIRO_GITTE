"""
Unit tests for admin convenience functions.
Tests database initialization, reset, and utility functions.
"""

import pytest
from datetime import datetime
from tempfile import NamedTemporaryFile
from unittest.mock import Mock, patch
from uuid import uuid4

from src.services.admin_functions import (
    init_all_db,
    reset_all_study_data,
    validate_database_integrity,
    get_database_stats,
    export_all_study_data,
    cleanup_orphaned_data,
    delete_participant_data,
)
from src.logic.admin_logic import InitializationResult, ResetResult


class TestAdminFunctions:
    """Test cases for admin convenience functions."""

    def test_init_all_db_success(self):
        """Test successful database initialization."""
        # Setup
        mock_result = InitializationResult(
            success=True,
            tables_created=['pseudonyms', 'study_consent_records'],
            errors=[],
            timestamp=datetime.utcnow()
        )
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.initialize_database_schema.return_value = mock_result
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = init_all_db()

            # Verify
            assert isinstance(result, InitializationResult)
            assert result.success is True
            assert len(result.tables_created) == 2
            assert 'pseudonyms' in result.tables_created
            assert len(result.errors) == 0

    def test_init_all_db_failure(self):
        """Test database initialization failure."""
        # Setup
        mock_result = InitializationResult(
            success=False,
            tables_created=[],
            errors=['Database connection failed'],
            timestamp=datetime.utcnow()
        )
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.initialize_database_schema.return_value = mock_result
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = init_all_db()

            # Verify
            assert result.success is False
            assert len(result.errors) == 1
            assert 'Database connection failed' in result.errors

    def test_init_all_db_exception(self):
        """Test database initialization with exception."""
        # Setup
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic_class.side_effect = Exception("Unexpected error")

            # Execute
            result = init_all_db()

            # Verify
            assert result.success is False
            assert len(result.errors) == 1
            assert 'Unexpected error' in result.errors[0]

    def test_reset_all_study_data_success(self):
        """Test successful database reset."""
        # Setup
        mock_result = ResetResult(
            success=True,
            tables_dropped=['pseudonyms', 'study_consent_records'],
            tables_recreated=['pseudonyms', 'study_consent_records'],
            errors=[],
            timestamp=datetime.utcnow()
        )
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.reset_all_study_data.return_value = mock_result
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = reset_all_study_data()

            # Verify
            assert isinstance(result, ResetResult)
            assert result.success is True
            assert len(result.tables_dropped) == 2
            assert len(result.tables_recreated) == 2
            assert len(result.errors) == 0

    def test_reset_all_study_data_failure(self):
        """Test database reset failure."""
        # Setup
        mock_result = ResetResult(
            success=False,
            tables_dropped=[],
            tables_recreated=[],
            errors=['Reset operation failed'],
            timestamp=datetime.utcnow()
        )
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.reset_all_study_data.return_value = mock_result
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = reset_all_study_data()

            # Verify
            assert result.success is False
            assert len(result.errors) == 1
            assert 'Reset operation failed' in result.errors

    def test_validate_database_integrity_success(self):
        """Test successful database integrity validation."""
        # Setup
        from src.logic.admin_logic import ValidationResult
        
        mock_result = ValidationResult(
            success=True,
            constraint_violations=[],
            missing_tables=[],
            errors=[],
            timestamp=datetime.utcnow()
        )
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.validate_database_integrity.return_value = mock_result
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = validate_database_integrity()

            # Verify
            assert result["success"] is True
            assert len(result["constraint_violations"]) == 0
            assert len(result["missing_tables"]) == 0
            assert len(result["errors"]) == 0
            assert "timestamp" in result

    def test_validate_database_integrity_with_violations(self):
        """Test database integrity validation with violations."""
        # Setup
        from src.logic.admin_logic import ValidationResult
        
        mock_result = ValidationResult(
            success=False,
            constraint_violations=['Found 5 orphaned consent records'],
            missing_tables=['study_pald_data'],
            errors=[],
            timestamp=datetime.utcnow()
        )
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.validate_database_integrity.return_value = mock_result
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = validate_database_integrity()

            # Verify
            assert result["success"] is False
            assert len(result["constraint_violations"]) == 1
            assert len(result["missing_tables"]) == 1
            assert 'orphaned consent records' in result["constraint_violations"][0]
            assert 'study_pald_data' in result["missing_tables"]

    def test_validate_database_integrity_exception(self):
        """Test database integrity validation with exception."""
        # Setup
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic_class.side_effect = Exception("Validation error")

            # Execute
            result = validate_database_integrity()

            # Verify
            assert result["success"] is False
            assert len(result["errors"]) == 1
            assert 'Validation error' in result["errors"][0]

    def test_get_database_stats_success(self):
        """Test successful database statistics retrieval."""
        # Setup
        mock_stats = {
            "pseudonyms": 10,
            "consent_records": 25,
            "survey_responses": 8,
            "active_pseudonyms": 9,
            "total_study_records": 50
        }
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.get_database_statistics.return_value = mock_stats
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            stats = get_database_stats()

            # Verify
            assert "pseudonyms" in stats
            assert "consent_records" in stats
            assert "active_pseudonyms" in stats
            assert stats["pseudonyms"] == 10
            assert stats["total_study_records"] == 50

    def test_get_database_stats_exception(self):
        """Test database statistics retrieval with exception."""
        # Setup
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic_class.side_effect = Exception("Stats error")

            # Execute
            stats = get_database_stats()

            # Verify
            assert "error" in stats
            assert 'Stats error' in stats["error"]

    def test_export_all_study_data_success(self):
        """Test successful study data export."""
        # Setup
        mock_export_result = {
            "success": True,
            "file_path": "/tmp/export.json",
            "records_exported": {
                "pseudonyms": 5,
                "consent_records": 15,
                "survey_responses": 3
            },
            "errors": [],
            "timestamp": "2024-01-01T00:00:00"
        }
        
        with patch('src.services.admin_functions.get_session') as mock_get_session, \
             patch('src.services.admin_functions.AdminService') as mock_admin_service_class:
            
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            mock_admin_service = Mock()
            mock_admin_service.export_study_data_to_file.return_value = mock_export_result
            mock_admin_service_class.return_value = mock_admin_service

            # Execute
            result = export_all_study_data("/tmp/test_export.json")

            # Verify
            assert result["success"] is True
            assert result["file_path"] == "/tmp/export.json"
            assert result["records_exported"]["pseudonyms"] == 5
            assert len(result["errors"]) == 0

    def test_export_all_study_data_failure(self):
        """Test study data export failure."""
        # Setup
        with patch('src.services.admin_functions.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Export error")

            # Execute
            result = export_all_study_data("/tmp/test_export.json")

            # Verify
            assert result["success"] is False
            assert len(result["errors"]) == 1
            assert 'Export error' in result["errors"][0]

    def test_cleanup_orphaned_data_success(self):
        """Test successful orphaned data cleanup."""
        # Setup
        mock_cleanup_counts = {
            "consent_records": 5,
            "survey_responses": 2,
            "chat_messages": 0,
            "pald_data": 1
        }
        
        with patch('src.services.admin_functions.get_session') as mock_get_session, \
             patch('src.services.admin_functions.AdminService') as mock_admin_service_class:
            
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            mock_admin_service = Mock()
            mock_admin_service.cleanup_orphaned_records.return_value = mock_cleanup_counts
            mock_admin_service_class.return_value = mock_admin_service

            # Execute
            result = cleanup_orphaned_data()

            # Verify
            assert result["consent_records"] == 5
            assert result["survey_responses"] == 2
            assert result["chat_messages"] == 0

    def test_cleanup_orphaned_data_failure(self):
        """Test orphaned data cleanup failure."""
        # Setup
        with patch('src.services.admin_functions.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Cleanup error")

            # Execute
            result = cleanup_orphaned_data()

            # Verify
            assert "error" in result
            assert 'Cleanup error' in result["error"]

    def test_delete_participant_data_success(self):
        """Test successful participant data deletion."""
        # Setup
        pseudonym_id = str(uuid4())
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.delete_participant_data.return_value = True
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = delete_participant_data(pseudonym_id)

            # Verify
            assert result is True

    def test_delete_participant_data_failure(self):
        """Test participant data deletion failure."""
        # Setup
        pseudonym_id = str(uuid4())
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic = Mock()
            mock_admin_logic.delete_participant_data.return_value = False
            mock_admin_logic_class.return_value = mock_admin_logic

            # Execute
            result = delete_participant_data(pseudonym_id)

            # Verify
            assert result is False

    def test_delete_participant_data_invalid_uuid(self):
        """Test participant data deletion with invalid UUID."""
        # Execute
        result = delete_participant_data("invalid-uuid")

        # Verify
        assert result is False

    def test_delete_participant_data_exception(self):
        """Test participant data deletion with exception."""
        # Setup
        pseudonym_id = str(uuid4())
        
        with patch('src.services.admin_functions.AdminLogic') as mock_admin_logic_class:
            mock_admin_logic_class.side_effect = Exception("Deletion error")

            # Execute
            result = delete_participant_data(pseudonym_id)

            # Verify
            assert result is False