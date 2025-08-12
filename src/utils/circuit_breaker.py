"""
Circuit breaker pattern implementation for external service resilience.
Provides automatic failure detection and recovery for external service calls.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from threading import Lock
from typing import Any

from src.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds before trying half-open
    success_threshold: int = 3  # Successes needed to close from half-open
    timeout: int = 30  # Request timeout in seconds
    expected_exceptions: tuple = (ExternalServiceError,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    state_changes: int = 0


class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = Lock()

        logger.info(f"Circuit breaker '{name}' initialized with config: {self.config}")

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        return wrapper

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        with self._lock:
            self.stats.total_requests += 1

            # Check if circuit should be opened
            if self._should_attempt_reset():
                self._attempt_reset()

            # Block requests if circuit is open
            if self.state == CircuitState.OPEN:
                self._record_blocked_request()
                error = ExternalServiceError(
                    self.name,
                    f"Circuit breaker is OPEN. Service unavailable for {self.config.recovery_timeout}s.",
                )
                error.details.update(
                    {
                        "circuit_state": self.state.value,
                        "failure_count": self.stats.failure_count,
                        "last_failure_time": self.stats.last_failure_time,
                    }
                )
                raise error

        # Attempt the call
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            self._record_success(execution_time)
            return result

        except self.config.expected_exceptions as e:
            execution_time = time.time() - start_time
            self._record_failure(e, execution_time)
            raise
        except Exception as e:
            # Unexpected exceptions don't count as circuit breaker failures
            logger.warning(f"Unexpected exception in circuit breaker '{self.name}': {e}")
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset from OPEN to HALF_OPEN."""
        if self.state != CircuitState.OPEN:
            return False

        if self.stats.last_failure_time is None:
            return False

        time_since_failure = time.time() - self.stats.last_failure_time
        return time_since_failure >= self.config.recovery_timeout

    def _attempt_reset(self) -> None:
        """Attempt to reset circuit from OPEN to HALF_OPEN."""
        logger.info(f"Circuit breaker '{self.name}' attempting reset to HALF_OPEN")
        self._change_state(CircuitState.HALF_OPEN)
        self.stats.success_count = 0  # Reset success count for half-open test

    def _record_success(self, execution_time: float) -> None:
        """Record successful execution."""
        with self._lock:
            self.stats.success_count += 1
            self.stats.total_successes += 1
            self.stats.last_success_time = time.time()

            logger.debug(
                f"Circuit breaker '{self.name}' recorded success (time: {execution_time:.2f}s)"
            )

            # Handle state transitions based on success
            if self.state == CircuitState.HALF_OPEN:
                if self.stats.success_count >= self.config.success_threshold:
                    self._change_state(CircuitState.CLOSED)
                    self.stats.failure_count = 0  # Reset failure count
                    logger.info(f"Circuit breaker '{self.name}' closed after successful recovery")

    def _record_failure(self, exception: Exception, execution_time: float) -> None:
        """Record failed execution."""
        with self._lock:
            self.stats.failure_count += 1
            self.stats.total_failures += 1
            self.stats.last_failure_time = time.time()

            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure: {exception} (time: {execution_time:.2f}s)"
            )

            # Handle state transitions based on failure
            if self.state == CircuitState.CLOSED:
                if self.stats.failure_count >= self.config.failure_threshold:
                    self._change_state(CircuitState.OPEN)
                    logger.error(
                        f"Circuit breaker '{self.name}' opened due to {self.stats.failure_count} failures"
                    )

            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open state immediately opens the circuit
                self._change_state(CircuitState.OPEN)
                logger.error(
                    f"Circuit breaker '{self.name}' reopened after failure during recovery test"
                )

    def _record_blocked_request(self) -> None:
        """Record a request that was blocked by open circuit."""
        logger.debug(f"Circuit breaker '{self.name}' blocked request (circuit is OPEN)")

    def _change_state(self, new_state: CircuitState) -> None:
        """Change circuit breaker state."""
        old_state = self.state
        self.state = new_state
        self.stats.state_changes += 1

        logger.info(
            f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}"
        )

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.stats.failure_count,
                "success_count": self.stats.success_count,
                "total_requests": self.stats.total_requests,
                "total_failures": self.stats.total_failures,
                "total_successes": self.stats.total_successes,
                "success_rate": (
                    self.stats.total_successes / self.stats.total_requests
                    if self.stats.total_requests > 0
                    else 0
                ),
                "last_failure_time": self.stats.last_failure_time,
                "last_success_time": self.stats.last_success_time,
                "state_changes": self.stats.state_changes,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout,
                },
            }

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset")
            self._change_state(CircuitState.CLOSED)
            self.stats.failure_count = 0
            self.stats.success_count = 0

    def force_open(self) -> None:
        """Manually force circuit breaker to OPEN state."""
        with self._lock:
            logger.warning(f"Circuit breaker '{self.name}' manually forced open")
            self._change_state(CircuitState.OPEN)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = Lock()

    def get_or_create(
        self, name: str, config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
                logger.info(f"Created new circuit breaker: {name}")
            return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")

    def get_unhealthy_services(self) -> list[str]:
        """Get list of services with open circuit breakers."""
        with self._lock:
            return [
                name
                for name, breaker in self._breakers.items()
                if breaker.state == CircuitState.OPEN
            ]


# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()


def circuit_breaker(name: str, config: CircuitBreakerConfig | None = None) -> Callable:
    """Decorator to add circuit breaker protection to a function."""

    def decorator(func: Callable) -> Callable:
        breaker = circuit_breaker_registry.get_or_create(name, config)
        return breaker(func)

    return decorator


def get_circuit_breaker(name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    return circuit_breaker_registry.get_or_create(name, config)


def get_all_circuit_breaker_stats() -> dict[str, dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    return circuit_breaker_registry.get_all_stats()


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers."""
    circuit_breaker_registry.reset_all()


def get_unhealthy_services() -> list[str]:
    """Get list of services with open circuit breakers."""
    return circuit_breaker_registry.get_unhealthy_services()
