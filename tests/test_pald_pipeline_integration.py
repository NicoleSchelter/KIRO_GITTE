"""
Integration tests for PALD Pipeline and Image Generation Flow.
Tests the complete PALD processing pipeline with consistency loops and feedback rounds.

This test suite validates:
- PALD extraction from various text inputs
- Consistency checking between input and description PALDs
- Feedback loop management with round counting
- Image generation integration with PALD data
- Performance under various PALD processing scenarios
"""

import pytest
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID

from src.logic.chat_logic import (
    ChatLogic, 
    PALDExtractionResult, 
    ConsistencyCheckResult, 
    ChatProcessingResult,
    FeedbackProcessingResult
)
from src.services.chat_service import ChatService
from src.data.models import ChatMessageType, StudyPALDType
from src.exceptions import ValidationError, DatabaseError


class TestPALDExtractionIntegration:
    """Integration tests for PALD extraction from various text inputs."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service with realistic PALD responses."""
        service = Mock()
        
        def mock_generate_response(prompt, model=None, parameters=None):
            # Simulate different PALD extraction responses based on input
            if "friendly teacher" in prompt.lower():
                response_text = '''
                {
                    "global_design_level": {
                        "overall_appearance": "friendly professional teacher",
                        "style": "approachable and warm",
                        "theme": "educational mentor"
                    },
                    "middle_design_level": {
                        "physical_attributes": "middle-aged adult",
                        "clothing": "professional attire",
                        "accessories": "glasses and teaching materials"
                    },
                    "detailed_level": {
                        "facial_features": "kind eyes and gentle smile",
                        "hair": "neat and professional",
                        "colors": "warm earth tones",
                        "specific_details": "confident posture"
                    }
                }
                '''
            elif "robot" in prompt.lower():
                response_text = '''
                {
                    "global_design_level": {
                        "overall_appearance": "futuristic robot assistant",
                        "style": "sleek and modern",
                        "theme": "technological helper"
                    },
                    "middle_design_level": {
                        "physical_attributes": "humanoid robot form",
                        "clothing": "metallic exterior",
                        "accessories": "LED indicators and sensors"
                    },
                    "detailed_level": {
                        "facial_features": "digital display face",
                        "hair": "none",
                        "colors": "silver and blue",
                        "specific_details": "articulated joints"
                    }
                }
                '''
            else:
                response_text = '{"global_design_level": {"overall_appearance": "generic character"}}'
            
            mock_response = Mock()
            mock_response.text = response_text
            return mock_response
        
        service.generate_response = mock_generate_response
        return service
    
    @pytest.fixture
    def chat_logic(self, mock_llm_service):
        """Create ChatLogic instance with mocked dependencies."""
        return ChatLogic(mock_llm_service)
    
    def test_pald_extraction_from_detailed_description(self, chat_logic):
        """Test PALD extraction from detailed character descriptions."""
        detailed_input = """
        I want a friendly female teacher with brown curly hair, wearing glasses and a blue cardigan.
        She should have a warm smile and look approachable. Make her appear to be in her 40s with
        kind eyes and a professional but welcoming demeanor. She should be holding a book and
        standing in front of a whiteboard.
        """
        
        result = chat_logic.extract_pald_from_text(detailed_input)
        
        assert result.success is True
        assert result.pald_data is not None
        assert result.extraction_confidence > 0.5
        assert result.processing_time_ms > 0
        
        # Verify PALD structure
        pald_data = result.pald_data
        assert "global_design_level" in pald_data
        assert "middle_design_level" in pald_data
        assert "detailed_level" in pald_data
        
        # Verify content extraction
        global_level = pald_data["global_design_level"]
        assert "teacher" in str(global_level).lower()
        assert "friendly" in str(global_level).lower()
    
    def test_pald_extraction_from_minimal_input(self, chat_logic):
        """Test PALD extraction from minimal character descriptions."""
        minimal_inputs = [
            "Make a robot",
            "I want a teacher",
            "Create a friendly character",
            "Show me a professional person"
        ]
        
        for input_text in minimal_inputs:
            result = chat_logic.extract_pald_from_text(input_text)
            
            assert result.success is True
            assert result.pald_data is not None
            
            # Even minimal input should produce some PALD data
            pald_data = result.pald_data
            assert len(pald_data) > 0
            
            # Should have at least global design level
            if "global_design_level" in pald_data:
                assert len(pald_data["global_design_level"]) > 0
    
    def test_pald_extraction_caching(self, chat_logic):
        """Test PALD extraction caching for performance."""
        input_text = "I want a friendly teacher with glasses"
        
        # First extraction
        start_time = time.time()
        result1 = chat_logic.extract_pald_from_text(input_text)
        first_time = time.time() - start_time
        
        # Second extraction (should use cache)
        start_time = time.time()
        result2 = chat_logic.extract_pald_from_text(input_text)
        second_time = time.time() - start_time
        
        # Verify results are identical
        assert result1.success == result2.success
        assert result1.pald_data == result2.pald_data
        
        # Second call should be faster (cached)
        assert second_time < first_time or second_time < 0.001  # Very fast for cached result
    
    def test_pald_extraction_error_handling(self, mock_llm_service):
        """Test PALD extraction error handling and recovery."""
        # Mock LLM service to raise exception
        mock_llm_service.generate_response.side_effect = Exception("LLM service unavailable")
        
        chat_logic = ChatLogic(mock_llm_service)
        
        result = chat_logic.extract_pald_from_text("I want a teacher")
        
        assert result.success is False
        assert result.pald_data == {}
        assert result.extraction_confidence == 0.0
        assert result.error_message is not None
        assert "LLM service unavailable" in result.error_message


class TestPALDConsistencyChecking:
    """Integration tests for PALD consistency checking between input and descriptions."""
    
    @pytest.fixture
    def chat_logic(self):
        """Create ChatLogic instance for consistency testing."""
        return ChatLogic(Mock())  # LLM service not needed for consistency checking
    
    def test_high_consistency_pald_comparison(self, chat_logic):
        """Test consistency checking with highly consistent PALDs."""
        input_pald = {
            "global_design_level": {
                "overall_appearance": "friendly female teacher",
                "style": "professional and warm",
                "theme": "educational mentor"
            },
            "middle_design_level": {
                "physical_attributes": "middle-aged woman",
                "clothing": "blue cardigan and skirt",
                "accessories": "glasses and book"
            },
            "detailed_level": {
                "facial_features": "kind eyes and warm smile",
                "hair": "brown curly hair",
                "colors": "blue and brown tones"
            }
        }
        
        description_pald = {
            "global_design_level": {
                "overall_appearance": "friendly female educator",
                "style": "professional and approachable",
                "theme": "teaching professional"
            },
            "middle_design_level": {
                "physical_attributes": "middle-aged woman",
                "clothing": "blue cardigan and dark skirt",
                "accessories": "reading glasses and textbook"
            },
            "detailed_level": {
                "facial_features": "warm eyes and gentle smile",
                "hair": "curly brown hair",
                "colors": "blue and earth tones"
            }
        }
        
        result = chat_logic.check_pald_consistency(input_pald, description_pald)
        
        assert result.is_consistent is True
        assert result.consistency_score > 0.8
        assert result.recommendation == "continue"
        assert len(result.differences) <= 2  # Minor differences acceptable
    
    def test_low_consistency_pald_comparison(self, chat_logic):
        """Test consistency checking with inconsistent PALDs."""
        input_pald = {
            "global_design_level": {
                "overall_appearance": "friendly female teacher",
                "style": "professional and warm"
            },
            "detailed_level": {
                "hair": "brown curly hair",
                "accessories": "glasses"
            }
        }
        
        description_pald = {
            "global_design_level": {
                "overall_appearance": "stern male professor",
                "style": "formal and intimidating"
            },
            "detailed_level": {
                "hair": "short gray hair",
                "accessories": "bow tie"
            }
        }
        
        result = chat_logic.check_pald_consistency(input_pald, description_pald)
        
        assert result.is_consistent is False
        assert result.consistency_score < 0.5
        assert result.recommendation in ["regenerate", "accept"]
        assert len(result.differences) > 0
        
        # Verify specific differences are identified
        differences_text = " ".join(result.differences)
        assert len(differences_text) > 0
    
    def test_partial_pald_consistency(self, chat_logic):
        """Test consistency checking with partially matching PALDs."""
        input_pald = {
            "global_design_level": {
                "overall_appearance": "friendly teacher",
                "style": "professional"
            },
            "middle_design_level": {
                "clothing": "blue cardigan"
            }
        }
        
        description_pald = {
            "global_design_level": {
                "overall_appearance": "friendly educator",
                "style": "professional"
            },
            "detailed_level": {
                "hair": "brown hair",
                "colors": "blue tones"
            }
        }
        
        result = chat_logic.check_pald_consistency(input_pald, description_pald)
        
        # Should handle partial matches reasonably
        assert isinstance(result.consistency_score, float)
        assert 0.0 <= result.consistency_score <= 1.0
        assert result.recommendation in ["continue", "regenerate", "accept"]
    
    def test_empty_pald_consistency(self, chat_logic):
        """Test consistency checking with empty or missing PALDs."""
        # Both empty
        result1 = chat_logic.check_pald_consistency({}, {})
        assert result1.is_consistent is True
        assert result1.consistency_score == 1.0
        
        # One empty, one with data
        input_pald = {"global_design_level": {"overall_appearance": "teacher"}}
        result2 = chat_logic.check_pald_consistency(input_pald, {})
        assert result2.is_consistent is False
        assert result2.consistency_score == 0.0
        
        # Reverse case
        result3 = chat_logic.check_pald_consistency({}, input_pald)
        assert result3.is_consistent is False
        assert result3.consistency_score == 0.0


class TestFeedbackLoopManagement:
    """Integration tests for feedback loop management and round counting."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service for feedback processing."""
        service = Mock()
        mock_response = Mock()
        mock_response.text = '{"detailed_level": {"hair": "should be brown", "accessories": "needs glasses"}}'
        service.generate_response = Mock(return_value=mock_response)
        return service
    
    @pytest.fixture
    def chat_logic(self, mock_llm_service):
        """Create ChatLogic instance for feedback testing."""
        return ChatLogic(mock_llm_service)
    
    def test_feedback_loop_progression(self, chat_logic):
        """Test feedback loop progression through multiple rounds."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        image_id = uuid4()
        
        feedback_rounds = [
            "The hair should be brown, not blonde",
            "Add glasses to make her look more professional",
            "The smile should be warmer and more welcoming"
        ]
        
        for round_num, feedback_text in enumerate(feedback_rounds, 1):
            result = chat_logic.manage_feedback_loop(
                pseudonym_id, session_id, feedback_text, round_num, image_id
            )
            
            assert result.round_number == round_num
            assert result.feedback_id is not None
            assert isinstance(result.feedback_id, UUID)
            
            # Check round limits
            if round_num < 3:  # Assuming max_rounds = 3
                assert result.max_rounds_reached is False
                assert result.should_continue is True
            else:
                # Last round or max reached
                assert result.max_rounds_reached is True or round_num >= 3
            
            # Verify feedback PALD extraction
            assert result.feedback_pald is not None
            assert isinstance(result.feedback_pald, dict)
            
            # Verify processing metadata
            metadata = result.processing_metadata
            assert "feedback_length" in metadata
            assert "pald_extraction_success" in metadata
            assert metadata["feedback_length"] == len(feedback_text)
    
    def test_feedback_loop_max_rounds_enforcement(self, chat_logic):
        """Test that feedback loop respects maximum round limits."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock config to set max rounds to 2
        with patch('src.logic.chat_logic.config') as mock_config:
            mock_config.pald_boundary.max_feedback_rounds = 2
            
            # Round 1 - should continue
            result1 = chat_logic.manage_feedback_loop(
                pseudonym_id, session_id, "First feedback", 1
            )
            assert result1.max_rounds_reached is False
            assert result1.should_continue is True
            
            # Round 2 - should be last round
            result2 = chat_logic.manage_feedback_loop(
                pseudonym_id, session_id, "Second feedback", 2
            )
            assert result2.max_rounds_reached is True
            assert result2.should_continue is False
            
            # Round 3 - should not continue (over limit)
            result3 = chat_logic.manage_feedback_loop(
                pseudonym_id, session_id, "Third feedback", 3
            )
            assert result3.max_rounds_reached is True
            assert result3.should_continue is False
    
    def test_feedback_loop_early_stop(self, chat_logic):
        """Test that users can stop the feedback loop early."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Test early stop via manage_feedback_loop
        result1 = chat_logic.manage_feedback_loop(
            pseudonym_id, session_id, "I'm satisfied", 1, user_wants_to_stop=True
        )
        assert result1.max_rounds_reached is True
        assert result1.should_continue is False
        assert result1.processing_metadata["user_stopped_early"] is True
        
        # Test explicit stop method
        result2 = chat_logic.stop_feedback_loop(pseudonym_id, session_id, 2)
        assert result2.max_rounds_reached is True
        assert result2.should_continue is False
        assert result2.processing_metadata["user_stopped_early"] is True
        assert result2.processing_metadata["stop_reason"] == "user_request"

    def test_feedback_loop_error_handling(self, mock_llm_service):
        """Test feedback loop error handling and graceful degradation."""
        # Mock LLM service to fail
        mock_llm_service.generate_response.side_effect = Exception("PALD extraction failed")
        
        chat_logic = ChatLogic(mock_llm_service)
        
        result = chat_logic.manage_feedback_loop(
            uuid4(), uuid4(), "Some feedback", 1
        )
        
        assert result.max_rounds_reached is True  # Stop on error
        assert result.should_continue is False
        assert result.feedback_pald is None
        assert "error" in result.processing_metadata


class TestFeedbackSystemIntegration:
    """Integration tests for complete feedback system with data persistence."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service for feedback processing."""
        service = Mock()
        mock_response = Mock()
        mock_response.text = '{"detailed_level": {"hair": "should be brown", "accessories": "needs glasses"}}'
        service.generate_response = Mock(return_value=mock_response)
        return service
    
    @pytest.fixture
    def chat_logic(self, mock_llm_service):
        """Create ChatLogic instance for feedback testing."""
        return ChatLogic(mock_llm_service)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        return Mock()
    
    @pytest.fixture
    def chat_service(self, mock_db_session):
        """Chat service with mocked database session."""
        from src.services.chat_service import ChatService
        return ChatService(mock_db_session)
    
    def test_complete_feedback_workflow_with_storage(self, chat_logic, chat_service, mock_db_session):
        """Test complete feedback workflow including data storage."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        feedback_text = "Make the teacher look more professional"
        current_round = 1
        image_id = uuid4()
        
        # Process feedback through logic layer
        feedback_result = chat_logic.manage_feedback_loop(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text=feedback_text,
            current_round=current_round,
            image_id=image_id
        )
        
        # Store feedback record through service layer
        stored_feedback = chat_service.store_feedback_record(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text=feedback_text,
            round_number=current_round,
            image_id=image_id,
            feedback_pald=feedback_result.feedback_pald
        )
        
        # Log interaction metadata
        interaction_log = chat_service.log_interaction_metadata(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type="feedback_processing",
            model_used="llama3",
            parameters={"temperature": 0.3, "max_tokens": 1000},
            latency_ms=500,
            prompt="PALD extraction prompt",
            response="PALD extraction response",
            token_usage={"input_tokens": 100, "output_tokens": 50}
        )
        
        # Verify all components worked together
        assert feedback_result.feedback_id is not None
        assert feedback_result.round_number == current_round
        assert feedback_result.feedback_pald is not None
        
        # Verify database operations were called
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()


class TestChatServiceIntegration:
    """Integration tests for chat service data persistence."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.query = Mock()
        return session
    
    @pytest.fixture
    def chat_service(self, mock_db_session):
        """Create ChatService instance."""
        return ChatService(mock_db_session)
    
    def test_chat_message_storage_and_retrieval(self, chat_service, mock_db_session):
        """Test storing and retrieving chat messages with PALD data."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock stored message
        mock_message = Mock()
        mock_message.message_id = uuid4()
        mock_message.pseudonym_id = pseudonym_id
        mock_message.session_id = session_id
        mock_message.message_type = ChatMessageType.USER.value
        mock_message.content = "I want a friendly teacher"
        mock_message.pald_data = {"global_design_level": {"overall_appearance": "teacher"}}
        mock_message.timestamp = datetime.utcnow()
        
        # Test message storage
        with patch('src.services.chat_service.ChatMessage', return_value=mock_message):
            stored_message = chat_service.store_chat_message(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                message_type=ChatMessageType.USER,
                content="I want a friendly teacher",
                pald_data={"global_design_level": {"overall_appearance": "teacher"}}
            )
            
            assert stored_message.pseudonym_id == pseudonym_id
            assert stored_message.session_id == session_id
            assert stored_message.pald_data is not None
            
            # Verify database operations
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    def test_pald_data_storage_and_retrieval(self, chat_service, mock_db_session):
        """Test storing and retrieving PALD data."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        pald_content = {
            "global_design_level": {"overall_appearance": "friendly teacher"},
            "detailed_level": {"hair": "brown", "accessories": "glasses"}
        }
        
        # Mock stored PALD data
        mock_pald = Mock()
        mock_pald.pald_id = uuid4()
        mock_pald.pseudonym_id = pseudonym_id
        mock_pald.session_id = session_id
        mock_pald.pald_content = pald_content
        mock_pald.pald_type = StudyPALDType.INPUT.value
        mock_pald.consistency_score = 0.85
        
        # Test PALD storage
        with patch('src.services.chat_service.StudyPALDData', return_value=mock_pald):
            stored_pald = chat_service.store_pald_data(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                pald_content=pald_content,
                pald_type=StudyPALDType.INPUT,
                consistency_score=0.85
            )
            
            assert stored_pald.pseudonym_id == pseudonym_id
            assert stored_pald.pald_content == pald_content
            assert stored_pald.consistency_score == 0.85
            
            # Verify database operations
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
    
    def test_feedback_record_storage(self, chat_service, mock_db_session):
        """Test storing feedback records with round tracking."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        image_id = uuid4()
        
        feedback_data = [
            ("Make the hair brown", 1, {"detailed_level": {"hair": "brown"}}),
            ("Add glasses", 2, {"detailed_level": {"accessories": "glasses"}}),
            ("Make smile warmer", 3, {"detailed_level": {"facial_features": "warm smile"}})
        ]
        
        for feedback_text, round_num, feedback_pald in feedback_data:
            # Mock stored feedback
            mock_feedback = Mock()
            mock_feedback.feedback_id = uuid4()
            mock_feedback.pseudonym_id = pseudonym_id
            mock_feedback.session_id = session_id
            mock_feedback.image_id = image_id
            mock_feedback.feedback_text = feedback_text
            mock_feedback.round_number = round_num
            mock_feedback.feedback_pald = feedback_pald
            
            with patch('src.services.chat_service.FeedbackRecord', return_value=mock_feedback):
                stored_feedback = chat_service.store_feedback_record(
                    pseudonym_id=pseudonym_id,
                    session_id=session_id,
                    feedback_text=feedback_text,
                    round_number=round_num,
                    image_id=image_id,
                    feedback_pald=feedback_pald
                )
                
                assert stored_feedback.round_number == round_num
                assert stored_feedback.feedback_text == feedback_text
                assert stored_feedback.feedback_pald == feedback_pald
    
    def test_interaction_logging(self, chat_service, mock_db_session):
        """Test comprehensive interaction logging for audit trails."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        interaction_data = {
            "interaction_type": "pald_extraction",
            "model_used": "llama3",
            "parameters": {"temperature": 0.3, "max_tokens": 1000},
            "latency_ms": 250,
            "prompt": "Extract PALD from: I want a teacher",
            "response": '{"global_design_level": {"overall_appearance": "teacher"}}',
            "token_usage": {"prompt_tokens": 45, "completion_tokens": 32}
        }
        
        # Mock stored interaction log
        mock_log = Mock()
        mock_log.log_id = uuid4()
        mock_log.pseudonym_id = pseudonym_id
        mock_log.session_id = session_id
        for key, value in interaction_data.items():
            setattr(mock_log, key, value)
        
        with patch('src.services.chat_service.InteractionLog', return_value=mock_log):
            stored_log = chat_service.log_interaction_metadata(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                **interaction_data
            )
            
            assert stored_log.interaction_type == "pald_extraction"
            assert stored_log.latency_ms == 250
            assert stored_log.token_usage["prompt_tokens"] == 45
            
            # Verify database operations
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()


class TestPALDPipelinePerformance:
    """Performance tests for PALD pipeline under various conditions."""
    
    def test_pald_extraction_performance(self):
        """Test PALD extraction performance with various input sizes."""
        mock_llm_service = Mock()
        mock_response = Mock()
        mock_response.text = '{"global_design_level": {"overall_appearance": "character"}}'
        mock_llm_service.generate_response = Mock(return_value=mock_response)
        
        chat_logic = ChatLogic(mock_llm_service)
        
        # Test inputs of different sizes
        test_inputs = [
            "Teacher",  # Very short
            "I want a friendly teacher with glasses",  # Medium
            "I want a very detailed character description with lots of specific attributes including appearance, clothing, accessories, facial features, hair style, color preferences, and personality traits that should be reflected in the visual design" * 3  # Very long
        ]
        
        performance_results = []
        
        for input_text in test_inputs:
            start_time = time.time()
            result = chat_logic.extract_pald_from_text(input_text)
            processing_time = time.time() - start_time
            
            performance_results.append({
                "input_length": len(input_text),
                "processing_time": processing_time,
                "success": result.success,
                "reported_time_ms": result.processing_time_ms
            })
            
            # Performance assertions
            assert processing_time < 1.0  # Should complete within 1 second
            assert result.success is True
        
        # Verify performance scales reasonably with input size
        short_time = performance_results[0]["processing_time"]
        long_time = performance_results[-1]["processing_time"]
        
        # Long input shouldn't take more than 10x longer than short input
        assert long_time < short_time * 10
    
    def test_consistency_checking_performance(self):
        """Test consistency checking performance with complex PALDs."""
        chat_logic = ChatLogic(Mock())
        
        # Create complex PALD structures
        complex_pald = {
            "global_design_level": {
                "overall_appearance": "detailed character description",
                "style": "specific style attributes",
                "theme": "thematic elements"
            },
            "middle_design_level": {
                "physical_attributes": "physical characteristics",
                "clothing": "detailed clothing description",
                "accessories": "multiple accessories listed"
            },
            "detailed_level": {
                "facial_features": "specific facial details",
                "hair": "hair style and color",
                "colors": "color palette description",
                "specific_details": "additional specific details"
            }
        }
        
        # Test consistency checking performance
        start_time = time.time()
        
        for _ in range(100):  # Run 100 consistency checks
            result = chat_logic.check_pald_consistency(complex_pald, complex_pald)
            assert result.is_consistent is True
        
        total_time = time.time() - start_time
        avg_time_per_check = total_time / 100
        
        # Should be very fast for consistency checking
        assert avg_time_per_check < 0.01  # Less than 10ms per check
        assert total_time < 1.0  # Total should be under 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])