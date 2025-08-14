"""
Enhanced error handling utilities for UX enhancement features.
Provides specialized error handling, retry logic, and fallback mechanisms.
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union

import streamlit as st

from src.exceptions import (
    BackgroundRemovalError,
    BatchProcessingError,
    CircuitBreakerOpenError,
    ImageCorruptionError,
    ImageIsolationError,
    ImageProcessingError,
    ImageTimeoutError,
    PersonDetectionError,
    PrerequisiteError,
    RequiredPrerequisiteError,
    RetryExhaustedError,
    ServiceUnavailableError,
    TooltipError,
    UnsupportedImageFormatError,
)
from src.utils.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, get_circuit_breaker
from src.utils.error_handler import error_handler

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry mechanisms."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple = None,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            ImageProcessingError,
            ServiceUnavailableError,
            PrerequisiteError,
        )


class UXErrorHandler:
    """Enhanced error handler for UX enhancement features."""

    def __init__(self):
        self.processing_stats = {
            "image_processing_failures": 0,
            "prerequisite_failures": 0,
            "tooltip_failures": 0,
            "fallback_activations": 0,
            "retry_exhaustions": 0,
        }
        self.circuit_breakers = {}

    def handle_image_processing_error(
        self,
        error: Exception,
        image_path: str = "",
        operation: str = "processing",
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Handle image processing errors with specialized logic.

        Args:
            error: The exception that occurred
            image_path: Path to the image being processed
            operation: Type of operation that failed
            context: Additional context information

        Returns:
            Dict containing error information and fallback options
        """
        self.processing_stats["image_processing_failures"] += 1

        # Convert to appropriate UX exception if needed
        if not isinstance(error, ImageProcessingError):
            if "timeout" in str(error).lower():
                error = ImageTimeoutError(operation, 30)
            elif "format" in str(error).lower() or "decode" in str(error).lower():
                error = UnsupportedImageFormatError("unknown", [".jpg", ".png", ".bmp"])
            elif "load" in str(error).lower() or "read" in str(error).lower():
                error = ImageCorruptionError(image_path)
            else:
                error = ImageProcessingError(str(error))

        # Enhanced context
        enhanced_context = {
            "image_path": image_path,
            "operation": operation,
            "processing_stats": self.processing_stats.copy(),
            **(context or {}),
        }

        # Handle the error with base handler
        error_record = error_handler.handle_error(
            error=error, context=enhanced_context, show_user_message=False
        )

        # Determine fallback options
        fallback_options = self._determine_image_fallback_options(error, operation, image_path)

        # Show specialized user message
        self._show_image_processing_message(error, fallback_options)

        return {
            **error_record,
            "fallback_options": fallback_options,
            "can_retry": self._can_retry_image_operation(error),
            "suggested_action": self._get_suggested_action(error),
        }

    def handle_prerequisite_error(
        self,
        error: Exception,
        checker_name: str = "",
        required: bool = True,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Handle prerequisite check errors with specialized logic.

        Args:
            error: The exception that occurred
            checker_name: Name of the prerequisite checker
            required: Whether this is a required prerequisite
            context: Additional context information

        Returns:
            Dict containing error information and resolution options
        """
        self.processing_stats["prerequisite_failures"] += 1

        # Convert to appropriate prerequisite exception
        if not isinstance(error, PrerequisiteError):
            if required:
                error = RequiredPrerequisiteError(checker_name, [])
            else:
                error = ServiceUnavailableError(checker_name)

        # Enhanced context
        enhanced_context = {
            "checker_name": checker_name,
            "required": required,
            "prerequisite_stats": self.processing_stats.copy(),
            **(context or {}),
        }

        # Handle the error
        error_record = error_handler.handle_error(
            error=error, context=enhanced_context, show_user_message=False
        )

        # Determine resolution options
        resolution_options = self._determine_prerequisite_resolution(error, checker_name, required)

        # Show specialized user message
        self._show_prerequisite_message(error, resolution_options, required)

        return {
            **error_record,
            "resolution_options": resolution_options,
            "blocks_operation": required,
            "can_continue_with_fallback": not required,
        }

    def handle_tooltip_error(
        self,
        error: Exception,
        element_id: str = "",
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Handle tooltip system errors gracefully.

        Args:
            error: The exception that occurred
            element_id: ID of the UI element
            context: Additional context information

        Returns:
            Dict containing error information and fallback content
        """
        self.processing_stats["tooltip_failures"] += 1

        # Convert to tooltip exception
        if not isinstance(error, TooltipError):
            error = TooltipError(f"Tooltip error for {element_id}: {str(error)}")

        # Enhanced context
        enhanced_context = {
            "element_id": element_id,
            "tooltip_stats": self.processing_stats.copy(),
            **(context or {}),
        }

        # Handle the error (don't show user message for tooltips)
        error_record = error_handler.handle_error(
            error=error, context=enhanced_context, show_user_message=False
        )

        # Provide fallback tooltip content
        fallback_content = self._get_fallback_tooltip_content(element_id)

        return {
            **error_record,
            "fallback_content": fallback_content,
            "should_hide_tooltip": True,
        }

    def _determine_image_fallback_options(
        self, error: ImageProcessingError, operation: str, image_path: str
    ) -> Dict[str, Any]:
        """Determine fallback options for image processing errors."""
        options = {
            "use_original": True,
            "retry_with_different_params": False,
            "suggest_different_image": False,
            "disable_feature": False,
        }

        if isinstance(error, ImageTimeoutError):
            options.update(
                {
                    "retry_with_different_params": True,
                    "suggested_params": {"max_processing_time": 60, "reduce_quality": True},
                }
            )
        elif isinstance(error, UnsupportedImageFormatError):
            options.update({"suggest_different_image": True, "use_original": False})
        elif isinstance(error, ImageCorruptionError):
            options.update({"suggest_different_image": True, "use_original": False})
        elif isinstance(error, PersonDetectionError):
            options.update(
                {
                    "retry_with_different_params": True,
                    "suggested_params": {"detection_threshold": 0.5, "use_fallback_detection": True},
                }
            )
        elif isinstance(error, BackgroundRemovalError):
            options.update(
                {
                    "retry_with_different_params": True,
                    "suggested_params": {"background_method": "transparent", "use_mask_fallback": True},
                }
            )

        return options

    def _determine_prerequisite_resolution(
        self, error: PrerequisiteError, checker_name: str, required: bool
    ) -> Dict[str, Any]:
        """Determine resolution options for prerequisite errors."""
        resolution = {
            "can_auto_resolve": False,
            "user_action_required": True,
            "resolution_steps": [],
            "estimated_time": "unknown",
        }

        if isinstance(error, ServiceUnavailableError):
            resolution.update(
                {
                    "resolution_steps": [
                        f"Check if {checker_name} service is running",
                        "Verify network connectivity",
                        "Wait for service to recover",
                    ],
                    "estimated_time": "1-5 minutes",
                }
            )
        elif isinstance(error, RequiredPrerequisiteError):
            if "ollama" in checker_name.lower():
                resolution.update(
                    {
                        "resolution_steps": [
                            "Install Ollama: https://ollama.ai/download",
                            "Start Ollama service: 'ollama serve'",
                            "Install a model: 'ollama pull llama2'",
                        ],
                        "estimated_time": "5-15 minutes",
                    }
                )
            elif "database" in checker_name.lower():
                resolution.update(
                    {
                        "resolution_steps": [
                            "Check PostgreSQL service status",
                            "Verify database connection settings",
                            "Run database migrations if needed",
                        ],
                        "estimated_time": "2-10 minutes",
                    }
                )
            elif "consent" in checker_name.lower():
                resolution.update(
                    {
                        "can_auto_resolve": True,
                        "resolution_steps": ["Go to Settings", "Review and accept required consents"],
                        "estimated_time": "1-2 minutes",
                    }
                )

        return resolution

    def _get_fallback_tooltip_content(self, element_id: str) -> str:
        """Get fallback tooltip content when tooltip system fails."""
        fallback_tooltips = {
            "register_button": "Create your account to access GITTE features",
            "consent_checkbox": "Required for AI features",
            "image_generation_button": "Generate your avatar image",
            "chat_input": "Chat with your AI assistant",
            "prerequisite_check": "Check system requirements",
        }

        return fallback_tooltips.get(element_id, "Help temporarily unavailable")

    def _can_retry_image_operation(self, error: ImageProcessingError) -> bool:
        """Determine if image operation can be retried."""
        non_retryable_errors = (UnsupportedImageFormatError, ImageCorruptionError)
        return not isinstance(error, non_retryable_errors)

    def _get_suggested_action(self, error: ImageProcessingError) -> str:
        """Get suggested action for image processing error."""
        if isinstance(error, ImageTimeoutError):
            return "Try with a smaller image or increase timeout"
        elif isinstance(error, UnsupportedImageFormatError):
            return "Convert image to JPG or PNG format"
        elif isinstance(error, ImageCorruptionError):
            return "Upload a different image file"
        elif isinstance(error, PersonDetectionError):
            return "Ensure image contains a clear, single person"
        elif isinstance(error, BackgroundRemovalError):
            return "Try with a different background removal method"
        else:
            return "Try again or contact support"

    def _show_image_processing_message(
        self, error: ImageProcessingError, fallback_options: Dict[str, Any]
    ):
        """Show user-friendly message for image processing errors."""
        try:
            if isinstance(error, ImageTimeoutError):
                st.warning(
                    "⏱️ Image processing is taking longer than expected. "
                    "Using original image for now. Try with a smaller image for faster processing."
                )
            elif isinstance(error, UnsupportedImageFormatError):
                st.error(
                    "🖼️ Unsupported image format. Please upload a JPG, PNG, or BMP image."
                )
            elif isinstance(error, ImageCorruptionError):
                st.error(
                    "💥 The image file appears to be corrupted. Please try uploading a different image."
                )
            elif isinstance(error, PersonDetectionError):
                st.warning(
                    "👤 Unable to detect a person in the image. "
                    "Please ensure the image contains a clear, single person."
                )
            elif isinstance(error, BackgroundRemovalError):
                st.info(
                    "🎨 Background removal failed. Using original image instead. "
                    "You can manually adjust the image if needed."
                )
            else:
                st.warning(f"⚠️ {error.user_message}")

            # Show fallback options if available
            if fallback_options.get("use_original"):
                st.info("ℹ️ Using original image as fallback.")

        except Exception:
            # Fail silently if Streamlit is not available
            pass

    def _show_prerequisite_message(
        self, error: PrerequisiteError, resolution_options: Dict[str, Any], required: bool
    ):
        """Show user-friendly message for prerequisite errors."""
        try:
            if required:
                st.error(f"🚫 {error.user_message}")
                
                if resolution_options["resolution_steps"]:
                    st.write("**To resolve this issue:**")
                    for i, step in enumerate(resolution_options["resolution_steps"], 1):
                        st.write(f"{i}. {step}")
                    
                    if resolution_options["estimated_time"] != "unknown":
                        st.write(f"⏱️ Estimated time: {resolution_options['estimated_time']}")
            else:
                st.warning(f"⚠️ {error.user_message}")
                st.info("ℹ️ You can continue with limited functionality.")

        except Exception:
            # Fail silently if Streamlit is not available
            pass

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.processing_stats,
            "total_failures": sum(self.processing_stats.values()),
            "circuit_breaker_stats": {
                name: breaker.get_stats() for name, breaker in self.circuit_breakers.items()
            },
        }

    def reset_stats(self):
        """Reset processing statistics."""
        for key in self.processing_stats:
            self.processing_stats[key] = 0


# Global UX error handler instance
ux_error_handler = UXErrorHandler()


def with_retry(
    retry_config: RetryConfig = None,
    circuit_breaker_name: str = None,
    fallback_func: Callable = None,
) -> Callable:
    """
    Decorator to add retry logic and circuit breaker protection.

    Args:
        retry_config: Configuration for retry behavior
        circuit_breaker_name: Name of circuit breaker to use
        fallback_func: Fallback function if all retries fail

    Returns:
        Decorated function with retry and circuit breaker logic
    """
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get circuit breaker if specified
            circuit_breaker = None
            if circuit_breaker_name:
                circuit_breaker = get_circuit_breaker(
                    circuit_breaker_name,
                    CircuitBreakerConfig(
                        failure_threshold=3,
                        recovery_timeout=60,
                        expected_exceptions=retry_config.retryable_exceptions,
                    ),
                )

            last_exception = None
            
            for attempt in range(retry_config.max_retries + 1):
                try:
                    # Use circuit breaker if available
                    if circuit_breaker:
                        return circuit_breaker.call(func, *args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except retry_config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < retry_config.max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            retry_config.base_delay * (retry_config.exponential_base ** attempt),
                            retry_config.max_delay,
                        )
                        
                        # Add jitter if enabled
                        if retry_config.jitter:
                            import random
                            delay *= (0.5 + random.random() * 0.5)
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{retry_config.max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s"
                        )
                        
                        time.sleep(delay)
                    else:
                        # All retries exhausted
                        retry_error = RetryExhaustedError(
                            func.__name__, retry_config.max_retries, str(e)
                        )
                        
                        # Try fallback if available
                        if fallback_func:
                            try:
                                logger.info(f"Using fallback for {func.__name__} after retry exhaustion")
                                fallback_result = fallback_func(*args, **kwargs)
                                
                                # Log fallback activation
                                ux_error_handler.processing_stats["fallback_activations"] += 1
                                
                                # Show user message about fallback
                                try:
                                    st.info("ℹ️ Using simplified functionality due to service issues.")
                                except:
                                    pass
                                
                                return fallback_result
                            except Exception as fallback_error:
                                logger.error(f"Fallback also failed for {func.__name__}: {fallback_error}")
                                raise retry_error from fallback_error
                        else:
                            ux_error_handler.processing_stats["retry_exhaustions"] += 1
                            raise retry_error from e

                except Exception as e:
                    # Non-retryable exception
                    raise e

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def with_image_error_handling(
    operation: str = "processing",
    fallback_to_original: bool = True,
    timeout_seconds: int = 30,
) -> Callable:
    """
    Decorator for image processing functions with specialized error handling.

    Args:
        operation: Name of the operation for error reporting
        fallback_to_original: Whether to fallback to original image
        timeout_seconds: Timeout for the operation

    Returns:
        Decorated function with image processing error handling
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            image_path = kwargs.get("image_path", args[0] if args else "unknown")

            try:
                # Check timeout during execution
                result = func(*args, **kwargs)
                
                processing_time = time.time() - start_time
                if processing_time > timeout_seconds:
                    raise ImageTimeoutError(operation, timeout_seconds)
                
                return result

            except Exception as e:
                processing_time = time.time() - start_time
                
                # Handle the error with specialized logic
                error_info = ux_error_handler.handle_image_processing_error(
                    error=e,
                    image_path=str(image_path),
                    operation=operation,
                    context={"processing_time": processing_time},
                )

                # Apply fallback if configured
                if fallback_to_original and error_info["fallback_options"].get("use_original"):
                    logger.info(f"Using original image as fallback for {operation}")
                    return {"success": False, "fallback_used": True, "original_path": image_path}

                # Re-raise if no fallback
                raise

        return wrapper

    return decorator


def with_prerequisite_error_handling(
    checker_name: str = "",
    required: bool = True,
    allow_fallback: bool = False,
) -> Callable:
    """
    Decorator for prerequisite checking functions with specialized error handling.

    Args:
        checker_name: Name of the prerequisite checker
        required: Whether this is a required prerequisite
        allow_fallback: Whether to allow fallback behavior

    Returns:
        Decorated function with prerequisite error handling
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                # Handle the error with specialized logic
                error_info = ux_error_handler.handle_prerequisite_error(
                    error=e, checker_name=checker_name, required=required
                )

                # If not required and fallback is allowed, return degraded result
                if not required and allow_fallback:
                    logger.info(f"Using fallback for non-required prerequisite {checker_name}")
                    return {
                        "status": "warning",
                        "message": f"{checker_name} unavailable, using fallback",
                        "fallback_used": True,
                    }

                # Re-raise for required prerequisites
                raise

        return wrapper

    return decorator


def safe_tooltip_execution(element_id: str = "") -> Callable:
    """
    Decorator for tooltip functions that should never fail.

    Args:
        element_id: ID of the UI element

    Returns:
        Decorated function that handles tooltip errors gracefully
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                # Handle tooltip error gracefully
                error_info = ux_error_handler.handle_tooltip_error(error=e, element_id=element_id)

                # Return fallback content
                return error_info["fallback_content"]

        return wrapper

    return decorator


def get_ux_error_stats() -> Dict[str, Any]:
    """Get UX enhancement error statistics."""
    return ux_error_handler.get_processing_stats()


def reset_ux_error_stats():
    """Reset UX enhancement error statistics."""
    ux_error_handler.reset_stats()