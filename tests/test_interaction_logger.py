"""
Unit tests for InteractionLogger service.
Tests comprehensive logging functionality for study participation.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch

from src.services.interaction_logger import InteractionLogger, InteractionLogEntry
from src.data.models import InteractionLog
from src.data.schemas import InteractionLogCreate, InteractionLogResponse


class TestInteractionLogEntry:
    """Test InteractionLogEntry context manager."""

    def test_entry_initialization(self):
        """Test interaction log entry initialization."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        interaction_type = "chat"
        model_used = "gpt-4"
        parameters = {"temperature": 0.7}

        entry = InteractionLogEntry(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type=interaction_type,
            model_used=model_used,
            parameters=parameters,
        )

        assert entry.pseudonym_id == pseudonym_id
        assert entry.session_id == session_id
        assert entry.interaction_type == interaction_type
        assert entry.model_used == model_used
        assert entry.parameters == parameters
        assert entry.log_id is None
        assert entry.prompt is None
        assert entry.response is None
        assert entry.token_usage is None
        assert not entry._finalized

    def test_entry_context_manager_success(self):
        """Test interaction log entry context manager success path."""
        mock_logger = Mock(spec=InteractionLogger)
        mock_logger.initialize_log.return_value = uuid4()
        mock_logger.finalize_log.return_value = True

        entry = InteractionLogEntry(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_type="chat",
            model_used="gpt-4",
            parameters={},
            interaction_logger=mock_logger,
        )

        with entry:
            entry.set_prompt("Test prompt")
            entry.set_response("Test response")
            entry.set_token_usage({"input": 10, "output": 20})

        assert entry.prompt == "Test prompt"
        assert entry.response == "Test response"
        assert entry.token_usage == {"input": 10, "output": 20}
        assert entry._finalized
        mock_logger.initialize_log.assert_called_once()
        mock_logger.finalize_log.assert_called_once()

    def test_entry_context_manager_exception(self):
        """Test interaction log entry context manager with exception."""
        mock_logger = Mock(spec=InteractionLogger)
        mock_logger.initialize_log.return_value = uuid4()
        mock_logger.finalize_log.return_value = True

        entry = InteractionLogEntry(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_type="chat",
            model_used="gpt-4",
            parameters={},
            interaction_logger=mock_logger,
        )

        with pytest.raises(ValueError):
            with entry:
                raise ValueError("Test exception")

        assert entry._finalized
        mock_logger.finalize_log.assert_called_once()

    def test_add_parameter(self):
        """Test adding parameters to entry."""
        mock_logger = Mock(spec=InteractionLogger)
        mock_logger.update_parameters.return_value = True

        entry = InteractionLogEntry(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_type="chat",
            model_used="gpt-4",
            parameters={"temperature": 0.7},
            interaction_logger=mock_logger,
        )
        entry.log_id = uuid4()

        entry.add_parameter("max_tokens", 100)

        assert entry.parameters["max_tokens"] == 100
        mock_logger.update_parameters.assert_called_once_with(
            entry.log_id, {"temperature": 0.7, "max_tokens": 100}
        )


class TestInteractionLogger:
    """Test InteractionLogger service."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def mock_repository(self):
        """Mock interaction log repository."""
        return Mock()

    @pytest.fixture
    def interaction_logger(self, mock_session, mock_repository):
        """Create InteractionLogger instance with mocked dependencies."""
        logger = InteractionLogger(mock_session)
        logger.repository = mock_repository
        return logger

    def test_initialization(self, mock_session):
        """Test InteractionLogger initialization."""
        with patch('src.services.interaction_logger.InteractionLogRepository') as mock_repo_class:
            logger = InteractionLogger(mock_session)
            assert logger.db_session == mock_session
            mock_repo_class.assert_called_once_with(mock_session)

    def test_create_interaction_context(self, interaction_logger):
        """Test creating interaction context."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        interaction_type = "pald_extraction"
        model_used = "gpt-4"
        parameters = {"temperature": 0.5}

        with patch.object(interaction_logger, 'initialize_log', return_value=uuid4()) as mock_init:
            with patch.object(interaction_logger, 'finalize_log', return_value=True) as mock_finalize:
                with interaction_logger.create_interaction_context(
                    pseudonym_id=pseudonym_id,
                    session_id=session_id,
                    interaction_type=interaction_type,
                    model_used=model_used,
                    parameters=parameters,
                ) as entry:
                    assert isinstance(entry, InteractionLogEntry)
                    assert entry.pseudonym_id == pseudonym_id
                    assert entry.session_id == session_id
                    assert entry.interaction_type == interaction_type
                    assert entry.model_used == model_used
                    assert entry.parameters == parameters

                mock_init.assert_called_once()
                mock_finalize.assert_called_once()

    def test_initialize_log_success(self, interaction_logger, mock_repository):
        """Test successful log initialization."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        log_id = uuid4()
        
        mock_log = Mock()
        mock_log.log_id = log_id
        mock_repository.create.return_value = mock_log

        result = interaction_logger.initialize_log(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type="chat",
            model_used="gpt-4",
            parameters={"temperature": 0.7},
        )

        assert result == log_id
        mock_repository.create.assert_called_once()
        interaction_logger.db_session.commit.assert_called_once()

    def test_initialize_log_failure(self, interaction_logger, mock_repository):
        """Test log initialization failure."""
        mock_repository.create.return_value = None

        result = interaction_logger.initialize_log(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_type="chat",
            model_used="gpt-4",
            parameters={},
        )

        assert result is None
        # No rollback called when repository returns None (not an exception)

    def test_finalize_log_success(self, interaction_logger, mock_repository):
        """Test successful log finalization."""
        log_id = uuid4()
        mock_log = Mock()
        mock_repository.get_by_id.return_value = mock_log
        mock_repository.update.return_value = mock_log

        result = interaction_logger.finalize_log(
            log_id=log_id,
            prompt="Test prompt",
            response="Test response",
            token_usage={"input": 10, "output": 20},
            latency_ms=1500,
        )

        assert result is True
        mock_repository.update.assert_called_once_with(
            log_id,
            {
                "prompt": "Test prompt",
                "response": "Test response",
                "token_usage": {"input": 10, "output": 20},
                "latency_ms": 1500,
            },
        )
        interaction_logger.db_session.commit.assert_called_once()

    def test_finalize_log_not_found(self, interaction_logger, mock_repository):
        """Test log finalization when log not found."""
        log_id = uuid4()
        mock_repository.get_by_id.return_value = None

        result = interaction_logger.finalize_log(log_id=log_id)

        assert result is False
        mock_repository.update.assert_not_called()

    def test_log_ai_interaction_success(self, interaction_logger, mock_repository):
        """Test successful AI interaction logging."""
        log_id = uuid4()
        mock_log = Mock()
        mock_log.log_id = log_id
        mock_repository.create.return_value = mock_log

        result = interaction_logger.log_ai_interaction(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_type="image_generation",
            model_used="stable-diffusion",
            prompt="Generate an image",
            response="Image generated successfully",
            parameters={"steps": 50, "guidance_scale": 7.5},
            token_usage={"input": 15, "output": 0},
            latency_ms=3000,
        )

        assert result == log_id
        mock_repository.create.assert_called_once()
        interaction_logger.db_session.commit.assert_called_once()

    def test_get_session_interactions(self, interaction_logger, mock_repository):
        """Test getting session interactions."""
        session_id = uuid4()
        mock_logs = [
            Mock(
                log_id=uuid4(),
                pseudonym_id=uuid4(),
                session_id=session_id,
                interaction_type="chat",
                prompt="Hello",
                response="Hi there",
                model_used="gpt-4",
                parameters={"temperature": 0.7},
                token_usage={"input": 5, "output": 10},
                latency_ms=1000,
                timestamp=datetime.utcnow(),
            )
        ]
        mock_repository.get_by_session.return_value = mock_logs

        result = interaction_logger.get_session_interactions(session_id)

        assert len(result) == 1
        assert isinstance(result[0], InteractionLogResponse)
        assert result[0].session_id == session_id
        mock_repository.get_by_session.assert_called_once_with(session_id)

    def test_get_pseudonym_interactions(self, interaction_logger, mock_repository):
        """Test getting pseudonym interactions."""
        pseudonym_id = uuid4()
        mock_logs = [
            Mock(
                log_id=uuid4(),
                pseudonym_id=pseudonym_id,
                session_id=uuid4(),
                interaction_type="pald_extraction",
                prompt="Extract PALD",
                response="PALD extracted",
                model_used="gpt-4",
                parameters={"temperature": 0.3},
                token_usage={"input": 20, "output": 15},
                latency_ms=2000,
                timestamp=datetime.utcnow(),
            )
        ]
        mock_repository.get_by_pseudonym.return_value = mock_logs

        result = interaction_logger.get_pseudonym_interactions(pseudonym_id, limit=10)

        assert len(result) == 1
        assert isinstance(result[0], InteractionLogResponse)
        assert result[0].pseudonym_id == pseudonym_id
        mock_repository.get_by_pseudonym.assert_called_once_with(pseudonym_id, limit=10)

    def test_export_interaction_data(self, interaction_logger, mock_repository):
        """Test exporting interaction data."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        mock_logs = [
            Mock(
                log_id=uuid4(),
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_type="feedback",
                prompt="Rate this image",
                response="Rating: 4/5",
                model_used="gpt-4",
                parameters={"temperature": 0.1},
                token_usage={"input": 8, "output": 5},
                latency_ms=800,
                timestamp=datetime.utcnow(),
            )
        ]
        mock_repository.get_filtered.return_value = mock_logs

        result = interaction_logger.export_interaction_data(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_types=["feedback"],
        )

        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["pseudonym_id"] == str(pseudonym_id)
        assert result[0]["session_id"] == str(session_id)
        assert result[0]["interaction_type"] == "feedback"
        mock_repository.get_filtered.assert_called_once()

    def test_get_interaction_statistics(self, interaction_logger, mock_repository):
        """Test getting interaction statistics."""
        mock_logs = [
            Mock(
                interaction_type="chat",
                model_used="gpt-4",
                latency_ms=1000,
                token_usage={"input": 10, "output": 15},
                session_id=uuid4(),
            ),
            Mock(
                interaction_type="pald_extraction",
                model_used="gpt-4",
                latency_ms=2000,
                token_usage={"input": 20, "output": 10},
                session_id=uuid4(),
            ),
            Mock(
                interaction_type="chat",
                model_used="claude-3",
                latency_ms=1500,
                token_usage={"input": 15, "output": 20},
                session_id=uuid4(),
            ),
        ]
        mock_repository.get_filtered.return_value = mock_logs

        result = interaction_logger.get_interaction_statistics()

        assert result["total_interactions"] == 3
        assert result["interaction_type_breakdown"]["chat"] == 2
        assert result["interaction_type_breakdown"]["pald_extraction"] == 1
        assert result["model_usage_breakdown"]["gpt-4"] == 2
        assert result["model_usage_breakdown"]["claude-3"] == 1
        assert result["average_latency_ms"] == 1500.0
        assert result["total_tokens"] == 90  # Sum of all input + output tokens
        assert result["unique_sessions"] == 3

    def test_get_interaction_statistics_empty(self, interaction_logger, mock_repository):
        """Test getting interaction statistics with no data."""
        mock_repository.get_filtered.return_value = []

        result = interaction_logger.get_interaction_statistics()

        assert result["total_interactions"] == 0
        assert result["interaction_type_breakdown"] == {}
        assert result["model_usage_breakdown"] == {}
        assert result["average_latency_ms"] == 0.0
        assert result["total_tokens"] == 0
        assert result["unique_sessions"] == 0

    def test_delete_pseudonym_data(self, interaction_logger, mock_repository):
        """Test deleting pseudonym data for GDPR compliance."""
        pseudonym_id = uuid4()
        mock_repository.delete_by_pseudonym.return_value = 5

        result = interaction_logger.delete_pseudonym_data(pseudonym_id)

        assert result is True
        mock_repository.delete_by_pseudonym.assert_called_once_with(pseudonym_id)
        interaction_logger.db_session.commit.assert_called_once()

    def test_delete_pseudonym_data_failure(self, interaction_logger, mock_repository):
        """Test deleting pseudonym data failure."""
        pseudonym_id = uuid4()
        mock_repository.delete_by_pseudonym.side_effect = Exception("Database error")

        result = interaction_logger.delete_pseudonym_data(pseudonym_id)

        assert result is False
        interaction_logger.db_session.rollback.assert_called_once()

    def test_update_parameters(self, interaction_logger, mock_repository):
        """Test updating log parameters."""
        log_id = uuid4()
        parameters = {"temperature": 0.8, "max_tokens": 200}
        mock_repository.update.return_value = Mock()

        result = interaction_logger.update_parameters(log_id, parameters)

        assert result is True
        mock_repository.update.assert_called_once_with(log_id, {"parameters": parameters})
        interaction_logger.db_session.commit.assert_called_once()


class TestInteractionLoggerIntegration:
    """Integration tests for InteractionLogger with real-like scenarios."""

    def test_complete_interaction_flow(self):
        """Test complete interaction logging flow."""
        mock_session = Mock()
        mock_repository = Mock()
        
        logger = InteractionLogger(mock_session)
        logger.repository = mock_repository

        # Mock successful initialization
        log_id = uuid4()
        mock_log = Mock()
        mock_log.log_id = log_id
        mock_repository.create.return_value = mock_log
        mock_repository.get_by_id.return_value = mock_log
        mock_repository.update.return_value = mock_log

        pseudonym_id = uuid4()
        session_id = uuid4()

        # Test context manager flow
        with logger.create_interaction_context(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type="chat",
            model_used="gpt-4",
            parameters={"temperature": 0.7},
        ) as entry:
            entry.set_prompt("What is AI?")
            entry.set_response("AI is artificial intelligence...")
            entry.set_token_usage({"input": 15, "output": 25})
            entry.add_parameter("max_tokens", 100)

        # Verify initialization was called
        assert mock_repository.create.call_count == 1
        
        # Verify finalization was called
        assert mock_repository.update.call_count >= 1
        
        # Verify session operations
        assert mock_session.commit.call_count >= 1

    def test_error_handling_in_context(self):
        """Test error handling in interaction context."""
        mock_session = Mock()
        mock_repository = Mock()
        
        logger = InteractionLogger(mock_session)
        logger.repository = mock_repository

        # Mock initialization
        log_id = uuid4()
        mock_log = Mock()
        mock_log.log_id = log_id
        mock_repository.create.return_value = mock_log
        mock_repository.update.return_value = mock_log

        with pytest.raises(ValueError):
            with logger.create_interaction_context(
                pseudonym_id=uuid4(),
                session_id=uuid4(),
                interaction_type="chat",
                model_used="gpt-4",
            ) as entry:
                raise ValueError("Simulated error")

        # Verify finalization was still called despite error
        assert mock_repository.update.call_count >= 1


# Test convenience functions
class TestConvenienceFunctions:
    """Test convenience functions for interaction logging."""

    def test_create_interaction_context_function(self):
        """Test create_interaction_context convenience function."""
        from src.services.interaction_logger import create_interaction_context
        
        mock_session = Mock()
        
        with patch('src.services.interaction_logger.InteractionLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            mock_context = Mock()
            mock_logger.create_interaction_context.return_value = mock_context

            result = create_interaction_context(
                db_session=mock_session,
                pseudonym_id=uuid4(),
                session_id=uuid4(),
                interaction_type="chat",
                model_used="gpt-4",
            )

            assert result == mock_context
            mock_logger_class.assert_called_once_with(mock_session)
            mock_logger.create_interaction_context.assert_called_once()

    def test_log_ai_interaction_function(self):
        """Test log_ai_interaction convenience function."""
        from src.services.interaction_logger import log_ai_interaction
        
        mock_session = Mock()
        log_id = uuid4()
        
        with patch('src.services.interaction_logger.InteractionLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            mock_logger.log_ai_interaction.return_value = log_id

            result = log_ai_interaction(
                db_session=mock_session,
                pseudonym_id=uuid4(),
                session_id=uuid4(),
                interaction_type="chat",
                model_used="gpt-4",
                prompt="Hello",
                response="Hi",
                parameters={},
            )

            assert result == log_id
            mock_logger_class.assert_called_once_with(mock_session)
            mock_logger.log_ai_interaction.assert_called_once()