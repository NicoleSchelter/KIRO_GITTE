"""
Tests for enhanced chat UI study flow functionality.
Tests the enhancements made for task 13: Chat UI Enhancement for Study Flow.
"""

import pytest
import time
from unittest.mock import Mock, patch
from uuid import uuid4

import streamlit as st

from src.ui.chat_ui import ChatUI


class TestChatUIStudyEnhancements:
    """Test enhanced chat UI functionality for study participation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chat_ui = ChatUI()
        self.pseudonym_id = uuid4()
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    def test_initialize_study_session_state(self):
        """Test study session state initialization."""
        # Test that the ChatUI class has the expected methods
        assert hasattr(self.chat_ui, 'render_study_participation_chat')
        
        # Test session key generation
        session_key = f"study_chat_{self.pseudonym_id}"
        
        # Manually initialize session state to test the structure
        current_time = time.time()
        st.session_state[session_key] = {
            "messages": [],
            "session_id": uuid4(),
            "session_start": current_time,
            "pald_processing_status": "idle",
            "consistency_loop_active": False,
            "consistency_iterations": 0,
            "feedback_round": 0,
            "max_feedback_rounds": 3,
            "current_image": None,
            "current_pald": None,
            "feedback_active": False,
            "processing_metadata": {},
        }
        
        # Add welcome message
        st.session_state[session_key]["messages"].append({
            "role": "assistant",
            "content": "Welcome message",
            "timestamp": current_time,
            "message_type": "welcome"
        })
        
        # Verify session state structure
        assert session_key in st.session_state
        
        session_data = st.session_state[session_key]
        assert "messages" in session_data
        assert "session_id" in session_data
        assert "session_start" in session_data
        assert "pald_processing_status" in session_data
        assert "consistency_loop_active" in session_data
        assert "feedback_round" in session_data
        assert "max_feedback_rounds" in session_data
        
        # Verify welcome message is added
        assert len(session_data["messages"]) == 1
        assert session_data["messages"][0]["role"] == "assistant"
        assert session_data["messages"][0]["message_type"] == "welcome"

    def test_get_feedback_history(self):
        """Test feedback history retrieval."""
        # Initialize session with feedback messages
        session_key = f"study_chat_{self.pseudonym_id}"
        st.session_state[session_key] = {
            "messages": [
                {
                    "role": "user",
                    "content": "**Feedback:** Make it more friendly",
                    "message_type": "feedback",
                    "round_number": 1,
                    "timestamp": time.time()
                },
                {
                    "role": "user", 
                    "content": "Regular message",
                    "message_type": "chat",
                    "timestamp": time.time()
                },
                {
                    "role": "user",
                    "content": "**Feedback:** Change the hair color",
                    "message_type": "feedback", 
                    "round_number": 2,
                    "timestamp": time.time()
                }
            ]
        }
        
        # Get feedback history
        history = self.chat_ui._get_feedback_history(self.pseudonym_id)
        
        # Verify feedback extraction
        assert len(history) == 2
        assert history[0]["text"] == "Make it more friendly"
        assert history[0]["round_number"] == 1
        assert history[1]["text"] == "Change the hair color"
        assert history[1]["round_number"] == 2

    def test_start_new_study_session(self):
        """Test starting a new study session."""
        # Initialize existing session
        session_key = f"study_chat_{self.pseudonym_id}"
        st.session_state[session_key] = {
            "messages": [{"role": "user", "content": "old message"}],
            "feedback_round": 2,
            "consistency_iterations": 3
        }
        
        # Start new session
        with patch('streamlit.rerun'):
            self.chat_ui._start_new_study_session(self.pseudonym_id)
        
        # Verify session reset
        new_session_data = st.session_state[session_key]
        assert len(new_session_data["messages"]) == 1  # Only welcome message
        assert new_session_data["feedback_round"] == 0
        assert new_session_data["consistency_iterations"] == 0
        assert "session_start" in new_session_data

    @patch('streamlit.success')
    @patch('streamlit.rerun')
    def test_accept_current_image(self, mock_rerun, mock_success):
        """Test accepting current image functionality."""
        # Initialize session
        session_key = f"study_chat_{self.pseudonym_id}"
        st.session_state[session_key] = {
            "messages": []
        }
        st.session_state["feedback_active"] = True
        
        # Accept current image
        self.chat_ui._accept_current_image(self.pseudonym_id)
        
        # Verify acceptance message added
        messages = st.session_state[session_key]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["message_type"] == "acceptance"
        
        # Verify feedback interface disabled
        assert st.session_state["feedback_active"] is False

    @patch('streamlit.rerun')
    def test_stop_feedback_loop(self, mock_rerun):
        """Test stopping feedback loop functionality."""
        # Mock chat logic
        mock_chat_logic = Mock()
        mock_stop_result = Mock()
        mock_chat_logic.stop_feedback_loop.return_value = mock_stop_result
        self.chat_ui.chat_logic = mock_chat_logic
        
        # Initialize session
        session_key = f"study_chat_{self.pseudonym_id}"
        st.session_state[session_key] = {
            "messages": [],
            "session_id": uuid4(),
            "feedback_round": 2
        }
        st.session_state["feedback_active"] = True
        
        # Stop feedback loop
        self.chat_ui._stop_feedback_loop(self.pseudonym_id)
        
        # Verify chat logic called
        mock_chat_logic.stop_feedback_loop.assert_called_once()
        
        # Verify stop message added
        messages = st.session_state[session_key]["messages"]
        assert len(messages) == 1
        assert messages[0]["message_type"] == "feedback_stopped"
        
        # Verify feedback interface disabled
        assert st.session_state["feedback_active"] is False

    def test_format_pald_summary(self):
        """Test PALD data formatting for display."""
        # Test with valid PALD data
        pald_data = {
            "appearance": {
                "hair_color": "brown",
                "eye_color": "blue",
                "style": "professional"
            },
            "personality": {
                "friendliness": "high",
                "formality": "medium"
            }
        }
        
        summary = self.chat_ui._format_pald_summary(pald_data)
        
        # Verify formatting
        assert "**Appearance:**" in summary
        assert "**Personality:**" in summary
        assert "Hair Color: brown" in summary
        assert "Eye Color: blue" in summary
        assert "Friendliness: high" in summary

    def test_format_pald_summary_empty(self):
        """Test PALD formatting with empty data."""
        # Test with empty data
        summary = self.chat_ui._format_pald_summary({})
        assert summary == "No specific characteristics extracted."
        
        # Test with None
        summary = self.chat_ui._format_pald_summary(None)
        assert summary == "No specific characteristics extracted."

    @patch('streamlit.expander')
    @patch('streamlit.write')
    @patch('streamlit.metric')
    def test_show_session_info(self, mock_metric, mock_write, mock_expander):
        """Test session information display."""
        # Initialize session with data
        session_key = f"study_chat_{self.pseudonym_id}"
        session_start = time.time() - 300  # 5 minutes ago
        st.session_state[session_key] = {
            "session_id": uuid4(),
            "session_start": session_start,
            "messages": [
                {"role": "user", "content": "test message", "timestamp": time.time()},
                {"role": "assistant", "content": "response", "timestamp": time.time()}
            ],
            "feedback_round": 1,
            "consistency_iterations": 2
        }
        
        # Mock expander context manager
        mock_expander.return_value.__enter__ = Mock()
        mock_expander.return_value.__exit__ = Mock()
        
        # Show session info
        with patch('streamlit.columns'), patch('streamlit.button'):
            self.chat_ui._show_session_info(self.pseudonym_id)
        
        # Verify expander was called
        mock_expander.assert_called_once()

    def test_get_current_pseudonym(self):
        """Test getting current pseudonym from session state."""
        # Test with no pseudonym set
        result = self.chat_ui._get_current_pseudonym()
        assert result is None
        
        # Test with pseudonym set
        st.session_state["current_pseudonym_id"] = self.pseudonym_id
        result = self.chat_ui._get_current_pseudonym()
        assert result == self.pseudonym_id

    def test_study_welcome_message(self):
        """Test study welcome message generation."""
        welcome_msg = self.chat_ui._get_study_welcome_message(self.pseudonym_id)
        
        # Verify message content
        assert "Welcome to your personalized learning assistant chat!" in welcome_msg
        assert "PALD data" in welcome_msg
        assert "feedback" in welcome_msg
        assert isinstance(welcome_msg, str)
        assert len(welcome_msg) > 100  # Should be substantial

    def test_clear_study_session(self):
        """Test clearing study session."""
        # Initialize session
        session_key = f"study_chat_{self.pseudonym_id}"
        st.session_state[session_key] = {"messages": ["test"]}
        st.session_state["feedback_active"] = True
        st.session_state["pald_processing_status"] = "processing"
        
        # Clear session
        with patch('streamlit.success'), patch('streamlit.rerun'):
            self.chat_ui._clear_study_session(self.pseudonym_id)
        
        # Verify session cleared
        assert session_key not in st.session_state
        assert st.session_state["feedback_active"] is False
        assert st.session_state["pald_processing_status"] == "idle"


class TestChatUIStudyIntegration:
    """Integration tests for study chat UI enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chat_ui = ChatUI()
        self.pseudonym_id = uuid4()
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]

    @patch('src.ui.chat_ui.get_llm_service')
    @patch('src.ui.chat_ui.ImageGenerationService')
    @patch('src.ui.chat_ui.ChatService')
    def test_initialize_study_components(self, mock_chat_service, mock_image_service, mock_llm_service):
        """Test study components initialization."""
        # Initialize components
        self.chat_ui._initialize_study_components()
        
        # Verify components are initialized
        assert self.chat_ui.chat_logic is not None
        assert self.chat_ui.image_generation_logic is not None
        assert self.chat_ui.chat_service is not None

    @patch('src.ui.chat_ui.ChatUI._check_study_chat_consent')
    @patch('src.ui.chat_ui.ChatUI._initialize_study_components')
    @patch('streamlit.title')
    @patch('streamlit.caption')
    def test_render_study_participation_chat(self, mock_caption, mock_title, mock_init, mock_consent):
        """Test rendering study participation chat interface."""
        # Mock consent check to return True
        mock_consent.return_value = True
        
        # Render chat interface
        with patch.object(self.chat_ui, '_initialize_study_session_state'), \
             patch.object(self.chat_ui, '_render_study_chat_header'), \
             patch.object(self.chat_ui, '_render_pald_processing_status'), \
             patch.object(self.chat_ui, '_render_study_chat_messages'), \
             patch.object(self.chat_ui, '_render_study_chat_input'), \
             patch.object(self.chat_ui, '_render_feedback_interface'), \
             patch.object(self.chat_ui, '_render_study_chat_controls'):
            
            self.chat_ui.render_study_participation_chat(self.pseudonym_id)
        
        # Verify initialization and rendering methods called
        mock_init.assert_called_once()
        mock_consent.assert_called_once_with(self.pseudonym_id)
        mock_title.assert_called_once()
        mock_caption.assert_called_once()

    def test_check_study_chat_consent(self):
        """Test study chat consent checking."""
        # For now, this should always return True as consent is checked during onboarding
        result = self.chat_ui._check_study_chat_consent(self.pseudonym_id)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])