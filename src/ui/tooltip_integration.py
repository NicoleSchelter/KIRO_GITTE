from __future__ import annotations
import re
import streamlit as st

__all__ = [
    "get_tooltip_integration",
    "tooltip_button",
    "tooltip_input",
    "tooltip_checkbox",
    "tooltip_selectbox",
    "tooltip_text_area",
    "tooltip_number_input",
    "tooltip_radio",
    "tooltip_multiselect",
    "form_submit_button",
]

def _resolve_label(passed_label, kwargs: dict, fallback: str) -> tuple[str, dict]:
    label = passed_label if passed_label is not None else kwargs.pop("label", None)
    if not label or not str(label).strip():
        placeholder = kwargs.get("placeholder")
        key = kwargs.get("key")
        if placeholder and str(placeholder).strip():
            label = str(placeholder).strip()
        elif key:
            s = re.sub(r"[_\\-]+", " ", str(key)).strip()
            label = s[:1].upper() + s[1:] if s else fallback
        else:
            label = fallback
    kwargs.setdefault("label_visibility", "collapsed")
    return label, kwargs

class _NoopTooltipIntegration:
    def wrap(self, widget_fn, *args, **kwargs):
        return widget_fn(*args, **kwargs)

def get_tooltip_integration():
    return _NoopTooltipIntegration()

def tooltip_button(*args, **kwargs):
    # Extract first positional arg as label if provided, otherwise use kwargs
    passed_label = args[0] if args else None
    remaining_args = args[1:] if args else ()
    label, kwargs = _resolve_label(passed_label, kwargs, "Submit")
    return st.button(label, *remaining_args, **kwargs)

def tooltip_input(*args, **kwargs):
    # Extract first positional arg as label if provided, otherwise use kwargs
    passed_label = args[0] if args else None
    remaining_args = args[1:] if args else ()
    fallback = "Password" if kwargs.get("type") == "password" else "Input"
    label, kwargs = _resolve_label(passed_label, kwargs, fallback)
    return st.text_input(label, *remaining_args, **kwargs)

def tooltip_checkbox(*args, **kwargs):
    # Extract first positional arg as label if provided, otherwise use kwargs
    passed_label = args[0] if args else None
    remaining_args = args[1:] if args else ()
    label, kwargs = _resolve_label(passed_label, kwargs, "I accept the terms")
    return st.checkbox(label, *remaining_args, **kwargs)

def tooltip_selectbox(*args, **kwargs):
    # Current usage pattern: tooltip_selectbox(label, key, options=[...], index=0)
    # Extract label and key from positional args
    passed_label = args[0] if args else None
    key = args[1] if len(args) > 1 else kwargs.pop('key', None)
    remaining_args = args[2:] if len(args) > 2 else ()
    
    # Get options from kwargs (required)
    options = kwargs.pop('options', [])
    
    label, kwargs = _resolve_label(passed_label, kwargs, "Select an option")
    return st.selectbox(label, options, key=key, *remaining_args, **kwargs)

def tooltip_text_area(*args, **kwargs):
    # Extract first positional arg as label if provided, otherwise use kwargs
    passed_label = args[0] if args else None
    remaining_args = args[1:] if args else ()
    label, kwargs = _resolve_label(passed_label, kwargs, "Input text")
    return st.text_area(label, *remaining_args, **kwargs)

def tooltip_number_input(*args, **kwargs):
    # Extract first positional arg as label if provided, otherwise use kwargs
    passed_label = args[0] if args else None
    remaining_args = args[1:] if args else ()
    label, kwargs = _resolve_label(passed_label, kwargs, "Enter a number")
    return st.number_input(label, *remaining_args, **kwargs)

def tooltip_radio(*args, **kwargs):
    # Current usage pattern would be: tooltip_radio(label, key, options=[...], index=0)
    # Extract label and key from positional args
    passed_label = args[0] if args else None
    key = args[1] if len(args) > 1 else kwargs.pop('key', None)
    remaining_args = args[2:] if len(args) > 2 else ()
    
    # Get options from kwargs (required)
    options = kwargs.pop('options', [])
    
    label, kwargs = _resolve_label(passed_label, kwargs, "Choose an option")
    return st.radio(label, options, key=key, *remaining_args, **kwargs)

def tooltip_multiselect(*args, **kwargs):
    # Current usage pattern would be: tooltip_multiselect(label, key, options=[...], default=[])
    # Extract label and key from positional args
    passed_label = args[0] if args else None
    key = args[1] if len(args) > 1 else kwargs.pop('key', None)
    remaining_args = args[2:] if len(args) > 2 else ()
    
    # Get options from kwargs (required)
    options = kwargs.pop('options', [])
    
    label, kwargs = _resolve_label(passed_label, kwargs, "Select one or more")
    return st.multiselect(label, options, key=key, *remaining_args, **kwargs)


def form_submit_button(label: str, key: str | None = None, form_valid: bool = True, **kwargs):
    """
    Enhanced form submit button wrapper with backward compatibility.
    
    Args:
        label: Button label text
        key: Optional unique key (IGNORED - st.form_submit_button doesn't support keys)
        form_valid: If False, button will be disabled
        **kwargs: Additional arguments passed to st.form_submit_button
        
    Returns:
        bool: True if button was clicked
        
    Note:
        - All supported Streamlit 1.48.1+ parameters are forwarded except 'key'
        - Form submit buttons are automatically keyed by Streamlit based on position
        - Enforces non-empty labels to avoid Streamlit warnings
        - Respects form_valid parameter by setting disabled state
    """
    # Enforce non-empty label for accessibility and to avoid Streamlit warnings
    if not label or not str(label).strip():
        label = "Submit"
    
    # Respect form_valid parameter (disable when invalid)
    # Only set disabled if not explicitly provided
    if "disabled" not in kwargs:
        kwargs["disabled"] = not form_valid
    
    # NOTE: st.form_submit_button does NOT support 'key' parameter
    # The key parameter is accepted for API compatibility but ignored
    # CRITICAL: Do not pass key parameter to st.form_submit_button
    return st.form_submit_button(label, **kwargs)
