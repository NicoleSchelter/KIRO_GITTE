"""
Streamlit Integration for GITTE Tooltip System.
Provides helper functions to integrate tooltips with Streamlit components.
"""

import logging
from typing import Any, Dict, Optional, Callable
from uuid import UUID

import streamlit as st

from src.ui.tooltip_content_manager import get_tooltip_content_manager
from src.ui.tooltip_system import get_tooltip_system

logger = logging.getLogger(__name__)


class StreamlitTooltipIntegration:
    """Integration layer between GITTE tooltip system and Streamlit components."""
    
    def __init__(self):
        """Initialize tooltip integration."""
        self.tooltip_manager = get_tooltip_content_manager()
        self.tooltip_system = get_tooltip_system()
        
        # Inject CSS on first use
        self.tooltip_system.inject_css()
    
    def button_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        disabled: bool = False,
        context: Optional[Dict[str, Any]] = None,
        **button_kwargs
    ) -> bool:
        """
        Render Streamlit button with integrated tooltip.
        
        Args:
            label: Button label text
            tooltip_id: Tooltip identifier
            disabled: Whether button is disabled
            context: Optional context for dynamic tooltips
            **button_kwargs: Additional arguments for st.button
            
        Returns:
            True if button was clicked
        """
        # Build context for disabled state
        tooltip_context = context or {}
        if disabled:
            tooltip_context.update({
                "disabled": True,
                "reason": tooltip_context.get("reason", "Prerequisites not met")
            })
        
        # Get tooltip help text
        help_text = self.tooltip_manager.get_tooltip_for_element(tooltip_id, tooltip_context)
        
        # Render button with tooltip
        return st.button(
            label,
            disabled=disabled,
            help=help_text,
            **button_kwargs
        )
    
    def text_input_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        value: str = "",
        context: Optional[Dict[str, Any]] = None,
        **input_kwargs
    ) -> str:
        """
        Render Streamlit text input with integrated tooltip.
        
        Args:
            label: Input label text
            tooltip_id: Tooltip identifier
            value: Default value
            context: Optional context for dynamic tooltips
            **input_kwargs: Additional arguments for st.text_input
            
        Returns:
            Input value
        """
        help_text = self.tooltip_manager.get_tooltip_for_element(tooltip_id, context)
        
        return st.text_input(
            label,
            value=value,
            help=help_text,
            **input_kwargs
        )
    
    def text_area_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        value: str = "",
        context: Optional[Dict[str, Any]] = None,
        **textarea_kwargs
    ) -> str:
        """
        Render Streamlit text area with integrated tooltip.
        
        Args:
            label: Text area label
            tooltip_id: Tooltip identifier
            value: Default value
            context: Optional context for dynamic tooltips
            **textarea_kwargs: Additional arguments for st.text_area
            
        Returns:
            Text area value
        """
        help_text = self.tooltip_manager.get_tooltip_for_element(tooltip_id, context)
        
        return st.text_area(
            label,
            value=value,
            help=help_text,
            **textarea_kwargs
        )
    
    def selectbox_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        options: list,
        index: int = 0,
        context: Optional[Dict[str, Any]] = None,
        **selectbox_kwargs
    ) -> Any:
        """
        Render Streamlit selectbox with integrated tooltip.
        
        Args:
            label: Selectbox label
            tooltip_id: Tooltip identifier
            options: List of options
            index: Default selected index
            context: Optional context for dynamic tooltips
            **selectbox_kwargs: Additional arguments for st.selectbox
            
        Returns:
            Selected value
        """
        help_text = self.tooltip_manager.get_tooltip_for_element(tooltip_id, context)
        
        return st.selectbox(
            label,
            options=options,
            index=index,
            help=help_text,
            **selectbox_kwargs
        )
    
    def checkbox_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        value: bool = False,
        context: Optional[Dict[str, Any]] = None,
        **checkbox_kwargs
    ) -> bool:
        """
        Render Streamlit checkbox with integrated tooltip.
        
        Args:
            label: Checkbox label
            tooltip_id: Tooltip identifier
            value: Default checked state
            context: Optional context for dynamic tooltips
            **checkbox_kwargs: Additional arguments for st.checkbox
            
        Returns:
            Checkbox state
        """
        help_text = self.tooltip_manager.get_tooltip_for_element(tooltip_id, context)
        
        return st.checkbox(
            label,
            value=value,
            help=help_text,
            **checkbox_kwargs
        )
    
    def slider_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        min_value: float,
        max_value: float,
        value: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        **slider_kwargs
    ) -> float:
        """
        Render Streamlit slider with integrated tooltip.
        
        Args:
            label: Slider label
            tooltip_id: Tooltip identifier
            min_value: Minimum value
            max_value: Maximum value
            value: Default value
            context: Optional context for dynamic tooltips
            **slider_kwargs: Additional arguments for st.slider
            
        Returns:
            Slider value
        """
        help_text = self.tooltip_manager.get_tooltip_for_element(tooltip_id, context)
        
        return st.slider(
            label,
            min_value=min_value,
            max_value=max_value,
            value=value,
            help=help_text,
            **slider_kwargs
        )
    
    def multiselect_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        options: list,
        default: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
        **multiselect_kwargs
    ) -> list:
        """
        Render Streamlit multiselect with integrated tooltip.
        
        Args:
            label: Multiselect label
            tooltip_id: Tooltip identifier
            options: List of options
            default: Default selected values
            context: Optional context for dynamic tooltips
            **multiselect_kwargs: Additional arguments for st.multiselect
            
        Returns:
            List of selected values
        """
        help_text = self.tooltip_manager.get_tooltip_for_element(tooltip_id, context)
        
        return st.multiselect(
            label,
            options=options,
            default=default or [],
            help=help_text,
            **multiselect_kwargs
        )
    
    def consent_checkbox_with_context(
        self,
        label: str,
        tooltip_id: str,
        user_id: UUID,
        consent_type: str,
        value: bool = False,
        **checkbox_kwargs
    ) -> bool:
        """
        Render consent checkbox with context-aware tooltip.
        
        Args:
            label: Checkbox label
            tooltip_id: Tooltip identifier
            user_id: User identifier
            consent_type: Type of consent
            value: Current consent state
            **checkbox_kwargs: Additional arguments for st.checkbox
            
        Returns:
            Checkbox state
        """
        # Build consent-specific context
        context = {
            "consent_granted": value,
            "consent_type": consent_type,
            "dependent_features": self._get_dependent_features(consent_type)
        }
        
        return self.checkbox_with_tooltip(
            label,
            tooltip_id,
            value=value,
            context=context,
            **checkbox_kwargs
        )
    
    def form_button_with_validation(
        self,
        label: str,
        tooltip_id: str,
        form_valid: bool,
        validation_errors: Optional[list] = None,
        **button_kwargs
    ) -> bool:
        """
        Render form submit button with validation-aware tooltip.
        
        Args:
            label: Button label
            tooltip_id: Tooltip identifier
            form_valid: Whether form is valid
            validation_errors: List of validation error messages
            **button_kwargs: Additional arguments for st.button
            
        Returns:
            True if button was clicked
        """
        context = {
            "disabled": not form_valid,
            "is_valid": form_valid,
            "validation_errors": validation_errors or [],
            "reason": "Complete required fields" if not form_valid else None
        }
        
        return self.button_with_tooltip(
            label,
            tooltip_id,
            disabled=not form_valid,
            context=context,
            **button_kwargs
        )
    
    def prerequisite_button(
        self,
        label: str,
        tooltip_id: str,
        prerequisites_met: bool,
        missing_prerequisites: Optional[list] = None,
        **button_kwargs
    ) -> bool:
        """
        Render button that requires prerequisites with informative tooltip.
        
        Args:
            label: Button label
            tooltip_id: Tooltip identifier
            prerequisites_met: Whether all prerequisites are satisfied
            missing_prerequisites: List of missing prerequisite names
            **button_kwargs: Additional arguments for st.button
            
        Returns:
            True if button was clicked
        """
        context = {
            "disabled": not prerequisites_met,
            "prerequisites_met": prerequisites_met,
            "missing_prerequisites": missing_prerequisites or [],
            "reason": f"Missing: {', '.join(missing_prerequisites or [])}" if not prerequisites_met else None
        }
        
        return self.button_with_tooltip(
            label,
            tooltip_id,
            disabled=not prerequisites_met,
            context=context,
            **button_kwargs
        )
    
    def _get_dependent_features(self, consent_type: str) -> list:
        """
        Get list of features that depend on a consent type.
        
        Args:
            consent_type: Type of consent
            
        Returns:
            List of dependent feature names
        """
        dependency_map = {
            "data_processing": ["Account creation", "Profile management"],
            "llm_interaction": ["Chat with assistant", "AI responses"],
            "image_generation": ["Avatar creation", "Visual customization"],
            "analytics": ["Usage insights", "Performance optimization"],
            "federated_learning": ["Model improvement", "Collaborative learning"]
        }
        
        return dependency_map.get(consent_type, [])
    
    def render_tooltip_help_section(self, element_ids: list) -> None:
        """
        Render a help section showing tooltips for multiple elements.
        
        Args:
            element_ids: List of element IDs to show help for
        """
        with st.expander("💡 Help & Tooltips", expanded=False):
            st.write("**Available help for this page:**")
            
            for element_id in element_ids:
                tooltip_content = self.tooltip_system.get_tooltip(element_id)
                if tooltip_content:
                    st.write(f"**{tooltip_content.title}**")
                    st.write(tooltip_content.description)
                    if tooltip_content.action_text:
                        st.info(f"💡 {tooltip_content.action_text}")
                    st.write("---")
    
    def validate_page_tooltip_coverage(self, page_elements: list) -> None:
        """
        Validate and report tooltip coverage for a page.
        
        Args:
            page_elements: List of element IDs on the page
        """
        if st.sidebar.button("🔍 Check Tooltip Coverage", help="Validate tooltip coverage for this page"):
            coverage = self.tooltip_manager.validate_tooltip_coverage(page_elements)
            
            st.sidebar.write("**Tooltip Coverage Report**")
            st.sidebar.metric("Coverage", f"{coverage['coverage_percentage']:.1f}%")
            st.sidebar.write(f"Covered: {coverage['covered_elements']}/{coverage['total_elements']}")
            
            if coverage['missing']:
                st.sidebar.warning(f"Missing tooltips: {', '.join(coverage['missing'])}")
            else:
                st.sidebar.success("All elements have tooltips!")


# Global integration instance
_tooltip_integration = None


def get_tooltip_integration() -> StreamlitTooltipIntegration:
    """
    Get global tooltip integration instance.
    
    Returns:
        StreamlitTooltipIntegration instance
    """
    global _tooltip_integration
    
    if _tooltip_integration is None:
        _tooltip_integration = StreamlitTooltipIntegration()
    
    return _tooltip_integration


# Convenience functions for common use cases
def tooltip_button(label: str, tooltip_id: str, **kwargs) -> bool:
    """Render button with tooltip."""
    return get_tooltip_integration().button_with_tooltip(label, tooltip_id, **kwargs)


def tooltip_input(label: str, tooltip_id: str, **kwargs) -> str:
    """Render text input with tooltip."""
    return get_tooltip_integration().text_input_with_tooltip(label, tooltip_id, **kwargs)


def tooltip_checkbox(label: str, tooltip_id: str, **kwargs) -> bool:
    """Render checkbox with tooltip."""
    return get_tooltip_integration().checkbox_with_tooltip(label, tooltip_id, **kwargs)


def tooltip_selectbox(label: str, tooltip_id: str, options: list, **kwargs) -> Any:
    """Render selectbox with tooltip."""
    return get_tooltip_integration().selectbox_with_tooltip(label, tooltip_id, options, **kwargs)


def consent_checkbox(label: str, tooltip_id: str, user_id: UUID, consent_type: str, **kwargs) -> bool:
    """Render consent checkbox with context-aware tooltip."""
    return get_tooltip_integration().consent_checkbox_with_context(
        label, tooltip_id, user_id, consent_type, **kwargs
    )


def form_submit_button(label: str, tooltip_id: str, form_valid: bool, **kwargs) -> bool:
    """Render form submit button with validation tooltip."""
    return get_tooltip_integration().form_button_with_validation(
        label, tooltip_id, form_valid, **kwargs
    )


def prerequisite_button(label: str, tooltip_id: str, prerequisites_met: bool, **kwargs) -> bool:
    """Render button with prerequisite checking tooltip."""
    return get_tooltip_integration().prerequisite_button(
        label, tooltip_id, prerequisites_met, **kwargs
    )