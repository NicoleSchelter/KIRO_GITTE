"""
Accessibility utilities for GITTE system.
Provides WCAG 2.1 AA compliance, keyboard navigation, and screen reader support.
"""

import logging
from enum import Enum
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


class ContrastLevel(str, Enum):
    """WCAG contrast level requirements."""

    AA_NORMAL = "AA_normal"  # 4.5:1 for normal text
    AA_LARGE = "AA_large"  # 3:1 for large text
    AAA_NORMAL = "AAA_normal"  # 7:1 for normal text
    AAA_LARGE = "AAA_large"  # 4.5:1 for large text


class AccessibilityHelper:
    """Helper class for accessibility features."""

    # WCAG 2.1 AA compliant color palette
    ACCESSIBLE_COLORS = {
        "primary": "#0066CC",  # Blue - 4.5:1 contrast on white
        "secondary": "#6C757D",  # Gray - 4.5:1 contrast on white
        "success": "#1B7332",  # Green - 4.5:1 contrast on white (darker than original)
        "warning": "#856404",  # Dark yellow - 4.5:1 contrast on white
        "danger": "#C82333",  # Red - 4.5:1 contrast on white (darker than original)
        "info": "#0F6674",  # Dark cyan - 4.5:1 contrast on white
        "light": "#F8F9FA",  # Light gray
        "dark": "#343A40",  # Dark gray - 4.5:1 contrast on white
        "white": "#FFFFFF",
        "black": "#000000",
    }

    # High contrast alternatives
    HIGH_CONTRAST_COLORS = {
        "primary": "#0000FF",  # Pure blue
        "secondary": "#000000",  # Black
        "success": "#006400",  # Dark green - 7:1 contrast on white
        "warning": "#5A4D00",  # Very dark yellow - 7:1 contrast on white
        "danger": "#8B0000",  # Dark red - 7:1 contrast on white
        "info": "#004D4D",  # Very dark teal - 7:1 contrast on white
        "light": "#FFFFFF",  # White
        "dark": "#000000",  # Black
        "white": "#FFFFFF",
        "black": "#000000",
    }

    @staticmethod
    def calculate_contrast_ratio(color1: str, color2: str) -> float:
        """
        Calculate contrast ratio between two colors.

        Args:
            color1: First color in hex format (#RRGGBB)
            color2: Second color in hex format (#RRGGBB)

        Returns:
            Contrast ratio (1-21)
        """

        def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
            """Convert hex color to RGB."""
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        def get_luminance(rgb: tuple[int, int, int]) -> float:
            """Calculate relative luminance."""

            def normalize_channel(channel: int) -> float:
                channel = channel / 255.0
                if channel <= 0.03928:
                    return channel / 12.92
                else:
                    return pow((channel + 0.055) / 1.055, 2.4)

            r, g, b = rgb
            r_norm = normalize_channel(r)
            g_norm = normalize_channel(g)
            b_norm = normalize_channel(b)

            return 0.2126 * r_norm + 0.7152 * g_norm + 0.0722 * b_norm

        try:
            rgb1 = hex_to_rgb(color1)
            rgb2 = hex_to_rgb(color2)

            lum1 = get_luminance(rgb1)
            lum2 = get_luminance(rgb2)

            # Ensure lighter color is in numerator
            if lum1 > lum2:
                return (lum1 + 0.05) / (lum2 + 0.05)
            else:
                return (lum2 + 0.05) / (lum1 + 0.05)

        except Exception as e:
            logger.error(f"Error calculating contrast ratio: {e}")
            return 1.0

    @staticmethod
    def meets_contrast_requirement(
        foreground: str, background: str, level: ContrastLevel = ContrastLevel.AA_NORMAL
    ) -> bool:
        """
        Check if color combination meets WCAG contrast requirements.

        Args:
            foreground: Foreground color in hex
            background: Background color in hex
            level: WCAG contrast level requirement

        Returns:
            True if contrast requirement is met
        """
        ratio = AccessibilityHelper.calculate_contrast_ratio(foreground, background)

        requirements = {
            ContrastLevel.AA_NORMAL: 4.5,
            ContrastLevel.AA_LARGE: 3.0,
            ContrastLevel.AAA_NORMAL: 7.0,
            ContrastLevel.AAA_LARGE: 4.5,
        }

        return ratio >= requirements[level]

    @staticmethod
    def get_accessible_color_pair(
        preferred_fg: str, preferred_bg: str, level: ContrastLevel = ContrastLevel.AA_NORMAL
    ) -> tuple[str, str]:
        """
        Get accessible color pair, adjusting if necessary.

        Args:
            preferred_fg: Preferred foreground color
            preferred_bg: Preferred background color
            level: WCAG contrast level requirement

        Returns:
            Tuple of (foreground, background) colors that meet requirements
        """
        if AccessibilityHelper.meets_contrast_requirement(preferred_fg, preferred_bg, level):
            return preferred_fg, preferred_bg

        # Try high contrast alternatives
        high_contrast_pairs = [
            ("#000000", "#FFFFFF"),  # Black on white
            ("#FFFFFF", "#000000"),  # White on black
            ("#0000FF", "#FFFFFF"),  # Blue on white
            ("#FFFFFF", "#0000FF"),  # White on blue
        ]

        for fg, bg in high_contrast_pairs:
            if AccessibilityHelper.meets_contrast_requirement(fg, bg, level):
                return fg, bg

        # Fallback to black on white
        return "#000000", "#FFFFFF"

    @staticmethod
    def generate_aria_label(
        element_type: str, content: str, state: str | None = None, position: str | None = None
    ) -> str:
        """
        Generate appropriate ARIA label for UI elements.

        Args:
            element_type: Type of element (button, input, etc.)
            content: Element content or purpose
            state: Current state (expanded, selected, etc.)
            position: Position information (1 of 5, etc.)

        Returns:
            ARIA label string
        """
        label_parts = []

        # Add element type context
        if element_type in ["button", "link"]:
            label_parts.append(content)
            if element_type == "button":
                label_parts.append("button")
        elif element_type == "input":
            label_parts.append(f"{content} input field")
        elif element_type == "heading":
            label_parts.append(f"{content} heading")
        elif element_type == "tab":
            label_parts.append(f"{content} tab")
        else:
            label_parts.append(content)

        # Add state information
        if state:
            if state == "expanded":
                label_parts.append("expanded")
            elif state == "collapsed":
                label_parts.append("collapsed")
            elif state == "selected":
                label_parts.append("selected")
            elif state == "disabled":
                label_parts.append("disabled")

        # Add position information
        if position:
            label_parts.append(position)

        return ", ".join(label_parts)

    @staticmethod
    def create_skip_link(target_id: str, text: str = "Skip to main content") -> str:
        """
        Create skip link for keyboard navigation.

        Args:
            target_id: ID of target element
            text: Skip link text

        Returns:
            HTML for skip link
        """
        return f"""
        <a href="#{target_id}" class="skip-link" 
           style="position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden;">
            {text}
        </a>
        """

    @staticmethod
    def add_focus_styles() -> str:
        """
        Add CSS for visible focus indicators.

        Returns:
            CSS styles for focus indicators
        """
        return """
        <style>
        /* Focus indicators for keyboard navigation */
        .stButton > button:focus,
        .stSelectbox > div > div:focus,
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stCheckbox > label:focus-within,
        .stRadio > div:focus-within {
            outline: 3px solid #005FCC !important;
            outline-offset: 2px !important;
            box-shadow: 0 0 0 3px rgba(0, 95, 204, 0.3) !important;
        }
        
        /* High contrast mode support */
        @media (prefers-contrast: high) {
            .stButton > button {
                border: 2px solid #000000 !important;
            }
            
            .stSelectbox > div > div,
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea {
                border: 2px solid #000000 !important;
            }
        }
        
        /* Reduced motion support */
        @media (prefers-reduced-motion: reduce) {
            * {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
        
        /* Responsive design support */
        @media (max-width: 768px) {
            .stButton > button {
                min-width: 100% !important;
                margin-bottom: 8px !important;
            }
        }
        
        /* Skip link styles */
        .skip-link:focus {
            position: absolute !important;
            left: 6px !important;
            top: 7px !important;
            width: auto !important;
            height: auto !important;
            padding: 8px 16px !important;
            background: #000000 !important;
            color: #FFFFFF !important;
            text-decoration: none !important;
            border-radius: 4px !important;
            z-index: 9999 !important;
        }
        
        /* Screen reader only text */
        .sr-only {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            padding: 0 !important;
            margin: -1px !important;
            overflow: hidden !important;
            clip: rect(0, 0, 0, 0) !important;
            white-space: nowrap !important;
            border: 0 !important;
        }
        </style>
        """


class KeyboardNavigation:
    """Keyboard navigation utilities."""

    @staticmethod
    def add_keyboard_shortcuts() -> str:
        """
        Add JavaScript for keyboard shortcuts.

        Returns:
            JavaScript code for keyboard navigation
        """
        return """
        <script>
        // Keyboard navigation support
        document.addEventListener('keydown', function(event) {
            // Alt + M: Skip to main content
            if (event.altKey && event.key === 'm') {
                const mainContent = document.getElementById('main-content');
                if (mainContent) {
                    mainContent.focus();
                    event.preventDefault();
                }
            }
            
            // Alt + N: Skip to navigation
            if (event.altKey && event.key === 'n') {
                const navigation = document.querySelector('[role="navigation"]');
                if (navigation) {
                    navigation.focus();
                    event.preventDefault();
                }
            }
            
            // Escape: Close modals/dropdowns
            if (event.key === 'Escape') {
                // Close any open dropdowns or modals
                const openElements = document.querySelectorAll('[aria-expanded="true"]');
                openElements.forEach(element => {
                    element.setAttribute('aria-expanded', 'false');
                });
            }
            
            // Track and manage activeElement for accessibility
            if (event.key === 'Tab') {
                setTimeout(() => {
                    const activeElement = document.activeElement;
                    if (activeElement && activeElement.tagName) {
                        activeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }, 10);
            }
            
            // Arrow key navigation for tab-like interfaces
            if (event.target.getAttribute('role') === 'tab') {
                let currentTab = event.target;
                let tabList = currentTab.closest('[role="tablist"]');
                let tabs = tabList.querySelectorAll('[role="tab"]');
                let currentIndex = Array.from(tabs).indexOf(currentTab);
                
                if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
                    let nextIndex = (currentIndex + 1) % tabs.length;
                    tabs[nextIndex].focus();
                    tabs[nextIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
                    event.preventDefault();
                } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
                    let prevIndex = (currentIndex - 1 + tabs.length) % tabs.length;
                    tabs[prevIndex].focus();
                    tabs[prevIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
                    event.preventDefault();
                }
            }
        });
        
        // Announce page changes to screen readers
        function announcePageChange(message) {
            const announcement = document.createElement('div');
            announcement.setAttribute('aria-live', 'polite');
            announcement.setAttribute('aria-atomic', 'true');
            announcement.className = 'sr-only';
            announcement.textContent = message;
            document.body.appendChild(announcement);
            
            setTimeout(() => {
                document.body.removeChild(announcement);
            }, 1000);
        }
        
        // Monitor for Streamlit page changes
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                    // Check if main content changed
                    const hasMainContent = Array.from(mutation.addedNodes).some(node => 
                        node.nodeType === 1 && (
                            node.querySelector && node.querySelector('[data-testid="stAppViewContainer"]')
                        )
                    );
                    
                    if (hasMainContent) {
                        announcePageChange('Page content updated');
                    }
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        </script>
        """

    @staticmethod
    def create_accessible_button(
        label: str, onclick: str, disabled: bool = False, aria_describedby: str | None = None
    ) -> str:
        """
        Create accessible button with proper ARIA attributes.

        Args:
            label: Button label
            onclick: JavaScript onclick handler
            disabled: Whether button is disabled
            aria_describedby: ID of element that describes the button

        Returns:
            HTML for accessible button
        """
        aria_attrs = []
        if aria_describedby:
            aria_attrs.append(f'aria-describedby="{aria_describedby}"')
        if disabled:
            aria_attrs.append('aria-disabled="true"')

        aria_str = " ".join(aria_attrs)
        disabled_str = "disabled" if disabled else ""

        return f"""
        <button type="button" 
                onclick="{onclick}"
                {disabled_str}
                {aria_str}
                class="accessible-button">
            {label}
        </button>
        """


class ScreenReaderSupport:
    """Screen reader support utilities."""

    @staticmethod
    def create_live_region(region_id: str, politeness: str = "polite") -> str:
        """
        Create ARIA live region for dynamic content announcements.

        Args:
            region_id: Unique ID for the live region
            politeness: ARIA live politeness level (polite, assertive, off)

        Returns:
            HTML for live region
        """
        return f"""
        <div id="{region_id}" 
             aria-live="{politeness}" 
             aria-atomic="true" 
             class="sr-only">
        </div>
        """

    @staticmethod
    def announce_to_screen_reader(message: str, region_id: str = "announcements") -> str:
        """
        Create JavaScript to announce message to screen readers.

        Args:
            message: Message to announce
            region_id: ID of live region to use

        Returns:
            JavaScript code to make announcement
        """
        return f"""
        <script>
        (function() {{
            const region = document.getElementById('{region_id}');
            if (region) {{
                region.textContent = '{message}';
                setTimeout(() => {{
                    region.textContent = '';
                }}, 1000);
            }}
        }})();
        </script>
        """

    @staticmethod
    def create_progress_announcement(current: int, total: int, task: str = "progress") -> str:
        """
        Create progress announcement for screen readers.

        Args:
            current: Current step/item
            total: Total steps/items
            task: Description of the task

        Returns:
            Announcement text
        """
        percentage = int((current / total) * 100) if total > 0 else 0
        return f"{task} {percentage}% complete, step {current} of {total}"


def apply_accessibility_features() -> None:
    """Apply accessibility features to Streamlit app."""
    # Add CSS for focus indicators and accessibility
    st.markdown(AccessibilityHelper.add_focus_styles(), unsafe_allow_html=True)

    # Add keyboard navigation JavaScript
    st.markdown(KeyboardNavigation.add_keyboard_shortcuts(), unsafe_allow_html=True)

    # Create live region for announcements
    st.markdown(ScreenReaderSupport.create_live_region("announcements"), unsafe_allow_html=True)

    # Add skip link
    st.markdown(
        AccessibilityHelper.create_skip_link("main-content", "Skip to main content"),
        unsafe_allow_html=True,
    )


def create_accessible_form_field(
    field_type: str,
    label: str,
    field_id: str,
    required: bool = False,
    help_text: str | None = None,
    error_message: str | None = None,
) -> dict[str, str]:
    """
    Create accessible form field with proper labels and ARIA attributes.

    Args:
        field_type: Type of field (text, email, password, etc.)
        label: Field label
        field_id: Unique field ID
        required: Whether field is required
        help_text: Optional help text
        error_message: Optional error message

    Returns:
        Dict with HTML components for the field
    """
    # Generate IDs for associated elements
    help_id = f"{field_id}-help" if help_text else None
    error_id = f"{field_id}-error" if error_message else None

    # Build aria-describedby
    described_by = []
    if help_id:
        described_by.append(help_id)
    if error_id:
        described_by.append(error_id)

    aria_describedby = " ".join(described_by) if described_by else None

    # Create label
    required_indicator = ' <span aria-label="required">*</span>' if required else ""
    label_html = f'<label for="{field_id}">{label}{required_indicator}</label>'

    # Create help text
    help_html = f'<div id="{help_id}" class="help-text">{help_text}</div>' if help_text else ""

    # Create error message
    error_html = (
        f'<div id="{error_id}" class="error-message" role="alert">{error_message}</div>'
        if error_message
        else ""
    )

    return {
        "label": label_html,
        "help": help_html,
        "error": error_html,
        "aria_describedby": aria_describedby,
        "field_id": field_id,
        "required": required,
    }


def check_color_contrast(foreground: str, background: str) -> dict[str, Any]:
    """
    Check color contrast and provide recommendations.

    Args:
        foreground: Foreground color in hex
        background: Background color in hex

    Returns:
        Dict with contrast information and recommendations
    """
    ratio = AccessibilityHelper.calculate_contrast_ratio(foreground, background)

    return {
        "ratio": ratio,
        "aa_normal": ratio >= 4.5,
        "aa_large": ratio >= 3.0,
        "aaa_normal": ratio >= 7.0,
        "aaa_large": ratio >= 4.5,
        "recommendation": "Pass" if ratio >= 4.5 else "Fail - needs improvement",
        "suggested_colors": (
            AccessibilityHelper.get_accessible_color_pair(
                foreground, background, ContrastLevel.AA_NORMAL
            )
            if ratio < 4.5
            else None
        ),
    }


# Global accessibility helper instance
accessibility_helper = AccessibilityHelper()
keyboard_navigation = KeyboardNavigation()
screen_reader_support = ScreenReaderSupport()
