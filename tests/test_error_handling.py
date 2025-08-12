"""
Unit tests for error handling system.
Tests custom exceptions, circuit breaker, and error handler functionality.
"""

import time
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.exceptions import (
    AuthenticationError,
    ConfigurationError,
    DatabaseConnectionError,
    DatabaseError,
    ErrorCategory,
    ErrorSeverity,
    ExternalServiceError,
    GITTEError,
    InvalidCredentialsError,
    InvalidInputError,
    LLMProviderError,
    LLMTimeoutError,
    MissingRequiredFieldError,
    RecordNotFoundError,
    SessionExpiredError,
    SystemError,
    ValidationError,
)
from src.utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker,
)
from src.utils.error_handler import ErrorHandler, handle_errors, safe_execute


class TestGITTEExceptions:
    """Test cases for GITTE exception hierarchy."""

    def test_base_gitte_error(self):
        """Test base GITTEError functionality."""
        error = GITTEError(
            message="Test error",
            user_message="User friendly message",
            error_code="TEST_ERROR",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            details={"key": "value"},
        )

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.user_message == "User friendly message"
        assert error.error_code == "TEST_ERROR"
        assert error.category == ErrorCategory.SYSTEM
        assert error.severity == ErrorSeverity.HIGH
        assert error.details == {"key": "value"}

    def test_gitte_error_defaults(self):
        """Test GITTEError with default values."""
        error = GITTEError("Test message")

        assert error.message == "Test message"
        assert (
            error.user_message
            == "An error occurred. Please try again or contact support if the problem persists."
        )
        assert error.error_code == "GITTE_GITTEERROR"
        assert error.category == ErrorCategory.SYSTEM
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.details == {}

    def test_gitte_error_to_dict(self):
        """Test GITTEError serialization."""
        error = GITTEError(
            "Test error",
            user_message="User message",
            error_code="TEST_001",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details={"field": "username"},
        )

        error_dict = error.to_dict()

        assert error_dict["error_code"] == "TEST_001"
        assert error_dict["message"] == "Test error"
        assert error_dict["user_message"] == "User message"
        assert error_dict["category"] == "validation"
        assert error_dict["severity"] == "low"
        assert error_dict["details"] == {"field": "username"}

    def test_authentication_errors(self):
        """Test authentication error hierarchy."""
        # Base authentication error
        auth_error = AuthenticationError("Auth failed")
        assert auth_error.category == ErrorCategory.AUTHENTICATION
        assert auth_error.severity == ErrorSeverity.MEDIUM
        assert "Authentication failed" in auth_error.user_message

        # Invalid credentials error
        cred_error = InvalidCredentialsError()
        assert isinstance(cred_error, AuthenticationError)
        assert "Invalid username or password" in cred_error.message
        assert "Invalid username or password" in cred_error.user_message

        # Session expired error
        session_error = SessionExpiredError()
        assert isinstance(session_error, AuthenticationError)
        assert "session has expired" in session_error.message.lower()

    def test_validation_errors(self):
        """Test validation error hierarchy."""
        # Base validation error
        val_error = ValidationError("Invalid data", field="username")
        assert val_error.category == ErrorCategory.VALIDATION
        assert val_error.severity == ErrorSeverity.LOW
        assert val_error.details["field"] == "username"

        # Invalid input error
        input_error = InvalidInputError("username", "test@", "must not contain special characters")
        assert isinstance(input_error, ValidationError)
        assert input_error.details["field"] == "username"
        assert input_error.details["value"] == "test@"
        assert input_error.details["reason"] == "must not contain special characters"

        # Missing required field error
        missing_error = MissingRequiredFieldError("email")
        assert isinstance(missing_error, ValidationError)
        assert missing_error.details["field"] == "email"
        assert "Please provide a value for email" in missing_error.user_message

    def test_external_service_errors(self):
        """Test external service error hierarchy."""
        # Base external service error
        service_error = ExternalServiceError("TestService", "Connection failed")
        assert service_error.category == ErrorCategory.EXTERNAL_SERVICE
        assert service_error.severity == ErrorSeverity.HIGH
        assert service_error.details["service_name"] == "TestService"

        # LLM provider errors
        llm_error = LLMProviderError("Model not available")
        assert isinstance(llm_error, ExternalServiceError)
        assert "AI service" in llm_error.user_message

        llm_timeout = LLMTimeoutError(30)
        assert isinstance(llm_timeout, LLMProviderError)
        assert llm_timeout.details["timeout_seconds"] == 30

    def test_database_errors(self):
        """Test database error hierarchy."""
        # Base database error
        db_error = DatabaseError("Query failed")
        assert db_error.category == ErrorCategory.DATABASE
        assert db_error.severity == ErrorSeverity.HIGH

        # Connection error
        conn_error = DatabaseConnectionError()
        assert isinstance(conn_error, DatabaseError)
        assert conn_error.severity == ErrorSeverity.CRITICAL

        # Record not found error
        not_found = RecordNotFoundError("User", "123")
        assert isinstance(not_found, DatabaseError)
        assert not_found.severity == ErrorSeverity.LOW
        assert not_found.details["entity_type"] == "User"
        assert not_found.details["identifier"] == "123"

    def test_system_errors(self):
        """Test system error hierarchy."""
        # Base system error
        sys_error = SystemError("System failure")
        assert sys_error.category == ErrorCategory.SYSTEM
        assert sys_error.severity == ErrorSeverity.HIGH

        # Configuration error
        config_error = ConfigurationError("database_url")
        assert isinstance(config_error, SystemError)
        assert config_error.severity == ErrorSeverity.CRITICAL
        assert config_error.details["setting"] == "database_url"


class TestCircuitBreaker:
    """Test cases for circuit breaker functionality."""

    @pytest.fixture
    def circuit_breaker_config(self):
        """Circuit breaker configuration for testing."""
        return CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,  # Short timeout for testing
            success_threshold=1,
            timeout=5,
        )

    @pytest.fixture
    def circuit_breaker_instance(self, circuit_breaker_config):
        """Circuit breaker instance for testing."""
        return CircuitBreaker("test_service", circuit_breaker_config)

    def test_circuit_breaker_initialization(self, circuit_breaker_instance):
        """Test circuit breaker initialization."""
        cb = circuit_breaker_instance

        assert cb.name == "test_service"
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.failure_count == 0
        assert cb.stats.success_count == 0
        assert cb.stats.total_requests == 0

    def test_circuit_breaker_success(self, circuit_breaker_instance):
        """Test successful circuit breaker execution."""
        cb = circuit_breaker_instance

        def successful_function():
            return "success"

        result = cb.call(successful_function)

        assert result == "success"
        assert cb.stats.total_requests == 1
        assert cb.stats.total_successes == 1
        assert cb.stats.success_count == 1
        assert cb.state == CircuitState.CLOSED

    def test_circuit_breaker_failure(self, circuit_breaker_instance):
        """Test circuit breaker failure handling."""
        cb = circuit_breaker_instance

        def failing_function():
            raise ExternalServiceError("TestService", "Service unavailable")

        # First failure
        with pytest.raises(ExternalServiceError):
            cb.call(failing_function)

        assert cb.stats.total_requests == 1
        assert cb.stats.total_failures == 1
        assert cb.stats.failure_count == 1
        assert cb.state == CircuitState.CLOSED  # Still closed, threshold is 2

        # Second failure - should open circuit
        with pytest.raises(ExternalServiceError):
            cb.call(failing_function)

        assert cb.stats.failure_count == 2
        assert cb.state == CircuitState.OPEN

    def test_circuit_breaker_open_blocks_requests(self, circuit_breaker_instance):
        """Test that open circuit breaker blocks requests."""
        cb = circuit_breaker_instance

        # Force circuit open
        cb._change_state(CircuitState.OPEN)
        cb.stats.last_failure_time = time.time()

        def test_function():
            return "should not execute"

        # Request should be blocked
        with pytest.raises(ExternalServiceError) as exc_info:
            cb.call(test_function)

        assert "Circuit breaker is OPEN" in str(exc_info.value)

    def test_circuit_breaker_recovery(self, circuit_breaker_instance):
        """Test circuit breaker recovery from OPEN to HALF_OPEN to CLOSED."""
        cb = circuit_breaker_instance

        # Force circuit open with old failure time
        cb._change_state(CircuitState.OPEN)
        cb.stats.last_failure_time = time.time() - 2  # 2 seconds ago

        def successful_function():
            return "success"

        # Should attempt reset to HALF_OPEN and succeed
        result = cb.call(successful_function)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED  # Should close after success

    def test_circuit_breaker_decorator(self, circuit_breaker_config):
        """Test circuit breaker as decorator."""

        @circuit_breaker("test_decorator", circuit_breaker_config)
        def decorated_function(value):
            if value == "fail":
                raise ExternalServiceError("TestService", "Failure")
            return f"success: {value}"

        # Test success
        result = decorated_function("test")
        assert result == "success: test"

        # Test failure
        with pytest.raises(ExternalServiceError):
            decorated_function("fail")

    def test_circuit_breaker_stats(self, circuit_breaker_instance):
        """Test circuit breaker statistics."""
        cb = circuit_breaker_instance

        def test_function():
            return "test"

        # Execute some requests
        cb.call(test_function)
        cb.call(test_function)

        stats = cb.get_stats()

        assert stats["name"] == "test_service"
        assert stats["state"] == "closed"
        assert stats["total_requests"] == 2
        assert stats["total_successes"] == 2
        assert stats["success_rate"] == 1.0
        assert "config" in stats

    def test_circuit_breaker_reset(self, circuit_breaker_instance):
        """Test manual circuit breaker reset."""
        cb = circuit_breaker_instance

        # Force some state
        cb._change_state(CircuitState.OPEN)
        cb.stats.failure_count = 5

        # Reset
        cb.reset()

        assert cb.state == CircuitState.CLOSED
        assert cb.stats.failure_count == 0
        assert cb.stats.success_count == 0


class TestCircuitBreakerRegistry:
    """Test cases for circuit breaker registry."""

    def test_registry_get_or_create(self):
        """Test registry get or create functionality."""
        registry = CircuitBreakerRegistry()

        # Create new circuit breaker
        cb1 = registry.get_or_create("service1")
        assert cb1.name == "service1"

        # Get existing circuit breaker
        cb2 = registry.get_or_create("service1")
        assert cb1 is cb2  # Should be same instance

        # Create different circuit breaker
        cb3 = registry.get_or_create("service2")
        assert cb3.name == "service2"
        assert cb1 is not cb3

    def test_registry_get_all_stats(self):
        """Test registry statistics collection."""
        registry = CircuitBreakerRegistry()

        registry.get_or_create("service1")
        registry.get_or_create("service2")

        all_stats = registry.get_all_stats()

        assert "service1" in all_stats
        assert "service2" in all_stats
        assert len(all_stats) == 2

    def test_registry_unhealthy_services(self):
        """Test unhealthy services detection."""
        registry = CircuitBreakerRegistry()

        registry.get_or_create("healthy_service")
        cb2 = registry.get_or_create("unhealthy_service")

        # Force one circuit open
        cb2._change_state(CircuitState.OPEN)

        unhealthy = registry.get_unhealthy_services()

        assert "unhealthy_service" in unhealthy
        assert "healthy_service" not in unhealthy
        assert len(unhealthy) == 1


class TestErrorHandler:
    """Test cases for error handler functionality."""

    @pytest.fixture
    def error_handler(self):
        """Error handler instance for testing."""
        return ErrorHandler()

    def test_error_handler_handle_gitte_error(self, error_handler):
        """Test handling of GITTE errors."""
        error = ValidationError("Invalid input", field="username")
        user_id = str(uuid4())

        with patch("streamlit.session_state", {}):
            error_record = error_handler.handle_error(
                error=error, user_id=user_id, show_user_message=False
            )

        assert error_record["user_id"] == user_id
        assert error_record["error"]["error_code"] == error.error_code
        assert error_record["error"]["message"] == error.message
        assert error_record["error"]["category"] == error.category.value
        assert error_record["error"]["severity"] == error.severity.value

    def test_error_handler_convert_generic_error(self, error_handler):
        """Test conversion of generic exceptions to GITTE errors."""
        generic_error = ValueError("Invalid value")

        with patch("streamlit.session_state", {}):
            error_record = error_handler.handle_error(error=generic_error, show_user_message=False)

        assert "SystemError" in error_record["error"]["error_code"]
        assert "ValueError" in error_record["error"]["message"]
        assert error_record["error"]["category"] == ErrorCategory.SYSTEM.value

    def test_error_handler_statistics(self, error_handler):
        """Test error statistics tracking."""
        error1 = ValidationError("Error 1")
        error2 = ValidationError("Error 2")
        error3 = AuthenticationError("Error 3")

        with patch("streamlit.session_state", {}):
            error_handler.handle_error(error1, show_user_message=False)
            error_handler.handle_error(error2, show_user_message=False)
            error_handler.handle_error(error3, show_user_message=False)

        stats = error_handler.get_error_stats()

        assert stats["total_errors"] == 3
        assert len(stats["error_counts"]) >= 2  # At least ValidationError and AuthenticationError
        assert stats["recent_errors_count"] == 3

    def test_handle_errors_decorator(self):
        """Test handle_errors decorator."""

        @handle_errors(show_user_message=False, reraise=False)
        def failing_function():
            raise ValueError("Test error")

        @handle_errors(show_user_message=False, reraise=False)
        def successful_function():
            return "success"

        with patch("streamlit.session_state", {}):
            # Failing function should return None
            result1 = failing_function()
            assert result1 is None

            # Successful function should return result
            result2 = successful_function()
            assert result2 == "success"

    def test_safe_execute(self):
        """Test safe_execute utility function."""

        def failing_function():
            raise ValueError("Test error")

        def successful_function(value):
            return f"result: {value}"

        with patch("streamlit.session_state", {}):
            # Failing function should return default
            result1 = safe_execute(
                failing_function, default_return="default", show_user_message=False
            )
            assert result1 == "default"

            # Successful function should return result
            result2 = safe_execute(
                successful_function, "test", default_return="default", show_user_message=False
            )
            assert result2 == "result: test"


class TestErrorIntegration:
    """Integration tests for error handling system."""

    def test_circuit_breaker_with_error_handler(self):
        """Test circuit breaker integration with error handler."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1)
        cb = CircuitBreaker("integration_test", config)

        def failing_service():
            raise ExternalServiceError("TestService", "Service down")

        # First failure should open circuit
        with pytest.raises(ExternalServiceError):
            cb.call(failing_service)

        assert cb.state == CircuitState.OPEN

        # Subsequent calls should be blocked
        with pytest.raises(ExternalServiceError) as exc_info:
            cb.call(failing_service)

        assert "Circuit breaker is OPEN" in str(exc_info.value)

    def test_error_categorization(self):
        """Test that errors are properly categorized."""
        errors = [
            (InvalidCredentialsError(), ErrorCategory.AUTHENTICATION),
            (ValidationError("test"), ErrorCategory.VALIDATION),
            (DatabaseConnectionError(), ErrorCategory.DATABASE),
            (LLMTimeoutError(30), ErrorCategory.EXTERNAL_SERVICE),
            (SystemError("test"), ErrorCategory.SYSTEM),
        ]

        for error, expected_category in errors:
            assert error.category == expected_category

    def test_error_severity_levels(self):
        """Test that errors have appropriate severity levels."""
        # Critical errors
        critical_errors = [DatabaseConnectionError(), ConfigurationError("test")]
        for error in critical_errors:
            assert error.severity == ErrorSeverity.CRITICAL

        # High severity errors
        high_errors = [ExternalServiceError("test", "error"), SystemError("test")]
        for error in high_errors:
            assert error.severity == ErrorSeverity.HIGH

        # Low severity errors
        low_errors = [ValidationError("test"), RecordNotFoundError("User", "123")]
        for error in low_errors:
            assert error.severity == ErrorSeverity.LOW
