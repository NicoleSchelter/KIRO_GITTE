"""
Tooltip integration for GITTE system - KORRIGIERTE VERSION
Provides tooltip functionality without key parameter conflicts.
"""

import logging
from datetime import datetime
from typing import Any, Optional, Callable

import streamlit as st

logger = logging.getLogger(__name__)


class TooltipIntegration:
    """Manages tooltip integration and form validation without key parameter issues."""

    def __init__(self):
        self.tooltips = {}
        self.button_states = {}
        if 'tooltip_integration_initialized' not in st.session_state:
            st.session_state.tooltip_integration_initialized = True

    def register_tooltip(self, tooltip_id: str, text: str) -> None:
        """Register tooltip text for an ID."""
        self.tooltips[tooltip_id] = text

    def get_tooltip_text(self, tooltip_id: str) -> Optional[str]:
        """Get tooltip text for an ID."""
        return self.tooltips.get(tooltip_id, None)

    def form_button_with_validation(
        self,
        label: str,
        tooltip_id: str,
        form_valid: bool = True,
        disabled: Optional[bool] = None,
        help: Optional[str] = None,
        button_type: str = "primary",
        on_click: Optional[Callable] = None,
        **kwargs
    ) -> bool:
        """
        Create form submit button with validation - OHNE key parameter.
        
        Args:
            label: Button text
            tooltip_id: Unique identifier for tooltip and tracking
            form_valid: Whether form validation passed
            disabled: Manual disable state
            help: Help text (overrides tooltip)
            button_type: Button type
            on_click: Callback function
            **kwargs: Additional parameters for st.form_submit_button
            
        Returns:
            bool: True if button was clicked
        """
        
        # Get tooltip text if no help provided
        tooltip_help = help or self.get_tooltip_text(tooltip_id)
        
        # Compute disabled state (manual disabled or validation failed)
        is_disabled = (disabled is True) or (not form_valid)
        
        # Determine button type based on validation
        resolved_type = "secondary" if not form_valid else button_type
        
        # Prepare parameters for st.form_submit_button (OHNE key parameter!)
        button_params = {
            'label': label,
            'type': resolved_type,
            'disabled': is_disabled
        }
        
        # Add help text if available
        if tooltip_help:
            button_params['help'] = tooltip_help
            
        # Add callback if provided
        if on_click:
            button_params['on_click'] = on_click
            
        # Add other allowed parameters
        allowed_params = ['args', 'kwargs', 'icon', 'use_container_width', 'width']
        for param in allowed_params:
            if param in kwargs:
                button_params[param] = kwargs[param]
        
        try:
            # Create submit button WITHOUT key parameter
            submitted = st.form_submit_button(**button_params)
            
            # Track button state manually in session state
            if submitted:
                button_state_key = f"button_clicked_{tooltip_id}"
                st.session_state[button_state_key] = {
                    'clicked': True,
                    'tooltip_id': tooltip_id,
                    'timestamp': datetime.now(),
                    'form_valid': form_valid,
                    'label': label
                }
                
                logger.info(f"Form button clicked: {tooltip_id} (valid: {form_valid})")
            
            return submitted
            
        except Exception as e:
            logger.error(f"Error creating form submit button {tooltip_id}: {e}")
            # Fallback button with minimal parameters
            return st.form_submit_button(label=label, disabled=is_disabled)

    def get_button_state(self, tooltip_id: str) -> Optional[dict]:
        """Get the last state of a button by tooltip_id."""
        button_state_key = f"button_clicked_{tooltip_id}"
        return st.session_state.get(button_state_key, None)

    def clear_button_state(self, tooltip_id: str) -> None:
        """Clear button state for tooltip_id."""
        button_state_key = f"button_clicked_{tooltip_id}"
        if button_state_key in st.session_state:
            del st.session_state[button_state_key]

    def was_button_clicked(self, tooltip_id: str) -> bool:
        """Check if a specific button was clicked in this session."""
        state = self.get_button_state(tooltip_id)
        return state is not None and state.get('clicked', False)


# Global tooltip integration instance
_tooltip_integration_instance = None

# In src/ui/tooltip_integration.py

def get_tooltip_integration() -> TooltipIntegration:
    """Get global tooltip integration instance."""
    global _tooltip_integration_instance
    if _tooltip_integration_instance is None:
        _tooltip_integration_instance = TooltipIntegration()
    return _tooltip_integration_instance

def tooltip_input(label, tooltip, *args, **kwargs):
    """
    Wrapper for streamlit.text_input with tooltip support.
    """
    st.markdown(f"**{label}**  \n<span style='font-size:smaller;color:gray'>{tooltip}</span>", unsafe_allow_html=True)
    return st.text_input("", *args, **kwargs)
    
def tooltip_button(label, tooltip, *args, **kwargs):
    """Button mit Tooltip."""
    st.markdown(f"**{label}**  \n<span style='font-size:smaller;color:gray'>{tooltip}</span>", unsafe_allow_html=True)
    return st.button("", *args, **kwargs)



def tooltip_checkbox(label, tooltip, *args, **kwargs):
    st.markdown(f"{label} <span style='font-size:smaller;color:gray'>{tooltip}</span>", unsafe_allow_html=True)
    return st.checkbox("", *args, **kwargs)

def tooltip_selectbox(label, tooltip, options, *args, **kwargs):
    st.markdown(f"{label} <span style='font-size:smaller;color:gray'>{tooltip}</span>", unsafe_allow_html=True)
    return st.selectbox("", options, *args, **kwargs)

def form_submit_button(
    label: str,
    tooltip_id: str,
    form_valid: bool = True,
    disabled: Optional[bool] = None,
    help: Optional[str] = None,
    **kwargs
) -> bool:
    """
    Global wrapper function for form submit buttons with validation.
    KORRIGIERTE VERSION - ohne key parameter.
    """
    return get_tooltip_integration().form_button_with_validation(
        label=label,
        tooltip_id=tooltip_id,
        form_valid=form_valid,
        disabled=disabled,
        help=help,
        **kwargs
    )


def register_tooltip(tooltip_id: str, text: str) -> None:
    """Register a tooltip globally."""
    get_tooltip_integration().register_tooltip(tooltip_id, text)


def get_tooltip_text(tooltip_id: str) -> Optional[str]:
    """Get tooltip text globally."""
    return get_tooltip_integration().get_tooltip_text(tooltip_id)
