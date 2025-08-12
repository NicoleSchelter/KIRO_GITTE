"""
LLM Provider interfaces and implementations for GITTE system.
Provides abstraction layer for different LLM services with Ollama implementation.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.config import config
from src.utils.circuit_breaker import CircuitBreakerConfig, circuit_breaker
from src.utils.error_handler import handle_errors

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM provider."""

    text: str
    model: str
    tokens_used: int | None = None
    latency_ms: int | None = None
    request_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid4())


@dataclass
class LLMStreamResponse:
    """Streaming response from LLM provider."""

    text_stream: Iterator[str]
    model: str
    request_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid4())


@dataclass
class LLMRequest:
    """Request to LLM provider."""

    prompt: str
    model: str
    parameters: dict[str, Any] | None = None
    stream: bool = False
    request_id: str | None = None

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid4())
        if self.parameters is None:
            self.parameters = {}


# Import exception classes from centralized exceptions module
from src.exceptions import LLMConnectionError, LLMModelError, LLMProviderError, LLMTimeoutError


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate_response(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            request: LLM request containing prompt, model, and parameters

        Returns:
            LLMResponse: Generated response

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
    def generate_streaming_response(self, request: LLMRequest) -> LLMStreamResponse:
        """
        Generate a streaming response from the LLM.

        Args:
            request: LLM request with stream=True

        Returns:
            LLMStreamResponse: Streaming response

        Raises:
            LLMProviderError: If generation fails
        """
        pass

    @abstractmethod
    def list_models(self) -> dict[str, Any]:
        """
        List available models.

        Returns:
            Dict containing available models and their metadata
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the LLM service is healthy.

        Returns:
            bool: True if service is healthy
        """
        pass

    @abstractmethod
    def get_model_info(self, model: str) -> dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            Dict containing model information
        """
        pass


class OllamaProvider(LLMProvider):
    """Ollama LLM provider implementation."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama server URL (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
            max_retries: Maximum retry attempts (defaults to config)
        """
        self.base_url = base_url or config.llm.ollama_url
        self.timeout = timeout or config.llm.timeout_seconds
        self.max_retries = max_retries or config.llm.max_retries

        # Ensure base_url doesn't end with slash
        self.base_url = self.base_url.rstrip("/")

        # Setup HTTP session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,  # Exponential backoff: 1, 2, 4 seconds
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(
            f"Initialized OllamaProvider with base_url={self.base_url}, timeout={self.timeout}s, max_retries={self.max_retries}"
        )

    @circuit_breaker(
        name="ollama_llm",
        config=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            success_threshold=2,
            timeout=30,
            expected_exceptions=(
                LLMProviderError,
                LLMConnectionError,
                LLMTimeoutError,
                LLMModelError,
            ),
        ),
    )
    @handle_errors(context={"service": "ollama_llm"})
    def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response from Ollama."""
        start_time = time.time()

        try:
            # Prepare request payload
            payload = {
                "model": request.model,
                "prompt": request.prompt,
                "stream": False,
                **request.parameters,
            }

            logger.debug(
                f"Sending request to Ollama: model={request.model}, prompt_length={len(request.prompt)}"
            )

            # Make request to Ollama
            response = self._make_request("/api/generate", payload)

            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract response data
            response_text = response.get("response", "")
            tokens_used = self._extract_token_count(response)

            llm_response = LLMResponse(
                text=response_text,
                model=request.model,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                request_id=request.request_id,
                metadata={
                    "ollama_response": response,
                    "prompt_length": len(request.prompt),
                    "response_length": len(response_text),
                },
            )

            logger.info(
                f"Generated response: model={request.model}, latency={latency_ms}ms, tokens={tokens_used}"
            )
            return llm_response

        except requests.exceptions.Timeout:
            raise LLMTimeoutError(f"Request to Ollama timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(f"Failed to connect to Ollama at {self.base_url}: {e}")
        except requests.exceptions.RequestException as e:
            raise LLMProviderError(f"Request to Ollama failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in generate_response: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def generate_streaming_response(self, request: LLMRequest) -> LLMStreamResponse:
        """Generate streaming response from Ollama."""
        try:
            # Prepare request payload
            payload = {
                "model": request.model,
                "prompt": request.prompt,
                "stream": True,
                **request.parameters,
            }

            logger.debug(f"Sending streaming request to Ollama: model={request.model}")

            # Make streaming request
            response = self.session.post(
                f"{self.base_url}/api/generate", json=payload, timeout=self.timeout, stream=True
            )
            response.raise_for_status()

            # Create text stream generator
            def text_generator():
                try:
                    for line in response.iter_lines(decode_unicode=True):
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse streaming response line: {line}")
                                continue
                except Exception as e:
                    logger.error(f"Error in streaming response: {e}")
                    raise LLMProviderError(f"Streaming error: {e}")

            return LLMStreamResponse(
                text_stream=text_generator(),
                model=request.model,
                request_id=request.request_id,
                metadata={"streaming": True},
            )

        except requests.exceptions.Timeout:
            raise LLMTimeoutError(f"Streaming request to Ollama timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise LLMConnectionError(f"Failed to connect to Ollama at {self.base_url}: {e}")
        except requests.exceptions.RequestException as e:
            raise LLMProviderError(f"Streaming request to Ollama failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in generate_streaming_response: {e}")
            raise LLMProviderError(f"Unexpected error: {e}")

    def list_models(self) -> dict[str, Any]:
        """List available models from Ollama."""
        try:
            response = self._make_request("/api/tags", method="GET")
            models = response.get("models", [])

            # Format models for easier consumption
            formatted_models = {}
            for model in models:
                name = model.get("name", "unknown")
                formatted_models[name] = {
                    "name": name,
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at"),
                    "digest": model.get("digest"),
                    "details": model.get("details", {}),
                }

            logger.debug(f"Listed {len(formatted_models)} models from Ollama")
            return {"models": formatted_models, "count": len(formatted_models)}

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise LLMProviderError(f"Failed to list models: {e}")

    def health_check(self) -> bool:
        """Check Ollama service health."""
        try:
            # Try to list models as a health check
            self._make_request("/api/tags", method="GET")
            logger.debug("Ollama health check passed")
            return True
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def get_model_info(self, model: str) -> dict[str, Any]:
        """Get information about a specific model."""
        try:
            payload = {"name": model}
            response = self._make_request("/api/show", payload)

            return {
                "name": model,
                "modelfile": response.get("modelfile", ""),
                "parameters": response.get("parameters", {}),
                "template": response.get("template", ""),
                "details": response.get("details", {}),
                "model_info": response.get("model_info", {}),
            }

        except Exception as e:
            logger.error(f"Failed to get model info for {model}: {e}")
            raise LLMModelError(f"Failed to get model info for {model}: {e}")

    def _make_request(
        self, endpoint: str, payload: dict[str, Any] | None = None, method: str = "POST"
    ) -> dict[str, Any]:
        """Make HTTP request to Ollama API."""
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url, timeout=self.timeout)
            else:
                response = self.session.post(url, json=payload, timeout=self.timeout)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise LLMModelError(f"Model or endpoint not found: {e}")
            elif response.status_code == 400:
                raise LLMModelError(f"Bad request to Ollama: {e}")
            else:
                raise LLMProviderError(f"HTTP error {response.status_code}: {e}")
        except requests.exceptions.JSONDecodeError:
            raise LLMProviderError("Invalid JSON response from Ollama")

    def _extract_token_count(self, response: dict[str, Any]) -> int | None:
        """Extract token count from Ollama response."""
        # Ollama may provide token information in different formats
        if "eval_count" in response:
            return response["eval_count"]
        elif "prompt_eval_count" in response and "eval_count" in response:
            return response["prompt_eval_count"] + response["eval_count"]
        else:
            # Fallback: estimate tokens (rough approximation)
            text = response.get("response", "")
            return len(text.split()) if text else None


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses: dict[str, str] | None = None, latency_ms: int = 100):
        """
        Initialize mock provider.

        Args:
            responses: Dict mapping prompts to responses
            latency_ms: Simulated latency
        """
        self.responses = responses or {"default": "Mock response"}
        self.latency_ms = latency_ms
        self.call_count = 0
        self.last_request = None

    def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate mock response."""
        self.call_count += 1
        self.last_request = request

        # Simulate latency
        time.sleep(self.latency_ms / 1000.0)

        # Find response
        response_text = self.responses.get(
            request.prompt, self.responses.get("default", "Mock response")
        )

        return LLMResponse(
            text=response_text,
            model=request.model,
            tokens_used=len(response_text.split()),
            latency_ms=self.latency_ms,
            request_id=request.request_id,
            metadata={"mock": True, "call_count": self.call_count},
        )

    def generate_streaming_response(self, request: LLMRequest) -> LLMStreamResponse:
        """Generate mock streaming response."""
        self.call_count += 1
        self.last_request = request

        response_text = self.responses.get(
            request.prompt, self.responses.get("default", "Mock response")
        )

        def text_generator():
            words = response_text.split()
            for word in words:
                time.sleep(0.01)  # Simulate streaming delay
                yield word + " "

        return LLMStreamResponse(
            text_stream=text_generator(),
            model=request.model,
            request_id=request.request_id,
            metadata={"mock": True, "streaming": True},
        )

    def list_models(self) -> dict[str, Any]:
        """List mock models."""
        return {
            "models": {
                "mock-model": {"name": "mock-model", "size": 1000},
                "test-model": {"name": "test-model", "size": 2000},
            },
            "count": 2,
        }

    def health_check(self) -> bool:
        """Mock health check."""
        return True

    def get_model_info(self, model: str) -> dict[str, Any]:
        """Get mock model info."""
        return {
            "name": model,
            "modelfile": "Mock modelfile",
            "parameters": {},
            "template": "Mock template",
            "details": {"mock": True},
        }
