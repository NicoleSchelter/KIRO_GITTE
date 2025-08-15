# src/ui/tooltip_integration.py
"""
Streamlit Integration for GITTE Tooltip System.
Provides helper functions to integrate tooltips with Streamlit components.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, List
from uuid import UUID

import streamlit as st

from src.ui.tooltip_content_manager import get_tooltip_content_manager
from src.ui.tooltip_system import get_tooltip_system

logger = logging.getLogger(__name__)


class StreamlitTooltipIntegration:
    """Integration layer between GITTE tooltip system and Streamlit components."""

    def __init__(self):
        self.tooltip_manager = get_tooltip_content_manager()
        self.tooltip_system = get_tooltip_system()
        self._css_injected = False

    # -------- internal --------
    def _ensure_css_injected(self) -> None:
        if not self._css_injected:
            try:
                self.tooltip_system.inject_css()
            except Exception:
                # Never let tooltips break the UI
                pass
            self._css_injected = True

    def _help_text(self, tooltip_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        try:
            return self.tooltip_manager.get_tooltip_for_element(tooltip_id, context or {})
        except Exception:
            return None

    # -------- basic widgets --------
    def button_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        disabled: bool = False,
        context: Optional[Dict[str, Any]] = None,
        **button_kwargs,
    ) -> bool:
        self._ensure_css_injected()
        help_text = self._help_text(tooltip_id, context)
        # Avoid conflicting help kwarg
        if "help" in button_kwargs:
            button_kwargs.pop("help")
        return st.button(label, disabled=disabled, help=help_text, **button_kwargs)

    def text_input_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        value: str = "",
        context: Optional[Dict[str, Any]] = None,
        **input_kwargs,
    ) -> str:
        self._ensure_css_injected()
        help_text = self._help_text(tooltip_id, context)
        input_kwargs.pop("help", None)
        return st.text_input(label, value=value, help=help_text, **input_kwargs)

    def text_area_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        value: str = "",
        context: Optional[Dict[str, Any]] = None,
        **textarea_kwargs,
    ) -> str:
        self._ensure_css_injected()
        help_text = self._help_text(tooltip_id, context)
        textarea_kwargs.pop("help", None)
        return st.text_area(label, value=value, help=help_text, **textarea_kwargs)

    def selectbox_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        options: list,
        index: int = 0,
        context: Optional[Dict[str, Any]] = None,
        **selectbox_kwargs,
    ) -> Any:
        self._ensure_css_injected()
        help_text = self._help_text(tooltip_id, context)
        selectbox_kwargs.pop("help", None)
        return st.selectbox(label, options=options, index=index, help=help_text, **selectbox_kwargs)

    def checkbox_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        value: bool = False,
        context: Optional[Dict[str, Any]] = None,
        **checkbox_kwargs,
    ) -> bool:
        self._ensure_css_injected()
        help_text = self._help_text(tooltip_id, context)
        checkbox_kwargs.pop("help", None)
        return st.checkbox(label, value=value, help=help_text, **checkbox_kwargs)

    def multiselect_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        options: list,
        default: Optional[list] = None,
        context: Optional[Dict[str, Any]] = None,
        **multiselect_kwargs,
    ) -> list:
        self._ensure_css_injected()
        help_text = self._help_text(tooltip_id, context)
        multiselect_kwargs.pop("help", None)
        return st.multiselect(label, options=options, default=default or [], help=help_text, **multiselect_kwargs)

    def slider_with_tooltip(
        self,
        label: str,
        tooltip_id: str,
        min_value: float,
        max_value: float,
        value: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        **slider_kwargs,
    ) -> float:
        self._ensure_css_injected()
        help_text = self._help_text(tooltip_id, context)
        slider_kwargs.pop("help", None)
        return st.slider(label, min_value=min_value, max_value=max_value, value=value, help=help_text, **slider_kwargs)

    # -------- consent/prereq helpers --------
    def consent_checkbox_with_context(
        self,
        label: str,
        tooltip_id: str,
        user_id: UUID,
        consent_type: str,
        value: bool = False,
        **checkbox_kwargs,
    ) -> bool:
        context = {
            "consent_granted": value,
            "consent_type": consent_type,
            "dependent_features": self._get_dependent_features(consent_type),
        }
        return self.checkbox_with_tooltip(label, tooltip_id, value=value, context=context, **checkbox_kwargs)

    def prerequisite_button(
        self,
        label: str,
        tooltip_id: str,
        prerequisites_met: bool,
        missing_prerequisites: Optional[list] = None,
        **button_kwargs,
    ) -> bool:
        context = {
            "disabled": not prerequisites_met,
            "prerequisites_met": prerequisites_met,
            "missing_prerequisites": missing_prerequisites or [],
            "reason": f"Missing: {', '.join(missing_prerequisites or [])}" if not prerequisites_met else None,
        }
        return self.button_with_tooltip(
            label,
            tooltip_id,
            disabled=not prerequisites_met,
            context=context,
            **button_kwargs,
        )

    def _get_dependent_features(self, consent_type: str) -> list:
        dependency_map = {
            "data_processing": ["Account creation", "Profile management"],
            "llm_interaction": ["Chat with assistant", "AI responses"],
            "image_generation": ["Avatar creation", "Visual customization"],
            "analytics": ["Usage insights", "Performance optimization"],
            "federated_learning": ["Model improvement", "Collaborative learning"],
        }
        return dependency_map.get(consent_type, [])

    # -------- the important one: submit inside st.form --------
    def form_button_with_validation(
        self,
        label: str,
        tooltip_id: str,
        form_valid: bool = True,
        validation_errors: Optional[List[str]] = None,
        *,
        key: Optional[str] = None,
        type: Optional[str] = None,  # "primary" | "secondary"
        use_container_width: Optional[bool] = None,
        disabled: Optional[bool] = None,
        help: Optional[str] = None,  # will be overridden by tooltip if present
        on_click=None,
        args=None,
        kwargs=None,
    ) -> bool:
        """
        Submit button to be used INSIDE a `with st.form(...):` block.
        Uses Streamlit's `st.form_submit_button` (Streamlit >= 1.20; tested on 1.48).
        """
        self._ensure_css_injected()

        # Build tooltip help text (never crash UI)
        context = {"is_valid": form_valid, "errors": validation_errors or [], "disabled": not form_valid}
        tooltip_help = self._help_text(tooltip_id, context)

        # Decide button style once
        resolved_type = type or ("primary" if True else "secondary")

        # Compute disabled state (validation wins)
        resolved_disabled = (disabled is True) or (not form_valid)

        submitted = st.form_submit_button(
            label=label,
            key=key,
            help=tooltip_help or help,
            type=resolved_type,
            disabled=resolved_disabled,
            use_container_width=use_container_width if use_container_width is not None else False,
            on_click=on_click,
            args=args,
            kwargs=kwargs,
        )

        if not form_valid and validation_errors:
            st.error("Please fix the following problems:")
            for err in validation_errors:
                st.write(f"- {err}")

        return submitted


# -------- singleton and public helpers --------
_tooltip_integration: Optional[StreamlitTooltipIntegration] = None

def get_tooltip_integration() -> StreamlitTooltipIntegration:
    global _tooltip_integration
    if _tooltip_integration is None or not hasattr(_tooltip_integration, "form_button_with_validation"):
        _tooltip_integration = StreamlitTooltipIntegration()
    return _tooltip_integration

# Convenience functions for common use cases
def tooltip_button(label: str, tooltip_id: str, **kwargs) -> bool:
    return get_tooltip_integration().button_with_tooltip(label, tooltip_id, **kwargs)

def tooltip_input(label: str, tooltip_id: str, **kwargs) -> str:
    return get_tooltip_integration().text_input_with_tooltip(label, tooltip_id, **kwargs)

def tooltip_checkbox(label: str, tooltip_id: str, **kwargs) -> bool:
    return get_tooltip_integration().checkbox_with_tooltip(label, tooltip_id, **kwargs)

def tooltip_selectbox(label: str, tooltip_id: str, options: list, **kwargs) -> Any:
    return get_tooltip_integration().selectbox_with_tooltip(label, tooltip_id, options, **kwargs)

def consent_checkbox(label: str, tooltip_id: str, user_id: UUID, consent_type: str, **kwargs) -> bool:
    return get_tooltip_integration().consent_checkbox_with_context(label, tooltip_id, user_id, consent_type, **kwargs)

def prerequisite_button(label: str, tooltip_id: str, prerequisites_met: bool, **kwargs) -> bool:
    return get_tooltip_integration().prerequisite_button(label, tooltip_id, prerequisites_met, **kwargs)

def form_submit_button(
    label: str,
    tooltip_id: str,
    *,
    form_valid: bool = True,
    validation_errors: Optional[List[str]] = None,
    **kwargs,
) -> bool:
    """
    Module-level wrapper used by UI code (e.g., auth_ui.py).
    Must be called INSIDE a `with st.form(...):` block.
    """
    return get_tooltip_integration().form_button_with_validation(
        label=label,
        tooltip_id=tooltip_id,
        form_valid=form_valid,
        validation_errors=validation_errors,
        **kwargs,
    )
