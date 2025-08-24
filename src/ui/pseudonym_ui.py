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
            Tuple of (success, pseudonym_id) where success indicates if pseudonym was created
        """
        try:
            st.title("🔐 Create Your Personal Pseudonym")
            
            # Instructions section
            st.markdown("""
            ### Instructions: How to create your personal pseudonym
            
            We do not store personal data (name, email, DOB). You provide a self-created pseudonym 
            so your answers stay anonymous and you can later find or delete your data.
            
            #### ✏️ How to create your pseudonym
            
            Combine:
            - First letter of your first name (uppercase)
            - Birth month (MM) 
            - First letter of your last name (lowercase)
            - Year of birth (YYYY)
            - First letters of parents' first names in alphabetical order (uppercase)
            - Any number/word (e.g., lucky number)
            
            #### ✅ Example
            **Name:** Maxima Schneider, born March 2001; parents: Angela & Jürgen; lucky number: 13  
            **Pseudonym:** M03s2001AJ13
            """)
            
            st.divider()
            
            # Pseudonym input form
            st.subheader("Generate Your Pseudonym")
            
            # Initialize session state for pseudonym
            if "pseudonym_input" not in st.session_state:
                st.session_state.pseudonym_input = ""
            if "pseudonym_validation" not in st.session_state:
                st.session_state.pseudonym_validation = None
            if "generated_pseudonym_id" not in st.session_state:
                st.session_state.generated_pseudonym_id = None
            
            # Input field
            pseudonym_text = st.text_input(
                "Enter your pseudonym:",
                value=st.session_state.pseudonym_input,
                placeholder="e.g., M03s2001AJ13",
                help="Follow the format above to create your unique pseudonym",
                key="pseudonym_text_input"
            )
            
            # Update session state
            st.session_state.pseudonym_input = pseudonym_text
            
            # Validation feedback
            if pseudonym_text:
                validation = self.pseudonym_service.validate_pseudonym(pseudonym_text)
                st.session_state.pseudonym_validation = validation
                
                if validation.is_valid and validation.is_unique:
                    st.success("✅ Pseudonym is valid and available!")
                elif validation.is_valid and not validation.is_unique:
                    st.error("❌ This pseudonym is already taken. Please modify it slightly.")
                else:
                    st.error(f"❌ {validation.error_message}")
            
            # Generate button
            col1, col2 = st.columns([2, 1])
            
            with col1:
                generate_button = st.button(
                    "Generate Key",
                    type="primary",
                    disabled=not (pseudonym_text and 
                                st.session_state.pseudonym_validation and 
                                st.session_state.pseudonym_validation.is_valid and 
                                st.session_state.pseudonym_validation.is_unique),
                    key="generate_pseudonym_btn"
                )
            
            with col2:
                if st.button("Clear", key="clear_pseudonym_btn"):
                    st.session_state.pseudonym_input = ""
                    st.session_state.pseudonym_validation = None
                    st.session_state.generated_pseudonym_id = None
                    st.rerun()
            
            # Handle pseudonym generation
            if generate_button:
                try:
                    pseudonym_response = self.pseudonym_service.create_pseudonym(
                        user_id=user_id,
                        pseudonym_text=pseudonym_text,
                        created_by="user_onboarding"
                    )
                    
                    if pseudonym_response:
                        st.session_state.generated_pseudonym_id = str(pseudonym_response.pseudonym_id)
                        st.success("🎉 Pseudonym created successfully!")
                        
                        # Show the participation key
                        st.subheader("Your Participation Key")
                        st.info("Please keep this key safe so you can delete your data later.")
                        
                        # Display the key in a copy-able format
                        participation_key = f"GITTE-{pseudonym_response.pseudonym_id}"
                        st.code(participation_key, language=None)
                        
                        # Copy button (using Streamlit's built-in functionality)
                        if st.button("📋 Copy Key", key="copy_key_btn"):
                            # Note: Actual copying to clipboard requires JavaScript
                            # For now, we'll show a message
                            st.toast("Key copied to clipboard!", icon="📋")
                        
                        st.markdown("---")
                        
                        # Confirmation section
                        st.subheader("Confirm and Continue")
                        st.write("I have saved my participation key and understand that:")
                        
                        confirmation_items = [
                            "This key is needed to access or delete my data later",
                            "I am responsible for keeping this key secure",
                            "I can now proceed with the study participation"
                        ]
                        
                        all_confirmed = True
                        for i, item in enumerate(confirmation_items):
                            confirmed = st.checkbox(
                                item,
                                key=f"confirm_item_{i}",
                                value=False
                            )
                            if not confirmed:
                                all_confirmed = False
                        
                        # Final confirmation button
                        if st.button(
                            "Confirm and Continue with Study",
                            type="primary",
                            disabled=not all_confirmed,
                            key="final_confirm_btn"
                        ):
                            return True, st.session_state.generated_pseudonym_id
                    else:
                        st.error("Failed to create pseudonym. Please try again.")
                        
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
            if st.session_state.generated_pseudonym_id:
                st.info("✅ Pseudonym created. Please confirm above to continue.")
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error rendering pseudonym creation screen: {e}")
            st.error("Error loading pseudonym creation screen. Please refresh and try again.")
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
                
                # Participation key
                participation_key = f"GITTE-{current_pseudonym.pseudonym_id}"
                st.subheader("Your Participation Key")
                st.code(participation_key, language=None)
                
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