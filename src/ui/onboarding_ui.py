"""
Onboarding UI components for GITTE study participation system.
Implements the consent-first onboarding flow with pseudonym creation.
"""

from __future__ import annotations

import logging
import streamlit as st
from uuid import UUID

from src.ui.consent_ui import consent_ui
from src.ui.pseudonym_ui import pseudonym_ui
from src.services.consent_service import get_study_consent_service
from src.services.pseudonym_service import PseudonymService
from src.logic.onboarding import OnboardingStep

logger = logging.getLogger(__name__)


class OnboardingUI:
    """UI components for consent-first onboarding flow."""

    def __init__(self):
        self.consent_service = get_study_consent_service()
        self.pseudonym_service = PseudonymService()

    def render_consent_first_onboarding(self, user_id: UUID) -> bool:
        """
        Render the consent-first onboarding flow.
        
        Flow:
        1. Collect consents (buffer in session state)
        2. Create pseudonym
        3. Finalize: persist buffered consents with pseudonym
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if onboarding completed successfully
        """
        try:
            # Initialize onboarding state
            if "onboarding_step" not in st.session_state:
                st.session_state.onboarding_step = "consent"
            if "buffered_consents" not in st.session_state:
                st.session_state.buffered_consents = {}
            if "created_pseudonym_id" not in st.session_state:
                st.session_state.created_pseudonym_id = None

            current_step = st.session_state.onboarding_step

            # Progress indicator
            self._render_progress_indicator(current_step)

            # Step 1: Consent Collection
            if current_step == "consent":
                st.header("Step 1: Privacy Consent")
                
                consent_granted = consent_ui.render_onboarding_consent(user_id=user_id)
                
                if consent_granted:
                    st.session_state.onboarding_step = "pseudonym"
                    st.rerun()

            # Step 2: Pseudonym Creation
            elif current_step == "pseudonym":
                st.header("Step 2: Create Your Study Identity")
                
                # Show consent summary
                if st.session_state.buffered_consents:
                    with st.expander("✅ Consents Granted"):
                        for consent_key, granted in st.session_state.buffered_consents.items():
                            if granted:
                                st.write(f"• {consent_key.replace('_', ' ').title()}")
                
                pseudonym_created, pseudonym_id = pseudonym_ui.render_pseudonym_creation_screen(user_id)
                
                if pseudonym_created and pseudonym_id:
                    st.session_state.created_pseudonym_id = pseudonym_id
                    st.session_state.onboarding_step = "finalize"
                    st.rerun()

            # Step 3: Finalization
            elif current_step == "finalize":
                st.header("Step 3: Finalize Registration")
                
                success = self._finalize_onboarding(user_id)
                
                if success:
                    st.session_state.onboarding_step = "complete"
                    st.rerun()
                else:
                    st.error("Failed to finalize registration. Please try again.")
                    if st.button("Retry Finalization"):
                        st.rerun()

            # Step 4: Completion
            elif current_step == "complete":
                st.header("🎉 Welcome to GITTE!")
                
                st.success("Your registration is complete!")
                
                st.markdown("""
                ### What's Next?
                
                You can now:
                - Participate in the research study
                - Interact with the AI tutoring system
                - Generate personalized learning content
                
                Your data is protected by your pseudonym and you can manage your privacy settings at any time.
                """)
                
                if st.button("Start Using GITTE", type="primary"):
                    # Clear onboarding state
                    self._clear_onboarding_state()
                    return True

            return False

        except Exception as e:
            logger.error(f"Error in consent-first onboarding: {e}")
            st.error("An error occurred during onboarding. Please refresh and try again.")
            
            # Show debug info in development
            with st.expander("Debug Information"):
                st.code(f"Error: {str(e)}")
                st.code(f"Step: {st.session_state.get('onboarding_step', 'unknown')}")
            
            return False

    def _render_progress_indicator(self, current_step: str) -> None:
        """Render progress indicator for onboarding steps."""
        steps = ["consent", "pseudonym", "finalize", "complete"]
        step_names = ["Consent", "Identity", "Finalize", "Complete"]
        
        current_index = steps.index(current_step) if current_step in steps else 0
        
        # Create progress bar
        progress = (current_index + 1) / len(steps)
        st.progress(progress)
        
        # Create step indicators
        cols = st.columns(len(steps))
        
        for i, (step, name) in enumerate(zip(steps, step_names)):
            with cols[i]:
                if i < current_index:
                    st.markdown(f"✅ **{name}**")
                elif i == current_index:
                    st.markdown(f"🔄 **{name}**")
                else:
                    st.markdown(f"⏳ {name}")

    def _finalize_onboarding(self, user_id: UUID) -> bool:
        """
        Finalize onboarding by persisting buffered consents with the created pseudonym.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if finalization successful
        """
        try:
            pseudonym_id = st.session_state.get("created_pseudonym_id")
            buffered_consents = st.session_state.get("buffered_consents", {})
            
            if not pseudonym_id:
                st.error("No pseudonym found. Please go back and create a pseudonym.")
                return False
            
            if not buffered_consents:
                st.error("No consents found. Please go back and grant required consents.")
                return False
            
            # Show finalization progress
            with st.spinner("Finalizing your registration..."):
                # Convert pseudonym_id string back to UUID
                from uuid import UUID as UUIDClass
                pseudonym_uuid = UUIDClass(pseudonym_id)
                
                # Process consent collection with the created pseudonym
                result = self.consent_service.process_consent_collection(
                    pseudonym_uuid, 
                    buffered_consents
                )
                
                if result["success"] and result["can_proceed"]:
                    st.success("✅ Registration finalized successfully!")
                    
                    # Show summary
                    st.subheader("Registration Summary")
                    st.write(f"**Pseudonym ID:** {pseudonym_id}")
                    st.write(f"**Consents Granted:** {len([k for k, v in buffered_consents.items() if v])}")
                    st.write(f"**Registration Date:** {st.session_state.get('registration_date', 'Today')}")
                    
                    return True
                else:
                    failed_consents = result.get("failed_consents", [])
                    st.error(f"Failed to save consents: {', '.join(failed_consents)}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error finalizing onboarding: {e}")
            st.error(f"Finalization failed: {e}")
            return False

    def _clear_onboarding_state(self) -> None:
        """Clear onboarding-related session state."""
        keys_to_clear = [
            "onboarding_step",
            "buffered_consents", 
            "created_pseudonym_id",
            "consent_form_state",
            "pseudonym_input",
            "pseudonym_validation",
            "generated_pseudonym_id"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    def render_onboarding_status(self, user_id: UUID) -> None:
        """
        Render onboarding status for existing users.
        
        Args:
            user_id: User identifier
        """
        try:
            st.subheader("Onboarding Status")
            
            # Check if user has pseudonym
            pseudonym = self.pseudonym_service.get_user_pseudonym(user_id)
            
            if pseudonym:
                st.success("✅ Onboarding completed")
                st.write(f"**Pseudonym:** {pseudonym.pseudonym_text}")
                st.write(f"**Created:** {pseudonym.created_at.strftime('%Y-%m-%d')}")
                
                # Check consent status
                consent_status = self.consent_service.get_consent_status(pseudonym.pseudonym_id)
                granted_count = sum(1 for granted in consent_status.values() if granted)
                
                st.write(f"**Active Consents:** {granted_count}/{len(consent_status)}")
                
                # Management options
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Manage Consents"):
                        st.session_state.show_consent_management = True
                        st.rerun()
                
                with col2:
                    if st.button("Manage Pseudonym"):
                        st.session_state.show_pseudonym_management = True
                        st.rerun()
            else:
                st.warning("⚠️ Onboarding not completed")
                st.write("You need to complete the onboarding process to use GITTE.")
                
                if st.button("Complete Onboarding", type="primary"):
                    st.session_state.show_onboarding = True
                    st.rerun()
                    
        except Exception as e:
            logger.error(f"Error rendering onboarding status: {e}")
            st.error("Error loading onboarding status.")


# Global onboarding UI instance
onboarding_ui = OnboardingUI()


# Convenience functions
def render_consent_first_onboarding(user_id: UUID) -> bool:
    """Render consent-first onboarding flow."""
    return onboarding_ui.render_consent_first_onboarding(user_id)


def render_onboarding_status(user_id: UUID) -> None:
    """Render onboarding status."""
    onboarding_ui.render_onboarding_status(user_id)


def render_guided_onboarding_flow(user_id: UUID) -> bool:
    """Render guided onboarding flow (alias for consent-first flow)."""
    return onboarding_ui.render_consent_first_onboarding(user_id)


def render_onboarding_summary(user_id: UUID) -> None:
    """Render onboarding summary (alias for status)."""
    onboarding_ui.render_onboarding_status(user_id)