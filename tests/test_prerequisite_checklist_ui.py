"""
Unit tests for prerequisite checklist UI components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

import streamlit as st

from src.ui.prerequisite_checklist_ui import (
    PrerequisiteChecklistUI,
    render_prerequisite_sidebar,
    render_prerequisite_page,
    render_accessible_prerequisite_checklist
)
from src.logic.prerequisite_validation import PrerequisiteValidationLogic
from src.services.prerequisite_checker import (
    PrerequisiteCheckSuite,
    PrerequisiteResult,
    PrerequisiteStatus,
    PrerequisiteType
)


class TestPrerequisiteChecklistUI:
    """Test cases for PrerequisiteChecklistUI."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_validation_logic = Mock(spec=PrerequisiteValidationLogic)
        self.mock_consent_service = Mock()
        self.user_id = uuid4()
        
        # Clear Streamlit session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
    
    def test_initialization(self):
        """Test UI component initialization."""
        ui = PrerequisiteChecklistUI(
            validation_logic=self.mock_validation_logic,
            consent_service=self.mock_consent_service
        )
        
        assert ui.validation_logic == self.mock_validation_logic
        assert ui.consent_service == self.mock_consent_service
    
    def test_initialization_without_dependencies(self):
        """Test UI component initialization without dependencies."""
        ui = PrerequisiteChecklistUI()
        
        assert ui.validation_logic is None
        assert ui.consent_service is None
    
    @patch('streamlit.subheader')
    @patch('streamlit.write')
    @patch('streamlit.columns')
    @patch('streamlit.button')
    @patch('streamlit.checkbox')
    def test_render_checklist_basic(self, mock_checkbox, mock_button, mock_columns, mock_write, mock_subheader):
        """Test basic checklist rendering."""
        # Mock Streamlit components with context manager support
        mock_col1, mock_col2, mock_col3 = MagicMock(), MagicMock(), MagicMock()
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=None)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=None)
        mock_col3.__enter__ = Mock(return_value=mock_col3)
        mock_col3.__exit__ = Mock(return_value=None)
        mock_columns.return_value = [mock_col1, mock_col2, mock_col3]
        mock_button.return_value = False
        mock_checkbox.return_value = False
        
        # Mock validation logic
        mock_result = PrerequisiteResult(
            name="Test Checker",
            status=PrerequisiteStatus.PASSED,
            message="Test passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        mock_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[mock_result],
            total_check_time=1.0,
            timestamp=datetime.now().isoformat()
        )
        
        self.mock_validation_logic.validate_for_operation.return_value = mock_suite
        
        ui = PrerequisiteChecklistUI(validation_logic=self.mock_validation_logic)
        
        with patch.object(ui, '_get_validation_logic', return_value=self.mock_validation_logic):
            with patch.object(ui, '_render_results', return_value={"status": "passed"}):
                result = ui.render_checklist("test_operation")
        
        assert result["status"] == "passed"
        mock_subheader.assert_called_once()
    
    @patch('streamlit.success')
    @patch('streamlit.warning')
    @patch('streamlit.error')
    def test_render_compact_status_ready(self, mock_error, mock_warning, mock_success):
        """Test compact status rendering when system is ready."""
        readiness = {
            "ready": True,
            "can_proceed_with_warnings": True,
            "required_failures": [],
            "recommended_failures": ["System Health"]
        }
        
        self.mock_validation_logic.check_operation_readiness.return_value = readiness
        
        ui = PrerequisiteChecklistUI(validation_logic=self.mock_validation_logic)
        
        with patch.object(ui, '_get_validation_logic', return_value=self.mock_validation_logic):
            result = ui.render_compact_status("test_operation")
        
        assert result == readiness
        mock_success.assert_called_once_with("✅ System Ready")
        mock_warning.assert_called_once()
    
    @patch('streamlit.error')
    @patch('streamlit.expander')
    def test_render_compact_status_not_ready(self, mock_expander, mock_error):
        """Test compact status rendering when system is not ready."""
        readiness = {
            "ready": False,
            "can_proceed_with_warnings": False,
            "required_failures": ["Database", "Ollama"],
            "recommended_failures": []
        }
        
        self.mock_validation_logic.check_operation_readiness.return_value = readiness
        
        # Mock expander context manager
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        ui = PrerequisiteChecklistUI(validation_logic=self.mock_validation_logic)
        
        with patch.object(ui, '_get_validation_logic', return_value=self.mock_validation_logic):
            result = ui.render_compact_status("test_operation")
        
        assert result == readiness
        mock_error.assert_called()
    
    @patch('streamlit.success')
    @patch('streamlit.metric')
    @patch('streamlit.columns')
    def test_render_overall_status_passed(self, mock_columns, mock_metric, mock_success):
        """Test rendering overall status when passed."""
        # Mock columns with context manager support
        mock_cols = []
        for i in range(4):
            col = MagicMock()
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            mock_cols.append(col)
        mock_columns.return_value = mock_cols
        
        mock_result = PrerequisiteResult(
            name="Test",
            status=PrerequisiteStatus.PASSED,
            message="Passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[mock_result],
            total_check_time=1.5,
            timestamp=datetime.now().isoformat()
        )
        
        ui = PrerequisiteChecklistUI()
        ui._render_overall_status(check_suite)
        
        mock_success.assert_called_once_with("✅ All Prerequisites Satisfied")
        assert mock_metric.call_count == 4  # Total, Passed, Failed, Check Time
    
    @patch('streamlit.warning')
    def test_render_overall_status_warning(self, mock_warning):
        """Test rendering overall status when warning."""
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.WARNING,
            required_passed=True,
            recommended_passed=False,
            results=[],
            total_check_time=1.0,
            timestamp=datetime.now().isoformat()
        )
        
        ui = PrerequisiteChecklistUI()
        
        # Mock columns with context manager support
        mock_cols = []
        for i in range(4):
            col = MagicMock()
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            mock_cols.append(col)
        
        with patch('streamlit.columns', return_value=mock_cols):
            with patch('streamlit.metric'):
                ui._render_overall_status(check_suite)
        
        mock_warning.assert_called_once_with("⚠️ Prerequisites Met with Warnings")
    
    @patch('streamlit.error')
    def test_render_overall_status_failed(self, mock_error):
        """Test rendering overall status when failed."""
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.FAILED,
            required_passed=False,
            recommended_passed=False,
            results=[],
            total_check_time=1.0,
            timestamp=datetime.now().isoformat()
        )
        
        ui = PrerequisiteChecklistUI()
        
        # Mock columns with context manager support
        mock_cols = []
        for i in range(4):
            col = MagicMock()
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            mock_cols.append(col)
        
        with patch('streamlit.columns', return_value=mock_cols):
            with patch('streamlit.metric'):
                ui._render_overall_status(check_suite)
        
        mock_error.assert_called_once_with("❌ Critical Prerequisites Failed")
    
    @patch('streamlit.write')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.divider')
    def test_render_prerequisite_item_passed(self, mock_divider, mock_columns, mock_button, mock_write):
        """Test rendering individual prerequisite item when passed."""
        # Mock columns with context manager support
        mock_cols = []
        for i in range(3):
            col = MagicMock()
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            mock_cols.append(col)
        mock_columns.return_value = mock_cols
        mock_button.return_value = False
        
        result = PrerequisiteResult(
            name="Test Checker",
            status=PrerequisiteStatus.PASSED,
            message="All good",
            details="Everything working",
            resolution_steps=["Step 1", "Step 2"],
            check_time=0.5,
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        ui = PrerequisiteChecklistUI()
        ui._render_prerequisite_item(result, is_required=True)
        
        # Verify write calls for name and message
        write_calls = [call.args[0] for call in mock_write.call_args_list]
        assert "**Test Checker**" in write_calls
        assert "All good" in write_calls
        
        mock_button.assert_called_once()
        mock_divider.assert_called_once()
    
    @patch('streamlit.write')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.expander')
    def test_render_prerequisite_item_expanded(self, mock_expander, mock_columns, mock_button, mock_write):
        """Test rendering prerequisite item when expanded."""
        # Mock columns with context manager support
        mock_cols = []
        for i in range(3):
            col = MagicMock()
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            mock_cols.append(col)
        mock_columns.return_value = mock_cols
        mock_button.return_value = False
        
        # Mock expander context manager
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        result = PrerequisiteResult(
            name="Test Checker",
            status=PrerequisiteStatus.FAILED,
            message="Failed",
            details="Error details",
            resolution_steps=["Fix step 1", "Fix step 2"],
            check_time=1.2,
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        ui = PrerequisiteChecklistUI()
        
        # Simulate expanded state
        st.session_state.expanded_items = {"Test Checker"}
        
        ui._render_prerequisite_item(result, is_required=True)
        
        mock_expander.assert_called_once()
    
    @patch('streamlit.write')
    @patch('streamlit.info')
    def test_render_recommendations_empty(self, mock_info, mock_write):
        """Test rendering recommendations when none available."""
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[],
            total_check_time=1.0,
            timestamp=datetime.now().isoformat()
        )
        
        self.mock_validation_logic.analyze_prerequisite_failures.return_value = []
        
        ui = PrerequisiteChecklistUI()
        ui._render_recommendations(check_suite, self.mock_validation_logic)
        
        mock_write.assert_called_with("### 💡 Recommendations")
        mock_info.assert_called_once_with("No specific recommendations available.")
    
    @patch('streamlit.write')
    @patch('streamlit.button')
    @patch('streamlit.columns')
    @patch('streamlit.container')
    @patch('streamlit.divider')
    def test_render_recommendations_with_items(self, mock_divider, mock_container, mock_columns, mock_button, mock_write):
        """Test rendering recommendations with items."""
        from src.logic.prerequisite_validation import PrerequisiteRecommendation
        
        recommendations = [
            PrerequisiteRecommendation(
                checker_name="Test Checker",
                issue_description="Test issue",
                priority="critical",
                resolution_steps=["Step 1", "Step 2"],
                estimated_time="5 minutes",
                automation_available=True
            )
        ]
        
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.FAILED,
            required_passed=False,
            recommended_passed=False,
            results=[],
            total_check_time=1.0,
            timestamp=datetime.now().isoformat()
        )
        
        self.mock_validation_logic.analyze_prerequisite_failures.return_value = recommendations
        
        # Mock Streamlit components
        mock_container.return_value.__enter__ = Mock()
        mock_container.return_value.__exit__ = Mock(return_value=None)
        mock_columns.return_value = [Mock(), Mock()]
        mock_button.return_value = False
        
        ui = PrerequisiteChecklistUI()
        ui._render_recommendations(check_suite, self.mock_validation_logic)
        
        mock_write.assert_called()
        mock_container.assert_called_once()
    
    @patch('streamlit.expander')
    @patch('streamlit.write')
    @patch('streamlit.columns')
    def test_render_metadata(self, mock_columns, mock_write, mock_expander):
        """Test rendering check metadata."""
        # Mock columns with context manager support
        mock_cols = []
        for i in range(2):
            col = MagicMock()
            col.__enter__ = Mock(return_value=col)
            col.__exit__ = Mock(return_value=None)
            mock_cols.append(col)
        mock_columns.return_value = mock_cols
        
        # Mock expander context manager
        mock_expander_context = Mock()
        mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
        mock_expander.return_value.__exit__ = Mock(return_value=None)
        
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[],
            total_check_time=2.5,
            timestamp="2024-01-01T00:00:00",
            cached=True
        )
        
        ui = PrerequisiteChecklistUI()
        ui._render_metadata(check_suite)
        
        mock_expander.assert_called_once_with("Check Metadata")
        mock_write.assert_called()
    
    @patch('streamlit.download_button')
    @patch('streamlit.success')
    def test_handle_export_request(self, mock_success, mock_download_button):
        """Test handling export request."""
        mock_result = PrerequisiteResult(
            name="Test",
            status=PrerequisiteStatus.PASSED,
            message="Passed",
            details="Details",
            resolution_steps=["Step 1"],
            check_time=1.0,
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[mock_result],
            total_check_time=1.0,
            timestamp="2024-01-01T00:00:00"
        )
        
        ui = PrerequisiteChecklistUI()
        ui._handle_export_request(check_suite)
        
        # Should create both JSON and CSV download buttons
        assert mock_download_button.call_count == 2
        mock_success.assert_called_once_with("Report export options generated!")
    
    @patch('streamlit.error')
    def test_handle_export_request_error(self, mock_error):
        """Test handling export request with error."""
        # Create invalid check suite that will cause JSON serialization error
        check_suite = Mock()
        check_suite.timestamp = datetime.now()  # Non-serializable datetime
        
        ui = PrerequisiteChecklistUI()
        ui._handle_export_request(check_suite)
        
        mock_error.assert_called()
    
    @patch('src.ui.prerequisite_checklist_ui.create_prerequisite_validation_logic')
    def test_get_validation_logic_creates_default(self, mock_create_logic):
        """Test that validation logic is created when not provided."""
        mock_logic = Mock()
        mock_create_logic.return_value = mock_logic
        
        ui = PrerequisiteChecklistUI(consent_service=self.mock_consent_service)
        
        result = ui._get_validation_logic(self.user_id)
        
        assert result == mock_logic
        mock_create_logic.assert_called_once_with(
            user_id=self.user_id,
            consent_service=self.mock_consent_service
        )
    
    def test_get_validation_logic_returns_existing(self):
        """Test that existing validation logic is returned."""
        ui = PrerequisiteChecklistUI(validation_logic=self.mock_validation_logic)
        
        result = ui._get_validation_logic(self.user_id)
        
        assert result == self.mock_validation_logic


class TestRenderFunctions:
    """Test cases for standalone render functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
    
    @patch('streamlit.sidebar')
    @patch('streamlit.write')
    @patch('src.ui.prerequisite_checklist_ui.PrerequisiteChecklistUI')
    def test_render_prerequisite_sidebar(self, mock_ui_class, mock_write, mock_sidebar):
        """Test rendering prerequisite sidebar."""
        mock_ui = Mock()
        mock_ui.render_compact_status.return_value = {"status": "ready"}
        mock_ui_class.return_value = mock_ui
        
        # Mock sidebar context manager
        mock_sidebar.__enter__ = Mock()
        mock_sidebar.__exit__ = Mock(return_value=None)
        
        result = render_prerequisite_sidebar("test_op", self.user_id)
        
        assert result == {"status": "ready"}
        mock_ui.render_compact_status.assert_called_once_with("test_op", self.user_id)
    
    @patch('streamlit.title')
    @patch('streamlit.write')
    @patch('src.ui.prerequisite_checklist_ui.PrerequisiteChecklistUI')
    def test_render_prerequisite_page(self, mock_ui_class, mock_write, mock_title):
        """Test rendering prerequisite page."""
        mock_ui = Mock()
        mock_ui.render_checklist.return_value = {"status": "completed"}
        mock_ui_class.return_value = mock_ui
        
        result = render_prerequisite_page("test_op", self.user_id)
        
        assert result == {"status": "completed"}
        mock_title.assert_called_once_with("System Prerequisites")
        mock_ui.render_checklist.assert_called_once_with(
            operation_name="test_op",
            user_id=self.user_id,
            show_header=False,
            auto_refresh=True
        )
    
    @patch('streamlit.write')
    @patch('streamlit.markdown')
    @patch('src.ui.prerequisite_checklist_ui.PrerequisiteChecklistUI')
    def test_render_accessible_prerequisite_checklist(self, mock_ui_class, mock_markdown, mock_write):
        """Test rendering accessible prerequisite checklist."""
        mock_ui = Mock()
        mock_ui.render_checklist.return_value = {"status": "accessible"}
        mock_ui_class.return_value = mock_ui
        
        result = render_accessible_prerequisite_checklist(
            "test_op", 
            self.user_id, 
            screen_reader_mode=True
        )
        
        assert result == {"status": "accessible"}
        mock_write.assert_called()
        mock_markdown.assert_called_once()  # CSS injection
        mock_ui.render_checklist.assert_called_once()
    
    @patch('streamlit.markdown')
    @patch('src.ui.prerequisite_checklist_ui.PrerequisiteChecklistUI')
    def test_render_accessible_prerequisite_checklist_normal_mode(self, mock_ui_class, mock_markdown):
        """Test rendering accessible checklist in normal mode."""
        mock_ui = Mock()
        mock_ui.render_checklist.return_value = {"status": "normal"}
        mock_ui_class.return_value = mock_ui
        
        result = render_accessible_prerequisite_checklist(
            "test_op", 
            self.user_id, 
            screen_reader_mode=False
        )
        
        assert result == {"status": "normal"}
        mock_markdown.assert_called_once()  # CSS injection only
        mock_ui.render_checklist.assert_called_once_with(
            operation_name="test_op",
            user_id=self.user_id,
            show_header=True,
            auto_refresh=False
        )


if __name__ == "__main__":
    pytest.main([__file__])