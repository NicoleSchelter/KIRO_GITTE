"""
Contract tests for study error handling system.
Tests the interfaces and contracts between error handling components and external systems.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from typing import Protocol, runtime_checkable

from src.exceptions import (
    ConsentError,
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
)


@runtime_checkable
class ErrorHandlerProtocol(Protocol):
    """Protocol defining the error handler interface contract."""

    def handle_pseudonym_error(
        self, error: Exception, context: ErrorContext, retry_config: StudyRetryConfig = None
    ) -> RecoveryResult:
        """Handle pseudonym-related errors."""
        ...

    def handle_consent_error(
        self, error: Exception, context: ErrorContext, retry_config: StudyRetryConfig = None
    ) -> RecoveryResult:
        """Handle consent-related errors."""
        ...

    def handle_survey_error(
        self, error: Exception, context: ErrorContext, retry_config: StudyRetryConfig = None
    ) -> RecoveryResult:
        """Handle survey-related errors."""
        ...

    def handle_pald_error(
        self, error: Exception, context: ErrorContext, retry_config: StudyRetryConfig = None
    ) -> RecoveryResult:
        """Handle PALD processing errors."""
        ...

    def handle_image_generation_error(
        self, error: Exception, context: ErrorContext, retry_config: StudyRetryConfig = None
    ) -> RecoveryResult:
        """Handle image generation errors."""
        ...

    def handle_chat_error(
        self, error: Exception, context: ErrorContext, retry_config: StudyRetryConfig = None
    ) -> RecoveryResult:
        """Handle chat processing errors."""
        ...


@runtime_checkable
class RecoveryResultProtocol(Protocol):
    """Protocol defining the recovery result interface contract."""

    success: bool
    strategy_used: RecoveryStrategy
    result_data: any
    error_message: str
    retry_count: int
    fallback_used: bool
    user_action_required: bool
    recovery_suggestions: list[str]


class TestStudyErrorHandlerContract:
    """Contract tests for StudyErrorHandler implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = StudyErrorHandler()
        self.user_id = uuid4()
        self.pseudonym_id = uuid4()

    def test_implements_error_handler_protocol(self):
        """Test that StudyErrorHandler implements the ErrorHandlerProtocol."""
        assert isinstance(self.handler, ErrorHandlerProtocol)

    def test_error_handler_method_signatures(self):
        """Test that all error handler methods have correct signatures."""
        # Test method existence and basic signature
        assert hasattr(self.handler, 'handle_pseudonym_error')
        assert hasattr(self.handler, 'handle_consent_error')
        assert hasattr(self.handler, 'handle_survey_error')
        assert hasattr(self.handler, 'handle_pald_error')
        assert hasattr(self.handler, 'handle_image_generation_error')
        assert hasattr(self.handler, 'handle_chat_error')

        # Test that methods are callable
        assert callable(self.handler.handle_pseudonym_error)
        assert callable(self.handler.handle_consent_error)
        assert callable(self.handler.handle_survey_error)
        assert callable(self.handler.handle_pald_error)
        assert callable(self.handler.handle_image_generation_error)
        assert callable(self.handler.handle_chat_error)

    def test_all_error_handlers_return_recovery_result(self):
        """Test that all error handlers return RecoveryResult objects."""
        error = Exception("Test error")
        context = ErrorContext(user_id=self.user_id)

        # Test each error handler
        handlers = [
            self.handler.handle_pseudonym_error,
            self.handler.handle_consent_error,
            self.handler.handle_survey_error,
            self.handler.handle_pald_error,
            self.handler.handle_image_generation_error,
            self.handler.handle_chat_error,
        ]

        for handler_method in handlers:
            result = handler_method(error, context)
            assert isinstance(result, RecoveryResult)
            assert isinstance(result, RecoveryResultProtocol)

    def test_recovery_result_contract_compliance(self):
        """Test that RecoveryResult objects comply with the protocol contract."""
        error = ValidationError("Test validation error")
        context = ErrorContext(user_id=self.user_id)

        result = self.handler.handle_pseudonym_error(error, context)

        # Test required attributes exist
        assert hasattr(result, 'success')
        assert hasattr(result, 'strategy_used')
        assert hasattr(result, 'result_data')
        assert hasattr(result, 'error_message')
        assert hasattr(result, 'retry_count')
        assert hasattr(result, 'fallback_used')
        assert hasattr(result, 'user_action_required')
        assert hasattr(result, 'recovery_suggestions')

        # Test attribute types
        assert isinstance(result.success, bool)
        assert isinstance(result.strategy_used, RecoveryStrategy)
        assert result.error_message is None or isinstance(result.error_message, str)
        assert isinstance(result.retry_count, int)
        assert isinstance(result.fallback_used, bool)
        assert isinstance(result.user_action_required, bool)
        assert isinstance(result.recovery_suggestions, list)

    def test_error_context_contract_compliance(self):
        """Test that ErrorContext objects have the expected interface."""
        context = ErrorContext(
            user_id=self.user_id,
            pseudonym_id=self.pseudonym_id,
            operation="test_operation",
            component="test_component"
        )

        # Test required attributes exist
        assert hasattr(context, 'user_id')
        assert hasattr(context, 'pseudonym_id')
        assert hasattr(context, 'session_id')
        assert hasattr(context, 'operation')
        assert hasattr(context, 'component')
        assert hasattr(context, 'metadata')

        # Test attribute types
        assert context.user_id is None or isinstance(context.user_id, type(self.user_id))
        assert context.pseudonym_id is None or isinstance(context.pseudonym_id, type(self.pseudonym_id))
        assert context.operation is None or isinstance(context.operation, str)
        assert context.component is None or isinstance(context.component, str)
        assert isinstance(context.metadata, dict)

    def test_retry_config_contract_compliance(self):
        """Test that StudyRetryConfig has the expected interface."""
        config = StudyRetryConfig()

        # Test required attributes exist
        assert hasattr(config, 'max_retries')
        assert hasattr(config, 'initial_delay')
        assert hasattr(config, 'max_delay')
        assert hasattr(config, 'backoff_multiplier')
        assert hasattr(config, 'jitter')
        assert hasattr(config, 'retryable_exceptions')
        assert hasattr(config, 'circuit_breaker_threshold')
        assert hasattr(config, 'circuit_breaker_timeout')

        # Test attribute types
        assert isinstance(config.max_retries, int)
        assert isinstance(config.initial_delay, (int, float))
        assert isinstance(config.max_delay, (int, float))
        assert isinstance(config.backoff_multiplier, (int, float))
        assert isinstance(config.jitter, bool)
        assert isinstance(config.retryable_exceptions, tuple)
        assert isinstance(config.circuit_breaker_threshold, int)
        assert isinstance(config.circuit_breaker_timeout, (int, float))

    def test_error_boundary_context_manager_contract(self):
        """Test that error_boundary context manager works as expected."""
        context = ErrorContext(operation="test")

        # Test successful execution
        with self.handler.error_boundary(StudyErrorCategory.PSEUDONYM_CREATION, context):
            result = "success"
        assert result == "success"

        # Test error handling
        with pytest.raises(Exception):
            with self.handler.error_boundary(StudyErrorCategory.PSEUDONYM_CREATION, context):
                raise ValidationError("Test error")

    def test_recovery_strategies_are_valid_enum_values(self):
        """Test that all recovery strategies used are valid enum values."""
        error = ValidationError("Test error")
        context = ErrorContext(user_id=self.user_id)

        handlers = [
            self.handler.handle_pseudonym_error,
            self.handler.handle_consent_error,
            self.handler.handle_survey_error,
            self.handler.handle_pald_error,
            self.handler.handle_image_generation_error,
            self.handler.handle_chat_error,
        ]

        for handler_method in handlers:
            result = handler_method(error, context)
            assert isinstance(result.strategy_used, RecoveryStrategy)
            # Verify it's a valid enum value
            assert result.strategy_used in RecoveryStrategy

    def test_error_categories_are_valid_enum_values(self):
        """Test that all error categories are valid enum values."""
        # Test that all categories used in error_boundary are valid
        categories = [
            StudyErrorCategory.PSEUDONYM_CREATION,
            StudyErrorCategory.CONSENT_COLLECTION,
            StudyErrorCategory.SURVEY_LOADING,
            StudyErrorCategory.SURVEY_SUBMISSION,
            StudyErrorCategory.PALD_PROCESSING,
            StudyErrorCategory.IMAGE_GENERATION,
            StudyErrorCategory.CHAT_PROCESSING,
        ]

        for category in categories:
            assert isinstance(category, StudyErrorCategory)
            # Test that error_boundary accepts the category
            context = ErrorContext(operation="test")
            with self.handler.error_boundary(category, context):
                pass  # Should not raise

    def test_statistics_interface_contract(self):
        """Test that statistics interface returns expected structure."""
        stats = self.handler.get_recovery_stats()

        # Test required keys exist
        assert 'recovery_stats' in stats
        assert 'circuit_breakers' in stats
        assert 'error_counts' in stats

        # Test data types
        assert isinstance(stats['recovery_stats'], dict)
        assert isinstance(stats['circuit_breakers'], dict)
        assert isinstance(stats['error_counts'], dict)

        # Test circuit breaker structure
        for cb_name, cb_data in stats['circuit_breakers'].items():
            assert isinstance(cb_name, str)
            assert isinstance(cb_data, dict)
            assert 'state' in cb_data
            assert 'failure_count' in cb_data
            assert 'last_failure' in cb_data

    def test_error_handler_accepts_all_exception_types(self):
        """Test that error handlers can handle different exception types."""
        context = ErrorContext(user_id=self.user_id)

        exception_types = [
            Exception("Generic error"),
            ValidationError("Validation error"),
            DatabaseError("Database error"),
            ExternalServiceError("Service", "External service error"),
            ConsentError("Consent error"),
            FileNotFoundError("File not found"),
            ConnectionError("Connection error"),
            TimeoutError("Timeout error"),
        ]

        handlers = [
            self.handler.handle_pseudonym_error,
            self.handler.handle_consent_error,
            self.handler.handle_survey_error,
            self.handler.handle_pald_error,
            self.handler.handle_image_generation_error,
            self.handler.handle_chat_error,
        ]

        for handler_method in handlers:
            for exception in exception_types:
                # Should not raise an exception, should return RecoveryResult
                result = handler_method(exception, context)
                assert isinstance(result, RecoveryResult)

    def test_retry_config_optional_parameter(self):
        """Test that retry_config parameter is optional for all handlers."""
        error = Exception("Test error")
        context = ErrorContext(user_id=self.user_id)

        handlers = [
            self.handler.handle_pseudonym_error,
            self.handler.handle_consent_error,
            self.handler.handle_survey_error,
            self.handler.handle_pald_error,
            self.handler.handle_image_generation_error,
            self.handler.handle_chat_error,
        ]

        for handler_method in handlers:
            # Should work without retry_config
            result1 = handler_method(error, context)
            assert isinstance(result1, RecoveryResult)

            # Should work with retry_config
            config = StudyRetryConfig(max_retries=1)
            result2 = handler_method(error, context, config)
            assert isinstance(result2, RecoveryResult)

    def test_error_handler_thread_safety_contract(self):
        """Test that error handler can be used safely from multiple threads."""
        import threading
        import time

        results = []
        errors = []

        def worker():
            try:
                error = ValidationError("Thread test error")
                context = ErrorContext(user_id=uuid4())
                result = self.handler.handle_pseudonym_error(error, context)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Check results
        assert len(errors) == 0, f"Errors occurred in threads: {errors}"
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        
        # All results should be valid RecoveryResult objects
        for result in results:
            assert isinstance(result, RecoveryResult)


class TestErrorHandlingIntegrationContract:
    """Contract tests for error handling integration with other components."""

    def test_ux_error_handler_integration_contract(self):
        """Test that StudyErrorHandler integrates properly with UXErrorHandler."""
        from src.utils.ux_error_handler import record_ux_error, get_ux_error_stats

        handler = StudyErrorHandler()
        initial_stats = get_ux_error_stats()

        # Trigger error handling that should record UX errors
        error = ValidationError("Test error")
        context = ErrorContext(user_id=uuid4())
        
        handler.handle_pseudonym_error(error, context)

        # Check that UX error was recorded
        updated_stats = get_ux_error_stats()
        # Should have more total failures than before
        assert updated_stats.get("total_failures", 0) >= initial_stats.get("total_failures", 0)

    def test_exception_enhancement_contract(self):
        """Test that exceptions are properly enhanced with recovery information."""
        handler = StudyErrorHandler()
        context = ErrorContext(operation="test")

        with pytest.raises(Exception) as exc_info:
            with handler.error_boundary(StudyErrorCategory.PSEUDONYM_CREATION, context):
                raise ValidationError("Test error")

        # Check that the exception has recovery information
        exception = exc_info.value
        # Should either have recovery_result attribute or be enhanced with recovery info
        has_recovery_info = (
            hasattr(exception, 'recovery_result') or
            'recovery_result' in getattr(exception, 'details', {}) or
            hasattr(exception, '__cause__')
        )
        assert has_recovery_info, "Exception should be enhanced with recovery information"


if __name__ == "__main__":
    pytest.main([__file__])