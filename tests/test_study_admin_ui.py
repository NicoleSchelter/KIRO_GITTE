"""
Unit tests for StudyAdminUI class.
Tests admin interface components for database management and data export functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from src.ui.study_admin_ui import StudyAdminUI, render_study_admin_page


def create_mock_columns(count=2):
    """Helper function to create properly mocked Streamlit columns."""
    columns = []
    for _ in range(count):
        col = Mock()
        col.__enter__ = Mock(return_value=col)
        col.__exit__ = Mock(return_value=None)
        columns.append(col)
    return columns


class TestStudyAdminUI:
    """Test cases for StudyAdminUI class."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch('src.logic.admin_logic.AdminLogic') as mock_admin_logic:
            self.mock_admin_logic = mock_admin_logic.return_value
            self.admin_ui = StudyAdminUI()

    @patch('streamlit.title')
    @patch('streamlit.markdown')
    def test_render_admin_dashboard_structure(self, mock_markdown, mock_title):
        """Test that admin dashboard renders with correct structure."""
        # Setup
        with patch.object(self.admin_ui, '_render_database_status') as mock_status, \
             patch.object(self.admin_ui, '_render_database_management') as mock_management, \
             patch.object(self.admin_ui, '_render_data_export') as mock_export, \
             patch.object(self.admin_ui, '_render_data_privacy') as mock_privacy:

            # Execute
            self.admin_ui.render_admin_dashboard()

            # Verify
            mock_title.assert_called_once_with("🔧 Study Administration Dashboard")
            mock_markdown.assert_called_with("---")
            mock_status.assert_called_once()
            mock_management.assert_called_once()
            mock_export.assert_called_once()
            mock_privacy.assert_called_once()

    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.button')
    @patch('streamlit.metric')
    @patch('streamlit.markdown')
    def test_render_database_status_success(self, mock_markdown, mock_metric, mock_button, mock_columns, mock_subheader):
        """Test database status rendering with successful statistics."""
        # Setup
        mock_columns.return_value = create_mock_columns(4)  # Need 4 columns for the UI
        mock_button.return_value = False
        
        mock_stats = {
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
        self.mock_admin_logic.get_database_statistics.return_value = mock_stats

        # Execute
        self.admin_ui._render_database_status()

        # Verify
        mock_subheader.assert_called_with("📊 Database Status")
        self.mock_admin_logic.get_database_statistics.assert_called_once()
        
        # Verify that the method completed without errors (main goal)
        assert mock_columns.called
        assert mock_button.called

    @patch('streamlit.subheader')
    @patch('streamlit.error')
    def test_render_database_status_error(self, mock_error, mock_subheader):
        """Test database status rendering with error."""
        # Setup
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.button') as mock_button:
            
            mock_columns.return_value = create_mock_columns(2)
            mock_button.return_value = False
            
            mock_stats = {"error": "Database connection failed"}
            self.mock_admin_logic.get_database_statistics.return_value = mock_stats

            # Execute
            self.admin_ui._render_database_status()

            # Verify
            mock_error.assert_called_with("Failed to load statistics: Database connection failed")

    @patch('streamlit.subheader')
    @patch('streamlit.warning')
    @patch('streamlit.columns')
    @patch('streamlit.button')
    @patch('streamlit.spinner')
    @patch('streamlit.success')
    def test_render_database_management_init_success(self, mock_success, mock_spinner, mock_button, 
                                                   mock_columns, mock_warning, mock_subheader):
        """Test database management with successful initialization."""
        # Setup
        mock_columns.return_value = create_mock_columns(2)
        mock_button.side_effect = [True, False]  # Init button clicked, reset not clicked
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        from src.logic.admin_logic import InitializationResult
        mock_result = InitializationResult(
            success=True,
            tables_created=["pseudonyms", "consent_records"],
            errors=[],
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.initialize_database_schema.return_value = mock_result

        # Execute
        self.admin_ui._render_database_management()

        # Verify
        mock_subheader.assert_called_with("🗄️ Database Management")
        mock_warning.assert_called_with("⚠️ **Warning**: Database operations are irreversible. Use with caution!")
        self.mock_admin_logic.initialize_database_schema.assert_called_once()
        mock_success.assert_called_with("✅ Database initialized successfully")

    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.button')
    @patch('streamlit.checkbox')
    @patch('streamlit.text_input')
    @patch('streamlit.spinner')
    @patch('streamlit.success')
    @patch('streamlit.rerun')
    def test_render_database_management_reset_success(self, mock_rerun, mock_success, mock_spinner, 
                                                    mock_text_input, mock_checkbox, mock_button, 
                                                    mock_columns, mock_subheader):
        """Test database management with successful reset."""
        # Setup
        mock_columns.return_value = create_mock_columns(2)
        mock_button.side_effect = [False, True]  # Init not clicked, reset clicked
        mock_checkbox.return_value = True
        mock_text_input.return_value = "DELETE ALL DATA"
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        from src.logic.admin_logic import ResetResult
        mock_result = ResetResult(
            success=True,
            tables_dropped=["pseudonyms", "consent_records"],
            tables_recreated=["pseudonyms", "consent_records"],
            errors=[],
            timestamp=datetime.utcnow()
        )
        self.mock_admin_logic.reset_all_study_data.return_value = mock_result

        # Execute
        self.admin_ui._render_database_management()

        # Verify
        self.mock_admin_logic.reset_all_study_data.assert_called_once()
        mock_success.assert_called_with("✅ Database reset completed")
        mock_rerun.assert_called_once()

    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.radio')
    @patch('streamlit.button')
    @patch('streamlit.spinner')
    @patch('streamlit.success')
    def test_render_data_export_preview_success(self, mock_success, mock_spinner, mock_button, 
                                              mock_radio, mock_columns, mock_subheader):
        """Test data export preview functionality."""
        # Setup
        mock_columns.return_value = create_mock_columns(2)
        mock_radio.return_value = "All Data"
        mock_button.side_effect = [True, False]  # Preview clicked, download not clicked
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        from src.logic.admin_logic import ExportResult
        mock_result = ExportResult(
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
        self.mock_admin_logic.export_study_data.return_value = mock_result

        # Execute
        self.admin_ui._render_data_export()

        # Verify
        mock_subheader.assert_called_with("📤 Data Export")
        self.mock_admin_logic.export_study_data.assert_called_once_with(None)
        mock_success.assert_called_with("✅ Export preview generated")

    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.radio')
    @patch('streamlit.text_input')
    @patch('streamlit.button')
    @patch('streamlit.error')
    def test_render_data_export_invalid_uuid(self, mock_error, mock_button, mock_text_input, 
                                           mock_radio, mock_columns, mock_subheader):
        """Test data export with invalid UUID input."""
        # Setup
        mock_columns.return_value = create_mock_columns(2)
        mock_radio.return_value = "Specific Pseudonym"
        mock_text_input.return_value = "invalid-uuid"
        mock_button.return_value = True

        # Execute
        self.admin_ui._render_data_export()

        # Verify
        mock_error.assert_called_with("Invalid UUID format")

    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.text_input')
    @patch('streamlit.checkbox')
    @patch('streamlit.button')
    @patch('streamlit.spinner')
    @patch('streamlit.success')
    def test_render_data_privacy_delete_success(self, mock_success, mock_spinner, mock_button, 
                                              mock_checkbox, mock_text_input, mock_columns, 
                                              mock_subheader):
        """Test participant data deletion functionality."""
        # Setup
        pseudonym_id = uuid4()
        mock_columns.return_value = create_mock_columns(2)
        mock_text_input.return_value = str(pseudonym_id)
        mock_checkbox.return_value = True
        mock_button.side_effect = [True, False, False]  # Delete clicked, cleanup and maintenance not clicked
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        self.mock_admin_logic.delete_participant_data.return_value = True

        # Execute
        self.admin_ui._render_data_privacy()

        # Verify
        mock_subheader.assert_called_with("🔒 Data Privacy & Participant Rights")
        self.mock_admin_logic.delete_participant_data.assert_called_once_with(pseudonym_id)
        mock_success.assert_called_with("✅ Participant data deleted successfully")

    @patch('streamlit.subheader')
    @patch('streamlit.columns')
    @patch('streamlit.button')
    @patch('streamlit.spinner')
    @patch('streamlit.success')
    @patch('src.ui.study_admin_ui.get_session')
    def test_render_data_privacy_cleanup_success(self, mock_get_session, mock_success, mock_spinner, 
                                               mock_button, mock_columns, mock_subheader):
        """Test orphaned data cleanup functionality."""
        # Setup
        mock_columns.return_value = create_mock_columns(2)
        mock_button.side_effect = [False, True, False]  # Delete not clicked, cleanup clicked, maintenance not clicked
        mock_spinner.return_value.__enter__ = Mock()
        mock_spinner.return_value.__exit__ = Mock()
        
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        from src.services.admin_service import AdminService
        with patch('src.ui.study_admin_ui.AdminService') as mock_admin_service_class:
            mock_admin_service = mock_admin_service_class.return_value
            mock_admin_service.cleanup_orphaned_records.return_value = {
                "consent_records": 5,
                "survey_responses": 2,
                "chat_messages": 0
            }

            # Execute
            self.admin_ui._render_data_privacy()

            # Verify
            mock_admin_service_class.assert_called_once_with(mock_session)
            mock_admin_service.cleanup_orphaned_records.assert_called_once()
            mock_success.assert_called_with("✅ Cleaned up 7 orphaned records")

    @patch('streamlit.sidebar')
    @patch('streamlit.metric')
    @patch('streamlit.success')
    def test_render_admin_sidebar_success(self, mock_success, mock_metric, mock_sidebar):
        """Test admin sidebar rendering with successful statistics."""
        # Setup
        mock_sidebar_context = Mock()
        mock_sidebar.return_value.__enter__.return_value = mock_sidebar_context
        mock_sidebar.return_value.__exit__.return_value = None
        
        mock_stats = {
            "total_study_records": 50,
            "active_pseudonyms": 10
        }
        self.mock_admin_logic.get_database_statistics.return_value = mock_stats

        # Execute
        self.admin_ui.render_admin_sidebar()

        # Verify
        self.mock_admin_logic.get_database_statistics.assert_called_once()
        mock_metric.assert_called_with("Total Study Records", 50)
        mock_success.assert_called_with("✅ 10 active participants")

    @patch('streamlit.sidebar')
    @patch('streamlit.error')
    def test_render_admin_sidebar_error(self, mock_error, mock_sidebar):
        """Test admin sidebar rendering with database error."""
        # Setup
        mock_sidebar_context = Mock()
        mock_sidebar.return_value.__enter__.return_value = mock_sidebar_context
        mock_sidebar.return_value.__exit__.return_value = None
        
        mock_stats = {"error": "Connection failed"}
        self.mock_admin_logic.get_database_statistics.return_value = mock_stats

        # Execute
        self.admin_ui.render_admin_sidebar()

        # Verify
        mock_error.assert_called_with("Database connection issue")

    @patch('src.ui.study_admin_ui.StudyAdminUI')
    def test_render_study_admin_page(self, mock_study_admin_ui_class):
        """Test main study admin page rendering function."""
        # Setup
        mock_admin_ui = mock_study_admin_ui_class.return_value

        # Execute
        render_study_admin_page()

        # Verify
        mock_study_admin_ui_class.assert_called_once()
        mock_admin_ui.render_admin_sidebar.assert_called_once()
        mock_admin_ui.render_admin_dashboard.assert_called_once()


@pytest.mark.integration
class TestStudyAdminUIIntegration:
    """Integration test cases for StudyAdminUI functionality."""

    def setup_method(self):
        """Set up test fixtures for integration tests."""
        # These tests would require actual Streamlit session state
        # and database connections, so we'll mock the critical components
        pass

    @patch('src.ui.study_admin_ui.get_session')
    @patch('streamlit.download_button')
    @patch('streamlit.success')
    def test_download_export_integration(self, mock_success, mock_download_button, mock_get_session):
        """Test complete data export download integration."""
        # Setup
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        
        from src.services.admin_service import AdminService
        with patch('src.ui.study_admin_ui.AdminService') as mock_admin_service_class, \
             patch('tempfile.NamedTemporaryFile') as mock_temp_file, \
             patch('builtins.open', create=True) as mock_open, \
             patch('pathlib.Path.unlink') as mock_unlink:
            
            # Setup mocks
            mock_temp_file.return_value.__enter__.return_value.name = "/tmp/test_export.json"
            mock_temp_file.return_value.__exit__.return_value = None
            
            mock_admin_service = mock_admin_service_class.return_value
            mock_admin_service.export_study_data_to_file.return_value = {
                "success": True,
                "records_exported": {"pseudonyms": 5, "consent_records": 10},
                "errors": []
            }
            
            mock_open.return_value.__enter__.return_value.read.return_value = '{"test": "data"}'
            mock_open.return_value.__exit__.return_value = None
            
            # Create admin UI and simulate button click
            with patch('src.logic.admin_logic.AdminLogic'):
                
                admin_ui = StudyAdminUI()
                
                # Mock Streamlit components for the download flow
                with patch('streamlit.button', return_value=True), \
                     patch('streamlit.spinner') as mock_spinner, \
                     patch('streamlit.columns', return_value=create_mock_columns(2)), \
                     patch('streamlit.radio', return_value="All Data"), \
                     patch('streamlit.selectbox', return_value="JSON"), \
                     patch('streamlit.subheader'), \
                     patch('streamlit.markdown'), \
                     patch('datetime.datetime') as mock_datetime:
                    
                    mock_spinner.return_value.__enter__ = Mock()
                    mock_spinner.return_value.__exit__ = Mock()
                    mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
                    
                    # Execute the download export functionality
                    admin_ui._render_data_export()
                    
                    # Verify the export process was called
                    mock_admin_service_class.assert_called_once_with(mock_session)
                    mock_admin_service.export_study_data_to_file.assert_called_once()
                    mock_download_button.assert_called_once()
                    mock_success.assert_called_with("✅ Export file ready for download")

    def test_database_validation_integration_flow(self):
        """Test complete database validation integration flow."""
        # This would test the full validation flow including:
        # 1. Database connection
        # 2. Table existence checks
        # 3. Foreign key constraint validation
        # 4. UI feedback display
        
        # For now, we'll test the logic flow with mocked components
        with patch('src.logic.admin_logic.AdminLogic') as mock_admin_logic_class:
            
            mock_admin_logic = mock_admin_logic_class.return_value
            
            from src.logic.admin_logic import ValidationResult
            mock_validation_result = ValidationResult(
                success=True,
                constraint_violations=[],
                missing_tables=[],
                errors=[],
                timestamp=datetime.utcnow()
            )
            mock_admin_logic.validate_database_integrity.return_value = mock_validation_result
            
            admin_ui = StudyAdminUI()
            
            # Mock Streamlit components
            with patch('streamlit.button', return_value=True), \
                 patch('streamlit.spinner') as mock_spinner, \
                 patch('streamlit.success') as mock_success, \
                 patch('streamlit.columns', return_value=create_mock_columns(2)), \
                 patch('streamlit.subheader'):
                
                mock_spinner.return_value.__enter__ = Mock()
                mock_spinner.return_value.__exit__ = Mock()
                
                # Execute validation
                admin_ui._render_database_status()
                
                # Verify validation was called and success was displayed
                mock_admin_logic.validate_database_integrity.assert_called_once()
                mock_success.assert_called_with("✅ Database integrity validation passed")