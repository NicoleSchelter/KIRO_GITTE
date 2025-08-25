"""
LLM Service Layer for GITTE system.
Provides high-level LLM operations with configuration management and error handling.
"""

import logging
from typing import Any
from uuid import UUID

from config.config import config
from src.services.llm_provider import (
    LLMModelError,
    LLMProvider,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    LLMStreamResponse,
    MockLLMProvider,
    OllamaProvider,
)

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service layer for LLM operations.
    Handles provider management, model configuration, and high-level operations.
    """

    def __init__(self, provider: LLMProvider | None = None):
        """
        Initialize LLM service.

        Args:
            provider: LLM provider instance (defaults to OllamaProvider)
        """
        self.provider = provider or self._create_default_provider()
        self._model_cache: dict[str, dict[str, Any]] = {}
        self._health_status: bool | None = None

    def _create_default_provider(self) -> LLMProvider:
        """Create default LLM provider based on configuration."""
        if config.environment == "test":
            return MockLLMProvider()
        else:
            return OllamaProvider(
                base_url=config.llm.ollama_url,
                timeout=config.llm.timeout_seconds,
                max_retries=config.llm.max_retries,
            )

    def generate_response(
        self,
        prompt: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None,
        user_id: UUID | None = None,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: Input prompt
            model: Model name (defaults to configured default)
            parameters: Generation parameters
            user_id: User ID for audit logging

        Returns:
            LLMResponse: Generated response

        Raises:
            LLMProviderError: If generation fails
        """
        # Resolve model name
        requested_model = model or self._get_default_model()
        
        # Try to find an available model with fallback logic
        available_model = self._find_available_model(requested_model)
        
        if not available_model:
            raise LLMModelError(f"No available models found. Requested: '{requested_model}'")
        
        if available_model != requested_model:
            logger.warning(f"Model '{requested_model}' not available, using fallback '{available_model}'")

        # Prepare request
        request = LLMRequest(prompt=prompt, model=available_model, parameters=parameters or {}, stream=False)

        logger.info(
            f"Generating LLM response: model={available_model}, prompt_length={len(prompt)}, user_id={user_id}"
        )

        try:
            response = self.provider.generate_response(request)

            # Log successful generation
            logger.info(
                f"LLM response generated: model={available_model}, latency={response.latency_ms}ms, tokens={response.tokens_used}"
            )

            return response

        except LLMProviderError as e:
            logger.error(f"LLM generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LLM generation: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def generate_streaming_response(
        self,
        prompt: str,
        model: str | None = None,
        parameters: dict[str, Any] | None = None,
        user_id: UUID | None = None,
    ) -> LLMStreamResponse:
        """
        Generate a streaming response from the LLM.

        Args:
            prompt: Input prompt
            model: Model name (defaults to configured default)
            parameters: Generation parameters
            user_id: User ID for audit logging

        Returns:
            LLMStreamResponse: Streaming response

        Raises:
            LLMProviderError: If generation fails
        """
        # Resolve model name
        model = model or self._get_default_model()

        # Validate model availability
        if not self._is_model_available(model):
            raise LLMModelError(f"Model '{model}' is not available")

        # Prepare request
        request = LLMRequest(prompt=prompt, model=model, parameters=parameters or {}, stream=True)

        logger.info(
            f"Generating streaming LLM response: model={model}, prompt_length={len(prompt)}, user_id={user_id}"
        )

        try:
            response = self.provider.generate_streaming_response(request)

            logger.info(f"Streaming LLM response started: model={model}")
            return response

        except LLMProviderError as e:
            logger.error(f"Streaming LLM generation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in streaming LLM generation: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def list_available_models(self) -> dict[str, Any]:
        """
        List all available models.

        Returns:
            Dict containing available models and metadata
        """
        try:
            models_info = self.provider.list_models()

            # Cache model information
            if "models" in models_info:
                self._model_cache.update(models_info["models"])

            logger.debug(f"Listed {models_info.get('count', 0)} available models")
            return models_info

        except LLMProviderError as e:
            logger.error(f"Failed to list models: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error listing models: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def get_model_info(self, model: str) -> dict[str, Any]:
        """
        Get detailed information about a specific model.

        Args:
            model: Model name

        Returns:
            Dict containing model information
        """
        try:
            # Check cache first
            if model in self._model_cache:
                cached_info = self._model_cache[model]
                if "details" in cached_info:
                    return cached_info

            # Fetch from provider
            model_info = self.provider.get_model_info(model)

            # Update cache
            self._model_cache[model] = model_info

            logger.debug(f"Retrieved model info for {model}")
            return model_info

        except LLMProviderError as e:
            logger.error(f"Failed to get model info for {model}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting model info: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def health_check(self) -> bool:
        """
        Check if the LLM service is healthy.

        Returns:
            bool: True if service is healthy
        """
        try:
            is_healthy = self.provider.health_check()
            self._health_status = is_healthy

            if is_healthy:
                logger.debug("LLM service health check passed")
            else:
                logger.warning("LLM service health check failed")

            return is_healthy

        except Exception as e:
            logger.error(f"Health check error: {e}")
            self._health_status = False
            return False

    def get_configured_models(self) -> dict[str, str]:
        """
        Get configured model mappings.

        Returns:
            Dict mapping model aliases to actual model names
        """
        return config.llm.models.copy()

    def resolve_model_name(self, model_alias: str) -> str:
        """
        Resolve model alias to actual model name.

        Args:
            model_alias: Model alias (e.g., "default", "creative")

        Returns:
            str: Actual model name
        """
        return config.llm.models.get(model_alias, model_alias)

    def is_service_available(self) -> bool:
        """
        Check if the LLM service is available.

        Returns:
            bool: True if service is available
        """
        if self._health_status is None:
            return self.health_check()
        return self._health_status

    def get_service_status(self) -> dict[str, Any]:
        """
        Get comprehensive service status.

        Returns:
            Dict containing service status information
        """
        try:
            is_healthy = self.health_check()

            status = {
                "healthy": is_healthy,
                "provider_type": type(self.provider).__name__,
                "configured_models": self.get_configured_models(),
                "default_model": self._get_default_model(),
            }

            if is_healthy:
                try:
                    models_info = self.list_available_models()
                    status["available_models"] = list(models_info.get("models", {}).keys())
                    status["model_count"] = models_info.get("count", 0)
                except Exception as e:
                    logger.warning(f"Could not fetch available models for status: {e}")
                    status["available_models"] = []
                    status["model_count"] = 0

            return status

        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "provider_type": type(self.provider).__name__,
            }

    def _get_default_model(self) -> str:
        """Get the default model name."""
        return config.llm.models.get("default", "llama3.2")

    def _find_available_model(self, requested_model: str) -> str | None:
        """
        Find an available model, trying fallbacks if the requested model is unavailable.
        
        Args:
            requested_model: The originally requested model
            
        Returns:
            str | None: Available model name or None if no models are available
        """
        # List of models to try in order of preference
        model_fallbacks = [
            requested_model,
            "llama3.2",
            "llama3", 
            "mistral",
            "llava",
            self._get_default_model()
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_models = []
        for model in model_fallbacks:
            if model not in seen:
                seen.add(model)
                unique_models.append(model)
        
        # Try each model in order
        for model in unique_models:
            if self._is_model_available(model):
                return model
                
        # Last resort: try to get any available model
        try:
            models_info = self.list_available_models()
            available_models = list(models_info.get("models", {}).keys())
            if available_models:
                fallback_model = available_models[0]
                logger.warning(f"Using first available model as last resort: {fallback_model}")
                return fallback_model
        except Exception as e:
            logger.error(f"Failed to get available models for fallback: {e}")
            
        return None

    def _is_model_available(self, model: str) -> bool:
        """
        Check if a model is available.

        Args:
            model: Model name

        Returns:
            bool: True if model is available
        """
        try:
            # For mock provider, always return True
            if isinstance(self.provider, MockLLMProvider):
                return True

            # Check if we have cached model info
            if model in self._model_cache:
                return True

            # Try to get model info
            self.get_model_info(model)
            return True

        except LLMModelError:
            return False
        except Exception as e:
            logger.warning(f"Error checking model availability for {model}: {e}")
            return False


# Global LLM service instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def set_llm_service(service: LLMService) -> None:
    """Set the global LLM service instance (useful for testing)."""
    global _llm_service
    _llm_service = service


# Convenience functions for common operations
def generate_response(
    prompt: str,
    model: str | None = None,
    parameters: dict[str, Any] | None = None,
    user_id: UUID | None = None,
) -> LLMResponse:
    """Generate a response using the global LLM service."""
    return get_llm_service().generate_response(prompt, model, parameters, user_id)


def generate_streaming_response(
    prompt: str,
    model: str | None = None,
    parameters: dict[str, Any] | None = None,
    user_id: UUID | None = None,
) -> LLMStreamResponse:
    """Generate a streaming response using the global LLM service."""
    return get_llm_service().generate_streaming_response(prompt, model, parameters, user_id)


def list_available_models() -> dict[str, Any]:
    """List available models using the global LLM service."""
    return get_llm_service().list_available_models()


def health_check() -> bool:
    """Check LLM service health using the global LLM service."""
    return get_llm_service().health_check()


def get_service_status() -> dict[str, Any]:
    """Get service status using the global LLM service."""
    return get_llm_service().get_service_status()
