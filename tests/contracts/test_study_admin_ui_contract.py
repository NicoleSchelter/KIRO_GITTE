"""
Contract tests for StudyAdminUI components.
Tests the interface contracts between UI components and admin logic/services.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from datetime import datetime

from src.ui.study_admin_ui import StudyAdminUI
from src.logic.admin_logic import AdminLogic, InitializationResult, ResetResult, ValidationResult, ExportResult
from src.services.admin_service import AdminService


def create_mock_columns(count=2):
    """Helper function to create properly mocked Streamlit columns."""
    columns = []
    for _ in range(count):
        col = Mock()
        col.__enter__ = Mock(return_value=col)
        col.__exit__ = Mock(return_value=None)
        columns.append(col)
    return columns


class TestStudyAdminUIContracts:
    """Contract test cases for StudyAdminUI interface compliance."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()
        self.mock_admin_logic = Mock(spec=AdminLogic)
        
        with patch('src.ui.study_admin_ui.DatabaseManager', return_value=self.mock_db_manager), \
             patch('src.ui.study_admin_ui.AdminLogic', return_value=self.mock_admin_logic):
            self.admin_ui = StudyAdminUI()

    def test_admin_logic_initialization_contract(self):
        """Test that AdminLogic is properly initialized with DatabaseManager."""
        # Verify the contract: AdminLogic should be initialized with DatabaseManager
        with patch('src.ui.study_admin_ui.DatabaseManager') as mock_db_manager_class, \
             patch('src.ui.study_admin_ui.AdminLogic') as mock_admin_logic_class:
            
            mock_db_manager_instance = mock_db_manager_class.return_value
            
            # Create new instance to test initialization
            admin_ui = StudyAdminUI()
            
            # Verify contract compliance
            mock_db_manager_class.assert_called_once()
            mock_admin_logic_class.assert_called_once_with(mock_db_manager_instance)

    def test_database_statistics_contract(self):
        """Test database statistics method contract compliance."""
        # Setup expected return format
        expected_stats = {
            "pseudonyms": 10,
            "consent_records": 15,
            "survey_responses": 8,
            "chat_messages": 25,
            "pald_data": 12,
            "generated_images": 5,
            "feedback_records": 3,
            "interaction_logs": 30,
            "active_pseudonyms": 8,
            "total_study_records": 98
        }
        self.mock_admin_logic.get_database_statistics.return_value = expected_stats

        # Execute method that uses the contract
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=create_mock_columns(2)), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.metric'), \
             patch('streamlit.markdown'):
            
            self.admin_ui._render_database_status()

        # Verify contract compliance
        self.mock_admin_logic.get_database_statistics.assert_called_once()
        
        # Verify the method was called without parameters (contract requirement)
        call_args = self.mock_admin_logic.get_database_statistics.call_args
        assert call_args == ((), {})  # No positional or keyword arguments

    def test_database_initialization_contract(self):
        """Test database initialization method contract compliance."""
        # Setup expected return type
        expected_result = InitializationResult(
            success=True,
            tables_created=["pseudonyms", "consent_records"],
            errors=[],
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.initialize_database_schema.return_value = expected_result

        # Execute method that uses the contract
        with patch('streamlit.subheader'), \
             patch('streamlit.warning'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', side_effect=[True, False]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success'), \
             patch('streamlit.info'):
            
            self.admin_ui._render_database_management()

        # Verify contract compliance
        self.mock_admin_logic.initialize_database_schema.assert_called_once()
        
        # Verify return type contract
        result = self.mock_admin_logic.initialize_database_schema.return_value
        assert hasattr(result, 'success')
        assert hasattr(result, 'tables_created')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'timestamp')
        assert isinstance(result.success, bool)
        assert isinstance(result.tables_created, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.timestamp, datetime)

    def test_database_reset_contract(self):
        """Test database reset method contract compliance."""
        # Setup expected return type
        expected_result = ResetResult(
            success=True,
            tables_dropped=["pseudonyms", "consent_records"],
            tables_recreated=["pseudonyms", "consent_records"],
            errors=[],
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.reset_all_study_data.return_value = expected_result

        # Execute method that uses the contract
        with patch('streamlit.subheader'), \
             patch('streamlit.warning'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', side_effect=[False, True]), \
             patch('streamlit.checkbox', return_value=True), \
             patch('streamlit.text_input', return_value="DELETE ALL DATA"), \
             patch('streamlit.spinner'), \
             patch('streamlit.success'), \
             patch('streamlit.info'), \
             patch('streamlit.rerun'):
            
            self.admin_ui._render_database_management()

        # Verify contract compliance
        self.mock_admin_logic.reset_all_study_data.assert_called_once()
        
        # Verify return type contract
        result = self.mock_admin_logic.reset_all_study_data.return_value
        assert hasattr(result, 'success')
        assert hasattr(result, 'tables_dropped')
        assert hasattr(result, 'tables_recreated')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'timestamp')
        assert isinstance(result.success, bool)
        assert isinstance(result.tables_dropped, list)
        assert isinstance(result.tables_recreated, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.timestamp, datetime)

    def test_database_validation_contract(self):
        """Test database validation method contract compliance."""
        # Setup expected return type
        expected_result = ValidationResult(
            success=True,
            constraint_violations=[],
            missing_tables=[],
            errors=[],
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.validate_database_integrity.return_value = expected_result

        # Execute method that uses the contract
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', side_effect=[False, True]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success'):
            
            self.admin_ui._render_database_status()

        # Verify contract compliance
        self.mock_admin_logic.validate_database_integrity.assert_called_once()
        
        # Verify return type contract
        result = self.mock_admin_logic.validate_database_integrity.return_value
        assert hasattr(result, 'success')
        assert hasattr(result, 'constraint_violations')
        assert hasattr(result, 'missing_tables')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'timestamp')
        assert isinstance(result.success, bool)
        assert isinstance(result.constraint_violations, list)
        assert isinstance(result.missing_tables, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.timestamp, datetime)

    def test_data_export_contract(self):
        """Test data export method contract compliance."""
        # Setup expected return type
        expected_result = ExportResult(
            success=True,
            exported_records={
                "pseudonyms": 5,
                "consent_records": 10,
                "survey_responses": 3
            },
            file_path=None,
            errors=[],
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.export_study_data.return_value = expected_result

        # Execute method that uses the contract
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.radio', return_value="All Data"), \
             patch('streamlit.selectbox', return_value="JSON"), \
             patch('streamlit.button', side_effect=[True, False]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success'), \
             patch('streamlit.write'), \
             patch('streamlit.info'):
            
            self.admin_ui._render_data_export()

        # Verify contract compliance
        self.mock_admin_logic.export_study_data.assert_called_once_with(None)
        
        # Verify return type contract
        result = self.mock_admin_logic.export_study_data.return_value
        assert hasattr(result, 'success')
        assert hasattr(result, 'exported_records')
        assert hasattr(result, 'file_path')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'timestamp')
        assert isinstance(result.success, bool)
        assert isinstance(result.exported_records, dict)
        assert isinstance(result.errors, list)
        assert isinstance(result.timestamp, datetime)

    def test_data_export_with_pseudonym_contract(self):
        """Test data export with specific pseudonym contract compliance."""
        # Setup
        pseudonym_id = uuid4()
        expected_result = ExportResult(
            success=True,
            exported_records={"pseudonyms": 1},
            file_path=None,
            errors=[],
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.export_study_data.return_value = expected_result

        # Execute method that uses the contract
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.radio', return_value="Specific Pseudonym"), \
             patch('streamlit.text_input', return_value=str(pseudonym_id)), \
             patch('streamlit.selectbox', return_value="JSON"), \
             patch('streamlit.button', side_effect=[True, False]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success'):
            
            self.admin_ui._render_data_export()

        # Verify contract compliance - method should be called with UUID
        self.mock_admin_logic.export_study_data.assert_called_once_with(pseudonym_id)

    def test_participant_data_deletion_contract(self):
        """Test participant data deletion method contract compliance."""
        # Setup
        pseudonym_id = uuid4()
        self.mock_admin_logic.delete_participant_data.return_value = True

        # Execute method that uses the contract
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.text_input', return_value=str(pseudonym_id)), \
             patch('streamlit.checkbox', return_value=True), \
             patch('streamlit.button', side_effect=[True, False, False]), \
             patch('streamlit.spinner'), \
             patch('streamlit.success'):
            
            self.admin_ui._render_data_privacy()

        # Verify contract compliance
        self.mock_admin_logic.delete_participant_data.assert_called_once_with(pseudonym_id)
        
        # Verify return type contract (should return boolean)
        result = self.mock_admin_logic.delete_participant_data.return_value
        assert isinstance(result, bool)

    def test_admin_service_session_contract(self):
        """Test AdminService session dependency contract compliance."""
        # This tests that AdminService is properly instantiated with a session
        mock_session = Mock()
        
        with patch('src.ui.study_admin_ui.get_session') as mock_get_session, \
             patch('src.ui.study_admin_ui.AdminService') as mock_admin_service_class:
            
            mock_get_session.return_value.__enter__.return_value = mock_session
            mock_get_session.return_value.__exit__.return_value = None
            
            mock_admin_service = mock_admin_service_class.return_value
            mock_admin_service.cleanup_orphaned_records.return_value = {"consent_records": 0}

            # Execute method that uses AdminService
            with patch('streamlit.subheader'), \
                 patch('streamlit.columns', return_value=[Mock(), Mock()]), \
                 patch('streamlit.button', side_effect=[False, True, False]), \
                 patch('streamlit.spinner'), \
                 patch('streamlit.info'):
                
                self.admin_ui._render_data_privacy()

            # Verify contract compliance - AdminService should be instantiated with session
            mock_admin_service_class.assert_called_once_with(mock_session)

    def test_streamlit_component_contracts(self):
        """Test that UI methods properly use Streamlit component contracts."""
        # This test verifies that the UI components use Streamlit methods correctly
        
        # Test that columns are used properly
        with patch('streamlit.columns') as mock_columns:
            mock_col1, mock_col2 = Mock(), Mock()
            mock_columns.return_value = [mock_col1, mock_col2]
            
            with patch('streamlit.subheader'), \
                 patch('streamlit.button', return_value=False), \
                 patch('streamlit.metric'):
                
                self.admin_ui._render_database_status()
                
                # Verify columns contract - should be called with 2 or 4 columns
                columns_calls = mock_columns.call_args_list
                assert len(columns_calls) > 0
                for call in columns_calls:
                    args = call[0]
                    assert len(args) == 1  # Should have one argument (number of columns)
                    assert args[0] in [2, 3, 4]  # Should be 2, 3, or 4 columns

    def test_error_handling_contracts(self):
        """Test error handling contract compliance."""
        # Test that UI properly handles and displays errors from admin logic
        
        # Test database statistics error handling
        self.mock_admin_logic.get_database_statistics.return_value = {
            "error": "Database connection failed"
        }
        
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', return_value=False), \
             patch('streamlit.error') as mock_error:
            
            self.admin_ui._render_database_status()
            
            # Verify error contract - should display error message
            mock_error.assert_called_with("Failed to load statistics: Database connection failed")

    def test_uuid_validation_contract(self):
        """Test UUID validation contract compliance."""
        # Test that invalid UUIDs are properly handled
        
        with patch('streamlit.subheader'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.radio', return_value="Specific Pseudonym"), \
             patch('streamlit.text_input', return_value="invalid-uuid-format"), \
             patch('streamlit.button', return_value=True), \
             patch('streamlit.error') as mock_error:
            
            self.admin_ui._render_data_export()
            
            # Verify UUID validation contract - should display error for invalid UUID
            mock_error.assert_called_with("Invalid UUID format")
            
            # Verify that admin logic is not called with invalid UUID
            self.mock_admin_logic.export_study_data.assert_not_called()

    def test_safety_confirmation_contract(self):
        """Test safety confirmation contract for destructive operations."""
        # Test that destructive operations require proper confirmation
        
        # Test reset operation safety contract
        with patch('streamlit.subheader'), \
             patch('streamlit.warning'), \
             patch('streamlit.columns', return_value=[Mock(), Mock()]), \
             patch('streamlit.button', side_effect=[False, True]), \
             patch('streamlit.checkbox', return_value=False), \
             patch('streamlit.text_input', return_value=""):
            
            self.admin_ui._render_database_management()
            
            # Verify safety contract - reset should not be called without confirmation
            self.mock_admin_logic.reset_all_study_data.assert_not_called()

    def test_session_management_contract(self):
        """Test database session management contract compliance."""
        # Test that database sessions are properly managed using context managers
        
        with patch('src.ui.study_admin_ui.get_session') as mock_get_session:
            mock_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__.return_value = mock_session
            mock_context_manager.__exit__.return_value = None
            mock_get_session.return_value = mock_context_manager
            
            with patch('src.ui.study_admin_ui.AdminService') as mock_admin_service_class, \
                 patch('streamlit.subheader'), \
                 patch('streamlit.columns', return_value=[Mock(), Mock()]), \
                 patch('streamlit.button', side_effect=[False, True, False]), \
                 patch('streamlit.spinner'), \
                 patch('streamlit.info'):
                
                mock_admin_service = mock_admin_service_class.return_value
                mock_admin_service.cleanup_orphaned_records.return_value = {"consent_records": 0}
                
                self.admin_ui._render_data_privacy()
                
                # Verify session management contract
                mock_get_session.assert_called_once()
                mock_context_manager.__enter__.assert_called_once()
                mock_context_manager.__exit__.assert_called_once()
                mock_admin_service_class.assert_called_once_with(mock_session)