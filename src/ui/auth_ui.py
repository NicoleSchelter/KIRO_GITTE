"""
Authentication UI components for GITTE system.
Provides Streamlit components for user login and registration.
"""

import logging
from typing import Any
from uuid import UUID
import regex as re
import streamlit as st

from config.config import get_text
from src.data.models import UserRole
from src.data.repositories import get_user_repository
from src.data.schemas import UserCreate, UserLogin
from src.logic.authentication import (
    AuthenticationError,
    AuthenticationLogic,
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from src.services.session_manager import get_session_manager
from src.ui.tooltip_integration import (
    get_tooltip_integration,
    tooltip_input,
    tooltip_button,
    tooltip_checkbox,
    tooltip_selectbox,
    form_submit_button
)

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    filename="gitte.log",  # Logdatei im aktuellen Verzeichnis
    filemode="a"
)

class AuthenticationUI:
    """UI components for user authentication."""

    def __init__(self):
        self.auth_logic = AuthenticationLogic(
            user_repository=get_user_repository(), session_manager=get_session_manager()
        )
        self.tooltip_integration = get_tooltip_integration()

    def render_login_page(self) -> dict[str, Any] | None:
        """
        Render login page with enhanced accessibility.

        Returns:
            Dict with user and session info if login successful, None otherwise
        """
        # Add page structure for screen readers
        st.markdown('<main role="main" id="main-content">', unsafe_allow_html=True)
        
        st.title(get_text("login_title"))
        
        # Add login instructions for screen readers
        st.markdown(
            """
            <div class="sr-only">
                Login form. Enter your username and password to access the GITTE learning system.
                If you don't have an account, you can register for a new one.
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("login_form"):
            st.subheader("Sign In")

            # Enhanced username input with better accessibility
            username = tooltip_input(
                "Username",
                "username_input",
                placeholder="Enter your username"
            )

            # Enhanced password input with accessibility features
            password = tooltip_input(
                "Password",
                "password_input",
                type="password",
                placeholder="Enter your password"
            )
            
            # Add password visibility toggle (conceptual - would need custom implementation)
            st.markdown(
                """
                <div class="form-help">
                    <small>Password is hidden for security. Make sure you're in a private location.</small>
                </div>
                """,
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            with col1:
                login_submitted = form_submit_button(
                    "🔑 Sign In", 
                    type="primary"
                )

            with col2:
                register_submitted = form_submit_button("👤 New User? Register")
                
            # Handle form submissions
            if register_submitted:
                st.session_state.show_registration = True
                st.rerun()
            
            # Add keyboard shortcuts info
            st.markdown(
                """
                <div class="form-help">
                    <small>💡 <strong>Tip:</strong> Press Tab to navigate between fields, Enter to submit</small>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Close main content area
        st.markdown('</main>', unsafe_allow_html=True)

        if login_submitted:
            if not username or not password:
                st.error("⚠️ Please enter both username and password.")
                # Announce error to screen readers
                st.markdown(
                    """
                    <div aria-live="polite" class="sr-only">
                        Login error: Please enter both username and password
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                return None

            try:
                # Show loading state with accessibility
                with st.spinner("🔐 Signing you in..."):
                    login_data = UserLogin(username=username, password=password)
                    result = self.auth_logic.login_user(login_data)

                # Store session info
                st.session_state.user_id = result["user"].id
                st.session_state.username = result["user"].username
                st.session_state.user_role = result["user"].role
                st.session_state.session_id = result["session"]["session_id"]
                st.session_state.authenticated = True

                st.success(f"✅ Welcome back, {result['user'].username}!")
                
                # Announce success to screen readers
                st.markdown(
                    f"""
                    <div aria-live="polite" class="sr-only">
                        Login successful. Welcome back, {result['user'].username}. Redirecting to main application.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                st.balloons()

                logger.info(f"User logged in successfully: {username}")
                return result

            except InvalidCredentialsError:
                st.error(f"❌ {get_text('error_auth_failed')}")
                st.markdown(
                    """
                    <div aria-live="assertive" class="sr-only">
                        Login failed: Invalid username or password
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            except InactiveUserError:
                st.error("❌ Your account is inactive. Please contact support.")
                st.markdown(
                    """
                    <div aria-live="assertive" class="sr-only">
                        Login failed: Account is inactive
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            except AuthenticationError as e:
                st.error(f"❌ Login failed: {str(e)}")
                st.markdown(
                    f"""
                    <div aria-live="assertive" class="sr-only">
                        Login failed: {str(e)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            except Exception as e:
                logger.error(f"Unexpected login error: {e}")
                st.error(f"❌ {get_text('error_generic')}")
                st.markdown(
                    """
                    <div aria-live="assertive" class="sr-only">
                        Login failed: An unexpected error occurred
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        return None

    def render_registration_page(self) -> bool:
        """
        Render registration page.

        Returns:
            bool: True if registration successful
        """
        st.title(get_text("register_title"))

        with st.form("registration_form"):
            st.subheader("Create New Account")

            username = tooltip_input(
                "Username",
                "username_input",
                placeholder="Choose a username"
            )

            password = tooltip_input(
                "Password",
                "password_input",
                type="password",
                placeholder="Choose a strong password"
            )

            confirm_password = tooltip_input(
                "Confirm Password",
                "confirm_password_input",
                type="password",
                placeholder="Re-enter your password"
            )

            role = tooltip_selectbox(
                "Account Type",
                "role_select",
                options=[UserRole.PARTICIPANT.value, UserRole.ADMIN.value],
                index=0
            )

            # Terms and conditions
            terms_accepted = tooltip_checkbox(
                "I accept the Terms of Service and Privacy Policy",
                "terms_checkbox"
            )
            def password_valid(password: str) -> bool:
                return (
                    bool(password)
                    and len(password) >= 8
                    and re.search(r"[A-Za-z]", password)
                    and re.search(r"\d", password)
                )
            # Konfigurierbare Bedingungen für die Registrierung
            registration_requirements = [
                {
                    "label": "Username must be at least 3 characters",
                    "fulfilled": bool(username) and len(username) >= 3,
                },
                {
                    "label": "Password must be at least 8 characters, contain at least one letter and one number",
                    "fulfilled": password_valid(password),
                },
                {
                    "label": "Passwords must match",
                    "fulfilled": bool(password) and bool(confirm_password) and password == confirm_password,
                },
                {
                    "label": "You must accept the Terms of Service and Privacy Policy",
                    "fulfilled": bool(terms_accepted),
                },
            ]

            st.markdown("**Folgende Bedingungen müssen erfüllt sein, um ein Konto zu erstellen:**")
            for req in registration_requirements:
                color = "green" if req["fulfilled"] else "red"
                symbol = "✅" if req["fulfilled"] else "❌"
                st.markdown(f"<span style='color:{color}'>{symbol} {req['label']}</span>", unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                # Button immer aktiv!
                register_submitted = form_submit_button(
                    "Create Account",
                    key="register_submit_button",
                    form_valid=True,  # Button immer aktiv
                    type="primary",
                )

            with col2:
                if form_submit_button("Back to Login"):
                    if "show_registration" in st.session_state:
                        del st.session_state.show_registration
                    st.rerun()

        if register_submitted:
            # Validation nach Klick!
            if not username or not password or not confirm_password:
                st.error("Bitte fülle alle Felder aus.")
                return False

            if len(username) < 3:
                st.error("Username muss mindestens 3 Zeichen lang sein.")
                return False

            if len(password) < 8:
                st.error("Passwort muss mindestens 8 Zeichen lang sein.")
                return False

            if password != confirm_password:
                st.error("Passwörter stimmen nicht überein.")
                return False

            if not terms_accepted:
                st.error("Du musst die Bedingungen akzeptieren, um ein Konto zu erstellen.")
                return False

            try:
                user_data = UserCreate(username=username, password=password, role=UserRole(role))

                # perform registration (raises on duplicate etc.)
                user = self.auth_logic.register_user(user_data)

                # Success messages (kept for UX)
                st.success(get_text("success_registration"))
                st.info("You can now log in with your new account.")

                # 👉 leave registration screen and automatically authenticate user
                st.session_state["show_registration"] = False
                
                # Auto-authenticate the newly registered user for better UX
                try:
                    # Create a session for the new user
                    session_info = self.auth_logic.login_user(UserLogin(username=username, password=password))
                    
                    # Set authentication state
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = session_info["user_id"]
                    st.session_state["username"] = username
                    st.session_state["user_role"] = user.role.value
                    st.session_state["session_id"] = session_info.get("session_id")
                    
                    logger.info(f"User registered and auto-authenticated successfully: {username}")
                    st.info("You have been automatically logged in!")
                    
                except Exception as login_error:
                    logger.warning(f"Auto-login after registration failed for {username}: {login_error}")
                    logger.info(f"User registered successfully: {username}")

                # Force immediate UI refresh so we're not stuck on the form
                st.rerun()

                # Fallback (usually not reached because st.rerun raises)
                return True

            except UserAlreadyExistsError:
                st.error("Username existiert bereits. Bitte wähle einen anderen.")
            except AuthenticationError as e:
                st.error(f"Registrierung fehlgeschlagen: {str(e)}")
            except Exception as e:
                logger.error(f"Unerwarteter Fehler bei der Registrierung: {e}")
                st.error(get_text("error_generic"))

        return False

    def render_logout_button(self) -> None:
        """Render logout button in sidebar."""
        if st.session_state.get("authenticated", False):
            with st.sidebar:
                st.write(f"Logged in as: **{st.session_state.get('username', 'Unknown')}**")
                st.write(f"Role: {st.session_state.get('user_role', 'Unknown')}")

                if st.button("Logout", type="secondary"):
                    self._logout_user()

    def check_authentication(self) -> bool:
        """
        Check if user is authenticated.

        Returns:
            bool: True if authenticated
        """
        if not st.session_state.get("authenticated", False):
            return False

        session_id = st.session_state.get("session_id")
        if not session_id:
            return False

        # Verify session is still valid
        user = self.auth_logic.get_current_user(session_id)
        if not user:
            self._clear_session()
            return False

        return True

    def require_authentication(self) -> UUID | None:
        """
        Require authentication, show login if not authenticated.

        Returns:
            UUID: User ID if authenticated, None otherwise
        """
        if self.check_authentication():
            return st.session_state.get("user_id")

        # Show authentication UI
        st.warning("Please log in to continue.")

        # Show registration form if requested
        if st.session_state.get("show_registration", False):
            if self.render_registration_page():
                st.rerun()
        else:
            # Show login form
            if self.render_login_page():
                st.rerun()

        return None

    def require_admin(self) -> UUID | None:
        """
        Require admin authentication.

        Returns:
            UUID: User ID if admin authenticated, None otherwise
        """
        user_id = self.require_authentication()
        if not user_id:
            return None

        user_role = st.session_state.get("user_role")
        if user_role != UserRole.ADMIN.value:
            st.error("Admin access required.")
            st.stop()

        return user_id

    def _logout_user(self) -> None:
        """Logout current user."""
        try:
            session_id = st.session_state.get("session_id")
            if session_id:
                self.auth_logic.logout_user(session_id)

            self._clear_session()
            st.success("Logged out successfully.")
            st.rerun()

        except Exception as e:
            logger.error(f"Logout error: {e}")
            self._clear_session()
            st.rerun()

    def _clear_session(self) -> None:
        """Clear session state."""
        keys_to_clear = [
            "authenticated",
            "user_id",
            "username",
            "user_role",
            "session_id",
            "show_registration",
            "show_consent_ui",
        ]

        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]


# Global authentication UI instance
auth_ui = AuthenticationUI()


# Convenience functions
def render_login_page() -> dict[str, Any] | None:
    """Render login page."""
    return auth_ui.render_login_page()


def render_registration_page() -> bool:
    """Render registration page."""
    return auth_ui.render_registration_page()


def render_logout_button() -> None:
    """Render logout button."""
    auth_ui.render_logout_button()


def check_authentication() -> bool:
    """Check if user is authenticated."""
    return auth_ui.check_authentication()


def require_authentication() -> UUID | None:
    """Require authentication."""
    return auth_ui.require_authentication()


def require_admin() -> UUID | None:
    """Require admin authentication."""
    return auth_ui.require_admin()
