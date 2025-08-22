"""
Onboarding UI components for GITTE system.
Provides comprehensive guided onboarding flow with automated navigation and state management.
"""

import logging
from typing import Any
from uuid import UUID
import time

import streamlit as st
try:
    # Streamlit >= 1.27 uses this exception to control reruns
    from streamlit.runtime.scriptrunner import RerunException
except Exception:
    RerunException = RuntimeError  # Fallback to a generic type if module path changes

from src.logic.onboarding import OnboardingStep, get_onboarding_logic
from src.services.consent_service import get_consent_service
from src.ui.chat_ui import render_chat_interface, render_embodiment_design_chat
from src.ui.consent_ui import render_onboarding_consent
from src.ui.image_ui import render_image_generation_interface
from src.ui.survey_ui import render_personalization_survey
from src.ui.tooltip_integration import form_submit_button

logger = logging.getLogger(__name__)


class OnboardingUI:
    """UI components for guided onboarding flow."""

    def __init__(self):
        self.onboarding_logic = get_onboarding_logic()
        self.consent_service = get_consent_service()

    def render_guided_onboarding_flow(self, user_id: UUID) -> bool:
        """Render the complete guided onboarding flow with anti-loop protection."""
        try:
            # Initialize flow control state
            flow_key = f"onboarding_flow_{user_id}"
            if flow_key not in st.session_state:
                st.session_state[flow_key] = {
                    "initialized": True,
                    "rerun_count": 0,
                    "last_rerun": 0,
                    "max_reruns": 5,  # Prevent infinite loops
                    "cooldown_time": 1  # Seconds between reruns
                }

            flow_state = st.session_state[flow_key]
            current_time = time.time()

            # Anti-loop protection
            if (flow_state["rerun_count"] >= flow_state["max_reruns"] and 
                current_time - flow_state["last_rerun"] < flow_state["cooldown_time"]):
                st.warning("⚠️ Flow rate limited. Please wait a moment before continuing.")
                return False

            # Get current onboarding state
            state = self.onboarding_logic.get_user_onboarding_state(user_id)

            # Check if onboarding is already complete
            if state["onboarding_complete"]:
                return True

            # Render onboarding header
            self._render_onboarding_header(state)

            # Render current step
            current_step = OnboardingStep(state["current_step"])
            step_result = self._render_current_step(user_id, current_step, state)

            # Handle step completion with controlled advancement
            if step_result:
                # Reset rerun count on successful step completion
                flow_state["rerun_count"] = 0
                return self._handle_controlled_step_completion(user_id, current_step, step_result)

            return False

        except RerunException:
            # Very important: allow Streamlit to perform a rerun without treating it as an error.
            raise
        except Exception as e:
            logger.error(f"Error rendering onboarding flow for user {user_id}: {e}")
            st.error("⚠️ Onboarding flow error. Please refresh the page.")
            return False

    def _handle_controlled_step_completion(self, user_id: UUID, current_step: OnboardingStep, step_data: dict) -> bool:
        """Handle step completion with controlled reruns."""
        flow_key = f"onboarding_flow_{user_id}"
        flow_state = st.session_state[flow_key]
        
        try:
            # Store step data
            if step_data.get("data"):
                self.onboarding_logic.collect_personalization_data(
                    user_id, f"step_{current_step.value}", step_data["data"]
                )

            # Advance to next step
            next_step = self.onboarding_logic.advance_to_next_step(
                user_id, current_step, step_data.get("data")
            )

            # Update flow control
            flow_state["rerun_count"] += 1
            flow_state["last_rerun"] = time.time()

            # Complete or advance
            if next_step == OnboardingStep.COMPLETE:
                st.session_state[f"onboarding_complete_{user_id}"] = True
                st.success("🎉 Onboarding completed successfully!")
                return True
            else:
                st.session_state[f"current_step_{user_id}"] = next_step.value
                
                # Controlled rerun with delay
                time.sleep(0.1)  # Brief pause to prevent race conditions
                st.rerun()

            return False

        except RerunException:
            # Let Streamlit rerun happen naturally.
            raise
        except Exception as e:
            logger.error(f"Error handling step completion: {e}")
            st.error("Error advancing to next step. Please try again.")
            return False


    def render_onboarding_summary(self, user_id: UUID) -> None:
        """
        Render onboarding progress summary.

        Args:
            user_id: User identifier
        """
        try:
            summary = self.onboarding_logic.get_onboarding_summary(user_id)

            st.subheader("📊 Your Onboarding Progress")

            # Progress metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Progress",
                    f"{summary['completion_progress']:.0%}",
                    f"{summary['completed_steps']}/{summary['total_steps']} steps",
                )

            with col2:
                st.metric("Current Step", summary["current_step"].replace("_", " ").title())

            with col3:
                st.metric(
                    "Consents Given",
                    f"{summary['consents_given']}/{summary['total_consent_types']}",
                )

            with col4:
                "green" if summary["onboarding_completed"] else "orange"
                st.metric(
                    "Status", "Complete" if summary["onboarding_completed"] else "In Progress"
                )

            # Detailed progress
            with st.expander("Detailed Progress", expanded=False):
                self._render_detailed_progress(summary)

        except Exception as e:
            logger.error(f"Error rendering onboarding summary for user {user_id}: {e}")
            st.error("Error loading onboarding summary.")

    def render_onboarding_restart(self, user_id: UUID) -> None:
        """
        Render onboarding restart interface (admin function).

        Args:
            user_id: User identifier
        """
        st.subheader("🔄 Restart Onboarding")

        st.warning(
            """
        **Warning:** Restarting onboarding will:
        - Reset your progress to the beginning
        - Clear your personalization data
        - Require you to go through all steps again
        
        This action cannot be undone.
        """
        )

        if st.button("Confirm Restart Onboarding", type="secondary"):
            try:
                self.onboarding_logic.reset_onboarding(user_id)

                # Clear session state
                onboarding_keys = [
                    "onboarding_complete",
                    "onboarding_step",
                    "survey_data",
                    "embodiment_characteristics",
                    "generated_avatar",
                ]

                for key in onboarding_keys:
                    if key in st.session_state:
                        del st.session_state[key]

                st.success("Onboarding has been restarted. Please refresh the page.")
                st.balloons()

            except Exception as e:
                logger.error(f"Error restarting onboarding for user {user_id}: {e}")
                st.error("Failed to restart onboarding. Please try again.")

    def _render_onboarding_header(self, state: dict[str, Any]) -> None:
        """Render onboarding header with progress."""
        st.title("Welcome to GITTE! 🤖")
        st.write("Let's set up your personalized learning assistant.")

        # Progress bar
        progress = state["progress"]
        st.progress(progress)

        # Step indicator
        current_step = state["current_step"]
        completed_steps = len(state["completed_steps"])
        total_steps = len(self.onboarding_logic.flow_steps)

        st.write(
            f"**Step {completed_steps + 1} of {total_steps}:** {current_step.replace('_', ' ').title()}"
        )

        # Progress indicators
        cols = st.columns(len(self.onboarding_logic.flow_steps))

        for i, step in enumerate(self.onboarding_logic.flow_steps):
            with cols[i]:
                if step in state["completed_steps"]:
                    st.success(f"✅ {step.value.replace('_', ' ').title()}")
                elif step.value == current_step:
                    st.info(f"🔄 {step.value.replace('_', ' ').title()}")
                else:
                    st.write(f"⏳ {step.value.replace('_', ' ').title()}")

    def _render_current_step(
        self, user_id: UUID, current_step: OnboardingStep, state: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Render the current onboarding step."""
        # Check if user can access this step
        can_access, reason = self.onboarding_logic.can_access_step(user_id, current_step)

        if not can_access:
            st.error(f"Cannot access this step: {reason}")
            return None

        # Render step-specific UI
        if current_step == OnboardingStep.CONSENT:
            return self._render_consent_step(user_id)
        elif current_step == OnboardingStep.SURVEY:
            return self._render_survey_step(user_id)
        elif current_step == OnboardingStep.INTRO_CHAT:
            return self._render_intro_chat_step(user_id)
        elif current_step == OnboardingStep.DESIGN:
            return self._render_design_step(user_id)
        elif current_step == OnboardingStep.CHAT:
            return self._render_chat_step(user_id)
        elif current_step == OnboardingStep.IMAGE_GENERATION:
            return self._render_image_step(user_id, state)
        elif current_step == OnboardingStep.FEEDBACK:
            return self._render_feedback_step(user_id)
        elif current_step == OnboardingStep.COMPLETE:
            return self._render_completion_step(user_id, state)

        return None

    def _render_consent_step(self, user_id: UUID) -> dict[str, Any] | None:
        """Render consent step."""
        st.subheader("🔒 Privacy & Consent")

        if render_onboarding_consent(user_id):
            return {"step": "consent", "completed": True}

        return None

    def _render_survey_step(self, user_id: UUID) -> dict[str, Any] | None:
        """Render survey step."""
        st.subheader("📋 Personalization Survey")

        survey_data = render_personalization_survey(user_id)

        if survey_data:
            return {"step": "survey", "completed": True, "data": survey_data}

        return None

    def _render_design_step(self, user_id: UUID) -> dict[str, Any] | None:
        """Render embodiment design step."""
        st.subheader("🎨 Design Your Embodiment")

        embodiment_characteristics = render_embodiment_design_chat(user_id)

        if embodiment_characteristics:
            return {
                "step": "design",
                "completed": True,
                "data": {"embodiment_characteristics": embodiment_characteristics},
            }

        return None

    def _render_chat_step(self, user_id: UUID) -> dict[str, Any] | None:
        """Render chat introduction step."""
        st.subheader("💬 Meet Your Assistant")
        st.write("Have a brief conversation with your personalized learning assistant!")

        # Render chat interface
        render_chat_interface(user_id)

        # Auto-advance after some interaction
        chat_messages = st.session_state.get("chat_messages", [])
        user_messages = [msg for msg in chat_messages if msg["role"] == "user"]

        if len(user_messages) >= 2:  # User has sent at least 2 messages
            st.success("Great! You've had a good conversation with your assistant.")

            if st.button("Continue to Image Generation", type="primary"):
                return {
                    "step": "chat",
                    "completed": True,
                    "data": {"chat_interaction_count": len(user_messages)},
                }
        else:
            st.info(f"Send a few messages to continue. ({len(user_messages)}/2 messages sent)")

        return None

    def _render_image_step(self, user_id: UUID, state: dict[str, Any]) -> dict[str, Any] | None:
        """Render image generation step."""
        st.subheader("🖼️ Create Your Avatar")
        st.write("Generate a visual representation of your learning assistant!")

        # Get embodiment data from previous steps
        embodiment_data = state.get("personalization_data", {}).get(
            "embodiment_characteristics", {}
        )

        # Render image generation interface
        generated_image = render_image_generation_interface(user_id, embodiment_data)

        if generated_image:
            st.success("Avatar generated successfully!")

            if st.button("Continue to Feedback", type="primary"):
                return {
                    "step": "image_generation",
                    "completed": True,
                    "data": {"generated_image_path": generated_image},
                }

        # Option to skip image generation
        if st.button("Skip Image Generation"):
            return {"step": "image_generation", "completed": True, "data": {"skipped": True}}

        return None

    def _render_feedback_step(self, user_id: UUID) -> dict[str, Any] | None:
        """Render feedback collection step."""
        st.subheader("📝 Quick Feedback")
        st.write("Help us improve your onboarding experience!")

        with st.form("onboarding_feedback"):
            # Experience rating
            experience_rating = st.select_slider(
                "How was your onboarding experience?",
                options=["Poor", "Fair", "Good", "Very Good", "Excellent"],
                value="Good",
            )

            # Specific feedback
            feedback_areas = st.multiselect(
                "Which parts worked well? (Select all that apply)",
                options=[
                    "Consent process was clear",
                    "Survey was comprehensive",
                    "Embodiment design was fun",
                    "Chat interaction was helpful",
                    "Image generation was impressive",
                    "Overall flow was smooth",
                ],
            )

            # Improvement suggestions
            improvements = st.text_area(
                "Any suggestions for improvement?",
                placeholder="Optional: Tell us how we can make onboarding better...",
                height=100,
            )

            # Submit feedback
            col1, col2 = st.columns(2)

            with col1:
                feedback_submitted = form_submit_button("Submit Feedback", type="primary")

            with col2:
                skip_feedback = form_submit_button("Skip Feedback")

        if feedback_submitted or skip_feedback:
            feedback_data = {
                "experience_rating": experience_rating,
                "feedback_areas": feedback_areas,
                "improvements": improvements,
                "submitted": feedback_submitted,
                "skipped": skip_feedback,
            }

            return {"step": "feedback", "completed": True, "data": feedback_data}

        return None

    def _render_completion_step(
        self, user_id: UUID, state: dict[str, Any]
    ) -> dict[str, Any] | None:
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
        ✅ Provided valuable feedback
        
        You're now ready to start your personalized learning journey!
        """
        )

        # Show personalization summary
        self._render_personalization_summary(state)

        if st.button("Start Using GITTE", type="primary"):
            return {"step": "complete", "completed": True, "data": {"onboarding_finished": True}}

        return None

    def _render_personalization_summary(self, state: dict[str, Any]) -> None:
        """Render summary of collected personalization data."""
        with st.expander("Your Personalization Summary", expanded=True):
            personalization = state.get("personalization_data", {})

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Learning Preferences")
                learning_prefs = personalization.get("learning_preferences", {})
                st.write(f"**Style:** {learning_prefs.get('learning_style', 'Not specified')}")
                st.write(
                    f"**Difficulty:** {learning_prefs.get('difficulty_preference', 'Not specified')}"
                )
                st.write(f"**Pace:** {learning_prefs.get('pace_preference', 'Not specified')}")
                st.write(
                    f"**Communication:** {learning_prefs.get('communication_style', 'Not specified')}"
                )

            with col2:
                st.subheader("Embodiment Design")
                embodiment = personalization.get("embodiment_characteristics", {})
                st.write(f"**Appearance:** {embodiment.get('appearance_style', 'Not specified')}")
                st.write(f"**Personality:** {embodiment.get('personality', 'Not specified')}")
                st.write(f"**Age Range:** {embodiment.get('age_range', 'Not specified')}")
                st.write(f"**Style:** {embodiment.get('communication_style', 'Not specified')}")

    def _render_detailed_progress(self, summary: dict[str, Any]) -> None:
        """Render detailed progress information."""
        st.write("**Learning Preferences:**")
        learning_prefs = summary.get("learning_preferences", {})
        if learning_prefs:
            for key, value in learning_prefs.items():
                st.write(f"- {key.replace('_', ' ').title()}: {value}")
        else:
            st.write("- Not completed yet")

        st.write("**Embodiment Design:**")
        embodiment = summary.get("embodiment_design", {})
        if embodiment:
            for key, value in embodiment.items():
                st.write(f"- {key.replace('_', ' ').title()}: {value}")
        else:
            st.write("- Not completed yet")

        st.write("**Survey Status:**")
        st.write(f"- Completed: {'Yes' if summary['survey_completed'] else 'No'}")

        st.write("**Consent Status:**")
        st.write(f"- Consents given: {summary['consents_given']}/{summary['total_consent_types']}")


    def _render_intro_chat_step(self, user_id: UUID) -> dict[str, Any] | None:
        """Render introductory chat step - first interaction with the AI assistant."""
        st.subheader("👋 Meet Your AI Learning Assistant!")
        
        # Engaging introduction
        st.markdown("""
        🎉 **Congratulations!** You've completed your preferences survey. 
        
        Now it's time to meet your personalized AI learning assistant! This is a brief introduction 
        where you can have your first conversation and get a feel for how your assistant will help you learn.
        """)
        
        # Initialize intro chat session
        intro_chat_key = f"intro_chat_{user_id}"
        if intro_chat_key not in st.session_state:
            st.session_state[intro_chat_key] = {
                "messages": [],
                "interaction_count": 0,
                "started": False
            }
        
        intro_state = st.session_state[intro_chat_key]
        
        # Welcome message from AI (only show once)
        if not intro_state["started"]:
            welcome_message = self._get_intro_welcome_message(user_id)
            intro_state["messages"].append({
                "role": "assistant",
                "content": welcome_message,
                "timestamp": time.time()
            })
            intro_state["started"] = True
        
        # Display chat messages
        st.markdown("### 💬 Your Conversation")
        
        # Create chat container
        chat_container = st.container()
        with chat_container:
            for message in intro_state["messages"]:
                if message["role"] == "user":
                    with st.chat_message("user", avatar="👤"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(message["content"])
        
        # Chat input
        user_input = st.chat_input(
            "Type your message here... Ask anything or just say hello!", 
            key=f"intro_chat_input_{user_id}"
        )
        
        if user_input:
            # Add user message
            intro_state["messages"].append({
                "role": "user",
                "content": user_input,
                "timestamp": time.time()
            })
            intro_state["interaction_count"] += 1
            
            # Generate AI response
            ai_response = self._generate_intro_chat_response(user_id, user_input, intro_state["interaction_count"])
            
            # Add AI response
            intro_state["messages"].append({
                "role": "assistant", 
                "content": ai_response,
                "timestamp": time.time()
            })
            
            st.rerun()
        
        # Progress indicator
        messages_needed = 3
        user_messages = len([msg for msg in intro_state["messages"] if msg["role"] == "user"])
        
        # Progress bar
        progress = min(user_messages / messages_needed, 1.0)
        st.progress(progress, text=f"Chat Progress: {user_messages}/{messages_needed} messages")
        
        # Completion logic
        if user_messages >= messages_needed:
            st.success("🎉 Great conversation! You're getting to know your AI assistant.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Continue to Embodiment Design", type="primary", key=f"continue_intro_{user_id}"):
                    return {
                        "step": "intro_chat",
                        "completed": True,
                        "data": {
                            "interaction_count": intro_state["interaction_count"],
                            "conversation_length": len(intro_state["messages"]),
                            "intro_completed": True
                        }
                    }
            
            with col2:
                if st.button("Have More Conversation", key=f"more_chat_{user_id}"):
                    st.info("Feel free to continue chatting! Click 'Continue' when you're ready to move on.")
        
        else:
            # Encourage more interaction
            remaining = messages_needed - user_messages
            st.info(f"💡 **Next Step:** Send {remaining} more message{'s' if remaining > 1 else ''} to continue. "
                   f"Try asking about learning topics, your preferences, or just have a friendly chat!")
            
            # Helpful suggestions
            with st.expander("💭 Need conversation ideas?", expanded=False):
                suggestions = [
                    "Hi! How can you help me learn?",
                    "What subjects are you good at teaching?",
                    "How will you adapt to my learning style?",
                    "Can you tell me about yourself?",
                    "What makes you different from other AI assistants?",
                    "How do you plan to help me with my studies?"
                ]
                
                st.markdown("**Try asking:**")
                for suggestion in suggestions:
                    if st.button(f"💬 {suggestion}", key=f"suggestion_{hash(suggestion)}_{user_id}"):
                        # Simulate user input
                        intro_state["messages"].append({
                            "role": "user",
                            "content": suggestion,
                            "timestamp": time.time()
                        })
                        intro_state["interaction_count"] += 1
                        
                        # Generate response
                        ai_response = self._generate_intro_chat_response(user_id, suggestion, intro_state["interaction_count"])
                        intro_state["messages"].append({
                            "role": "assistant",
                            "content": ai_response, 
                            "timestamp": time.time()
                        })
                        
                        st.rerun()
        
        return None
    
    def _get_intro_welcome_message(self, user_id: UUID) -> str:
        """Get personalized welcome message for intro chat."""
        return """
        Hello there! 👋 I'm your personalized AI learning assistant, and I'm excited to meet you!
        
        Based on your survey responses, I'm already learning about your preferences and how I can best help you. 
        I'm here to make learning engaging, effective, and tailored just for you.
        
        This is our first conversation together! Feel free to:
        • Ask me questions about how I work
        • Tell me about topics you'd like to learn
        • Ask about my capabilities
        • Or just have a friendly chat to get to know each other
        
        What would you like to know or talk about? 😊
        """
    
    def _generate_intro_chat_response(self, user_id: UUID, user_input: str, interaction_count: int) -> str:
        """Generate contextual response for intro chat."""
        # Simple response generation based on input patterns
        user_input_lower = user_input.lower()
        
        # Greeting responses
        if any(word in user_input_lower for word in ["hello", "hi", "hey", "greetings"]):
            responses = [
                "Hello! It's wonderful to meet you! I'm really looking forward to helping you learn and grow. What interests you most about learning?",
                "Hi there! 😊 I'm so excited to be your learning companion. What would you like to explore together?",
                "Hey! Great to meet you! I'm here to make learning fun and effective for you. What subjects fascinate you?"
            ]
            return responses[interaction_count % len(responses)]
        
        # Learning-related questions
        elif any(word in user_input_lower for word in ["learn", "teach", "study", "help"]):
            return """
            I'm designed to be your personalized learning partner! Here's how I can help:
            
            🎯 **Adaptive Teaching**: I adjust my explanations based on your learning style
            📚 **Subject Expertise**: I can help with various topics and subjects
            🤔 **Interactive Learning**: We'll have conversations, not just Q&A
            💡 **Personalized Approach**: Everything is tailored to your preferences
            
            What subject or topic would you like to start exploring?
            """
        
        # Capabilities questions
        elif any(word in user_input_lower for word in ["can you", "what can", "abilities", "capabilities"]):
            return """
            I have many capabilities to support your learning journey:
            
            ✨ **Explain Complex Topics**: Break down difficult concepts into understandable parts
            🔍 **Answer Questions**: Provide detailed, accurate answers
            📖 **Create Learning Materials**: Generate examples, exercises, and summaries
            🎨 **Visual Learning**: Help create mental models and visual explanations
            🗣️ **Conversational Learning**: Learn through natural dialogue
            
            I'm also constantly learning about your preferences to serve you better!
            """
        
        # Personal questions about the AI
        elif any(word in user_input_lower for word in ["you", "yourself", "about you", "who are"]):
            return """
            I'm your personalized AI learning assistant! Here's what makes me special:
            
            🤖 **Adaptive**: I learn from our interactions to better serve you
            🎯 **Focused**: My primary goal is helping YOU learn effectively
            💭 **Thoughtful**: I consider your learning style, pace, and preferences
            🌟 **Encouraging**: I'm here to support and motivate you
            
            I'm not just a generic AI - I'm becoming YOUR learning companion, shaped by your needs and preferences!
            """
        
        # Subject-specific questions
        elif any(word in user_input_lower for word in ["math", "science", "history", "language", "programming"]):
            return f"""
            Great question about {user_input}! I can definitely help with that subject.
            
            I'll adapt my teaching style to match your preferences from the survey. Whether you prefer:
            • Visual explanations with diagrams and examples
            • Step-by-step logical breakdowns
            • Interactive problem-solving
            • Real-world applications
            
            I'll make sure the content is at the right difficulty level for you and presented in a way that clicks with your learning style!
            """
        
        # Default encouraging response
        else:
            responses = [
                "That's an interesting point! I love how curious you are. Learning is all about asking questions and exploring ideas together.",
                "I appreciate you sharing that with me! It helps me understand how to better support your learning journey.",
                "Fascinating! Your perspective helps me learn how to be a better learning assistant for you. What else would you like to explore?",
                "Thank you for that insight! I'm getting to know your communication style, which will help me tailor our future interactions."
            ]
            return responses[interaction_count % len(responses)]


    def _handle_step_completion(self, user_id: UUID, current_step: OnboardingStep, step_data: dict[str, Any]) -> bool:
        try:
            # Konsistente Session State Initialisierung
            if "onboarding_state" not in st.session_state:
                st.session_state.onboarding_state = {
                    "complete": False,
                    "current_step": current_step.value,
                    "last_update": time.time()
                }
            
            # Store step data if provided
            if step_data.get("data"):
                self.onboarding_logic.collect_personalization_data(
                    user_id, f"step_{current_step.value}", step_data["data"]
                )

            # Advance to next step
            next_step = self.onboarding_logic.advance_to_next_step(
                user_id, current_step, step_data.get("data")
            )

            # Update session state atomically
            if next_step == OnboardingStep.COMPLETE:
                st.session_state.onboarding_state["complete"] = True
                st.session_state.onboarding_state["completion_time"] = time.time()
                return True
            else:
                st.session_state.onboarding_state["current_step"] = next_step.value
                st.session_state.onboarding_state["last_update"] = time.time()
                # Only rerun if step actually changed
                if st.session_state.onboarding_state.get("previous_step") != next_step.value:
                    st.session_state.onboarding_state["previous_step"] = next_step.value
                    st.rerun()

            return False

        except Exception as e:
            logger.error(f"Error handling step completion for user {user_id}: {e}")
            st.error("Error advancing to next step. Please try again.")
            return False

# Global onboarding UI instance
onboarding_ui = OnboardingUI()


# Convenience functions
def render_guided_onboarding_flow(user_id: UUID) -> bool:
    """Render guided onboarding flow."""
    return onboarding_ui.render_guided_onboarding_flow(user_id)


def render_onboarding_summary(user_id: UUID) -> None:
    """Render onboarding summary."""
    onboarding_ui.render_onboarding_summary(user_id)


def render_onboarding_restart(user_id: UUID) -> None:
    """Render onboarding restart interface."""
    onboarding_ui.render_onboarding_restart(user_id)
