"""
Example of updating consent UI to use accessible form components.
This demonstrates how to replace st.button() with accessible alternatives.
"""

import streamlit as st
from typing import Dict, Any
from uuid import UUID

from src.ui.accessible_form_components import accessible_form_components, ValidationResult
from src.services.consent_service import ConsentService, ConsentType
from src.exceptions import ConsentError


class AccessibleConsentUI:
    """Example of consent UI using accessible form components."""
    
    def __init__(self):
        self.consent_service = ConsentService()
        self.form_components = accessible_form_components
    
    def render_consent_management(self, user_id: UUID):
        """Render consent management interface with accessible components."""
        st.title("Privacy & Consent Management")
        
        # Get current consent status
        consent_status = self._get_consent_status(user_id)
        
        # Create accessible form for consent management
        consent_fields = [
            {
                "type": "checkbox",
                "key": "data_processing",
                "label": "Data Processing Consent",
                "help": "Allow processing of your data for core functionality"
            },
            {
                "type": "checkbox", 
                "key": "analytics",
                "label": "Analytics Consent",
                "help": "Allow collection of usage analytics to improve the service"
            },
            {
                "type": "checkbox",
                "key": "personalization",
                "label": "Personalization Consent", 
                "help": "Allow personalization of your experience"
            }
        ]
        
        # Pre-fill with current consent status
        for field in consent_fields:
            consent_type = ConsentType(field["key"])
            if f"consent_form_{field['key']}" not in st.session_state:
                st.session_state[f"consent_form_{field['key']}"] = consent_status.get(consent_type, False)
        
        # Render accessible form
        form_data = self.form_components.create_accessible_form(
            form_key="consent_management",
            title="Consent Preferences",
            fields=consent_fields,
            submit_callback=lambda data: self._save_consent_preferences(user_id, data),
            validation_callback=lambda data: self._validate_consent_data(data)
        )
        
        if form_data:
            st.success("✅ Consent preferences updated successfully!")
        
        # Withdrawal section using accessible confirmation
        st.subheader("Withdraw All Consent")
        st.warning("⚠️ This will withdraw all consents and disable GITTE features.")
        
        withdrawal_confirmed = self.form_components.confirmation_dialog(
            message="Are you sure you want to withdraw all consent? This action cannot be undone.",
            confirm_label="Yes, Withdraw All",
            cancel_label="Cancel",
            key="withdraw_confirmation"
        )
        
        if withdrawal_confirmed is True:
            self._withdraw_all_consent(user_id)
        elif withdrawal_confirmed is False:
            st.info("Withdrawal cancelled.")
    
    def render_quick_consent_check(self, user_id: UUID, required_consents: list[ConsentType]):
        """Render quick consent check with accessible components."""
        missing_consents = self._get_missing_consents(user_id, required_consents)
        
        if not missing_consents:
            st.success("✅ All required consents are provided")
            return True
        
        st.warning(f"⚠️ Missing required consents: {', '.join([c.value for c in missing_consents])}")
        
        # Use accessible action button instead of st.button
        consent_granted = self.form_components.accessible_action_button(
            label="Grant Required Consents",
            key="grant_consents",
            callback=lambda: self._grant_missing_consents(user_id, missing_consents),
            help_text="Click to provide the required consents",
            icon="✅",
            button_type="primary"
        )
        
        if consent_granted:
            st.success("✅ Required consents granted!")
            st.rerun()
        
        return False
    
    def render_consent_status_dashboard(self, user_id: UUID):
        """Render consent status dashboard with accessible components."""
        st.subheader("Consent Status Dashboard")
        
        consent_status = self._get_consent_status(user_id)
        
        # Display status using accessible components
        for consent_type, granted in consent_status.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                status_icon = "✅" if granted else "❌"
                st.write(f"{status_icon} {consent_type.value}")
            
            with col2:
                if granted:
                    st.success("Granted")
                else:
                    st.error("Not Granted")
            
            with col3:
                # Use accessible action button for individual consent management
                action_taken = self.form_components.accessible_action_button(
                    label="Withdraw" if granted else "Grant",
                    key=f"toggle_{consent_type.value}",
                    callback=lambda ct=consent_type: self._toggle_consent(user_id, ct),
                    help_text=f"{'Withdraw' if granted else 'Grant'} {consent_type.value} consent",
                    icon="❌" if granted else "✅"
                )
        
        # Refresh button using accessible components
        refresh_requested = self.form_components.accessible_action_button(
            label="Refresh Status",
            key="refresh_consent_status",
            callback=lambda: st.rerun(),
            help_text="Refresh the consent status display",
            icon="🔄"
        )
    
    def _get_consent_status(self, user_id: UUID) -> Dict[ConsentType, bool]:
        """Get current consent status for user."""
        try:
            status = {}
            for consent_type in ConsentType:
                status[consent_type] = self.consent_service.has_consent(user_id, consent_type)
            return status
        except Exception as e:
            st.error(f"Error retrieving consent status: {e}")
            return {}
    
    def _get_missing_consents(self, user_id: UUID, required_consents: list[ConsentType]) -> list[ConsentType]:
        """Get list of missing required consents."""
        missing = []
        for consent_type in required_consents:
            if not self.consent_service.has_consent(user_id, consent_type):
                missing.append(consent_type)
        return missing
    
    def _save_consent_preferences(self, user_id: UUID, form_data: Dict[str, Any]):
        """Save consent preferences from form data."""
        try:
            for field_key, granted in form_data.items():
                if field_key in ["data_processing", "analytics", "personalization"]:
                    consent_type = ConsentType(field_key)
                    
                    if granted:
                        self.consent_service.grant_consent(
                            user_id, consent_type, "User granted consent via form"
                        )
                    else:
                        self.consent_service.withdraw_consent(
                            user_id, consent_type, "User withdrew consent via form"
                        )
        
        except ConsentError as e:
            st.error(f"Failed to save consent preferences: {e}")
            raise
    
    def _validate_consent_data(self, form_data: Dict[str, Any]) -> ValidationResult:
        """Validate consent form data."""
        errors = []
        warnings = []
        
        # Check if at least one consent is granted
        any_granted = any(form_data.values())
        if not any_granted:
            warnings.append("No consents granted - GITTE functionality will be limited")
        
        # Check for data processing consent (usually required)
        if not form_data.get("data_processing", False):
            warnings.append("Data processing consent is required for core functionality")
        
        return ValidationResult(
            is_valid=True,  # Always valid, but may have warnings
            errors=errors,
            warnings=warnings
        )
    
    def _withdraw_all_consent(self, user_id: UUID):
        """Withdraw all consent for user."""
        try:
            for consent_type in ConsentType:
                self.consent_service.withdraw_consent(
                    user_id, consent_type, "User requested withdrawal of all consents"
                )
            
            st.success("✅ All consents have been withdrawn.")
            st.warning("⚠️ You will no longer be able to use GITTE features until you provide consent again.")
            
        except Exception as e:
            st.error(f"Error withdrawing consents: {e}")
    
    def _grant_missing_consents(self, user_id: UUID, missing_consents: list[ConsentType]):
        """Grant missing required consents."""
        try:
            for consent_type in missing_consents:
                self.consent_service.grant_consent(
                    user_id, consent_type, "User granted required consent"
                )
        except Exception as e:
            st.error(f"Error granting consents: {e}")
            raise
    
    def _toggle_consent(self, user_id: UUID, consent_type: ConsentType):
        """Toggle individual consent."""
        try:
            current_status = self.consent_service.has_consent(user_id, consent_type)
            
            if current_status:
                self.consent_service.withdraw_consent(
                    user_id, consent_type, "User withdrew consent via dashboard"
                )
                st.success(f"✅ Withdrew {consent_type.value} consent")
            else:
                self.consent_service.grant_consent(
                    user_id, consent_type, "User granted consent via dashboard"
                )
                st.success(f"✅ Granted {consent_type.value} consent")
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Error toggling consent: {e}")


# Example usage function
def render_accessible_consent_example():
    """Example function showing how to use accessible consent UI."""
    if "user_id" not in st.session_state:
        st.session_state.user_id = UUID("12345678-1234-5678-9012-123456789012")  # Example UUID
    
    consent_ui = AccessibleConsentUI()
    
    # Tab-based interface using accessible components
    tab1, tab2, tab3 = st.tabs(["Consent Management", "Quick Check", "Status Dashboard"])
    
    with tab1:
        consent_ui.render_consent_management(st.session_state.user_id)
    
    with tab2:
        required_consents = [ConsentType.DATA_PROCESSING, ConsentType.ANALYTICS]
        consent_ui.render_quick_consent_check(st.session_state.user_id, required_consents)
    
    with tab3:
        consent_ui.render_consent_status_dashboard(st.session_state.user_id)


if __name__ == "__main__":
    render_accessible_consent_example()