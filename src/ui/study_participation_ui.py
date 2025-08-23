"""
Study Participation UI components for GITTE system.
Provides Streamlit components for pseudonym creation and consent collection in the study participation flow.
"""

import logging
import re
from typing import Any, Dict
from uuid import UUID

import streamlit as st

from config.config import get_text
from src.data.models import StudyConsentType
from src.logic.pseudonym_logic import (
    InvalidPseudonymFormatError,
    PseudonymError,
    PseudonymNotUniqueError,
)
from src.services.consent_service import get_study_consent_service
from src.services.pseudonym_service import PseudonymService
from src.ui.tooltip_integration import form_submit_button

logger = logging.getLogger(__name__)


class StudyParticipationUI:
    """UI components for study participation onboarding flow."""

    def __init__(self):
        self.pseudonym_service = PseudonymService()
        self.consent_service = get_study_consent_service()

    def render_pseudonym_creation(self, user_id: UUID) -> Dict[str, Any] | None:
        """
        Render pseudonym creation interface with validation and error handling.

        Args:
            user_id: User identifier

        Returns:
            Dict containing pseudonym data if created successfully, None otherwise
        """
        st.title("🔐 Create Your Study Pseudonym")

        # Check if user already has a pseudonym
        existing_pseudonym = self.pseudonym_service.get_user_pseudonym(user_id)
        if existing_pseudonym:
            st.success("✅ You already have a study pseudonym!")
            self._render_existing_pseudonym_info(existing_pseudonym)
            
            if st.button("Continue to Consent Collection", type="primary"):
                return {
                    "pseudonym_created": True,
                    "pseudonym_id": existing_pseudonym.pseudonym_id,
                    "pseudonym_text": existing_pseudonym.pseudonym_text,
                    "existing": True
                }
            return None

        # Render pseudonym creation form
        st.markdown("""
        **Welcome to the GITTE Study!** 🎓

        To protect your privacy while participating in our research, you need to create a unique pseudonym. 
        This pseudonym will be used to identify your data throughout the study while keeping your real identity separate.
        """)

        # Instructions
        with st.expander("📋 How to Create Your Pseudonym", expanded=True):
            st.markdown("""
            **Your pseudonym should follow this format:**

            `[FirstLetter][BirthMonth][LastLetter][BirthYear][ParentLetters][CustomPart]`

            **Step-by-step example:**
            - Your name: **Maxima Schneider**
            - Born: **March 2001**
            - Father: **Jürgen**, Mother: **Angela**
            - Lucky number: **13**

            **Result:** `M03s2001AJ13`

            **Breakdown:**
            - `M` - First letter of your first name (uppercase)
            - `03` - Birth month (two digits, March = 03)
            - `s` - First letter of your last name (lowercase)
            - `2001` - Year of birth (four digits)
            - `AJ` - First letters of parents' names in alphabetical order (uppercase)
            - `13` - Your custom part (lucky number, word, etc.)
            """)

        # Pseudonym creation form
        with st.form("pseudonym_creation"):
            st.subheader("Create Your Pseudonym")

            pseudonym_text = st.text_input(
                "Enter your pseudonym:",
                placeholder="e.g., M03s2001AJ13",
                help="Follow the format shown above",
                max_chars=50
            )

            # Real-time validation display
            if pseudonym_text:
                validation_result = self._validate_pseudonym_format_ui(pseudonym_text)
                if validation_result["is_valid"]:
                    st.success("✅ Format looks good!")
                else:
                    st.error(f"❌ {validation_result['error_message']}")

            # Privacy reminder
            st.info("""
            **Privacy Reminder:** 
            - Your pseudonym will be used for all study data
            - It cannot be changed once created
            - Keep it private and memorable
            - Never share it with other participants
            """)

            # Submit buttons
            col1, col2 = st.columns(2)
            
            with col1:
                create_pseudonym = form_submit_button("Create Pseudonym", type="primary")
            
            with col2:
                show_help = form_submit_button("Need Help?")

        # Handle form submission
        if create_pseudonym:
            if not pseudonym_text:
                st.error("Please enter a pseudonym.")
                return None

            return self._handle_pseudonym_creation(user_id, pseudonym_text)

        if show_help:
            self._render_pseudonym_help()

        return None

    def render_consent_collection(self, pseudonym_id: UUID) -> Dict[str, Any] | None:
        """
        Render consent collection interface with multi-step validation.

        Args:
            pseudonym_id: Pseudonym identifier

        Returns:
            Dict containing consent data if completed successfully, None otherwise
        """
        st.title("📋 Study Participation Consent")

        try:
            # Check existing consent status
            consent_status = self.consent_service.check_consent_status(pseudonym_id)
        except Exception as e:
            logger.error(f"Error loading consent status: {e}")
            st.error("❌ Unable to load consent status. Please try again.")
            return None
        
        if consent_status.get("all_required_granted", False):
            st.success("✅ All required consents have been provided!")
            self._render_consent_summary(consent_status)
            
            if st.button("Continue to Survey", type="primary"):
                return {
                    "consents_completed": True,
                    "consent_status": consent_status,
                    "existing": True
                }
            return None

        # Render consent collection form
        st.markdown("""
        **Informed Consent for Study Participation** 📄

        Before participating in our research study, we need your informed consent for different aspects 
        of data collection and processing. Please read each section carefully and indicate your consent.
        """)

        # Progress indicator
        current_consents = consent_status.get("consent_status", {})
        granted_count = sum(1 for granted in current_consents.values() if granted)
        total_count = len(StudyConsentType)
        
        progress = granted_count / total_count if total_count > 0 else 0
        st.progress(progress, text=f"Consent Progress: {granted_count}/{total_count} completed")

        # Consent form
        with st.form("consent_collection"):
            consents = {}

            # Data Protection Consent
            st.subheader("🔒 Data Protection & Privacy")
            st.markdown("""
            **What this covers:**
            - Collection and storage of your study data under your pseudonym
            - Processing of your responses for research purposes
            - Secure handling of your information according to GDPR
            - Your right to withdraw and delete your data at any time
            """)
            
            consents["data_protection"] = st.checkbox(
                "I consent to data protection and privacy handling as described above",
                value=current_consents.get("data_protection", False),
                help="Required for study participation"
            )

            st.divider()

            # AI Interaction Consent
            st.subheader("🤖 AI Interaction & Processing")
            st.markdown("""
            **What this covers:**
            - Interaction with AI systems during the study
            - Processing of your messages and responses by AI models
            - Analysis of your learning patterns and preferences
            - Generation of personalized content based on your input
            """)
            
            consents["ai_interaction"] = st.checkbox(
                "I consent to AI interaction and processing as described above",
                value=current_consents.get("ai_interaction", False),
                help="Required for AI-based features"
            )

            st.divider()

            # Study Participation Consent
            st.subheader("📊 Research Study Participation")
            st.markdown("""
            **What this covers:**
            - Participation in the GITTE learning assistant research study
            - Use of your anonymized data for research analysis
            - Potential publication of aggregated, non-identifiable results
            - Contribution to educational technology research
            """)
            
            consents["study_participation"] = st.checkbox(
                "I consent to research study participation as described above",
                value=current_consents.get("study_participation", False),
                help="Required for study participation"
            )

            st.divider()

            # Consent validation
            required_consents = ["data_protection", "ai_interaction", "study_participation"]
            all_required_given = all(consents.get(ct, False) for ct in required_consents)

            if not all_required_given:
                st.warning("⚠️ All consents are required to participate in the study.")

            # Additional information
            with st.expander("📖 Additional Information", expanded=False):
                st.markdown("""
                **Your Rights:**
                - You can withdraw your consent at any time
                - You can request deletion of your data
                - You can access your stored data
                - You can contact us with questions about data handling

                **Data Security:**
                - All data is stored securely with encryption
                - Access is limited to authorized research personnel
                - Your pseudonym protects your identity
                - No personal identifiers are stored with research data

                **Contact Information:**
                - For questions about the study: [study contact]
                - For data protection concerns: [privacy contact]
                - For technical issues: [support contact]
                """)

            # Submit buttons
            col1, col2 = st.columns(2)
            
            with col1:
                submit_consents = form_submit_button(
                    "Submit Consents", 
                    type="primary",
                    disabled=not all_required_given
                )
            
            with col2:
                save_progress = form_submit_button("Save Progress")

        # Handle form submission
        if submit_consents:
            return self._handle_consent_submission(pseudonym_id, consents, complete=True)

        if save_progress:
            return self._handle_consent_submission(pseudonym_id, consents, complete=False)

        return None

    def render_study_participation_status(self, user_id: UUID) -> None:
        """
        Render current study participation status.

        Args:
            user_id: User identifier
        """
        st.subheader("📊 Your Study Participation Status")

        try:
            # Get pseudonym
            pseudonym = self.pseudonym_service.get_user_pseudonym(user_id)
            
            if not pseudonym:
                st.warning("⚠️ No study pseudonym found. Please create one to participate.")
                return

            # Get consent status
            consent_status = self.consent_service.check_consent_status(pseudonym.pseudonym_id)
        except Exception as e:
            logger.error(f"Error loading study participation status: {e}")
            st.error("❌ Unable to load study participation status. Please try again.")
            return

        # Status overview
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Pseudonym Status",
                "✅ Created" if pseudonym else "❌ Missing",
                f"ID: {str(pseudonym.pseudonym_id)[:8]}..." if pseudonym else None
            )

        with col2:
            granted_count = consent_status.get("granted_count", 0)
            total_count = consent_status.get("total_count", 0)
            st.metric(
                "Consents Given",
                f"{granted_count}/{total_count}",
                f"{consent_status.get('completion_rate', 0):.0%}"
            )

        with col3:
            can_proceed = consent_status.get("can_proceed_to_study", False)
            st.metric(
                "Study Status",
                "✅ Ready" if can_proceed else "⏳ Pending",
                "Can participate" if can_proceed else "Consents needed"
            )

        # Detailed status
        with st.expander("Detailed Status", expanded=False):
            st.write("**Pseudonym Information:**")
            st.write(f"- Pseudonym ID: `{pseudonym.pseudonym_id}`")
            st.write(f"- Created: {pseudonym.created_at}")
            st.write(f"- Status: {'Active' if pseudonym.is_active else 'Inactive'}")

            st.write("**Consent Status:**")
            for consent_type, granted in consent_status.get("consent_status", {}).items():
                status_icon = "✅" if granted else "❌"
                st.write(f"- {consent_type.replace('_', ' ').title()}: {status_icon}")

    def _validate_pseudonym_format_ui(self, pseudonym_text: str) -> Dict[str, Any]:
        """Validate pseudonym format for UI display."""
        try:
            validation = self.pseudonym_service.validate_pseudonym(pseudonym_text)
            return {
                "is_valid": validation.is_valid and validation.is_unique,
                "error_message": validation.error_message
            }
        except Exception as e:
            logger.error(f"Error validating pseudonym in UI: {e}")
            return {
                "is_valid": False,
                "error_message": "Validation error occurred"
            }

    def _handle_pseudonym_creation(self, user_id: UUID, pseudonym_text: str) -> Dict[str, Any] | None:
        """Handle pseudonym creation with error handling."""
        try:
            # Create pseudonym
            pseudonym = self.pseudonym_service.create_pseudonym(user_id, pseudonym_text)
            
            st.success("🎉 Pseudonym created successfully!")
            st.balloons()
            
            logger.info(f"Pseudonym created for user {user_id}")
            
            return {
                "pseudonym_created": True,
                "pseudonym_id": pseudonym.pseudonym_id,
                "pseudonym_text": pseudonym.pseudonym_text,
                "existing": False
            }

        except InvalidPseudonymFormatError as e:
            st.error(f"❌ Invalid pseudonym format: {e}")
            return None
        except PseudonymNotUniqueError as e:
            st.error(f"❌ Pseudonym already exists: {e}")
            st.info("💡 Please try a different custom part (e.g., different number or word)")
            return None
        except PseudonymError as e:
            st.error(f"❌ Error creating pseudonym: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating pseudonym: {e}")
            st.error("❌ An unexpected error occurred. Please try again.")
            return None

    def _handle_consent_submission(
        self, 
        pseudonym_id: UUID, 
        consents: Dict[str, bool], 
        complete: bool = True
    ) -> Dict[str, Any] | None:
        """Handle consent submission with error handling."""
        try:
            # Process consent collection
            result = self.consent_service.process_consent_collection(pseudonym_id, consents)
            
            if result.get("success", False):
                if complete and result.get("can_proceed", False):
                    st.success("🎉 All consents provided successfully!")
                    st.balloons()
                    
                    logger.info(f"Consents completed for pseudonym {pseudonym_id}")
                    
                    return {
                        "consents_completed": True,
                        "consent_status": result,
                        "existing": False
                    }
                elif not complete:
                    st.info("💾 Progress saved successfully!")
                    return None
                else:
                    st.warning("⚠️ Some required consents are missing.")
                    return None
            else:
                failed_consents = result.get("failed_consents", [])
                st.error(f"❌ Failed to process consents: {', '.join(failed_consents)}")
                return None

        except Exception as e:
            logger.error(f"Error processing consents: {e}")
            st.error("❌ An error occurred while processing consents. Please try again.")
            return None

    def _render_existing_pseudonym_info(self, pseudonym) -> None:
        """Render information about existing pseudonym."""
        with st.expander("Your Pseudonym Information", expanded=False):
            st.write(f"**Pseudonym:** `{pseudonym.pseudonym_text}`")
            st.write(f"**Created:** {pseudonym.created_at}")
            st.write(f"**Status:** {'Active' if pseudonym.is_active else 'Inactive'}")
            
            st.info("""
            **Remember:** Your pseudonym is used to identify your study data while protecting your privacy. 
            Keep it safe and don't share it with other participants.
            """)

    def _render_consent_summary(self, consent_status: Dict[str, Any]) -> None:
        """Render summary of current consent status."""
        with st.expander("Your Consent Summary", expanded=False):
            consents = consent_status.get("consent_status", {})
            
            for consent_type, granted in consents.items():
                status_icon = "✅" if granted else "❌"
                status_text = "Granted" if granted else "Not granted"
                st.write(f"**{consent_type.replace('_', ' ').title()}:** {status_icon} {status_text}")

    def _render_pseudonym_help(self) -> None:
        """Render additional help for pseudonym creation."""
        st.info("📞 **Need Help Creating Your Pseudonym?**")
        
        with st.expander("Detailed Examples", expanded=True):
            st.markdown("""
            **Example 1:**
            - Name: Sarah Johnson
            - Born: July 1995
            - Parents: David (father), Maria (mother)
            - Lucky number: 7
            - **Pseudonym:** `S07j1995DM7`

            **Example 2:**
            - Name: Alex Chen
            - Born: December 2000
            - Parents: Lisa (mother), Robert (father)
            - Favorite word: star
            - **Pseudonym:** `A12c2000LRstar`

            **Tips:**
            - Use uppercase for first letters of names
            - Use lowercase for last name initial
            - Always use 2 digits for month (01-12)
            - Always use 4 digits for year
            - Parent letters in alphabetical order
            - Custom part can be numbers, words, or both
            """)

        st.markdown("""
        **Still having trouble?**
        - Make sure you follow the exact format
        - Check that your birth month is 2 digits (e.g., 03 not 3)
        - Ensure parent letters are in alphabetical order
        - Try a different custom part if your pseudonym already exists
        """)


# Global study participation UI instance
study_participation_ui = StudyParticipationUI()


# Convenience functions
def render_pseudonym_creation(user_id: UUID) -> Dict[str, Any] | None:
    """Render pseudonym creation interface."""
    return study_participation_ui.render_pseudonym_creation(user_id)


def render_consent_collection(pseudonym_id: UUID) -> Dict[str, Any] | None:
    """Render consent collection interface."""
    return study_participation_ui.render_consent_collection(pseudonym_id)


def render_study_participation_status(user_id: UUID) -> None:
    """Render study participation status."""
    study_participation_ui.render_study_participation_status(user_id)