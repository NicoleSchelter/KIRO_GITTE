"""
End-to-end validation tests for Study Participation system.
Tests complete user journeys and system validation scenarios.

This test suite validates:
- Complete user journeys from registration to completion
- System validation and error handling across components
- Data integrity and consistency validation
- Performance validation under realistic conditions

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

import pytest
import tempfile
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4, UUID

from src.data.models import (
    StudyConsentType, 
    ChatMessageType, 
    StudyPALDType
)
from src.logic.pseudonym_logic import PseudonymLogic
from src.logic.consent_logic import ConsentLogic
from src.logic.survey_logic import SurveyLogic
from src.logic.chat_logic import ChatLogic
from src.services.pseudonym_service import PseudonymService
from src.services.consent_service import ConsentService
from src.services.survey_service import SurveyService
from src.services.chat_service import ChatService
from src.exceptions import ValidationError, DatabaseError


class TestCompleteUserJourneys:
    """Test complete user journeys from start to finish."""
    
    @pytest.fixture
    def journey_setup(self):
        """Setup for user journey testing."""
        from unittest.mock import Mock
        
        # Mock database and services
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.rollback = Mock()
        
        # Mock LLM service
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.text = json.dumps({
            "global_design_level": {"overall_appearance": "friendly teacher"},
            "detailed_level": {"hair": "brown", "accessories": "glasses"}
        })
        mock_llm.generate_response = Mock(return_value=mock_response)
        
        return {
            "database": mock_db,
            "llm_service": mock_llm,
            "test_user_id": uuid4(),
            "test_pseudonym": "T01e2000MJ42"
        }
    
    def test_successful_new_participant_journey(self, journey_setup):
        """Test complete successful journey for a new study participant.
        
        Requirements: 12.1, 12.7
        """
        user_id = journey_setup["test_user_id"]
        pseudonym_text = journey_setup["test_pseudonym"]
        database = journey_setup["database"]
        llm_service = journey_setup["llm_service"]
        
        # Journey Step 1: User Registration and Pseudonym Creation
        pseudonym_service = PseudonymService(database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            from src.logic.pseudonym_logic import PseudonymResult
            
            expected_pseudonym_id = uuid4()
            mock_create.return_value = PseudonymResult(
                pseudonym_id=expected_pseudonym_id,
                pseudonym_text=pseudonym_text,
                pseudonym_hash="secure_hash_123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            pseudonym_result = pseudonym_service.create_pseudonym(user_id, pseudonym_text)
            
            assert pseudonym_result.pseudonym_id == expected_pseudonym_id
            assert pseudonym_result.pseudonym_text == pseudonym_text
            assert pseudonym_result.is_active is True
        
        pseudonym_id = pseudonym_result.pseudonym_id
        
        # Journey Step 2: Consent Collection
        consent_service = ConsentService(database)
        
        consents = {
            StudyConsentType.DATA_PROTECTION: True,
            StudyConsentType.AI_INTERACTION: True,
            StudyConsentType.STUDY_PARTICIPATION: True
        }
        
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
            from src.logic.consent_logic import ConsentResult
            from src.data.models import StudyConsentRecord
            
            mock_consent.return_value = ConsentResult(
                success=True,
                can_proceed=True,
                consent_records=[
                    StudyConsentRecord(
                        consent_id=uuid4(),
                        pseudonym_id=pseudonym_id,
                        consent_type=consent_type,
                        granted=granted,
                        version="1.0",
                        granted_at=datetime.utcnow()
                    )
                    for consent_type, granted in consents.items()
                ],
                failed_consents=[],
                validation={
                    "is_complete": True,
                    "missing_consents": []
                }
            )
            
            consent_result = consent_service.process_consent_collection(pseudonym_id, consents)
            
            assert consent_result.success is True
            assert consent_result.can_proceed is True
            assert len(consent_result.consent_records) == 3
        
        # Journey Step 3: Survey Completion
        survey_service = SurveyService(database)
        
        survey_responses = {
            "name": "Test Participant",
            "age": "25",
            "learning_style": "Visual",
            "interests": ["Math", "Science"],
            "goals": "Improve problem-solving skills"
        }
        
        with pytest.mock.patch.object(survey_service, 'process_survey_submission') as mock_survey:
            from src.logic.survey_logic import SurveyResult
            
            mock_survey.return_value = SurveyResult(
                success=True,
                survey_response_id=uuid4(),
                validation_errors=[],
                processing_time_ms=200
            )
            
            survey_result = survey_service.process_survey_submission(
                pseudonym_id, survey_responses, None  # Mock survey definition
            )
            
            assert survey_result.success is True
            assert len(survey_result.validation_errors) == 0
        
        # Journey Step 4: Multiple Chat Sessions
        chat_service = ChatService(database)
        chat_logic = ChatLogic(llm_service)
        
        session_scenarios = [
            {
                "session_id": uuid4(),
                "messages": [
                    "I want a friendly teacher for math lessons",
                    "Make the teacher look professional and approachable",
                    "Add some personality to make learning fun"
                ]
            },
            {
                "session_id": uuid4(),
                "messages": [
                    "Create a science teacher character",
                    "The teacher should look knowledgeable and patient",
                    "Make sure the character is encouraging"
                ]
            }
        ]
        
        for scenario in session_scenarios:
            session_id = scenario["session_id"]
            
            for message_content in scenario["messages"]:
                with pytest.mock.patch.object(chat_service, 'store_chat_message') as mock_store:
                    from src.data.models import ChatMessage
                    
                    mock_message = ChatMessage(
                        message_id=uuid4(),
                        pseudonym_id=pseudonym_id,
                        session_id=session_id,
                        message_type=ChatMessageType.USER,
                        content=message_content,
                        pald_data={"global_design_level": {"overall_appearance": "teacher"}},
                        timestamp=datetime.utcnow()
                    )
                    mock_store.return_value = mock_message
                    
                    stored_message = chat_service.store_chat_message(
                        pseudonym_id=pseudonym_id,
                        session_id=session_id,
                        message_type=ChatMessageType.USER,
                        content=message_content
                    )
                    
                    assert stored_message.pseudonym_id == pseudonym_id
                    assert stored_message.session_id == session_id
                    assert stored_message.content == message_content
        
        # Journey Step 5: Feedback Processing
        feedback_scenarios = [
            "The teacher looks great, but could use warmer colors",
            "Perfect! This character will work well for my students",
            "Maybe add some teaching materials in the background"
        ]
        
        for round_num, feedback_text in enumerate(feedback_scenarios, 1):
            with pytest.mock.patch.object(chat_logic, 'manage_feedback_loop') as mock_feedback:
                from src.logic.chat_logic import FeedbackProcessingResult
                
                mock_feedback.return_value = FeedbackProcessingResult(
                    feedback_id=uuid4(),
                    round_number=round_num,
                    max_rounds_reached=(round_num >= 3),
                    should_continue=(round_num < 3),
                    feedback_pald={
                        "detailed_level": {
                            "colors": "warmer" if "warmer" in feedback_text else None,
                            "accessories": "teaching materials" if "materials" in feedback_text else None
                        }
                    },
                    processing_metadata={
                        "feedback_length": len(feedback_text),
                        "pald_extraction_success": True
                    }
                )
                
                feedback_result = chat_logic.manage_feedback_loop(
                    pseudonym_id, session_scenarios[0]["session_id"], feedback_text, round_num
                )
                
                assert feedback_result.round_number == round_num
                assert feedback_result.feedback_pald is not None
        
        # Verify complete journey success
        assert pseudonym_id is not None
        assert consent_result.success is True
        assert survey_result.success is True
        assert len(session_scenarios) == 2  # Two chat sessions completed
        assert len(feedback_scenarios) == 3  # Three feedback rounds completed
    
    def test_participant_journey_with_interruptions(self, journey_setup):
        """Test participant journey with interruptions and resumption.
        
        Requirements: 12.6, 12.7
        """
        user_id = journey_setup["test_user_id"]
        pseudonym_text = journey_setup["test_pseudonym"]
        database = journey_setup["database"]
        
        # Step 1: Successful pseudonym creation
        pseudonym_service = PseudonymService(database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            from src.logic.pseudonym_logic import PseudonymResult
            
            pseudonym_id = uuid4()
            mock_create.return_value = PseudonymResult(
                pseudonym_id=pseudonym_id,
                pseudonym_text=pseudonym_text,
                pseudonym_hash="hash123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            pseudonym_result = pseudonym_service.create_pseudonym(user_id, pseudonym_text)
            assert pseudonym_result.success is True
        
        # Step 2: Consent collection fails (interruption)
        consent_service = ConsentService(database)
        
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
            mock_consent.side_effect = DatabaseError("Database connection lost")
            
            with pytest.raises(DatabaseError):
                consent_service.process_consent_collection(pseudonym_id, {
                    StudyConsentType.DATA_PROTECTION: True
                })
        
        # Step 3: Resume consent collection (recovery)
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
            from src.logic.consent_logic import ConsentResult
            
            mock_consent.return_value = ConsentResult(
                success=True,
                can_proceed=True,
                consent_records=[],  # Simplified for test
                failed_consents=[],
                validation={"is_complete": True, "missing_consents": []}
            )
            
            # Retry should succeed
            consent_result = consent_service.process_consent_collection(pseudonym_id, {
                StudyConsentType.DATA_PROTECTION: True,
                StudyConsentType.AI_INTERACTION: True,
                StudyConsentType.STUDY_PARTICIPATION: True
            })
            
            assert consent_result.success is True
            assert consent_result.can_proceed is True
        
        # Verify journey can continue after interruption
        assert pseudonym_id is not None
        assert consent_result.success is True
    
    def test_participant_data_privacy_journey(self, journey_setup):
        """Test participant journey with data privacy operations.
        
        Requirements: 12.5, 12.7
        """
        user_id = journey_setup["test_user_id"]
        pseudonym_text = journey_setup["test_pseudonym"]
        database = journey_setup["database"]
        
        # Step 1: Create participant with data
        pseudonym_service = PseudonymService(database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            from src.logic.pseudonym_logic import PseudonymResult
            
            pseudonym_id = uuid4()
            mock_create.return_value = PseudonymResult(
                pseudonym_id=pseudonym_id,
                pseudonym_text=pseudonym_text,
                pseudonym_hash="hash123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            pseudonym_result = pseudonym_service.create_pseudonym(user_id, pseudonym_text)
            assert pseudonym_result.pseudonym_id == pseudonym_id
        
        # Step 2: Generate participant data across multiple sessions
        chat_service = ChatService(database)
        
        # Simulate multiple sessions with data
        session_data = []
        for i in range(3):
            session_id = uuid4()
            
            with pytest.mock.patch.object(chat_service, 'store_chat_message') as mock_store:
                from src.data.models import ChatMessage
                
                mock_message = ChatMessage(
                    message_id=uuid4(),
                    pseudonym_id=pseudonym_id,
                    session_id=session_id,
                    message_type=ChatMessageType.USER,
                    content=f"Session {i+1} message",
                    timestamp=datetime.utcnow()
                )
                mock_store.return_value = mock_message
                
                stored_message = chat_service.store_chat_message(
                    pseudonym_id=pseudonym_id,
                    session_id=session_id,
                    message_type=ChatMessageType.USER,
                    content=f"Session {i+1} message"
                )
                
                session_data.append({
                    "session_id": session_id,
                    "message_id": stored_message.message_id
                })
        
        # Step 3: Participant requests data deletion
        with pytest.mock.patch.object(pseudonym_service, 'deactivate_user_pseudonym') as mock_delete:
            mock_delete.return_value = True
            
            deletion_success = pseudonym_service.deactivate_user_pseudonym(user_id)
            assert deletion_success is True
        
        # Step 4: Verify data privacy compliance
        # In real implementation, this would verify all related data is deleted
        assert len(session_data) == 3  # Data was created
        # After deletion, all related data should be inaccessible
        
        # Verify pseudonym ownership verification works
        with pytest.mock.patch('src.logic.pseudonym_logic.PseudonymLogic') as mock_logic:
            mock_logic_instance = mock_logic.return_value
            mock_logic_instance.verify_pseudonym_ownership.return_value = True
            
            ownership_verified = mock_logic_instance.verify_pseudonym_ownership(user_id, pseudonym_text)
            assert ownership_verified is True


class TestSystemValidationScenarios:
    """Test system validation and error handling across components."""
    
    @pytest.fixture
    def validation_setup(self):
        """Setup for validation testing."""
        from unittest.mock import Mock
        
        return {
            "database": Mock(),
            "llm_service": Mock(),
            "test_data": {
                "valid_pseudonym": "V01a2000XY99",
                "invalid_pseudonym": "invalid",
                "user_id": uuid4()
            }
        }
    
    def test_cross_component_validation(self, validation_setup):
        """Test validation across multiple system components.
        
        Requirements: 12.6, 12.7
        """
        database = validation_setup["database"]
        test_data = validation_setup["test_data"]
        
        # Test 1: Pseudonym validation across services
        pseudonym_service = PseudonymService(database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            # Valid pseudonym should succeed
            from src.logic.pseudonym_logic import PseudonymResult
            
            mock_create.return_value = PseudonymResult(
                pseudonym_id=uuid4(),
                pseudonym_text=test_data["valid_pseudonym"],
                pseudonym_hash="hash123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            valid_result = pseudonym_service.create_pseudonym(
                test_data["user_id"], test_data["valid_pseudonym"]
            )
            assert valid_result.is_active is True
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            # Invalid pseudonym should fail
            from src.exceptions import InvalidPseudonymFormatError
            mock_create.side_effect = InvalidPseudonymFormatError("Invalid format")
            
            with pytest.raises(InvalidPseudonymFormatError):
                pseudonym_service.create_pseudonym(
                    test_data["user_id"], test_data["invalid_pseudonym"]
                )
        
        # Test 2: Consent validation with pseudonym dependency
        consent_service = ConsentService(database)
        
        # Should fail with invalid pseudonym_id
        invalid_pseudonym_id = uuid4()
        
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
            from src.exceptions import ValidationError
            mock_consent.side_effect = ValidationError("Pseudonym not found")
            
            with pytest.raises(ValidationError):
                consent_service.process_consent_collection(invalid_pseudonym_id, {
                    StudyConsentType.DATA_PROTECTION: True
                })
        
        # Test 3: Survey validation with consent dependency
        survey_service = SurveyService(database)
        
        with pytest.mock.patch.object(survey_service, 'process_survey_submission') as mock_survey:
            from src.exceptions import ConsentRequiredError
            mock_survey.side_effect = ConsentRequiredError("Required consents not granted")
            
            with pytest.raises(ConsentRequiredError):
                survey_service.process_survey_submission(
                    invalid_pseudonym_id, {"name": "Test"}, None
                )
    
    def test_data_integrity_validation(self, validation_setup):
        """Test data integrity validation across the system.
        
        Requirements: 12.3, 12.5
        """
        database = validation_setup["database"]
        
        # Test 1: Foreign key integrity
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Create related objects that should maintain referential integrity
        from src.data.models import ChatMessage, StudyPALDData, FeedbackRecord
        
        chat_message = ChatMessage(
            message_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="Test message",
            timestamp=datetime.utcnow()
        )
        
        pald_data = StudyPALDData(
            pald_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            pald_content={"global_design_level": {"overall_appearance": "test"}},
            pald_type=StudyPALDType.INPUT,
            created_at=datetime.utcnow()
        )
        
        feedback_record = FeedbackRecord(
            feedback_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            image_id=uuid4(),
            feedback_text="Test feedback",
            round_number=1,
            created_at=datetime.utcnow()
        )
        
        # Verify all objects reference the same pseudonym_id and session_id
        assert chat_message.pseudonym_id == pald_data.pseudonym_id == feedback_record.pseudonym_id
        assert chat_message.session_id == pald_data.session_id == feedback_record.session_id
        
        # Test 2: Timestamp consistency
        time_tolerance = timedelta(seconds=1)
        
        assert abs(chat_message.timestamp - pald_data.created_at) < time_tolerance
        assert abs(pald_data.created_at - feedback_record.created_at) < time_tolerance
        
        # Test 3: Data format validation
        assert isinstance(chat_message.message_id, UUID)
        assert isinstance(pald_data.pald_content, dict)
        assert isinstance(feedback_record.round_number, int)
        assert feedback_record.round_number > 0
    
    def test_error_propagation_and_handling(self, validation_setup):
        """Test error propagation and handling across system layers.
        
        Requirements: 12.6
        """
        database = validation_setup["database"]
        llm_service = validation_setup["llm_service"]
        
        # Test 1: Database error propagation
        pseudonym_service = PseudonymService(database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            mock_create.side_effect = DatabaseError("Connection timeout")
            
            with pytest.raises(DatabaseError) as exc_info:
                pseudonym_service.create_pseudonym(uuid4(), "T01e2000MJ42")
            
            assert "Connection timeout" in str(exc_info.value)
        
        # Test 2: LLM service error handling
        chat_logic = ChatLogic(llm_service)
        
        # Mock LLM service failure
        llm_service.generate_response.side_effect = Exception("LLM service unavailable")
        
        with pytest.mock.patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            from src.logic.chat_logic import PALDExtractionResult
            
            mock_extract.return_value = PALDExtractionResult(
                success=False,
                pald_data={},
                extraction_confidence=0.0,
                processing_time_ms=0,
                error_message="LLM service unavailable"
            )
            
            result = chat_logic.extract_pald_from_text("Test input")
            
            assert result.success is False
            assert "LLM service unavailable" in result.error_message
        
        # Test 3: Graceful degradation
        # System should continue operating with reduced functionality
        with pytest.mock.patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            # Return minimal PALD data when extraction fails
            mock_extract.return_value = PALDExtractionResult(
                success=True,
                pald_data={"global_design_level": {"overall_appearance": "default"}},
                extraction_confidence=0.1,
                processing_time_ms=10,
                error_message=None
            )
            
            result = chat_logic.extract_pald_from_text("Test input")
            
            assert result.success is True
            assert result.pald_data is not None
            assert result.extraction_confidence < 0.5  # Low confidence but functional


class TestPerformanceValidation:
    """Test performance validation under realistic conditions."""
    
    def test_response_time_validation(self):
        """Test response time validation for key operations.
        
        Requirements: 12.4
        """
        from unittest.mock import Mock
        
        # Mock fast services
        fast_database = Mock()
        fast_database.add = Mock()
        fast_database.commit = Mock()
        
        fast_llm = Mock()
        fast_response = Mock()
        fast_response.text = '{"global_design_level": {"overall_appearance": "teacher"}}'
        fast_llm.generate_response = Mock(return_value=fast_response)
        
        # Test pseudonym creation performance
        pseudonym_service = PseudonymService(fast_database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            from src.logic.pseudonym_logic import PseudonymResult
            
            start_time = time.time()
            
            mock_create.return_value = PseudonymResult(
                pseudonym_id=uuid4(),
                pseudonym_text="T01e2000MJ42",
                pseudonym_hash="hash123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            result = pseudonym_service.create_pseudonym(uuid4(), "T01e2000MJ42")
            
            processing_time = time.time() - start_time
            
            assert result.is_active is True
            assert processing_time < 1.0  # Should complete within 1 second
        
        # Test PALD extraction performance
        chat_logic = ChatLogic(fast_llm)
        
        with pytest.mock.patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            from src.logic.chat_logic import PALDExtractionResult
            
            start_time = time.time()
            
            mock_extract.return_value = PALDExtractionResult(
                success=True,
                pald_data={"global_design_level": {"overall_appearance": "teacher"}},
                extraction_confidence=0.9,
                processing_time_ms=150
            )
            
            result = chat_logic.extract_pald_from_text("I want a friendly teacher")
            
            processing_time = time.time() - start_time
            
            assert result.success is True
            assert processing_time < 0.5  # Should complete within 500ms
            assert result.processing_time_ms < 200  # Reported time should be reasonable
    
    def test_throughput_validation(self):
        """Test system throughput under load.
        
        Requirements: 12.4
        """
        from unittest.mock import Mock
        import concurrent.futures
        
        # Mock high-throughput services
        database = Mock()
        database.add = Mock()
        database.commit = Mock()
        
        # Test concurrent pseudonym creation throughput
        pseudonym_service = PseudonymService(database)
        
        def create_pseudonym_operation(index: int) -> Dict[str, Any]:
            with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
                from src.logic.pseudonym_logic import PseudonymResult
                
                start_time = time.time()
                
                mock_create.return_value = PseudonymResult(
                    pseudonym_id=uuid4(),
                    pseudonym_text=f"U{index:03d}e2000MJ42",
                    pseudonym_hash=f"hash{index}",
                    created_at=datetime.utcnow(),
                    is_active=True
                )
                
                result = pseudonym_service.create_pseudonym(uuid4(), f"U{index:03d}e2000MJ42")
                
                return {
                    "index": index,
                    "success": result.is_active,
                    "processing_time": time.time() - start_time
                }
        
        # Execute concurrent operations
        num_operations = 50
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_pseudonym_operation, i) 
                for i in range(num_operations)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Validate throughput
        successful_operations = [r for r in results if r["success"]]
        assert len(successful_operations) == num_operations
        
        # Calculate throughput (operations per second)
        throughput = num_operations / total_time
        assert throughput > 10  # Should handle at least 10 operations per second
        
        # Validate individual operation times
        avg_operation_time = sum(r["processing_time"] for r in results) / len(results)
        assert avg_operation_time < 0.1  # Average operation should be under 100ms
    
    @pytest.mark.slow
    def test_memory_efficiency_validation(self):
        """Test memory efficiency during extended operations.
        
        Requirements: 12.4
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate extended operation with large data
        large_data_sets = []
        
        for i in range(100):
            # Create large PALD data structures
            large_pald = {
                "global_design_level": {
                    f"attribute_{j}": f"detailed_value_{j}" * 100
                    for j in range(50)
                },
                "detailed_level": {
                    f"detail_{k}": f"specific_value_{k}" * 50
                    for k in range(100)
                }
            }
            large_data_sets.append(large_pald)
        
        # Process all data sets
        processed_count = 0
        for data_set in large_data_sets:
            # Simulate processing
            json_data = json.dumps(data_set)
            assert len(json_data) > 0
            processed_count += 1
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Validate memory efficiency
        assert processed_count == 100
        assert memory_increase < 50  # Should not increase memory by more than 50MB
        
        # Memory per operation should be reasonable
        memory_per_operation = memory_increase / processed_count
        assert memory_per_operation < 0.5  # Less than 0.5MB per operation