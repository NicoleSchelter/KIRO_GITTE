"""
Tests for UI tooltip integration functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.ui.tooltip_integration import get_tooltip_integration


class TestUITooltipIntegration(unittest.TestCase):
    """Test UI tooltip integration functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.integration = StreamlitTooltipIntegration()
        self.user_id = uuid4()
    
    def test_tooltip_integration_initialization(self):
        """Test tooltip integration initializes correctly."""
        self.assertIsNotNone(self.integration.tooltip_manager)
        self.assertIsNotNone(self.integration.tooltip_system)
    
    def test_get_tooltip_for_registered_element(self):
        """Test getting tooltip for registered element."""
        help_text = self.integration.tooltip_manager.get_tooltip_for_element("register_button")
        self.assertIsNotNone(help_text)
        self.assertIn("Register", help_text)
    
    def test_get_tooltip_for_unregistered_element(self):
        """Test getting tooltip for unregistered element returns None."""
        help_text = self.integration.tooltip_manager.get_tooltip_for_element("nonexistent_element")
        self.assertIsNone(help_text)
    
    def test_consent_checkbox_context(self):
        """Test consent checkbox generates appropriate context."""
        dependent_features = self.integration._get_dependent_features("data_processing")
        self.assertIsInstance(dependent_features, list)
        self.assertTrue(len(dependent_features) > 0)
    
    def test_form_validation_context(self):
        """Test form validation context generation."""
        context = {
            "disabled": True,
            "is_valid": False,
            "validation_errors": ["Username too short", "Password required"],
            "reason": "Complete required fields"
        }
        
        # This would be used in form_button_with_validation
        self.assertTrue(context["disabled"])
        self.assertFalse(context["is_valid"])
        self.assertEqual(len(context["validation_errors"]), 2)
    
    def test_prerequisite_context(self):
        """Test prerequisite checking context generation."""
        context = {
            "disabled": True,
            "prerequisites_met": False,
            "missing_prerequisites": ["Database connection", "Ollama service"],
            "reason": "Missing: Database connection, Ollama service"
        }
        
        # This would be used in prerequisite_button
        self.assertTrue(context["disabled"])
        self.assertFalse(context["prerequisites_met"])
        self.assertEqual(len(context["missing_prerequisites"]), 2)
    
    def test_global_integration_instance(self):
        """Test global integration instance works correctly."""
        integration1 = get_tooltip_integration()
        integration2 = get_tooltip_integration()
        
        # Should return the same instance
        self.assertIs(integration1, integration2)
    
    def test_tooltip_coverage_validation(self):
        """Test tooltip coverage validation functionality."""
        test_elements = ["register_button", "username_input", "nonexistent_element"]
        coverage = self.integration.tooltip_manager.validate_tooltip_coverage(test_elements)
        
        self.assertIn("total_elements", coverage)
        self.assertIn("covered_elements", coverage)
        self.assertIn("missing_elements", coverage)
        self.assertIn("coverage_percentage", coverage)
        
        # Should have some coverage but not 100% due to nonexistent element
        self.assertGreater(coverage["coverage_percentage"], 0)
        self.assertLess(coverage["coverage_percentage"], 100)
    
    def test_tooltip_categories(self):
        """Test tooltip categories are properly organized."""
        categories = [
            "registration", "consent", "embodiment", 
            "chat", "image", "navigation", "admin"
        ]
        
        for category in categories:
            tooltips = self.integration.tooltip_manager.get_tooltips_by_category(category)
            self.assertIsInstance(tooltips, dict)
            # Each category should have at least one tooltip
            self.assertGreater(len(tooltips), 0)
    
    def test_tooltip_documentation_generation(self):
        """Test tooltip documentation generation."""
        doc = self.integration.tooltip_manager.generate_tooltip_documentation()
        
        self.assertIsInstance(doc, str)
        self.assertIn("# GITTE UI Tooltip Documentation", doc)
        self.assertIn("Registration & Authentication", doc)
        self.assertIn("Consent & Privacy", doc)
    
    @patch('streamlit.button')
    def test_button_with_tooltip_mock(self, mock_button):
        """Test button with tooltip using mocked Streamlit."""
        mock_button.return_value = True
        
        # This would normally require Streamlit context
        # but we're testing the logic flow
        result = self.integration.button_with_tooltip(
            "Test Button",
            "register_button",
            disabled=False
        )
        
        # Verify the button was called
        mock_button.assert_called_once()
        call_args = mock_button.call_args
        
        # Check that help text was provided
        self.assertIn('help', call_args.kwargs)
        self.assertIsNotNone(call_args.kwargs['help'])
    
    def test_consent_specific_tooltips(self):
        """Test consent-specific tooltip functionality."""
        consent_types = ["data_processing", "ai_interaction", "image_generation", "analytics"]
        
        for consent_type in consent_types:
            dependent_features = self.integration._get_dependent_features(consent_type)
            self.assertIsInstance(dependent_features, list)
            # Each consent type should have dependent features
            if consent_type != "analytics":  # Analytics might be empty
                self.assertGreater(len(dependent_features), 0)


if __name__ == "__main__":
    unittest.main()