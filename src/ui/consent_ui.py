"""
Consent UI components for GITTE system.
Provides Streamlit components for consent management and privacy compliance.
"""

import logging
from uuid import UUID

import streamlit as st

from config.config import get_text
from src.data.models import ConsentType
from src.logic.consent import ConsentError
from src.services.consent_service import get_consent_service
from src.ui.tooltip_integration import (
    get_tooltip_integration,
    consent_checkbox,
    tooltip_button
)

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

    def render_onboarding_consent(self, user_id: UUID) -> bool:
        """
        Render consent form for onboarding flow.

        Args:
            user_id: User identifier

        Returns:
            bool: True if consent was successfully recorded
        """
        try:
            st.title("Welcome to GITTE!")
            st.write(
                "Before we begin, we need your consent for data processing and AI interactions."
            )

            # Show privacy information
            with st.expander("Privacy Information", expanded=True):
                st.write(
                    """
                **What data do we collect?**
                - Basic profile information for personalization
                - Chat interactions to improve your learning experience
                - Generated images and preferences
                - Usage analytics to improve the system
                
                **How do we use your data?**
                - To provide personalized tutoring experiences
                - To generate visual representations of your learning assistant
                - To improve our AI models (optional, with federated learning)
                - To ensure system security and compliance
                
                **Your rights:**
                - You can withdraw consent at any time
                - You can request data export or deletion
                - Your data is processed according to GDPR standards
                """
                )

            # Essential consents (required for basic functionality)
            st.subheader("Essential Consents (Required)")
            essential_consents = [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION]
            essential_values = {}

            tooltip_id_map = {
                ConsentType.DATA_PROCESSING: "data_processing_consent",
                ConsentType.AI_INTERACTION: "llm_interaction_consent", 
                ConsentType.IMAGE_GENERATION: "image_generation_consent",
                ConsentType.ANALYTICS: "analytics_consent"
            }

            for consent_type in essential_consents:
                display_name = self._get_consent_display_name(consent_type)
                tooltip_id = tooltip_id_map.get(consent_type, "data_processing_consent")

                essential_values[consent_type] = consent_checkbox(
                    display_name,
                    tooltip_id,
                    user_id=user_id,
                    consent_type=consent_type.value,
                    value=False,
                    key=f"essential_{consent_type.value}"
                )

            # Optional consents
            st.subheader("Optional Consents")
            optional_consents = [
                ConsentType.IMAGE_GENERATION,
                ConsentType.FEDERATED_LEARNING,
                ConsentType.ANALYTICS,
            ]
            optional_values = {}

            for consent_type in optional_consents:
                display_name = self._get_consent_display_name(consent_type)
                tooltip_id = tooltip_id_map.get(consent_type, "analytics_consent")

                optional_values[consent_type] = consent_checkbox(
                    display_name,
                    tooltip_id,
                    user_id=user_id,
                    consent_type=consent_type.value,
                    value=True,  # Default to True for optional consents
                    key=f"optional_{consent_type.value}"
                )

            # Check if essential consents are given
            essential_given = all(essential_values.values())

            if not essential_given:
                st.warning("Essential consents are required to use GITTE.")

            # Save consent button
            if tooltip_button(
                "Continue with These Settings", 
                "register_submit_button",
                disabled=not essential_given,
                context={"reason": "Essential consents required"} if not essential_given else None,
                type="primary"
            ):
                all_consents = {**essential_values, **optional_values}

                try:
                    # Record bulk consent
                    self.consent_service.record_bulk_consent(
                        user_id,
                        all_consents,
                        {
                            "source": "onboarding",
                            "timestamp": str(st.session_state.get("current_time", "")),
                        },
                    )

                    st.success(get_text("success_consent_recorded"))
                    st.balloons()

                    # Clear the consent UI flag
                    if "show_consent_ui" in st.session_state:
                        del st.session_state.show_consent_ui

                    return True

                except ConsentError as e:
                    st.error(f"Failed to record consent: {e}")
                    return False

            return False

        except Exception as e:
            logger.error(f"Error rendering onboarding consent: {e}")
            st.error("Error loading consent form. Please try again.")
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
