"""
Unit tests for Chat UI Study Participation Integration.
Tests the enhanced chat UI components for study participation flow.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4, UUID
import streamlit as st
from datetime import datetime

from src.ui.chat_ui import ChatUI
from src.logic.chat_logic import ChatProcessingResult, FeedbackProcessingResult, PALDExtractionResult
from src.logic.image_generation_logic import ImageGenerationResult, ImageDescriptionResult
from src.data.models import ChatMessageType, StudyPALDType


class TestChatUIStudyIntegration:
    """Test suite for chat UI study participation integration."""

    @pytest.fixture
    def chat_ui(self):
        """Create ChatUI instance for testing."""
        return ChatUI()

    @pytest.fixture
    def mock_pseudonym_id(self):
        """Create mock pseudonym ID."""
        return uuid4()

    @pytest.fixture
    def mock_session_state(self):
        """Mock Streamlit session state."""
        with patch.object(st, 'session_state', {}) as mock_state:
            yield mock_state

    @pytest.fixture
    def mock_components(self):
        """Mock study participation components."""
        with patch('src.ui.chat_ui.get_llm_service') as mock_llm_service, \
             patch('src.ui.chat_ui.get_session') as mock_db_session, \
             patch('src.ui.chat_ui.ChatLogic') as mock_chat_logic, \
             patch('src.ui.chat_ui.ImageGenerationLogic') as mock_image_logic, \
             patch('src.ui.chat_ui.ChatService') as mock_chat_service:
            
            yield {
                'llm_service': mock_llm_service,
                'db_session': mock_db_session,
                'chat_logic': mock_chat_logic,
                'image_logic': mock_image_logic,
                'chat_service': mock_chat_service
            }

    def test_initialize_study_components(self, chat_ui, mock_components):
        """Test initialization of study participation components."""
        # Test component initialization
        chat_ui._initialize_study_components()
        
        # Verify components are initialized
        assert chat_ui.chat_logic is not None
        assert chat_ui.image_generation_logic is not None
        assert chat_ui.chat_service is not None
        
        # Verify services are called
        mock_components['llm_service'].assert_called_once()

    def test_initialize_study_session_state(self, chat_ui, mock_pseudonym_id, mock_session_state):
        """Test initialization of study session state."""
        with patch('src.ui.chat_ui.config') as mock_config:
            mock_config.pald_boundary.max_feedback_rounds = 3
            
            chat_ui._initialize_study_session_state(mock_pseudonym_id)
            
            session_key = f"study_chat_{mock_pseudonym_id}"
            assert session_key in st.session_state
            
            session_data = st.session_state[session_key]
            assert session_data['messages'] is not None
            assert session_data['session_id'] is not None
            assert session_data['pald_processing_status'] == 'idle'
            assert session_data['feedback_round'] == 0
            assert session_data['max_feedback_rounds'] == 3
            assert len(session_data['messages']) == 1  # Welcome message

    def test_get_study_welcome_message(self, chat_ui, mock_pseudonym_id):
        """Test generation of study welcome message."""
        welcome_msg = chat_ui._get_study_welcome_message(mock_pseudonym_id)
        
        assert isinstance(welcome_msg, str)
        assert len(welcome_msg) > 0
        assert "learning assistant" in welcome_msg.lower()
        assert "pald" in welcome_msg.lower()

    @patch('streamlit.spinner')
    @patch('streamlit.rerun')
    def test_process_study_chat_input_success(self, mock_rerun, mock_spinner, chat_ui, mock_pseudonym_id, mock_session_state, mock_components):
        """Test successful processing of study chat input."""
        # Setup
        chat_ui._initialize_study_components()
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        
        # Mock processing result
        mock_processing_result = ChatProcessingResult(
            message_id=uuid4(),
            pald_extracted=True,
            pald_data={"global_design_level": {"appearance": "friendly"}},
            consistency_check_performed=False,
            consistency_result=None,
            requires_regeneration=False,
            processing_metadata={"processing_time_ms": 100}
        )
        
        chat_ui.chat_logic.process_chat_input.return_value = mock_processing_result
        
        # Test input processing
        user_input = "I want a friendly learning assistant"
        
        with patch('src.ui.chat_ui.config') as mock_config:
            mock_config.feature_flags.enable_consistency_check = True
            
            chat_ui._process_study_chat_input(mock_pseudonym_id, user_input)
        
        # Verify chat logic was called
        chat_ui.chat_logic.process_chat_input.assert_called_once()
        
        # Verify message was added to session
        session_key = f"study_chat_{mock_pseudonym_id}"
        messages = st.session_state[session_key]['messages']
        
        # Should have welcome message + user message + assistant response
        assert len(messages) >= 2
        
        # Check user message was added
        user_messages = [msg for msg in messages if msg['role'] == 'user']
        assert len(user_messages) == 1
        assert user_messages[0]['content'] == user_input

    @patch('streamlit.rerun')
    def test_process_study_chat_input_error(self, mock_rerun, chat_ui, mock_pseudonym_id, mock_session_state, mock_components):
        """Test error handling in study chat input processing."""
        # Setup
        chat_ui._initialize_study_components()
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        
        # Mock error in processing
        chat_ui.chat_logic.process_chat_input.side_effect = Exception("Processing error")
        
        # Test input processing with error
        user_input = "Test input"
        chat_ui._process_study_chat_input(mock_pseudonym_id, user_input)
        
        # Verify error status is set
        assert st.session_state.get("pald_processing_status") == "error"
        
        # Verify error message was added
        session_key = f"study_chat_{mock_pseudonym_id}"
        messages = st.session_state[session_key]['messages']
        
        error_messages = [msg for msg in messages if msg.get('message_type') == 'error']
        assert len(error_messages) == 1

    def test_generate_assistant_response_with_pald(self, chat_ui, mock_pseudonym_id, mock_session_state, mock_components):
        """Test assistant response generation with PALD extraction."""
        # Setup
        chat_ui._initialize_study_components()
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        
        # Mock processing result with PALD
        mock_processing_result = Mock()
        mock_processing_result.pald_extracted = True
        mock_processing_result.pald_data = {
            "global_design_level": {"appearance": "friendly", "style": "casual"}
        }
        
        response = chat_ui._generate_assistant_response(
            mock_pseudonym_id, "Test input", mock_processing_result
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
        assert "characteristics" in response.lower()

    def test_generate_assistant_response_without_pald(self, chat_ui, mock_pseudonym_id, mock_session_state, mock_components):
        """Test assistant response generation without PALD extraction."""
        # Setup
        chat_ui._initialize_study_components()
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        
        # Mock processing result without PALD
        mock_processing_result = Mock()
        mock_processing_result.pald_extracted = False
        mock_processing_result.pald_data = None
        
        response = chat_ui._generate_assistant_response(
            mock_pseudonym_id, "Test input", mock_processing_result
        )
        
        assert isinstance(response, str)
        assert len(response) > 0

    def test_format_pald_summary(self, chat_ui):
        """Test PALD data formatting for display."""
        # Test with valid PALD data
        pald_data = {
            "global_design_level": {
                "appearance": "friendly",
                "style": "casual"
            },
            "middle_design_level": {
                "clothing": "professional attire"
            }
        }
        
        summary = chat_ui._format_pald_summary(pald_data)
        
        assert isinstance(summary, str)
        assert "Global Design Level" in summary
        assert "Appearance: friendly" in summary
        assert "Style: casual" in summary
        assert "Middle Design Level" in summary
        assert "Clothing: professional attire" in summary

    def test_format_pald_summary_empty(self, chat_ui):
        """Test PALD formatting with empty data."""
        # Test with empty data
        summary = chat_ui._format_pald_summary({})
        assert summary == "No specific characteristics extracted."
        
        # Test with None
        summary = chat_ui._format_pald_summary(None)
        assert summary == "No specific characteristics extracted."

    @patch('streamlit.rerun')
    def test_process_feedback_success(self, mock_rerun, chat_ui, mock_pseudonym_id, mock_session_state, mock_components):
        """Test successful feedback processing."""
        # Setup
        chat_ui._initialize_study_components()
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        
        # Mock feedback result
        mock_feedback_result = FeedbackProcessingResult(
            feedback_id=uuid4(),
            round_number=1,
            max_rounds_reached=False,
            feedback_pald={"improvement": "make more friendly"},
            should_continue=True,
            processing_metadata={"processing_time_ms": 50}
        )
        
        chat_ui.chat_logic.manage_feedback_loop.return_value = mock_feedback_result
        
        # Test feedback processing
        feedback_text = "Make the character more friendly"
        chat_ui._process_feedback(mock_pseudonym_id, feedback_text)
        
        # Verify feedback logic was called
        chat_ui.chat_logic.manage_feedback_loop.assert_called_once()
        
        # Verify feedback message was added
        session_key = f"study_chat_{mock_pseudonym_id}"
        messages = st.session_state[session_key]['messages']
        
        feedback_messages = [msg for msg in messages if msg.get('message_type') == 'feedback']
        assert len(feedback_messages) == 1
        assert feedback_text in feedback_messages[0]['content']

    @patch('streamlit.rerun')
    def test_process_feedback_max_rounds(self, mock_rerun, chat_ui, mock_pseudonym_id, mock_session_state, mock_components):
        """Test feedback processing when max rounds reached."""
        # Setup
        chat_ui._initialize_study_components()
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        
        # Mock feedback result with max rounds reached
        mock_feedback_result = FeedbackProcessingResult(
            feedback_id=uuid4(),
            round_number=3,
            max_rounds_reached=True,
            feedback_pald=None,
            should_continue=False,
            processing_metadata={"max_rounds": 3}
        )
        
        chat_ui.chat_logic.manage_feedback_loop.return_value = mock_feedback_result
        
        # Test feedback processing
        feedback_text = "Final feedback"
        chat_ui._process_feedback(mock_pseudonym_id, feedback_text)
        
        # Verify feedback round was updated
        session_key = f"study_chat_{mock_pseudonym_id}"
        session_data = st.session_state[session_key]
        assert session_data['feedback_round'] == 3

    @patch('streamlit.rerun')
    def test_accept_current_image(self, mock_rerun, chat_ui, mock_pseudonym_id, mock_session_state):
        """Test accepting current image."""
        # Setup
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        st.session_state["feedback_active"] = True
        
        # Test accepting image
        chat_ui._accept_current_image(mock_pseudonym_id)
        
        # Verify feedback is disabled
        assert st.session_state["feedback_active"] is False
        
        # Verify acceptance message was added
        session_key = f"study_chat_{mock_pseudonym_id}"
        messages = st.session_state[session_key]['messages']
        
        acceptance_messages = [msg for msg in messages if msg.get('message_type') == 'acceptance']
        assert len(acceptance_messages) == 1

    @patch('streamlit.rerun')
    def test_stop_feedback_loop(self, mock_rerun, chat_ui, mock_pseudonym_id, mock_session_state, mock_components):
        """Test stopping feedback loop early."""
        # Setup
        chat_ui._initialize_study_components()
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        st.session_state["feedback_active"] = True
        
        # Mock stop result
        mock_stop_result = FeedbackProcessingResult(
            feedback_id=uuid4(),
            round_number=1,
            max_rounds_reached=True,
            feedback_pald=None,
            should_continue=False,
            processing_metadata={"user_stopped_early": True}
        )
        
        chat_ui.chat_logic.stop_feedback_loop.return_value = mock_stop_result
        
        # Test stopping feedback loop
        chat_ui._stop_feedback_loop(mock_pseudonym_id)
        
        # Verify feedback is disabled
        assert st.session_state["feedback_active"] is False
        
        # Verify stop message was added
        session_key = f"study_chat_{mock_pseudonym_id}"
        messages = st.session_state[session_key]['messages']
        
        stop_messages = [msg for msg in messages if msg.get('message_type') == 'feedback_stopped']
        assert len(stop_messages) == 1

    @patch('streamlit.rerun')
    def test_start_new_study_session(self, mock_rerun, chat_ui, mock_pseudonym_id, mock_session_state):
        """Test starting a new study session."""
        with patch('src.ui.chat_ui.config') as mock_config:
            mock_config.pald_boundary.max_feedback_rounds = 3
            
            # Setup existing session
            chat_ui._initialize_study_session_state(mock_pseudonym_id)
            session_key = f"study_chat_{mock_pseudonym_id}"
            
            # Add some messages to existing session
            st.session_state[session_key]['messages'].append({
                "role": "user",
                "content": "Test message",
                "timestamp": 123456789
            })
            
            # Start new session
            chat_ui._start_new_study_session(mock_pseudonym_id)
            
            # Verify session was reset
            session_data = st.session_state[session_key]
            assert len(session_data['messages']) == 1  # Only welcome message
            assert session_data['feedback_round'] == 0
            assert session_data['consistency_iterations'] == 0
            assert st.session_state.get("feedback_active") is False

    def test_export_study_session_data(self, chat_ui, mock_pseudonym_id, mock_session_state):
        """Test exporting study session data."""
        # Setup session with data
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        session_key = f"study_chat_{mock_pseudonym_id}"
        
        # Add test messages
        st.session_state[session_key]['messages'].extend([
            {
                "role": "user",
                "content": "Test user message",
                "timestamp": 123456789,
                "message_type": "chat",
                "pald_extracted": True
            },
            {
                "role": "assistant",
                "content": "Test assistant response",
                "timestamp": 123456790,
                "message_type": "response",
                "consistency_score": 0.85
            }
        ])
        
        st.session_state[session_key]['feedback_round'] = 2
        st.session_state[session_key]['consistency_iterations'] = 1
        
        with patch('streamlit.download_button') as mock_download:
            chat_ui._export_study_session_data(mock_pseudonym_id)
            
            # Verify download button was called
            mock_download.assert_called_once()
            
            # Check the data structure
            call_args = mock_download.call_args
            assert 'data' in call_args.kwargs
            
            # Parse the JSON data
            import json
            export_data = json.loads(call_args.kwargs['data'])
            
            assert 'session_id' in export_data
            assert 'pseudonym_id' in export_data
            assert 'statistics' in export_data
            assert 'messages' in export_data
            
            # Check statistics
            stats = export_data['statistics']
            assert stats['total_messages'] == 3  # welcome + user + assistant
            assert stats['feedback_rounds'] == 2
            assert stats['consistency_iterations'] == 1
            
            # Check messages
            messages = export_data['messages']
            assert len(messages) == 3
            
            # Check user message metadata
            user_msg = next(msg for msg in messages if msg['role'] == 'user')
            assert user_msg['pald_extracted'] is True
            
            # Check assistant message metadata
            assistant_msg = next(msg for msg in messages if msg['role'] == 'assistant' and 'consistency_score' in msg)
            assert assistant_msg['consistency_score'] == 0.85

    @patch('streamlit.warning')
    def test_export_study_session_data_empty(self, mock_warning, chat_ui, mock_pseudonym_id, mock_session_state):
        """Test exporting empty session data."""
        # Setup empty session
        session_key = f"study_chat_{mock_pseudonym_id}"
        st.session_state[session_key] = {"messages": []}
        
        chat_ui._export_study_session_data(mock_pseudonym_id)
        
        # Verify warning was shown
        mock_warning.assert_called_once_with("No session data to export.")

    @patch('streamlit.rerun')
    @patch('streamlit.success')
    def test_clear_study_session(self, mock_success, mock_rerun, chat_ui, mock_pseudonym_id, mock_session_state):
        """Test clearing study session."""
        # Setup session
        chat_ui._initialize_study_session_state(mock_pseudonym_id)
        session_key = f"study_chat_{mock_pseudonym_id}"
        
        # Verify session exists
        assert session_key in st.session_state
        
        # Clear session
        chat_ui._clear_study_session(mock_pseudonym_id)
        
        # Verify session was removed
        assert session_key not in st.session_state
        assert st.session_state.get("feedback_active") is False
        assert st.session_state.get("pald_processing_status") == "idle"
        
        # Verify success message
        mock_success.assert_called_once()


class TestChatUIStudyRenderMethods:
    """Test suite for chat UI rendering methods."""

    @pytest.fixture
    def chat_ui(self):
        """Create ChatUI instance for testing."""
        return ChatUI()

    @pytest.fixture
    def mock_pseudonym_id(self):
        """Create mock pseudonym ID."""
        return uuid4()

    @patch('streamlit.title')
    @patch('streamlit.caption')
    def test_render_study_participation_chat_consent_check(self, mock_caption, mock_title, chat_ui, mock_pseudonym_id):
        """Test study participation chat rendering with consent check."""
        with patch.object(chat_ui, '_check_study_chat_consent', return_value=False):
            chat_ui.render_study_participation_chat(mock_pseudonym_id)
            
            # Should not proceed past consent check
            # Title should not be called if consent fails
            mock_title.assert_not_called()

    @patch('streamlit.title')
    @patch('streamlit.caption')
    def test_render_study_participation_chat_success(self, mock_caption, mock_title, chat_ui, mock_pseudonym_id):
        """Test successful study participation chat rendering."""
        with patch.object(chat_ui, '_check_study_chat_consent', return_value=True), \
             patch.object(chat_ui, '_initialize_study_components'), \
             patch.object(chat_ui, '_initialize_study_session_state'), \
             patch.object(chat_ui, '_render_study_chat_header'), \
             patch.object(chat_ui, '_render_pald_processing_status'), \
             patch.object(chat_ui, '_render_study_chat_messages'), \
             patch.object(chat_ui, '_render_study_chat_input'), \
             patch.object(chat_ui, '_render_feedback_interface'), \
             patch.object(chat_ui, '_render_study_chat_controls'):
            
            chat_ui.render_study_participation_chat(mock_pseudonym_id)
            
            # Verify title was set
            mock_title.assert_called_once()
            mock_caption.assert_called_once()

    def test_check_study_chat_consent_success(self, chat_ui, mock_pseudonym_id):
        """Test study chat consent check success."""
        # For now, this always returns True
        result = chat_ui._check_study_chat_consent(mock_pseudonym_id)
        assert result is True

    @patch('streamlit.info')
    @patch('streamlit.warning')
    @patch('streamlit.success')
    @patch('streamlit.error')
    def test_render_pald_processing_status_all_states(self, mock_error, mock_success, mock_warning, mock_info, chat_ui):
        """Test PALD processing status rendering for all states."""
        # Test different processing states
        test_states = [
            ("extracting_pald", mock_info),
            ("generating_image", mock_info),
            ("describing_image", mock_info),
            ("checking_consistency", mock_warning),
            ("processing_feedback", mock_info),
            ("completed", mock_success),
            ("error", mock_error)
        ]
        
        for state, expected_mock in test_states:
            # Reset mocks
            for mock_func in [mock_info, mock_warning, mock_success, mock_error]:
                mock_func.reset_mock()
            
            with patch.object(st, 'session_state', {"pald_processing_status": state}):
                chat_ui._render_pald_processing_status()
                expected_mock.assert_called_once()

    @patch('streamlit.session_state', {})
    def test_render_pald_processing_status_consistency_loop(self, chat_ui):
        """Test PALD processing status with active consistency loop."""
        with patch('streamlit.warning') as mock_warning, \
             patch('src.ui.chat_ui.config') as mock_config:
            
            mock_config.pald_boundary.pald_consistency_max_iterations = 5
            
            st.session_state.update({
                "consistency_loop_active": True,
                "consistency_iterations": 2
            })
            
            chat_ui._render_pald_processing_status()
            
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0][0]
            assert "iteration 2/5" in call_args


# Integration test for the complete flow
class TestChatUIStudyIntegrationFlow:
    """Integration tests for complete study participation chat flow."""

    @pytest.fixture
    def chat_ui(self):
        """Create ChatUI instance for testing."""
        return ChatUI()

    @pytest.fixture
    def mock_pseudonym_id(self):
        """Create mock pseudonym ID."""
        return uuid4()

    def test_complete_chat_flow_simulation(self, chat_ui, mock_pseudonym_id):
        """Test a complete chat flow simulation."""
        with patch.object(st, 'session_state', {}) as mock_session_state, \
             patch('src.ui.chat_ui.config') as mock_config, \
             patch.object(chat_ui, '_initialize_study_components'), \
             patch('streamlit.rerun'):
            
            mock_config.pald_boundary.max_feedback_rounds = 3
            mock_config.pald_boundary.pald_consistency_max_iterations = 5
            
            # Initialize session
            chat_ui._initialize_study_session_state(mock_pseudonym_id)
            
            session_key = f"study_chat_{mock_pseudonym_id}"
            initial_message_count = len(st.session_state[session_key]['messages'])
            
            # Simulate user input processing
            with patch.object(chat_ui, 'chat_logic') as mock_chat_logic, \
                 patch.object(chat_ui, 'chat_service') as mock_chat_service:
                
                # Mock successful PALD extraction
                mock_processing_result = ChatProcessingResult(
                    message_id=uuid4(),
                    pald_extracted=True,
                    pald_data={"global_design_level": {"appearance": "friendly"}},
                    consistency_check_performed=False,
                    consistency_result=None,
                    requires_regeneration=False,
                    processing_metadata={"processing_time_ms": 100}
                )
                
                mock_chat_logic.process_chat_input.return_value = mock_processing_result
                
                # Process user input
                user_input = "I want a friendly learning assistant"
                chat_ui._process_study_chat_input(mock_pseudonym_id, user_input)
                
                # Verify messages were added
                messages = st.session_state[session_key]['messages']
                assert len(messages) > initial_message_count
                
                # Verify user message was stored
                user_messages = [msg for msg in messages if msg['role'] == 'user']
                assert len(user_messages) == 1
                assert user_messages[0]['content'] == user_input
                
                # Verify assistant response was generated
                assistant_messages = [msg for msg in messages if msg['role'] == 'assistant' and msg.get('message_type') != 'welcome']
                assert len(assistant_messages) >= 1

    def test_feedback_loop_simulation(self, chat_ui, mock_pseudonym_id):
        """Test feedback loop simulation."""
        with patch.object(st, 'session_state', {}) as mock_session_state, \
             patch('src.ui.chat_ui.config') as mock_config, \
             patch.object(chat_ui, '_initialize_study_components'), \
             patch('streamlit.rerun'):
            
            mock_config.pald_boundary.max_feedback_rounds = 3
            
            # Initialize session
            chat_ui._initialize_study_session_state(mock_pseudonym_id)
            
            with patch.object(chat_ui, 'chat_logic') as mock_chat_logic, \
                 patch.object(chat_ui, 'chat_service') as mock_chat_service:
                
                # Simulate multiple feedback rounds
                for round_num in range(1, 4):  # 3 rounds
                    mock_feedback_result = FeedbackProcessingResult(
                        feedback_id=uuid4(),
                        round_number=round_num,
                        max_rounds_reached=(round_num == 3),
                        feedback_pald={"improvement": f"round {round_num}"},
                        should_continue=(round_num < 3),
                        processing_metadata={"round": round_num}
                    )
                    
                    mock_chat_logic.manage_feedback_loop.return_value = mock_feedback_result
                    
                    # Process feedback
                    feedback_text = f"Feedback round {round_num}"
                    chat_ui._process_feedback(mock_pseudonym_id, feedback_text)
                    
                    # Verify feedback round was updated
                    session_key = f"study_chat_{mock_pseudonym_id}"
                    session_data = st.session_state[session_key]
                    assert session_data['feedback_round'] == round_num
                
                # Verify all feedback messages were stored
                session_key = f"study_chat_{mock_pseudonym_id}"
                messages = st.session_state[session_key]['messages']
                feedback_messages = [msg for msg in messages if msg.get('message_type') == 'feedback']
                assert len(feedback_messages) == 3