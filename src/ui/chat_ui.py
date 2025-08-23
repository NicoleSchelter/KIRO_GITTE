"""
Chat UI components for GITTE system.
Provides Streamlit components for embodiment chat interface with study participation integration.
"""

import logging
import time
from typing import Any
from uuid import UUID, uuid4

import streamlit as st

from config.config import get_text, config
from src.data.database import get_session
from src.data.models import ConsentType, ChatMessageType, StudyPALDType
from src.logic.embodiment import get_embodiment_logic
from src.logic.llm import get_llm_logic
from src.logic.pald import PALDManager
from src.logic.chat_logic import ChatLogic
from src.logic.image_generation_logic import ImageGenerationLogic
from src.services.consent_service import get_study_consent_service
from src.services.chat_service import ChatService
from src.services.llm_service import get_llm_service, LLMService
from src.services.image_generation_service import ImageGenerationService
from src.services.image_service import get_image_service

logger = logging.getLogger(__name__)


class ChatUI:
    """UI components for embodiment chat interface with study participation integration."""

    def __init__(self):
        self.llm_logic = get_llm_logic()
        self.embodiment_logic = get_embodiment_logic()
        self.consent_service = get_study_consent_service()
        # Study participation components
        self.chat_logic = None
        self.image_generation_logic = None
        self.chat_service = None
        self.image_generation_service = None

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

    def render_study_participation_chat(self, pseudonym_id: UUID) -> None:
        """
        Render enhanced chat interface for study participation with PALD processing.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
        """
        # Initialize study participation components
        self._initialize_study_components()
        
        # Check consent for AI interaction
        if not self._check_study_chat_consent(pseudonym_id):
            return

        st.title("🤖 Chat with Your Learning Assistant")
        st.caption("Your responses will be processed through our PALD pipeline for personalized learning")

        # Initialize session state for study chat
        self._initialize_study_session_state(pseudonym_id)
        
        # Render study chat interface
        self._render_study_chat_header(pseudonym_id)
        self._render_pald_processing_status()
        self._render_study_chat_messages()
        self._render_study_chat_input(pseudonym_id)
        self._render_feedback_interface(pseudonym_id)
        self._render_study_chat_controls(pseudonym_id)

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
        """Render chat input field with unique keys."""
        # Generate unique key based on user and timestamp
        chat_session_key = f"chat_input_{user_id}_{int(time.time() / 300)}"  # 5min windows
        
        # Initialize input state if not exists
        if f"chat_state_{user_id}" not in st.session_state:
            st.session_state[f"chat_state_{user_id}"] = {
                "message_count": 0,
                "last_activity": time.time(),
                "input_key": chat_session_key
            }
        
        user_input = st.chat_input(
            "Type your message here...", 
            key=st.session_state[f"chat_state_{user_id}"]["input_key"]
        )

        if user_input:
            # Increment message count for unique keys
            st.session_state[f"chat_state_{user_id}"]["message_count"] += 1
            st.session_state[f"chat_state_{user_id}"]["last_activity"] = time.time()
            
            # Process message without immediate rerun
            self._add_message_and_process(user_id, user_input)

    def _add_message_and_process(self, user_id: UUID, message: str) -> None:
        """Add message and process response without triggering rerun."""
        try:
            # Add user message
            chat_key = f"chat_messages_{user_id}"
            if chat_key not in st.session_state:
                st.session_state[chat_key] = []
            
            st.session_state[chat_key].append({
                "role": "user",
                "content": message.strip(),
                "timestamp": time.time(),
                "id": f"msg_{len(st.session_state[chat_key])}"
            })

            # Process in background without rerun
            with st.spinner("🤖 Assistant is thinking..."):
                response = self._process_chat_input(user_id, message)

            # Add assistant response
            st.session_state[chat_key].append({
                "role": "assistant", 
                "content": response, 
                "timestamp": time.time(),
                "id": f"msg_{len(st.session_state[chat_key])}"
            })

            # Single rerun at the end
            st.rerun()

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            st.error("Failed to send message. Please try again.")


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

    # === Study Chat Processing Methods ===

    def _get_current_pseudonym(self) -> UUID | None:
        """Get current pseudonym from session state."""
        return st.session_state.get("current_pseudonym_id")

    def _get_study_welcome_message(self, pseudonym_id: UUID) -> str:
        """Get welcome message for study participation chat."""
        return """
        Welcome to your personalized learning assistant chat! 🤖
        
        I'm here to help you learn and explore topics while we create a visual representation 
        of your ideal learning companion. 
        
        **How it works:**
        1. Describe your ideal learning assistant or ask questions
        2. I'll extract key characteristics (PALD data) from your description
        3. Generate an image based on those characteristics
        4. You can provide feedback to refine the image
        
        Your interactions help us understand your learning preferences better.
        What would you like to discuss or explore today?
        """

    def _process_study_chat_input(self, pseudonym_id: UUID, user_input: str) -> None:
        """Process user input through the complete PALD pipeline."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        try:
            # Update processing status
            st.session_state["pald_processing_status"] = "extracting_pald"
            
            # Add user message to chat
            user_message = {
                "role": "user",
                "content": user_input,
                "timestamp": time.time(),
                "message_type": "chat"
            }
            session_data["messages"].append(user_message)
            
            # Process through chat logic
            with st.spinner("🔍 Processing your message..."):
                processing_result = self.chat_logic.process_chat_input(
                    pseudonym_id=pseudonym_id,
                    session_id=session_data["session_id"],
                    message_content=user_input,
                    message_type=ChatMessageType.USER
                )
            
            # Store chat message in database
            self.chat_service.store_chat_message(
                pseudonym_id=pseudonym_id,
                session_id=session_data["session_id"],
                message_type=ChatMessageType.USER,
                content=user_input,
                pald_data=processing_result.pald_data
            )
            
            # Update message with PALD extraction result
            user_message["pald_extracted"] = processing_result.pald_extracted
            user_message["processing_metadata"] = processing_result.processing_metadata
            
            # Generate assistant response
            assistant_response = self._generate_assistant_response(pseudonym_id, user_input, processing_result)
            
            # If PALD was extracted and image generation is enabled, start image generation
            if (processing_result.pald_extracted and 
                processing_result.pald_data and 
                st.session_state.get("enable_pald_processing", True)):
                
                self._start_image_generation_pipeline(pseudonym_id, processing_result.pald_data)
            
            st.session_state["pald_processing_status"] = "completed"
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error processing study chat input: {e}")
            st.session_state["pald_processing_status"] = "error"
            
            # Add error message
            error_message = {
                "role": "assistant",
                "content": "I apologize, but I encountered an error processing your message. Please try again.",
                "timestamp": time.time(),
                "message_type": "error",
                "error": str(e)
            }
            session_data["messages"].append(error_message)
            st.rerun()

    def _generate_assistant_response(self, pseudonym_id: UUID, user_input: str, processing_result) -> str:
        """Generate assistant response based on user input and processing result."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        try:
            # Create context-aware response
            if processing_result.pald_extracted:
                response_content = f"""
                Thank you for that description! I've extracted some key characteristics about your ideal learning assistant:
                
                {self._format_pald_summary(processing_result.pald_data)}
                
                I'm now generating a visual representation based on these characteristics. 
                This may take a moment...
                """
            else:
                response_content = """
                I understand your message, though I wasn't able to extract specific visual characteristics 
                for your learning assistant from it. Feel free to describe more about how you'd like 
                your learning assistant to look or behave, and I'll help create a visual representation.
                """
            
            # Add assistant message
            assistant_message = {
                "role": "assistant",
                "content": response_content,
                "timestamp": time.time(),
                "message_type": "response",
                "pald_extracted": processing_result.pald_extracted
            }
            session_data["messages"].append(assistant_message)
            
            # Store in database
            self.chat_service.store_chat_message(
                pseudonym_id=pseudonym_id,
                session_id=session_data["session_id"],
                message_type=ChatMessageType.ASSISTANT,
                content=response_content
            )
            
            return response_content
            
        except Exception as e:
            logger.error(f"Error generating assistant response: {e}")
            return "I apologize, but I had trouble generating a response. Please try again."

    def _start_image_generation_pipeline(self, pseudonym_id: UUID, pald_data: dict[str, Any]) -> None:
        """Start the image generation and consistency checking pipeline."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        try:
            st.session_state["pald_processing_status"] = "generating_image"
            
            # Generate image from PALD data
            with st.spinner("🎨 Generating your learning assistant image..."):
                image_result = self.image_generation_logic.generate_image_from_pald(pald_data)
            
            if image_result.success:
                st.session_state["pald_processing_status"] = "describing_image"
                
                # Generate description of the image
                with st.spinner("📝 Analyzing the generated image..."):
                    description_result = self.image_generation_logic.describe_generated_image(
                        image_result.image_path
                    )
                
                # Check consistency if enabled
                if st.session_state.get("enable_consistency_check", True):
                    self._perform_consistency_check(pseudonym_id, pald_data, description_result)
                else:
                    # Skip consistency check, present image directly
                    self._present_final_image(pseudonym_id, image_result, description_result)
            else:
                # Image generation failed
                self._handle_image_generation_error(pseudonym_id, image_result.error_message)
                
        except Exception as e:
            logger.error(f"Error in image generation pipeline: {e}")
            self._handle_image_generation_error(pseudonym_id, str(e))

    def _perform_consistency_check(self, pseudonym_id: UUID, input_pald: dict[str, Any], description_result) -> None:
        """Perform PALD consistency checking."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        try:
            st.session_state["pald_processing_status"] = "checking_consistency"
            st.session_state["consistency_loop_active"] = True
            
            # Extract PALD from image description
            description_pald_result = self.chat_logic.extract_pald_from_text(description_result.description)
            
            if description_pald_result.success:
                # Check consistency
                consistency_result = self.chat_logic.check_pald_consistency(
                    input_pald, description_pald_result.pald_data
                )
                
                # Update consistency iterations
                session_data["consistency_iterations"] += 1
                
                # Store consistency check results
                session_data["current_consistency"] = {
                    "score": consistency_result.consistency_score,
                    "is_consistent": consistency_result.is_consistent,
                    "differences": consistency_result.differences,
                    "recommendation": consistency_result.recommendation
                }
                
                # Decide next action based on consistency result
                if (consistency_result.is_consistent or 
                    consistency_result.recommendation == "accept" or
                    session_data["consistency_iterations"] >= config.pald_boundary.pald_consistency_max_iterations):
                    
                    # Accept current result
                    self._present_final_image(pseudonym_id, description_result, consistency_result)
                else:
                    # Regenerate image
                    self._regenerate_image_for_consistency(pseudonym_id, input_pald, consistency_result)
            else:
                # PALD extraction from description failed, accept current image
                self._present_final_image(pseudonym_id, description_result, None)
                
        except Exception as e:
            logger.error(f"Error in consistency check: {e}")
            # On error, accept current image to avoid infinite loops
            self._present_final_image(pseudonym_id, description_result, None)
        finally:
            st.session_state["consistency_loop_active"] = False

    def _present_final_image(self, pseudonym_id: UUID, image_result, consistency_result=None) -> None:
        """Present the final image to the user."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        try:
            # Create final message with image
            consistency_info = ""
            if consistency_result:
                consistency_info = f"\n\n⚖️ Consistency Score: {consistency_result.consistency_score:.2f}"
            
            final_message = {
                "role": "assistant",
                "content": f"Here's your personalized learning assistant!{consistency_info}",
                "timestamp": time.time(),
                "message_type": "image_result",
                "image_path": image_result.image_path,
                "consistency_score": consistency_result.consistency_score if consistency_result else None
            }
            
            session_data["messages"].append(final_message)
            session_data["current_image"] = image_result.image_path
            
            # Enable feedback interface
            st.session_state["feedback_active"] = True
            st.session_state["pald_processing_status"] = "completed"
            
        except Exception as e:
            logger.error(f"Error presenting final image: {e}")

    def _process_feedback(self, pseudonym_id: UUID, feedback_text: str) -> None:
        """Process user feedback and potentially regenerate image."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        try:
            current_round = session_data.get("feedback_round", 0)
            
            # Process feedback through chat logic
            feedback_result = self.chat_logic.manage_feedback_loop(
                pseudonym_id=pseudonym_id,
                session_id=session_data["session_id"],
                feedback_text=feedback_text,
                current_round=current_round + 1,
                image_id=None  # Would be set if we had image IDs
            )
            
            # Store feedback in database
            self.chat_service.store_feedback_record(
                pseudonym_id=pseudonym_id,
                session_id=session_data["session_id"],
                feedback_text=feedback_text,
                round_number=feedback_result.round_number,
                feedback_pald=feedback_result.feedback_pald
            )
            
            # Update session state
            session_data["feedback_round"] = feedback_result.round_number
            
            # Add feedback message to chat
            feedback_message = {
                "role": "user",
                "content": f"**Feedback:** {feedback_text}",
                "timestamp": time.time(),
                "message_type": "feedback",
                "round_number": feedback_result.round_number
            }
            session_data["messages"].append(feedback_message)
            
            if feedback_result.should_continue and not feedback_result.max_rounds_reached:
                # Process feedback and regenerate
                self._regenerate_from_feedback(pseudonym_id, feedback_result)
            else:
                # Max rounds reached or user wants to stop
                self._finalize_feedback_loop(pseudonym_id, feedback_result)
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            st.error("Failed to process feedback. Please try again.")

    def _accept_current_image(self, pseudonym_id: UUID) -> None:
        """Accept the current image and end feedback loop."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        # Add acceptance message
        acceptance_message = {
            "role": "assistant",
            "content": "Great! You've accepted the current image. Feel free to continue our conversation or describe other aspects of your learning preferences.",
            "timestamp": time.time(),
            "message_type": "acceptance"
        }
        session_data["messages"].append(acceptance_message)
        
        # Disable feedback interface
        st.session_state["feedback_active"] = False
        st.rerun()

    def _stop_feedback_loop(self, pseudonym_id: UUID) -> None:
        """Stop the feedback loop early at user request."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        try:
            current_round = session_data.get("feedback_round", 0)
            
            # Process stop request through chat logic
            stop_result = self.chat_logic.stop_feedback_loop(
                pseudonym_id=pseudonym_id,
                session_id=session_data["session_id"],
                current_round=current_round
            )
            
            # Add stop message
            stop_message = {
                "role": "assistant",
                "content": "Feedback loop stopped. We'll continue with the current image. What would you like to explore next?",
                "timestamp": time.time(),
                "message_type": "feedback_stopped"
            }
            session_data["messages"].append(stop_message)
            
            # Disable feedback interface
            st.session_state["feedback_active"] = False
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error stopping feedback loop: {e}")
            st.session_state["feedback_active"] = False
            st.rerun()

    def _format_pald_summary(self, pald_data: dict[str, Any]) -> str:
        """Format PALD data for display."""
        if not pald_data:
            return "No specific characteristics extracted."
        
        summary_parts = []
        
        for level, data in pald_data.items():
            if isinstance(data, dict) and data:
                level_name = level.replace("_", " ").title()
                summary_parts.append(f"**{level_name}:**")
                for key, value in data.items():
                    if value:
                        key_name = key.replace("_", " ").title()
                        summary_parts.append(f"  • {key_name}: {value}")
        
        return "\n".join(summary_parts) if summary_parts else "No specific characteristics extracted."

    def _get_feedback_history(self, pseudonym_id: UUID) -> list[dict[str, Any]]:
        """Get feedback history for the current session."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state.get(session_key, {})
        messages = session_data.get("messages", [])
        
        feedback_history = []
        for message in messages:
            if message.get("message_type") == "feedback":
                feedback_history.append({
                    "text": message["content"].replace("**Feedback:** ", ""),
                    "timestamp": time.strftime("%H:%M:%S", time.localtime(message.get("timestamp", time.time()))),
                    "round_number": message.get("round_number", 0)
                })
        
        return feedback_history

    def _show_session_info(self, pseudonym_id: UUID) -> None:
        """Show detailed session information in a modal."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state.get(session_key, {})
        
        # Create a modal-like display using expander
        with st.expander("📋 Detailed Session Information", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Session Details**")
                st.write(f"• **Session ID**: {str(session_data.get('session_id', 'N/A'))}")
                st.write(f"• **Pseudonym**: {str(pseudonym_id)[:8]}...")
                
                session_start = session_data.get("session_start", time.time())
                start_time = time.strftime("%H:%M:%S", time.localtime(session_start))
                st.write(f"• **Started**: {start_time}")
                
                duration = int((time.time() - session_start) / 60)
                st.write(f"• **Duration**: {duration} minutes")
            
            with col2:
                st.write("**Activity Summary**")
                messages = session_data.get("messages", [])
                user_messages = [m for m in messages if m["role"] == "user"]
                assistant_messages = [m for m in messages if m["role"] == "assistant"]
                
                st.write(f"• **User Messages**: {len(user_messages)}")
                st.write(f"• **Assistant Messages**: {len(assistant_messages)}")
                st.write(f"• **Feedback Rounds**: {session_data.get('feedback_round', 0)}")
                st.write(f"• **Consistency Checks**: {session_data.get('consistency_iterations', 0)}")
            
            # PALD processing summary
            st.write("**PALD Processing Summary**")
            pald_extracted_count = sum(1 for m in messages if m.get("pald_extracted"))
            images_generated = sum(1 for m in messages if m.get("image_path"))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("PALD Extractions", pald_extracted_count)
            with col2:
                st.metric("Images Generated", images_generated)
            with col3:
                current_consistency = st.session_state.get("current_consistency", {})
                consistency_score = current_consistency.get("score", 0)
                st.metric("Last Consistency", f"{consistency_score:.2f}")
            
            # Recent activity
            if messages:
                st.write("**Recent Activity**")
                recent_messages = messages[-3:] if len(messages) > 3 else messages
                for msg in recent_messages:
                    timestamp = time.strftime("%H:%M:%S", time.localtime(msg.get("timestamp", time.time())))
                    role_icon = "👤" if msg["role"] == "user" else "🤖"
                    content_preview = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                    st.write(f"• {timestamp} {role_icon} {content_preview}")
        
        # Close button
        if st.button("✅ Close Session Info"):
            st.rerun()

    def _start_new_study_session(self, pseudonym_id: UUID) -> None:
        """Start a new study chat session."""
        session_key = f"study_chat_{pseudonym_id}"
        current_time = time.time()
        
        # Reset session state
        st.session_state[session_key] = {
            "messages": [],
            "session_id": uuid4(),
            "session_start": current_time,
            "pald_processing_status": "idle",
            "consistency_loop_active": False,
            "consistency_iterations": 0,
            "feedback_round": 0,
            "max_feedback_rounds": config.pald_boundary.max_feedback_rounds,
            "current_image": None,
            "current_pald": None,
            "feedback_active": False,
            "processing_metadata": {},
        }
        
        # Add welcome message
        welcome_msg = self._get_study_welcome_message(pseudonym_id)
        st.session_state[session_key]["messages"].append({
            "role": "assistant",
            "content": welcome_msg,
            "timestamp": current_time,
            "message_type": "welcome"
        })
        
        st.session_state["feedback_active"] = False
        st.session_state["pald_processing_status"] = "idle"
        st.success("🔄 New study session started!")
        st.rerun()

    def _export_study_session_data(self, pseudonym_id: UUID) -> None:
        """Export study session data."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state.get(session_key, {})
        
        if not session_data.get("messages"):
            st.warning("No session data to export.")
            return
        
        # Create export data
        export_data = {
            "session_id": str(session_data.get("session_id", "")),
            "pseudonym_id": str(pseudonym_id),
            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "statistics": {
                "total_messages": len(session_data.get("messages", [])),
                "feedback_rounds": session_data.get("feedback_round", 0),
                "consistency_iterations": session_data.get("consistency_iterations", 0),
            },
            "messages": []
        }
        
        # Add messages
        for msg in session_data.get("messages", []):
            export_msg = {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(msg.get("timestamp", time.time()))),
                "message_type": msg.get("message_type", "chat")
            }
            
            # Add metadata if present
            if msg.get("pald_extracted"):
                export_msg["pald_extracted"] = True
            if msg.get("consistency_score"):
                export_msg["consistency_score"] = msg["consistency_score"]
            if msg.get("round_number"):
                export_msg["round_number"] = msg["round_number"]
                
            export_data["messages"].append(export_msg)
        
        # Convert to JSON
        import json
        export_json = json.dumps(export_data, indent=2)
        
        st.download_button(
            label="Download Session Data (JSON)",
            data=export_json,
            file_name=f"study_session_{pseudonym_id}_{int(time.time())}.json",
            mime="application/json"
        )

    def _clear_study_session(self, pseudonym_id: UUID) -> None:
        """Clear the current study session."""
        session_key = f"study_chat_{pseudonym_id}"
        if session_key in st.session_state:
            del st.session_state[session_key]
        
        st.session_state["feedback_active"] = False
        st.session_state["pald_processing_status"] = "idle"
        st.success("Session cleared successfully!")
        st.rerun()

    # Placeholder methods for missing functionality
    def _regenerate_image_for_consistency(self, pseudonym_id: UUID, input_pald: dict[str, Any], consistency_result) -> None:
        """Regenerate image to improve consistency (placeholder)."""
        # This would implement the regeneration logic
        # For now, we'll just present the current image
        logger.info("Consistency regeneration not fully implemented, accepting current image")
        self._present_final_image(pseudonym_id, None, consistency_result)

    def _regenerate_from_feedback(self, pseudonym_id: UUID, feedback_result) -> None:
        """Regenerate image based on feedback (placeholder)."""
        # This would implement feedback-based regeneration
        # For now, we'll just add a message indicating processing
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        processing_message = {
            "role": "assistant",
            "content": "Thank you for your feedback! I'm processing your suggestions to improve the image...",
            "timestamp": time.time(),
            "message_type": "feedback_processing"
        }
        session_data["messages"].append(processing_message)
        
        # Disable feedback for now
        st.session_state["feedback_active"] = False
        st.rerun()

    def _finalize_feedback_loop(self, pseudonym_id: UUID, feedback_result) -> None:
        """Finalize the feedback loop."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        final_message = {
            "role": "assistant",
            "content": f"We've completed {feedback_result.round_number} rounds of feedback. Thank you for helping improve your learning assistant! What would you like to explore next?",
            "timestamp": time.time(),
            "message_type": "feedback_complete"
        }
        session_data["messages"].append(final_message)
        
        st.session_state["feedback_active"] = False
        st.rerun()

    def _handle_image_generation_error(self, pseudonym_id: UUID, error_message: str) -> None:
        """Handle image generation errors."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        error_msg = {
            "role": "assistant",
            "content": f"I apologize, but I encountered an issue generating your image: {error_message}. Let's continue our conversation, and I'll try again with your next description.",
            "timestamp": time.time(),
            "message_type": "error"
        }
        session_data["messages"].append(error_msg)
        
        st.session_state["pald_processing_status"] = "error"
        st.rerun()

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

    # === Study Participation Chat Methods ===

    def _initialize_study_components(self) -> None:
        """Initialize study participation components."""
        if self.chat_logic is None:
            llm_service = get_llm_service()
            self.chat_logic = ChatLogic(llm_service)
        
        if self.image_generation_logic is None:
            # Initialize services with database session
            if "db_session" not in st.session_state:
                st.session_state.db_session = get_session()
            
            image_service = ImageGenerationService(st.session_state.db_session)
            self.image_generation_logic = ImageGenerationLogic(image_service)
        
        if self.chat_service is None:
            if "db_session" not in st.session_state:
                st.session_state.db_session = get_session()
            self.chat_service = ChatService(st.session_state.db_session)

    def _check_study_chat_consent(self, pseudonym_id: UUID) -> bool:
        """Check if participant has consent for AI interaction in study context."""
        try:
            # For study participation, we assume consent was already checked during onboarding
            # But we can add additional checks here if needed
            return True
        except Exception as e:
            logger.error(f"Error checking study chat consent for pseudonym {pseudonym_id}: {e}")
            st.error("Error checking consent status.")
            return False

    def _initialize_study_session_state(self, pseudonym_id: UUID) -> None:
        """Initialize session state for study participation chat."""
        session_key = f"study_chat_{pseudonym_id}"
        
        if session_key not in st.session_state:
            current_time = time.time()
            st.session_state[session_key] = {
                "messages": [],
                "session_id": uuid4(),
                "session_start": current_time,
                "pald_processing_status": "idle",
                "consistency_loop_active": False,
                "consistency_iterations": 0,
                "feedback_round": 0,
                "max_feedback_rounds": config.pald_boundary.max_feedback_rounds,
                "current_image": None,
                "current_pald": None,
                "feedback_active": False,
                "processing_metadata": {},
            }
            
            # Add welcome message
            welcome_msg = self._get_study_welcome_message(pseudonym_id)
            st.session_state[session_key]["messages"].append({
                "role": "assistant",
                "content": welcome_msg,
                "timestamp": current_time,
                "message_type": "welcome"
            })

    def _render_study_chat_header(self, pseudonym_id: UUID) -> None:
        """Render study chat header with session info."""
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.write("💬 **Study Participation Chat Session**")
            st.caption(f"Session ID: {str(session_data['session_id'])[:8]}...")
        
        with col2:
            feedback_round = session_data.get("feedback_round", 0)
            max_rounds = session_data.get("max_feedback_rounds", 3)
            st.metric("Feedback Round", f"{feedback_round}/{max_rounds}")
        
        with col3:
            consistency_iterations = session_data.get("consistency_iterations", 0)
            st.metric("Consistency Checks", consistency_iterations)
        
        with col4:
            if st.button("🔄 New Session"):
                self._start_new_study_session(pseudonym_id)

    def _render_pald_processing_status(self) -> None:
        """Render enhanced PALD processing status indicators with detailed feedback."""
        # Get current processing status from session state
        processing_status = st.session_state.get("pald_processing_status", "idle")
        consistency_active = st.session_state.get("consistency_loop_active", False)
        
        # Status indicator container with enhanced visual feedback
        status_container = st.container()
        
        with status_container:
            if processing_status == "extracting_pald":
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info("🔍 **PALD Extraction**: Analyzing your message for learning assistant characteristics...")
                with col2:
                    if st.button("⏸️ Defer PALD", key="defer_pald_extraction"):
                        st.session_state["pald_analysis_deferred"] = True
                        st.session_state["pald_processing_status"] = "deferred"
                        st.rerun()
                        
            elif processing_status == "generating_image":
                progress_bar = st.progress(0.3)
                st.info("🎨 **Image Generation**: Creating visual representation from PALD data...")
                st.caption("This may take 15-30 seconds depending on complexity")
                
            elif processing_status == "describing_image":
                progress_bar = st.progress(0.7)
                st.info("📝 **Image Analysis**: Extracting characteristics from generated image...")
                
            elif processing_status == "checking_consistency":
                iterations = st.session_state.get("consistency_iterations", 0)
                max_iterations = config.pald_boundary.pald_consistency_max_iterations
                progress = min(iterations / max_iterations, 1.0)
                progress_bar = st.progress(progress)
                st.warning(f"⚖️ **Consistency Check**: Comparing input vs. generated characteristics (iteration {iterations}/{max_iterations})")
                
            elif processing_status == "processing_feedback":
                st.info("💭 **Feedback Processing**: Analyzing your feedback for image improvements...")
                
            elif processing_status == "deferred":
                st.warning("⏸️ **PALD Analysis Deferred**: Processing will continue without deep PALD analysis")
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("▶️ Resume PALD", key="resume_pald_analysis"):
                        st.session_state["pald_analysis_deferred"] = False
                        st.session_state["pald_processing_status"] = "idle"
                        st.rerun()
                        
            elif consistency_active:
                iterations = st.session_state.get("consistency_iterations", 0)
                max_iterations = config.pald_boundary.pald_consistency_max_iterations
                current_consistency = st.session_state.get("current_consistency", {})
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.warning(f"🔄 **Consistency Loop Active** (iteration {iterations}/{max_iterations})")
                    if current_consistency.get("score"):
                        st.caption(f"Current consistency score: {current_consistency['score']:.2f}")
                with col2:
                    if st.button("⏹️ Accept Current", key="accept_consistency"):
                        st.session_state["consistency_loop_active"] = False
                        st.session_state["pald_processing_status"] = "completed"
                        st.rerun()
                        
            elif processing_status == "completed":
                st.success("✅ **Processing Complete**: Your learning assistant is ready!")
                
            elif processing_status == "error":
                st.error("❌ **Processing Error**: Encountered an issue during processing")
                col1, col2 = st.columns([3, 1])
                with col2:
                    if st.button("🔄 Retry", key="retry_processing"):
                        st.session_state["pald_processing_status"] = "idle"
                        st.rerun()

    def _render_study_chat_messages(self) -> None:
        """Render study chat messages with enhanced metadata and processing indicators."""
        # Get messages from current session
        current_pseudonym = self._get_current_pseudonym()
        if not current_pseudonym:
            return
            
        session_key = f"study_chat_{current_pseudonym}"
        messages = st.session_state.get(session_key, {}).get("messages", [])
        
        # Create scrollable chat container
        chat_container = st.container()
        
        with chat_container:
            for i, message in enumerate(messages):
                message_type = message.get("message_type", "chat")
                
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                        
                        # Enhanced PALD extraction indicators
                        if message.get("pald_extracted"):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.success("🔍 **PALD Extracted**: Learning assistant characteristics identified")
                            with col2:
                                if st.button("📊 View PALD", key=f"view_pald_{i}"):
                                    with st.expander("PALD Data", expanded=True):
                                        pald_data = message.get("processing_metadata", {}).get("pald_data", {})
                                        if pald_data:
                                            st.json(pald_data)
                                        else:
                                            st.info("No PALD data available")
                        elif message.get("processing_metadata", {}).get("pald_attempted"):
                            st.info("🔍 **PALD Processing**: Attempted but no characteristics extracted")
                        
                        # Show processing metadata if available
                        processing_meta = message.get("processing_metadata", {})
                        if processing_meta:
                            with st.expander("Processing Details", expanded=False):
                                col1, col2 = st.columns(2)
                                with col1:
                                    if processing_meta.get("processing_time"):
                                        st.metric("Processing Time", f"{processing_meta['processing_time']:.2f}s")
                                    if processing_meta.get("token_count"):
                                        st.metric("Tokens Used", processing_meta["token_count"])
                                with col2:
                                    if processing_meta.get("model_used"):
                                        st.write(f"**Model**: {processing_meta['model_used']}")
                                    if processing_meta.get("temperature"):
                                        st.write(f"**Temperature**: {processing_meta['temperature']}")
                        
                elif message["role"] == "assistant":
                    with st.chat_message("assistant"):
                        st.write(message["content"])
                        
                        # Enhanced consistency information display
                        if message.get("consistency_score"):
                            score = message["consistency_score"]
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                # Color-coded consistency score
                                if score >= 0.8:
                                    st.success(f"⚖️ **High Consistency**: {score:.2f}")
                                elif score >= 0.6:
                                    st.warning(f"⚖️ **Medium Consistency**: {score:.2f}")
                                else:
                                    st.error(f"⚖️ **Low Consistency**: {score:.2f}")
                            with col2:
                                if st.button("📈 Details", key=f"consistency_details_{i}"):
                                    consistency_data = message.get("consistency_details", {})
                                    with st.expander("Consistency Analysis", expanded=True):
                                        if consistency_data:
                                            st.write("**Differences Found:**")
                                            for diff in consistency_data.get("differences", []):
                                                st.write(f"• {diff}")
                                            if consistency_data.get("recommendation"):
                                                st.write(f"**Recommendation**: {consistency_data['recommendation']}")
                                        else:
                                            st.info("No detailed consistency data available")
                        
                        # Enhanced image display with metadata
                        if message.get("image_path"):
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.image(message["image_path"], caption="Generated Learning Assistant")
                            with col2:
                                # Image generation metadata
                                image_meta = message.get("image_metadata", {})
                                if image_meta:
                                    st.write("**Generation Info:**")
                                    if image_meta.get("generation_time"):
                                        st.metric("Generation Time", f"{image_meta['generation_time']:.1f}s")
                                    if image_meta.get("prompt_tokens"):
                                        st.metric("Prompt Tokens", image_meta["prompt_tokens"])
                                    if image_meta.get("model_version"):
                                        st.caption(f"Model: {image_meta['model_version']}")
                            
                            # Enhanced feedback controls for latest image
                            if i == len(messages) - 1 and not st.session_state.get("feedback_active", False):
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if st.button("💭 Provide Feedback", key=f"feedback_btn_{i}", type="primary"):
                                        st.session_state["feedback_active"] = True
                                        st.rerun()
                                with col2:
                                    if st.button("👍 Accept Image", key=f"accept_btn_{i}"):
                                        self._accept_current_image(current_pseudonym)
                                with col3:
                                    if st.button("🔄 Regenerate", key=f"regen_btn_{i}"):
                                        st.session_state["feedback_active"] = True
                                        st.session_state["auto_feedback"] = "Please regenerate with the same characteristics"
                                        st.rerun()
                        
                        # Show feedback round information for feedback messages
                        if message_type == "feedback":
                            round_num = message.get("round_number", 0)
                            st.caption(f"💭 Feedback Round {round_num}")
                        
                        # Show processing status for system messages
                        elif message_type in ["feedback_processing", "feedback_complete", "feedback_stopped"]:
                            if message_type == "feedback_processing":
                                st.info("🔄 Processing your feedback...")
                            elif message_type == "feedback_complete":
                                st.success("✅ Feedback processing complete")
                            elif message_type == "feedback_stopped":
                                st.warning("⏹️ Feedback loop stopped by user")
                
                # Add timestamp for all messages
                timestamp = message.get("timestamp", time.time())
                st.caption(f"⏰ {time.strftime('%H:%M:%S', time.localtime(timestamp))}")
                
                # Add separator between messages (except for the last one)
                if i < len(messages) - 1:
                    st.divider()

    def _render_study_chat_input(self, pseudonym_id: UUID) -> None:
        """Render study chat input with PALD processing."""
        session_key = f"study_chat_{pseudonym_id}"
        
        # Check if processing is active
        processing_status = st.session_state.get("pald_processing_status", "idle")
        is_processing = processing_status not in ["idle", "completed", "error"]
        
        # Disable input during processing
        disabled = is_processing or st.session_state.get("feedback_active", False)
        
        placeholder_text = "Describe your ideal learning assistant..." if not disabled else "Processing..."
        
        user_input = st.chat_input(
            placeholder_text,
            disabled=disabled,
            key=f"study_chat_input_{pseudonym_id}"
        )
        
        if user_input and not disabled:
            self._process_study_chat_input(pseudonym_id, user_input)

    def _render_feedback_interface(self, pseudonym_id: UUID) -> None:
        """Render enhanced feedback collection interface with detailed round counting and controls."""
        if not st.session_state.get("feedback_active", False):
            return
        
        session_key = f"study_chat_{pseudonym_id}"
        session_data = st.session_state[session_key]
        
        current_round = session_data.get("feedback_round", 0)
        max_rounds = session_data.get("max_feedback_rounds", 3)
        
        st.divider()
        
        # Enhanced feedback header with progress indicator
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader("💭 Feedback Collection")
            progress = (current_round + 1) / max_rounds
            st.progress(progress, text=f"Round {current_round + 1} of {max_rounds}")
        
        with col2:
            st.metric("Rounds Used", f"{current_round}/{max_rounds}")
        
        with col3:
            remaining = max_rounds - current_round - 1
            st.metric("Remaining", remaining)
        
        # Feedback guidance
        st.info("""
        **Feedback Guidelines:**
        • Be specific about what you'd like to change
        • Mention visual characteristics (appearance, style, colors)
        • Describe personality traits or expressions
        • Note any missing or unwanted elements
        """)
        
        # Current image display (if available)
        current_image = session_data.get("current_image")
        if current_image:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(current_image, caption="Current Image", use_column_width=True)
            with col2:
                # Show current PALD characteristics if available
                current_pald = session_data.get("current_pald", {})
                if current_pald:
                    st.write("**Current Characteristics:**")
                    st.json(current_pald)
        
        # Feedback input with enhanced options
        feedback_text = st.text_area(
            "What would you like to change about the generated image?",
            placeholder="e.g., Make the character more friendly, change the hair color to brown, add glasses, make them look more professional...",
            key=f"feedback_input_{current_round}",
            height=100
        )
        
        # Quick feedback options
        st.write("**Quick Feedback Options:**")
        quick_feedback_cols = st.columns(4)
        
        quick_options = [
            ("😊 More Friendly", "Make the character appear more friendly and approachable"),
            ("👔 More Professional", "Make the character look more professional and formal"),
            ("🎨 More Creative", "Add more creative and artistic elements"),
            ("🤓 More Academic", "Make the character appear more scholarly and academic")
        ]
        
        selected_quick = None
        for i, (label, description) in enumerate(quick_options):
            with quick_feedback_cols[i]:
                if st.button(label, key=f"quick_{i}"):
                    selected_quick = description
        
        # Combine manual and quick feedback
        final_feedback = feedback_text.strip()
        if selected_quick:
            final_feedback = f"{final_feedback}\n{selected_quick}".strip()
        
        # Feedback action buttons with enhanced controls
        st.write("**Actions:**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            submit_disabled = not final_feedback or current_round >= max_rounds
            if st.button("✅ Submit Feedback", disabled=submit_disabled, type="primary"):
                self._process_feedback(pseudonym_id, final_feedback)
        
        with col2:
            if st.button("👍 Accept Current Image", type="secondary"):
                self._accept_current_image(pseudonym_id)
        
        with col3:
            if st.button("🛑 Stop Feedback Loop", type="secondary"):
                self._stop_feedback_loop(pseudonym_id)
        
        with col4:
            if st.button("❌ Skip This Round"):
                st.session_state["feedback_active"] = False
                st.rerun()
        
        # Show warning if approaching max rounds
        if current_round >= max_rounds - 1:
            st.warning(f"⚠️ This is your final feedback round ({max_rounds}/{max_rounds}). After this, the current image will be finalized.")
        
        # Feedback history for this session
        if current_round > 0:
            with st.expander("📝 Previous Feedback in This Session"):
                feedback_history = self._get_feedback_history(pseudonym_id)
                for i, feedback in enumerate(feedback_history, 1):
                    st.write(f"**Round {i}:** {feedback['text']}")
                    if feedback.get('timestamp'):
                        st.caption(f"Submitted: {feedback['timestamp']}")
                    st.divider()

    def _render_study_chat_controls(self, pseudonym_id: UUID) -> None:
        """Render enhanced study chat control panel with detailed session management."""
        with st.sidebar:
            st.subheader("🎛️ Study Chat Controls")
            
            session_key = f"study_chat_{pseudonym_id}"
            session_data = st.session_state.get(session_key, {})
            
            # Enhanced session statistics with visual indicators
            st.write("**📊 Session Statistics**")
            
            col1, col2 = st.columns(2)
            with col1:
                message_count = len(session_data.get("messages", []))
                st.metric("Messages", message_count)
                
                feedback_round = session_data.get("feedback_round", 0)
                max_feedback = session_data.get("max_feedback_rounds", 3)
                st.metric("Feedback", f"{feedback_round}/{max_feedback}")
            
            with col2:
                consistency_iterations = session_data.get("consistency_iterations", 0)
                st.metric("Consistency Checks", consistency_iterations)
                
                # Session duration
                session_start = session_data.get("session_start", time.time())
                duration_minutes = int((time.time() - session_start) / 60)
                st.metric("Duration", f"{duration_minutes}m")
            
            # Processing status indicator
            processing_status = st.session_state.get("pald_processing_status", "idle")
            status_colors = {
                "idle": "🟢",
                "extracting_pald": "🟡", 
                "generating_image": "🟡",
                "checking_consistency": "🟠",
                "completed": "🟢",
                "error": "🔴",
                "deferred": "🟣"
            }
            status_color = status_colors.get(processing_status, "⚪")
            st.write(f"**Status**: {status_color} {processing_status.replace('_', ' ').title()}")
            
            st.divider()
            
            # Quick actions
            st.write("**⚡ Quick Actions**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📝 Export Data", use_container_width=True):
                    self._export_study_session_data(pseudonym_id)
                
                if st.button("🔄 New Session", use_container_width=True):
                    self._start_new_study_session(pseudonym_id)
            
            with col2:
                if st.button("📋 Session Info", use_container_width=True):
                    self._show_session_info(pseudonym_id)
                
                if st.button("🗑️ Clear Session", use_container_width=True, type="secondary"):
                    if st.button("⚠️ Confirm Clear", use_container_width=True, type="secondary"):
                        self._clear_study_session(pseudonym_id)
            
            st.divider()
            
            # Enhanced PALD processing settings
            with st.expander("🔧 PALD Processing Settings"):
                st.session_state["enable_pald_processing"] = st.checkbox(
                    "Enable PALD Processing",
                    value=st.session_state.get("enable_pald_processing", True),
                    help="Extract PALD data from messages for learning assistant characteristics"
                )
                
                st.session_state["enable_consistency_check"] = st.checkbox(
                    "Enable Consistency Checking",
                    value=st.session_state.get("enable_consistency_check", True),
                    help="Check consistency between input and generated content"
                )
                
                st.session_state["auto_image_generation"] = st.checkbox(
                    "Auto Image Generation",
                    value=st.session_state.get("auto_image_generation", True),
                    help="Automatically generate images when PALD data is extracted"
                )
                
                # Consistency threshold
                consistency_threshold = st.slider(
                    "Consistency Threshold",
                    min_value=0.0,
                    max_value=1.0,
                    value=st.session_state.get("consistency_threshold", 0.8),
                    step=0.1,
                    help="Minimum consistency score to accept generated content"
                )
                st.session_state["consistency_threshold"] = consistency_threshold
            
            # Enhanced feedback settings
            with st.expander("💭 Feedback Settings"):
                current_max = session_data.get("max_feedback_rounds", 3)
                new_max_rounds = st.slider(
                    "Max Feedback Rounds",
                    min_value=1,
                    max_value=10,
                    value=current_max,
                    help="Maximum number of feedback rounds per image"
                )
                
                if new_max_rounds != current_max:
                    session_data["max_feedback_rounds"] = new_max_rounds
                    st.success(f"Updated max feedback rounds to {new_max_rounds}")
                
                st.session_state["enable_quick_feedback"] = st.checkbox(
                    "Enable Quick Feedback Options",
                    value=st.session_state.get("enable_quick_feedback", True),
                    help="Show quick feedback buttons for common adjustments"
                )
                
                st.session_state["auto_accept_high_consistency"] = st.checkbox(
                    "Auto-accept High Consistency",
                    value=st.session_state.get("auto_accept_high_consistency", False),
                    help="Automatically accept images with consistency score > 0.9"
                )
            
            # Model and generation settings
            with st.expander("🤖 Model Settings"):
                # LLM settings
                st.write("**Language Model**")
                llm_temperature = st.slider(
                    "LLM Temperature",
                    min_value=0.0,
                    max_value=1.0,
                    value=st.session_state.get("llm_temperature", 0.7),
                    step=0.1,
                    help="Controls creativity of text responses"
                )
                st.session_state["llm_temperature"] = llm_temperature
                
                # Image generation settings
                st.write("**Image Generation**")
                image_steps = st.slider(
                    "Generation Steps",
                    min_value=10,
                    max_value=50,
                    value=st.session_state.get("image_steps", 20),
                    step=5,
                    help="More steps = higher quality but slower generation"
                )
                st.session_state["image_steps"] = image_steps
                
                guidance_scale = st.slider(
                    "Guidance Scale",
                    min_value=1.0,
                    max_value=20.0,
                    value=st.session_state.get("guidance_scale", 7.5),
                    step=0.5,
                    help="How closely to follow the prompt"
                )
                st.session_state["guidance_scale"] = guidance_scale
            
            # Debug information
            if st.checkbox("Show Debug Info", value=False):
                with st.expander("🐛 Debug Information", expanded=True):
                    st.write("**Session State Keys:**")
                    for key in sorted(st.session_state.keys()):
                        if key.startswith("study_chat") or key.startswith("pald"):
                            st.write(f"• {key}")
                    
                    st.write("**Current Session Data:**")
                    if session_data:
                        st.json({
                            "session_id": str(session_data.get("session_id", "")),
                            "message_count": len(session_data.get("messages", [])),
                            "feedback_round": session_data.get("feedback_round", 0),
                            "consistency_iterations": session_data.get("consistency_iterations", 0),
                            "processing_status": processing_status
                        })
                    else:
                        st.write("No session data available")


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


def render_study_participation_chat(pseudonym_id: UUID) -> None:
    """Render study participation chat interface."""
    chat_ui.render_study_participation_chat(pseudonym_id)

# === Task 9: PALD Response Helpers (append-only) =============================
# Pure helpers for banners/notices/summary lines + thin Streamlit wrapper.
# NOTE: We keep imports inside the functions where possible to avoid hard deps.

from typing import Optional, List

try:
    # Import UI contracts for typing and helper logic.
    from src.ui.contracts import PALDProcessingResponse, UiJobStatus
except Exception:  # pragma: no cover - typing fallback if contracts are missing at import time
    PALDProcessingResponse = object  # type: ignore
    class UiJobStatus:  # type: ignore
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"

def banner_text(status: "UiJobStatus") -> str:
    """Return a human-readable banner text for a given job status."""
    mapping = {
        getattr(UiJobStatus, "PENDING", "pending"): "⏳ Processing request…",
        getattr(UiJobStatus, "RUNNING", "running"): "🔧 Analysis in progress…",
        getattr(UiJobStatus, "COMPLETED", "completed"): "✅ Processing completed successfully",
        getattr(UiJobStatus, "FAILED", "failed"): "❌ Processing failed",
    }
    # Support Enum-like .value or plain strings
    key = getattr(status, "value", status)
    return mapping.get(key, f"Status: {key}")

def defer_text(response: "PALDProcessingResponse") -> Optional[str]:
    """Return a defer notice if heavy bias scan was deferred."""
    notice = getattr(response, "defer_notice", None)
    if not notice:
        return None
    if isinstance(notice, str):
        return notice
    return "⚠️ Heavy bias scan deferred. Results will be available later."

def error_text(response: "PALDProcessingResponse") -> Optional[str]:
    """Return user-facing error text (if present)."""
    msg = getattr(response, "error_message", None)
    return str(msg) if msg else None

def pald_summary_lines(response: "PALDProcessingResponse", max_items: int = 20) -> List[str]:
    """
    Build a concise summary list:
    1) The pald_diff_summary (truncated to max_items, with ellipsis)
    2) A few populated pald_light keys for quick glance
    """
    lines: List[str] = []

    # 1) diff
    diff = list(getattr(response, "pald_diff_summary", []) or [])
    if diff:
        if len(diff) > max_items:
            lines.extend(diff[:max_items])
            lines.append("…")
        else:
            lines.extend(diff)

    # 2) sample of pald_light
    pald = dict(getattr(response, "pald_light", {}) or {})
    shown = 0
    for k, v in pald.items():
        if shown >= 5:
            lines.append("…")
            break
        lines.append(f"pald:{k} -> {v}")
        shown += 1

    return lines

def render_pald_response(resp: "PALDProcessingResponse") -> None:
    """
    Thin Streamlit wrapper that uses the pure helpers above.
    Guarded import ensures tests can import helpers without Streamlit installed.
    """
    try:
        import streamlit as st  # guarded import
    except Exception:
        return

    st.info(banner_text(resp.status))
    dt = defer_text(resp)
    if dt:
        st.warning(dt)

    for line in pald_summary_lines(resp):
        st.write(f"- {line}")

    et = error_text(resp)
    if et:
        st.error(et)
# === End Task 9 append-only ===================================================
