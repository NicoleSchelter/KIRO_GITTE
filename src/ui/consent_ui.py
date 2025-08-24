"""
Consent UI components for GITTE system.
Provides Streamlit components for consent management and privacy compliance.
"""

from __future__ import annotations

import logging
from uuid import UUID
import time
import streamlit as st

from config.config import get_text, CONSENT_TYPES_UI, DEBUG_UI_CONSENT_KEYS
from src.data.models import StudyConsentType, ConsentType
from src.exceptions import ConsentError
from src.services.consent_service import get_study_consent_service
from src.ui.tooltip_integration import get_tooltip_integration, tooltip_button, tooltip_checkbox
from src.logic.onboarding import OnboardingStep

logger = logging.getLogger(__name__)


class ConsentUI:
    """UI components for consent management."""

    def __init__(self):
        self.consent_service = get_study_consent_service()
        self.tooltip_integration = get_tooltip_integration()

    def render_consent_gate(self, user_id: UUID, operation: str) -> bool:
        """
        Render consent gate that blocks access without valid consent.

        Args:
            user_id: User identifier
            operation: Operation being attempted

        Returns:
            bool: True if user has required consents
        """
        try:
            # Check if consent gate is enabled
            if not self.consent_service.is_consent_gate_enabled():
                return True

            # Check if user has required consents
            if self.consent_service.check_operation_consent(user_id, operation):
                return True

            # Show consent gate UI
            st.error(get_text("error_consent_required"))
            st.warning(f"You need to provide consent to access {operation} functionality.")

            # Get missing consents
            required_consents = self.consent_service.get_required_consents_for_operation(operation)
            missing_consents = []

            for consent_type in required_consents:
                if not self.consent_service.check_consent(user_id, consent_type):
                    missing_consents.append(consent_type)

            if missing_consents:
                st.write("**Missing consents:**")
                for consent_type in missing_consents:
                    st.write(f"- {self._get_consent_display_name(consent_type)}")

            # Provide link to consent management
            if tooltip_button("Manage Consent Settings", "consent_settings_button"):
                st.session_state.show_consent_ui = True
                st.rerun()

            return False

        except Exception as e:
            logger.error(f"Error rendering consent gate: {e}")
            st.error("Error checking consent status. Please try again.")
            return False

    def render_consent_form(
        self, user_id: UUID, consent_types: list[ConsentType] | None = None
    ) -> dict[ConsentType, bool]:
        """
        Render consent form for recording user consent.

        Args:
            user_id: User identifier
            consent_types: Specific consent types to show (None for all)

        Returns:
            Dict mapping consent types to their values
        """
        try:
            st.subheader(get_text("consent_title"))

            # Get current consent status
            current_status = self.consent_service.get_consent_status(user_id)

            # Use all consent types if none specified
            if consent_types is None:
                consent_types = list(ConsentType)

            consent_values = {}

            # Render consent checkboxes
            for consent_type in consent_types:
                display_name = self._get_consent_display_name(consent_type)
                current_value = current_status.get(consent_type.value, False)

                # Map consent type to tooltip ID
                tooltip_id_map = {
                    ConsentType.DATA_PROCESSING: "data_processing_consent",
                    ConsentType.AI_INTERACTION: "llm_interaction_consent", 
                    ConsentType.IMAGE_GENERATION: "image_generation_consent",
                    ConsentType.ANALYTICS: "analytics_consent",
                    ConsentType.INVESTIGATION_PARTICIPATION: "investigation_participation_consent",
                }
                
                tooltip_id = tooltip_id_map.get(consent_type, "data_processing_consent")

                # Create checkbox with tooltip
                consent_values[consent_type] = tooltip_checkbox(
                    display_name,
                    tooltip_id,
                    value=current_value,
                    key=f"consent_{consent_type.value}"
                )

            return consent_values

        except Exception as e:
            logger.error(f"Error rendering consent form: {e}")
            st.error("Error loading consent form. Please try again.")
            return {}

    def render_consent_management(self, user_id: UUID) -> None:
        """
        Render comprehensive consent management interface.

        Args:
            user_id: User identifier
        """
        try:
            st.title("Privacy Consent Management")

            # Show current consent status
            self._render_consent_status(user_id)

            # Consent form
            st.subheader("Update Consent Preferences")

            consent_values = self.render_consent_form(user_id)

            col1, col2, col3 = st.columns(3)

            with col1:
                if tooltip_button("Save Consent Preferences", type="primary"):
                    self._save_consent_preferences(user_id, consent_values)

            with col2:
                if tooltip_button("Withdraw All Consent"):
                    self._withdraw_all_consent(user_id)

            with col3:
                if tooltip_button("Export My Data"):
                    self._export_user_data(user_id)

            # Show consent history
            self._render_consent_history(user_id)

        except Exception as e:
            logger.error(f"Error rendering consent management: {e}")
            st.error("Error loading consent management. Please try again.")


    def _render_consent_status(self, user_id: UUID) -> None:
        """Render current consent status."""
        try:
            consent_summary = self.consent_service.get_consent_summary(user_id)

            if consent_summary:
                st.subheader("Current Consent Status")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Consents Given", consent_summary.get("consents_given", 0))

                with col2:
                    st.metric("Total Types", consent_summary.get("total_consent_types", 0))

                with col3:
                    completion_rate = consent_summary.get("consent_completion_rate", 0)
                    st.metric("Completion Rate", f"{completion_rate:.1%}")

                # Show individual consent status
                consent_status = consent_summary.get("consent_status", {})

                for consent_type, status in consent_status.items():
                    status_icon = "✅" if status else "❌"
                    display_name = self._get_consent_display_name(ConsentType(consent_type))
                    st.write(f"{status_icon} {display_name}")

        except Exception as e:
            logger.error(f"Error rendering consent status: {e}")
            st.error("Error loading consent status.")

    def _render_consent_history(self, user_id: UUID) -> None:
        """Render consent history."""
        try:
            with st.expander("Consent History"):
                consent_records = self.consent_service.get_user_consents(user_id)

                if consent_records:
                    for record in consent_records[:10]:  # Show last 10 records
                        status_text = "Granted" if record.consent_given else "Withdrawn"
                        status_color = "green" if record.consent_given else "red"

                        st.write(
                            f"**{self._get_consent_display_name(ConsentType(record.consent_type))}**"
                        )
                        st.write(f"Status: :{status_color}[{status_text}]")
                        st.write(f"Date: {record.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.write(f"Version: {record.consent_version}")
                        st.divider()
                else:
                    st.write("No consent history found.")

        except Exception as e:
            logger.error(f"Error rendering consent history: {e}")
            st.error("Error loading consent history.")

    def _save_consent_preferences(
        self, user_id: UUID, consent_values: dict[ConsentType, bool]
    ) -> None:
        """Save consent preferences."""
        try:
            self.consent_service.record_bulk_consent(
                user_id, consent_values, {"source": "preferences_update"}
            )
            st.success("Consent preferences saved successfully!")
            st.rerun()

        except ConsentError as e:
            st.error(f"Failed to save consent preferences: {e}")

    def _withdraw_all_consent(self, user_id: UUID) -> None:
        """Withdraw all consent."""
        try:
            if st.button("Confirm Withdrawal", key="confirm_withdraw"):
                for consent_type in ConsentType:
                    self.consent_service.withdraw_consent(
                        user_id, consent_type, "User requested withdrawal of all consents"
                    )

                st.success("All consents have been withdrawn.")
                st.warning(
                    "You will no longer be able to use GITTE features until you provide consent again."
                )
                st.rerun()

        except Exception as e:
            logger.error(f"Error withdrawing all consent: {e}")
            st.error("Failed to withdraw consent. Please try again.")

    def _export_user_data(self, user_id: UUID) -> None:
        """Export user data (placeholder)."""
        st.info("Data export functionality will be implemented in a future task.")

    def _get_consent_display_name(self, consent_type: ConsentType) -> str:
        """Get user-friendly display name for consent type."""
        display_names = {
            ConsentType.DATA_PROCESSING: "Data Processing",
            ConsentType.AI_INTERACTION: "AI Interaction",
            ConsentType.IMAGE_GENERATION: "Image Generation",
            ConsentType.FEDERATED_LEARNING: "Federated Learning",
            ConsentType.ANALYTICS: "Analytics & Improvements",
            ConsentType.INVESTIGATION_PARTICIPATION: "Investigation Participation",
        }
        return display_names.get(consent_type, consent_type.value.replace("_", " ").title())

    def _get_consent_description(self, consent_type: ConsentType) -> str:
        """Get description for consent type."""
        descriptions = {
            ConsentType.DATA_PROCESSING: "Allow processing of your personal data for core functionality",
            ConsentType.AI_INTERACTION: "Allow AI interactions and chat functionality",
            ConsentType.IMAGE_GENERATION: "Allow generation of visual representations and avatars",
            ConsentType.FEDERATED_LEARNING: "Participate in privacy-preserving model improvements",
            ConsentType.ANALYTICS: "Allow collection of usage analytics to improve the system",
            ConsentType.INVESTIGATION_PARTICIPATION: "Participate in research study to improve educational AI systems",
        }
        return descriptions.get(consent_type, f"Consent for {consent_type.value}")

    def render_onboarding_consent(self, user_id: UUID | None = None, pseudonym_id: UUID | None = None) -> bool:
        """Render onboarding-specific consent form for initial setup.
        
        Args:
            user_id: User identifier (for consent-first flow)
            pseudonym_id: Pseudonym identifier (for pseudonym-first flow)
            
        Returns:
            bool: True if consent was granted and saved, False otherwise
        """
        try:
            st.write(
                """
                To use GITTE and participate in our research investigation, we need your consent for data processing, AI interactions, and research participation.
                Your privacy is important to us, and you can change these settings at any time.
                
                **Research Study**: By using GITTE, you have the opportunity to participate in a research investigation 
                about personalized AI tutoring systems. This helps improve educational technology for future learners.
                """
            )

            # Initialize session state for consent tracking
            if "consent_form_state" not in st.session_state:
                st.session_state.consent_form_state = {}

            # Get current consent status - handle both user_id and pseudonym_id
            if pseudonym_id:
                current_status = self.consent_service.get_consent_status(pseudonym_id)
            else:
                # For consent-first flow, start with empty status
                current_status = {}

            # Create the consent form using centralized configuration
            st.subheader("Privacy Consent Form")
            st.write("Please read and consent to the following items:")

            # Required consents section
            st.markdown("### ✅ Required Consents")
            st.write("These consents are required to use GITTE:")
            
            required_consent_granted = True
            
            for i, (consent_key, consent_label) in enumerate(CONSENT_TYPES_UI):
                # Use pre-fetched consent status as default
                current_value = current_status.get(consent_key, False)
                
                # Create unique key for each checkbox
                checkbox_key = f"required_consent_{consent_key}_{i}"
                
                # Clear container for each consent item
                with st.container():
                    st.markdown(f"**{i+1}. {consent_label}**")
                    
                    # Simple checkbox without complex formatting
                    granted = st.checkbox(
                        f"I consent to {consent_label.lower()}",
                        value=current_value,
                        key=checkbox_key,
                        help=f"Required for study participation: {consent_label}"
                    )
                    
                    # Track consent state using canonical key
                    st.session_state.consent_form_state[consent_key] = granted
                    
                    # Show description in expandable section
                    with st.expander(f"View details for {consent_label}"):
                        st.write(self._get_consent_description_by_key(consent_key))
                    
                    # Update overall required status
                    if not granted:
                        required_consent_granted = False
                    
                    st.write("")  # Add spacing

            # Status display
            st.divider()
            st.subheader("Consent Status")
            
            # Debug display if enabled
            if DEBUG_UI_CONSENT_KEYS:
                with st.expander("Debug: Consent Keys to Submit"):
                    consent_payload = {k: v for k, v in st.session_state.consent_form_state.items()}
                    st.code(f"Consent payload: {consent_payload}")
            
            if required_consent_granted:
                st.success("✅ All required consents have been granted. You can proceed with onboarding.")
            else:
                missing_required = []
                for consent_key, consent_label in CONSENT_TYPES_UI:
                    if not st.session_state.consent_form_state.get(consent_key, False):
                        missing_required.append(consent_label)
                
                st.error(f"⚠️ Missing required consents: {', '.join(missing_required)}")
                st.info("Please check all required consent boxes above to continue.")

            # Action buttons
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if not required_consent_granted:
                    st.warning("Please grant all required consents to continue.")
            
            with col2:
                submit_button = st.button(
                    "Continue with Onboarding",
                    type="primary",
                    disabled=not required_consent_granted,
                    key="consent_submit_btn"
                )

            # Process form submission
            if submit_button and required_consent_granted:
                try:
                    # Build final consent values from session state using canonical keys
                    final_consent_dict = {}
                    for consent_key, granted in st.session_state.consent_form_state.items():
                        final_consent_dict[consent_key] = granted
                    
                    # Handle consent-first flow (buffer consents in session state)
                    if user_id and not pseudonym_id:
                        # Store consents in session state for later processing
                        st.session_state.buffered_consents = final_consent_dict
                        st.success("✅ Consent preferences recorded!")
                        st.info("Proceeding to pseudonym creation...")
                        
                        # Clear the form state
                        del st.session_state.consent_form_state
                        
                        return True
                    
                    # Handle pseudonym-first flow (immediate processing)
                    elif pseudonym_id:
                        # Process consent collection with normalization
                        result = self.consent_service.process_consent_collection(
                            pseudonym_id, 
                            final_consent_dict
                        )
                        
                        if result["success"] and result["can_proceed"]:
                            st.success("✅ Consent preferences saved successfully!")
                            st.info("Continuing with onboarding...")
                            
                            # Clear the form state
                            del st.session_state.consent_form_state
                            
                            return True
                        else:
                            failed_consents = result.get("failed_consents", [])
                            st.error(f"Failed to save some consents: {', '.join(failed_consents)}")
                            return False
                    else:
                        st.error("Invalid onboarding state - missing user or pseudonym ID")
                        return False
                    
                except ConsentError as e:
                    logger.error(f"Error saving onboarding consent: {e}")
                    st.error(f"Failed to save consent preferences: {e}")
                    return False
                    
            elif submit_button and not required_consent_granted:
                st.error("Please grant all required consents to continue.")

            return False
            
        except Exception as e:
            logger.error(f"Error rendering onboarding consent: {e}")
            st.error("Error loading consent form. Please refresh the page and try again.")
            
            # Show debug information if there's an error
            with st.expander("Debug Information (Error Details)"):
                st.code(f"Error: {str(e)}")
                st.code(f"Error Type: {type(e).__name__}")
            
            return False

    def _get_consent_description_by_key(self, consent_key: str) -> str:
        """Get description for consent type by key."""
        descriptions = {
            "data_protection": "Allow processing of your personal data for core functionality and GDPR compliance",
            "ai_interaction": "Allow AI interactions and chat functionality with our tutoring system",
            "study_participation": "Participate in research study to improve educational AI systems",
        }
        return descriptions.get(consent_key, f"Consent for {consent_key.replace('_', ' ')}")


# Global consent UI instance
consent_ui = ConsentUI()


# Convenience functions
def render_consent_gate(user_id: UUID, operation: str) -> bool:
    """Render consent gate for an operation."""
    return consent_ui.render_consent_gate(user_id, operation)


def render_consent_form(
    user_id: UUID, consent_types: list[ConsentType] | None = None
) -> dict[ConsentType, bool]:
    """Render consent form."""
    return consent_ui.render_consent_form(user_id, consent_types)


def render_consent_management(user_id: UUID) -> None:
    """Render consent management interface."""
    consent_ui.render_consent_management(user_id)


def render_onboarding_consent(user_id: UUID) -> bool:
    """Render onboarding consent form."""
    return consent_ui.render_onboarding_consent(user_id)


def check_and_render_consent_gate(user_id: UUID, operation: str) -> bool:
    """Check consent and render gate if needed."""
    return consent_ui.render_consent_gate(user_id, operation)
