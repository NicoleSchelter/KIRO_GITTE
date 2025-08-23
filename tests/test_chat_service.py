"""
Unit tests for ChatService class.
Tests data persistence for chat messages, PALD data, and interaction logging.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from src.data.models import (
    ChatMessage,
    ChatMessageType,
    FeedbackRecord,
    InteractionLog,
    StudyPALDData,
    StudyPALDType,
)
from src.exceptions import DatabaseError, ValidationError
from src.services.chat_service import ChatService


class TestChatService:
    """Test suite for ChatService class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def chat_service(self, mock_db_session):
        """Create ChatService instance with mocked database session."""
        return ChatService(mock_db_session)

    @pytest.fixture
    def sample_pseudonym_id(self):
        """Sample pseudonym ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_session_id(self):
        """Sample session ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_pald_data(self):
        """Sample PALD data for testing."""
        return {
            "global_design_level": {
                "overall_appearance": "friendly teacher",
                "style": "professional"
            },
            "middle_design_level": {
                "physical_attributes": "middle-aged woman",
                "clothing": "business attire"
            }
        }

    def test_store_chat_message_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test successful chat message storage."""
        # Setup
        content = "Hello, I need help with creating a teacher avatar"
        message_type = ChatMessageType.USER
        pald_data = {"test": "data"}
        
        # Execute
        result = chat_service.store_chat_message(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            message_type=message_type,
            content=content,
            pald_data=pald_data
        )
        
        # Verify
        assert isinstance(result, ChatMessage)
        assert result.pseudonym_id == sample_pseudonym_id
        assert result.session_id == sample_session_id
        assert result.message_type == message_type.value
        assert result.content == content
        assert result.pald_data == pald_data
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_store_chat_message_empty_content(self, chat_service, sample_pseudonym_id, sample_session_id):
        """Test chat message storage with empty content."""
        # Execute and verify exception
        with pytest.raises(ValidationError, match="Message content cannot be empty"):
            chat_service.store_chat_message(
                pseudonym_id=sample_pseudonym_id,
                session_id=sample_session_id,
                message_type=ChatMessageType.USER,
                content="   ",  # Only whitespace
            )

    def test_store_chat_message_database_error(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test chat message storage with database error."""
        # Setup
        mock_db_session.commit.side_effect = Exception("Database connection failed")
        
        # Execute and verify exception
        with pytest.raises(DatabaseError, match="Failed to store chat message"):
            chat_service.store_chat_message(
                pseudonym_id=sample_pseudonym_id,
                session_id=sample_session_id,
                message_type=ChatMessageType.USER,
                content="Test message"
            )
        
        # Verify rollback was called
        mock_db_session.rollback.assert_called_once()

    def test_get_chat_history_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test successful chat history retrieval."""
        # Setup
        mock_messages = [
            Mock(spec=ChatMessage, timestamp="2024-01-01 10:00:00"),
            Mock(spec=ChatMessage, timestamp="2024-01-01 10:01:00"),
        ]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_messages
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = chat_service.get_chat_history(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            limit=50
        )
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Verify query construction
        mock_db_session.query.assert_called_once_with(ChatMessage)
        assert mock_query.filter.call_count >= 1  # At least pseudonym filter
        mock_query.order_by.assert_called_once()
        mock_query.limit.assert_called_once_with(50)

    def test_get_chat_history_no_session_filter(self, chat_service, mock_db_session, sample_pseudonym_id):
        """Test chat history retrieval without session filter."""
        # Setup
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = chat_service.get_chat_history(
            pseudonym_id=sample_pseudonym_id,
            session_id=None,  # No session filter
            limit=100
        )
        
        # Verify
        assert isinstance(result, list)
        mock_query.limit.assert_called_once_with(100)

    def test_store_pald_data_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id, sample_pald_data):
        """Test successful PALD data storage."""
        # Setup
        pald_type = StudyPALDType.INPUT
        consistency_score = 0.85
        
        # Execute
        result = chat_service.store_pald_data(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            pald_content=sample_pald_data,
            pald_type=pald_type,
            consistency_score=consistency_score
        )
        
        # Verify
        assert isinstance(result, StudyPALDData)
        assert result.pseudonym_id == sample_pseudonym_id
        assert result.session_id == sample_session_id
        assert result.pald_content == sample_pald_data
        assert result.pald_type == pald_type.value
        assert result.consistency_score == consistency_score
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_store_pald_data_empty_content(self, chat_service, sample_pseudonym_id, sample_session_id):
        """Test PALD data storage with empty content."""
        # Execute and verify exception
        with pytest.raises(ValidationError, match="PALD content cannot be empty"):
            chat_service.store_pald_data(
                pseudonym_id=sample_pseudonym_id,
                session_id=sample_session_id,
                pald_content={},  # Empty content
                pald_type=StudyPALDType.INPUT
            )

    def test_get_pald_data_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test successful PALD data retrieval."""
        # Setup
        mock_pald_records = [
            Mock(spec=StudyPALDData),
            Mock(spec=StudyPALDData),
        ]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_pald_records
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = chat_service.get_pald_data(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            pald_type=StudyPALDType.INPUT,
            limit=25
        )
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Verify query construction
        mock_db_session.query.assert_called_once_with(StudyPALDData)
        assert mock_query.filter.call_count >= 1  # Multiple filters
        mock_query.limit.assert_called_once_with(25)

    def test_store_feedback_record_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test successful feedback record storage."""
        # Setup
        feedback_text = "Please make the teacher look more friendly"
        round_number = 2
        image_id = uuid4()
        feedback_pald = {"feedback": "data"}
        
        # Execute
        result = chat_service.store_feedback_record(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            feedback_text=feedback_text,
            round_number=round_number,
            image_id=image_id,
            feedback_pald=feedback_pald
        )
        
        # Verify
        assert isinstance(result, FeedbackRecord)
        assert result.pseudonym_id == sample_pseudonym_id
        assert result.session_id == sample_session_id
        assert result.feedback_text == feedback_text
        assert result.round_number == round_number
        assert result.image_id == image_id
        assert result.feedback_pald == feedback_pald
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_store_feedback_record_empty_text(self, chat_service, sample_pseudonym_id, sample_session_id):
        """Test feedback record storage with empty text."""
        # Execute and verify exception
        with pytest.raises(ValidationError, match="Feedback text cannot be empty"):
            chat_service.store_feedback_record(
                pseudonym_id=sample_pseudonym_id,
                session_id=sample_session_id,
                feedback_text="   ",  # Only whitespace
                round_number=1
            )

    def test_store_feedback_record_invalid_round(self, chat_service, sample_pseudonym_id, sample_session_id):
        """Test feedback record storage with invalid round number."""
        # Execute and verify exception
        with pytest.raises(ValidationError, match="Round number must be positive"):
            chat_service.store_feedback_record(
                pseudonym_id=sample_pseudonym_id,
                session_id=sample_session_id,
                feedback_text="Test feedback",
                round_number=0  # Invalid round number
            )

    def test_get_feedback_records_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test successful feedback records retrieval."""
        # Setup
        mock_feedback_records = [
            Mock(spec=FeedbackRecord),
            Mock(spec=FeedbackRecord),
        ]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_feedback_records
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = chat_service.get_feedback_records(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            limit=30
        )
        
        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Verify query construction
        mock_db_session.query.assert_called_once_with(FeedbackRecord)
        mock_query.limit.assert_called_once_with(30)

    def test_log_interaction_metadata_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test successful interaction metadata logging."""
        # Setup
        interaction_type = "pald_extraction"
        model_used = "llama3"
        parameters = {"temperature": 0.3, "max_tokens": 1000}
        latency_ms = 500
        prompt = "Extract PALD from this text"
        response = "PALD data extracted"
        token_usage = {"input_tokens": 50, "output_tokens": 100}
        
        # Execute
        result = chat_service.log_interaction_metadata(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            interaction_type=interaction_type,
            model_used=model_used,
            parameters=parameters,
            latency_ms=latency_ms,
            prompt=prompt,
            response=response,
            token_usage=token_usage
        )
        
        # Verify
        assert isinstance(result, InteractionLog)
        assert result.pseudonym_id == sample_pseudonym_id
        assert result.session_id == sample_session_id
        assert result.interaction_type == interaction_type
        assert result.model_used == model_used
        assert result.parameters == parameters
        assert result.latency_ms == latency_ms
        assert result.prompt == prompt
        assert result.response == response
        assert result.token_usage == token_usage
        
        # Verify database operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_log_interaction_metadata_minimal(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test interaction metadata logging with minimal required fields."""
        # Execute
        result = chat_service.log_interaction_metadata(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id,
            interaction_type="consistency_check",
            model_used="llama3",
            parameters={"temperature": 0.5},
            latency_ms=200
        )
        
        # Verify
        assert isinstance(result, InteractionLog)
        assert result.prompt is None
        assert result.response is None
        assert result.token_usage is None

    def test_get_session_statistics_success(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test successful session statistics retrieval."""
        # Setup mock query results
        def mock_query_count(model_class):
            mock_query = Mock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = 5  # Mock count
            return mock_query
        
        mock_db_session.query.side_effect = mock_query_count
        
        # Execute
        result = chat_service.get_session_statistics(
            pseudonym_id=sample_pseudonym_id,
            session_id=sample_session_id
        )
        
        # Verify
        assert isinstance(result, dict)
        assert "message_counts" in result
        assert "pald_counts" in result
        assert "feedback_count" in result
        assert "interaction_count" in result
        assert "total_messages" in result
        assert "total_pald_extractions" in result
        
        # Verify structure of nested counts
        assert isinstance(result["message_counts"], dict)
        assert isinstance(result["pald_counts"], dict)
        
        # Check that all message types are included
        for msg_type in ChatMessageType:
            assert msg_type.value in result["message_counts"]
        
        # Check that all PALD types are included
        for pald_type in StudyPALDType:
            assert pald_type.value in result["pald_counts"]

    def test_get_session_statistics_database_error(self, chat_service, mock_db_session, sample_pseudonym_id, sample_session_id):
        """Test session statistics retrieval with database error."""
        # Setup
        mock_db_session.query.side_effect = Exception("Database query failed")
        
        # Execute and verify exception
        with pytest.raises(DatabaseError, match="Failed to get session statistics"):
            chat_service.get_session_statistics(
                pseudonym_id=sample_pseudonym_id,
                session_id=sample_session_id
            )


class TestChatServiceIntegration:
    """Integration tests for ChatService with realistic scenarios."""

    @pytest.fixture
    def chat_service_with_mock_db(self):
        """Create ChatService with a more realistic mock database."""
        mock_db = Mock(spec=Session)
        return ChatService(mock_db), mock_db

    def test_complete_chat_session_workflow(self, chat_service_with_mock_db):
        """Test complete workflow of storing and retrieving chat session data."""
        chat_service, mock_db = chat_service_with_mock_db
        
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock successful database operations
        mock_db.commit.return_value = None
        mock_db.rollback.return_value = None
        
        # Test storing user message
        user_message = chat_service.store_chat_message(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="Create a friendly teacher avatar"
        )
        assert isinstance(user_message, ChatMessage)
        
        # Test storing PALD data
        pald_data = {
            "global_design_level": {"overall_appearance": "friendly teacher"}
        }
        stored_pald = chat_service.store_pald_data(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            pald_content=pald_data,
            pald_type=StudyPALDType.INPUT
        )
        assert isinstance(stored_pald, StudyPALDData)
        
        # Test storing assistant response
        assistant_message = chat_service.store_chat_message(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.ASSISTANT,
            content="I'll help you create a friendly teacher avatar."
        )
        assert isinstance(assistant_message, ChatMessage)
        
        # Test storing feedback
        feedback = chat_service.store_feedback_record(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            feedback_text="Make the teacher look more professional",
            round_number=1
        )
        assert isinstance(feedback, FeedbackRecord)
        
        # Test logging interaction
        interaction_log = chat_service.log_interaction_metadata(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type="pald_extraction",
            model_used="llama3",
            parameters={"temperature": 0.3},
            latency_ms=450
        )
        assert isinstance(interaction_log, InteractionLog)
        
        # Verify all database operations were called
        assert mock_db.add.call_count == 5  # 5 objects stored
        assert mock_db.commit.call_count == 5  # 5 commits

    def test_error_recovery_workflow(self, chat_service_with_mock_db):
        """Test error recovery in chat service operations."""
        chat_service, mock_db = chat_service_with_mock_db
        
        # Setup
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Test database error and recovery
        mock_db.commit.side_effect = [Exception("Connection lost"), None]  # Fail first, succeed second
        
        # First operation should fail
        with pytest.raises(DatabaseError):
            chat_service.store_chat_message(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                message_type=ChatMessageType.USER,
                content="Test message"
            )
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()
        
        # Second operation should succeed
        mock_db.reset_mock()  # Reset mock call counts
        result = chat_service.store_chat_message(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content="Test message retry"
        )
        
        assert isinstance(result, ChatMessage)
        mock_db.commit.assert_called_once()