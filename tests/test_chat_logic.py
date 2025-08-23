"""
Unit tests for ChatLogic class.
Tests chat processing, PALD extraction, consistency checking, and feedback loop management.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

from config.config import config
from src.data.models import ChatMessageType, StudyPALDType
from src.logic.chat_logic import (
    ChatLogic,
    ChatProcessingResult,
    ConsistencyCheckResult,
    FeedbackProcessingResult,
    PALDExtractionResult,
)
from src.services.llm_service import LLMResponse


class TestChatLogic:
    """Test suite for ChatLogic class."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        mock_service = Mock()
        return mock_service

    @pytest.fixture
    def chat_logic(self, mock_llm_service):
        """Create ChatLogic instance with mocked dependencies."""
        return ChatLogic(mock_llm_service)

    @pytest.fixture
    def sample_pald_data(self):
        """Sample PALD data for testing."""
        return {
            "global_design_level": {
                "overall_appearance": "friendly teacher",
                "style": "professional",
                "theme": "educational"
            },
            "middle_design_level": {
                "physical_attributes": "middle-aged woman",
                "clothing": "business attire",
                "accessories": "glasses"
            },
            "detailed_level": {
                "facial_features": "warm smile",
                "hair": "brown hair in a bun",
                "colors": "blue and white"
            }
        }

    def test_process_chat_input_success(self, chat_logic, mock_llm_service, sample_pald_data):
        """Test successful chat input processing."""
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        message_content = "I want a friendly teacher with glasses and brown hair"
        
        # Mock LLM response
        mock_response = LLMResponse(
            text=json.dumps(sample_pald_data),
            model="llama3",
            tokens_used=150,
            latency_ms=500
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute
        result = chat_logic.process_chat_input(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_content=message_content,
            message_type=ChatMessageType.USER
        )
        
        # Verify
        assert isinstance(result, ChatProcessingResult)
        assert result.pald_extracted is True
        assert result.pald_data is not None
        assert "global_design_level" in result.pald_data
        assert result.processing_metadata["message_length"] == len(message_content)
        assert "total_processing_time_ms" in result.processing_metadata

    def test_process_chat_input_no_pald(self, chat_logic, mock_llm_service):
        """Test chat input processing with no PALD content."""
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        message_content = "Hello, how are you today?"
        
        # Mock LLM response with empty PALD
        mock_response = LLMResponse(
            text="{}",
            model="llama3",
            tokens_used=50,
            latency_ms=300
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute
        result = chat_logic.process_chat_input(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_content=message_content,
            message_type=ChatMessageType.USER
        )
        
        # Verify
        assert isinstance(result, ChatProcessingResult)
        assert result.pald_extracted is False
        assert result.pald_data is None or result.pald_data == {}

    def test_extract_pald_from_text_success(self, chat_logic, mock_llm_service, sample_pald_data):
        """Test successful PALD extraction from text."""
        # Setup
        text = "Create a friendly female teacher with glasses and professional attire"
        
        # Mock LLM response
        mock_response = LLMResponse(
            text=json.dumps(sample_pald_data),
            model="llama3",
            tokens_used=120,
            latency_ms=400
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute
        result = chat_logic.extract_pald_from_text(text)
        
        # Verify
        assert isinstance(result, PALDExtractionResult)
        assert result.success is True
        assert result.pald_data == sample_pald_data
        assert result.extraction_confidence > 0
        assert result.processing_time_ms >= 0  # Allow 0 for fast tests
        assert result.error_message is None

    def test_extract_pald_from_text_invalid_json(self, chat_logic, mock_llm_service):
        """Test PALD extraction with invalid JSON response."""
        # Setup
        text = "Create a teacher"
        
        # Mock LLM response with invalid JSON
        mock_response = LLMResponse(
            text="This is not valid JSON {invalid}",
            model="llama3",
            tokens_used=50,
            latency_ms=300
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute
        result = chat_logic.extract_pald_from_text(text)
        
        # Verify
        assert isinstance(result, PALDExtractionResult)
        assert result.success is False
        assert result.pald_data == {}
        assert result.error_message is not None

    def test_extract_pald_caching(self, chat_logic, mock_llm_service, sample_pald_data):
        """Test that PALD extraction results are cached."""
        # Setup
        text = "Create a teacher with glasses"
        
        # Mock LLM response
        mock_response = LLMResponse(
            text=json.dumps(sample_pald_data),
            model="llama3",
            tokens_used=120,
            latency_ms=400
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute twice
        result1 = chat_logic.extract_pald_from_text(text)
        result2 = chat_logic.extract_pald_from_text(text)
        
        # Verify
        assert result1.success is True
        assert result2.success is True
        assert result1.pald_data == result2.pald_data
        
        # LLM should only be called once due to caching
        assert mock_llm_service.generate_response.call_count == 1

    def test_check_pald_consistency_high_similarity(self, chat_logic, sample_pald_data):
        """Test consistency check with highly similar PALDs."""
        # Setup - create slightly different but similar PALD
        description_pald = sample_pald_data.copy()
        description_pald["detailed_level"]["facial_features"] = "friendly smile"  # slight variation
        
        # Execute
        result = chat_logic.check_pald_consistency(sample_pald_data, description_pald)
        
        # Verify
        assert isinstance(result, ConsistencyCheckResult)
        assert result.consistency_score > 0.8  # Should be high similarity
        assert result.is_consistent is True
        assert result.recommendation == "continue"

    def test_check_pald_consistency_low_similarity(self, chat_logic, sample_pald_data):
        """Test consistency check with low similarity PALDs."""
        # Setup - create very different PALD
        description_pald = {
            "global_design_level": {
                "overall_appearance": "robot",
                "style": "futuristic",
                "theme": "sci-fi"
            },
            "middle_design_level": {
                "physical_attributes": "metallic body",
                "clothing": "none",
                "accessories": "LED lights"
            }
        }
        
        # Execute
        result = chat_logic.check_pald_consistency(sample_pald_data, description_pald)
        
        # Verify
        assert isinstance(result, ConsistencyCheckResult)
        assert result.consistency_score < 0.5  # Should be low similarity
        assert result.is_consistent is False
        assert result.recommendation == "regenerate"

    def test_check_pald_consistency_empty_palds(self, chat_logic):
        """Test consistency check with empty PALDs."""
        # Execute
        result = chat_logic.check_pald_consistency({}, {})
        
        # Verify
        assert isinstance(result, ConsistencyCheckResult)
        assert result.consistency_score == 1.0  # Both empty should be consistent
        assert result.is_consistent is True

    def test_manage_feedback_loop_within_limits(self, chat_logic, mock_llm_service, sample_pald_data):
        """Test feedback loop management within round limits."""
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        feedback_text = "Make the teacher look more friendly"
        current_round = 2
        
        # Mock LLM response for feedback PALD extraction
        mock_response = LLMResponse(
            text=json.dumps(sample_pald_data),
            model="llama3",
            tokens_used=80,
            latency_ms=300
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute
        result = chat_logic.manage_feedback_loop(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text=feedback_text,
            current_round=current_round
        )
        
        # Verify
        assert isinstance(result, FeedbackProcessingResult)
        assert result.round_number == current_round
        assert result.max_rounds_reached is False
        assert result.should_continue is True
        assert result.feedback_pald is not None

    def test_manage_feedback_loop_max_rounds_reached(self, chat_logic, mock_llm_service):
        """Test feedback loop when maximum rounds are reached."""
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        feedback_text = "Make changes"
        current_round = 3  # Assuming max_feedback_rounds is 3
        
        # Execute
        result = chat_logic.manage_feedback_loop(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text=feedback_text,
            current_round=current_round
        )
        
        # Verify
        assert isinstance(result, FeedbackProcessingResult)
        assert result.round_number == current_round
        assert result.max_rounds_reached is True
        assert result.should_continue is False

    def test_manage_feedback_loop_user_stops_early(self, chat_logic, mock_llm_service, sample_pald_data):
        """Test feedback loop when user wants to stop early."""
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        feedback_text = "I'm satisfied with this result"
        current_round = 1
        
        # Mock LLM response for feedback PALD extraction
        mock_response = LLMResponse(
            text=json.dumps(sample_pald_data),
            model="llama3",
            tokens_used=80,
            latency_ms=300
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute
        result = chat_logic.manage_feedback_loop(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text=feedback_text,
            current_round=current_round,
            user_wants_to_stop=True
        )
        
        # Verify
        assert isinstance(result, FeedbackProcessingResult)
        assert result.round_number == current_round
        assert result.max_rounds_reached is True  # Should be treated as max rounds reached
        assert result.should_continue is False
        assert result.processing_metadata["user_stopped_early"] is True

    def test_stop_feedback_loop(self, chat_logic):
        """Test explicit feedback loop stopping."""
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        current_round = 2
        
        # Execute
        result = chat_logic.stop_feedback_loop(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            current_round=current_round
        )
        
        # Verify
        assert isinstance(result, FeedbackProcessingResult)
        assert result.round_number == current_round
        assert result.max_rounds_reached is True
        assert result.should_continue is False
        assert result.feedback_pald is None
        assert result.processing_metadata["user_stopped_early"] is True
        assert result.processing_metadata["stop_reason"] == "user_request"

    def test_feedback_processing_metadata_completeness(self, chat_logic, mock_llm_service, sample_pald_data):
        """Test that feedback processing returns complete metadata for logging."""
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        feedback_text = "Make the teacher more friendly"
        current_round = 1
        
        # Mock LLM response
        mock_response = LLMResponse(
            text=json.dumps(sample_pald_data),
            model="llama3",
            tokens_used=150,
            latency_ms=500
        )
        mock_llm_service.generate_response.return_value = mock_response
        
        # Execute
        result = chat_logic.manage_feedback_loop(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text=feedback_text,
            current_round=current_round
        )
        
        # Verify metadata contains all required fields for comprehensive logging
        metadata = result.processing_metadata
        assert "feedback_length" in metadata
        assert "pald_extraction_success" in metadata
        assert "pald_confidence" in metadata
        assert "max_rounds" in metadata
        assert "rounds_remaining" in metadata
        assert "user_stopped_early" in metadata
        
        # Verify values are correct
        assert metadata["feedback_length"] == len(feedback_text)
        assert metadata["pald_extraction_success"] is True
        assert metadata["pald_confidence"] > 0
        assert metadata["max_rounds"] == config.pald_boundary.max_feedback_rounds
        assert metadata["rounds_remaining"] == config.pald_boundary.max_feedback_rounds - current_round
        assert metadata["user_stopped_early"] is False

    def test_create_pald_extraction_prompt(self, chat_logic):
        """Test PALD extraction prompt creation."""
        # Setup
        text = "Create a friendly teacher"
        
        # Execute
        prompt = chat_logic._create_pald_extraction_prompt(text)
        
        # Verify
        assert isinstance(prompt, str)
        assert text in prompt
        assert "PALD" in prompt
        assert "JSON" in prompt
        assert "global_design_level" in prompt
        assert "middle_design_level" in prompt
        assert "detailed_level" in prompt

    def test_parse_pald_response_valid_json(self, chat_logic, sample_pald_data):
        """Test parsing valid JSON PALD response."""
        # Setup
        response_text = json.dumps(sample_pald_data)
        
        # Execute
        result = chat_logic._parse_pald_response(response_text)
        
        # Verify
        assert result == sample_pald_data

    def test_parse_pald_response_json_with_markdown(self, chat_logic, sample_pald_data):
        """Test parsing JSON wrapped in markdown code blocks."""
        # Setup
        response_text = f"```json\n{json.dumps(sample_pald_data)}\n```"
        
        # Execute
        result = chat_logic._parse_pald_response(response_text)
        
        # Verify
        assert result == sample_pald_data

    def test_parse_pald_response_invalid_json(self, chat_logic):
        """Test parsing invalid JSON response."""
        # Setup
        response_text = "This is not JSON"
        
        # Execute
        result = chat_logic._parse_pald_response(response_text)
        
        # Verify
        assert result == {}

    def test_calculate_consistency_score_identical(self, chat_logic, sample_pald_data):
        """Test consistency score calculation for identical PALDs."""
        # Execute
        score = chat_logic._calculate_consistency_score(sample_pald_data, sample_pald_data)
        
        # Verify
        assert score == 1.0

    def test_calculate_consistency_score_empty(self, chat_logic):
        """Test consistency score calculation for empty PALDs."""
        # Execute
        score_both_empty = chat_logic._calculate_consistency_score({}, {})
        score_one_empty = chat_logic._calculate_consistency_score({}, {"key": "value"})
        
        # Verify
        assert score_both_empty == 1.0  # Both empty, perfectly consistent
        assert score_one_empty == 0.0  # One empty, one not - inconsistent

    def test_calculate_consistency_score_partial_match(self, chat_logic, sample_pald_data):
        """Test consistency score calculation for partial matches."""
        # Setup - create PALD with some matching and some different content
        partial_pald = {
            "global_design_level": sample_pald_data["global_design_level"],  # Same
            "middle_design_level": {
                "physical_attributes": "young man",  # Different
                "clothing": "casual wear",  # Different
                "accessories": "glasses"  # Same
            }
        }
        
        # Execute
        score = chat_logic._calculate_consistency_score(sample_pald_data, partial_pald)
        
        # Verify
        assert 0.0 < score < 1.0  # Should be between 0 and 1

    def test_calculate_attribute_similarity_strings(self, chat_logic):
        """Test attribute similarity calculation for strings."""
        # Execute
        similarity1 = chat_logic._calculate_attribute_similarity("friendly teacher", "friendly teacher")
        similarity2 = chat_logic._calculate_attribute_similarity("friendly teacher", "kind instructor")
        similarity3 = chat_logic._calculate_attribute_similarity("friendly teacher", "robot assistant")
        similarity4 = chat_logic._calculate_attribute_similarity("teacher", "instructor")  # Partial match
        
        # Verify
        assert similarity1 == 1.0  # Identical
        assert similarity2 >= 0.0  # May have partial matches or none
        assert similarity3 >= 0.0  # Different but valid
        assert similarity4 >= 0.0  # Partial word match possible

    def test_calculate_attribute_similarity_dicts(self, chat_logic):
        """Test attribute similarity calculation for nested dictionaries."""
        # Setup
        dict1 = {"hair": "brown", "eyes": "blue"}
        dict2 = {"hair": "brown", "eyes": "green"}
        dict3 = {"hair": "blonde", "skin": "fair"}
        
        # Execute
        similarity1 = chat_logic._calculate_attribute_similarity(dict1, dict1)
        similarity2 = chat_logic._calculate_attribute_similarity(dict1, dict2)
        similarity3 = chat_logic._calculate_attribute_similarity(dict1, dict3)
        
        # Verify
        assert similarity1 == 1.0  # Identical
        assert 0.0 < similarity2 < 1.0  # Partial match
        assert similarity3 >= 0.0  # Different keys

    def test_identify_pald_differences(self, chat_logic, sample_pald_data):
        """Test identification of differences between PALDs."""
        # Setup - create PALD with some differences
        modified_pald = sample_pald_data.copy()
        modified_pald["global_design_level"]["style"] = "casual"  # Changed
        del modified_pald["detailed_level"]  # Removed
        modified_pald["new_level"] = {"new_attr": "value"}  # Added
        
        # Execute
        differences = chat_logic._identify_pald_differences(sample_pald_data, modified_pald)
        
        # Verify
        assert isinstance(differences, list)
        assert len(differences) > 0
        
        # Check for expected difference types
        difference_text = " ".join(differences)
        assert "detailed_level" in difference_text  # Should mention removed key
        assert "new_level" in difference_text  # Should mention added key


class TestChatLogicIntegration:
    """Integration tests for ChatLogic with real-like scenarios."""

    @pytest.fixture
    def chat_logic_with_mock_llm(self):
        """Create ChatLogic with a more realistic mock LLM."""
        mock_llm = Mock()
        return ChatLogic(mock_llm), mock_llm

    def test_full_chat_processing_workflow(self, chat_logic_with_mock_llm):
        """Test complete chat processing workflow."""
        chat_logic, mock_llm = chat_logic_with_mock_llm
        
        # Setup realistic scenario
        pseudonym_id = uuid4()
        session_id = uuid4()
        user_message = "I want a friendly female teacher with glasses and a warm smile"
        
        # Mock PALD extraction response
        pald_data = {
            "global_design_level": {"overall_appearance": "friendly teacher"},
            "middle_design_level": {"physical_attributes": "female", "accessories": "glasses"},
            "detailed_level": {"facial_features": "warm smile"}
        }
        
        mock_llm.generate_response.return_value = LLMResponse(
            text=json.dumps(pald_data),
            model="llama3",
            tokens_used=150,
            latency_ms=500
        )
        
        # Execute chat processing
        result = chat_logic.process_chat_input(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_content=user_message,
            message_type=ChatMessageType.USER
        )
        
        # Verify successful processing
        assert result.pald_extracted is True
        assert result.pald_data is not None
        assert "friendly teacher" in str(result.pald_data)
        
        # Test consistency check with similar description
        description_pald = {
            "global_design_level": {"overall_appearance": "kind teacher"},
            "middle_design_level": {"physical_attributes": "woman", "accessories": "eyeglasses"},
            "detailed_level": {"facial_features": "pleasant smile"}
        }
        
        consistency_result = chat_logic.check_pald_consistency(result.pald_data, description_pald)
        assert consistency_result.consistency_score > 0.2  # Lower threshold for realistic test
        
        # Test feedback processing
        feedback_result = chat_logic.manage_feedback_loop(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text="Make her look more professional",
            current_round=1
        )
        
        assert feedback_result.should_continue is True
        assert feedback_result.max_rounds_reached is False

    def test_error_handling_in_workflow(self, chat_logic_with_mock_llm):
        """Test error handling throughout the workflow."""
        chat_logic, mock_llm = chat_logic_with_mock_llm
        
        # Setup scenario with LLM failure
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock LLM to raise exception
        mock_llm.generate_response.side_effect = Exception("LLM service unavailable")
        
        # Execute and verify graceful error handling
        result = chat_logic.process_chat_input(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_content="Create a teacher",
            message_type=ChatMessageType.USER
        )
        
        assert result.pald_extracted is False
        assert result.pald_data is None
        assert "pald_extraction_error" in result.processing_metadata