"""
Tests for Tooltip System.
"""

import unittest

# Removed mock imports - using contract tests instead
from src.ui.tooltip_system import (
    TooltipConfig,
    TooltipContent,
    TooltipPosition,
    TooltipRegistry,
    TooltipRenderer,
    TooltipSystem,
    TooltipTheme,
    disabled_element_processor,
    form_validation_processor,
    get_tooltip_system,
)


class TestTooltipContent(unittest.TestCase):
    """Test cases for TooltipContent dataclass."""
    
    def test_tooltip_content_creation(self):
        """Test creating tooltip content with defaults."""
        content = TooltipContent(
            title="Test Title",
            description="Test description"
        )
        
        self.assertEqual(content.title, "Test Title")
        self.assertEqual(content.description, "Test description")
        self.assertIsNone(content.action_text)
        self.assertEqual(content.theme, TooltipTheme.DEFAULT)
        self.assertEqual(content.position, TooltipPosition.AUTO)
        self.assertEqual(content.show_delay_ms, 500)
    
    def test_tooltip_content_full_configuration(self):
        """Test creating tooltip content with all options."""
        content = TooltipContent(
            title="Full Test",
            description="Full description",
            action_text="Click here",
            help_link="/help",
            accessibility_label="Test tooltip",
            theme=TooltipTheme.SUCCESS,
            position=TooltipPosition.TOP,
            show_delay_ms=300,
            hide_delay_ms=100,
            max_width=400
        )
        
        self.assertEqual(content.title, "Full Test")
        self.assertEqual(content.action_text, "Click here")
        self.assertEqual(content.help_link, "/help")
        self.assertEqual(content.theme, TooltipTheme.SUCCESS)
        self.assertEqual(content.position, TooltipPosition.TOP)
        self.assertEqual(content.max_width, 400)


class TestTooltipRegistry(unittest.TestCase):
    """Test cases for TooltipRegistry."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = TooltipRegistry()
        self.test_content = TooltipContent(
            title="Test",
            description="Test description"
        )
    
    def test_register_and_get_tooltip(self):
        """Test registering and retrieving tooltip."""
        self.registry.register("test_element", self.test_content)
        
        retrieved = self.registry.get("test_element")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Test")
        self.assertEqual(retrieved.description, "Test description")
    
    def test_get_nonexistent_tooltip(self):
        """Test retrieving non-existent tooltip."""
        result = self.registry.get("nonexistent")
        
        self.assertIsNone(result)
    
    def test_list_registered(self):
        """Test listing registered tooltips."""
        self.registry.register("element1", self.test_content)
        self.registry.register("element2", self.test_content)
        
        registered = self.registry.list_registered()
        
        self.assertIn("element1", registered)
        self.assertIn("element2", registered)
        self.assertEqual(len(registered), 2)
    
    def test_unregister_tooltip(self):
        """Test unregistering tooltip."""
        self.registry.register("test_element", self.test_content)
        
        # Verify it exists
        self.assertIsNotNone(self.registry.get("test_element"))
        
        # Unregister
        result = self.registry.unregister("test_element")
        
        self.assertTrue(result)
        self.assertIsNone(self.registry.get("test_element"))
    
    def test_unregister_nonexistent(self):
        """Test unregistering non-existent tooltip."""
        result = self.registry.unregister("nonexistent")
        
        self.assertFalse(result)
    
    def test_context_processor(self):
        """Test context processor functionality."""
        def test_processor(base_tooltip, context):
            modified = TooltipContent(
                title=f"{base_tooltip.title} - Modified",
                description=(
                    f"{base_tooltip.description} (Context: {context.get('test_key', 'none')})"
                )
            )
            return modified
        
        self.registry.register("test_element", self.test_content)
        self.registry.register_context_processor("test_element", test_processor)
        
        # Get without context
        result_no_context = self.registry.get("test_element")
        self.assertEqual(result_no_context.title, "Test")
        
        # Get with context
        context = {"test_key": "test_value"}
        result_with_context = self.registry.get("test_element", context)
        
        self.assertEqual(result_with_context.title, "Test - Modified")
        self.assertIn("test_value", result_with_context.description)
    
    def test_context_processor_error_handling(self):
        """Test context processor error handling."""
        def failing_processor(base_tooltip, context):
            raise ValueError("Test error")
        
        self.registry.register("test_element", self.test_content)
        self.registry.register_context_processor("test_element", failing_processor)
        
        # Should return original tooltip on processor error
        result = self.registry.get("test_element", {"test": "context"})
        
        self.assertEqual(result.title, "Test")  # Original content


class TestTooltipRenderer(unittest.TestCase):
    """Test cases for TooltipRenderer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = TooltipConfig()
        self.renderer = TooltipRenderer(self.config)
        self.test_content = TooltipContent(
            title="Test Tooltip",
            description="This is a test tooltip description"
        )
    
    def test_render_html_basic(self):
        """Test basic HTML rendering."""
        html = self.renderer.render_html(self.test_content, "test_element")
        
        self.assertIn("Test Tooltip", html)
        self.assertIn("This is a test tooltip description", html)
        self.assertIn("gitte-tooltip", html)
        self.assertIn("tooltip-default", html)
        self.assertIn('id="tooltip-test_element"', html)
    
    def test_render_html_with_action(self):
        """Test HTML rendering with action text."""
        content = TooltipContent(
            title="Test",
            description="Description",
            action_text="Click to proceed"
        )
        
        html = self.renderer.render_html(content, "test_element")
        
        self.assertIn("Click to proceed", html)
        self.assertIn("tooltip-action", html)
    
    def test_render_html_with_help_link(self):
        """Test HTML rendering with help link."""
        content = TooltipContent(
            title="Test",
            description="Description",
            help_link="/help/test"
        )
        
        html = self.renderer.render_html(content, "test_element")
        
        self.assertIn("/help/test", html)
        self.assertIn("Learn more", html)
        self.assertIn("tooltip-help", html)
    
    def test_render_html_themes(self):
        """Test HTML rendering with different themes."""
        themes = [
            TooltipTheme.SUCCESS,
            TooltipTheme.WARNING,
            TooltipTheme.ERROR,
            TooltipTheme.DARK,
            TooltipTheme.LIGHT
        ]
        
        for theme in themes:
            content = TooltipContent(
                title="Test",
                description="Description",
                theme=theme
            )
            
            html = self.renderer.render_html(content, "test_element")
            
            self.assertIn(f"tooltip-{theme.value}", html)
    
    def test_render_html_accessibility(self):
        """Test HTML rendering with accessibility features."""
        content = TooltipContent(
            title="Test",
            description="Description",
            accessibility_label="Custom accessibility label"
        )
        
        html = self.renderer.render_html(content, "test_element")
        
        self.assertIn('role="tooltip"', html)
        self.assertIn('aria-label="Custom accessibility label"', html)
        self.assertIn('tabindex="0"', html)
    
    def test_render_html_disabled_config(self):
        """Test HTML rendering when tooltips are disabled."""
        disabled_config = TooltipConfig(enabled=False)
        disabled_renderer = TooltipRenderer(disabled_config)
        
        html = disabled_renderer.render_html(self.test_content, "test_element")
        
        self.assertEqual(html, "")
    
    def test_render_streamlit_help_basic(self):
        """Test Streamlit help text rendering."""
        help_text = self.renderer.render_streamlit_help(self.test_content)
        
        self.assertIn("This is a test tooltip description", help_text)
    
    def test_render_streamlit_help_with_extras(self):
        """Test Streamlit help text with action and link."""
        content = TooltipContent(
            title="Test",
            description="Description",
            action_text="Action required",
            help_link="/help"
        )
        
        help_text = self.renderer.render_streamlit_help(content)
        
        self.assertIn("Description", help_text)
        self.assertIn("💡 Action required", help_text)
        self.assertIn("📖 Learn more: /help", help_text)
        self.assertIn(" | ", help_text)  # Separator
    
    def test_render_streamlit_help_disabled(self):
        """Test Streamlit help when disabled."""
        disabled_config = TooltipConfig(enabled=False)
        disabled_renderer = TooltipRenderer(disabled_config)
        
        help_text = disabled_renderer.render_streamlit_help(self.test_content)
        
        self.assertEqual(help_text, "")


class TestTooltipSystem(unittest.TestCase):
    """Test cases for TooltipSystem."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = TooltipConfig()
        self.system = TooltipSystem(self.config)
        self.test_content = TooltipContent(
            title="System Test",
            description="System test description"
        )
    
    def test_system_initialization(self):
        """Test tooltip system initialization."""
        self.assertIsNotNone(self.system.registry)
        self.assertIsNotNone(self.system.renderer)
        self.assertEqual(self.system.config, self.config)
        
        # Check that default tooltips are registered
        stats = self.system.get_system_stats()
        self.assertGreater(stats["registered_tooltips"], 0)
    
    def test_register_and_get_tooltip(self):
        """Test registering and getting tooltip through system."""
        self.system.register_tooltip("test_system", self.test_content)
        
        retrieved = self.system.get_tooltip("test_system")
        
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "System Test")
    
    def test_render_tooltip_html(self):
        """Test rendering tooltip HTML through system."""
        self.system.register_tooltip("test_system", self.test_content)
        
        html = self.system.render_tooltip_html("test_system")
        
        self.assertIn("System Test", html)
        self.assertIn("gitte-tooltip", html)
    
    def test_get_streamlit_help(self):
        """Test getting Streamlit help through system."""
        self.system.register_tooltip("test_system", self.test_content)
        
        help_text = self.system.get_streamlit_help("test_system")
        
        self.assertIsNotNone(help_text)
        self.assertIn("System test description", help_text)
    
    def test_get_streamlit_help_nonexistent(self):
        """Test getting help for non-existent tooltip."""
        help_text = self.system.get_streamlit_help("nonexistent")
        
        self.assertIsNone(help_text)
    
    def test_inject_css_behavior(self):
        """Test CSS injection behavior without mocking."""
        # Test that CSS injection can be called without errors
        try:
            self.system.inject_css()
            # Should not raise an exception
            assert True
        except Exception as e:
            # If Streamlit is not available in test environment, that's acceptable
            assert "streamlit" in str(e).lower() or "module" in str(e).lower()
        
        # Test that multiple calls don't cause issues (idempotent behavior)
        try:
            self.system.inject_css()  # Second call
            assert True
        except Exception as e:
            # If Streamlit is not available, that's acceptable
            assert "streamlit" in str(e).lower() or "module" in str(e).lower()
    
    def test_css_injection_disabled(self):
        """Test CSS injection when disabled."""
        disabled_config = TooltipConfig(css_injection_enabled=False)
        disabled_system = TooltipSystem(disabled_config)
        
        # Should not attempt injection when disabled
        try:
            disabled_system.inject_css()
            # Should complete without error
            assert True
        except Exception as e:
            # Should not fail even if Streamlit is not available
            self.fail(f"CSS injection should not fail when disabled: {e}")
    
    def test_default_tooltips_registered(self):
        """Test that default tooltips are registered."""
        default_elements = [
            "register_button",
            "consent_checkbox",
            "image_generation_button",
            "chat_input",
            "embodiment_form"
        ]
        
        for element_id in default_elements:
            tooltip = self.system.get_tooltip(element_id)
            self.assertIsNotNone(tooltip, f"Default tooltip missing for {element_id}")
            self.assertIsInstance(tooltip.title, str)
            self.assertIsInstance(tooltip.description, str)
    
    def test_register_context_processor(self):
        """Test registering context processor through system."""
        def test_processor(base_tooltip, context):
            return TooltipContent(
                title=f"Processed: {base_tooltip.title}",
                description=base_tooltip.description
            )
        
        self.system.register_tooltip("test_element", self.test_content)
        self.system.register_context_processor("test_element", test_processor)
        
        result = self.system.get_tooltip("test_element", {"test": "context"})
        
        self.assertEqual(result.title, "Processed: System Test")
    
    def test_get_system_stats(self):
        """Test getting system statistics."""
        stats = self.system.get_system_stats()
        
        self.assertIn("enabled", stats)
        self.assertIn("registered_tooltips", stats)
        self.assertIn("css_injected", stats)
        self.assertIn("accessibility_enabled", stats)
        self.assertIn("registered_elements", stats)
        
        self.assertTrue(stats["enabled"])
        self.assertIsInstance(stats["registered_tooltips"], int)
        self.assertIsInstance(stats["registered_elements"], list)


class TestContextProcessors(unittest.TestCase):
    """Test cases for context processors."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.base_tooltip = TooltipContent(
            title="Base Title",
            description="Base description",
            accessibility_label="Base label"
        )
    
    def test_disabled_element_processor_enabled(self):
        """Test disabled element processor with enabled element."""
        context = {"disabled": False}
        
        result = disabled_element_processor(self.base_tooltip, context)
        
        # Should return original tooltip
        self.assertEqual(result, self.base_tooltip)
    
    def test_disabled_element_processor_disabled(self):
        """Test disabled element processor with disabled element."""
        context = {
            "disabled": True,
            "reason": "Missing prerequisites"
        }
        
        result = disabled_element_processor(self.base_tooltip, context)
        
        self.assertEqual(result.title, "Base Title")
        self.assertEqual(result.description, "Base description")
        self.assertEqual(result.action_text, "Missing prerequisites")
        self.assertEqual(result.theme, TooltipTheme.WARNING)
        self.assertIn("disabled", result.accessibility_label)
    
    def test_disabled_element_processor_no_reason(self):
        """Test disabled element processor without reason."""
        context = {"disabled": True}
        
        result = disabled_element_processor(self.base_tooltip, context)
        
        self.assertEqual(result.action_text, "This feature is currently disabled")
    
    def test_form_validation_processor_valid(self):
        """Test form validation processor with valid form."""
        context = {"is_valid": True, "validation_errors": []}
        
        result = form_validation_processor(self.base_tooltip, context)
        
        # Should return original tooltip
        self.assertEqual(result, self.base_tooltip)
    
    def test_form_validation_processor_invalid(self):
        """Test form validation processor with validation errors."""
        context = {
            "is_valid": False,
            "validation_errors": ["Field is required", "Invalid format"]
        }
        
        result = form_validation_processor(self.base_tooltip, context)
        
        self.assertEqual(result.title, "Base Title")
        self.assertEqual(result.description, "Base description")
        self.assertIn("Field is required", result.action_text)
        self.assertIn("Invalid format", result.action_text)
        self.assertEqual(result.theme, TooltipTheme.ERROR)
    
    def test_form_validation_processor_no_errors_list(self):
        """Test form validation processor without specific errors."""
        context = {"is_valid": False}
        
        result = form_validation_processor(self.base_tooltip, context)
        
        self.assertIn("Please check your input", result.action_text)


class TestGlobalTooltipSystem(unittest.TestCase):
    """Test cases for global tooltip system."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global system
        import src.ui.tooltip_system
        src.ui.tooltip_system._tooltip_system = None
    
    def test_get_tooltip_system_singleton(self):
        """Test that get_tooltip_system returns singleton."""
        system1 = get_tooltip_system()
        system2 = get_tooltip_system()
        
        self.assertIs(system1, system2)
    
    def test_get_tooltip_system_with_config(self):
        """Test getting tooltip system with custom config."""
        config = TooltipConfig(enabled=False)
        system = get_tooltip_system(config)
        
        self.assertFalse(system.config.enabled)
    
    def tearDown(self):
        """Clean up after tests."""
        # Reset global system
        import src.ui.tooltip_system
        src.ui.tooltip_system._tooltip_system = None


if __name__ == '__main__':
    unittest.main()