#allowed monkey patch for stable diffusion
import os
os.environ.setdefault("STREAMLIT_SERVER_FILE_WATCHER_TYPE", "none")

try:
    import torch
    if not hasattr(torch.classes, "__path__") or not isinstance(torch.classes.__path__, list):
        torch.classes.__path__ = []
except Exception:
    pass

#Main Streamlit application entry point for GITTE.
#Implements the guided onboarding flow and main application interface.

import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID
# --- UUID normalization helper ---
from typing import Union

def to_uuid(value: Union[str, UUID]) -> UUID:
    """Return a UUID, accepting either str or UUID."""
    return value if isinstance(value, UUID) else UUID(str(value))

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
from src.ui.tooltip_integration import get_tooltip_integration, tooltip_button


def main():
    """Main application entry point."""
    # Set page config FIRST before any other Streamlit operations
    try:
        st.set_page_config(
            page_title=get_text("app_title"),
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="expanded",
        )
    except st.errors.StreamlitAPIException:
        # Page config already set, ignore
        pass

    # Apply comprehensive accessibility features
    apply_accessibility_features()
    _apply_enhanced_accessibility_features()
    
    # Initialize tooltip system
    tooltip_integration = get_tooltip_integration()

    # Initialize session state safely
    from src.ui.session_state_manager import SessionStateManager
    SessionStateManager.initialize_session_state()
    
    # Set current time if not already set
    if not SessionStateManager.get('current_time'):
        SessionStateManager.set('current_time', datetime.now())

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

    # Check if user has already completed onboarding by checking session state or actual completion
    user_uuid = to_uuid(user_id)
    
    # Check session state first
    session_complete = st.session_state.get('onboarding_complete', False)
    
    # If session state indicates completion, show main app
    if session_complete:
        render_main_application(user_id)
        return
    
    # Otherwise, use the NEW consent-first onboarding system which will detect completion
    onboarding_complete = render_guided_onboarding_flow(user_uuid)

    if onboarding_complete:
        # Set session state to avoid re-checking
        st.session_state.onboarding_complete = True
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
    if tooltip_button("Continue to Image Generation", "save_button", type="primary"):
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
    if tooltip_button("Complete Onboarding", "save_button", type="primary"):
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

    if tooltip_button("Start Using GITTE", "save_button", type="primary"):
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
    
    # Check if user has completed onboarding and has a pseudonym
    pseudonym_uuid = st.session_state.get("created_pseudonym_uuid") or st.session_state.get("generated_pseudonym_uuid")
    pseudonym_key = st.session_state.get("created_pseudonym_key")
    
    if pseudonym_uuid and pseudonym_key and st.session_state.get("onboarding_complete", False):
        # User has completed onboarding with new system - use study participation chat
        from src.ui.chat_ui import render_study_participation_chat
        
        try:
            render_study_participation_chat(pseudonym_uuid)
        except Exception as e:
            st.error(f"Error loading chat: {e}")
            # Show debug info
            with st.expander("Debug Info"):
                st.write(f"Pseudonym UUID: {pseudonym_uuid}")
                st.write(f"Pseudonym Key: {pseudonym_key}")
                st.write(f"UUID Type: {type(pseudonym_uuid)}")
    else:
        # No onboarding completed or missing pseudonym data
        st.warning("Please complete onboarding first to access the chat feature.")
        if st.button("Go to Onboarding"):
            st.session_state.onboarding_complete = False
            st.rerun()


def render_images_tab(user_id: str) -> None:
    """Render images tab."""
    
    # Check if user has completed onboarding and has a pseudonym
    pseudonym_uuid = st.session_state.get("created_pseudonym_uuid") or st.session_state.get("generated_pseudonym_uuid")
    pseudonym_key = st.session_state.get("created_pseudonym_key")
    
    if pseudonym_uuid and pseudonym_key and st.session_state.get("onboarding_complete", False):
        # User has completed onboarding with new system - use pseudonym-based operations
        st.info(f"🔐 Using your participation key: {pseudonym_key}")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Generate New Avatar")
            embodiment_data = st.session_state.get("embodiment_characteristics", {})
            # For now, use user_id for image generation until we implement pseudonym-based image generation
            render_image_generation_interface(user_id, embodiment_data)

        with col2:
            st.subheader("Your Gallery")
            render_image_gallery(user_id)
    else:
        # No onboarding completed or missing pseudonym data
        st.warning("Please complete onboarding first to access the image generation feature.")
        if st.button("Go to Onboarding"):
            st.session_state.onboarding_complete = False
            st.rerun()


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
        render_onboarding_summary(to_uuid(user_id))

    # User preferences
    with st.expander("Learning Preferences", expanded=False):
        st.info("Preference updates will be available in future updates.")

    # Privacy settings
    with st.expander("Privacy & Consent", expanded=False):
        if st.button("Manage Consent Settings", key="main_consent_settings_button"):
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


def _apply_enhanced_accessibility_features():
    """Apply enhanced accessibility features for WCAG 2.1 AA compliance."""
    enhanced_styles = """
    <style>
    /* Enhanced focus indicators */
    .stButton > button:focus,
    .stSelectbox > div > div:focus,
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stCheckbox > label:focus-within,
    .stRadio > div:focus-within,
    .stSlider > div:focus-within,
    .stNumberInput > div > div > input:focus {
        outline: 3px solid #005FCC !important;
        outline-offset: 2px !important;
        box-shadow: 0 0 0 3px rgba(0, 95, 204, 0.3) !important;
    }
    
    /* High contrast mode enhancements */
    @media (prefers-contrast: high) {
        .stApp {
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        
        .stButton > button {
            border: 2px solid #000000 !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        
        .stButton > button:hover {
            background-color: #000000 !important;
            color: #FFFFFF !important;
        }
        
        .stSelectbox > div > div,
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            border: 2px solid #000000 !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            border: 2px solid #000000 !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
        }
        
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background-color: #000000 !important;
            color: #FFFFFF !important;
        }
    }
    
    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
        
        .stSpinner > div {
            animation: none !important;
        }
    }
    
    /* Enhanced text readability */
    .stMarkdown p, .stMarkdown li, .stText {
        line-height: 1.6 !important;
        font-size: 16px !important;
    }
    
    /* Better spacing for touch targets */
    .stButton > button {
        min-height: 44px !important;
        min-width: 44px !important;
        padding: 12px 24px !important;
    }
    
    .stCheckbox > label {
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    .stRadio > div > label {
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Screen reader improvements */
    .sr-only {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
    }
    
    /* Skip links */
    .skip-link {
        position: absolute;
        left: -9999px;
        width: 1px;
        height: 1px;
        overflow: hidden;
    }
    
    .skip-link:focus {
        position: absolute !important;
        left: 6px !important;
        top: 7px !important;
        width: auto !important;
        height: auto !important;
        padding: 8px 16px !important;
        background: #000000 !important;
        color: #FFFFFF !important;
        text-decoration: none !important;
        border-radius: 4px !important;
        z-index: 9999 !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }
    
    /* Error and success message accessibility */
    .stAlert {
        border-left: 4px solid !important;
        padding: 16px !important;
        margin: 16px 0 !important;
    }
    
    .stAlert[data-baseweb="notification"] {
        role: alert !important;
    }
    
    /* Progress indicators */
    .stProgress > div {
        background-color: #E0E0E0 !important;
        border-radius: 4px !important;
    }
    
    .stProgress > div > div {
        background-color: #2196F3 !important;
        border-radius: 4px !important;
    }
    
    /* Tab accessibility */
    .stTabs [data-baseweb="tab-list"] {
        role: tablist !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        role: tab !important;
        cursor: pointer !important;
        border-radius: 4px 4px 0 0 !important;
        padding: 12px 16px !important;
        margin-right: 2px !important;
    }
    
    .stTabs [data-baseweb="tab"]:focus {
        outline: 3px solid #005FCC !important;
        outline-offset: 2px !important;
    }
    
    /* Form validation styling */
    .form-error {
        color: #D32F2F !important;
        font-size: 14px !important;
        margin-top: 4px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    .form-error::before {
        content: "⚠️" !important;
        margin-right: 8px !important;
    }
    
    .form-success {
        color: #388E3C !important;
        font-size: 14px !important;
        margin-top: 4px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    .form-success::before {
        content: "✅" !important;
        margin-right: 8px !important;
    }
    
    /* Loading states */
    .loading-container {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 20px !important;
    }
    
    .loading-text {
        margin-left: 12px !important;
        font-size: 16px !important;
    }
    
    /* Responsive design improvements */
    @media (max-width: 768px) {
        .stButton > button {
            width: 100% !important;
            margin-bottom: 8px !important;
        }
        
        .stColumns > div {
            margin-bottom: 16px !important;
        }
    }
    
    /* Color contrast improvements */
    .stSelectbox > div > div {
        background-color: #FFFFFF !important;
        border: 2px solid #CCCCCC !important;
    }
    
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #FFFFFF !important;
        border: 2px solid #CCCCCC !important;
        color: #000000 !important;
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: #666666 !important;
    }
    
    /* Sidebar accessibility */
    .css-1d391kg {
        background-color: #F5F5F5 !important;
        border-right: 2px solid #E0E0E0 !important;
    }
    
    /* Main content area */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    </style>
    """
    
    st.markdown(enhanced_styles, unsafe_allow_html=True)
    
    # Add skip navigation links
    skip_links = """
    <div class="skip-links">
        <a href="#main-content" class="skip-link">Skip to main content</a>
        <a href="#navigation" class="skip-link">Skip to navigation</a>
        <a href="#sidebar" class="skip-link">Skip to sidebar</a>
    </div>
    """
    st.markdown(skip_links, unsafe_allow_html=True)
    
    # Add keyboard navigation JavaScript
    keyboard_nav_js = """
    <script>
    // Enhanced keyboard navigation
    document.addEventListener('keydown', function(event) {
        // Alt + 1: Focus on main content
        if (event.altKey && event.key === '1') {
            const mainContent = document.querySelector('[data-testid="stAppViewContainer"]');
            if (mainContent) {
                mainContent.focus();
                mainContent.scrollIntoView();
                event.preventDefault();
            }
        }
        
        // Alt + 2: Focus on sidebar
        if (event.altKey && event.key === '2') {
            const sidebar = document.querySelector('.css-1d391kg');
            if (sidebar) {
                const firstButton = sidebar.querySelector('button, input, select, textarea, a[href]');
                if (firstButton) {
                    firstButton.focus();
                    event.preventDefault();
                }
            }
        }
        
        // Alt + 3: Focus on first interactive element
        if (event.altKey && event.key === '3') {
            const firstInteractive = document.querySelector('button, input, select, textarea, a[href]');
            if (firstInteractive) {
                firstInteractive.focus();
                event.preventDefault();
            }
        }
        
        // Escape: Close any open dropdowns or modals
        if (event.key === 'Escape') {
            const openDropdowns = document.querySelectorAll('[aria-expanded="true"]');
            openDropdowns.forEach(element => {
                element.setAttribute('aria-expanded', 'false');
            });
        }
        
        // Tab navigation improvements
        if (event.key === 'Tab') {
            // Ensure focus is visible
            setTimeout(() => {
                const focused = document.activeElement;
                if (focused && focused.tagName) {
                    focused.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }, 10);
        }
    });
    
    // Announce page changes to screen readers
    function announcePageChange(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'sr-only';
        announcement.textContent = message;
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            if (document.body.contains(announcement)) {
                document.body.removeChild(announcement);
            }
        }, 1000);
    }
    
    // Monitor for Streamlit updates
    const observer = new MutationObserver(function(mutations) {
        let hasSignificantChange = false;
        
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                const hasMainContent = Array.from(mutation.addedNodes).some(node => 
                    node.nodeType === 1 && (
                        node.querySelector && (
                            node.querySelector('[data-testid="stAppViewContainer"]') ||
                            node.querySelector('.stAlert') ||
                            node.querySelector('.stSuccess') ||
                            node.querySelector('.stError')
                        )
                    )
                );
                
                if (hasMainContent) {
                    hasSignificantChange = true;
                }
            }
        });
        
        if (hasSignificantChange) {
            announcePageChange('Page content updated');
        }
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Add ARIA labels to Streamlit elements
    function enhanceStreamlitAccessibility() {
        // Add labels to buttons without proper labels
        const buttons = document.querySelectorAll('button:not([aria-label]):not([aria-labelledby])');
        buttons.forEach(button => {
            if (button.textContent.trim()) {
                button.setAttribute('aria-label', button.textContent.trim());
            }
        });
        
        // Add labels to input fields
        const inputs = document.querySelectorAll('input:not([aria-label]):not([aria-labelledby])');
        inputs.forEach(input => {
            const label = input.closest('.stTextInput, .stNumberInput')?.querySelector('label');
            if (label && label.textContent.trim()) {
                input.setAttribute('aria-label', label.textContent.trim());
            }
        });
        
        // Add role attributes to tabs
        const tabs = document.querySelectorAll('[data-baseweb="tab"]');
        tabs.forEach((tab, index) => {
            tab.setAttribute('role', 'tab');
            tab.setAttribute('tabindex', tab.getAttribute('aria-selected') === 'true' ? '0' : '-1');
        });
        
        const tabList = document.querySelector('[data-baseweb="tab-list"]');
        if (tabList) {
            tabList.setAttribute('role', 'tablist');
        }
    }
    
    // Run accessibility enhancements periodically
    setInterval(enhanceStreamlitAccessibility, 1000);
    
    // Initial run
    setTimeout(enhanceStreamlitAccessibility, 500);
    </script>
    """
    st.markdown(keyboard_nav_js, unsafe_allow_html=True)


if __name__ == "__main__":
    main()

# === Task 9: PALD wiring (append-only) =======================================
from typing import Any, Dict

_PALD_SCHEMA_CACHE: Dict[str, Any] | None = None

def _get_pald_schema_cached() -> dict:
    """
    Load PALD schema once and cache it.
    Reads default path resolution from the service loader (env/config-aware).
    """
    global _PALD_SCHEMA_CACHE
    if _PALD_SCHEMA_CACHE is None:
        try:
            from src.services.pald_schema import load_pald_schema
            from src.utils.logging import get_logger
            logger = get_logger(__name__)
            _PALD_SCHEMA_CACHE = load_pald_schema()
            logger.info("pald_schema_loaded ok=1")
        except Exception as e:  # pragma: no cover
            try:
                from src.utils.logging import get_logger
                get_logger(__name__).error("pald_schema_load_failed error=%s", e)
            except Exception:
                pass
            _PALD_SCHEMA_CACHE = {}
    return _PALD_SCHEMA_CACHE or {}

def validate_and_render_pald(response: "object") -> None:
    """
    Validate response.pald_light against schema and render banners/summary/errors.
    This function expects a PALDProcessingResponse (UI contract).
    """
    try:
        from src.services.pald_schema import validate_pald_light
        from src.ui.chat_ui import render_pald_response
        from src.utils.logging import get_logger

        logger = get_logger(__name__)
        schema = _get_pald_schema_cached()

        pald = dict(getattr(response, "pald_light", {}) or {})
        before = len(pald)

        validated = validate_pald_light(pald, schema)
        after = len(validated)
        stripped = before - after
        if stripped > 0:
            logger.info("pald_validation_stripped keys=%d", stripped)

        # Mutate the response object to the validated shape so the UI shows only allowed keys.
        try:
            response.pald_light = validated  # type: ignore[attr-defined]
        except Exception:
            pass

        render_pald_response(response)

    except Exception as e:  # pragma: no cover
        # Graceful UI error for end users
        try:
            import streamlit as st
            st.error(f"PALD UI rendering failed: {e}")
        except Exception:
            pass

def is_defer_enabled() -> bool:
    """
    Read defer flag from central config if available.
    This is optional; the actual defer_notice is expected to be set in the response.
    """
    try:
        from config.config import config
        cfg = getattr(config, "PALDEnhancementConfig", None)
        return bool(getattr(cfg, "defer_bias_scan", False))
    except Exception:
        return False

# USAGE (example):
#   - When you receive a PALDProcessingResponse instance named `resp`, call:
#       validate_and_render_pald(resp)
#   - The function will validate resp.pald_light, log stripped keys, and render the UI parts.
# === End Task 9 append-only ===================================================
