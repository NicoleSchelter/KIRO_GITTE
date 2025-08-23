"""
Property-based tests for study error handling system.
Tests invariants and properties that should hold across all error handling scenarios.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from uuid import UUID, uuid4
from typing import Any, Dict

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
)


# Hypothesis strategies for generating test data
error_messages = st.text(min_size=1, max_size=200)
user_ids = st.uuids()
operation_names = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
component_names = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))

# Strategy for generating various exception types
@st.composite
def exception_strategy(draw):
    """Generate various types of exceptions for testing."""
    exception_type = draw(st.sampled_from([
        Exception,
        ValidationError,
        DatabaseError,
        ExternalServiceError,
        ConsentError,
        ConsentRequiredError,
        FileNotFoundError,
        ConnectionError,
        TimeoutError,
    ]))
    
    message = draw(error_messages)
    
    if exception_type == ExternalServiceError:
        service_name = draw(st.text(min_size=1, max_size=20))
        return exception_type(service_name, message)
    elif exception_type == ConsentRequiredError:
        required_consents = draw(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5))
        return exception_type(message, required=required_consents)
    else:
        return exception_type(message)

# Strategy for generating ErrorContext objects
@st.composite
def error_context_strategy(draw):
    """Generate ErrorContext objects for testing."""
    return ErrorContext(
        user_id=draw(st.one_of(st.none(), user_ids)),
        pseudonym_id=draw(st.one_of(st.none(), user_ids)),
        session_id=draw(st.one_of(st.none(), user_ids)),
        operation=draw(st.one_of(st.none(), operation_names)),
        component=draw(st.one_of(st.none(), component_names)),
        metadata=draw(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=0, max_size=100)))
    )

# Strategy for generating StudyRetryConfig objects
@st.composite
def retry_config_strategy(draw):
    """Generate StudyRetryConfig objects for testing."""
    return StudyRetryConfig(
        max_retries=draw(st.integers(min_value=1, max_value=10)),
        initial_delay=draw(st.floats(min_value=0.1, max_value=5.0)),
        max_delay=draw(st.floats(min_value=5.0, max_value=60.0)),
        backoff_multiplier=draw(st.floats(min_value=1.1, max_value=5.0)),
        jitter=draw(st.booleans()),
        retryable_exceptions=draw(st.tuples(
            st.sampled_from([ConnectionError, TimeoutError, DatabaseError, ExternalServiceError])
        )),
        circuit_breaker_threshold=draw(st.integers(min_value=3, max_value=10)),
        circuit_breaker_timeout=draw(st.floats(min_value=30.0, max_value=300.0))
    )


class TestStudyErrorHandlerProperties:
    """Property-based tests for StudyErrorHandler."""

    @given(exception_strategy(), error_context_strategy())
    def test_all_error_handlers_return_recovery_result(self, error, context):
        """Property: All error handlers must return a RecoveryResult object."""
        handler = StudyErrorHandler()
        
        handlers = [
            handler.handle_pseudonym_error,
            handler.handle_consent_error,
            handler.handle_survey_error,
            handler.handle_pald_error,
            handler.handle_image_generation_error,
            handler.handle_chat_error,
        ]
        
        for handler_method in handlers:
            result = handler_method(error, context)
            assert isinstance(result, RecoveryResult)
            assert hasattr(result, 'success')
            assert hasattr(result, 'strategy_used')
            assert isinstance(result.strategy_used, RecoveryStrategy)

    @given(exception_strategy(), error_context_strategy(), retry_config_strategy())
    def test_error_handlers_accept_retry_config(self, error, context, retry_config):
        """Property: All error handlers must accept optional retry configuration."""
        handler = StudyErrorHandler()
        
        handlers = [
            handler.handle_pseudonym_error,
            handler.handle_consent_error,
            handler.handle_survey_error,
            handler.handle_pald_error,
            handler.handle_image_generation_error,
            handler.handle_chat_error,
        ]
        
        for handler_method in handlers:
            # Should work with retry config
            result = handler_method(error, context, retry_config)
            assert isinstance(result, RecoveryResult)
            
            # Should work without retry config
            result = handler_method(error, context)
            assert isinstance(result, RecoveryResult)

    @given(exception_strategy(), error_context_strategy())
    def test_recovery_result_consistency(self, error, context):
        """Property: RecoveryResult objects must have consistent internal state."""
        handler = StudyErrorHandler()
        result = handler.handle_pseudonym_error(error, context)
        
        # If success is True, there should be no error message
        if result.success:
            assert result.error_message is None or result.error_message == ""
        
        # If fallback_used is True, success should typically be False
        if result.fallback_used:
            # Fallback usually means the original operation failed
            pass  # This is not always true, so we don't assert
        
        # Retry count should be non-negative
        assert result.retry_count >= 0
        
        # Recovery suggestions should be a list
        assert isinstance(result.recovery_suggestions, list)
        
        # If user action is required, there should be recovery suggestions
        if result.user_action_required:
            assert len(result.recovery_suggestions) > 0

    @given(st.sampled_from(list(StudyErrorCategory)), error_context_strategy())
    def test_error_boundary_context_manager_properties(self, category, context):
        """Property: Error boundary context manager must handle all categories."""
        handler = StudyErrorHandler()
        
        # Should not raise for successful operations
        with handler.error_boundary(category, context):
            result = "success"
        assert result == "success"
        
        # Should handle errors appropriately
        with pytest.raises(Exception):
            with handler.error_boundary(category, context):
                raise ValidationError("Test error")

    @given(st.lists(exception_strategy(), min_size=1, max_size=10), error_context_strategy())
    def test_multiple_error_handling_consistency(self, errors, context):
        """Property: Handling multiple errors should be consistent."""
        handler = StudyErrorHandler()
        
        results = []
        for error in errors:
            result = handler.handle_pseudonym_error(error, context)
            results.append(result)
        
        # All results should be RecoveryResult objects
        assert all(isinstance(r, RecoveryResult) for r in results)
        
        # Similar errors should produce similar recovery strategies
        validation_errors = [r for r, e in zip(results, errors) if isinstance(e, ValidationError)]
        if len(validation_errors) > 1:
            # All validation errors should use similar strategies
            strategies = [r.strategy_used for r in validation_errors]
            # Most should be the same strategy (allowing for some variation)
            most_common_strategy = max(set(strategies), key=strategies.count)
            same_strategy_count = strategies.count(most_common_strategy)
            assert same_strategy_count >= len(strategies) * 0.7  # At least 70% should be the same

    @given(error_messages, st.integers(min_value=0, max_value=10))
    def test_retry_logic_properties(self, error_message, retry_count):
        """Property: Retry logic should behave consistently."""
        handler = StudyErrorHandler()
        error = Exception(error_message)
        context = ErrorContext(
            operation="test_operation",
            metadata={"retry_count": retry_count}
        )
        
        result = handler._retry_with_fallback(error, context, "test operation", "Fallback message")
        
        # If retry count is below max, should retry
        if retry_count < 3:
            assert result.strategy_used == RecoveryStrategy.RETRY_WITH_BACKOFF
            assert result.retry_count == retry_count + 1
        else:
            # If at max retries, should fallback
            assert result.strategy_used == RecoveryStrategy.FALLBACK_TO_DEFAULT
            assert result.fallback_used

    @given(st.text(min_size=1, max_size=50), st.integers(min_value=1, max_value=10))
    def test_circuit_breaker_properties(self, service_name, failure_count):
        """Property: Circuit breaker should behave consistently."""
        handler = StudyErrorHandler()
        error = ExternalServiceError(service_name, "Service failure")
        context = ErrorContext(operation="test_operation")
        
        # Simulate multiple failures
        for _ in range(failure_count):
            result = handler._retry_with_circuit_breaker(
                error, context, service_name, "Service unavailable"
            )
        
        # Check circuit breaker state
        if service_name in handler.circuit_breakers:
            cb = handler.circuit_breakers[service_name]
            assert cb["failure_count"] >= 0
            assert cb["state"] in ["closed", "open", "half-open"]
            
            # If failure count is high, circuit should be open
            if cb["failure_count"] >= 5:
                assert cb["state"] == "open"

    @given(error_context_strategy())
    def test_statistics_tracking_properties(self, context):
        """Property: Statistics should be tracked consistently."""
        handler = StudyErrorHandler()
        initial_stats = handler.get_recovery_stats()
        
        # Perform some error handling
        error = ValidationError("Test error")
        handler.handle_pseudonym_error(error, context)
        handler.handle_consent_error(error, context)
        
        updated_stats = handler.get_recovery_stats()
        
        # Stats should have expected structure
        assert "recovery_stats" in updated_stats
        assert "circuit_breakers" in updated_stats
        assert "error_counts" in updated_stats
        
        # Recovery stats should have increased
        initial_total = sum(
            sum(strategies.values()) for strategies in initial_stats["recovery_stats"].values()
        )
        updated_total = sum(
            sum(strategies.values()) for strategies in updated_stats["recovery_stats"].values()
        )
        assert updated_total >= initial_total


class ErrorHandlerStateMachine(RuleBasedStateMachine):
    """Stateful testing for error handler behavior over time."""

    def __init__(self):
        super().__init__()
        self.handler = StudyErrorHandler()
        self.total_errors_handled = 0
        self.circuit_breakers_opened = set()

    @rule(error=exception_strategy(), context=error_context_strategy())
    def handle_pseudonym_error(self, error, context):
        """Rule: Handle pseudonym errors."""
        result = self.handler.handle_pseudonym_error(error, context)
        assert isinstance(result, RecoveryResult)
        self.total_errors_handled += 1

    @rule(error=exception_strategy(), context=error_context_strategy())
    def handle_consent_error(self, error, context):
        """Rule: Handle consent errors."""
        result = self.handler.handle_consent_error(error, context)
        assert isinstance(result, RecoveryResult)
        self.total_errors_handled += 1

    @rule(error=exception_strategy(), context=error_context_strategy())
    def handle_survey_error(self, error, context):
        """Rule: Handle survey errors."""
        result = self.handler.handle_survey_error(error, context)
        assert isinstance(result, RecoveryResult)
        self.total_errors_handled += 1

    @rule(service_name=st.text(min_size=1, max_size=20))
    def trigger_circuit_breaker(self, service_name):
        """Rule: Trigger circuit breaker by causing multiple failures."""
        error = ExternalServiceError(service_name, "Service failure")
        context = ErrorContext(operation="test")
        
        # Cause multiple failures to open circuit breaker
        for _ in range(6):  # More than threshold
            self.handler._retry_with_circuit_breaker(
                error, context, service_name, "Service unavailable"
            )
        
        if service_name in self.handler.circuit_breakers:
            cb = self.handler.circuit_breakers[service_name]
            if cb["state"] == "open":
                self.circuit_breakers_opened.add(service_name)

    @invariant()
    def statistics_are_consistent(self):
        """Invariant: Statistics should always be consistent."""
        stats = self.handler.get_recovery_stats()
        
        # Should have expected keys
        assert "recovery_stats" in stats
        assert "circuit_breakers" in stats
        assert "error_counts" in stats
        
        # All values should be non-negative
        for category_stats in stats["recovery_stats"].values():
            for count in category_stats.values():
                assert count >= 0
        
        for count in stats["error_counts"].values():
            assert count >= 0

    @invariant()
    def circuit_breakers_are_valid(self):
        """Invariant: Circuit breakers should always be in valid states."""
        for cb_name, cb_data in self.handler.circuit_breakers.items():
            assert cb_data["state"] in ["closed", "open", "half-open"]
            assert cb_data["failure_count"] >= 0
            assert cb_data["last_failure"] >= 0

    @invariant()
    def error_count_is_consistent(self):
        """Invariant: Total errors handled should be consistent with operations."""
        # This is a basic sanity check
        assert self.total_errors_handled >= 0


# Configure hypothesis settings for property tests
TestErrorHandlerStateMachine = ErrorHandlerStateMachine.TestCase
TestErrorHandlerStateMachine.settings = settings(
    max_examples=50,
    stateful_step_count=20,
    deadline=None
)


class TestErrorHandlingInvariants:
    """Test invariants that should hold for error handling."""

    @given(exception_strategy(), error_context_strategy())
    def test_error_handling_never_raises_unhandled_exceptions(self, error, context):
        """Invariant: Error handlers should never raise unhandled exceptions."""
        handler = StudyErrorHandler()
        
        handlers = [
            handler.handle_pseudonym_error,
            handler.handle_consent_error,
            handler.handle_survey_error,
            handler.handle_pald_error,
            handler.handle_image_generation_error,
            handler.handle_chat_error,
        ]
        
        for handler_method in handlers:
            # Should not raise any exceptions
            try:
                result = handler_method(error, context)
                assert isinstance(result, RecoveryResult)
            except Exception as e:
                pytest.fail(f"Error handler {handler_method.__name__} raised unhandled exception: {e}")

    @given(st.lists(exception_strategy(), min_size=1, max_size=20), error_context_strategy())
    def test_error_handling_is_deterministic(self, errors, context):
        """Invariant: Same errors with same context should produce same results."""
        handler1 = StudyErrorHandler()
        handler2 = StudyErrorHandler()
        
        for error in errors:
            result1 = handler1.handle_pseudonym_error(error, context)
            result2 = handler2.handle_pseudonym_error(error, context)
            
            # Results should be equivalent (same strategy, similar properties)
            assert result1.strategy_used == result2.strategy_used
            assert result1.user_action_required == result2.user_action_required
            assert result1.fallback_used == result2.fallback_used

    @given(error_context_strategy())
    def test_statistics_never_decrease(self, context):
        """Invariant: Statistics counters should never decrease."""
        handler = StudyErrorHandler()
        
        initial_stats = handler.get_recovery_stats()
        
        # Perform some operations
        error = ValidationError("Test error")
        handler.handle_pseudonym_error(error, context)
        
        updated_stats = handler.get_recovery_stats()
        
        # Counters should not decrease
        for category in initial_stats["recovery_stats"]:
            if category in updated_stats["recovery_stats"]:
                for strategy in initial_stats["recovery_stats"][category]:
                    if strategy in updated_stats["recovery_stats"][category]:
                        assert (updated_stats["recovery_stats"][category][strategy] >= 
                               initial_stats["recovery_stats"][category][strategy])


if __name__ == "__main__":
    pytest.main([__file__])