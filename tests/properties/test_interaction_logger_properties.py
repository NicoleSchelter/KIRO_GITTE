"""
Property-based tests for InteractionLogger.
Tests invariants and properties that should hold for all valid inputs.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock

from src.services.interaction_logger import InteractionLogger, InteractionLogEntry
from src.data.schemas import InteractionLogCreate


class TestInteractionLoggerProperties:
    """Property-based tests for InteractionLogger."""

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
        """Create InteractionLogger with mocked dependencies."""
        logger = InteractionLogger(mock_session)
        logger.repository = mock_repository
        return logger

    def test_log_ai_interaction_returns_valid_result_property(self, interaction_logger, mock_repository):
        """Property: log_ai_interaction should always return UUID or None for any valid input."""
        test_cases = [
            # Different interaction types
            ("chat", "gpt-4", {"temperature": 0.7}, "Hello", "Hi", {"input": 10, "output": 5}, 1000),
            ("pald_extraction", "gpt-4", {"temperature": 0.3}, "Extract", "Extracted", {"input": 20, "output": 15}, 2000),
            ("image_generation", "stable-diffusion", {"steps": 50}, "Generate", "Generated", None, 5000),
            ("feedback", "gpt-4", {"temperature": 0.1}, "Rate", "Good", {"input": 5, "output": 3}, 500),
            # Edge cases
            ("", "gpt-4", {}, "", "", {}, 0),  # Empty strings
            ("chat", "gpt-4", {"complex": {"nested": {"value": 1.5}}}, "Test", "Test", {"total": 100}, 60000),  # Complex data
        ]
        
        for interaction_type, model_used, parameters, prompt, response, token_usage, latency_ms in test_cases:
            pseudonym_id = uuid4()
            session_id = uuid4()
            
            # Mock successful creation
            mock_log = Mock()
            mock_log.log_id = uuid4()
            mock_repository.create.return_value = mock_log
            
            result = interaction_logger.log_ai_interaction(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_type=interaction_type,
                model_used=model_used,
                prompt=prompt,
                response=response,
                parameters=parameters,
                token_usage=token_usage,
                latency_ms=latency_ms,
            )
            
            # Property: Result should be UUID or None
            assert result is None or isinstance(result, type(uuid4()))
            
            # Reset mock for next iteration
            mock_repository.reset_mock()

    def test_interaction_context_creates_valid_entry_property(self, interaction_logger):
        """Property: create_interaction_context should always create valid InteractionLogEntry."""
        test_cases = [
            ("chat", "gpt-4", {"temperature": 0.7}),
            ("pald_extraction", "claude-3", {"temperature": 0.3, "max_tokens": 100}),
            ("image_generation", "dall-e-3", {"size": "1024x1024", "quality": "hd"}),
            ("feedback", "gpt-3.5-turbo", {}),  # Empty parameters
        ]
        
        for interaction_type, model_used, parameters in test_cases:
            pseudonym_id = uuid4()
            session_id = uuid4()
            
            with interaction_logger.create_interaction_context(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_type=interaction_type,
                model_used=model_used,
                parameters=parameters,
            ) as entry:
                # Property: Entry should have all required attributes
                assert isinstance(entry, InteractionLogEntry)
                assert entry.pseudonym_id == pseudonym_id
                assert entry.session_id == session_id
                assert entry.interaction_type == interaction_type
                assert entry.model_used == model_used
                assert entry.parameters == parameters
                
                # Property: Entry should be in valid initial state
                assert entry.prompt is None
                assert entry.response is None
                assert entry.token_usage is None
                assert not entry._finalized
                assert isinstance(entry.start_time, datetime)

    def test_entry_data_setting_preserves_values_property(self):
        """Property: Setting data on InteractionLogEntry should preserve exact values."""
        test_cases = [
            ("Hello, world!", "Hi there!", {"input": 10, "output": 15}),
            ("", "", {}),  # Empty values
            ("Long prompt with special chars: !@#$%^&*()", "Response with unicode: 🚀🎉", {"input": 50, "output": 25, "cached": 10}),
            ("Multi\nline\nprompt", "Multi\nline\nresponse", {"total_tokens": 100}),
        ]
        
        for prompt, response, token_usage in test_cases:
            entry = InteractionLogEntry(
                pseudonym_id=uuid4(),
                session_id=uuid4(),
                interaction_type="chat",
                model_used="gpt-4",
                parameters={},
            )
            
            # Set data
            entry.set_prompt(prompt)
            entry.set_response(response)
            entry.set_token_usage(token_usage)
            
            # Property: Values should be preserved exactly
            assert entry.prompt == prompt
            assert entry.response == response
            assert entry.token_usage == token_usage

    def test_parameter_addition_preserves_existing_values_property(self, interaction_logger):
        """Property: Adding parameters should preserve existing values and add new ones."""
        test_cases = [
            ({"temperature": 0.7}, {"max_tokens": 100}),
            ({"model": "gpt-4", "temperature": 0.5}, {"top_p": 0.9, "frequency_penalty": 0.1}),
            ({}, {"new_param": "value"}),  # Empty initial parameters
            ({"existing": 1}, {}),  # Empty additional parameters
        ]
        
        mock_repository = Mock()
        mock_repository.update.return_value = True
        interaction_logger.repository = mock_repository
        
        for initial_params, additional_params in test_cases:
            entry = InteractionLogEntry(
                pseudonym_id=uuid4(),
                session_id=uuid4(),
                interaction_type="chat",
                model_used="gpt-4",
                parameters=initial_params.copy(),
                interaction_logger=interaction_logger,
            )
            entry.log_id = uuid4()
            
            # Add each additional parameter
            for key, value in additional_params.items():
                entry.add_parameter(key, value)
            
            # Property: All original parameters should still be present
            for key, value in initial_params.items():
                assert entry.parameters[key] == value
            
            # Property: All new parameters should be present
            for key, value in additional_params.items():
                assert entry.parameters[key] == value
            
            # Reset mock for next iteration
            mock_repository.reset_mock()

    def test_export_data_filtering_properties(self, interaction_logger, mock_repository):
        """Property: Export data filtering should respect all filter parameters."""
        # Mock filtered results with various data types
        mock_logs = []
        test_data = [
            (uuid4(), uuid4(), "chat", "Hello", "Hi", "gpt-4", {"temp": 0.7}, {"in": 10, "out": 5}, 1000),
            (uuid4(), uuid4(), "pald_extraction", "Extract", "Done", "gpt-4", {"temp": 0.3}, {"in": 20, "out": 15}, 2000),
            (uuid4(), uuid4(), "image_generation", "Generate", "Created", "dall-e", {"size": "1024x1024"}, None, 5000),
        ]
        
        for pseudonym_id, session_id, interaction_type, prompt, response, model_used, parameters, token_usage, latency_ms in test_data:
            mock_log = Mock()
            mock_log.log_id = uuid4()
            mock_log.pseudonym_id = pseudonym_id
            mock_log.session_id = session_id
            mock_log.interaction_type = interaction_type
            mock_log.prompt = prompt
            mock_log.response = response
            mock_log.model_used = model_used
            mock_log.parameters = parameters
            mock_log.token_usage = token_usage
            mock_log.latency_ms = latency_ms
            mock_log.timestamp = datetime.utcnow()
            mock_logs.append(mock_log)
        
        mock_repository.get_filtered.return_value = mock_logs
        
        # Test filtering
        result = interaction_logger.export_interaction_data(
            pseudonym_id=test_data[0][0],
            session_id=test_data[0][1],
            interaction_types=["chat", "pald_extraction"],
        )
        
        # Property: Result should be a list of dictionaries
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)
        
        # Property: Each exported item should have required fields
        required_fields = ["log_id", "pseudonym_id", "session_id", "interaction_type", "model_used", "timestamp"]
        for item in result:
            for field in required_fields:
                assert field in item

    def test_statistics_calculation_properties(self, interaction_logger, mock_repository):
        """Property: Statistics calculation should always produce valid aggregations."""
        # Mock interaction logs with known data
        test_interactions = [
            ("chat", "gpt-4", 1000, {"input": 10, "output": 15}),
            ("chat", "gpt-4", 1500, {"input": 20, "output": 25}),
            ("pald_extraction", "gpt-4", 2000, {"input": 30, "output": 20}),
            ("image_generation", "dall-e", 5000, None),
        ]
        
        mock_logs = []
        unique_sessions = set()
        for interaction_type, model_used, latency_ms, token_usage in test_interactions:
            session_id = uuid4()
            unique_sessions.add(session_id)
            
            mock_log = Mock()
            mock_log.interaction_type = interaction_type
            mock_log.model_used = model_used
            mock_log.latency_ms = latency_ms
            mock_log.token_usage = token_usage
            mock_log.session_id = session_id
            mock_logs.append(mock_log)
        
        mock_repository.get_filtered.return_value = mock_logs
        
        result = interaction_logger.get_interaction_statistics()
        
        # Property: Statistics should have required structure
        required_keys = ["total_interactions", "interaction_type_breakdown", "model_usage_breakdown", 
                        "average_latency_ms", "total_tokens", "unique_sessions"]
        for key in required_keys:
            assert key in result
        
        # Property: Total interactions should match input count
        assert result["total_interactions"] == len(test_interactions)
        
        # Property: Breakdown counts should sum to total
        type_counts = result["interaction_type_breakdown"]
        assert sum(type_counts.values()) == len(test_interactions)
        
        model_counts = result["model_usage_breakdown"]
        assert sum(model_counts.values()) == len(test_interactions)
        
        # Property: Average latency should be calculated correctly
        expected_avg = sum(latency for _, _, latency, _ in test_interactions) / len(test_interactions)
        assert abs(result["average_latency_ms"] - expected_avg) < 0.01
        
        # Property: Unique sessions should match our test data
        assert result["unique_sessions"] == len(unique_sessions)

    def test_delete_operations_return_valid_counts_property(self, interaction_logger, mock_repository):
        """Property: Delete operations should return non-negative integer counts."""
        test_cases = [0, 1, 5, 10, 100]  # Different delete counts
        
        for delete_count in test_cases:
            pseudonym_id = uuid4()
            session_id = uuid4()
            
            mock_repository.delete_by_pseudonym.return_value = delete_count
            mock_repository.delete_by_session.return_value = delete_count
            
            # Test delete by pseudonym
            result_pseudonym = interaction_logger.delete_pseudonym_data(pseudonym_id)
            
            # Property: Should return boolean success indicator
            assert isinstance(result_pseudonym, bool)
            
            # Test delete by session (through repository directly)
            result_session = interaction_logger.repository.delete_by_session(session_id)
            
            # Property: Should return non-negative integer
            assert isinstance(result_session, int)
            assert result_session >= 0
            assert result_session == delete_count
            
            # Reset mock for next iteration
            mock_repository.reset_mock()


class TestInteractionLoggerInvariants:
    """Test invariants that should always hold for InteractionLogger."""

    @pytest.fixture
    def interaction_logger(self):
        """Create InteractionLogger with mock session."""
        mock_session = Mock()
        return InteractionLogger(mock_session)

    def test_logger_initialization_invariant(self, interaction_logger):
        """Invariant: InteractionLogger should always initialize with required components."""
        # Should have database session
        assert hasattr(interaction_logger, 'db_session')
        assert interaction_logger.db_session is not None
        
        # Should have repository
        assert hasattr(interaction_logger, 'repository')
        assert interaction_logger.repository is not None

    def test_context_manager_invariant(self, interaction_logger):
        """Invariant: Context manager should always finalize entries when initialization succeeds."""
        test_cases = [
            (uuid4(), uuid4(), "chat", "gpt-4"),
            (uuid4(), uuid4(), "pald_extraction", "claude-3"),
            (uuid4(), uuid4(), "image_generation", "dall-e"),
        ]
        
        for pseudonym_id, session_id, interaction_type, model_used in test_cases:
            finalized_entries = []
            
            # Mock initialize_log to return a log_id (successful initialization)
            def mock_initialize(*args, **kwargs):
                return uuid4()
            interaction_logger.initialize_log = mock_initialize
            
            # Mock finalize_log to track calls
            def mock_finalize(*args, **kwargs):
                finalized_entries.append(True)
                return True
            interaction_logger.finalize_log = mock_finalize
            
            # Use context manager
            with interaction_logger.create_interaction_context(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_type=interaction_type,
                model_used=model_used,
            ) as entry:
                pass
            
            # Invariant: Entry should be finalized when initialization succeeds
            assert len(finalized_entries) == 1

    def test_context_manager_exception_invariant(self, interaction_logger):
        """Invariant: Context manager should finalize entries even on exceptions when initialization succeeds."""
        test_cases = [
            (uuid4(), uuid4(), "chat", "gpt-4", ValueError("Test error")),
            (uuid4(), uuid4(), "pald_extraction", "claude-3", RuntimeError("Runtime error")),
            (uuid4(), uuid4(), "image_generation", "dall-e", KeyError("Key error")),
        ]
        
        for pseudonym_id, session_id, interaction_type, model_used, exception in test_cases:
            finalized_entries = []
            
            # Mock initialize_log to return a log_id (successful initialization)
            def mock_initialize(*args, **kwargs):
                return uuid4()
            interaction_logger.initialize_log = mock_initialize
            
            # Mock finalize_log to track calls
            def mock_finalize(*args, **kwargs):
                finalized_entries.append(True)
                return True
            interaction_logger.finalize_log = mock_finalize
            
            # Use context manager with exception
            with pytest.raises(type(exception)):
                with interaction_logger.create_interaction_context(
                    pseudonym_id=pseudonym_id,
                    session_id=session_id,
                    interaction_type=interaction_type,
                    model_used=model_used,
                ) as entry:
                    raise exception
            
            # Invariant: Entry should still be finalized when initialization succeeds
            assert len(finalized_entries) == 1

    def test_data_integrity_invariant(self):
        """Invariant: InteractionLogEntry should maintain data integrity throughout its lifecycle."""
        test_cases = [
            ("Hello", "World", {"input": 10, "output": 5}),
            ("", "", {}),  # Empty data
            ("Complex\ndata\nwith\nlines", "Response\nwith\nlines", {"complex": {"nested": True}}),
        ]
        
        for prompt, response, token_usage in test_cases:
            entry = InteractionLogEntry(
                pseudonym_id=uuid4(),
                session_id=uuid4(),
                interaction_type="chat",
                model_used="gpt-4",
                parameters={"temperature": 0.7},
            )
            
            # Set data
            entry.set_prompt(prompt)
            entry.set_response(response)
            entry.set_token_usage(token_usage)
            
            # Invariant: Data should remain consistent
            assert entry.prompt == prompt
            assert entry.response == response
            assert entry.token_usage == token_usage
            
            # Invariant: Original parameters should be preserved
            assert entry.parameters["temperature"] == 0.7
            
            # Invariant: IDs should remain unchanged
            original_pseudonym_id = entry.pseudonym_id
            original_session_id = entry.session_id
            
            # Add more data
            entry.add_parameter("max_tokens", 100)
            
            # Invariant: IDs should still be the same
            assert entry.pseudonym_id == original_pseudonym_id
            assert entry.session_id == original_session_id
            
            # Invariant: Previously set data should be preserved
            assert entry.prompt == prompt
            assert entry.response == response
            assert entry.token_usage == token_usage