"""
Pseudonym UI components for GITTE study participation system.
Provides Streamlit components for pseudonym creation and management.
"""

from __future__ import annotations

import logging
import streamlit as st
from uuid import UUID

from src.services.pseudonym_service import PseudonymService
from src.logic.pseudonym_logic import InvalidPseudonymFormatError, PseudonymNotUniqueError, PseudonymError

logger = logging.getLogger(__name__)


class PseudonymUI:
    """UI components for pseudonym management."""

    def __init__(self):
        self.pseudonym_service = PseudonymService()

    def render_pseudonym_creation_screen(self, user_id: UUID) -> tuple[bool, str | None]:
        """
        Render the pseudonym creation screen for onboarding.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (success, pseudonym_text) where success indicates if pseudonym was confirmed
        """
        try:
            # First check if user already has a pseudonym
            existing_pseudonym = self.pseudonym_service.get_user_pseudonym(user_id)
            
            if existing_pseudonym:
                # User already has a pseudonym - show confirmation screen
                return self._render_existing_pseudonym_confirmation(existing_pseudonym)
            
            st.title("🔐 Create Your Personal Pseudonym")
            
            # Instructions section
            st.markdown("""
            ### Create Your Participation Key (Pseudonym)
            
            **Important:** Your pseudonym IS your participation key. We do not store personal data (name, email, DOB). 
            You create a unique pseudonym that will be your key to access or delete your study data later.
            
            #### ✏️ How to create your pseudonym
            
            Combine these elements to create a unique identifier:
            - First letter of your first name (uppercase)
            - Birth month (MM) 
            - First letter of your last name (lowercase)
            - Year of birth (YYYY)
            - First letters of parents' first names in alphabetical order (uppercase)
            - Any number/word (e.g., lucky number)
            
            #### ✅ Example
            **Name:** Maxima Schneider, born March 2001; parents: Angela & Jürgen; lucky number: 13  
            **Pseudonym/Key:** M03s2001AJ13
            
            💡 **Remember:** This pseudonym will be your only way to identify and delete your data later!
            """)
            
            st.divider()
            
            # Pseudonym input form
            st.subheader("Create Your Participation Key")
            
            # Initialize session state for pseudonym
            if "pseudonym_input" not in st.session_state:
                st.session_state.pseudonym_input = ""
            if "pseudonym_validation" not in st.session_state:
                st.session_state.pseudonym_validation = None
            if "generated_pseudonym_id" not in st.session_state:
                st.session_state.generated_pseudonym_id = None
            if "generated_pseudonym_key" not in st.session_state:
                st.session_state.generated_pseudonym_key = None
            
            # Input field with immediate validation
            def validate_on_change():
                """Validate pseudonym on input change."""
                pseudonym_text = st.session_state.pseudonym_text_input
                st.session_state.pseudonym_input = pseudonym_text
                if pseudonym_text:
                    validation = self.pseudonym_service.validate_pseudonym(pseudonym_text)
                    st.session_state.pseudonym_validation = validation
                else:
                    st.session_state.pseudonym_validation = None
            
            pseudonym_text = st.text_input(
                "Enter your pseudonym:",
                value=st.session_state.pseudonym_input,
                placeholder="e.g., M03s2001AJ13",
                help="Follow the format above to create your unique pseudonym",
                key="pseudonym_text_input",
                on_change=validate_on_change
            )
            
            # Update session state
            st.session_state.pseudonym_input = pseudonym_text
            
            # Validation feedback - validate on every input change
            if pseudonym_text:
                validation = self.pseudonym_service.validate_pseudonym(pseudonym_text)
                st.session_state.pseudonym_validation = validation
                
                if validation.is_valid and validation.is_unique:
                    st.success("✅ Pseudonym is valid and available!")
                elif validation.is_valid and not validation.is_unique:
                    st.error("❌ This pseudonym is already taken. Please modify it slightly.")
                else:
                    st.error(f"❌ {validation.error_message}")
            else:
                # Clear validation when input is empty
                st.session_state.pseudonym_validation = None
            
            # Generate button - enabled as soon as input is valid
            col1, col2 = st.columns([2, 1])
            
            # Check if button should be enabled
            button_enabled = (pseudonym_text and 
                            st.session_state.pseudonym_validation and 
                            st.session_state.pseudonym_validation.is_valid and 
                            st.session_state.pseudonym_validation.is_unique)
            
            with col1:
                generate_button = st.button(
                    "✅ Confirm This Pseudonym",
                    type="primary",
                    disabled=not button_enabled,
                    key="generate_pseudonym_btn",
                    help="Click to confirm this pseudonym as your participation key"
                )
                
                # Handle Enter key press (simulate button click)
                if button_enabled and pseudonym_text != st.session_state.get("last_pseudonym_text", ""):
                    # Check if user pressed Enter (this is a workaround since Streamlit doesn't have direct Enter handling)
                    st.session_state.last_pseudonym_text = pseudonym_text
            
            with col2:
                if st.button("Clear", key="clear_pseudonym_btn"):
                    st.session_state.pseudonym_input = ""
                    st.session_state.pseudonym_validation = None
                    st.session_state.generated_pseudonym_id = None
                    st.session_state.generated_pseudonym_key = None
                    st.session_state.last_pseudonym_text = ""
                    st.rerun()
            
            # Handle pseudonym generation
            if generate_button:
                try:
                    # Check if we have staged consents from Flow B
                    staged_consents = st.session_state.get("buffered_consents", {})
                    
                    if staged_consents:
                        # Flow B: Handle pseudonym with staged consents
                        from src.logic.pseudonym_logic import PseudonymLogic
                        from src.logic.consent_logic import ConsentLogic
                        from src.data.repositories import PseudonymRepository, StudyConsentRepository
                        from src.data.database_factory import get_session
                        
                        with get_session() as session:
                            pseudonym_logic = PseudonymLogic(PseudonymRepository(session))
                            consent_logic = ConsentLogic(StudyConsentRepository(session))
                            
                            # Check if user already has a pseudonym
                            existing_pseudonym = pseudonym_logic.pseudonym_repository.get_by_user_id(user_id)
                            
                            if existing_pseudonym and existing_pseudonym.pseudonym_text == pseudonym_text:
                                # User already has this exact pseudonym - just link consents
                                staging_result = consent_logic.stage_consents(user_id, staged_consents)
                                
                                if staging_result["success"]:
                                    # Persist consents to existing pseudonym
                                    link_result = consent_logic.persist_staged_consents(
                                        existing_pseudonym.pseudonym_id,
                                        staging_result["staged_consents"]
                                    )
                                    
                                    if link_result["success"]:
                                        # Store the pseudonym text as the key
                                        st.session_state.generated_pseudonym_key = pseudonym_text
                                        st.session_state.generated_pseudonym_id = str(existing_pseudonym.pseudonym_id)
                                        
                                        # Clear buffered consents
                                        if "buffered_consents" in st.session_state:
                                            del st.session_state.buffered_consents
                                        
                                        st.success("🎉 Participation key confirmed and consents saved successfully!")
                                    else:
                                        st.error(f"Failed to link consents: {link_result.get('error', 'Unknown error')}")
                                        return False, None
                                else:
                                    st.error("Failed to stage consents")
                                    return False, None
                            else:
                                # Create new pseudonym with staged consents
                                staging_result = consent_logic.stage_consents(user_id, staged_consents)
                                
                                if staging_result["success"]:
                                    # Create pseudonym with staged consents
                                    creation_result = pseudonym_logic.create_pseudonym_with_consents(
                                        user_id=user_id,
                                        pseudonym_text=pseudonym_text,
                                        staged_consents=staging_result["staged_consents"],
                                        created_by="user_onboarding"
                                    )
                                    
                                    if creation_result["success"]:
                                        pseudonym = creation_result["pseudonym"]
                                        # Store the pseudonym text as the key, not the UUID
                                        st.session_state.generated_pseudonym_key = pseudonym_text
                                        st.session_state.generated_pseudonym_id = str(pseudonym.pseudonym_id)  # Keep for compatibility
                                        
                                        # Clear buffered consents
                                        if "buffered_consents" in st.session_state:
                                            del st.session_state.buffered_consents
                                        
                                        st.success("🎉 Participation key created and consents saved successfully!")
                                    else:
                                        st.error(f"Failed to create pseudonym: {creation_result.get('error', 'Unknown error')}")
                                        return False, None
                                else:
                                    st.error("Failed to stage consents")
                                    return False, None
                    else:
                        # Legacy flow: Create pseudonym only
                        pseudonym_response = self.pseudonym_service.create_pseudonym(
                            user_id=user_id,
                            pseudonym_text=pseudonym_text,
                            created_by="user_onboarding"
                        )
                        
                        if pseudonym_response:
                            # Store the pseudonym text as the key, not the UUID
                            st.session_state.generated_pseudonym_key = pseudonym_text
                            st.session_state.generated_pseudonym_id = str(pseudonym_response.pseudonym_id)  # Keep for compatibility
                            st.success("🎉 Participation key created successfully!")
                        else:
                            st.error("Failed to create pseudonym. Please try again.")
                            return False, None
                    
                    # Show the participation key (which is the pseudonym itself)
                    st.subheader("Your Participation Key")
                    st.success("✅ Your participation key has been generated!")
                    st.info("**Important:** Your participation key is your pseudonym. Keep it safe - you'll need it to delete your data later.")
                    st.info("We do not store personal data. Your pseudonym links your study responses and allows you to delete them later.")
                    
                    # Display the pseudonym as the key
                    st.markdown("**Your Participation Key:**")
                    st.code(pseudonym_text, language=None)
                    
                    # Copy button for the pseudonym
                    if st.button("📋 Copy Pseudonym", key="copy_key_btn"):
                        st.toast(f"Pseudonym '{pseudonym_text}' copied! Keep it safe.", icon="📋")
                    
                    st.markdown("---")
                    
                    # Confirmation section
                    st.subheader("Confirm and Continue")
                    st.markdown(f"""
                    **Please confirm:** I understand that my pseudonym `{pseudonym_text}` will be used to:
                    - Link my study responses anonymously
                    - Allow me to delete my data later if needed
                    - Keep my personal information private
                    """)
                    
                    # Single confirmation checkbox
                    final_confirmation = st.checkbox(
                        f"✅ I confirm that '{pseudonym_text}' is my participation key and I will keep it safe",
                        key="final_pseudonym_confirmation",
                        value=False
                    )
                    
                    # Final confirmation button
                    if st.button(
                        "Continue to Study",
                        type="primary",
                        disabled=not final_confirmation,
                        key="final_confirm_btn"
                    ):
                        # Return the pseudonym text as the key, not the UUID
                        return True, pseudonym_text
                        
                except InvalidPseudonymFormatError as e:
                    st.error(f"Invalid pseudonym format: {e}")
                except PseudonymNotUniqueError as e:
                    st.error(f"Pseudonym not unique: {e}")
                except PseudonymError as e:
                    st.error(f"Error creating pseudonym: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error creating pseudonym: {e}")
                    st.error("An unexpected error occurred. Please try again.")
            
            # Show current status
            if st.session_state.get("generated_pseudonym_key"):
                st.info("✅ Participation key created. Please confirm above to continue.")
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error rendering pseudonym creation screen: {e}")
            st.error("Error loading pseudonym creation screen. Please refresh and try again.")
            return False, None

    def _render_existing_pseudonym_confirmation(self, existing_pseudonym) -> tuple[bool, str | None]:
        """
        Render confirmation screen for users who already have a pseudonym.
        
        Args:
            existing_pseudonym: The existing pseudonym object
            
        Returns:
            Tuple of (success, pseudonym_text) where success indicates if user confirmed
        """
        try:
            st.title("🔐 Your Participation Key")
            
            st.success("✅ You already have a participation key!")
            
            st.markdown("""
            ### Your Existing Participation Key
            
            You have already created a participation key (pseudonym) for this study.
            This key will be used to link your study responses and allow you to delete your data later if needed.
            """)
            
            # Display the existing pseudonym as the participation key
            st.subheader("Your Participation Key")
            st.info("**Important:** This is your participation key. Keep it safe - you'll need it to delete your data later.")
            
            # Display the pseudonym text as the key
            st.markdown("**Your Participation Key:**")
            st.code(existing_pseudonym.pseudonym_text, language=None)
            
            # Copy button for the pseudonym
            if st.button("📋 Copy Participation Key", key="copy_existing_key_btn"):
                st.toast(f"Participation key '{existing_pseudonym.pseudonym_text}' copied! Keep it safe.", icon="📋")
            
            st.markdown("---")
            
            # Confirmation section
            st.subheader("Confirm and Continue")
            st.markdown(f"""
            **Please confirm:** I understand that my participation key `{existing_pseudonym.pseudonym_text}` will be used to:
            - Link my study responses anonymously
            - Allow me to delete my data later if needed
            - Keep my personal information private
            """)
            
            # Single confirmation checkbox
            final_confirmation = st.checkbox(
                f"✅ I confirm that '{existing_pseudonym.pseudonym_text}' is my participation key",
                key="existing_pseudonym_confirmation",
                value=False
            )
            
            # Final confirmation button
            if st.button(
                "Continue to Study",
                type="primary",
                disabled=not final_confirmation,
                key="existing_confirm_btn"
            ):
                # Return the pseudonym text as the key
                return True, existing_pseudonym.pseudonym_text
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error rendering existing pseudonym confirmation: {e}")
            st.error("Error loading participation key confirmation. Please try again.")
            return False, None

    def render_pseudonym_management(self, user_id: UUID) -> None:
        """
        Render pseudonym management interface for existing users.
        
        Args:
            user_id: User identifier
        """
        try:
            st.title("Pseudonym Management")
            
            # Get current pseudonym
            current_pseudonym = self.pseudonym_service.get_user_pseudonym(user_id)
            
            if current_pseudonym:
                st.subheader("Current Pseudonym")
                st.info(f"Your pseudonym: **{current_pseudonym.pseudonym_text}**")
                st.write(f"Created: {current_pseudonym.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"Status: {'Active' if current_pseudonym.is_active else 'Inactive'}")
                
                # Participation key (the pseudonym itself)
                st.subheader("Your Participation Key")
                st.info("Your participation key is your pseudonym. Use this to delete your data if needed.")
                st.code(current_pseudonym.pseudonym_text, language=None)
                
                # Management actions
                st.subheader("Management Actions")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Deactivate Pseudonym", type="secondary"):
                        if st.button("Confirm Deactivation", key="confirm_deactivate"):
                            success = self.pseudonym_service.deactivate_user_pseudonym(user_id)
                            if success:
                                st.success("Pseudonym deactivated successfully.")
                                st.rerun()
                            else:
                                st.error("Failed to deactivate pseudonym.")
                
                with col2:
                    if st.button("Export Data", type="secondary"):
                        st.info("Data export functionality will be implemented in a future update.")
            
            else:
                st.warning("No pseudonym found for your account.")
                if st.button("Create Pseudonym", type="primary"):
                    # Redirect to pseudonym creation
                    st.session_state.show_pseudonym_creation = True
                    st.rerun()
                    
        except Exception as e:
            logger.error(f"Error rendering pseudonym management: {e}")
            st.error("Error loading pseudonym management. Please try again.")


# Global pseudonym UI instance
pseudonym_ui = PseudonymUI()


# Convenience functions
def render_pseudonym_creation_screen(user_id: UUID) -> tuple[bool, str | None]:
    """Render pseudonym creation screen."""
    return pseudonym_ui.render_pseudonym_creation_screen(user_id)


def render_pseudonym_management(user_id: UUID) -> None:
    """Render pseudonym management interface."""
    pseudonym_ui.render_pseudonym_management(user_id)