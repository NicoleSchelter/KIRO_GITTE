"""
Main Streamlit application entry point for GITTE.
Implements the guided onboarding flow and main application interface.
"""

import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID

import streamlit as st

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.config import config, get_text
from src.data.models import UserRole
from src.ui.accessibility import apply_accessibility_features
from src.ui.admin_ui import render_admin_ui
from src.ui.auth_ui import render_logout_button, require_authentication
from src.ui.chat_ui import render_chat_interface, render_embodiment_design_chat
from src.ui.consent_ui import check_and_render_consent_gate, render_onboarding_consent
from src.ui.image_ui import render_image_gallery, render_image_generation_interface
from src.ui.onboarding_ui import render_guided_onboarding_flow, render_onboarding_summary
from src.ui.survey_ui import render_personalization_survey


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title=get_text("app_title"),
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Apply accessibility features
    apply_accessibility_features()

    # Initialize session state
    if "current_time" not in st.session_state:
        st.session_state.current_time = datetime.now()

    # Check authentication
    user_id = require_authentication()
    if not user_id:
        return

    # Render logout button in sidebar
    render_logout_button()

    # Check user role and route accordingly
    user_role = st.session_state.get("user_role")

    if user_role == UserRole.ADMIN.value:
        render_admin_interface(user_id)
    else:
        render_participant_interface(user_id)


def render_participant_interface(user_id: str) -> None:
    """Render interface for participant users with guided onboarding flow."""

    # Use the new onboarding system
    onboarding_complete = render_guided_onboarding_flow(UUID(user_id))

    if onboarding_complete:
        render_main_application(user_id)
    # If not complete, the onboarding UI handles the flow


def render_guided_onboarding(user_id: str) -> None:
    """Render the guided onboarding flow."""

    st.title("Welcome to GITTE! 🤖")
    st.write("Let's get you set up with your personalized learning assistant.")

    # Onboarding progress tracking
    onboarding_steps = ["consent", "survey", "design", "chat", "image_generation", "complete"]

    current_step = st.session_state.get("onboarding_step", "consent")

    # Progress indicator
    step_index = onboarding_steps.index(current_step) if current_step in onboarding_steps else 0
    progress = (step_index + 1) / len(onboarding_steps)

    st.progress(progress)
    st.write(
        f"Step {step_index + 1} of {len(onboarding_steps)}: {current_step.replace('_', ' ').title()}"
    )

    # Render current step
    if current_step == "consent":
        render_onboarding_consent_step(user_id)
    elif current_step == "survey":
        render_onboarding_survey_step(user_id)
    elif current_step == "design":
        render_onboarding_design_step(user_id)
    elif current_step == "chat":
        render_onboarding_chat_step(user_id)
    elif current_step == "image_generation":
        render_onboarding_image_step(user_id)
    elif current_step == "complete":
        render_onboarding_complete_step(user_id)


def render_onboarding_consent_step(user_id: str) -> None:
    """Render consent step of onboarding."""

    if render_onboarding_consent(user_id):
        st.session_state.onboarding_step = "survey"
        st.rerun()


def render_onboarding_survey_step(user_id: str) -> None:
    """Render survey step of onboarding."""

    survey_data = render_personalization_survey(user_id)

    if survey_data:
        st.session_state.survey_data = survey_data
        st.session_state.onboarding_step = "design"
        st.rerun()


def render_onboarding_design_step(user_id: str) -> None:
    """Render embodiment design step of onboarding."""

    embodiment_characteristics = render_embodiment_design_chat(user_id)

    if embodiment_characteristics:
        st.session_state.embodiment_characteristics = embodiment_characteristics
        st.session_state.onboarding_step = "chat"
        st.rerun()


def render_onboarding_chat_step(user_id: str) -> None:
    """Render chat introduction step of onboarding."""

    st.subheader("🗣️ Meet Your Learning Assistant")
    st.write("Now let's have a quick chat with your personalized learning assistant!")

    # Check consent for chat
    if not check_and_render_consent_gate(user_id, "chat"):
        return

    # Render chat interface
    render_chat_interface(user_id)

    # Continue button
    if st.button("Continue to Image Generation", type="primary"):
        st.session_state.onboarding_step = "image_generation"
        st.rerun()


def render_onboarding_image_step(user_id: str) -> None:
    """Render image generation step of onboarding."""

    st.subheader("🎨 Create Your Avatar")
    st.write("Generate a visual representation of your learning assistant!")

    # Check consent for image generation
    if not check_and_render_consent_gate(user_id, "image_generation"):
        return

    # Get embodiment data
    embodiment_data = st.session_state.get("embodiment_characteristics", {})

    # Render image generation interface
    generated_image = render_image_generation_interface(user_id, embodiment_data)

    if generated_image:
        st.session_state.generated_avatar = generated_image

    # Continue button
    if st.button("Complete Onboarding", type="primary"):
        st.session_state.onboarding_step = "complete"
        st.rerun()


def render_onboarding_complete_step(user_id: str) -> None:
    """Render onboarding completion step."""

    st.success("🎉 Onboarding Complete!")
    st.balloons()

    st.write(
        """
    Congratulations! You've successfully set up your personalized GITTE learning assistant.
    
    **What you've accomplished:**
    ✅ Provided consent for data processing
    ✅ Completed your learning preferences survey
    ✅ Designed your embodiment characteristics
    ✅ Had your first chat interaction
    ✅ Generated your avatar image
    
    You're now ready to start your personalized learning journey!
    """
    )

    # Show summary
    with st.expander("Your Setup Summary", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Learning Preferences")
            survey_data = st.session_state.get("survey_data", {})
            learning_prefs = survey_data.get("learning_preferences", {})
            st.write(f"**Style:** {learning_prefs.get('learning_style', 'Not specified')}")
            st.write(
                f"**Difficulty:** {learning_prefs.get('difficulty_preference', 'Not specified')}"
            )
            st.write(f"**Pace:** {learning_prefs.get('pace_preference', 'Not specified')}")

        with col2:
            st.subheader("Embodiment Design")
            embodiment = st.session_state.get("embodiment_characteristics", {})
            st.write(f"**Style:** {embodiment.get('appearance_style', 'Not specified')}")
            st.write(f"**Personality:** {embodiment.get('personality', 'Not specified')}")
            st.write(f"**Communication:** {embodiment.get('communication_style', 'Not specified')}")

    if st.button("Start Using GITTE", type="primary"):
        st.session_state.onboarding_complete = True
        st.rerun()


def render_main_application(user_id: str) -> None:
    """Render main application interface for completed users."""

    st.title("GITTE - Your Personalized Learning Assistant")

    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat", "🎨 Images", "📊 Progress", "⚙️ Settings"])

    with tab1:
        render_chat_tab(user_id)

    with tab2:
        render_images_tab(user_id)

    with tab3:
        render_progress_tab(user_id)

    with tab4:
        render_settings_tab(user_id)


def render_chat_tab(user_id: str) -> None:
    """Render chat tab."""

    if check_and_render_consent_gate(user_id, "chat"):
        render_chat_interface(user_id)


def render_images_tab(user_id: str) -> None:
    """Render images tab."""

    if check_and_render_consent_gate(user_id, "image_generation"):
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Generate New Avatar")
            embodiment_data = st.session_state.get("embodiment_characteristics", {})
            render_image_generation_interface(user_id, embodiment_data)

        with col2:
            st.subheader("Your Gallery")
            render_image_gallery(user_id)


def render_progress_tab(user_id: str) -> None:
    """Render progress tracking tab."""

    st.subheader("📈 Your Learning Progress")

    # Mock progress data - would be real data in production
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Chat Sessions", "12", "+3")

    with col2:
        st.metric("Images Generated", "8", "+2")

    with col3:
        st.metric("Topics Explored", "5", "+1")

    # Recent activity
    st.subheader("Recent Activity")
    st.info("Progress tracking will be enhanced in future updates.")


def render_settings_tab(user_id: str) -> None:
    """Render settings tab."""

    st.subheader("⚙️ Settings")

    # Onboarding status
    with st.expander("Onboarding Status", expanded=False):
        render_onboarding_summary(UUID(user_id))

    # User preferences
    with st.expander("Learning Preferences", expanded=False):
        st.info("Preference updates will be available in future updates.")

    # Privacy settings
    with st.expander("Privacy & Consent", expanded=False):
        if st.button("Manage Consent Settings"):
            st.session_state.show_consent_ui = True
            st.rerun()

    # Account settings
    with st.expander("Account Settings", expanded=False):
        st.write(f"**Username:** {st.session_state.get('username', 'Unknown')}")
        st.write(f"**Role:** {st.session_state.get('user_role', 'Unknown')}")
        st.write(f"**Member Since:** {st.session_state.get('current_time', 'Unknown')}")


def render_admin_interface(user_id: str) -> None:
    """Render admin interface."""

    render_admin_ui(user_id)


def render_system_status() -> None:
    """Render system status for debugging."""

    with st.sidebar, st.expander("System Status", expanded=False):
        st.write("**Environment:**", config.environment)
        st.write("**Database DSN:**", config.database.dsn)
        st.write("**LLM URL:**", config.llm.ollama_url)

        st.subheader("Feature Flags")
        for flag_name in config.feature_flags.__dataclass_fields__:
            flag_value = getattr(config.feature_flags, flag_name)
            st.write(f"**{flag_name}:**", "✅" if flag_value else "❌")


if __name__ == "__main__":
    main()
