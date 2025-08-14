"""
Tests for Tooltip Integration helpers.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock

from src.ui.tooltip_integration import (
    StreamlitTooltipIntegration,
    get_tooltip_integration,
    tooltip_button,
    tooltip_input,
    tooltip_selectbox,
    tooltip_checkbox,
    consent_checkbox,
    form_submit_button,
    prerequisite_button
)


class TestTooltipIntegration(unittest.TestCase):
    """Test cases for TooltipIntegration class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock the tooltip content manager
        self.mock_tooltip_manager = Mock()
        self.mock_tooltip_manager.get_tooltip_for_element.return_value = "Test tooltip help text"
        self.mock_tooltip_manager.tooltip_system = Mock()
        
        # Create integration instance with mocked manager
        self.integration = TooltipIntegration()
        self.integration.tooltip_manager = self.mock_tooltip_manager
    
    @patch('streamlit.button')
    def test_button_with_tooltip(self, mock_st_button):
        """Test button creation with tooltip."""
        mock_st_button.return_value = True
        
        result = self.integration.button(
            "Test Button",
            tooltip_id="test_button",
            context={"test": "context"}
        )
        
        # Verify tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "test_button", {"test": "context"}
        )
        
        # Verify button was created with help text
        mock_st_button.assert_called_once_with(
            "Test Button",
            help="Test tooltip help text"
        )
        
        self.assertTrue(result)
    
    @patch('streamlit.button')
    def test_button_without_tooltip(self, mock_st_button):
        """Test button creation without tooltip."""
        mock_st_button.return_value = False
        
        result = self.integration.button("Test Button")
        
        # Verify no tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_not_called()
        
        # Verify button was created without help
        mock_st_button.assert_called_once_with("Test Button")
        
        self.assertFalse(result)
    
    @patch('streamlit.button')
    def test_button_with_existing_help(self, mock_st_button):
        """Test button with existing help parameter."""
        mock_st_button.return_value = True
        
        result = self.integration.button(
            "Test Button",
            tooltip_id="test_button",
            help="Existing help text"
        )
        
        # Should not override existing help
        mock_st_button.assert_called_once_with(
            "Test Button",
            help="Existing help text"
        )
    
    @patch('streamlit.text_input')
    def test_text_input_with_tooltip(self, mock_st_text_input):
        """Test text input creation with tooltip."""
        mock_st_text_input.return_value = "test value"
        
        result = self.integration.text_input(
            "Test Input",
            tooltip_id="test_input",
            value="default"
        )
        
        # Verify tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "test_input", None
        )
        
        # Verify text input was created with help
        mock_st_text_input.assert_called_once_with(
            "Test Input",
            value="default",
            help="Test tooltip help text"
        )
        
        self.assertEqual(result, "test value")
    
    @patch('streamlit.selectbox')
    def test_selectbox_with_tooltip(self, mock_st_selectbox):
        """Test selectbox creation with tooltip."""
        mock_st_selectbox.return_value = "option1"
        options = ["option1", "option2", "option3"]
        
        result = self.integration.selectbox(
            "Test Select",
            options,
            tooltip_id="test_select",
            index=0
        )
        
        # Verify tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "test_select", None
        )
        
        # Verify selectbox was created with help
        mock_st_selectbox.assert_called_once_with(
            "Test Select",
            options,
            index=0,
            help="Test tooltip help text"
        )
        
        self.assertEqual(result, "option1")
    
    @patch('streamlit.checkbox')
    def test_checkbox_with_tooltip(self, mock_st_checkbox):
        """Test checkbox creation with tooltip."""
        mock_st_checkbox.return_value = True
        
        result = self.integration.checkbox(
            "Test Checkbox",
            tooltip_id="test_checkbox",
            value=False
        )
        
        # Verify tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "test_checkbox", None
        )
        
        # Verify checkbox was created with help
        mock_st_checkbox.assert_called_once_with(
            "Test Checkbox",
            value=False,
            help="Test tooltip help text"
        )
        
        self.assertTrue(result)
    
    @patch('streamlit.slider')
    def test_slider_with_tooltip(self, mock_st_slider):
        """Test slider creation with tooltip."""
        mock_st_slider.return_value = 50
        
        result = self.integration.slider(
            "Test Slider",
            min_value=0,
            max_value=100,
            tooltip_id="test_slider",
            value=25
        )
        
        # Verify tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "test_slider", None
        )
        
        # Verify slider was created with help
        mock_st_slider.assert_called_once_with(
            "Test Slider",
            0,
            100,
            value=25,
            help="Test tooltip help text"
        )
        
        self.assertEqual(result, 50)
    
    @patch('streamlit.number_input')
    def test_number_input_with_tooltip(self, mock_st_number_input):
        """Test number input creation with tooltip."""
        mock_st_number_input.return_value = 42
        
        result = self.integration.number_input(
            "Test Number",
            tooltip_id="test_number",
            min_value=0,
            max_value=100
        )
        
        # Verify tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "test_number", None
        )
        
        # Verify number input was created with help
        mock_st_number_input.assert_called_once_with(
            "Test Number",
            min_value=0,
            max_value=100,
            help="Test tooltip help text"
        )
        
        self.assertEqual(result, 42)
    
    @patch('streamlit.text_area')
    def test_text_area_with_tooltip(self, mock_st_text_area):
        """Test text area creation with tooltip."""
        mock_st_text_area.return_value = "test text"
        
        result = self.integration.text_area(
            "Test Area",
            tooltip_id="test_area",
            height=100
        )
        
        # Verify tooltip was requested
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "test_area", None
        )
        
        # Verify text area was created with help
        mock_st_text_area.assert_called_once_with(
            "Test Area",
            height=100,
            help="Test tooltip help text"
        )
        
        self.assertEqual(result, "test text")
    
    def test_tooltip_manager_no_tooltip_found(self):
        """Test behavior when no tooltip is found."""
        # Mock manager to return None
        self.mock_tooltip_manager.get_tooltip_for_element.return_value = None
        
        with patch('streamlit.button') as mock_st_button:
            mock_st_button.return_value = True
            
            result = self.integration.button(
                "Test Button",
                tooltip_id="nonexistent_tooltip"
            )
            
            # Should still create button without help
            mock_st_button.assert_called_once_with("Test Button")
            self.assertTrue(result)


class TestGlobalTooltipIntegration(unittest.TestCase):
    """Test cases for global tooltip integration functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global integration
        import src.ui.tooltip_integration
        src.ui.tooltip_integration._tooltip_integration = None
    
    def test_get_tooltip_integration_singleton(self):
        """Test that get_tooltip_integration returns singleton."""
        integration1 = get_tooltip_integration()
        integration2 = get_tooltip_integration()
        
        self.assertIs(integration1, integration2)
        self.assertIsInstance(integration1, TooltipIntegration)
    
    @patch('src.ui.tooltip_integration.get_tooltip_integration')
    def test_convenience_functions(self, mock_get_integration):
        """Test convenience functions."""
        mock_integration = Mock()
        mock_get_integration.return_value = mock_integration
        
        # Test tooltip_button
        mock_integration.button.return_value = True
        result = tooltip_button("Test", tooltip_id="test")
        mock_integration.button.assert_called_once_with("Test", "test", None)
        self.assertTrue(result)
        
        # Test tooltip_text_input
        mock_integration.text_input.return_value = "test"
        result = tooltip_text_input("Test", tooltip_id="test")
        mock_integration.text_input.assert_called_once_with("Test", "test", None)
        self.assertEqual(result, "test")
        
        # Test tooltip_selectbox
        mock_integration.selectbox.return_value = "option1"
        result = tooltip_selectbox("Test", ["option1", "option2"], tooltip_id="test")
        mock_integration.selectbox.assert_called_once_with("Test", ["option1", "option2"], "test", None)
        self.assertEqual(result, "option1")
        
        # Test tooltip_checkbox
        mock_integration.checkbox.return_value = True
        result = tooltip_checkbox("Test", tooltip_id="test")
        mock_integration.checkbox.assert_called_once_with("Test", "test", None)
        self.assertTrue(result)
        
        # Test tooltip_slider
        mock_integration.slider.return_value = 50
        result = tooltip_slider("Test", 0, 100, tooltip_id="test")
        mock_integration.slider.assert_called_once_with("Test", 0, 100, "test", None)
        self.assertEqual(result, 50)
    
    @patch('src.ui.tooltip_integration.get_tooltip_content_manager')
    def test_add_tooltip_to_existing_element(self, mock_get_manager):
        """Test adding tooltip to existing element."""
        mock_manager = Mock()
        mock_manager.get_tooltip_for_element.return_value = "Tooltip text"
        mock_get_manager.return_value = mock_manager
        
        result = add_tooltip_to_existing_element("test_element", {"context": "test"})
        
        mock_manager.get_tooltip_for_element.assert_called_once_with("test_element", {"context": "test"})
        self.assertEqual(result, "Tooltip text")
    
    @patch('src.ui.tooltip_integration.get_tooltip_content_manager')
    def test_validate_ui_tooltip_coverage(self, mock_get_manager):
        """Test UI tooltip coverage validation."""
        mock_manager = Mock()
        mock_coverage = {
            "total_elements": 5,
            "covered_elements": 4,
            "coverage_percentage": 80.0,
            "missing": ["element5"]
        }
        mock_manager.validate_tooltip_coverage.return_value = mock_coverage
        mock_get_manager.return_value = mock_manager
        
        ui_elements = ["element1", "element2", "element3", "element4", "element5"]
        result = validate_ui_tooltip_coverage(ui_elements)
        
        mock_manager.validate_tooltip_coverage.assert_called_once_with(ui_elements)
        self.assertEqual(result, mock_coverage)
    
    def tearDown(self):
        """Clean up after tests."""
        # Reset global integration
        import src.ui.tooltip_integration
        src.ui.tooltip_integration._tooltip_integration = None


class TestTooltipIntegrationWithContext(unittest.TestCase):
    """Test tooltip integration with various context scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_tooltip_manager = Mock()
        self.integration = TooltipIntegration()
        self.integration.tooltip_manager = self.mock_tooltip_manager
    
    @patch('streamlit.button')
    def test_disabled_button_context(self, mock_st_button):
        """Test button with disabled context."""
        # Mock tooltip manager to return context-aware tooltip
        self.mock_tooltip_manager.get_tooltip_for_element.return_value = "Button is disabled: Missing prerequisites"
        
        context = {
            "disabled": True,
            "reason": "Missing prerequisites"
        }
        
        result = self.integration.button(
            "Submit",
            tooltip_id="submit_button",
            context=context,
            disabled=True
        )
        
        # Verify context was passed to tooltip manager
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "submit_button", context
        )
        
        # Verify button was created with contextual help
        mock_st_button.assert_called_once_with(
            "Submit",
            disabled=True,
            help="Button is disabled: Missing prerequisites"
        )
    
    @patch('streamlit.text_input')
    def test_form_validation_context(self, mock_st_text_input):
        """Test text input with form validation context."""
        self.mock_tooltip_manager.get_tooltip_for_element.return_value = "Email is required and must be valid format"
        
        context = {
            "is_valid": False,
            "validation_errors": ["Email is required", "Invalid email format"]
        }
        
        result = self.integration.text_input(
            "Email",
            tooltip_id="email_input",
            context=context
        )
        
        # Verify context was passed
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "email_input", context
        )
        
        # Verify input was created with validation help
        mock_st_text_input.assert_called_once_with(
            "Email",
            help="Email is required and must be valid format"
        )
    
    @patch('streamlit.checkbox')
    def test_consent_checkbox_context(self, mock_st_checkbox):
        """Test checkbox with consent context."""
        self.mock_tooltip_manager.get_tooltip_for_element.return_value = "⚠️ Data Processing Consent - Check to enable: AI chat, Image generation"
        
        context = {
            "consent_granted": False,
            "dependent_features": ["AI chat", "Image generation"]
        }
        
        result = self.integration.checkbox(
            "Data Processing Consent",
            tooltip_id="data_processing_consent",
            context=context
        )
        
        # Verify context was passed
        self.mock_tooltip_manager.get_tooltip_for_element.assert_called_once_with(
            "data_processing_consent", context
        )
        
        # Verify checkbox was created with consent-specific help
        mock_st_checkbox.assert_called_once_with(
            "Data Processing Consent",
            help="⚠️ Data Processing Consent - Check to enable: AI chat, Image generation"
        )


class TestTooltipIntegrationErrorHandling(unittest.TestCase):
    """Test error handling in tooltip integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_tooltip_manager = Mock()
        self.integration = TooltipIntegration()
        self.integration.tooltip_manager = self.mock_tooltip_manager
    
    @patch('streamlit.button')
    def test_tooltip_manager_exception(self, mock_st_button):
        """Test handling of tooltip manager exceptions."""
        # Mock tooltip manager to raise exception
        self.mock_tooltip_manager.get_tooltip_for_element.side_effect = Exception("Tooltip error")
        
        mock_st_button.return_value = True
        
        # Should not raise exception, should create button without tooltip
        result = self.integration.button(
            "Test Button",
            tooltip_id="test_button"
        )
        
        # Verify button was still created
        mock_st_button.assert_called_once_with("Test Button")
        self.assertTrue(result)
    
    @patch('streamlit.text_input')
    def test_none_tooltip_response(self, mock_st_text_input):
        """Test handling when tooltip manager returns None."""
        self.mock_tooltip_manager.get_tooltip_for_element.return_value = None
        
        mock_st_text_input.return_value = "test"
        
        result = self.integration.text_input(
            "Test Input",
            tooltip_id="nonexistent_tooltip"
        )
        
        # Should create input without help
        mock_st_text_input.assert_called_once_with("Test Input")
        self.assertEqual(result, "test")


if __name__ == '__main__':
    unittest.main()