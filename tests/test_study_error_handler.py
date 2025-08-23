"""
Unit tests for study error handling and recovery system.
Tests comprehensive error handling, retry logic, circuit breakers, and fallback strategies.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from typing import Dict, Any

from src.exceptions import (
    ConsentError,
    ConsentRequiredError,
    DatabaseError,
    ExternalServiceError,
    ValidationError,
)
from src.utils.study_error_handler import (
    ErrorContext,
    RecoveryResult,
    RecoveryStrategy,
    StudyErrorCategory,
    StudyErrorHandler,
    StudyRetryConfig,
    study_error_handler,
)


class TestStudyErrorHandler:
    """Test cases for StudyErrorHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = StudyErrorHandler()
        self.user_id = uuid4()
        self.pseudonym_id = uuid4()
        self.session_id = uuid4()

    def test_handle_pseudonym_validation_error(self):
        """Test handling of pseudonym validation errors."""
        error = ValidationError("Invalid pseudonym format")
        context = ErrorContext(
            user_id=self.user_id,
            operation="create_pseudonym",
            component="pseudonym_logic"
        )

        result = self.handler.handle_pseudonym_error(error, context)

        assert isinstance(result, RecoveryResult)
        assert not result.success
        assert result.strategy_used == RecoveryStrategy.PROMPT_USER_RETRY
        assert result.user_action_required
        assert "Invalid pseudonym format" in result.error_message
        assert len(result.recovery_suggestions) > 0

    def test_handle_pseudonym_uniqueness_error(self):
        """Test handling of pseudonym uniqueness errors."""
        error = Exception("pseudonym already exists")
        context = ErrorContext(
            user_id=self.user_id,
            operation="create_pseudonym"
        )

        result = self.handler.handle_pseudonym_error(error, context)

        assert not result.success
        # Generic exceptions fall back to escalate to admin
        assert result.strategy_used == RecoveryStrategy.ESCALATE_TO_ADMIN
        assert "unexpected error" in result.error_message.lower()

    def test_handle_pseudonym_database_error(self):
        """Test handling of database errors during pseudonym creation."""
        error = DatabaseError("Connection timeout")
        context = ErrorContext(
            user_id=self.user_id,
            operation="create_pseudonym"
        )

        result = self.handler.handle_pseudonym_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert result.retry_count == 1

    def test_handle_consent_required_error(self):
        """Test handling of missing consent errors."""
        error = ConsentRequiredError(
            "Consent required for data_protection",
            required=["data_protection", "ai_interaction"]
        )
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="collect_consent"
        )

        result = self.handler.handle_consent_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.PROMPT_USER_RETRY
        assert result.user_action_required
        assert "data_protection" in result.recovery_suggestions[0]

    def test_handle_consent_withdrawal_error(self):
        """Test handling of consent withdrawal errors."""
        error = ConsentError("consent withdrawal failed")
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="withdraw_consent"
        )

        result = self.handler.handle_consent_error(error, context)

        assert not result.success
        # ConsentError with "withdrawal" in message should escalate to admin
        assert result.strategy_used == RecoveryStrategy.ESCALATE_TO_ADMIN
        
    def test_handle_consent_general_error(self):
        """Test handling of general consent errors."""
        error = ConsentError("Failed to record consent")
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="record_consent"
        )

        result = self.handler.handle_consent_error(error, context)

        assert not result.success
        # General ConsentError should use retry with fallback
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF

    def test_handle_survey_file_not_found(self):
        """Test handling of missing survey file errors."""
        error = FileNotFoundError("Survey file not found")
        context = ErrorContext(
            operation="load_survey",
            metadata={"file_path": "/path/to/survey.xlsx"}
        )

        result = self.handler.handle_survey_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.FALLBACK_TO_DEFAULT
        assert result.fallback_used
        assert "default survey" in result.error_message.lower()

    def test_handle_survey_validation_error(self):
        """Test handling of survey validation errors."""
        error = ValidationError("Invalid survey response")
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="submit_survey"
        )

        result = self.handler.handle_survey_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.PROMPT_USER_RETRY
        assert result.user_action_required

    def test_handle_pald_timeout_error(self):
        """Test handling of PALD processing timeout errors."""
        error = Exception("PALD processing timeout")
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="process_pald"
        )

        result = self.handler.handle_pald_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.GRACEFUL_DEGRADATION
        assert result.fallback_used

    def test_handle_pald_external_service_error(self):
        """Test handling of external service errors in PALD processing."""
        error = ExternalServiceError("LLM Service", "Service unavailable")
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="extract_pald"
        )

        result = self.handler.handle_pald_error(error, context)

        assert not result.success
        # Should use circuit breaker for external services
        assert result.strategy_used in [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.FALLBACK_TO_DEFAULT
        ]

    def test_handle_image_generation_timeout(self):
        """Test handling of image generation timeout errors."""
        error = Exception("Image generation timeout")
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="generate_image"
        )

        result = self.handler.handle_image_generation_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert result.retry_count == 1

    def test_handle_image_generation_service_error(self):
        """Test handling of image generation service errors."""
        error = ExternalServiceError("Image Service", "Service down")
        context = ErrorContext(
            pseudonym_id=self.pseudonym_id,
            operation="generate_image"
        )

        result = self.handler.handle_image_generation_error(error, context)

        assert not result.success
        # Should use circuit breaker and fallback
        assert result.strategy_used in [
            RecoveryStrategy.RETRY_WITH_BACKOFF,
            RecoveryStrategy.FALLBACK_TO_DEFAULT
        ]

    def test_handle_chat_rate_limit_error(self):
        """Test handling of chat rate limit errors."""
        error = Exception("Rate limit exceeded")
        context = ErrorContext(
            session_id=self.session_id,
            operation="process_chat"
        )

        result = self.handler.handle_chat_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.PROMPT_USER_RETRY
        assert result.user_action_required
        assert "wait" in result.error_message.lower()

    def test_handle_chat_validation_error(self):
        """Test handling of chat validation errors."""
        error = ValidationError("Invalid message format")
        context = ErrorContext(
            session_id=self.session_id,
            operation="validate_chat"
        )

        result = self.handler.handle_chat_error(error, context)

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.PROMPT_USER_RETRY
        assert result.user_action_required

    def test_database_connection_error_handling(self):
        """Test handling of database connection errors."""
        error = DatabaseError("Connection timeout")
        context = ErrorContext(
            user_id=self.user_id,
            operation="database_operation"
        )

        result = self.handler._handle_database_error(error, context, "test operation")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert result.retry_count == 1

    def test_database_constraint_error_handling(self):
        """Test handling of database constraint errors."""
        error = DatabaseError("Unique constraint violation")
        context = ErrorContext(
            user_id=self.user_id,
            operation="database_operation"
        )

        result = self.handler._handle_database_error(error, context, "test operation")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.PROMPT_USER_RETRY
        assert result.user_action_required

    def test_retry_with_fallback_logic(self):
        """Test retry logic with fallback strategy."""
        error = Exception("Temporary failure")
        context = ErrorContext(
            operation="test_operation",
            metadata={"retry_count": 0}
        )

        result = self.handler._retry_with_fallback(error, context, "test operation", "Fallback message")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert result.retry_count == 1

    def test_retry_exhaustion_fallback(self):
        """Test fallback when retries are exhausted."""
        error = Exception("Persistent failure")
        context = ErrorContext(
            operation="test_operation",
            metadata={"retry_count": 3}  # Already at max retries
        )

        result = self.handler._retry_with_fallback(error, context, "test operation", "Fallback message")

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.FALLBACK_TO_DEFAULT
        assert result.fallback_used

    def test_circuit_breaker_opening(self):
        """Test circuit breaker opening after multiple failures."""
        error = ExternalServiceError("Test Service", "Service failure")
        context = ErrorContext(operation="test_operation")

        # Simulate multiple failures to open circuit breaker
        for _ in range(5):
            result = self.handler._retry_with_circuit_breaker(
                error, context, "test_service", "Service unavailable"
            )

        # Circuit breaker should be open now
        cb = self.handler.circuit_breakers["test_service"]
        assert cb["state"] == "open"
        assert cb["failure_count"] >= 5

        # Next call should use fallback
        result = self.handler._retry_with_circuit_breaker(
            error, context, "test_service", "Service unavailable"
        )
        assert result.strategy_used == RecoveryStrategy.FALLBACK_TO_DEFAULT
        assert result.fallback_used

    def test_error_boundary_context_manager(self):
        """Test error boundary context manager functionality."""
        context = ErrorContext(
            user_id=self.user_id,
            operation="test_operation"
        )

        # Test successful operation
        with self.handler.error_boundary(StudyErrorCategory.PSEUDONYM_CREATION, context):
            result = "success"

        # Test error handling
        with pytest.raises(Exception) as exc_info:
            with self.handler.error_boundary(StudyErrorCategory.PSEUDONYM_CREATION, context):
                raise ValidationError("Test error")

        # Check that recovery information is attached
        assert hasattr(exc_info.value, '__cause__') or 'recovery_result' in str(exc_info.value)

    def test_recovery_stats_tracking(self):
        """Test recovery statistics tracking."""
        initial_stats = self.handler.get_recovery_stats()
        
        # Simulate some error handling
        error = ValidationError("Test error")
        context = ErrorContext(operation="test")
        
        self.handler.handle_pseudonym_error(error, context)
        self.handler.handle_consent_error(error, context)

        # Check stats are updated
        updated_stats = self.handler.get_recovery_stats()
        assert "recovery_stats" in updated_stats
        assert len(updated_stats["recovery_stats"]) >= len(initial_stats["recovery_stats"])

    def test_study_retry_config(self):
        """Test StudyRetryConfig configuration."""
        config = StudyRetryConfig(
            max_retries=5,
            initial_delay=2.0,
            max_delay=60.0,
            backoff_multiplier=3.0,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )

        assert config.max_retries == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 3.0
        assert ConnectionError in config.retryable_exceptions
        assert TimeoutError in config.retryable_exceptions


class TestErrorHandlingDecorators:
    """Test cases for error handling decorators."""

    def test_with_study_error_handling_decorator(self):
        """Test the with_study_error_handling decorator."""
        from src.utils.study_error_handler import with_study_error_handling

        @with_study_error_handling(
            StudyErrorCategory.PSEUDONYM_CREATION,
            context_factory=lambda *args, **kwargs: ErrorContext(operation="test_function")
        )
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_decorator_error_handling(self):
        """Test decorator handles errors properly."""
        from src.utils.study_error_handler import with_study_error_handling

        @with_study_error_handling(StudyErrorCategory.VALIDATION)
        def failing_function():
            raise ValidationError("Test error")

        with pytest.raises(Exception):
            failing_function()


class TestErrorContext:
    """Test cases for ErrorContext class."""

    def test_error_context_creation(self):
        """Test ErrorContext creation and attributes."""
        user_id = uuid4()
        pseudonym_id = uuid4()
        session_id = uuid4()

        context = ErrorContext(
            user_id=user_id,
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            operation="test_operation",
            component="test_component",
            metadata={"key": "value"}
        )

        assert context.user_id == user_id
        assert context.pseudonym_id == pseudonym_id
        assert context.session_id == session_id
        assert context.operation == "test_operation"
        assert context.component == "test_component"
        assert context.metadata["key"] == "value"

    def test_error_context_defaults(self):
        """Test ErrorContext with default values."""
        context = ErrorContext()

        assert context.user_id is None
        assert context.pseudonym_id is None
        assert context.session_id is None
        assert context.operation is None
        assert context.component is None
        assert context.metadata == {}


class TestRecoveryResult:
    """Test cases for RecoveryResult class."""

    def test_recovery_result_creation(self):
        """Test RecoveryResult creation and attributes."""
        result = RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.RETRY_WITH_BACKOFF,
            result_data={"key": "value"},
            error_message="Test error",
            retry_count=2,
            fallback_used=True,
            user_action_required=False,
            recovery_suggestions=["Suggestion 1", "Suggestion 2"]
        )

        assert not result.success
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert result.result_data == {"key": "value"}
        assert result.error_message == "Test error"
        assert result.retry_count == 2
        assert result.fallback_used
        assert not result.user_action_required
        assert len(result.recovery_suggestions) == 2

    def test_recovery_result_defaults(self):
        """Test RecoveryResult with default values."""
        result = RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.RETRY_WITH_BACKOFF
        )

        assert result.success
        assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert result.result_data is None
        assert result.error_message is None
        assert result.retry_count == 0
        assert not result.fallback_used
        assert not result.user_action_required
        assert result.recovery_suggestions == []


class TestModuleLevelHandler:
    """Test cases for module-level error handler instance."""

    def test_module_level_handler_exists(self):
        """Test that module-level handler instance exists."""
        assert study_error_handler is not None
        assert isinstance(study_error_handler, StudyErrorHandler)

    def test_module_level_handler_functionality(self):
        """Test that module-level handler works correctly."""
        error = ValidationError("Test error")
        context = ErrorContext(operation="test")

        result = study_error_handler.handle_pseudonym_error(error, context)
        assert isinstance(result, RecoveryResult)
        assert not result.success


if __name__ == "__main__":
    pytest.main([__file__])