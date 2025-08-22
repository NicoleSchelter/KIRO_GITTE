#!/usr/bin/env python3
"""
Script to add the missing intro_chat step to onboarding UI.
"""

def add_intro_chat_step():
    """Add the missing intro_chat step implementation."""
    file_path = "src/ui/onboarding_ui.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Add the case for INTRO_CHAT in _render_current_step
    old_case = '''        elif current_step == OnboardingStep.SURVEY:
            return self._render_survey_step(user_id)
        elif current_step == OnboardingStep.DESIGN:'''
    
    new_case = '''        elif current_step == OnboardingStep.SURVEY:
            return self._render_survey_step(user_id)
        elif current_step == OnboardingStep.INTRO_CHAT:
            return self._render_intro_chat_step(user_id)
        elif current_step == OnboardingStep.DESIGN:'''
    
    content = content.replace(old_case, new_case)
    
    # 2. Add the method implementations before the last method
    method_code = '''
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

'''
    
    # Insert the methods before the last method in the class
    insertion_point = "    def _handle_step_completion(self, user_id: UUID, current_step: OnboardingStep, step_data: dict[str, Any]) -> bool:"
    content = content.replace(insertion_point, method_code + "\n" + insertion_point)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Added intro_chat step implementation to {file_path}")

if __name__ == "__main__":
    add_intro_chat_step()
    print("Intro chat step added successfully!")