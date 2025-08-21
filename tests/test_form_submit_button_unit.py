#!/usr/bin/env python3
"""
Unit test for tooltip wrapper functions including form_submit_button.
Tests parameter handling and edge cases for all tooltip wrappers.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch
from src.ui.tooltip_integration import (
    form_submit_button, tooltip_input, tooltip_selectbox, 
    tooltip_checkbox, tooltip_button
)

class TestTooltipWrappers(unittest.TestCase):
    """Test cases for tooltip wrapper functions."""
    
    @patch('src.ui.tooltip_integration.st')
    def test_form_submit_button_basic(self, mock_st):
        """Test basic form_submit_button functionality."""
        mock_st.form_submit_button.return_value = True
        
        result = form_submit_button("Test Label")
        
        mock_st.form_submit_button.assert_called_once_with(
            "Test Label", 
            disabled=False
        )
        self.assertTrue(result)
    
    @patch('src.ui.tooltip_integration.st')
    def test_form_submit_button_supports_all_kwargs(self, mock_st):
        """Test that all Streamlit parameters are now supported."""
        mock_st.form_submit_button.return_value = False
        
        result = form_submit_button(
            "Test Label",
            type="primary",
            use_container_width=True,
            disabled=True,
            help="Test help"
        )
        
        # Should pass all supported parameters
        mock_st.form_submit_button.assert_called_once_with(
            "Test Label", 
            type="primary",
            use_container_width=True,
            disabled=True,
            help="Test help"
        )
        self.assertFalse(result)
    
    @patch('src.ui.tooltip_integration.st')
    def test_tooltip_input_with_positional_args(self, mock_st):
        """Test tooltip_input with positional arguments."""
        mock_st.text_input.return_value = "test_value"
        
        # Test the actual usage pattern: tooltip_input("Label", "key", placeholder="...")
        result = tooltip_input("Username", "username_key", placeholder="Enter username")
        
        # Should extract label from first arg, key from second arg
        mock_st.text_input.assert_called_once_with(
            "Username",  # resolved label
            "username_key",  # remaining args
            placeholder="Enter username",
            label_visibility="collapsed"
        )
        self.assertEqual(result, "test_value")
    
    @patch('src.ui.tooltip_integration.st')
    def test_tooltip_selectbox_with_options_kwarg(self, mock_st):
        """Test tooltip_selectbox with options in kwargs."""
        mock_st.selectbox.return_value = "option1"
        
        # Test the actual usage pattern: tooltip_selectbox("Label", "key", options=[...], index=0)
        result = tooltip_selectbox(
            "Account Type", 
            "role_select", 
            options=["User", "Admin"], 
            index=0
        )
        
        mock_st.selectbox.assert_called_once_with(
            "Account Type",  # resolved label
            ["User", "Admin"],  # options
            key="role_select",  # key
            index=0,
            label_visibility="collapsed"
        )
        self.assertEqual(result, "option1")
    
    @patch('src.ui.tooltip_integration.st')
    def test_tooltip_checkbox_with_positional_args(self, mock_st):
        """Test tooltip_checkbox with positional arguments."""
        mock_st.checkbox.return_value = True
        
        # Test the actual usage pattern: tooltip_checkbox("Label", "key")
        result = tooltip_checkbox("I accept terms", "terms_checkbox")
        
        mock_st.checkbox.assert_called_once_with(
            "I accept terms",  # resolved label
            "terms_checkbox",  # remaining args
            label_visibility="collapsed"
        )
        self.assertTrue(result)
    
    @patch('src.ui.tooltip_integration.st')
    def test_empty_label_fallback(self, mock_st):
        """Test that empty labels fallback correctly."""
        mock_st.form_submit_button.return_value = False
        mock_st.text_input.return_value = ""
        mock_st.checkbox.return_value = False
        
        # Test form_submit_button with empty label
        form_submit_button("")
        mock_st.form_submit_button.assert_called_with(
            "Submit",  # fallback
            disabled=False
        )
        
        # Test tooltip_input with empty label
        tooltip_input("", "key")
        args, kwargs = mock_st.text_input.call_args
        self.assertEqual(args[0], "Input")  # fallback for text input
        
        # Test tooltip_checkbox with empty label
        tooltip_checkbox("", "key")
        args, kwargs = mock_st.checkbox.call_args
        self.assertEqual(args[0], "I accept the terms")  # fallback for checkbox

if __name__ == "__main__":
    unittest.main()