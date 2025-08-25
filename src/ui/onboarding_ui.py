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
        1. Check if user has already completed onboarding
        2. Collect consents (buffer in session state)
        3. Create pseudonym
        4. Finalize: persist buffered consents with pseudonym
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if onboarding completed successfully
        """
        try:
            # First, check if user has already completed onboarding
            if self._is_onboarding_already_complete(user_id):
                # User has already completed onboarding, set flag and return
                st.session_state.onboarding_complete = True
                return True
            
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
                
                pseudonym_created, pseudonym_key = pseudonym_ui.render_pseudonym_creation_screen(user_id)
                
                if pseudonym_created and pseudonym_key:
                    # Store both the pseudonym text (key) and UUID
                    st.session_state.created_pseudonym_key = pseudonym_key
                    # Get the actual UUID from the pseudonym creation session state
                    pseudonym_uuid = st.session_state.get("generated_pseudonym_uuid")
                    if pseudonym_uuid:
                        st.session_state.created_pseudonym_id = str(pseudonym_uuid)
                        st.session_state.created_pseudonym_uuid = pseudonym_uuid
                    else:
                        # Fallback: use the string ID if UUID not available
                        st.session_state.created_pseudonym_id = st.session_state.get("generated_pseudonym_id", pseudonym_key)
                    
                    # Check if buffered consents still exist (Flow A) or were consumed by Flow B
                    buffered_consents_exist = bool(st.session_state.get("buffered_consents"))
                    logger.info(f"Pseudonym created for user {user_id}, buffered_consents exist: {buffered_consents_exist}")
                    
                    if buffered_consents_exist:
                        # Flow A - buffered consents still exist, need finalization step
                        st.session_state.onboarding_step = "finalize"
                        logger.info(f"Moving to finalize step (Flow A) for user {user_id}")
                    else:
                        # Flow B - buffered consents were consumed during pseudonym creation, go directly to complete
                        st.session_state.onboarding_step = "complete"
                        logger.info(f"Moving to complete step (Flow B) for user {user_id}")
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
                
                # Add balloons celebration
                st.balloons()
                
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
                    # Set completion flag for main application
                    st.session_state.onboarding_complete = True
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
        Note: In Flow B, this step may be skipped as consents are already persisted.
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if finalization successful
        """
        try:
            pseudonym_key = st.session_state.get("created_pseudonym_key")
            buffered_consents = st.session_state.get("buffered_consents", {})
            
            if not pseudonym_key:
                st.error("No pseudonym found. Please go back and create a pseudonym.")
                return False
            
            # Check if this is Flow B (consents already persisted)
            if not buffered_consents:
                # Flow B was used - consents already persisted during pseudonym creation
                st.success("✅ Registration already completed during pseudonym creation!")
                
                # Show summary
                st.subheader("Registration Summary")
                st.write(f"**Participation Key:** {pseudonym_key}")
                st.write(f"**Status:** Active")
                st.write("**Consents:** Already granted and saved")
                
                return True
            
            # Legacy flow - need to persist consents
            # This should rarely happen with the new Flow B
            st.warning("Using legacy consent persistence flow...")
            
            # Show finalization progress
            with st.spinner("Finalizing your registration..."):
                # For legacy flow, we need to find the pseudonym UUID
                # This is a fallback and should be improved
                try:
                    # Try to get the pseudonym UUID from the service
                    pseudonym_response = self.pseudonym_service.get_user_pseudonym(user_id)
                    if pseudonym_response:
                        pseudonym_uuid = pseudonym_response.pseudonym_id
                        
                        # Process consent collection with the created pseudonym
                        result = self.consent_service.process_consent_collection(
                            pseudonym_uuid, 
                            buffered_consents
                        )
                        
                        if result["success"] and result["can_proceed"]:
                            st.success("✅ Registration finalized successfully!")
                            
                            # Show summary
                            st.subheader("Registration Summary")
                            st.write(f"**Participation Key:** {pseudonym_key}")
                            st.write(f"**Consents Granted:** {len([k for k, v in buffered_consents.items() if v])}")
                            
                            return True
                        else:
                            failed_consents = result.get("failed_consents", [])
                            st.error(f"Failed to save consents: {', '.join(failed_consents)}")
                            return False
                    else:
                        st.error("Could not find created pseudonym for consent persistence.")
                        return False
                        
                except Exception as e:
                    logger.error(f"Error in legacy consent persistence: {e}")
                    st.error("Failed to persist consents. Please try again.")
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
            "created_pseudonym_uuid",
            "consent_form_state",
            "pseudonym_input",
            "pseudonym_validation",
            "generated_pseudonym_id",
            "generated_pseudonym_key",
            "generated_pseudonym_uuid"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

    def _is_onboarding_already_complete(self, user_id: UUID) -> bool:
        """
        Check if user has already completed onboarding.
        
        Since user-pseudonym connections have been removed for privacy,
        we check for:
        1. Session state indicating completion
        2. Recent successful pseudonym creation in this session
        3. Database-driven verification (fallback when session state is unreliable)
        
        Args:
            user_id: User identifier
            
        Returns:
            bool: True if onboarding appears complete
        """
        # Check if user has session state indicating completion
        if st.session_state.get("onboarding_complete", False):
            logger.info(f"Onboarding completion check for user {user_id} - returning True (session state flag set)")
            return True
            
        # Check if user just completed pseudonym creation with consents in this session
        if (
            st.session_state.get("created_pseudonym_key") and 
            st.session_state.get("onboarding_step") == "complete"
        ):
            logger.info(f"Onboarding completion check for user {user_id} - returning True (just completed in session)")
            return True
        
        # Database-driven verification as fallback
        try:
            # Check if user has created any pseudonyms (indicates onboarding started/completed)
            # Since we removed user-pseudonym connections, we check for recent pseudonym activity
            from src.data.database import get_session
            from src.data.repositories import PseudonymRepository, StudyConsentRepository
            from src.data.models import Pseudonym  # Import Pseudonym model directly
            
            with get_session() as session:
                pseudonym_repo = PseudonymRepository(session)
                consent_repo = StudyConsentRepository(session)
                
                # Strategy 1: Check for very recent pseudonyms (last 1 hour - more precise)
                from datetime import datetime, timedelta
                very_recent_time = datetime.utcnow() - timedelta(hours=1)
                
                # Get very recent pseudonyms first
                very_recent_pseudonyms = session.query(Pseudonym).filter(
                    Pseudonym.created_at >= very_recent_time,
                    Pseudonym.is_active == True
                ).order_by(Pseudonym.created_at.desc()).all()
                
                logger.info(f"Found {len(very_recent_pseudonyms)} very recent pseudonyms for completion check")
                
                for pseudonym in very_recent_pseudonyms:
                    # Check if this pseudonym has all required consents
                    consent_records = consent_repo.get_by_pseudonym(pseudonym.pseudonym_id)
                    required_consent_types = ['data_protection', 'ai_interaction', 'study_participation']
                    
                    granted_consents = [record.consent_type for record in consent_records if record.granted and not record.revoked_at]
                    
                    logger.info(f"Pseudonym {pseudonym.pseudonym_id} has consents: {granted_consents}")
                    
                    if all(ct in granted_consents for ct in required_consent_types):
                        # Found a recently created pseudonym with all consents
                        logger.info(f"Found completed pseudonym {pseudonym.pseudonym_id}")
                        
                        # IMPORTANT: We can't reliably link this to the current user due to privacy design
                        # So we'll be more conservative and NOT mark onboarding as complete
                        # This will force the user to go through onboarding, ensuring they create their own pseudonym
                        logger.info(f"Onboarding completion check for user {user_id} - returning False (conservative approach due to privacy design)")
                        return False
                
                # Strategy 2: Fallback to broader search (last 24 hours) if nothing found
                broader_time = datetime.utcnow() - timedelta(hours=24)
                
                broader_pseudonyms = session.query(Pseudonym).filter(
                    Pseudonym.created_at >= broader_time,
                    Pseudonym.is_active == True
                ).order_by(Pseudonym.created_at.desc()).limit(10).all()  # Limit to prevent excessive checks
                
                logger.info(f"Checking {len(broader_pseudonyms)} broader recent pseudonyms for completion")
                
                for pseudonym in broader_pseudonyms:
                    # Check if this pseudonym has all required consents
                    consent_records = consent_repo.get_by_pseudonym(pseudonym.pseudonym_id)
                    required_consent_types = ['data_protection', 'ai_interaction', 'study_participation']
                    
                    granted_consents = [record.consent_type for record in consent_records if record.granted and not record.revoked_at]
                    
                    if all(ct in granted_consents for ct in required_consent_types):
                        # Found a completed pseudonym
                        logger.info(f"Found completed pseudonym {pseudonym.pseudonym_id} in broader search")
                        
                        # IMPORTANT: We can't reliably link this to the current user due to privacy design
                        # So we'll be more conservative and NOT mark onboarding as complete
                        logger.info(f"Onboarding completion check for user {user_id} - returning False (conservative approach due to privacy design)")
                        return False
                        
        except Exception as e:
            logger.error(f"Error in database-driven completion check: {e}")
            # On error, default to not complete for security
        
        logger.info(f"Onboarding completion check for user {user_id} - returning False (no completion indicators)")
        return False

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