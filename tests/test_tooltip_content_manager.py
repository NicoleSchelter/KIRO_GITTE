"""
Tests for Tooltip Content Manager.
"""

import unittest
from unittest.mock import Mock, patch

from src.ui.tooltip_content_manager import (
    TooltipContentManager,
    UIElementTooltips,
    get_tooltip_content_manager
)
from src.ui.tooltip_system import TooltipSystem, TooltipContent, TooltipTheme


class TestTooltipContentManager(unittest.TestCase):
    """Test cases for TooltipContentManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock tooltip system
        self.mock_tooltip_system = Mock(spec=TooltipSystem)
        self.mock_tooltip_system.registry = Mock()
        self.mock_tooltip_system.registry.list_registered.return_value = []
        
        # Create manager with mock system
        self.manager = TooltipContentManager(self.mock_tooltip_system)
    
    def test_manager_initialization(self):
        """Test tooltip content manager initialization."""
        self.assertIsNotNone(self.manager.tooltip_system)
        self.assertIsNotNone(self.manager.ui_tooltips)
        self.assertIsInstance(self.manager.ui_tooltips, UIElementTooltips)
    
    def test_ui_tooltips_structure(self):
        """Test that UI tooltips structure is properly created."""
        tooltips = self.manager.ui_tooltips
        
        # Check all categories exist
        self.assertIsInstance(tooltips.registration_tooltips, dict)
        self.assertIsInstance(tooltips.consent_tooltips, dict)
        self.assertIsInstance(tooltips.embodiment_tooltips, dict)
        self.assertIsInstance(tooltips.chat_tooltips, dict)
        self.assertIsInstance(tooltips.image_tooltips, dict)
        self.assertIsInstance(tooltips.navigation_tooltips, dict)
        self.assertIsInstance(tooltips.admin_tooltips, dict)
        
        # Check that categories have content
        self.assertGreater(len(tooltips.registration_tooltips), 0)
        self.assertGreater(len(tooltips.consent_tooltips), 0)
        self.assertGreater(len(tooltips.embodiment_tooltips), 0)
    
    def test_registration_tooltips_content(self):
        """Test registration tooltips content."""
        reg_tooltips = self.manager.ui_tooltips.registration_tooltips
        
        # Check key elements exist
        expected_elements = [
            "username_input",
            "email_input", 
            "password_input",
            "register_submit_button",
            "login_button"
        ]
        
        for element in expected_elements:
            self.assertIn(element, reg_tooltips)
            tooltip = reg_tooltips[element]
            self.assertIsInstance(tooltip, TooltipContent)
            self.assertIsInstance(tooltip.title, str)
            self.assertIsInstance(tooltip.description, str)
            self.assertGreater(len(tooltip.title), 0)
            self.assertGreater(len(tooltip.description), 0)
    
    def test_consent_tooltips_content(self):
        """Test consent tooltips content."""
        consent_tooltips = self.manager.ui_tooltips.consent_tooltips
        
        expected_elements = [
            "data_processing_consent",
            "llm_interaction_consent",
            "image_generation_consent"
        ]
        
        for element in expected_elements:
            self.assertIn(element, consent_tooltips)
            tooltip = consent_tooltips[element]
            self.assertIsInstance(tooltip, TooltipContent)
            # Consent tooltips should have help links
            self.assertIsNotNone(tooltip.help_link)
    
    def test_embodiment_tooltips_content(self):
        """Test embodiment design tooltips content."""
        embodiment_tooltips = self.manager.ui_tooltips.embodiment_tooltips
        
        expected_elements = [
            "character_name_input",
            "character_age_slider",
            "character_gender_select",
            "generate_preview_button"
        ]
        
        for element in expected_elements:
            self.assertIn(element, embodiment_tooltips)
            tooltip = embodiment_tooltips[element]
            self.assertIsInstance(tooltip, TooltipContent)
    
    def test_chat_tooltips_content(self):
        """Test chat interface tooltips content."""
        chat_tooltips = self.manager.ui_tooltips.chat_tooltips
        
        expected_elements = [
            "chat_input_field",
            "send_message_button",
            "clear_chat_button",
            "chat_history_button"
        ]
        
        for element in expected_elements:
            self.assertIn(element, chat_tooltips)
            tooltip = chat_tooltips[element]
            self.assertIsInstance(tooltip, TooltipContent)
    
    def test_image_tooltips_content(self):
        """Test image generation tooltips content."""
        image_tooltips = self.manager.ui_tooltips.image_tooltips
        
        expected_elements = [
            "image_prompt_input",
            "generate_image_button",
            "save_image_button",
            "download_image_button"
        ]
        
        for element in expected_elements:
            self.assertIn(element, image_tooltips)
            tooltip = image_tooltips[element]
            self.assertIsInstance(tooltip, TooltipContent)
    
    def test_navigation_tooltips_content(self):
        """Test navigation tooltips content."""
        nav_tooltips = self.manager.ui_tooltips.navigation_tooltips
        
        expected_elements = [
            "home_nav_button",
            "profile_nav_button",
            "settings_nav_button",
            "logout_button"
        ]
        
        for element in expected_elements:
            self.assertIn(element, nav_tooltips)
            tooltip = nav_tooltips[element]
            self.assertIsInstance(tooltip, TooltipContent)
    
    def test_admin_tooltips_content(self):
        """Test admin tooltips content."""
        admin_tooltips = self.manager.ui_tooltips.admin_tooltips
        
        expected_elements = [
            "admin_dashboard_button",
            "user_management_button",
            "system_settings_button"
        ]
        
        for element in expected_elements:
            self.assertIn(element, admin_tooltips)
            tooltip = admin_tooltips[element]
            self.assertIsInstance(tooltip, TooltipContent)
            # Admin tooltips should have warning/error themes
            self.assertIn(tooltip.theme, [TooltipTheme.WARNING, TooltipTheme.ERROR])
    
    def test_tooltip_registration(self):
        """Test that tooltips are registered with the system."""
        # Verify register_tooltip was called
        self.mock_tooltip_system.register_tooltip.assert_called()
        
        # Count total expected registrations
        total_expected = (
            len(self.manager.ui_tooltips.registration_tooltips) +
            len(self.manager.ui_tooltips.consent_tooltips) +
            len(self.manager.ui_tooltips.embodiment_tooltips) +
            len(self.manager.ui_tooltips.chat_tooltips) +
            len(self.manager.ui_tooltips.image_tooltips) +
            len(self.manager.ui_tooltips.navigation_tooltips) +
            len(self.manager.ui_tooltips.admin_tooltips)
        )
        
        # Verify correct number of calls
        self.assertEqual(
            self.mock_tooltip_system.register_tooltip.call_count,
            total_expected
        )
    
    def test_context_processor_registration(self):
        """Test that context processors are registered."""
        # Verify register_context_processor was called
        self.mock_tooltip_system.register_context_processor.assert_called()
        
        # Should be called for form inputs, buttons, and consent elements
        self.assertGreater(self.mock_tooltip_system.register_context_processor.call_count, 0)
    
    def test_get_tooltip_for_element(self):
        """Test getting tooltip for specific element."""
        # Mock the tooltip system response
        self.mock_tooltip_system.get_streamlit_help.return_value = "Test help text"
        
        result = self.manager.get_tooltip_for_element("test_element")
        
        self.assertEqual(result, "Test help text")
        self.mock_tooltip_system.get_streamlit_help.assert_called_once_with("test_element", None)
    
    def test_get_tooltip_for_element_with_context(self):
        """Test getting tooltip with context."""
        context = {"disabled": True, "reason": "Test reason"}
        self.mock_tooltip_system.get_streamlit_help.return_value = "Contextual help"
        
        result = self.manager.get_tooltip_for_element("test_element", context)
        
        self.assertEqual(result, "Contextual help")
        self.mock_tooltip_system.get_streamlit_help.assert_called_once_with("test_element", context)
    
    def test_get_all_registered_elements(self):
        """Test getting all registered elements."""
        expected_elements = ["element1", "element2", "element3"]
        self.mock_tooltip_system.registry.list_registered.return_value = expected_elements
        
        result = self.manager.get_all_registered_elements()
        
        self.assertEqual(result, expected_elements)
    
    def test_get_tooltips_by_category(self):
        """Test getting tooltips by category."""
        # Test valid categories
        categories = ["registration", "consent", "embodiment", "chat", "image", "navigation", "admin"]
        
        for category in categories:
            result = self.manager.get_tooltips_by_category(category)
            self.assertIsInstance(result, dict)
            self.assertGreater(len(result), 0)
        
        # Test invalid category
        result = self.manager.get_tooltips_by_category("invalid_category")
        self.assertEqual(result, {})
    
    def test_validate_tooltip_coverage(self):
        """Test tooltip coverage validation."""
        # Mock registered elements
        registered = ["element1", "element2", "element3", "element4"]
        self.mock_tooltip_system.registry.list_registered.return_value = registered
        
        # Test elements to check
        ui_elements = ["element1", "element2", "element5"]  # element5 is missing
        
        result = self.manager.validate_tooltip_coverage(ui_elements)
        
        self.assertEqual(result["total_elements"], 3)
        self.assertEqual(result["covered_elements"], 2)
        self.assertEqual(result["missing_elements"], 1)
        self.assertAlmostEqual(result["coverage_percentage"], 66.67, places=1)
        self.assertIn("element1", result["covered"])
        self.assertIn("element2", result["covered"])
        self.assertIn("element5", result["missing"])
        self.assertIn("element3", result["extra_registered"])
    
    def test_validate_tooltip_coverage_empty_list(self):
        """Test coverage validation with empty element list."""
        result = self.manager.validate_tooltip_coverage([])
        
        self.assertEqual(result["total_elements"], 0)
        self.assertEqual(result["coverage_percentage"], 0)
    
    def test_consent_processor(self):
        """Test consent context processor."""
        base_tooltip = TooltipContent(
            title="Test Consent",
            description="Test description",
            accessibility_label="Test label"
        )
        
        # Test granted consent
        context_granted = {
            "consent_granted": True,
            "dependent_features": ["chat", "images"]
        }
        
        result_granted = self.manager._consent_processor(base_tooltip, context_granted)
        
        self.assertIn("✅", result_granted.title)
        self.assertIn("granted", result_granted.description)
        self.assertEqual(result_granted.theme, TooltipTheme.SUCCESS)
        
        # Test not granted consent
        context_not_granted = {
            "consent_granted": False,
            "dependent_features": ["chat", "images"]
        }
        
        result_not_granted = self.manager._consent_processor(base_tooltip, context_not_granted)
        
        self.assertIn("⚠️", result_not_granted.title)
        self.assertIn("chat, images", result_not_granted.action_text)
        self.assertEqual(result_not_granted.theme, TooltipTheme.WARNING)
    
    def test_generate_tooltip_documentation(self):
        """Test tooltip documentation generation."""
        doc = self.manager.generate_tooltip_documentation()
        
        self.assertIsInstance(doc, str)
        self.assertIn("# GITTE UI Tooltip Documentation", doc)
        self.assertIn("## Registration & Authentication", doc)
        self.assertIn("## Consent & Privacy", doc)
        self.assertIn("username_input", doc)
        self.assertIn("data_processing_consent", doc)
    
    def test_tooltip_themes_assignment(self):
        """Test that appropriate themes are assigned to tooltips."""
        # Success theme for positive actions
        generate_button = self.manager.ui_tooltips.embodiment_tooltips["generate_preview_button"]
        self.assertEqual(generate_button.theme, TooltipTheme.SUCCESS)
        
        # Warning theme for potentially destructive actions
        clear_chat = self.manager.ui_tooltips.chat_tooltips["clear_chat_button"]
        self.assertEqual(clear_chat.theme, TooltipTheme.WARNING)
        
        # Warning/Error themes for admin functions
        admin_tooltips = self.manager.ui_tooltips.admin_tooltips
        for tooltip in admin_tooltips.values():
            self.assertIn(tooltip.theme, [TooltipTheme.WARNING, TooltipTheme.ERROR])
    
    def test_accessibility_labels(self):
        """Test that accessibility labels are provided."""
        all_tooltips = []
        
        # Collect all tooltips
        for category in [
            self.manager.ui_tooltips.registration_tooltips,
            self.manager.ui_tooltips.consent_tooltips,
            self.manager.ui_tooltips.embodiment_tooltips,
            self.manager.ui_tooltips.chat_tooltips,
            self.manager.ui_tooltips.image_tooltips,
            self.manager.ui_tooltips.navigation_tooltips,
            self.manager.ui_tooltips.admin_tooltips
        ]:
            all_tooltips.extend(category.values())
        
        # Check that all tooltips have accessibility labels
        for tooltip in all_tooltips:
            self.assertIsNotNone(tooltip.accessibility_label)
            self.assertGreater(len(tooltip.accessibility_label), 0)
    
    def test_help_links_for_important_elements(self):
        """Test that important elements have help links."""
        # Consent tooltips should have help links
        consent_tooltips = self.manager.ui_tooltips.consent_tooltips
        for tooltip in consent_tooltips.values():
            if "consent" in tooltip.title.lower():
                self.assertIsNotNone(tooltip.help_link)
        
        # Help navigation should have help link
        help_nav = self.manager.ui_tooltips.navigation_tooltips.get("help_nav_button")
        if help_nav:
            self.assertIsNotNone(help_nav.help_link)


class TestGlobalTooltipContentManager(unittest.TestCase):
    """Test cases for global tooltip content manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global manager
        import src.ui.tooltip_content_manager
        src.ui.tooltip_content_manager._tooltip_content_manager = None
    
    def test_get_tooltip_content_manager_singleton(self):
        """Test that get_tooltip_content_manager returns singleton."""
        manager1 = get_tooltip_content_manager()
        manager2 = get_tooltip_content_manager()
        
        self.assertIs(manager1, manager2)
        self.assertIsInstance(manager1, TooltipContentManager)
    
    def tearDown(self):
        """Clean up after tests."""
        # Reset global manager
        import src.ui.tooltip_content_manager
        src.ui.tooltip_content_manager._tooltip_content_manager = None


class TestTooltipContentIntegration(unittest.TestCase):
    """Integration tests for tooltip content with real tooltip system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use real tooltip system for integration testing
        self.manager = TooltipContentManager()
    
    def test_real_tooltip_system_integration(self):
        """Test integration with real tooltip system."""
        # Test getting tooltip for registered element
        help_text = self.manager.get_tooltip_for_element("username_input")
        
        self.assertIsNotNone(help_text)
        self.assertIsInstance(help_text, str)
        self.assertGreater(len(help_text), 0)
    
    def test_context_processing_integration(self):
        """Test context processing with real system."""
        # Test disabled button context
        context = {
            "disabled": True,
            "reason": "Form validation failed"
        }
        
        help_text = self.manager.get_tooltip_for_element("register_submit_button", context)
        
        self.assertIsNotNone(help_text)
        self.assertIn("validation", help_text.lower())
    
    def test_consent_context_processing(self):
        """Test consent context processing."""
        # Test consent not granted
        context = {
            "consent_granted": False,
            "dependent_features": ["AI chat", "Image generation"]
        }
        
        help_text = self.manager.get_tooltip_for_element("data_processing_consent", context)
        
        self.assertIsNotNone(help_text)
        self.assertIn("AI chat", help_text)
    
    def test_coverage_validation_real_elements(self):
        """Test coverage validation with realistic UI elements."""
        # Simulate real UI elements that should have tooltips
        ui_elements = [
            "username_input",
            "password_input", 
            "register_submit_button",
            "data_processing_consent",
            "chat_input_field",
            "generate_image_button",
            "some_missing_element"  # This one should be missing
        ]
        
        coverage = self.manager.validate_tooltip_coverage(ui_elements)
        
        self.assertGreater(coverage["coverage_percentage"], 80)  # Should have good coverage
        self.assertIn("some_missing_element", coverage["missing"])


if __name__ == '__main__':
    unittest.main()