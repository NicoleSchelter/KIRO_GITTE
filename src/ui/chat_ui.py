"""
Chat UI components for GITTE system.
Provides Streamlit components for embodiment chat interface.
"""

import logging
import time
from typing import Any
from uuid import UUID

import streamlit as st

from config.config import get_text
from src.data.database import get_session
from src.data.models import ConsentType
from src.logic.embodiment import get_embodiment_logic
from src.logic.llm import get_llm_logic
from src.logic.pald import PALDManager
from src.services.consent_service import get_consent_service

logger = logging.getLogger(__name__)


class ChatUI:
    """UI components for embodiment chat interface."""

    def __init__(self):
        self.llm_logic = get_llm_logic()
        self.embodiment_logic = get_embodiment_logic()
        self.consent_service = get_consent_service()

    def render_chat_interface(self, user_id: UUID) -> None:
        """
        Render the main chat interface for embodiment interaction.

        Args:
            user_id: User identifier
        """
        # Check consent for AI interaction
        if not self._check_chat_consent(user_id):
            return

        st.title(get_text("chat_title"))

        # Initialize chat history
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []
            # Add welcome message
            welcome_msg = self._get_welcome_message(user_id)
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": welcome_msg, "timestamp": time.time()}
            )

        # Chat interface layout
        self._render_chat_header(user_id)
        self._render_chat_messages()
        self._render_chat_input(user_id)
        self._render_chat_controls()

    def render_embodiment_design_chat(self, user_id: UUID) -> dict[str, Any] | None:
        """
        Render specialized chat for embodiment design and feature discussion.

        Args:
            user_id: User identifier

        Returns:
            Dict with embodiment characteristics if design completed
        """
        st.title("🎨 Design Your Embodiment")

        st.write(
            """
        Let's design your personalized learning assistant! Describe how you'd like your 
        embodiment to look, act, and interact with you. Be as detailed or general as you prefer.
        """
        )

        # Initialize design chat history
        if "design_chat_messages" not in st.session_state:
            st.session_state.design_chat_messages = []
            # Add design-specific welcome message
            design_welcome = self._get_design_welcome_message()
            st.session_state.design_chat_messages.append(
                {"role": "assistant", "content": design_welcome, "timestamp": time.time()}
            )

        # Design chat interface
        self._render_design_chat_messages()

        # Design input
        design_input = st.chat_input("Describe your ideal embodiment...", key="design_chat_input")

        if design_input:
            # Add user message
            st.session_state.design_chat_messages.append(
                {"role": "user", "content": design_input, "timestamp": time.time()}
            )

            # Process design input
            response = self._process_design_input(user_id, design_input)

            # Add assistant response
            st.session_state.design_chat_messages.append(
                {"role": "assistant", "content": response["content"], "timestamp": time.time()}
            )

            # Check if design is complete
            if response.get("design_complete", False):
                return response.get("embodiment_characteristics")

            st.rerun()

        # Design completion button
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Complete Design", type="primary"):
                characteristics = self._extract_embodiment_characteristics(user_id)
                if characteristics:
                    st.success("Embodiment design completed!")
                    return characteristics
                else:
                    st.warning("Please provide more details about your preferred embodiment.")

        with col2:
            if st.button("Use Default Design"):
                return self._get_default_embodiment_characteristics()

        return None

    def render_chat_history(self, user_id: UUID) -> None:
        """
        Render chat history viewer.

        Args:
            user_id: User identifier
        """
        st.subheader("💬 Chat History")

        # Get chat history from session or database
        messages = st.session_state.get("chat_messages", [])

        if not messages:
            st.info("No chat history available.")
            return

        # Display options
        col1, col2, col3 = st.columns(3)

        with col1:
            show_timestamps = st.checkbox("Show timestamps", value=False)

        with col2:
            message_limit = st.selectbox(
                "Messages to show", options=[10, 25, 50, 100, "All"], index=1
            )

        with col3:
            if st.button("Clear History"):
                st.session_state.chat_messages = []
                st.rerun()

        # Display messages
        display_messages = messages
        if message_limit != "All":
            display_messages = messages[-message_limit:]

        for i, message in enumerate(display_messages):
            with st.container():
                role_icon = "🤖" if message["role"] == "assistant" else "👤"
                role_name = "Assistant" if message["role"] == "assistant" else "You"

                if show_timestamps:
                    timestamp = time.strftime(
                        "%H:%M:%S", time.localtime(message.get("timestamp", time.time()))
                    )
                    st.write(f"{role_icon} **{role_name}** ({timestamp})")
                else:
                    st.write(f"{role_icon} **{role_name}**")

                st.write(message["content"])

                if i < len(display_messages) - 1:
                    st.divider()

    def _check_chat_consent(self, user_id: UUID) -> bool:
        """Check if user has consent for AI interaction."""
        try:
            if not self.consent_service.check_consent(user_id, ConsentType.AI_INTERACTION):
                st.error(get_text("error_consent_required"))
                st.warning(
                    "You need to provide consent for AI interactions to use the chat feature."
                )

                if st.button("Manage Consent Settings"):
                    st.session_state.show_consent_ui = True
                    st.rerun()

                return False

            return True

        except Exception as e:
            logger.error(f"Error checking chat consent for user {user_id}: {e}")
            st.error("Error checking consent status.")
            return False

    def _render_chat_header(self, user_id: UUID) -> None:
        """Render chat header with embodiment info."""
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.write("💬 **Chat with your personalized learning assistant**")

        with col2:
            if st.button("🔄 New Topic"):
                self._start_new_topic()

        with col3:
            if st.button("📋 History"):
                st.session_state.show_chat_history = True

    def _render_chat_messages(self) -> None:
        """Render chat message history."""
        messages = st.session_state.get("chat_messages", [])

        # Create scrollable chat container
        chat_container = st.container()

        with chat_container:
            for message in messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(message["content"])

    def _render_chat_input(self, user_id: UUID) -> None:
        """Render chat input field."""
        user_input = st.chat_input("Type your message here...", key="main_chat_input")

        if user_input:
            # Add user message to history
            st.session_state.chat_messages.append(
                {"role": "user", "content": user_input, "timestamp": time.time()}
            )

            # Process user input and get response
            with st.spinner("Thinking..."):
                response = self._process_chat_input(user_id, user_input)

            # Add assistant response to history
            st.session_state.chat_messages.append(
                {"role": "assistant", "content": response, "timestamp": time.time()}
            )

            st.rerun()

    def _render_chat_controls(self) -> None:
        """Render chat control buttons."""
        with st.sidebar:
            st.subheader("Chat Controls")

            if st.button("📝 Export Chat"):
                self._export_chat_history()

            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_messages = []
                st.rerun()

            # Chat settings
            with st.expander("Chat Settings"):
                st.session_state.chat_temperature = st.slider(
                    "Response creativity",
                    min_value=0.0,
                    max_value=1.0,
                    value=st.session_state.get("chat_temperature", 0.7),
                    step=0.1,
                    help="Higher values make responses more creative",
                )

                st.session_state.chat_max_tokens = st.slider(
                    "Response length",
                    min_value=50,
                    max_value=500,
                    value=st.session_state.get("chat_max_tokens", 200),
                    step=50,
                    help="Maximum length of responses",
                )

    def _render_design_chat_messages(self) -> None:
        """Render design chat messages."""
        messages = st.session_state.get("design_chat_messages", [])

        for message in messages:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(message["content"])

    def _process_chat_input(self, user_id: UUID, user_input: str) -> str:
        """Process user chat input and generate response."""
        try:
            # Get user's PALD data for context
            context = self._get_user_context(user_id)

            # Create prompt with context
            prompt = self._create_chat_prompt(user_input, context)

            # Generate response using LLM
            response = self.llm_logic.generate_response(
                prompt=prompt,
                user_id=user_id,
                model="default",
                parameters={
                    "temperature": st.session_state.get("chat_temperature", 0.7),
                    "max_tokens": st.session_state.get("chat_max_tokens", 200),
                },
            )

            # Extract attributes for PALD evolution
            self._extract_and_track_attributes(user_id, user_input)

            return response.text

        except Exception as e:
            logger.error(f"Error processing chat input for user {user_id}: {e}")
            return (
                "I apologize, but I encountered an error processing your message. Please try again."
            )

    def _process_design_input(self, user_id: UUID, design_input: str) -> dict[str, Any]:
        """Process design input and generate appropriate response."""
        try:
            # Create design-focused prompt
            prompt = self._create_design_prompt(design_input)

            # Generate response
            response = self.llm_logic.generate_response(
                prompt=prompt,
                user_id=user_id,
                model="creative",
                parameters={"temperature": 0.8, "max_tokens": 300},
            )

            # Extract design characteristics
            characteristics = self._extract_design_characteristics(design_input)

            # Check if design seems complete
            design_complete = self._is_design_complete(design_input, characteristics)

            return {
                "content": response.text,
                "design_complete": design_complete,
                "embodiment_characteristics": characteristics if design_complete else None,
            }

        except Exception as e:
            logger.error(f"Error processing design input: {e}")
            return {
                "content": "I had trouble processing your design input. Could you try describing your embodiment again?",
                "design_complete": False,
            }

    def _get_welcome_message(self, user_id: UUID) -> str:
        """Get personalized welcome message."""
        try:
            context = self._get_user_context(user_id)
            name = context.get("name", "there")

            return f"""
            Hello {name}! 👋 I'm your personalized learning assistant embodiment. 
            I'm here to help you learn and grow in a way that matches your preferences and style.
            
            Feel free to ask me questions, discuss topics you're interested in, or let me know 
            how you'd like to adjust our interactions. What would you like to explore today?
            """
        except:
            return """
            Hello! 👋 I'm your personalized learning assistant embodiment. 
            I'm here to help you learn and explore topics in a way that works best for you.
            
            What would you like to learn about or discuss today?
            """

    def _get_design_welcome_message(self) -> str:
        """Get welcome message for design chat."""
        return """
        Welcome to the embodiment design process! 🎨
        
        I'll help you create a personalized learning assistant that matches your preferences. 
        You can describe:
        
        • **Appearance**: How should your embodiment look? (style, age, formality, etc.)
        • **Personality**: What kind of personality traits do you prefer? (friendly, professional, enthusiastic, etc.)
        • **Teaching Style**: How should I explain things? (detailed, concise, with examples, etc.)
        • **Interaction Style**: How should we communicate? (formal, casual, encouraging, etc.)
        
        Tell me about your ideal learning assistant, and I'll help bring it to life!
        """

    def _get_user_context(self, user_id: UUID) -> dict[str, Any]:
        """Get user context from PALD data."""
        try:
            with get_session() as db_session:
                pald_manager = PALDManager(db_session)
                pald_data_list = pald_manager.get_user_pald_data(user_id)

                if pald_data_list:
                    # Use the most recent PALD data
                    latest_pald = pald_data_list[-1]
                    return latest_pald.pald_content

                return {}

        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}

    def _create_chat_prompt(self, user_input: str, context: dict[str, Any]) -> str:
        """Create chat prompt with user context."""
        # Extract relevant context
        learning_style = context.get("learning_preferences", {}).get("learning_style", "mixed")
        communication_style = context.get("interaction_style", {}).get(
            "communication_style", "friendly"
        )
        difficulty_level = context.get("learning_preferences", {}).get(
            "difficulty_preference", "intermediate"
        )

        prompt = f"""
        You are a personalized learning assistant embodiment. Respond to the user's message 
        in a way that matches their preferences:
        
        Learning Style: {learning_style}
        Communication Style: {communication_style}
        Difficulty Level: {difficulty_level}
        
        User Message: {user_input}
        
        Provide a helpful, engaging response that matches the user's preferences. Keep it 
        conversational and educational.
        """

        return prompt

    def _create_design_prompt(self, design_input: str) -> str:
        """Create prompt for design conversation."""
        return f"""
        You are helping a user design their personalized learning assistant embodiment. 
        They have described: {design_input}
        
        Respond by:
        1. Acknowledging their input
        2. Asking clarifying questions if needed
        3. Suggesting specific embodiment characteristics
        4. Encouraging them to be more specific about aspects they haven't covered
        
        Keep the conversation engaging and help them think through all aspects of their 
        ideal learning assistant.
        """

    def _extract_and_track_attributes(self, user_id: UUID, user_input: str) -> None:
        """Extract and track embodiment attributes from user input."""
        try:
            with get_session() as db_session:
                pald_manager = PALDManager(db_session)
                pald_manager.process_chat_for_attribute_extraction(user_id, user_input)
        except Exception as e:
            logger.error(f"Error extracting attributes: {e}")

    def _extract_design_characteristics(self, design_input: str) -> dict[str, Any]:
        """Extract embodiment characteristics from design input."""
        # Simple keyword-based extraction (could be enhanced with NLP)
        characteristics = {}

        # Appearance keywords
        if any(word in design_input.lower() for word in ["professional", "formal", "business"]):
            characteristics["appearance_style"] = "professional"
        elif any(word in design_input.lower() for word in ["friendly", "casual", "approachable"]):
            characteristics["appearance_style"] = "friendly"
        elif any(word in design_input.lower() for word in ["creative", "artistic", "colorful"]):
            characteristics["appearance_style"] = "creative"

        # Personality keywords
        if any(word in design_input.lower() for word in ["enthusiastic", "energetic", "excited"]):
            characteristics["personality"] = "enthusiastic"
        elif any(word in design_input.lower() for word in ["calm", "patient", "gentle"]):
            characteristics["personality"] = "calm"
        elif any(
            word in design_input.lower() for word in ["encouraging", "supportive", "positive"]
        ):
            characteristics["personality"] = "encouraging"

        return characteristics

    def _extract_embodiment_characteristics(self, user_id: UUID) -> dict[str, Any] | None:
        """Extract embodiment characteristics from design chat history."""
        messages = st.session_state.get("design_chat_messages", [])
        user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]

        if not user_messages:
            return None

        # Combine all user input
        combined_input = " ".join(user_messages)

        # Extract characteristics
        characteristics = self._extract_design_characteristics(combined_input)

        # Add default values if not specified
        characteristics.setdefault("appearance_style", "friendly")
        characteristics.setdefault("personality", "encouraging")
        characteristics.setdefault("communication_style", "conversational")

        return characteristics

    def _is_design_complete(self, design_input: str, characteristics: dict[str, Any]) -> bool:
        """Check if design seems complete based on input and characteristics."""
        # Simple heuristic: check if user has provided enough detail
        word_count = len(design_input.split())
        has_characteristics = len(characteristics) > 0

        return word_count > 20 and has_characteristics

    def _get_default_embodiment_characteristics(self) -> dict[str, Any]:
        """Get default embodiment characteristics."""
        return {
            "appearance_style": "friendly",
            "personality": "encouraging",
            "communication_style": "conversational",
            "age_range": "adult",
            "formality_level": "casual",
            "teaching_approach": "supportive",
        }

    def _start_new_topic(self) -> None:
        """Start a new chat topic."""
        if st.session_state.get("chat_messages"):
            # Add topic separator
            st.session_state.chat_messages.append(
                {
                    "role": "assistant",
                    "content": "--- New Topic ---\nWhat would you like to discuss now?",
                    "timestamp": time.time(),
                }
            )
        st.rerun()

    def _export_chat_history(self) -> None:
        """Export chat history."""
        messages = st.session_state.get("chat_messages", [])
        if messages:
            # Create export data
            export_data = []
            for msg in messages:
                export_data.append(
                    {
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(msg.get("timestamp", time.time()))
                        ),
                    }
                )

            # Convert to text format
            export_text = "\n".join(
                [
                    f"[{msg['timestamp']}] {msg['role'].upper()}: {msg['content']}"
                    for msg in export_data
                ]
            )

            st.download_button(
                label="Download Chat History",
                data=export_text,
                file_name=f"gitte_chat_history_{int(time.time())}.txt",
                mime="text/plain",
            )


# Global chat UI instance
chat_ui = ChatUI()


# Convenience functions
def render_chat_interface(user_id: UUID) -> None:
    """Render chat interface."""
    chat_ui.render_chat_interface(user_id)


def render_embodiment_design_chat(user_id: UUID) -> dict[str, Any] | None:
    """Render embodiment design chat."""
    return chat_ui.render_embodiment_design_chat(user_id)


def render_chat_history(user_id: UUID) -> None:
    """Render chat history."""
    chat_ui.render_chat_history(user_id)
