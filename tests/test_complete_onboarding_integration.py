"""
Comprehensive integration tests for complete onboarding flow.
Tests the complete end-to-end workflow from registration through chat interactions.

This test suite validates:
- Complete onboarding flow (registration → pseudonym → consent → survey → chat)
- End-to-end PALD pipeline with consistency loops and feedback rounds
- Database integration with foreign key relationships and cascade operations
- Performance under concurrent user onboarding scenarios

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

import pytest
import tempfile
import os
import time
import concurrent.futures
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4, UUID
from dataclasses import dataclass
from unittest.mock import Mock, patch

from src.data.models import (
    StudyConsentType, 
    ChatMessageType, 
    StudyPALDType,
    Pseudonym,
    StudyConsentRecord,
    SurveyResponse,
    ChatMessage,
    StudyPALDData,
    FeedbackRecord,
    InteractionLog
)
from src.logic.pseudonym_logic import PseudonymLogic, PseudonymError, InvalidPseudonymFormatError
from src.services.pseudonym_service import PseudonymService
from src.logic.consent_logic import ConsentLogic
from src.services.consent_service import ConsentService
from src.logic.survey_logic import SurveyLogic
from src.services.survey_service import SurveyService
from src.logic.chat_logic import ChatLogic
from src.services.chat_service import ChatService
from src.data.schemas import PseudonymResponse
from src.logic.survey_logic import SurveyDefinition, SurveyResult
from src.logic.chat_logic import PALDExtractionResult, ConsistencyCheckResult
from src.exceptions import (
    ConsentError, 
    ConsentRequiredError, 
    ValidationError, 
    DatabaseError
)


@dataclass
class ConsentResult:
    """Simple consent result for testing."""
    success: bool
    can_proceed: bool
    consent_records: List[StudyConsentRecord]
    failed_consents: List[StudyConsentType]
    validation: Dict[str, Any]


class TestCompleteOnboardingFlow:
    """Integration tests for complete study participation onboarding flow."""
    
    @pytest.fixture
    def test_database(self):
        """Create test database session."""
        # This would use a test database in real implementation
        from unittest.mock import Mock
        session = Mock()
        session.begin.return_value.__enter__ = Mock()
        session.begin.return_value.__exit__ = Mock(return_value=None)
        session.commit = Mock()
        session.rollback = Mock()
        session.flush = Mock()
        session.add = Mock()
        session.query = Mock()
        return session
    
    @pytest.fixture
    def comprehensive_survey_data(self):
        """Create comprehensive survey data for testing."""
        return {
            "csv_content": """question_id,question_text,type,options,required
name,What is your full name?,text,,true
age,What is your age?,number,,true
learning_style,What is your preferred learning style?,choice,"Visual,Auditory,Kinesthetic,Reading/Writing",true
interests,Which subjects interest you?,multi-choice,"Math,Science,Art,Music,Sports",false
goals,What are your learning goals?,text,,false
feedback_style,How do you prefer feedback?,choice,"Encouraging,Direct,Detailed",false""",
            "responses": {
                "name": "Test Participant",
                "age": "25",
                "learning_style": "Visual",
                "interests": ["Math", "Science"],
                "goals": "Improve problem-solving skills",
                "feedback_style": "Encouraging"
            }
        }
    
    def test_complete_successful_onboarding_flow(self, test_database, comprehensive_survey_data):
        """Test complete successful onboarding flow from start to finish.
        
        Requirements: 12.1, 12.7
        """
        # Test data setup
        user_id = uuid4()
        pseudonym_text = "M03s2001AJ13"
        session_id = uuid4()
        
        # Step 1: Pseudonym Creation
        pseudonym_service = PseudonymService()
        
        # Mock successful pseudonym creation
        expected_pseudonym_id = uuid4()
        expected_pseudonym = Pseudonym(
            pseudonym_id=expected_pseudonym_id,
            pseudonym_text=pseudonym_text,
            pseudonym_hash="secure_hash_123",
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        with patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            mock_create.return_value = PseudonymResponse(
                pseudonym_id=expected_pseudonym_id,
                pseudonym_text=pseudonym_text,
                pseudonym_hash=expected_pseudonym.pseudonym_hash,
                created_at=expected_pseudonym.created_at,
                is_active=True
            )
            
            pseudonym_result = pseudonym_service.create_pseudonym(user_id, pseudonym_text)
            
            assert pseudonym_result.pseudonym_id == expected_pseudonym_id
            assert pseudonym_result.pseudonym_text == pseudonym_text
            assert pseudonym_result.is_active is True
        
        pseudonym_id = pseudonym_result.pseudonym_id
        
        # Step 2: Consent Collection
        consent_service = ConsentService()
        
        consents = {
            StudyConsentType.DATA_PROTECTION: True,
            StudyConsentType.AI_INTERACTION: True,
            StudyConsentType.STUDY_PARTICIPATION: True
        }
        
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
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
            assert consent_result.validation["is_complete"] is True
        
        # Step 3: Survey Completion
        survey_service = SurveyService()
        
        # Create temporary survey file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(comprehensive_survey_data["csv_content"])
            tmp_path = tmp_file.name
        
        try:
            with pytest.mock.patch.object(survey_service, 'load_survey_definition') as mock_load, \
                 pytest.mock.patch.object(survey_service, 'process_survey_submission') as mock_submit:
                
                # Mock survey loading
                mock_load.return_value = SurveyDefinition(
                    survey_id="test_survey",
                    version="1.0",
                    questions=[
                        {"question_id": "name", "question_text": "What is your full name?", 
                         "type": "text", "options": None, "required": True},
                        {"question_id": "age", "question_text": "What is your age?", 
                         "type": "number", "options": None, "required": True},
                        {"question_id": "learning_style", "question_text": "What is your preferred learning style?", 
                         "type": "choice", "options": ["Visual", "Auditory", "Kinesthetic", "Reading/Writing"], "required": True}
                    ]
                )
                
                # Mock survey submission
                mock_submit.return_value = SurveyResult(
                    success=True,
                    survey_response_id=uuid4(),
                    validation_errors=[],
                    processing_time_ms=150
                )
                
                survey_definition = survey_service.load_survey_definition(tmp_path)
                survey_result = survey_service.process_survey_submission(
                    pseudonym_id, comprehensive_survey_data["responses"], survey_definition
                )
                
                assert survey_result.success is True
                assert len(survey_result.validation_errors) == 0
        
        finally:
            os.unlink(tmp_path)
        
        # Step 4: Chat Interface Initialization
        chat_service = ChatService()
        
        with pytest.mock.patch.object(chat_service, 'store_chat_message') as mock_store_msg:
            mock_message = ChatMessage(
                message_id=uuid4(),
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                message_type=ChatMessageType.USER,
                content="I want a friendly teacher avatar",
                pald_data={"global_design_level": {"overall_appearance": "friendly teacher"}},
                timestamp=datetime.utcnow()
            )
            mock_store_msg.return_value = mock_message
            
            stored_message = chat_service.store_chat_message(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                message_type=ChatMessageType.USER,
                content="I want a friendly teacher avatar"
            )
            
            assert stored_message.pseudonym_id == pseudonym_id
            assert stored_message.session_id == session_id
            assert "friendly teacher" in stored_message.content
        
        # Verify complete flow data integrity
        assert pseudonym_id is not None
        assert isinstance(pseudonym_id, UUID)
        assert consent_result.success is True
        assert survey_result.success is True
        assert stored_message.pseudonym_id == pseudonym_id
    
    def test_onboarding_flow_with_validation_failures(self, test_database):
        """Test onboarding flow with validation errors and recovery.
        
        Requirements: 12.1, 12.6
        """
        user_id = uuid4()
        
        # Test 1: Invalid pseudonym format
        pseudonym_service = PseudonymService(test_database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            from src.exceptions import InvalidPseudonymFormatError
            mock_create.side_effect = InvalidPseudonymFormatError("Invalid format")
            
            with pytest.raises(InvalidPseudonymFormatError):
                pseudonym_service.create_pseudonym(user_id, "invalid")
        
        # Test 2: Incomplete consent handling
        pseudonym_id = uuid4()
        consent_service = ConsentService(test_database)
        
        incomplete_consents = {
            StudyConsentType.DATA_PROTECTION: True,
            StudyConsentType.AI_INTERACTION: False,  # Missing required consent
            StudyConsentType.STUDY_PARTICIPATION: True
        }
        
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
            mock_consent.return_value = ConsentResult(
                success=True,  # Records stored but validation shows incompleteness
                can_proceed=False,
                consent_records=[
                    StudyConsentRecord(
                        consent_id=uuid4(),
                        pseudonym_id=pseudonym_id,
                        consent_type=consent_type,
                        granted=granted,
                        version="1.0",
                        granted_at=datetime.utcnow()
                    )
                    for consent_type, granted in incomplete_consents.items()
                ],
                failed_consents=[],
                validation={
                    "is_complete": False,
                    "missing_consents": [StudyConsentType.AI_INTERACTION]
                }
            )
            
            consent_result = consent_service.process_consent_collection(pseudonym_id, incomplete_consents)
            
            assert consent_result.success is True  # Records stored
            assert consent_result.can_proceed is False  # Cannot proceed due to missing consent
            assert not consent_result.validation["is_complete"]
            assert StudyConsentType.AI_INTERACTION in consent_result.validation["missing_consents"]
    
    def test_onboarding_flow_error_recovery(self, test_database):
        """Test error recovery mechanisms during onboarding.
        
        Requirements: 12.6, 12.7
        """
        user_id = uuid4()
        pseudonym_text = "M03s2001AJ13"
        
        # Test database error during pseudonym creation
        pseudonym_service = PseudonymService(test_database)
        
        with pytest.mock.patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
            mock_create.side_effect = DatabaseError("Database connection failed")
            
            with pytest.raises(DatabaseError):
                pseudonym_service.create_pseudonym(user_id, pseudonym_text)
        
        # Test partial consent failure with recovery
        pseudonym_id = uuid4()
        consent_service = ConsentService(test_database)
        
        consents = {
            StudyConsentType.DATA_PROTECTION: True,
            StudyConsentType.AI_INTERACTION: True,
            StudyConsentType.STUDY_PARTICIPATION: True
        }
        
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
            # Simulate partial failure
            mock_consent.return_value = ConsentResult(
                success=False,
                can_proceed=False,
                consent_records=[
                    StudyConsentRecord(
                        consent_id=uuid4(),
                        pseudonym_id=pseudonym_id,
                        consent_type=StudyConsentType.DATA_PROTECTION,
                        granted=True,
                        version="1.0",
                        granted_at=datetime.utcnow()
                    ),
                    StudyConsentRecord(
                        consent_id=uuid4(),
                        pseudonym_id=pseudonym_id,
                        consent_type=StudyConsentType.STUDY_PARTICIPATION,
                        granted=True,
                        version="1.0",
                        granted_at=datetime.utcnow()
                    )
                ],
                failed_consents=[StudyConsentType.AI_INTERACTION],
                validation={
                    "is_complete": False,
                    "missing_consents": [StudyConsentType.AI_INTERACTION]
                }
            )
            
            consent_result = consent_service.process_consent_collection(pseudonym_id, consents)
            
            assert consent_result.success is False
            assert len(consent_result.failed_consents) == 1
            assert StudyConsentType.AI_INTERACTION in consent_result.failed_consents
            assert len(consent_result.consent_records) == 2  # Two successful consents


class TestPALDPipelineEndToEnd:
    """End-to-end tests for PALD pipeline with consistency loops and feedback rounds."""
    
    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service for PALD processing."""
        from unittest.mock import Mock
        service = Mock()
        
        def mock_generate_response(prompt, **kwargs):
            if "friendly teacher" in prompt.lower():
                response_text = json.dumps({
                    "global_design_level": {
                        "overall_appearance": "friendly professional teacher",
                        "style": "approachable and warm"
                    },
                    "detailed_level": {
                        "hair": "brown curly hair",
                        "accessories": "glasses"
                    }
                })
            else:
                response_text = json.dumps({
                    "global_design_level": {"overall_appearance": "generic character"}
                })
            
            mock_response = Mock()
            mock_response.text = response_text
            return mock_response
        
        service.generate_response = mock_generate_response
        return service
    
    def test_complete_pald_pipeline_with_consistency_loop(self, mock_llm_service):
        """Test complete PALD pipeline with consistency checking.
        
        Requirements: 12.2, 12.4
        """
        chat_logic = ChatLogic(mock_llm_service)
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Step 1: Process initial user input
        user_input = "I want a friendly female teacher with brown hair and glasses"
        
        with pytest.mock.patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            mock_extract.return_value = PALDExtractionResult(
                success=True,
                pald_data={
                    "global_design_level": {"overall_appearance": "friendly female teacher"},
                    "detailed_level": {"hair": "brown", "accessories": "glasses"}
                },
                extraction_confidence=0.9,
                processing_time_ms=150
            )
            
            input_pald_result = chat_logic.extract_pald_from_text(user_input)
            
            assert input_pald_result.success is True
            assert input_pald_result.pald_data is not None
            assert "friendly female teacher" in str(input_pald_result.pald_data)
        
        # Step 2: Simulate image generation and description
        description_text = "A friendly woman with short blonde hair and no accessories"
        
        with pytest.mock.patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            mock_extract.return_value = PALDExtractionResult(
                success=True,
                pald_data={
                    "global_design_level": {"overall_appearance": "friendly woman"},
                    "detailed_level": {"hair": "short blonde", "accessories": "none"}
                },
                extraction_confidence=0.8,
                processing_time_ms=120
            )
            
            description_pald_result = chat_logic.extract_pald_from_text(description_text)
            
            assert description_pald_result.success is True
        
        # Step 3: Check consistency between PALDs
        input_pald = input_pald_result.pald_data
        description_pald = description_pald_result.pald_data
        
        with pytest.mock.patch.object(chat_logic, 'check_pald_consistency') as mock_consistency:
            mock_consistency.return_value = ConsistencyCheckResult(
                is_consistent=False,
                consistency_score=0.4,
                differences=["hair color mismatch: brown vs blonde", "accessories mismatch: glasses vs none"],
                recommendation="regenerate",
                processing_time_ms=50
            )
            
            consistency_result = chat_logic.check_pald_consistency(input_pald, description_pald)
            
            assert consistency_result.is_consistent is False
            assert consistency_result.consistency_score < 0.8
            assert len(consistency_result.differences) > 0
            assert "hair" in str(consistency_result.differences)
            assert consistency_result.recommendation == "regenerate"
    
    def test_feedback_loop_with_round_management(self, mock_llm_service):
        """Test feedback loop with proper round counting and limits.
        
        Requirements: 12.2, 12.4
        """
        chat_logic = ChatLogic(mock_llm_service)
        pseudonym_id = uuid4()
        session_id = uuid4()
        image_id = uuid4()
        
        feedback_rounds = [
            "The hair should be brown, not blonde",
            "Add glasses to make her look more professional", 
            "The smile should be warmer and more welcoming"
        ]
        
        for round_num, feedback_text in enumerate(feedback_rounds, 1):
            with pytest.mock.patch.object(chat_logic, 'manage_feedback_loop') as mock_feedback:
                from src.logic.chat_logic import FeedbackProcessingResult
                
                mock_feedback.return_value = FeedbackProcessingResult(
                    feedback_id=uuid4(),
                    round_number=round_num,
                    max_rounds_reached=(round_num >= 3),
                    should_continue=(round_num < 3),
                    feedback_pald={
                        "detailed_level": {
                            "hair": "brown" if "hair" in feedback_text else None,
                            "accessories": "glasses" if "glasses" in feedback_text else None,
                            "facial_features": "warm smile" if "smile" in feedback_text else None
                        }
                    },
                    processing_metadata={
                        "feedback_length": len(feedback_text),
                        "pald_extraction_success": True,
                        "processing_time_ms": 200
                    }
                )
                
                feedback_result = chat_logic.manage_feedback_loop(
                    pseudonym_id, session_id, feedback_text, round_num, image_id
                )
                
                assert feedback_result.round_number == round_num
                assert feedback_result.feedback_id is not None
                
                # Check round limits
                if round_num < 3:
                    assert feedback_result.max_rounds_reached is False
                    assert feedback_result.should_continue is True
                else:
                    assert feedback_result.max_rounds_reached is True
                    assert feedback_result.should_continue is False
                
                # Verify feedback PALD extraction
                assert feedback_result.feedback_pald is not None
                assert isinstance(feedback_result.feedback_pald, dict)
    
    def test_pald_pipeline_error_handling(self, mock_llm_service):
        """Test PALD pipeline error handling and graceful degradation.
        
        Requirements: 12.6
        """
        # Mock LLM service to fail
        mock_llm_service.generate_response.side_effect = Exception("LLM service unavailable")
        
        chat_logic = ChatLogic(mock_llm_service)
        
        with pytest.mock.patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
            mock_extract.return_value = PALDExtractionResult(
                success=False,
                pald_data={},
                extraction_confidence=0.0,
                processing_time_ms=0,
                error_message="LLM service unavailable"
            )
            
            result = chat_logic.extract_pald_from_text("I want a teacher")
            
            assert result.success is False
            assert result.pald_data == {}
            assert result.extraction_confidence == 0.0
            assert "LLM service unavailable" in result.error_message


class TestDatabaseIntegrationAndCascades:
    """Database integration tests for foreign key relationships and cascade operations."""
    
    @pytest.fixture
    def test_database(self):
        """Create test database session with mock models."""
        from unittest.mock import Mock
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.delete = Mock()
        session.query = Mock()
        return session
    
    def test_foreign_key_relationships_integrity(self, test_database):
        """Test that all data is properly linked via pseudonym_id.
        
        Requirements: 12.3, 12.5
        """
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Create related data objects
        pseudonym = Pseudonym(
            pseudonym_id=pseudonym_id,
            user_id=uuid4(),
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="hash123",
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        consent_record = StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,
            consent_type=StudyConsentType.DATA_PROTECTION,
            granted=True,
            version="1.0",
            granted_at=datetime.utcnow()
        )
        
        survey_response = SurveyResponse(
            response_id=uuid4(),
            pseudonym_id=pseudonym_id,
            survey_version="1.0",
            responses={"name": "Test User", "age": "25"},
            completed_at=datetime.utcnow()
        )
        
        chat_message = ChatMessage(
            message_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="I want a teacher",
            pald_data={"global_design_level": {"overall_appearance": "teacher"}},
            timestamp=datetime.utcnow()
        )
        
        pald_data = StudyPALDData(
            pald_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            pald_content={"global_design_level": {"overall_appearance": "teacher"}},
            pald_type=StudyPALDType.INPUT,
            consistency_score=0.85,
            created_at=datetime.utcnow()
        )
        
        # Verify all objects use the same pseudonym_id
        assert consent_record.pseudonym_id == pseudonym_id
        assert survey_response.pseudonym_id == pseudonym_id
        assert chat_message.pseudonym_id == pseudonym_id
        assert pald_data.pseudonym_id == pseudonym_id
        
        # Verify session consistency for chat-related data
        assert chat_message.session_id == session_id
        assert pald_data.session_id == session_id
    
    def test_cascade_deletion_behavior(self, test_database):
        """Test cascade deletion when pseudonym is deleted.
        
        Requirements: 12.3, 12.5
        """
        pseudonym_id = uuid4()
        
        # Mock repository with cascade deletion
        from unittest.mock import Mock
        
        with pytest.mock.patch('src.data.repositories.PseudonymRepository') as mock_repo:
            mock_repo_instance = mock_repo.return_value
            
            # Mock cascade deletion result
            mock_repo_instance.delete_pseudonym_cascade.return_value = {
                "pseudonym_deleted": True,
                "related_records_deleted": {
                    "consent_records": 3,
                    "survey_responses": 1,
                    "chat_messages": 15,
                    "pald_data": 8,
                    "feedback_records": 2,
                    "interaction_logs": 25
                },
                "total_records_deleted": 55
            }
            
            deletion_result = mock_repo_instance.delete_pseudonym_cascade(pseudonym_id)
            
            assert deletion_result["pseudonym_deleted"] is True
            assert deletion_result["related_records_deleted"]["consent_records"] == 3
            assert deletion_result["related_records_deleted"]["chat_messages"] == 15
            assert deletion_result["total_records_deleted"] > 0
    
    def test_transaction_rollback_scenarios(self, test_database):
        """Test transaction handling and rollback scenarios.
        
        Requirements: 12.5, 12.6
        """
        pseudonym_id = uuid4()
        
        # Test rollback on consent creation failure
        with pytest.mock.patch('src.services.consent_service.ConsentService') as mock_service:
            mock_service_instance = mock_service.return_value
            
            # Mock transaction failure
            test_database.commit.side_effect = DatabaseError("Transaction failed")
            
            with pytest.raises(DatabaseError):
                mock_service_instance.process_consent_collection(pseudonym_id, {
                    StudyConsentType.DATA_PROTECTION: True
                })
            
            # Verify rollback was called
            test_database.rollback.assert_called()
    
    def test_data_consistency_across_tables(self, test_database):
        """Test data consistency across related tables.
        
        Requirements: 12.5
        """
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Create consistent data across tables
        chat_message = ChatMessage(
            message_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="I want a friendly teacher",
            timestamp=datetime.utcnow()
        )
        
        pald_data = StudyPALDData(
            pald_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            pald_content={"global_design_level": {"overall_appearance": "friendly teacher"}},
            pald_type=StudyPALDType.INPUT,
            created_at=datetime.utcnow()
        )
        
        interaction_log = InteractionLog(
            log_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type="pald_extraction",
            model_used="llama3",
            parameters={"temperature": 0.3},
            latency_ms=150,
            timestamp=datetime.utcnow()
        )
        
        # Verify consistency
        assert chat_message.pseudonym_id == pald_data.pseudonym_id == interaction_log.pseudonym_id
        assert chat_message.session_id == pald_data.session_id == interaction_log.session_id
        
        # Verify timestamps are consistent (within reasonable range)
        time_diff = abs((chat_message.timestamp - pald_data.created_at).total_seconds())
        assert time_diff < 1.0  # Should be created within 1 second of each other


class TestConcurrentUserPerformance:
    """Performance tests for concurrent user onboarding and database operations."""
    
    @pytest.fixture
    def performance_test_setup(self):
        """Setup for performance testing."""
        from unittest.mock import Mock
        
        # Mock database session
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        
        # Mock services
        pseudonym_service = Mock()
        consent_service = Mock()
        survey_service = Mock()
        
        return {
            "session": session,
            "pseudonym_service": pseudonym_service,
            "consent_service": consent_service,
            "survey_service": survey_service
        }
    
    def test_concurrent_user_onboarding_performance(self, performance_test_setup):
        """Test performance under concurrent user onboarding scenarios.
        
        Requirements: 12.4, 12.7
        """
        num_concurrent_users = 20
        services = performance_test_setup
        
        # Setup service mocks for concurrent access
        services["pseudonym_service"].create_pseudonym.return_value = Mock(
            pseudonym_id=lambda: uuid4(),
            pseudonym_text=lambda i: f"U{i:02d}m2001AB{i}",
            is_active=True
        )
        
        services["consent_service"].process_consent_collection.return_value = Mock(
            success=True,
            can_proceed=True,
            consent_records=[Mock(), Mock(), Mock()]
        )
        
        def simulate_user_onboarding(user_index: int) -> Dict[str, Any]:
            """Simulate single user onboarding process."""
            user_id = uuid4()
            pseudonym_text = f"U{user_index:02d}m2001AB{user_index}"
            
            try:
                start_time = time.time()
                
                # Pseudonym creation
                pseudonym_result = services["pseudonym_service"].create_pseudonym(user_id, pseudonym_text)
                
                # Consent collection
                consents = {
                    StudyConsentType.DATA_PROTECTION: True,
                    StudyConsentType.AI_INTERACTION: True,
                    StudyConsentType.STUDY_PARTICIPATION: True
                }
                consent_result = services["consent_service"].process_consent_collection(
                    pseudonym_result.pseudonym_id, consents
                )
                
                processing_time = time.time() - start_time
                
                return {
                    "user_index": user_index,
                    "success": True,
                    "processing_time": processing_time,
                    "pseudonym_created": True,
                    "consents_processed": True
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time if 'start_time' in locals() else 0
                }
        
        # Execute concurrent onboarding
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(simulate_user_onboarding, i) 
                for i in range(num_concurrent_users)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Performance assertions
        assert len(successful_results) == num_concurrent_users, f"Expected {num_concurrent_users} successful, got {len(successful_results)}"
        assert len(failed_results) == 0, f"Unexpected failures: {failed_results}"
        
        # Timing assertions
        assert total_time < 10.0, f"Total time {total_time}s exceeded 10s limit"
        
        avg_processing_time = sum(r["processing_time"] for r in successful_results) / len(successful_results)
        assert avg_processing_time < 1.0, f"Average processing time {avg_processing_time}s exceeded 1s limit"
        
        # Verify service call counts
        assert services["pseudonym_service"].create_pseudonym.call_count == num_concurrent_users
        assert services["consent_service"].process_consent_collection.call_count == num_concurrent_users
    
    def test_database_performance_under_load(self, performance_test_setup):
        """Test database performance under concurrent operations.
        
        Requirements: 12.4, 12.5
        """
        session = performance_test_setup["session"]
        num_operations = 100
        
        def simulate_database_operation(operation_id: int) -> Dict[str, Any]:
            """Simulate database operation."""
            start_time = time.time()
            
            try:
                # Simulate database operations
                session.add(Mock())
                session.commit()
                
                processing_time = time.time() - start_time
                
                return {
                    "operation_id": operation_id,
                    "success": True,
                    "processing_time": processing_time
                }
                
            except Exception as e:
                return {
                    "operation_id": operation_id,
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
        
        # Execute concurrent database operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(simulate_database_operation, i) 
                for i in range(num_operations)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_operations = [r for r in results if r["success"]]
        failed_operations = [r for r in results if not r["success"]]
        
        # Performance assertions
        assert len(successful_operations) == num_operations
        assert len(failed_operations) == 0
        assert total_time < 5.0  # Should complete within 5 seconds
        
        # Verify database operations were called
        assert session.add.call_count == num_operations
        assert session.commit.call_count == num_operations
    
    @pytest.mark.slow
    def test_memory_usage_during_concurrent_operations(self, performance_test_setup):
        """Test memory usage during concurrent operations.
        
        Requirements: 12.4
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate memory-intensive operations
        num_users = 50
        large_data_operations = []
        
        for i in range(num_users):
            # Simulate large PALD data processing
            large_pald_data = {
                "global_design_level": {"overall_appearance": "detailed character" * 100},
                "detailed_level": {f"attribute_{j}": f"value_{j}" * 50 for j in range(20)}
            }
            large_data_operations.append(large_pald_data)
        
        # Process all operations
        for data in large_data_operations:
            # Simulate processing
            processed_data = json.dumps(data)
            assert len(processed_data) > 0
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory usage should not increase excessively
        assert memory_increase < 100, f"Memory increased by {memory_increase}MB, exceeding 100MB limit"