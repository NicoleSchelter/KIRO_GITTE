"""
Accessible chat UI components for GITTE system.
Provides WCAG 2.1 AA compliant chat interface with keyboard navigation and screen reader support.
"""

import logging
import time
from typing import Any
from uuid import UUID

import streamlit as st

from src.data.models import ConsentType
from src.logic.embodiment import get_embodiment_logic
from src.logic.llm import get_llm_logic
from src.services.consent_service import get_consent_service
from src.ui.accessibility import (
    AccessibilityHelper,
    ScreenReaderSupport,
    apply_accessibility_features,
    create_accessible_form_field,
)
from src.utils.error_handler import handle_errors

logger = logging.getLogger(__name__)


class AccessibleChatUI:
    """Accessible chat UI with WCAG 2.1 AA compliance."""

    def __init__(self):
        self.llm_logic = get_llm_logic()
        self.embodiment_logic = get_embodiment_logic()
        self.consent_service = get_consent_service()
        self.accessibility_helper = AccessibilityHelper()
        self.screen_reader = ScreenReaderSupport()

        # Chat interface settings
        self.greeting_cleanup_delay = 5  # seconds
        self.max_message_length = 1000
        self.auto_scroll = True

    @handle_errors(context={"component": "accessible_chat"})
    def render_accessible_chat_interface(self, user_id: UUID) -> None:
        """
        Render accessible chat interface with full WCAG compliance.

        Args:
            user_id: User identifier
        """
        # Apply accessibility features
        apply_accessibility_features()

        # Check consent
        if not self._check_chat_consent(user_id):
            return

        # Add chat-specific accessibility styles
        self._add_chat_accessibility_styles()

        # Create main chat container with proper ARIA labels
        st.markdown(
            '<div id="main-content" role="main" aria-label="Chat interface">',
            unsafe_allow_html=True,
        )

        # Chat header with accessibility features
        self._render_accessible_chat_header(user_id)

        # Chat messages area
        self._render_accessible_chat_messages(user_id)

        # Chat input area
        self._render_accessible_chat_input(user_id)

        # Chat controls and settings
        self._render_accessible_chat_controls()

        # Close main container
        st.markdown("</div>", unsafe_allow_html=True)

        # Handle greeting cleanup
        self._handle_greeting_cleanup()

    def _add_chat_accessibility_styles(self) -> None:
        """Add chat-specific accessibility styles."""
        chat_styles = """
        <style>
        /* Chat message accessibility */
        .chat-message {
            margin-bottom: 16px;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #E0E0E0;
            position: relative;
        }
        
        .chat-message-user {
            background-color: #E3F2FD;
            margin-left: 20%;
            border-color: #2196F3;
        }
        
        .chat-message-assistant {
            background-color: #F5F5F5;
            margin-right: 20%;
            border-color: #757575;
        }
        
        .chat-message-header {
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        .chat-message-content {
            line-height: 1.5;
            font-size: 16px;
        }
        
        .chat-message-timestamp {
            font-size: 12px;
            color: #666;
            margin-top: 8px;
        }
        
        /* Chat input accessibility */
        .chat-input-container {
            border: 2px solid #2196F3;
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
            background-color: #FAFAFA;
        }
        
        .chat-input-label {
            font-weight: bold;
            margin-bottom: 8px;
            display: block;
        }
        
        .chat-input-help {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }
        
        .chat-input-counter {
            font-size: 12px;
            color: #666;
            text-align: right;
            margin-top: 4px;
        }
        
        /* High contrast mode support */
        @media (prefers-contrast: high) {
            .chat-message {
                border-width: 2px;
            }
            
            .chat-message-user {
                background-color: #FFFFFF;
                border-color: #000000;
            }
            
            .chat-message-assistant {
                background-color: #F0F0F0;
                border-color: #000000;
            }
            
            .chat-input-container {
                border-color: #000000;
                background-color: #FFFFFF;
            }
        }
        
        /* Focus indicators for chat elements */
        .chat-message:focus {
            outline: 3px solid #2196F3;
            outline-offset: 2px;
        }
        
        /* Screen reader announcements */
        .chat-announcement {
            position: absolute;
            left: -9999px;
            width: 1px;
            height: 1px;
            overflow: hidden;
        }
        
        /* Chat status indicators */
        .chat-status {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            padding: 8px 12px;
            background-color: #E8F5E8;
            border: 1px solid #4CAF50;
            border-radius: 4px;
        }
        
        .chat-status-icon {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background-color: #4CAF50;
        }
        
        .chat-status.offline .chat-status-icon {
            background-color: #F44336;
        }
        
        .chat-status.offline {
            background-color: #FFEBEE;
            border-color: #F44336;
        }
        </style>
        """

        st.markdown(chat_styles, unsafe_allow_html=True)

    def _render_accessible_chat_header(self, user_id: UUID) -> None:
        """Render accessible chat header."""
        # Chat status indicator
        status_html = """
        <div class="chat-status" role="status" aria-live="polite">
            <div class="chat-status-icon" aria-hidden="true"></div>
            <span>Chat assistant is online and ready</span>
        </div>
        """
        st.markdown(status_html, unsafe_allow_html=True)

        # Chat title with proper heading structure
        st.markdown(
            '<h1 id="chat-title">💬 Chat with Your Learning Assistant</h1>', unsafe_allow_html=True
        )

        # Chat description for screen readers
        st.markdown(
            """
            <p id="chat-description">
                This is an interactive chat interface where you can ask questions and have conversations 
                with your personalized learning assistant. Use the text input below to send messages.
            </p>
            """,
            unsafe_allow_html=True,
        )

        # Keyboard shortcuts help
        with st.expander("⌨️ Keyboard Shortcuts", expanded=False):
            st.markdown(
                """
            **Chat Navigation:**
            - **Enter**: Send message
            - **Shift + Enter**: New line in message
            - **Alt + C**: Focus on chat input
            - **Alt + M**: Focus on messages area
            - **Escape**: Clear current message
            
            **General Navigation:**
            - **Alt + M**: Skip to main content
            - **Alt + N**: Skip to navigation
            - **Tab**: Move to next interactive element
            - **Shift + Tab**: Move to previous interactive element
            """
            )

    def _render_accessible_chat_messages(self, user_id: UUID) -> None:
        """Render accessible chat messages with proper ARIA labels."""
        # Initialize chat history
        if "accessible_chat_messages" not in st.session_state:
            st.session_state.accessible_chat_messages = []
            # Add welcome message with accessibility features
            welcome_msg = self._create_accessible_welcome_message(user_id)
            st.session_state.accessible_chat_messages.append(welcome_msg)

        # Messages container with ARIA labels
        st.markdown(
            """
            <div id="chat-messages" 
                 role="log" 
                 aria-live="polite" 
                 aria-label="Chat conversation history"
                 tabindex="0">
            """,
            unsafe_allow_html=True,
        )

        # Render messages with accessibility features
        messages = st.session_state.accessible_chat_messages

        for i, message in enumerate(messages):
            self._render_accessible_message(message, i, len(messages))

        # Close messages container
        st.markdown("</div>", unsafe_allow_html=True)

        # Auto-scroll to latest message
        if self.auto_scroll and messages:
            st.markdown(
                """
                <script>
                const messagesContainer = document.getElementById('chat-messages');
                if (messagesContainer) {
                    messagesContainer.scrollTop = messagesContainer.scrollHeight;
                }
                </script>
                """,
                unsafe_allow_html=True,
            )

    def _render_accessible_message(self, message: dict[str, Any], index: int, total: int) -> None:
        """Render individual message with accessibility features."""
        role = message["role"]
        content = message["content"]
        timestamp = message.get("timestamp", time.time())

        # Format timestamp
        time_str = time.strftime("%H:%M", time.localtime(timestamp))

        # Create ARIA label
        position_info = f"{index + 1} of {total}"
        sender = "You" if role == "user" else "Assistant"
        aria_label = f"Message {position_info} from {sender} at {time_str}"

        # Message container with accessibility attributes
        message_class = f"chat-message chat-message-{role}"

        message_html = f"""
        <div class="{message_class}" 
             role="article"
             aria-label="{aria_label}"
             tabindex="0">
            <div class="chat-message-header">
                <span aria-hidden="true">{'👤' if role == 'user' else '🤖'}</span>
                {sender}
                <span class="chat-message-timestamp">({time_str})</span>
            </div>
            <div class="chat-message-content">
                {self._format_message_content(content)}
            </div>
        </div>
        """

        st.markdown(message_html, unsafe_allow_html=True)

    def _render_accessible_chat_input(self, user_id: UUID) -> None:
        """Render accessible chat input with proper form controls."""
        # Create accessible form field
        field_info = create_accessible_form_field(
            field_type="textarea",
            label="Your message",
            field_id="chat-input",
            required=False,
            help_text=f"Type your message here (max {self.max_message_length} characters). Press Enter to send, Shift+Enter for new line.",
            error_message=None,
        )

        # Chat input container
        st.markdown(
            f"""
            <div class="chat-input-container">
                {field_info['label']}
                {field_info['help']}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Use Streamlit's text area with accessibility attributes
        user_input = st.text_area(
            label="Your message",
            placeholder="Type your message here...",
            max_chars=self.max_message_length,
            height=100,
            key="accessible_chat_input",
            label_visibility="collapsed",
        )

        # Character counter
        char_count = len(user_input) if user_input else 0
        remaining = self.max_message_length - char_count

        counter_html = f"""
        <div class="chat-input-counter" 
             role="status" 
             aria-live="polite"
             aria-label="Character count">
            {char_count}/{self.max_message_length} characters
            {f"({remaining} remaining)" if remaining > 0 else "(limit reached)"}
        </div>
        """
        st.markdown(counter_html, unsafe_allow_html=True)

        # Send button with accessibility features
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            send_button = st.button(
                "📤 Send Message",
                disabled=not user_input or len(user_input.strip()) == 0,
                help="Send your message to the assistant",
                key="send_message_btn",
            )

        with col2:
            clear_button = st.button(
                "🗑️ Clear", help="Clear the current message", key="clear_message_btn"
            )

        with col3:
            # Voice input placeholder (would integrate with speech recognition)
            st.button(
                "🎤 Voice Input",
                disabled=True,
                help="Voice input (coming soon)",
                key="voice_input_btn",
            )

        # Handle button actions
        if send_button and user_input:
            self._handle_send_message(user_id, user_input)

        if clear_button:
            st.session_state.accessible_chat_input = ""
            st.rerun()

    def _render_accessible_chat_controls(self) -> None:
        """Render accessible chat controls and settings."""
        with st.sidebar:
            st.markdown("### ⚙️ Chat Settings")

            # Auto-scroll toggle
            self.auto_scroll = st.checkbox(
                "Auto-scroll to new messages",
                value=self.auto_scroll,
                help="Automatically scroll to the latest message when new messages arrive",
            )

            # High contrast mode toggle
            high_contrast = st.checkbox(
                "High contrast mode",
                value=False,
                help="Enable high contrast colors for better visibility",
            )

            if high_contrast:
                st.markdown(
                    """
                    <style>
                    .stApp {
                        filter: contrast(150%) brightness(110%);
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

            # Font size adjustment
            font_size = st.selectbox(
                "Font size",
                options=["Small", "Medium", "Large", "Extra Large"],
                index=1,
                help="Adjust text size for better readability",
            )

            font_sizes = {"Small": "14px", "Medium": "16px", "Large": "18px", "Extra Large": "20px"}

            if font_size != "Medium":
                st.markdown(
                    f"""
                    <style>
                    .chat-message-content {{
                        font-size: {font_sizes[font_size]} !important;
                    }}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

            # Chat actions
            st.markdown("### 📋 Chat Actions")

            if st.button("📥 Export Chat"):
                self._export_accessible_chat()

            if st.button("🗑️ Clear Chat History"):
                self._clear_chat_with_confirmation()

            if st.button("🔄 Restart Conversation"):
                self._restart_conversation_with_confirmation()

    def _handle_send_message(self, user_id: UUID, message: str) -> None:
        """Handle sending a message with accessibility announcements."""
        try:
            # Add user message
            user_message = {"role": "user", "content": message.strip(), "timestamp": time.time()}
            st.session_state.accessible_chat_messages.append(user_message)

            # Announce message sent to screen readers
            st.markdown(
                self.screen_reader.announce_to_screen_reader(
                    f"Message sent: {message[:50]}{'...' if len(message) > 50 else ''}",
                    "announcements",
                ),
                unsafe_allow_html=True,
            )

            # Generate response
            with st.spinner("🤖 Assistant is thinking..."):
                response = self._generate_accessible_response(user_id, message)

            # Add assistant response
            assistant_message = {"role": "assistant", "content": response, "timestamp": time.time()}
            st.session_state.accessible_chat_messages.append(assistant_message)

            # Announce response received
            st.markdown(
                self.screen_reader.announce_to_screen_reader(
                    f"Assistant responded: {response[:50]}{'...' if len(response) > 50 else ''}",
                    "announcements",
                ),
                unsafe_allow_html=True,
            )

            # Clear input
            st.session_state.accessible_chat_input = ""
            st.rerun()

        except Exception as e:
            logger.error(f"Error handling message send: {e}")
            st.error("Failed to send message. Please try again.")

    def _generate_accessible_response(self, user_id: UUID, message: str) -> str:
        """Generate response with accessibility considerations."""
        try:
            # Create context-aware prompt
            context = self._get_accessible_chat_context(user_id)

            # Generate response using LLM logic
            response = self.llm_logic.generate_response(
                prompt=f"User message: {message}\n\nContext: {context}",
                user_id=user_id,
                model="default",
                parameters={"temperature": 0.7, "max_tokens": 300},
            )

            return response.text

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I'm having trouble responding right now. Please try again."

    def _get_accessible_chat_context(self, user_id: UUID) -> str:
        """Get context for accessible chat responses."""
        return """
        You are an accessible learning assistant. Please:
        - Use clear, simple language
        - Structure responses with headings when appropriate
        - Avoid overly complex sentences
        - Be encouraging and supportive
        - Ask clarifying questions when needed
        - Provide step-by-step explanations when helpful
        """

    def _create_accessible_welcome_message(self, user_id: UUID) -> dict[str, Any]:
        """Create accessible welcome message."""
        welcome_text = """
        Hello! I'm your personalized learning assistant. I'm here to help you learn and explore topics in a way that works best for you.

        I'm designed to be accessible and easy to use. You can:
        • Ask me questions about any topic
        • Request explanations in different formats
        • Get step-by-step guidance
        • Practice conversations

        What would you like to learn about today?
        """

        return {
            "role": "assistant",
            "content": welcome_text,
            "timestamp": time.time(),
            "is_greeting": True,
        }

    def _handle_greeting_cleanup(self) -> None:
        """Handle automatic cleanup of greeting message."""
        if "greeting_cleanup_time" not in st.session_state:
            st.session_state.greeting_cleanup_time = time.time() + self.greeting_cleanup_delay

        messages = st.session_state.get("accessible_chat_messages", [])

        # Check if it's time to clean up greeting and user has interacted
        if (
            time.time() > st.session_state.greeting_cleanup_time
            and len(messages) > 1  # More than just greeting
            and any(msg.get("is_greeting") for msg in messages)
        ):

            # Remove greeting message
            st.session_state.accessible_chat_messages = [
                msg for msg in messages if not msg.get("is_greeting")
            ]

            # Announce cleanup to screen readers
            st.markdown(
                self.screen_reader.announce_to_screen_reader(
                    "Welcome message cleared to keep chat focused", "announcements"
                ),
                unsafe_allow_html=True,
            )

            st.rerun()

    def _format_message_content(self, content: str) -> str:
        """Format message content for accessibility."""
        # Simple formatting for better readability
        content = content.replace("\n", "<br>")

        # Add semantic markup for lists
        lines = content.split("<br>")
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if line.startswith("•") or line.startswith("-"):
                # Convert to proper list item
                formatted_lines.append(f"<li>{line[1:].strip()}</li>")
            elif line.startswith(("1.", "2.", "3.", "4.", "5.")):
                # Convert to numbered list item
                formatted_lines.append(f"<li>{line[2:].strip()}</li>")
            else:
                formatted_lines.append(line)

        return "<br>".join(formatted_lines)

    def _check_chat_consent(self, user_id: UUID) -> bool:
        """Check if user has consent for chat functionality."""
        try:
            if not self.consent_service.check_consent(user_id, ConsentType.AI_INTERACTION):
                st.error("🔒 Chat functionality requires AI interaction consent.")
                st.info("Please update your consent settings to use the chat feature.")

                if st.button("Manage Consent Settings"):
                    st.session_state.show_consent_ui = True
                    st.rerun()

                return False

            return True

        except Exception as e:
            logger.error(f"Error checking chat consent: {e}")
            st.error("Unable to verify consent status.")
            return False

    def _export_accessible_chat(self) -> None:
        """Export chat history in accessible format."""
        messages = st.session_state.get("accessible_chat_messages", [])

        if not messages:
            st.warning("No chat history to export.")
            return

        # Create accessible export format
        export_content = "# Chat History Export\n\n"
        export_content += f"Exported on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        for i, message in enumerate(messages):
            role = "You" if message["role"] == "user" else "Assistant"
            timestamp = time.strftime("%H:%M:%S", time.localtime(message["timestamp"]))
            content = message["content"]

            export_content += f"## Message {i + 1} - {role} ({timestamp})\n\n"
            export_content += f"{content}\n\n"

        # Provide download
        st.download_button(
            label="📥 Download Chat History",
            data=export_content,
            file_name=f"chat_history_{int(time.time())}.md",
            mime="text/markdown",
            help="Download your chat history as a markdown file",
        )

    def _clear_chat_with_confirmation(self) -> None:
        """Clear chat history with confirmation."""
        if "confirm_clear_chat" not in st.session_state:
            st.session_state.confirm_clear_chat = False

        if not st.session_state.confirm_clear_chat:
            st.warning("⚠️ This will permanently delete your chat history.")
            if st.button("Confirm Clear Chat History"):
                st.session_state.confirm_clear_chat = True
                st.rerun()
        else:
            st.session_state.accessible_chat_messages = []
            st.session_state.confirm_clear_chat = False
            st.success("Chat history cleared.")
            st.rerun()

    def _restart_conversation_with_confirmation(self) -> None:
        """Restart conversation with confirmation."""
        if "confirm_restart_chat" not in st.session_state:
            st.session_state.confirm_restart_chat = False

        if not st.session_state.confirm_restart_chat:
            st.warning("⚠️ This will clear your chat history and start fresh.")
            if st.button("Confirm Restart Conversation"):
                st.session_state.confirm_restart_chat = True
                st.rerun()
        else:
            # Clear chat and add new welcome message
            welcome_msg = self._create_accessible_welcome_message(st.session_state.get("user_id"))
            st.session_state.accessible_chat_messages = [welcome_msg]
            st.session_state.confirm_restart_chat = False
            st.success("Conversation restarted.")
            st.rerun()


# Global accessible chat UI instance
accessible_chat_ui = AccessibleChatUI()


# Convenience functions
def render_accessible_chat_interface(user_id: UUID) -> None:
    """Render accessible chat interface."""
    accessible_chat_ui.render_accessible_chat_interface(user_id)
