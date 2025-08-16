"""
Unit tests for accessible form components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ui.accessible_form_components import (
    AccessibleFormComponents,
    ValidationResult,
    SubmissionMethod
)


class TestAccessibleFormComponents:
    """Test accessible form components functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.components = AccessibleFormComponents()
    
    def test_validation_result_creation(self):
        """Test ValidationResult dataclass creation."""
        # Valid result
        valid_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert valid_result.is_valid is True
        assert len(valid_result.errors) == 0
        assert len(valid_result.warnings) == 0
        
        # Invalid result with errors
        invalid_result = ValidationResult(
            is_valid=False, 
            errors=["Field is required"], 
            warnings=["Consider adding more detail"]
        )
        assert invalid_result.is_valid is False
        assert len(invalid_result.errors) == 1
        assert len(invalid_result.warnings) == 1
    
    @patch('streamlit.form_submit_button')
    def test_form_submit_handler_success(self, mock_submit_button):
        """Test successful form submission handling."""
        mock_submit_button.return_value = True
        callback_mock = Mock()
        
        result = self.components.form_submit_handler(
            form_key="test_form",
            submit_label="Submit Test",
            callback=callback_mock
        )
        
        assert result is True
        callback_mock.assert_called_once()
        mock_submit_button.assert_called_once()
    
    @patch('streamlit.form_submit_button')
    def test_form_submit_handler_not_submitted(self, mock_submit_button):
        """Test form submission handler when not submitted."""
        mock_submit_button.return_value = False
        callback_mock = Mock()
        
        result = self.components.form_submit_handler(
            form_key="test_form",
            callback=callback_mock
        )
        
        assert result is False
        callback_mock.assert_not_called()
    
    @patch('streamlit.form_submit_button')
    @patch('streamlit.error')
    def test_form_submit_handler_validation_failure(self, mock_error, mock_submit_button):
        """Test form submission with validation failure."""
        mock_submit_button.return_value = True
        
        validation_callback = Mock(return_value=ValidationResult(
            is_valid=False,
            errors=["Invalid input"],
            warnings=[]
        ))
        
        result = self.components.form_submit_handler(
            form_key="test_form",
            validation_callback=validation_callback
        )
        
        assert result is False
        validation_callback.assert_called_once()
        mock_error.assert_called_once_with("Invalid input")
    
    @patch('streamlit.form_submit_button')
    @patch('streamlit.error')
    def test_form_submit_handler_callback_error(self, mock_error, mock_submit_button):
        """Test form submission with callback error."""
        mock_submit_button.return_value = True
        callback_mock = Mock(side_effect=Exception("Callback error"))
        
        result = self.components.form_submit_handler(
            form_key="test_form",
            callback=callback_mock
        )
        
        assert result is False
        callback_mock.assert_called_once()
        mock_error.assert_called_once()
    
    def test_auto_submit_form_trigger_change(self):
        """Test auto-submit when trigger field changes."""
        callback_mock = Mock()
        
        # First call - no previous state
        form_data = {"trigger_field": "new_value", "other_field": "data"}
        result = self.components.auto_submit_form(
            form_key="test_form",
            form_data=form_data,
            trigger_field="trigger_field",
            callback=callback_mock
        )
        
        assert result is True
        callback_mock.assert_called_once_with(form_data)
    
    def test_auto_submit_form_no_change(self):
        """Test auto-submit when trigger field doesn't change."""
        callback_mock = Mock()
        
        # Set initial state
        form_data = {"trigger_field": "value", "other_field": "data"}
        self.components.form_states["test_form"] = {"trigger_field": "value"}
        
        result = self.components.auto_submit_form(
            form_key="test_form",
            form_data=form_data,
            trigger_field="trigger_field",
            callback=callback_mock
        )
        
        assert result is False
        callback_mock.assert_not_called()
    
    @patch('streamlit.selectbox')
    def test_accessible_action_button_triggered(self, mock_selectbox):
        """Test accessible action button when action is selected."""
        mock_selectbox.return_value = "🔄 Refresh"
        callback_mock = Mock()
        
        with patch('streamlit.session_state', {}):
            result = self.components.accessible_action_button(
                label="Refresh",
                key="refresh_btn",
                callback=callback_mock,
                icon="🔄"
            )
        
        assert result is True
        callback_mock.assert_called_once()
    
    @patch('streamlit.selectbox')
    def test_accessible_action_button_not_triggered(self, mock_selectbox):
        """Test accessible action button when no action is selected."""
        mock_selectbox.return_value = "Select action..."
        callback_mock = Mock()
        
        result = self.components.accessible_action_button(
            label="Refresh",
            key="refresh_btn",
            callback=callback_mock
        )
        
        assert result is False
        callback_mock.assert_not_called()
    
    @patch('streamlit.radio')
    @patch('streamlit.warning')
    def test_confirmation_dialog_confirm(self, mock_warning, mock_radio):
        """Test confirmation dialog with confirm choice."""
        mock_radio.return_value = "Confirm"
        
        result = self.components.confirmation_dialog(
            message="Are you sure?",
            confirm_label="Confirm",
            cancel_label="Cancel"
        )
        
        assert result is True
        mock_warning.assert_called_once_with("Are you sure?")
    
    @patch('streamlit.radio')
    @patch('streamlit.warning')
    def test_confirmation_dialog_cancel(self, mock_warning, mock_radio):
        """Test confirmation dialog with cancel choice."""
        mock_radio.return_value = "Cancel"
        
        result = self.components.confirmation_dialog(
            message="Are you sure?",
            confirm_label="Confirm",
            cancel_label="Cancel"
        )
        
        assert result is False
    
    @patch('streamlit.progress')
    @patch('streamlit.columns')
    @patch('streamlit.success')
    @patch('streamlit.info')
    @patch('streamlit.write')
    def test_progress_indicator(self, mock_write, mock_info, mock_success, mock_columns, mock_progress):
        """Test progress indicator display."""
        # Mock columns
        mock_col = Mock()
        mock_columns.return_value = [mock_col, mock_col, mock_col]
        
        step_names = ["Step 1", "Step 2", "Step 3"]
        
        result = self.components.progress_indicator(
            current_step=2,
            total_steps=3,
            step_names=step_names,
            show_navigation=False
        )
        
        mock_progress.assert_called_once_with(2/3, text="Step 2 of 3")
        assert mock_columns.called
    
    @patch('streamlit.success')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    def test_validation_feedback(self, mock_warning, mock_error, mock_success):
        """Test validation feedback display."""
        # Valid result
        valid_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        self.components.validation_feedback("test_field", valid_result)
        mock_success.assert_called_once_with("✅ test_field is valid")
        
        # Invalid result with errors and warnings
        invalid_result = ValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=["Warning 1"]
        )
        self.components.validation_feedback("test_field", invalid_result)
        
        assert mock_error.call_count == 2
        mock_warning.assert_called_once_with("⚠️ test_field: Warning 1")
    
    @patch('streamlit.file_uploader')
    @patch('streamlit.info')
    @patch('streamlit.success')
    def test_accessible_file_uploader_success(self, mock_success, mock_info, mock_uploader):
        """Test accessible file uploader with successful processing."""
        # Mock uploaded file
        mock_file = Mock()
        mock_file.name = "test.txt"
        mock_file.size = 1024
        mock_uploader.return_value = mock_file
        
        callback_mock = Mock(return_value="processed_data")
        
        result = self.components.accessible_file_uploader(
            label="Upload File",
            key="file_upload",
            accepted_types=["txt"],
            callback=callback_mock
        )
        
        assert result == "processed_data"
        callback_mock.assert_called_once_with(mock_file)
        mock_info.assert_called_once_with("📁 File: test.txt (1024 bytes)")
        mock_success.assert_called_once_with("✅ File processed successfully")
    
    @patch('streamlit.multiselect')
    @patch('streamlit.success')
    def test_accessible_multi_select_valid(self, mock_success, mock_multiselect):
        """Test accessible multi-select with valid selection."""
        mock_multiselect.return_value = ["option1", "option2"]
        callback_mock = Mock()
        
        result = self.components.accessible_multi_select(
            label="Select Options",
            options=["option1", "option2", "option3"],
            key="multi_select",
            callback=callback_mock,
            min_selections=1,
            max_selections=3
        )
        
        assert result == ["option1", "option2"]
        callback_mock.assert_called_once_with(["option1", "option2"])
        mock_success.assert_called_once_with("✅ 2 option(s) selected")
    
    @patch('streamlit.multiselect')
    @patch('streamlit.error')
    def test_accessible_multi_select_invalid(self, mock_error, mock_multiselect):
        """Test accessible multi-select with invalid selection."""
        mock_multiselect.return_value = []  # No selections
        callback_mock = Mock()
        
        result = self.components.accessible_multi_select(
            label="Select Options",
            options=["option1", "option2", "option3"],
            key="multi_select",
            callback=callback_mock,
            min_selections=1
        )
        
        assert result == []
        callback_mock.assert_not_called()
        mock_error.assert_called_once_with("Please select at least 1 option(s)")
    
    @patch('streamlit.number_input')
    def test_accessible_number_input_valid(self, mock_number_input):
        """Test accessible number input with valid value."""
        mock_number_input.return_value = 5.0
        callback_mock = Mock()
        
        result = self.components.accessible_number_input(
            label="Enter Number",
            key="number_input",
            min_value=1.0,
            max_value=10.0,
            callback=callback_mock
        )
        
        assert result == 5.0
        callback_mock.assert_called_once_with(5.0)
    
    @patch('streamlit.number_input')
    @patch('streamlit.error')
    def test_accessible_number_input_invalid(self, mock_error, mock_number_input):
        """Test accessible number input with invalid value."""
        mock_number_input.return_value = 15.0  # Above max
        callback_mock = Mock()
        
        result = self.components.accessible_number_input(
            label="Enter Number",
            key="number_input",
            min_value=1.0,
            max_value=10.0,
            callback=callback_mock
        )
        
        assert result is None
        callback_mock.assert_not_called()
        mock_error.assert_called_once_with("Value must be no more than 10.0")
    
    @patch('streamlit.text_area')
    @patch('streamlit.success')
    def test_accessible_text_area_valid(self, mock_success, mock_text_area):
        """Test accessible text area with valid input."""
        mock_text_area.return_value = "Valid text input"
        callback_mock = Mock()
        
        result = self.components.accessible_text_area(
            label="Enter Text",
            key="text_area",
            callback=callback_mock,
            min_length=5
        )
        
        assert result == "Valid text input"
        callback_mock.assert_called_once_with("Valid text input")
        mock_success.assert_called_once_with("✅ 16 characters entered")
    
    @patch('streamlit.text_area')
    @patch('streamlit.error')
    def test_accessible_text_area_invalid(self, mock_error, mock_text_area):
        """Test accessible text area with invalid input."""
        mock_text_area.return_value = "Hi"  # Too short
        callback_mock = Mock()
        
        result = self.components.accessible_text_area(
            label="Enter Text",
            key="text_area",
            callback=callback_mock,
            min_length=5
        )
        
        assert result == "Hi"
        callback_mock.assert_not_called()
        mock_error.assert_called_once_with("Please enter at least 5 characters")
    
    @patch('streamlit.form')
    @patch('streamlit.subheader')
    @patch('streamlit.text_input')
    def test_create_accessible_form(self, mock_text_input, mock_subheader, mock_form):
        """Test creating a complete accessible form."""
        # Mock form context manager
        mock_form.return_value.__enter__ = Mock()
        mock_form.return_value.__exit__ = Mock()
        
        mock_text_input.return_value = "test_value"
        
        fields = [
            {
                "type": "text",
                "key": "name",
                "label": "Name",
                "help": "Enter your name"
            }
        ]
        
        submit_callback = Mock()
        
        with patch.object(self.components, 'form_submit_handler', return_value=True):
            result = self.components.create_accessible_form(
                form_key="test_form",
                title="Test Form",
                fields=fields,
                submit_callback=submit_callback
            )
        
        assert "name" in result
        mock_subheader.assert_called_once_with("Test Form")


if __name__ == "__main__":
    pytest.main([__file__])