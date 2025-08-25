"""
Example integration of consent system with GITTE UI.
Demonstrates how to integrate consent checking into the main application flow.
"""

from uuid import UUID

import streamlit as st

from src.services.consent_middleware import check_consent_gate, get_missing_consents
from src.services.consent_service import get_consent_service
from src.services.session_manager import get_session_manager
from src.ui.consent_ui import render_consent_gate, render_onboarding_consent


def get_current_user_from_session() -> UUID | None:
    """Get current user ID from session state."""
    if "session_id" in st.session_state:
        session_manager = get_session_manager()
        session_data = session_manager.get_session(st.session_state.session_id)
        if session_data:
            return session_data["user_id"]
    return None


def require_authentication() -> UUID | None:
    """Require user authentication, redirect to login if needed."""
    user_id = get_current_user_from_session()
    if not user_id:
        st.error("Please log in to continue.")
        st.stop()
    return user_id


def show_consent_protected_chat():
    """Example of consent-protected chat functionality."""
    st.title("GITTE Chat")

    # Require authentication
    user_id = require_authentication()

    # Check consent gate for chat operation
    if not render_consent_gate(user_id, "chat"):
        st.info("Please provide the required consents to access chat functionality.")
        return

    # Chat functionality (placeholder)
    st.success("✅ Consent verified! Chat functionality is available.")

    user_input = st.text_input("Enter your message:")
    if user_input:
        st.write(f"You said: {user_input}")
        st.write("AI Response: This is a placeholder response.")


def show_consent_protected_image_generation():
    """Example of consent-protected image generation functionality."""
    st.title("Avatar Generation")

    # Require authentication
    user_id = require_authentication()

    # Check consent gate for AI interaction (which now covers image generation)
    if not render_consent_gate(user_id, "chat"):  # Use chat operation which requires AI_INTERACTION
        st.info("Please provide the required consents to access image generation.")
        return

    # Image generation functionality (placeholder)
    st.success("✅ Consent verified! Image generation is available.")

    prompt = st.text_input("Describe your avatar:")
    if st.button("Generate Avatar") and prompt:
        st.write(f"Generating avatar for: {prompt}")
        st.info("This would generate an image based on your description.")


def show_onboarding_flow():
    """Example onboarding flow with consent."""
    st.title("Welcome to GITTE!")

    # Require authentication
    user_id = require_authentication()

    # Check if user has already completed onboarding
    consent_service = get_consent_service()
    consent_status = consent_service.get_consent_status(user_id)

    # If user has some consents, they've likely been through onboarding
    if any(consent_status.values()):
        st.success("Welcome back! You've already completed the onboarding process.")
        st.write("Current consent status:")
        for consent_type, status in consent_status.items():
            status_icon = "✅" if status else "❌"
            st.write(f"{status_icon} {consent_type.replace('_', ' ').title()}")
        return

    # Show onboarding consent form
    st.write("Let's get you set up with GITTE. First, we need your consent for data processing.")

    if render_onboarding_consent(user_id):
        st.success("Onboarding complete! You can now use GITTE.")
        st.balloons()


def show_consent_dashboard():
    """Example consent management dashboard."""
    st.title("Privacy & Consent Dashboard")

    # Require authentication
    user_id = require_authentication()

    # Show consent summary
    consent_service = get_consent_service()
    consent_summary = consent_service.get_consent_summary(user_id)

    if consent_summary:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Consents Given", consent_summary.get("consents_given", 0))

        with col2:
            st.metric("Total Types", consent_summary.get("total_consent_types", 0))

        with col3:
            completion_rate = consent_summary.get("consent_completion_rate", 0)
            st.metric("Completion Rate", f"{completion_rate:.1%}")

    # Show what each consent enables
    st.subheader("What Your Consents Enable")

    operations = {
        "chat": "AI Chat Interactions",
        "survey": "Personalization Surveys",
        "federated_learning": "Privacy-Preserving Model Improvements",
    }

    for operation, description in operations.items():
        can_access = check_consent_gate(user_id, operation)
        status_icon = "✅" if can_access else "❌"

        with st.expander(f"{status_icon} {description}"):
            if can_access:
                st.success("You have all required consents for this feature.")
            else:
                missing = get_missing_consents(user_id, operation)
                st.warning(f"Missing consents: {', '.join([c.value for c in missing])}")

                if st.button(f"Enable {description}", key=f"enable_{operation}"):
                    st.info("This would redirect to consent management.")


def main():
    """Main application with consent integration examples."""
    st.set_page_config(
        page_title="GITTE - Consent Integration Example", page_icon="🤖", layout="wide"
    )

    # Sidebar navigation
    st.sidebar.title("GITTE Navigation")

    pages = {
        "Onboarding": show_onboarding_flow,
        "Chat (Consent Protected)": show_consent_protected_chat,
        "Image Generation (Consent Protected)": show_consent_protected_image_generation,
        "Consent Dashboard": show_consent_dashboard,
    }

    selected_page = st.sidebar.selectbox("Choose a page:", list(pages.keys()))

    # Show selected page
    if selected_page in pages:
        pages[selected_page]()

    # Show consent status in sidebar
    st.sidebar.divider()
    st.sidebar.subheader("Consent Status")

    user_id = get_current_user_from_session()
    if user_id:
        consent_service = get_consent_service()
        consent_status = consent_service.get_consent_status(user_id)

        for consent_type, status in consent_status.items():
            status_icon = "✅" if status else "❌"
            display_name = consent_type.replace("_", " ").title()
            st.sidebar.write(f"{status_icon} {display_name}")
    else:
        st.sidebar.info("Please log in to see consent status.")


if __name__ == "__main__":
    main()
