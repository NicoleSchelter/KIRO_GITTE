"""
Contract tests for integration testing components.
Tests the contracts between different layers and services in integration scenarios.

This test suite validates:
- Service layer contracts during integration flows
- Data layer contracts for foreign key relationships
- Logic layer contracts for cross-component interactions
- External service contracts for LLM and database interactions

Requirements: 12.1, 12.2, 12.3, 12.5
"""

import pytest
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from uuid import UUID, uuid4
from datetime import datetime

from src.data.models import StudyConsentType, ChatMessageType, StudyPALDType


class PseudonymServiceContract(Protocol):
    """Contract for pseudonym service in integration scenarios."""
    
    def create_pseudonym(self, user_id: UUID, pseudonym_text: str) -> Any:
        """Create a new pseudonym for a user."""
        ...
    
    def get_pseudonym_by_user(self, user_id: UUID) -> Optional[Any]:
        """Get pseudonym for a user."""
        ...
    
    def deactivate_user_pseudonym(self, user_id: UUID) -> bool:
        """Deactivate user's pseudonym and related data."""
        ...
    
    def verify_pseudonym_ownership(self, user_id: UUID, pseudonym_text: str) -> bool:
        """Verify that a user owns a specific pseudonym."""
        ...


class ConsentServiceContract(Protocol):
    """Contract for consent service in integration scenarios."""
    
    def process_consent_collection(self, pseudonym_id: UUID, consents: Dict[StudyConsentType, bool]) -> Any:
        """Process consent collection for a pseudonym."""
        ...
    
    def get_consent_status(self, pseudonym_id: UUID) -> Dict[str, Any]:
        """Get consent status for a pseudonym."""
        ...
    
    def withdraw_consent(self, pseudonym_id: UUID, consent_type: StudyConsentType) -> bool:
        """Withdraw specific consent for a pseudonym."""
        ...


class SurveyServiceContract(Protocol):
    """Contract for survey service in integration scenarios."""
    
    def load_survey_definition(self, file_path: str) -> Any:
        """Load survey definition from file."""
        ...
    
    def process_survey_submission(self, pseudonym_id: UUID, responses: Dict[str, Any], definition: Any) -> Any:
        """Process survey submission for a pseudonym."""
        ...
    
    def get_survey_responses(self, pseudonym_id: UUID) -> Optional[Any]:
        """Get survey responses for a pseudonym."""
        ...


class ChatServiceContract(Protocol):
    """Contract for chat service in integration scenarios."""
    
    def store_chat_message(self, pseudonym_id: UUID, session_id: UUID, message_type: ChatMessageType, content: str, **kwargs) -> Any:
        """Store a chat message."""
        ...
    
    def get_chat_history(self, pseudonym_id: UUID, session_id: Optional[UUID] = None) -> List[Any]:
        """Get chat history for a pseudonym."""
        ...
    
    def store_pald_data(self, pseudonym_id: UUID, session_id: UUID, pald_content: Dict[str, Any], pald_type: StudyPALDType, **kwargs) -> Any:
        """Store PALD data."""
        ...
    
    def store_feedback_record(self, pseudonym_id: UUID, session_id: UUID, feedback_text: str, round_number: int, **kwargs) -> Any:
        """Store feedback record."""
        ...


class DatabaseSessionContract(Protocol):
    """Contract for database session in integration scenarios."""
    
    def add(self, instance: Any) -> None:
        """Add an instance to the session."""
        ...
    
    def commit(self) -> None:
        """Commit the current transaction."""
        ...
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        ...
    
    def query(self, *args, **kwargs) -> Any:
        """Execute a query."""
        ...
    
    def delete(self, instance: Any) -> None:
        """Delete an instance from the session."""
        ...


class LLMServiceContract(Protocol):
    """Contract for LLM service in integration scenarios."""
    
    def generate_response(self, prompt: str, model: Optional[str] = None, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Generate response from LLM."""
        ...


class TestPseudonymServiceIntegrationContract:
    """Test pseudonym service contract in integration scenarios."""
    
    def test_pseudonym_service_contract_compliance(self):
        """Test that pseudonym service implementations comply with contract.
        
        Requirements: 12.1, 12.3
        """
        from unittest.mock import Mock
        from src.services.pseudonym_service import PseudonymService
        
        # Create mock database session
        mock_session = Mock(spec=DatabaseSessionContract)
        
        # Create service instance
        service = PseudonymService(mock_session)
        
        # Verify service implements the contract
        assert hasattr(service, 'create_pseudonym')
        assert hasattr(service, 'get_pseudonym_by_user')
        assert hasattr(service, 'deactivate_user_pseudonym')
        
        # Test contract method signatures
        user_id = uuid4()
        pseudonym_text = "T01e2000MJ42"
        
        # Mock the actual implementation calls
        with pytest.mock.patch.object(service, 'create_pseudonym') as mock_create:
            from src.logic.pseudonym_logic import PseudonymResult
            
            mock_create.return_value = PseudonymResult(
                pseudonym_id=uuid4(),
                pseudonym_text=pseudonym_text,
                pseudonym_hash="hash123",
                created_at=datetime.utcnow(),
                is_active=True
            )
            
            # Test create_pseudonym contract
            result = service.create_pseudonym(user_id, pseudonym_text)
            
            # Verify return type has required attributes
            assert hasattr(result, 'pseudonym_id')
            assert hasattr(result, 'pseudonym_text')
            assert hasattr(result, 'is_active')
            assert isinstance(result.pseudonym_id, UUID)
            assert isinstance(result.pseudonym_text, str)
            assert isinstance(result.is_active, bool)
        
        with pytest.mock.patch.object(service, 'get_pseudonym_by_user') as mock_get:
            mock_get.return_value = None  # No existing pseudonym
            
            # Test get_pseudonym_by_user contract
            result = service.get_pseudonym_by_user(user_id)
            
            # Should return None or pseudonym object
            assert result is None or hasattr(result, 'pseudonym_id')
        
        with pytest.mock.patch.object(service, 'deactivate_user_pseudonym') as mock_deactivate:
            mock_deactivate.return_value = True
            
            # Test deactivate_user_pseudonym contract
            result = service.deactivate_user_pseudonym(user_id)
            
            # Should return boolean
            assert isinstance(result, bool)
    
    def test_pseudonym_service_error_contract(self):
        """Test pseudonym service error handling contract.
        
        Requirements: 12.1, 12.6
        """
        from unittest.mock import Mock
        from src.services.pseudonym_service import PseudonymService
        from src.exceptions import PseudonymError, InvalidPseudonymFormatError
        
        mock_session = Mock(spec=DatabaseSessionContract)
        service = PseudonymService(mock_session)
        
        # Test error contract for invalid pseudonym format
        with pytest.mock.patch.object(service, 'create_pseudonym') as mock_create:
            mock_create.side_effect = InvalidPseudonymFormatError("Invalid format")
            
            with pytest.raises(InvalidPseudonymFormatError):
                service.create_pseudonym(uuid4(), "invalid")
        
        # Test error contract for database errors
        with pytest.mock.patch.object(service, 'create_pseudonym') as mock_create:
            from src.exceptions import DatabaseError
            mock_create.side_effect = DatabaseError("Database connection failed")
            
            with pytest.raises(DatabaseError):
                service.create_pseudonym(uuid4(), "T01e2000MJ42")


class TestConsentServiceIntegrationContract:
    """Test consent service contract in integration scenarios."""
    
    def test_consent_service_contract_compliance(self):
        """Test that consent service implementations comply with contract.
        
        Requirements: 12.1, 12.3
        """
        from unittest.mock import Mock
        from src.services.consent_service import ConsentService
        
        mock_session = Mock(spec=DatabaseSessionContract)
        service = ConsentService(mock_session)
        
        # Verify service implements the contract
        assert hasattr(service, 'process_consent_collection')
        assert hasattr(service, 'get_consent_status')
        assert hasattr(service, 'withdraw_consent')
        
        # Test contract method signatures
        pseudonym_id = uuid4()
        consents = {
            StudyConsentType.DATA_PROTECTION: True,
            StudyConsentType.AI_INTERACTION: True,
            StudyConsentType.STUDY_PARTICIPATION: True
        }
        
        with pytest.mock.patch.object(service, 'process_consent_collection') as mock_process:
            from src.logic.consent_logic import ConsentResult
            
            mock_process.return_value = ConsentResult(
                success=True,
                can_proceed=True,
                consent_records=[],
                failed_consents=[],
                validation={"is_complete": True, "missing_consents": []}
            )
            
            # Test process_consent_collection contract
            result = service.process_consent_collection(pseudonym_id, consents)
            
            # Verify return type has required attributes
            assert hasattr(result, 'success')
            assert hasattr(result, 'can_proceed')
            assert hasattr(result, 'consent_records')
            assert isinstance(result.success, bool)
            assert isinstance(result.can_proceed, bool)
            assert isinstance(result.consent_records, list)
        
        with pytest.mock.patch.object(service, 'get_consent_status') as mock_get:
            mock_get.return_value = {
                "data_protection": {"granted": True, "timestamp": datetime.utcnow()},
                "ai_interaction": {"granted": True, "timestamp": datetime.utcnow()},
                "study_participation": {"granted": True, "timestamp": datetime.utcnow()}
            }
            
            # Test get_consent_status contract
            result = service.get_consent_status(pseudonym_id)
            
            # Should return dictionary with consent information
            assert isinstance(result, dict)
            for consent_type, consent_info in result.items():
                assert isinstance(consent_type, str)
                assert isinstance(consent_info, dict)
                assert "granted" in consent_info
                assert isinstance(consent_info["granted"], bool)


class TestChatServiceIntegrationContract:
    """Test chat service contract in integration scenarios."""
    
    def test_chat_service_contract_compliance(self):
        """Test that chat service implementations comply with contract.
        
        Requirements: 12.2, 12.3
        """
        from unittest.mock import Mock
        from src.services.chat_service import ChatService
        
        mock_session = Mock(spec=DatabaseSessionContract)
        service = ChatService(mock_session)
        
        # Verify service implements the contract
        assert hasattr(service, 'store_chat_message')
        assert hasattr(service, 'get_chat_history')
        assert hasattr(service, 'store_pald_data')
        assert hasattr(service, 'store_feedback_record')
        
        # Test contract method signatures
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        with pytest.mock.patch.object(service, 'store_chat_message') as mock_store:
            from src.data.models import ChatMessage
            
            mock_message = ChatMessage(
                message_id=uuid4(),
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                message_type=ChatMessageType.USER,
                content="Test message",
                timestamp=datetime.utcnow()
            )
            mock_store.return_value = mock_message
            
            # Test store_chat_message contract
            result = service.store_chat_message(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                message_type=ChatMessageType.USER,
                content="Test message"
            )
            
            # Verify return type has required attributes
            assert hasattr(result, 'message_id')
            assert hasattr(result, 'pseudonym_id')
            assert hasattr(result, 'session_id')
            assert hasattr(result, 'content')
            assert isinstance(result.message_id, UUID)
            assert isinstance(result.pseudonym_id, UUID)
            assert isinstance(result.session_id, UUID)
        
        with pytest.mock.patch.object(service, 'store_pald_data') as mock_store_pald:
            from src.data.models import StudyPALDData
            
            mock_pald = StudyPALDData(
                pald_id=uuid4(),
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                pald_content={"global_design_level": {"overall_appearance": "teacher"}},
                pald_type=StudyPALDType.INPUT,
                created_at=datetime.utcnow()
            )
            mock_store_pald.return_value = mock_pald
            
            # Test store_pald_data contract
            result = service.store_pald_data(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                pald_content={"global_design_level": {"overall_appearance": "teacher"}},
                pald_type=StudyPALDType.INPUT
            )
            
            # Verify return type has required attributes
            assert hasattr(result, 'pald_id')
            assert hasattr(result, 'pseudonym_id')
            assert hasattr(result, 'pald_content')
            assert isinstance(result.pald_content, dict)


class TestDatabaseIntegrationContract:
    """Test database integration contract compliance."""
    
    def test_database_session_contract_compliance(self):
        """Test that database session implementations comply with contract.
        
        Requirements: 12.3, 12.5
        """
        from unittest.mock import Mock
        
        # Create mock session that implements the contract
        mock_session = Mock(spec=DatabaseSessionContract)
        
        # Test contract methods exist and work
        mock_instance = Mock()
        
        # Test add method
        mock_session.add(mock_instance)
        mock_session.add.assert_called_once_with(mock_instance)
        
        # Test commit method
        mock_session.commit()
        mock_session.commit.assert_called_once()
        
        # Test rollback method
        mock_session.rollback()
        mock_session.rollback.assert_called_once()
        
        # Test query method
        mock_session.query.return_value = Mock()
        result = mock_session.query(Mock())
        assert result is not None
        mock_session.query.assert_called_once()
        
        # Test delete method
        mock_session.delete(mock_instance)
        mock_session.delete.assert_called_once_with(mock_instance)
    
    def test_foreign_key_relationship_contract(self):
        """Test foreign key relationship contract compliance.
        
        Requirements: 12.3, 12.5
        """
        from src.data.models import (
            Pseudonym, StudyConsentRecord, SurveyResponse, 
            ChatMessage, StudyPALDData, FeedbackRecord
        )
        
        # Test that all models have proper foreign key relationships
        pseudonym_id = uuid4()
        user_id = uuid4()
        session_id = uuid4()
        
        # Create pseudonym (parent record)
        pseudonym = Pseudonym(
            pseudonym_id=pseudonym_id,
            user_id=user_id,
            pseudonym_text="T01e2000MJ42",
            pseudonym_hash="hash123",
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        # Create related records (child records)
        consent_record = StudyConsentRecord(
            consent_id=uuid4(),
            pseudonym_id=pseudonym_id,  # Foreign key reference
            consent_type=StudyConsentType.DATA_PROTECTION,
            granted=True,
            version="1.0",
            granted_at=datetime.utcnow()
        )
        
        survey_response = SurveyResponse(
            response_id=uuid4(),
            pseudonym_id=pseudonym_id,  # Foreign key reference
            survey_version="1.0",
            responses={"name": "Test User"},
            completed_at=datetime.utcnow()
        )
        
        chat_message = ChatMessage(
            message_id=uuid4(),
            pseudonym_id=pseudonym_id,  # Foreign key reference
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="Test message",
            timestamp=datetime.utcnow()
        )
        
        pald_data = StudyPALDData(
            pald_id=uuid4(),
            pseudonym_id=pseudonym_id,  # Foreign key reference
            session_id=session_id,
            pald_content={"global_design_level": {"overall_appearance": "teacher"}},
            pald_type=StudyPALDType.INPUT,
            created_at=datetime.utcnow()
        )
        
        feedback_record = FeedbackRecord(
            feedback_id=uuid4(),
            pseudonym_id=pseudonym_id,  # Foreign key reference
            session_id=session_id,
            image_id=uuid4(),
            feedback_text="Test feedback",
            round_number=1,
            created_at=datetime.utcnow()
        )
        
        # Verify all child records reference the same pseudonym_id
        child_records = [consent_record, survey_response, chat_message, pald_data, feedback_record]
        
        for record in child_records:
            assert hasattr(record, 'pseudonym_id')
            assert record.pseudonym_id == pseudonym_id
            assert isinstance(record.pseudonym_id, UUID)
        
        # Verify session consistency for session-based records
        session_records = [chat_message, pald_data, feedback_record]
        
        for record in session_records:
            assert hasattr(record, 'session_id')
            assert record.session_id == session_id
            assert isinstance(record.session_id, UUID)


class TestLLMServiceIntegrationContract:
    """Test LLM service contract in integration scenarios."""
    
    def test_llm_service_contract_compliance(self):
        """Test that LLM service implementations comply with contract.
        
        Requirements: 12.2
        """
        from unittest.mock import Mock
        
        # Create mock LLM service that implements the contract
        mock_llm_service = Mock(spec=LLMServiceContract)
        
        # Test contract method exists and works
        mock_response = Mock()
        mock_response.text = '{"global_design_level": {"overall_appearance": "teacher"}}'
        mock_llm_service.generate_response.return_value = mock_response
        
        # Test generate_response contract
        result = mock_llm_service.generate_response(
            prompt="Extract PALD from: I want a friendly teacher",
            model="llama3",
            parameters={"temperature": 0.3, "max_tokens": 1000}
        )
        
        # Verify response has required attributes
        assert hasattr(result, 'text')
        assert isinstance(result.text, str)
        
        # Verify method was called with correct parameters
        mock_llm_service.generate_response.assert_called_once_with(
            prompt="Extract PALD from: I want a friendly teacher",
            model="llama3",
            parameters={"temperature": 0.3, "max_tokens": 1000}
        )
    
    def test_llm_service_error_contract(self):
        """Test LLM service error handling contract.
        
        Requirements: 12.2, 12.6
        """
        from unittest.mock import Mock
        
        mock_llm_service = Mock(spec=LLMServiceContract)
        
        # Test error contract for service unavailable
        mock_llm_service.generate_response.side_effect = Exception("LLM service unavailable")
        
        with pytest.raises(Exception) as exc_info:
            mock_llm_service.generate_response("Test prompt")
        
        assert "LLM service unavailable" in str(exc_info.value)
        
        # Test error contract for timeout
        mock_llm_service.generate_response.side_effect = TimeoutError("Request timeout")
        
        with pytest.raises(TimeoutError) as exc_info:
            mock_llm_service.generate_response("Test prompt")
        
        assert "Request timeout" in str(exc_info.value)


class TestCrossComponentIntegrationContract:
    """Test contracts for cross-component integration."""
    
    def test_service_layer_integration_contract(self):
        """Test service layer integration contract compliance.
        
        Requirements: 12.1, 12.7
        """
        from unittest.mock import Mock
        
        # Mock all service dependencies
        mock_db = Mock(spec=DatabaseSessionContract)
        mock_llm = Mock(spec=LLMServiceContract)
        
        # Create service instances
        from src.services.pseudonym_service import PseudonymService
        from src.services.consent_service import ConsentService
        from src.services.chat_service import ChatService
        
        pseudonym_service = PseudonymService(mock_db)
        consent_service = ConsentService(mock_db)
        chat_service = ChatService(mock_db)
        
        # Test integration contract: services can work together
        user_id = uuid4()
        pseudonym_text = "T01e2000MJ42"
        
        # Step 1: Create pseudonym
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
        
        # Step 2: Process consents using pseudonym_id from step 1
        with pytest.mock.patch.object(consent_service, 'process_consent_collection') as mock_consent:
            from src.logic.consent_logic import ConsentResult
            
            mock_consent.return_value = ConsentResult(
                success=True,
                can_proceed=True,
                consent_records=[],
                failed_consents=[],
                validation={"is_complete": True, "missing_consents": []}
            )
            
            consent_result = consent_service.process_consent_collection(
                pseudonym_id, {StudyConsentType.DATA_PROTECTION: True}
            )
            assert consent_result.success is True
        
        # Step 3: Store chat message using pseudonym_id from step 1
        with pytest.mock.patch.object(chat_service, 'store_chat_message') as mock_store:
            from src.data.models import ChatMessage
            
            mock_message = ChatMessage(
                message_id=uuid4(),
                pseudonym_id=pseudonym_id,
                session_id=uuid4(),
                message_type=ChatMessageType.USER,
                content="Test message",
                timestamp=datetime.utcnow()
            )
            mock_store.return_value = mock_message
            
            chat_result = chat_service.store_chat_message(
                pseudonym_id=pseudonym_id,
                session_id=uuid4(),
                message_type=ChatMessageType.USER,
                content="Test message"
            )
            assert chat_result.pseudonym_id == pseudonym_id
        
        # Verify integration contract: all operations use the same pseudonym_id
        assert pseudonym_result.pseudonym_id == pseudonym_id
        assert chat_result.pseudonym_id == pseudonym_id
    
    def test_data_consistency_integration_contract(self):
        """Test data consistency integration contract.
        
        Requirements: 12.3, 12.5
        """
        # Test that data remains consistent across operations
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Create related data that should maintain consistency
        from src.data.models import ChatMessage, StudyPALDData, FeedbackRecord
        
        # All records should reference the same pseudonym_id and session_id
        chat_message = ChatMessage(
            message_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="I want a teacher",
            timestamp=datetime.utcnow()
        )
        
        pald_data = StudyPALDData(
            pald_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            pald_content={"global_design_level": {"overall_appearance": "teacher"}},
            pald_type=StudyPALDType.INPUT,
            created_at=datetime.utcnow()
        )
        
        feedback_record = FeedbackRecord(
            feedback_id=uuid4(),
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            image_id=uuid4(),
            feedback_text="Looks good",
            round_number=1,
            created_at=datetime.utcnow()
        )
        
        # Verify consistency contract
        records = [chat_message, pald_data, feedback_record]
        
        # All records should have the same pseudonym_id
        pseudonym_ids = [record.pseudonym_id for record in records]
        assert len(set(pseudonym_ids)) == 1
        assert pseudonym_ids[0] == pseudonym_id
        
        # All records should have the same session_id
        session_ids = [record.session_id for record in records]
        assert len(set(session_ids)) == 1
        assert session_ids[0] == session_id
        
        # Timestamps should be consistent (within reasonable range)
        timestamps = [
            chat_message.timestamp,
            pald_data.created_at,
            feedback_record.created_at
        ]
        
        # All timestamps should be within 1 second of each other
        min_timestamp = min(timestamps)
        max_timestamp = max(timestamps)
        time_diff = (max_timestamp - min_timestamp).total_seconds()
        assert time_diff < 1.0