"""
Accessible Form Components
Provides Streamlit form components without standard buttons for improved accessibility.
"""

import logging
import streamlit as st
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SubmissionMethod(Enum):
    """Methods for form submission without standard buttons."""
    FORM_SUBMIT = "form_submit"
    AUTO_SUBMIT = "auto_submit"
    ENTER_KEY = "enter_key"
    SELECTBOX_CHANGE = "selectbox_change"


@dataclass
class ValidationResult:
    """Result of form validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class AccessibleFormComponents:
    """Streamlit form components without standard buttons."""
    
    def __init__(self):
        self.form_states: Dict[str, Dict[str, Any]] = {}
    
    def form_submit_handler(
        self, 
        form_key: str, 
        submit_label: str = "Submit",
        callback: Optional[Callable] = None,
        validation_callback: Optional[Callable] = None,
        disabled: bool = False
    ) -> bool:
        """Handle form submission using st.form_submit_button instead of st.button."""
        try:
            # Use form_submit_button which is accessible and doesn't cause rerun issues
            submitted = st.form_submit_button(
                label=submit_label,
                disabled=disabled,
                help="Press Enter or click to submit the form"
            )
            
            if submitted:
                # Run validation if provided
                if validation_callback:
                    validation_result = validation_callback()
                    if isinstance(validation_result, ValidationResult) and not validation_result.is_valid:
                        for error in validation_result.errors:
                            st.error(error)
                        for warning in validation_result.warnings:
                            st.warning(warning)
                        return False
                
                # Run callback if provided
                if callback:
                    try:
                        callback()
                    except Exception as e:
                        st.error(f"Error processing form: {str(e)}")
                        logger.error(f"Form callback error for {form_key}: {e}")
                        return False
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in form submit handler for {form_key}: {e}")
            st.error("An error occurred while processing the form")
            return False
    
    def auto_submit_form(
        self, 
        form_key: str, 
        form_data: Dict[str, Any], 
        trigger_field: str,
        callback: Optional[Callable] = None
    ) -> bool:
        """Auto-submit form when trigger field changes."""
        try:
            # Store previous state
            if form_key not in self.form_states:
                self.form_states[form_key] = {}
            
            previous_value = self.form_states[form_key].get(trigger_field)
            current_value = form_data.get(trigger_field)
            
            # Check if trigger field changed
            if previous_value != current_value and current_value is not None:
                self.form_states[form_key][trigger_field] = current_value
                
                if callback:
                    try:
                        callback(form_data)
                        return True
                    except Exception as e:
                        st.error(f"Error in auto-submit: {str(e)}")
                        logger.error(f"Auto-submit callback error for {form_key}: {e}")
            
            # Update stored state
            self.form_states[form_key].update(form_data)
            return False
            
        except Exception as e:
            logger.error(f"Error in auto-submit for {form_key}: {e}")
            return False
    
    def accessible_action_button(
        self,
        label: str,
        key: str,
        callback: Optional[Callable] = None,
        help_text: Optional[str] = None,
        icon: Optional[str] = None,
        button_type: str = "secondary",
        disabled: bool = False
    ) -> bool:
        """Create accessible action using selectbox instead of button."""
        try:
            # Create a selectbox that acts like a button
            display_label = f"{icon} {label}" if icon else label
            
            # Use selectbox with options that trigger actions
            options = ["Select action...", display_label]
            
            selected = st.selectbox(
                label="Action",
                options=options,
                key=key,
                help=help_text,
                disabled=disabled,
                label_visibility="collapsed"
            )
            
            # If action is selected (not default option)
            if selected != "Select action..." and selected == display_label:
                if callback:
                    try:
                        callback()
                        # Reset selectbox to default after action
                        st.session_state[key] = "Select action..."
                        return True
                    except Exception as e:
                        st.error(f"Error executing action: {str(e)}")
                        logger.error(f"Action callback error for {key}: {e}")
                        st.session_state[key] = "Select action..."
            
            return False
            
        except Exception as e:
            logger.error(f"Error in accessible action button {key}: {e}")
            return False
    
    def confirmation_dialog(
        self,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        key: str = "confirm_dialog"
    ) -> Optional[bool]:
        """Create accessible confirmation dialog using radio buttons."""
        try:
            st.warning(message)
            
            choice = st.radio(
                "Please confirm your choice:",
                options=[cancel_label, confirm_label],
                key=key,
                horizontal=True
            )
            
            if choice == confirm_label:
                return True
            elif choice == cancel_label:
                return False
            
            return None
            
        except Exception as e:
            logger.error(f"Error in confirmation dialog {key}: {e}")
            return None
    
    def progress_indicator(
        self, 
        current_step: int, 
        total_steps: int, 
        step_names: List[str],
        show_navigation: bool = True
    ):
        """Show accessible progress indicator with optional navigation."""
        try:
            # Progress bar
            progress = current_step / total_steps
            st.progress(progress, text=f"Step {current_step} of {total_steps}")
            
            # Step names with status indicators
            cols = st.columns(total_steps)
            for i, (col, step_name) in enumerate(zip(cols, step_names)):
                with col:
                    if i < current_step:
                        st.success(f"✅ {step_name}")
                    elif i == current_step:
                        st.info(f"🔄 {step_name}")
                    else:
                        st.write(f"⏳ {step_name}")
            
            # Navigation if enabled
            if show_navigation and total_steps > 1:
                nav_cols = st.columns([1, 1, 1])
                
                with nav_cols[0]:
                    if current_step > 1:
                        if st.form_submit_button("⬅️ Previous"):
                            return "previous"
                
                with nav_cols[2]:
                    if current_step < total_steps:
                        if st.form_submit_button("Next ➡️"):
                            return "next"
            
            return None
            
        except Exception as e:
            logger.error(f"Error in progress indicator: {e}")
            return None
    
    def validation_feedback(
        self, 
        field_name: str, 
        validation_result: ValidationResult,
        show_success: bool = True
    ):
        """Provide accessible validation feedback."""
        try:
            if validation_result.is_valid and show_success:
                st.success(f"✅ {field_name} is valid")
            
            for error in validation_result.errors:
                st.error(f"❌ {field_name}: {error}")
            
            for warning in validation_result.warnings:
                st.warning(f"⚠️ {field_name}: {warning}")
                
        except Exception as e:
            logger.error(f"Error showing validation feedback for {field_name}: {e}")
    
    def accessible_file_uploader(
        self,
        label: str,
        key: str,
        accepted_types: List[str],
        callback: Optional[Callable] = None,
        help_text: Optional[str] = None
    ) -> Optional[Any]:
        """Create accessible file uploader with automatic processing."""
        try:
            uploaded_file = st.file_uploader(
                label=label,
                key=key,
                type=accepted_types,
                help=help_text
            )
            
            if uploaded_file is not None:
                # Show file info
                st.info(f"📁 File: {uploaded_file.name} ({uploaded_file.size} bytes)")
                
                # Auto-process if callback provided
                if callback:
                    try:
                        result = callback(uploaded_file)
                        st.success("✅ File processed successfully")
                        return result
                    except Exception as e:
                        st.error(f"❌ Error processing file: {str(e)}")
                        logger.error(f"File upload callback error for {key}: {e}")
            
            return uploaded_file
            
        except Exception as e:
            logger.error(f"Error in accessible file uploader {key}: {e}")
            return None
    
    def accessible_multi_select(
        self,
        label: str,
        options: List[str],
        key: str,
        callback: Optional[Callable] = None,
        help_text: Optional[str] = None,
        min_selections: int = 0,
        max_selections: Optional[int] = None
    ) -> List[str]:
        """Create accessible multi-select with validation."""
        try:
            selected = st.multiselect(
                label=label,
                options=options,
                key=key,
                help=help_text
            )
            
            # Validation
            validation_errors = []
            
            if len(selected) < min_selections:
                validation_errors.append(f"Please select at least {min_selections} option(s)")
            
            if max_selections and len(selected) > max_selections:
                validation_errors.append(f"Please select no more than {max_selections} option(s)")
            
            # Show validation feedback
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            elif selected:
                st.success(f"✅ {len(selected)} option(s) selected")
            
            # Auto-callback on valid selection
            if not validation_errors and selected and callback:
                try:
                    callback(selected)
                except Exception as e:
                    st.error(f"Error processing selection: {str(e)}")
                    logger.error(f"Multi-select callback error for {key}: {e}")
            
            return selected
            
        except Exception as e:
            logger.error(f"Error in accessible multi-select {key}: {e}")
            return []
    
    def accessible_number_input(
        self,
        label: str,
        key: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        step: float = 1.0,
        callback: Optional[Callable] = None,
        help_text: Optional[str] = None,
        format_string: str = "%d"
    ) -> Optional[float]:
        """Create accessible number input with validation."""
        try:
            value = st.number_input(
                label=label,
                key=key,
                min_value=min_value,
                max_value=max_value,
                step=step,
                help=help_text,
                format=format_string
            )
            
            # Additional validation
            validation_errors = []
            
            if min_value is not None and value < min_value:
                validation_errors.append(f"Value must be at least {min_value}")
            
            if max_value is not None and value > max_value:
                validation_errors.append(f"Value must be no more than {max_value}")
            
            # Show validation feedback
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
                return None
            
            # Auto-callback on valid input
            if callback:
                try:
                    callback(value)
                except Exception as e:
                    st.error(f"Error processing number input: {str(e)}")
                    logger.error(f"Number input callback error for {key}: {e}")
            
            return value
            
        except Exception as e:
            logger.error(f"Error in accessible number input {key}: {e}")
            return None
    
    def accessible_text_area(
        self,
        label: str,
        key: str,
        callback: Optional[Callable] = None,
        help_text: Optional[str] = None,
        min_length: int = 0,
        max_length: Optional[int] = None,
        placeholder: Optional[str] = None
    ) -> str:
        """Create accessible text area with validation."""
        try:
            value = st.text_area(
                label=label,
                key=key,
                help=help_text,
                placeholder=placeholder
            )
            
            # Validation
            validation_errors = []
            
            if len(value.strip()) < min_length:
                validation_errors.append(f"Please enter at least {min_length} characters")
            
            if max_length and len(value) > max_length:
                validation_errors.append(f"Please enter no more than {max_length} characters")
            
            # Show validation feedback
            if validation_errors:
                for error in validation_errors:
                    st.error(error)
            elif value.strip():
                st.success(f"✅ {len(value)} characters entered")
            
            # Auto-callback on valid input
            if not validation_errors and value.strip() and callback:
                try:
                    callback(value)
                except Exception as e:
                    st.error(f"Error processing text input: {str(e)}")
                    logger.error(f"Text area callback error for {key}: {e}")
            
            return value
            
        except Exception as e:
            logger.error(f"Error in accessible text area {key}: {e}")
            return ""
    
    def create_accessible_form(
        self,
        form_key: str,
        title: str,
        fields: List[Dict[str, Any]],
        submit_callback: Optional[Callable] = None,
        validation_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Create a complete accessible form with multiple fields."""
        try:
            form_data = {}
            
            with st.form(key=form_key):
                st.subheader(title)
                
                # Render fields
                for field in fields:
                    field_type = field.get("type", "text")
                    field_key = field.get("key")
                    field_label = field.get("label")
                    
                    if field_type == "text":
                        form_data[field_key] = st.text_input(
                            label=field_label,
                            key=f"{form_key}_{field_key}",
                            help=field.get("help"),
                            placeholder=field.get("placeholder")
                        )
                    elif field_type == "textarea":
                        form_data[field_key] = st.text_area(
                            label=field_label,
                            key=f"{form_key}_{field_key}",
                            help=field.get("help"),
                            placeholder=field.get("placeholder")
                        )
                    elif field_type == "number":
                        form_data[field_key] = st.number_input(
                            label=field_label,
                            key=f"{form_key}_{field_key}",
                            min_value=field.get("min_value"),
                            max_value=field.get("max_value"),
                            step=field.get("step", 1),
                            help=field.get("help")
                        )
                    elif field_type == "selectbox":
                        form_data[field_key] = st.selectbox(
                            label=field_label,
                            options=field.get("options", []),
                            key=f"{form_key}_{field_key}",
                            help=field.get("help")
                        )
                    elif field_type == "multiselect":
                        form_data[field_key] = st.multiselect(
                            label=field_label,
                            options=field.get("options", []),
                            key=f"{form_key}_{field_key}",
                            help=field.get("help")
                        )
                    elif field_type == "checkbox":
                        form_data[field_key] = st.checkbox(
                            label=field_label,
                            key=f"{form_key}_{field_key}",
                            help=field.get("help")
                        )
                
                # Submit button
                submitted = self.form_submit_handler(
                    form_key=form_key,
                    submit_label=field.get("submit_label", "Submit"),
                    callback=lambda: submit_callback(form_data) if submit_callback else None,
                    validation_callback=lambda: validation_callback(form_data) if validation_callback else ValidationResult(True, [], [])
                )
                
                if submitted:
                    return form_data
            
            return {}
            
        except Exception as e:
            logger.error(f"Error creating accessible form {form_key}: {e}")
            st.error("An error occurred while creating the form")
            return {}


# Global instance for use across UI components
accessible_form_components = AccessibleFormComponents()