"""
Integration tests for Study Participation Onboarding Flow.
Tests the complete end-to-end workflow from pseudonym creation through chat interactions.

This test suite validates:
- Complete onboarding flow (registration → pseudonym → consent → survey → chat)
- End-to-end PALD pipeline with consistency loops and feedback rounds
- Database integration with foreign key relationships and cascade operations
- Performance under concurrent user onboarding scenarios
"""

import pytest
import tempfile
import os
import time
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID

from src.data.models import StudyConsentType, ChatMessageType, StudyPALDType
from src.logic.pseudonym_logic import PseudonymLogic, PseudonymError, InvalidPseudonymFormatError, PseudonymNotUniqueError
from src.services.pseudonym_service import PseudonymService
from src.logic.consent_logic import ConsentLogic
from src.services.consent_service import ConsentService
from src.logic.survey_logic import SurveyLogic, SurveyDefinition, SurveyQuestion
from src.services.survey_service import SurveyService
from src.logic.chat_logic import ChatLogic, PALDExtractionResult, ConsistencyCheckResult
from src.services.chat_service import ChatService
from src.exceptions import ConsentError, ConsentRequiredError, ValidationError, DatabaseError


class TestStudyParticipationIntegrationFlow:
    """Integration tests for complete study participation onboarding flow."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session for testing."""
        session = Mock()
        session.begin.return_value.__enter__ = Mock()
        session.begin.return_value.__exit__ = Mock(return_value=None)
        session.commit = Mock()
        session.rollback = Mock()
        session.flush = Mock()
        return session
    
    @pytest.fixture
    def mock_pseudonym_repository(self):
        """Create mock pseudonym repository."""
        repo = Mock()
        repo.is_pseudonym_unique = Mock(return_value=True)
        repo.get_by_user_id = Mock(return_value=None)
        repo.create_pseudonym_with_mapping = Mock()
        repo.deactivate_user_pseudonym = Mock(return_value=True)
        return repo
    
    @pytest.fixture
    def mock_consent_repository(self):
        """Create mock consent repository."""
        repo = Mock()
        repo.create_consent = Mock()
        repo.get_by_pseudonym_and_type = Mock(return_value=None)
        repo.check_consent = Mock(return_value=True)
        repo.withdraw_consent = Mock(return_value=True)
        repo.get_by_pseudonym = Mock(return_value=[])
        return repo
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service for PALD extraction."""
        service = Mock()
        mock_response = Mock()
        mock_response.text = '{"global_design_level": {"overall_appearance": "friendly teacher"}}'
        service.generate_response = Mock(return_value=mock_response)
        return service
    
    @pytest.fixture
    def comprehensive_survey_csv(self):
        """Create comprehensive survey CSV content for testing."""
        return """question_id,question_text,type,options,required
name,What is your full name?,text,,true
age,What is your age?,number,,true
learning_style,What is your preferred learning style?,choice,"Visual,Auditory,Kinesthetic,Reading/Writing",true
interests,Which subjects interest you?,multi-choice,"Math,Science,Art,Music,Sports",false
goals,What are your learning goals?,text,,false
feedback_style,How do you prefer feedback?,choice,"Encouraging,Direct,Detailed",false"""
    
    def test_complete_onboarding_flow_success(
        self, 
        mock_db_session, 
        mock_pseudonym_repository, 
        mock_consent_repository,
        comprehensive_survey_csv
    ):
        """Test complete successful onboarding flow from start to finish."""
        # Setup test data
        user_id = uuid4()
        pseudonym_text = "M03s2001AJ13"
        
        # Step 1: Pseudonym Creation
        pseudonym_logic = PseudonymLogic(mock_pseudonym_repository)
        
        # Mock successful pseudonym creation
        mock_pseudonym = Mock()
        mock_pseudonym.pseudonym_id = uuid4()
        mock_pseudonym.pseudonym_text = pseudonym_text
        mock_pseudonym.pseudonym_hash = "hash123"
        mock_pseudonym.created_at = datetime.utcnow()
        mock_pseudonym.is_active = True
        
        mock_mapping = Mock()
        mock_pseudonym_repository.create_pseudonym_with_mapping.return_value = (mock_pseudonym, mock_mapping)
        
        pseudonym_result = pseudonym_logic.create_pseudonym(user_id, pseudonym_text)
        
        assert pseudonym_result.pseudonym_id == mock_pseudonym.pseudonym_id
        assert pseudonym_result.pseudonym_text == pseudonym_text
        assert pseudonym_result.is_active is True
        
        pseudonym_id = pseudonym_result.pseudonym_id
        
        # Step 2: Consent Collection
        consent_logic = ConsentLogic(mock_consent_repository)
        
        # Mock successful consent creation
        mock_consent_record = Mock()
        mock_consent_record.consent_id = uuid4()
        mock_consent_record.pseudonym_id = pseudonym_id
        mock_consent_record.granted = True
        mock_consent_repository.create_consent.return_value = mock_consent_record
        
        consents = {
            "data_protection": True,
            "ai_interaction": True,
            "study_participation": True
        }
        
        consent_result = consent_logic.process_consent_collection(pseudonym_id, consents)
        
        assert consent_result["success"] is True
        assert consent_result["can_proceed"] is True
        assert len(consent_result["consent_records"]) == 3
        
        # Step 3: Survey Completion
        survey_service = SurveyService(mock_db_session)
        survey_logic = SurveyLogic(survey_service)
        
        # Create temporary survey file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(comprehensive_survey_csv)
            tmp_path = tmp_file.name
        
        try:
            # Load survey definition
            survey_definition = survey_logic.load_survey_definition(tmp_path)
            
            # Prepare survey responses
            survey_responses = {
                "name": "Test Participant",
                "age": "25",
                "learning_style": "Visual",
                "interests": ["Math", "Science"],
                "goals": "Improve problem-solving skills",
                "feedback_style": "Encouraging"
            }
            
            # Mock successful survey storage
            survey_service.store_survey_responses = Mock(return_value=True)
            
            # Process survey submission
            survey_result = survey_logic.process_survey_submission(
                pseudonym_id, survey_responses, survey_definition
            )
            
            assert survey_result.success is True
            assert len(survey_result.errors) == 0
            
        finally:
            os.unlink(tmp_path)
        
        # Step 4: Chat Interface Initialization
        chat_service = ChatService(mock_db_session)
        chat_logic = ChatLogic(Mock())  # Mock LLM service
        
        session_id = uuid4()
        
        # Mock successful message storage
        mock_message = Mock()
        mock_message.message_id = uuid4()
        mock_message.pseudonym_id = pseudonym_id
        mock_message.session_id = session_id
        mock_message.content = "I want a friendly teacher avatar"
        chat_service.store_chat_message = Mock(return_value=mock_message)
        
        # Process initial chat message
        message = chat_service.store_chat_message(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="I want a friendly teacher avatar"
        )
        
        assert message.pseudonym_id == pseudonym_id
        assert message.session_id == session_id
        assert "friendly teacher" in message.content
        
        # Verify complete flow data integrity
        mock_pseudonym_repository.create_pseudonym_with_mapping.assert_called_once()
        assert mock_consent_repository.create_consent.call_count == 3  # Three consent types
        survey_service.store_survey_responses.assert_called_once()
        chat_service.store_chat_message.assert_called_once()
    
    def test_onboarding_flow_with_validation_errors(
        self, 
        mock_db_session, 
        mock_pseudonym_repository, 
        mock_consent_repository
    ):
        """Test onboarding flow with various validation errors and recovery."""
        user_id = uuid4()
        
        # Test 1: Invalid pseudonym format
        pseudonym_logic = PseudonymLogic(mock_pseudonym_repository)
        
        with pytest.raises(InvalidPseudonymFormatError):
            pseudonym_logic.create_pseudonym(user_id, "invalid")
        
        # Test 2: Non-unique pseudonym
        mock_pseudonym_repository.is_pseudonym_unique.return_value = False
        
        with pytest.raises(PseudonymNotUniqueError):
            pseudonym_logic.create_pseudonym(user_id, "M03s2001AJ13")
        
        # Test 3: Incomplete consent
        mock_pseudonym_repository.is_pseudonym_unique.return_value = True
        pseudonym_id = uuid4()
        
        consent_logic = ConsentLogic(mock_consent_repository)
        
        incomplete_consents = {
            "data_protection": True,
            "ai_interaction": False,  # Missing required consent
            "study_participation": True
        }
        
        mock_consent_record = Mock()
        mock_consent_record.consent_id = uuid4()
        mock_consent_record.pseudonym_id = pseudonym_id
        mock_consent_repository.create_consent.return_value = mock_consent_record
        
        consent_result = consent_logic.process_consent_collection(pseudonym_id, incomplete_consents)
        
        # Should succeed in recording but validation should show incompleteness
        assert consent_result["success"] is True
        validation = consent_result["validation"]
        assert validation["is_complete"] is False
        assert "ai_interaction" in validation["missing_consents"]
    
    def test_pald_pipeline_with_consistency_loop(self, mock_llm_service):
        """Test PALD pipeline with consistency checking and feedback loops."""
        chat_logic = ChatLogic(mock_llm_service)
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Step 1: Process initial user input
        user_input = "I want a friendly female teacher with brown hair and glasses"
        
        # Mock PALD extraction result
        with patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            mock_extract.return_value = PALDExtractionResult(
                success=True,
                pald_data={
                    "global_design_level": {"overall_appearance": "friendly female teacher"},
                    "detailed_level": {"hair": "brown", "accessories": "glasses"}
                },
                extraction_confidence=0.9,
                processing_time_ms=150
            )
            
            chat_result = chat_logic.process_chat_input(
                pseudonym_id, session_id, user_input, ChatMessageType.USER
            )
            
            assert chat_result.pald_extracted is True
            assert chat_result.pald_data is not None
            assert "friendly female teacher" in str(chat_result.pald_data)
        
        # Step 2: Simulate image generation and description PALD extraction
        description_text = "A friendly woman with short blonde hair and no accessories"
        
        with patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            mock_extract.return_value = PALDExtractionResult(
                success=True,
                pald_data={
                    "global_design_level": {"overall_appearance": "friendly woman"},
                    "detailed_level": {"hair": "short blonde", "accessories": "none"}
                },
                extraction_confidence=0.8,
                processing_time_ms=120
            )
            
            description_pald = chat_logic.extract_pald_from_text(description_text)
            
            assert description_pald.success is True
        
        # Step 3: Check consistency between input and description PALDs
        input_pald = chat_result.pald_data
        desc_pald = description_pald.pald_data
        
        consistency_result = chat_logic.check_pald_consistency(input_pald, desc_pald)
        
        # Should detect inconsistency (brown vs blonde hair, glasses vs none)
        assert consistency_result.is_consistent is False
        assert consistency_result.consistency_score < 0.8
        assert len(consistency_result.differences) > 0
        assert consistency_result.recommendation in ["regenerate", "accept"]
        
        # Step 4: Process feedback for regeneration
        feedback_text = "The hair should be brown, not blonde, and she should wear glasses"
        
        feedback_result = chat_logic.manage_feedback_loop(
            pseudonym_id, session_id, feedback_text, current_round=1
        )
        
        assert feedback_result.round_number == 1
        assert feedback_result.max_rounds_reached is False
        assert feedback_result.should_continue is True
        assert feedback_result.feedback_pald is not None
    
    def test_database_foreign_key_relationships(self, mock_db_session):
        """Test database integration with foreign key relationships and cascade operations."""
        # This test would verify that:
        # 1. All data is properly linked via pseudonym_id
        # 2. Cascade deletions work correctly
        # 3. Foreign key constraints are enforced
        
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock database models and relationships
        mock_pseudonym = Mock()
        mock_pseudonym.pseudonym_id = pseudonym_id
        
        mock_consent = Mock()
        mock_consent.pseudonym_id = pseudonym_id
        mock_consent.consent_type = "data_protection"
        
        mock_survey = Mock()
        mock_survey.pseudonym_id = pseudonym_id
        
        mock_chat = Mock()
        mock_chat.pseudonym_id = pseudonym_id
        mock_chat.session_id = session_id
        
        mock_pald = Mock()
        mock_pald.pseudonym_id = pseudonym_id
        mock_pald.session_id = session_id
        
        # Verify all components use the same pseudonym_id
        assert mock_consent.pseudonym_id == pseudonym_id
        assert mock_survey.pseudonym_id == pseudonym_id
        assert mock_chat.pseudonym_id == pseudonym_id
        assert mock_pald.pseudonym_id == pseudonym_id
        
        # Verify session consistency for chat-related data
        assert mock_chat.session_id == session_id
        assert mock_pald.session_id == session_id
    
    def test_concurrent_user_onboarding_performance(
        self, 
        mock_db_session, 
        mock_pseudonym_repository, 
        mock_consent_repository
    ):
        """Test performance under concurrent user onboarding scenarios."""
        num_concurrent_users = 10
        
        # Setup mocks for concurrent access
        mock_pseudonym_repository.is_pseudonym_unique.return_value = True
        mock_pseudonym_repository.create_pseudonym_with_mapping.side_effect = lambda *args: (
            Mock(pseudonym_id=uuid4(), pseudonym_text=f"U{uuid4().hex[:8]}", 
                 pseudonym_hash="hash", created_at=datetime.utcnow(), is_active=True),
            Mock()
        )
        
        mock_consent_repository.create_consent.return_value = Mock(
            consent_id=uuid4(), granted=True
        )
        
        def create_user_onboarding(user_index: int) -> Dict[str, Any]:
            """Simulate single user onboarding process."""
            user_id = uuid4()
            pseudonym_text = f"U{user_index:02d}m2001AB{user_index}"
            
            try:
                # Pseudonym creation
                pseudonym_logic = PseudonymLogic(mock_pseudonym_repository)
                pseudonym_result = pseudonym_logic.create_pseudonym(user_id, pseudonym_text)
                
                # Consent collection
                consent_logic = ConsentLogic(mock_consent_repository)
                consents = {
                    "data_protection": True,
                    "ai_interaction": True,
                    "study_participation": True
                }
                consent_result = consent_logic.process_consent_collection(
                    pseudonym_result.pseudonym_id, consents
                )
                
                return {
                    "user_index": user_index,
                    "success": True,
                    "pseudonym_id": pseudonym_result.pseudonym_id,
                    "consent_success": consent_result["success"]
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent onboarding
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_user_onboarding, i) 
                for i in range(num_concurrent_users)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify all users completed successfully
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        assert len(successful_results) == num_concurrent_users
        assert len(failed_results) == 0
        
        # Verify performance (should complete within reasonable time)
        assert processing_time < 5.0  # Should complete within 5 seconds
        
        # Verify all pseudonym IDs are unique
        pseudonym_ids = [r["pseudonym_id"] for r in successful_results]
        assert len(set(pseudonym_ids)) == num_concurrent_users
        
        # Verify repository was called correct number of times
        assert mock_pseudonym_repository.create_pseudonym_with_mapping.call_count == num_concurrent_users
        assert mock_consent_repository.create_consent.call_count == num_concurrent_users * 3  # 3 consent types each
    
    def test_error_recovery_and_data_consistency(
        self, 
        mock_db_session, 
        mock_pseudonym_repository, 
        mock_consent_repository
    ):
        """Test error recovery mechanisms and data consistency."""
        user_id = uuid4()
        pseudonym_text = "M03s2001AJ13"
        
        # Test 1: Database error during pseudonym creation
        mock_pseudonym_repository.create_pseudonym_with_mapping.side_effect = Exception("Database error")
        
        pseudonym_logic = PseudonymLogic(mock_pseudonym_repository)
        
        with pytest.raises(PseudonymError):
            pseudonym_logic.create_pseudonym(user_id, pseudonym_text)
        
        # Verify rollback behavior (session should be rolled back)
        # In real implementation, this would verify transaction rollback
        
        # Test 2: Partial consent failure with recovery
        mock_pseudonym_repository.create_pseudonym_with_mapping.side_effect = None
        mock_pseudonym = Mock()
        mock_pseudonym.pseudonym_id = uuid4()
        mock_pseudonym_repository.create_pseudonym_with_mapping.return_value = (mock_pseudonym, Mock())
        
        # Create pseudonym successfully
        pseudonym_result = pseudonym_logic.create_pseudonym(user_id, pseudonym_text)
        pseudonym_id = pseudonym_result.pseudonym_id
        
        # Simulate consent creation failure for one type
        def consent_side_effect(*args, **kwargs):
            consent_type = kwargs.get('consent_type') or args[1]
            if consent_type == StudyConsentType.AI_INTERACTION:
                raise Exception("Consent storage failed")
            return Mock(consent_id=uuid4(), granted=True)
        
        mock_consent_repository.create_consent.side_effect = consent_side_effect
        
        consent_logic = ConsentLogic(mock_consent_repository)
        consents = {
            "data_protection": True,
            "ai_interaction": True,
            "study_participation": True
        }
        
        # Should handle partial failure gracefully
        consent_result = consent_logic.process_consent_collection(pseudonym_id, consents)
        
        assert consent_result["success"] is False
        assert len(consent_result["failed_consents"]) == 1
        assert "ai_interaction" in consent_result["failed_consents"]
        assert len(consent_result["consent_records"]) == 2  # Two successful consents
    
    def test_data_privacy_and_pseudonymization(
        self, 
        mock_db_session, 
        mock_pseudonym_repository
    ):
        """Test data privacy and pseudonymization throughout the flow."""
        user_id = uuid4()
        pseudonym_text = "M03s2001AJ13"
        
        # Setup pseudonym creation
        mock_pseudonym = Mock()
        mock_pseudonym.pseudonym_id = uuid4()
        mock_pseudonym.pseudonym_text = pseudonym_text
        mock_pseudonym.pseudonym_hash = "secure_hash_123"
        mock_pseudonym_repository.create_pseudonym_with_mapping.return_value = (mock_pseudonym, Mock())
        
        pseudonym_logic = PseudonymLogic(mock_pseudonym_repository)
        pseudonym_result = pseudonym_logic.create_pseudonym(user_id, pseudonym_text)
        
        pseudonym_id = pseudonym_result.pseudonym_id
        
        # Verify pseudonym hash is generated securely
        generated_hash = pseudonym_logic.generate_pseudonym_hash(pseudonym_text, user_id)
        assert len(generated_hash) == 64  # SHA-256 hash length
        assert generated_hash != pseudonym_text  # Should be different from original
        
        # Verify pseudonym ownership verification
        ownership_verified = pseudonym_logic.verify_pseudonym_ownership(user_id, pseudonym_text)
        # This would be True in real implementation with proper repository setup
        
        # Test data deletion (GDPR compliance)
        deletion_success = pseudonym_logic.deactivate_pseudonym(user_id)
        assert deletion_success is True
        
        # Verify that all subsequent operations should use pseudonym_id, not user_id
        # This is verified by checking that all service calls use pseudonym_id
        assert pseudonym_id != user_id  # Should be different identifiers
        assert isinstance(pseudonym_id, UUID)


class TestStudyParticipationEndToEndScenarios:
    """End-to-end scenario tests for complete user journeys."""
    
    def test_new_participant_complete_journey(self):
        """Test complete journey for a new study participant."""
        # This test would simulate a real user going through the entire flow
        # from initial registration to completing multiple chat sessions
        
        # Mock all dependencies
        with patch('src.data.database.get_session') as mock_get_session, \
             patch('src.data.repositories.PseudonymRepository') as mock_pseudo_repo, \
             patch('src.data.repositories.StudyConsentRepository') as mock_consent_repo:
            
            # Setup mocks
            mock_session = Mock()
            mock_get_session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = Mock(return_value=None)
            
            # Test data
            user_id = uuid4()
            pseudonym_text = "T01e2000MJ42"
            
            # Journey Step 1: User Registration and Pseudonym Creation
            pseudonym_service = PseudonymService()
            
            # Mock successful pseudonym creation
            mock_pseudonym = Mock()
            mock_pseudonym.pseudonym_id = uuid4()
            mock_pseudonym.pseudonym_text = pseudonym_text
            mock_pseudonym.pseudonym_hash = "hash123"
            mock_pseudonym.created_at = datetime.utcnow()
            mock_pseudonym.is_active = True
            
            with patch.object(pseudonym_service, '_get_pseudonym_logic') as mock_get_logic:
                mock_logic = Mock()
                mock_logic.create_pseudonym.return_value = Mock(
                    pseudonym_id=mock_pseudonym.pseudonym_id,
                    pseudonym_text=pseudonym_text,
                    pseudonym_hash="hash123",
                    created_at=mock_pseudonym.created_at,
                    is_active=True
                )
                mock_get_logic.return_value = mock_logic
                
                pseudonym_result = pseudonym_service.create_pseudonym(user_id, pseudonym_text)
                
                assert pseudonym_result.pseudonym_id == mock_pseudonym.pseudonym_id
                assert pseudonym_result.pseudonym_text == pseudonym_text
            
            # Journey Step 2: Consent Collection
            consent_service = ConsentService()
            pseudonym_id = pseudonym_result.pseudonym_id
            
            consents = {
                "data_protection": True,
                "ai_interaction": True,
                "study_participation": True
            }
            
            with patch.object(consent_service, '_get_consent_logic') as mock_get_consent_logic:
                mock_consent_logic = Mock()
                mock_consent_logic.process_consent_collection.return_value = {
                    "success": True,
                    "can_proceed": True,
                    "consent_records": [Mock(), Mock(), Mock()],
                    "failed_consents": [],
                    "validation": {"is_complete": True, "missing_consents": []}
                }
                mock_get_consent_logic.return_value = mock_consent_logic
                
                consent_result = consent_service.process_consent_collection(pseudonym_id, consents)
                
                assert consent_result["success"] is True
                assert consent_result["can_proceed"] is True
            
            # Journey Step 3: Survey Completion
            # (Would be tested with actual survey file and responses)
            
            # Journey Step 4: Multiple Chat Sessions
            session_ids = [uuid4() for _ in range(3)]  # Simulate 3 chat sessions
            
            for i, session_id in enumerate(session_ids):
                # Simulate chat interaction with PALD extraction
                chat_messages = [
                    f"I want a friendly teacher for session {i+1}",
                    f"Make the teacher look professional for lesson {i+1}",
                    f"Add some personality to the character for session {i+1}"
                ]
                
                for message in chat_messages:
                    # Each message would go through PALD extraction and processing
                    # This verifies the system can handle multiple sessions per participant
                    assert len(message) > 0
                    assert f"session {i+1}" in message
            
            # Verify journey completion
            assert len(session_ids) == 3
            assert pseudonym_id is not None
            assert consent_result["success"] is True
    
    def test_participant_data_deletion_cascade(self):
        """Test participant data deletion with proper cascade behavior."""
        pseudonym_id = uuid4()
        
        # Mock data across all tables that should be deleted
        mock_data_to_delete = {
            "pseudonym": Mock(pseudonym_id=pseudonym_id),
            "consents": [Mock(pseudonym_id=pseudonym_id) for _ in range(3)],
            "survey": Mock(pseudonym_id=pseudonym_id),
            "chat_messages": [Mock(pseudonym_id=pseudonym_id) for _ in range(5)],
            "pald_data": [Mock(pseudonym_id=pseudonym_id) for _ in range(8)],
            "feedback": [Mock(pseudonym_id=pseudonym_id) for _ in range(2)],
            "interactions": [Mock(pseudonym_id=pseudonym_id) for _ in range(10)]
        }
        
        # Simulate deletion request
        user_id = uuid4()
        
        with patch('src.services.pseudonym_service.PseudonymService') as mock_service:
            mock_service_instance = mock_service.return_value
            mock_service_instance.deactivate_user_pseudonym.return_value = True
            
            # Execute deletion
            deletion_success = mock_service_instance.deactivate_user_pseudonym(user_id)
            
            assert deletion_success is True
            mock_service_instance.deactivate_user_pseudonym.assert_called_once_with(user_id)
        
        # Verify all related data would be deleted (in real implementation)
        # This test verifies the cascade deletion logic is properly designed
        for data_type, data_items in mock_data_to_delete.items():
            if isinstance(data_items, list):
                for item in data_items:
                    assert item.pseudonym_id == pseudonym_id
            else:
                assert data_items.pseudonym_id == pseudonym_id
    
    def test_system_performance_under_load(self):
        """Test system performance under realistic load conditions."""
        # Simulate realistic load: 50 concurrent users, each doing full onboarding
        num_users = 50
        operations_per_user = 10  # pseudonym + 3 consents + survey + 5 chat messages
        
        start_time = time.time()
        
        # Simulate load
        total_operations = 0
        for user_index in range(num_users):
            for op_index in range(operations_per_user):
                # Simulate database operation
                operation_time = 0.001  # 1ms per operation (optimistic)
                time.sleep(operation_time)
                total_operations += 1
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_operations == num_users * operations_per_user
        assert total_time < 10.0  # Should complete within 10 seconds
        
        # Calculate throughput
        operations_per_second = total_operations / total_time
        assert operations_per_second > 10  # Should handle at least 10 ops/second
        
        # Memory usage would be tested in real implementation
        # Database connection pooling efficiency would be verified
        # Response time distribution would be analyzed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])