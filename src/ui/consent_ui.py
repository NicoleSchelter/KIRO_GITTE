"""
Consent UI components for GITTE system.
Provides Streamlit components for consent management and privacy compliance.
"""

import logging
from uuid import UUID
import time
import streamlit as st

from config.config import get_text
from src.data.models import ConsentType
from src.logic.consent import ConsentError
from src.services.consent_service import get_consent_service
from src.ui.tooltip_integration import get_tooltip_integration
from src.logic.onboarding import OnboardingStep

logger = logging.getLogger(__name__)


class ConsentUI:
    """UI components for consent management."""

    def __init__(self):
        self.consent_service = get_consent_service()
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
                    ConsentType.ANALYTICS: "analytics_consent"
                }
                
                tooltip_id = tooltip_id_map.get(consent_type, "data_processing_consent")

                # Create checkbox with tooltip
                consent_values[consent_type] = consent_checkbox(
                    display_name,
                    tooltip_id,
                    user_id=user_id,
                    consent_type=consent_type.value,
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
                if tooltip_button("Save Consent Preferences", "save_button", type="primary"):
                    self._save_consent_preferences(user_id, consent_values)

            with col2:
                if tooltip_button("Withdraw All Consent", "delete_button"):
                    self._withdraw_all_consent(user_id)

            with col3:
                if tooltip_button("Export My Data", "export_button"):
                    self._export_user_data(user_id)

            # Show consent history
            self._render_consent_history(user_id)

        except Exception as e:
            logger.error(f"Error rendering consent management: {e}")
            st.error("Error loading consent management. Please try again.")

    def render_guided_onboarding_flow(self, user_id: UUID) -> bool:
        """Render the complete guided onboarding flow with anti-loop protection."""
        try:
            # Initialize flow control state
            flow_key = f"onboarding_flow_{user_id}"
            if flow_key not in st.session_state:
                st.session_state[flow_key] = {
                    "initialized": True,
                    "rerun_count": 0,
                    "last_rerun": 0,
                    "max_reruns": 5,  # Prevent infinite loops
                    "cooldown_time": 1  # Seconds between reruns
                }

            flow_state = st.session_state[flow_key]
            current_time = time.time()

            # Anti-loop protection
            if (flow_state["rerun_count"] >= flow_state["max_reruns"] and 
                current_time - flow_state["last_rerun"] < flow_state["cooldown_time"]):
                st.warning("⚠️ Flow rate limited. Please wait a moment before continuing.")
                return False

            # Get current onboarding state
            state = self.onboarding_logic.get_user_onboarding_state(user_id)

            # Check if onboarding is already complete
            if state["onboarding_complete"]:
                return True

            # Render onboarding header
            self._render_onboarding_header(state)

            # Render current step
            current_step = OnboardingStep(state["current_step"])
            step_result = self._render_current_step(user_id, current_step, state)

            # Handle step completion with controlled advancement
            if step_result:
                # Reset rerun count on successful step completion
                flow_state["rerun_count"] = 0
                return self._handle_controlled_step_completion(user_id, current_step, step_result)

            return False

        except Exception as e:
            logger.error(f"Error rendering onboarding flow for user {user_id}: {e}")
            st.error("⚠️ Onboarding flow error. Please refresh the page.")
            return False

    def _handle_controlled_step_completion(self, user_id: UUID, current_step: OnboardingStep, step_data: dict) -> bool:
        """Handle step completion with controlled reruns."""
        flow_key = f"onboarding_flow_{user_id}"
        flow_state = st.session_state[flow_key]
        
        try:
            # Store step data
            if step_data.get("data"):
                self.onboarding_logic.collect_personalization_data(
                    user_id, f"step_{current_step.value}", step_data["data"]
                )

            # Advance to next step
            next_step = self.onboarding_logic.advance_to_next_step(
                user_id, current_step, step_data.get("data")
            )

            # Update flow control
            flow_state["rerun_count"] += 1
            flow_state["last_rerun"] = time.time()

            # Complete or advance
            if next_step == OnboardingStep.COMPLETE:
                st.session_state[f"onboarding_complete_{user_id}"] = True
                st.success("🎉 Onboarding completed successfully!")
                return True
            else:
                st.session_state[f"current_step_{user_id}"] = next_step.value
                
                # Controlled rerun with delay
                time.sleep(0.1)  # Brief pause to prevent race conditions
                st.rerun()

            return False

        except Exception as e:
            logger.error(f"Error handling step completion: {e}")
            st.error("Error advancing to next step. Please try again.")
            return False


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
        }
        return descriptions.get(consent_type, f"Consent for {consent_type.value}")


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
