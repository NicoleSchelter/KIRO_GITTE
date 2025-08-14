"""
Tooltip System for GITTE UI Components.
Provides context-sensitive tooltips with accessibility support.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List
from enum import Enum

import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)


class TooltipPosition(Enum):
    """Tooltip positioning options."""
    AUTO = "auto"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class TooltipTheme(Enum):
    """Tooltip theme options."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class TooltipContent:
    """Content structure for tooltips."""
    
    title: str
    description: str
    action_text: Optional[str] = None
    action_callback: Optional[Callable] = None
    help_link: Optional[str] = None
    accessibility_label: Optional[str] = None
    theme: TooltipTheme = TooltipTheme.DEFAULT
    position: TooltipPosition = TooltipPosition.AUTO
    show_delay_ms: int = 500
    hide_delay_ms: int = 200
    max_width: int = 300


@dataclass
class TooltipConfig:
    """Configuration for tooltip system."""
    
    enabled: bool = True
    default_show_delay_ms: int = 500
    default_hide_delay_ms: int = 200
    default_max_width: int = 300
    default_position: TooltipPosition = TooltipPosition.AUTO
    default_theme: TooltipTheme = TooltipTheme.DEFAULT
    css_injection_enabled: bool = True
    accessibility_enabled: bool = True


class TooltipRegistry:
    """Registry for managing tooltip content."""
    
    def __init__(self):
        """Initialize tooltip registry."""
        self._tooltips: Dict[str, TooltipContent] = {}
        self._context_processors: Dict[str, Callable] = {}
    
    def register(self, element_id: str, content: TooltipContent):
        """
        Register tooltip content for an element.
        
        Args:
            element_id: Unique identifier for the UI element
            content: Tooltip content configuration
        """
        self._tooltips[element_id] = content
        logger.debug(f"Registered tooltip for element: {element_id}")
    
    def register_context_processor(self, element_id: str, processor: Callable):
        """
        Register context processor for dynamic tooltip content.
        
        Args:
            element_id: Element identifier
            processor: Function that takes context and returns modified TooltipContent
        """
        self._context_processors[element_id] = processor
    
    def get(self, element_id: str, context: Optional[Dict[str, Any]] = None) -> Optional[TooltipContent]:
        """
        Get tooltip content for an element with optional context.
        
        Args:
            element_id: Element identifier
            context: Optional context for dynamic content
            
        Returns:
            TooltipContent or None if not found
        """
        base_tooltip = self._tooltips.get(element_id)
        if not base_tooltip:
            return None
        
        # Apply context processing if available
        if context and element_id in self._context_processors:
            try:
                processor = self._context_processors[element_id]
                return processor(base_tooltip, context)
            except Exception as e:
                logger.error(f"Error processing tooltip context for {element_id}: {e}")
        
        return base_tooltip
    
    def list_registered(self) -> List[str]:
        """Get list of registered element IDs."""
        return list(self._tooltips.keys())
    
    def unregister(self, element_id: str) -> bool:
        """
        Unregister tooltip for an element.
        
        Args:
            element_id: Element identifier
            
        Returns:
            True if element was registered, False otherwise
        """
        if element_id in self._tooltips:
            del self._tooltips[element_id]
            if element_id in self._context_processors:
                del self._context_processors[element_id]
            logger.debug(f"Unregistered tooltip for element: {element_id}")
            return True
        return False


class TooltipRenderer:
    """Renders tooltips in various formats."""
    
    def __init__(self, config: TooltipConfig):
        """
        Initialize tooltip renderer.
        
        Args:
            config: Tooltip system configuration
        """
        self.config = config
    
    def render_html(self, content: TooltipContent, element_id: str) -> str:
        """
        Render tooltip as HTML.
        
        Args:
            content: Tooltip content
            element_id: Element identifier for CSS targeting
            
        Returns:
            HTML string for tooltip
        """
        if not self.config.enabled:
            return ""
        
        # Build CSS classes
        css_classes = [
            "gitte-tooltip",
            f"tooltip-{content.theme.value}",
            f"tooltip-{content.position.value}"
        ]
        
        # Accessibility attributes
        aria_attrs = ""
        if self.config.accessibility_enabled:
            aria_label = content.accessibility_label or content.title
            aria_attrs = f'role="tooltip" aria-label="{aria_label}" tabindex="0"'
        
        # Build tooltip HTML
        html = f"""
        <div class="{' '.join(css_classes)}" 
             id="tooltip-{element_id}"
             {aria_attrs}
             style="max-width: {content.max_width}px;">
            <div class="tooltip-header">
                <span class="tooltip-title">{content.title}</span>
            </div>
            <div class="tooltip-body">
                <p class="tooltip-description">{content.description}</p>
                {self._render_action_section(content)}
                {self._render_help_link(content)}
            </div>
        </div>
        """
        
        return html.strip()
    
    def _render_action_section(self, content: TooltipContent) -> str:
        """Render action section of tooltip."""
        if not content.action_text:
            return ""
        
        return f"""
        <div class="tooltip-action">
            <span class="action-text">{content.action_text}</span>
        </div>
        """
    
    def _render_help_link(self, content: TooltipContent) -> str:
        """Render help link section of tooltip."""
        if not content.help_link:
            return ""
        
        return f"""
        <div class="tooltip-help">
            <a href="{content.help_link}" 
               class="help-link" 
               target="_blank" 
               rel="noopener noreferrer">
                Learn more →
            </a>
        </div>
        """
    
    def render_streamlit_help(self, content: TooltipContent) -> str:
        """
        Render tooltip content as Streamlit help text.
        
        Args:
            content: Tooltip content
            
        Returns:
            Formatted help text for Streamlit components
        """
        if not self.config.enabled:
            return ""
        
        help_parts = [content.description]
        
        if content.action_text:
            help_parts.append(f"💡 {content.action_text}")
        
        if content.help_link:
            help_parts.append(f"📖 Learn more: {content.help_link}")
        
        return " | ".join(help_parts)


class TooltipSystem:
    """Main tooltip system coordinator."""
    
    def __init__(self, config: Optional[TooltipConfig] = None):
        """
        Initialize tooltip system.
        
        Args:
            config: Optional configuration, uses defaults if not provided
        """
        self.config = config or TooltipConfig()
        self.registry = TooltipRegistry()
        self.renderer = TooltipRenderer(self.config)
        self._css_injected = False
        
        # Initialize default tooltips
        self._initialize_default_tooltips()
    
    def register_tooltip(self, element_id: str, content: TooltipContent):
        """
        Register tooltip content for an element.
        
        Args:
            element_id: Unique identifier for UI element
            content: Tooltip content configuration
        """
        self.registry.register(element_id, content)
    
    def get_tooltip(self, element_id: str, context: Optional[Dict[str, Any]] = None) -> Optional[TooltipContent]:
        """
        Get tooltip content for an element.
        
        Args:
            element_id: Element identifier
            context: Optional context for dynamic content
            
        Returns:
            TooltipContent or None if not found
        """
        return self.registry.get(element_id, context)
    
    def render_tooltip_html(self, element_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render tooltip as HTML for an element.
        
        Args:
            element_id: Element identifier
            context: Optional context
            
        Returns:
            HTML string for tooltip
        """
        content = self.get_tooltip(element_id, context)
        if not content:
            return ""
        
        return self.renderer.render_html(content, element_id)
    
    def get_streamlit_help(self, element_id: str, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get help text for Streamlit component.
        
        Args:
            element_id: Element identifier
            context: Optional context
            
        Returns:
            Help text string or None
        """
        content = self.get_tooltip(element_id, context)
        if not content:
            return None
        
        return self.renderer.render_streamlit_help(content)
    
    def inject_css(self):
        """Inject CSS styles for tooltips into Streamlit."""
        if not self.config.css_injection_enabled or self._css_injected:
            return
        
        css = self._generate_tooltip_css()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        self._css_injected = True
        logger.debug("Tooltip CSS injected into Streamlit")
    
    def _generate_tooltip_css(self) -> str:
        """Generate CSS styles for tooltips."""
        return """
        /* GITTE Tooltip Styles */
        .gitte-tooltip {
            background: #333;
            color: white;
            padding: 12px;
            border-radius: 6px;
            font-size: 14px;
            line-height: 1.4;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 1000;
            position: relative;
            border: 1px solid #555;
        }
        
        .gitte-tooltip.tooltip-dark {
            background: #1a1a1a;
            color: #f0f0f0;
            border-color: #333;
        }
        
        .gitte-tooltip.tooltip-light {
            background: #ffffff;
            color: #333333;
            border-color: #ddd;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .gitte-tooltip.tooltip-success {
            background: #4CAF50;
            color: white;
            border-color: #45a049;
        }
        
        .gitte-tooltip.tooltip-warning {
            background: #ff9800;
            color: white;
            border-color: #f57c00;
        }
        
        .gitte-tooltip.tooltip-error {
            background: #f44336;
            color: white;
            border-color: #d32f2f;
        }
        
        .tooltip-header {
            margin-bottom: 8px;
        }
        
        .tooltip-title {
            font-weight: 600;
            font-size: 15px;
        }
        
        .tooltip-body {
            margin: 0;
        }
        
        .tooltip-description {
            margin: 0 0 8px 0;
            font-size: 14px;
        }
        
        .tooltip-action {
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid rgba(255,255,255,0.2);
        }
        
        .action-text {
            font-style: italic;
            font-size: 13px;
            opacity: 0.9;
        }
        
        .tooltip-help {
            margin-top: 8px;
        }
        
        .help-link {
            color: #81C784;
            text-decoration: none;
            font-size: 13px;
            font-weight: 500;
        }
        
        .help-link:hover {
            color: #A5D6A7;
            text-decoration: underline;
        }
        
        /* Accessibility improvements */
        .gitte-tooltip:focus {
            outline: 2px solid #4CAF50;
            outline-offset: 2px;
        }
        
        /* Responsive design */
        @media (max-width: 768px) {
            .gitte-tooltip {
                max-width: 280px !important;
                font-size: 13px;
            }
        }
        """
    
    def _initialize_default_tooltips(self):
        """Initialize default tooltips for common GITTE elements."""
        default_tooltips = {
            "register_button": TooltipContent(
                title="Create Account",
                description="Register to access personalized learning features and save your progress",
                action_text="Complete all required fields to enable registration",
                accessibility_label="Registration button - complete form to enable"
            ),
            
            "consent_checkbox": TooltipContent(
                title="Data Processing Consent",
                description="Required to use AI features like chat and image generation. Your data is processed securely and never shared.",
                action_text="Check this box to provide consent and unlock AI features",
                help_link="/privacy-policy",
                accessibility_label="Consent checkbox - required for AI features"
            ),
            
            "image_generation_button": TooltipContent(
                title="Generate Avatar",
                description="Create a visual representation of your learning assistant based on your preferences",
                action_text="Complete embodiment design and provide consent first",
                accessibility_label="Avatar generation button - requires setup completion"
            ),
            
            "chat_input": TooltipContent(
                title="Chat with GITTE",
                description="Interact with your personalized learning assistant. Ask questions, get explanations, or request help with topics",
                action_text="Complete registration and consent to start chatting",
                accessibility_label="Chat input field - requires account setup"
            ),
            
            "embodiment_form": TooltipContent(
                title="Design Your Assistant",
                description="Customize the appearance and personality of your learning assistant to match your preferences",
                action_text="Fill out the form to define your assistant's characteristics",
                accessibility_label="Embodiment design form"
            ),
            
            "save_button": TooltipContent(
                title="Save Changes",
                description="Save your current settings and preferences to your account",
                action_text="Make changes to enable saving",
                theme=TooltipTheme.SUCCESS,
                accessibility_label="Save button - saves current changes"
            ),
            
            "delete_button": TooltipContent(
                title="Delete Item",
                description="Permanently remove this item. This action cannot be undone.",
                action_text="Click to confirm deletion",
                theme=TooltipTheme.ERROR,
                accessibility_label="Delete button - permanent action"
            ),
            
            "help_button": TooltipContent(
                title="Get Help",
                description="Access documentation, tutorials, and support resources",
                action_text="Click to open help documentation and support",
                help_link="/help",
                accessibility_label="Help button - opens support resources"
            )
        }
        
        for element_id, content in default_tooltips.items():
            self.registry.register(element_id, content)
        
        logger.info(f"Initialized {len(default_tooltips)} default tooltips")
    
    def register_context_processor(self, element_id: str, processor: Callable):
        """
        Register context processor for dynamic tooltip content.
        
        Args:
            element_id: Element identifier
            processor: Function that modifies tooltip based on context
        """
        self.registry.register_context_processor(element_id, processor)
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get statistics about the tooltip system."""
        return {
            "enabled": self.config.enabled,
            "registered_tooltips": len(self.registry.list_registered()),
            "css_injected": self._css_injected,
            "accessibility_enabled": self.config.accessibility_enabled,
            "registered_elements": self.registry.list_registered()
        }


# Context processors for common scenarios
def disabled_element_processor(base_tooltip: TooltipContent, context: Dict[str, Any]) -> TooltipContent:
    """
    Context processor for disabled elements.
    
    Args:
        base_tooltip: Base tooltip content
        context: Context containing 'disabled' and 'reason' keys
        
    Returns:
        Modified tooltip content
    """
    if not context.get("disabled", False):
        return base_tooltip
    
    # Create modified tooltip for disabled state
    modified = TooltipContent(
        title=base_tooltip.title,
        description=f"{base_tooltip.description}",
        action_text=context.get("reason", "This feature is currently disabled"),
        theme=TooltipTheme.WARNING,
        accessibility_label=f"{base_tooltip.accessibility_label} - disabled: {context.get('reason', 'unknown reason')}"
    )
    
    return modified


def form_validation_processor(base_tooltip: TooltipContent, context: Dict[str, Any]) -> TooltipContent:
    """
    Context processor for form validation states.
    
    Args:
        base_tooltip: Base tooltip content
        context: Context containing validation information
        
    Returns:
        Modified tooltip content
    """
    validation_errors = context.get("validation_errors", [])
    is_valid = context.get("is_valid", True)
    
    if is_valid and not validation_errors:
        return base_tooltip
    
    # Create validation-aware tooltip
    error_text = "; ".join(validation_errors) if validation_errors else "Please check your input"
    
    modified = TooltipContent(
        title=base_tooltip.title,
        description=base_tooltip.description,
        action_text=f"Validation issues: {error_text}",
        theme=TooltipTheme.ERROR,
        accessibility_label=f"{base_tooltip.accessibility_label} - validation errors present"
    )
    
    return modified


# Global tooltip system instance
_tooltip_system = None


def get_tooltip_system(config: Optional[TooltipConfig] = None) -> TooltipSystem:
    """
    Get global tooltip system instance.
    
    Args:
        config: Optional configuration for first initialization
        
    Returns:
        TooltipSystem instance
    """
    global _tooltip_system
    
    if _tooltip_system is None:
        _tooltip_system = TooltipSystem(config)
    
    return _tooltip_system