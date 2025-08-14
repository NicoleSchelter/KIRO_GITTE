"""
Tests for accessibility compliance in GITTE UX enhancements.
Validates WCAG 2.1 AA compliance, keyboard navigation, and screen reader support.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from src.ui.accessibility import (
    AccessibilityHelper,
    KeyboardNavigation,
    ScreenReaderSupport,
    ContrastLevel,
    apply_accessibility_features,
    create_accessible_form_field,
    check_color_contrast,
)


class TestAccessibilityHelper:
    """Test accessibility helper functions."""

    def test_calculate_contrast_ratio_black_white(self):
        """Test contrast ratio calculation for black and white."""
        helper = AccessibilityHelper()
        ratio = helper.calculate_contrast_ratio("#000000", "#FFFFFF")
        assert ratio == 21.0  # Maximum contrast ratio

    def test_calculate_contrast_ratio_same_colors(self):
        """Test contrast ratio for identical colors."""
        helper = AccessibilityHelper()
        ratio = helper.calculate_contrast_ratio("#FF0000", "#FF0000")
        assert ratio == 1.0  # Minimum contrast ratio

    def test_meets_contrast_requirement_aa_normal(self):
        """Test WCAG AA normal text contrast requirement."""
        helper = AccessibilityHelper()
        
        # Should pass AA normal (4.5:1)
        assert helper.meets_contrast_requirement("#000000", "#FFFFFF", ContrastLevel.AA_NORMAL)
        assert helper.meets_contrast_requirement("#0066CC", "#FFFFFF", ContrastLevel.AA_NORMAL)
        
        # Should fail AA normal
        assert not helper.meets_contrast_requirement("#CCCCCC", "#FFFFFF", ContrastLevel.AA_NORMAL)

    def test_meets_contrast_requirement_aa_large(self):
        """Test WCAG AA large text contrast requirement."""
        helper = AccessibilityHelper()
        
        # Should pass AA large (3:1)
        assert helper.meets_contrast_requirement("#767676", "#FFFFFF", ContrastLevel.AA_LARGE)
        
        # Should fail AA large
        assert not helper.meets_contrast_requirement("#CCCCCC", "#FFFFFF", ContrastLevel.AA_LARGE)

    def test_get_accessible_color_pair_valid(self):
        """Test getting accessible color pair when colors are already valid."""
        helper = AccessibilityHelper()
        fg, bg = helper.get_accessible_color_pair("#000000", "#FFFFFF")
        assert fg == "#000000"
        assert bg == "#FFFFFF"

    def test_get_accessible_color_pair_invalid(self):
        """Test getting accessible color pair when colors need adjustment."""
        helper = AccessibilityHelper()
        fg, bg = helper.get_accessible_color_pair("#CCCCCC", "#FFFFFF")
        
        # Should return a high contrast pair
        assert helper.meets_contrast_requirement(fg, bg, ContrastLevel.AA_NORMAL)

    def test_generate_aria_label_button(self):
        """Test ARIA label generation for buttons."""
        helper = AccessibilityHelper()
        label = helper.generate_aria_label("button", "Save Changes", "disabled")
        assert "Save Changes" in label
        assert "button" in label
        assert "disabled" in label

    def test_generate_aria_label_with_position(self):
        """Test ARIA label generation with position information."""
        helper = AccessibilityHelper()
        label = helper.generate_aria_label("tab", "Settings", "selected", "2 of 4")
        assert "Settings" in label
        assert "tab" in label
        assert "selected" in label
        assert "2 of 4" in label

    def test_create_skip_link(self):
        """Test skip link creation."""
        helper = AccessibilityHelper()
        skip_link = helper.create_skip_link("main-content", "Skip to main")
        
        assert 'href="#main-content"' in skip_link
        assert "Skip to main" in skip_link
        assert "skip-link" in skip_link

    def test_add_focus_styles(self):
        """Test focus styles CSS generation."""
        helper = AccessibilityHelper()
        styles = helper.add_focus_styles()
        
        assert "focus" in styles
        assert "outline" in styles
        assert "prefers-contrast: high" in styles
        assert "prefers-reduced-motion: reduce" in styles


class TestKeyboardNavigation:
    """Test keyboard navigation utilities."""

    def test_add_keyboard_shortcuts(self):
        """Test keyboard shortcuts JavaScript generation."""
        nav = KeyboardNavigation()
        js_code = nav.add_keyboard_shortcuts()
        
        assert "keydown" in js_code
        assert "Alt" in js_code
        assert "Escape" in js_code
        assert "ArrowRight" in js_code
        assert "announcePageChange" in js_code

    def test_create_accessible_button(self):
        """Test accessible button creation."""
        nav = KeyboardNavigation()
        button_html = nav.create_accessible_button(
            "Click Me", 
            "handleClick()", 
            disabled=True, 
            aria_describedby="help-text"
        )
        
        assert "Click Me" in button_html
        assert "handleClick()" in button_html
        assert "disabled" in button_html
        assert 'aria-describedby="help-text"' in button_html
        assert 'aria-disabled="true"' in button_html


class TestScreenReaderSupport:
    """Test screen reader support utilities."""

    def test_create_live_region(self):
        """Test ARIA live region creation."""
        sr = ScreenReaderSupport()
        live_region = sr.create_live_region("announcements", "assertive")
        
        assert 'id="announcements"' in live_region
        assert 'aria-live="assertive"' in live_region
        assert 'aria-atomic="true"' in live_region
        assert "sr-only" in live_region

    def test_announce_to_screen_reader(self):
        """Test screen reader announcement generation."""
        sr = ScreenReaderSupport()
        announcement = sr.announce_to_screen_reader("Test message", "test-region")
        
        assert "Test message" in announcement
        assert "test-region" in announcement
        assert "textContent" in announcement

    def test_create_progress_announcement(self):
        """Test progress announcement creation."""
        sr = ScreenReaderSupport()
        announcement = sr.create_progress_announcement(3, 10, "file upload")
        
        assert "30%" in announcement
        assert "step 3 of 10" in announcement
        assert "file upload" in announcement


class TestAccessibleFormField:
    """Test accessible form field creation."""

    def test_create_accessible_form_field_basic(self):
        """Test basic form field creation."""
        field_info = create_accessible_form_field(
            "text", "Username", "username-field"
        )
        
        assert field_info["field_id"] == "username-field"
        assert "Username" in field_info["label"]
        assert field_info["required"] is False
        assert field_info["help"] == ""
        assert field_info["error"] == ""

    def test_create_accessible_form_field_required(self):
        """Test required form field creation."""
        field_info = create_accessible_form_field(
            "email", "Email Address", "email-field", required=True
        )
        
        assert field_info["required"] is True
        assert "required" in field_info["label"]
        assert "*" in field_info["label"]

    def test_create_accessible_form_field_with_help(self):
        """Test form field with help text."""
        field_info = create_accessible_form_field(
            "password", 
            "Password", 
            "password-field", 
            help_text="Must be at least 8 characters"
        )
        
        assert "Must be at least 8 characters" in field_info["help"]
        assert "password-field-help" in field_info["help"]
        assert "password-field-help" in field_info["aria_describedby"]

    def test_create_accessible_form_field_with_error(self):
        """Test form field with error message."""
        field_info = create_accessible_form_field(
            "text", 
            "Username", 
            "username-field", 
            error_message="Username is required"
        )
        
        assert "Username is required" in field_info["error"]
        assert "username-field-error" in field_info["error"]
        assert "username-field-error" in field_info["aria_describedby"]
        assert 'role="alert"' in field_info["error"]


class TestColorContrastChecker:
    """Test color contrast checking functionality."""

    def test_check_color_contrast_pass(self):
        """Test color contrast check that passes."""
        result = check_color_contrast("#000000", "#FFFFFF")
        
        assert result["ratio"] == 21.0
        assert result["aa_normal"] is True
        assert result["aa_large"] is True
        assert result["aaa_normal"] is True
        assert result["aaa_large"] is True
        assert result["recommendation"] == "Pass"
        assert result["suggested_colors"] is None

    def test_check_color_contrast_fail(self):
        """Test color contrast check that fails."""
        result = check_color_contrast("#CCCCCC", "#FFFFFF")
        
        assert result["ratio"] < 4.5
        assert result["aa_normal"] is False
        assert result["recommendation"] == "Fail - needs improvement"
        assert result["suggested_colors"] is not None

    def test_check_color_contrast_large_text_pass(self):
        """Test color contrast for large text that passes AA but not AAA."""
        result = check_color_contrast("#888888", "#FFFFFF")  # Gray that passes AA large but fails AA normal
        
        assert result["aa_large"] is True
        assert result["aa_normal"] is False


class TestAccessibilityIntegration:
    """Test accessibility integration with UI components."""

    @patch('streamlit.markdown')
    def test_apply_accessibility_features(self, mock_markdown):
        """Test applying accessibility features."""
        apply_accessibility_features()
        
        # Should call st.markdown multiple times for different features
        assert mock_markdown.call_count >= 3
        
        # Check that CSS styles are applied
        calls = [call[0][0] for call in mock_markdown.call_args_list]
        css_calls = [call for call in calls if '<style>' in call]
        assert len(css_calls) > 0
        
        # Check that JavaScript is applied
        js_calls = [call for call in calls if '<script>' in call]
        assert len(js_calls) > 0
        
        # Check that live region is created
        live_region_calls = [call for call in calls if 'aria-live' in call]
        assert len(live_region_calls) > 0

    def test_accessible_colors_contrast_compliance(self):
        """Test that all accessible colors meet contrast requirements."""
        helper = AccessibilityHelper()
        
        # Test primary accessible colors against white background
        for color_name, color_value in helper.ACCESSIBLE_COLORS.items():
            if color_name not in ['light', 'white']:  # Skip light colors
                assert helper.meets_contrast_requirement(
                    color_value, "#FFFFFF", ContrastLevel.AA_NORMAL
                ), f"Color {color_name} ({color_value}) fails AA contrast on white"

    def test_high_contrast_colors_compliance(self):
        """Test that high contrast colors meet AAA requirements."""
        helper = AccessibilityHelper()
        
        # Test high contrast colors
        for color_name, color_value in helper.HIGH_CONTRAST_COLORS.items():
            if color_name not in ['light', 'white']:  # Skip light colors
                assert helper.meets_contrast_requirement(
                    color_value, "#FFFFFF", ContrastLevel.AAA_NORMAL
                ), f"High contrast color {color_name} ({color_value}) fails AAA contrast"


class TestKeyboardNavigationIntegration:
    """Test keyboard navigation integration."""

    def test_keyboard_shortcuts_coverage(self):
        """Test that keyboard shortcuts cover essential functions."""
        nav = KeyboardNavigation()
        js_code = nav.add_keyboard_shortcuts()
        
        # Essential keyboard shortcuts
        essential_shortcuts = [
            "Alt",  # Alt key combinations
            "Escape",  # Close modals/dropdowns
            "Tab",  # Tab navigation
            "Arrow",  # Arrow key navigation
        ]
        
        for shortcut in essential_shortcuts:
            assert shortcut in js_code, f"Missing essential keyboard shortcut: {shortcut}"

    def test_focus_management(self):
        """Test focus management functionality."""
        nav = KeyboardNavigation()
        js_code = nav.add_keyboard_shortcuts()
        
        # Focus management features
        focus_features = [
            "focus()",
            "scrollIntoView",
            "activeElement",
        ]
        
        for feature in focus_features:
            assert feature in js_code, f"Missing focus management feature: {feature}"


class TestScreenReaderIntegration:
    """Test screen reader integration."""

    def test_aria_live_regions(self):
        """Test ARIA live region functionality."""
        sr = ScreenReaderSupport()
        
        # Test different politeness levels
        polite_region = sr.create_live_region("polite-region", "polite")
        assertive_region = sr.create_live_region("assertive-region", "assertive")
        
        assert 'aria-live="polite"' in polite_region
        assert 'aria-live="assertive"' in assertive_region

    def test_progress_announcements(self):
        """Test progress announcement formatting."""
        sr = ScreenReaderSupport()
        
        # Test various progress scenarios
        start_progress = sr.create_progress_announcement(1, 10, "image generation")
        mid_progress = sr.create_progress_announcement(5, 10, "image generation")
        end_progress = sr.create_progress_announcement(10, 10, "image generation")
        
        assert "10%" in start_progress
        assert "50%" in mid_progress
        assert "100%" in end_progress
        
        for progress in [start_progress, mid_progress, end_progress]:
            assert "image generation" in progress
            assert "step" in progress
            assert "of 10" in progress


@pytest.fixture
def mock_streamlit():
    """Mock Streamlit functions for testing."""
    with patch('streamlit.markdown') as mock_markdown, \
         patch('streamlit.title') as mock_title, \
         patch('streamlit.write') as mock_write:
        yield {
            'markdown': mock_markdown,
            'title': mock_title,
            'write': mock_write
        }


class TestAccessibilityCompliance:
    """Test overall accessibility compliance."""

    def test_wcag_aa_compliance_checklist(self):
        """Test WCAG 2.1 AA compliance checklist."""
        helper = AccessibilityHelper()
        
        # WCAG AA requirements checklist
        requirements = {
            "contrast_ratio_normal": lambda: helper.meets_contrast_requirement("#000000", "#FFFFFF", ContrastLevel.AA_NORMAL),
            "contrast_ratio_large": lambda: helper.meets_contrast_requirement("#767676", "#FFFFFF", ContrastLevel.AA_LARGE),
            "focus_indicators": lambda: "outline" in helper.add_focus_styles(),
            "keyboard_navigation": lambda: "keydown" in KeyboardNavigation().add_keyboard_shortcuts(),
            "screen_reader_support": lambda: "aria-live" in ScreenReaderSupport().create_live_region("test"),
            "skip_links": lambda: "skip-link" in helper.create_skip_link("main", "Skip"),
        }
        
        for requirement_name, requirement_test in requirements.items():
            assert requirement_test(), f"WCAG AA requirement failed: {requirement_name}"

    def test_accessibility_error_handling(self):
        """Test accessibility features handle errors gracefully."""
        helper = AccessibilityHelper()
        
        # Test with invalid color values
        ratio = helper.calculate_contrast_ratio("invalid", "#FFFFFF")
        assert ratio == 1.0  # Should return minimum ratio on error
        
        # Test with empty values
        label = helper.generate_aria_label("", "", "", "")
        assert isinstance(label, str)  # Should return string even with empty inputs

    def test_responsive_accessibility(self):
        """Test accessibility features work across different screen sizes."""
        helper = AccessibilityHelper()
        styles = helper.add_focus_styles()
        
        # Should include responsive design considerations
        assert "@media" in styles
        assert "max-width" in styles or "min-width" in styles

    def test_reduced_motion_support(self):
        """Test support for users who prefer reduced motion."""
        helper = AccessibilityHelper()
        styles = helper.add_focus_styles()
        
        assert "prefers-reduced-motion: reduce" in styles
        assert "animation-duration: 0.01ms" in styles
        assert "transition-duration: 0.01ms" in styles