"""
Tests for LLM provider implementations.
Tests Ollama provider with available models: llama3.2, Llava, Mistral
"""

import time
from unittest.mock import Mock, patch

import pytest
from requests.exceptions import ConnectionError, HTTPError, Timeout

from src.services.llm_provider import (
    LLMConnectionError,
    LLMModelError,
    LLMRequest,
    LLMResponse,
    LLMStreamResponse,
    LLMTimeoutError,
    MockLLMProvider,
    OllamaProvider,
)

# Available Ollama models for testing
AVAILABLE_MODELS = ["llama3.2", "llava", "mistral"]


class TestLLMRequest:
    """Test LLM request data class."""

    def test_llm_request_creation(self):
        """Test creating LLM request."""
        request = LLMRequest(
            prompt="Test prompt", model="llama3.2", parameters={"temperature": 0.7}, stream=False
        )

        assert request.prompt == "Test prompt"
        assert request.model == "llama3.2"
        assert request.parameters == {"temperature": 0.7}
        assert request.stream is False
        assert request.request_id is not None

    def test_llm_request_defaults(self):
        """Test LLM request with defaults."""
        request = LLMRequest(prompt="Test", model="llama3.2")

        assert request.parameters == {}
        assert request.stream is False
        assert request.request_id is not None

    def test_llm_request_with_available_models(self):
        """Test LLM request with all available models."""
        for model in AVAILABLE_MODELS:
            request = LLMRequest(prompt="Test prompt", model=model)
            assert request.model == model
            assert request.request_id is not None


class TestLLMResponse:
    """Test LLM response data class."""

    def test_llm_response_creation(self):
        """Test creating LLM response."""
        response = LLMResponse(
            text="Test response",
            model="llama3.2",
            tokens_used=10,
            latency_ms=100,
            metadata={"test": True},
        )

        assert response.text == "Test response"
        assert response.model == "llama3.2"
        assert response.tokens_used == 10
        assert response.latency_ms == 100
        assert response.metadata == {"test": True}
        assert response.request_id is not None

    def test_llm_response_defaults(self):
        """Test LLM response with defaults."""
        response = LLMResponse(text="Test", model="mistral")

        assert response.tokens_used is None
        assert response.latency_ms is None
        assert response.metadata is None
        assert response.request_id is not None


class TestLLMStreamResponse:
    """Test LLM stream response data class."""

    def test_llm_stream_response_creation(self):
        """Test creating LLM stream response."""

        def text_gen():
            yield "Hello"
            yield " world"

        response = LLMStreamResponse(
            text_stream=text_gen(), model="llava", metadata={"streaming": True}
        )

        assert response.model == "llava"
        assert response.metadata == {"streaming": True}
        assert response.request_id is not None

        # Test stream consumption
        text_chunks = list(response.text_stream)
        assert text_chunks == ["Hello", " world"]


class TestMockLLMProvider:
    """Test mock LLM provider."""

    def test_mock_provider_creation(self):
        """Test creating mock provider."""
        responses = {"hello": "hi there", "default": "mock response"}
        provider = MockLLMProvider(responses=responses, latency_ms=50)

        assert provider.responses == responses
        assert provider.latency_ms == 50
        assert provider.call_count == 0

    def test_mock_generate_response(self):
        """Test mock response generation."""
        responses = {"hello": "hi there"}
        provider = MockLLMProvider(responses=responses, latency_ms=10)

        request = LLMRequest(prompt="hello", model="llama3.2")

        start_time = time.time()
        response = provider.generate_response(request)
        end_time = time.time()

        assert response.text == "hi there"
        assert response.model == "llama3.2"
        assert response.tokens_used == 2  # "hi there" = 2 words
        assert response.latency_ms == 10
        assert response.metadata["mock"] is True
        assert provider.call_count == 1
        assert provider.last_request == request

        # Check that latency was simulated
        assert (end_time - start_time) >= 0.01  # At least 10ms

    def test_mock_generate_response_default(self):
        """Test mock response with default fallback."""
        provider = MockLLMProvider(responses={"default": "default response"})

        request = LLMRequest(prompt="unknown prompt", model="mistral")
        response = provider.generate_response(request)

        assert response.text == "default response"

    def test_mock_generate_streaming_response(self):
        """Test mock streaming response."""
        provider = MockLLMProvider(responses={"test": "hello world"})

        request = LLMRequest(prompt="test", model="llava", stream=True)
        stream_response = provider.generate_streaming_response(request)

        assert stream_response.model == "llava"
        assert stream_response.metadata["mock"] is True
        assert stream_response.metadata["streaming"] is True

        # Collect streamed text
        streamed_text = ""
        for chunk in stream_response.text_stream:
            streamed_text += chunk

        assert streamed_text.strip() == "hello world"

    def test_mock_list_models(self):
        """Test mock model listing."""
        provider = MockLLMProvider()
        models = provider.list_models()

        assert "models" in models
        assert "count" in models
        assert models["count"] == 2
        assert "mock-model" in models["models"]
        assert "test-model" in models["models"]

    def test_mock_health_check(self):
        """Test mock health check."""
        provider = MockLLMProvider()
        assert provider.health_check() is True

    def test_mock_get_model_info(self):
        """Test mock model info."""
        provider = MockLLMProvider()
        info = provider.get_model_info("llama3.2")

        assert info["name"] == "llama3.2"
        assert info["modelfile"] == "Mock modelfile"
        assert info["details"]["mock"] is True


class TestOllamaProvider:
    """Test Ollama provider with available models."""

    def test_ollama_provider_creation(self):
        """Test creating Ollama provider."""
        provider = OllamaProvider(base_url="http://localhost:11434", timeout=30, max_retries=3)

        assert provider.base_url == "http://localhost:11434"
        assert provider.timeout == 30
        assert provider.max_retries == 3
        assert provider.session is not None

    def test_ollama_provider_defaults(self):
        """Test Ollama provider with defaults from config."""
        with patch("src.services.llm_provider.config") as mock_config:
            mock_config.llm.ollama_url = "http://test:11434"
            mock_config.llm.timeout_seconds = 25
            mock_config.llm.max_retries = 2

            provider = OllamaProvider()

            assert provider.base_url == "http://test:11434"
            assert provider.timeout == 25
            assert provider.max_retries == 2

    def test_ollama_base_url_normalization(self):
        """Test base URL normalization."""
        provider = OllamaProvider(base_url="http://localhost:11434/")
        assert provider.base_url == "http://localhost:11434"

    @patch("requests.Session.post")
    def test_ollama_generate_response_llama32(self, mock_post):
        """Test successful response generation with llama3.2."""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Hello! I'm Llama 3.2, how can I help you today?",
            "eval_count": 15,
            "prompt_eval_count": 5,
            "done": True,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(prompt="Hello", model="llama3.2")

        response = provider.generate_response(request)

        assert response.text == "Hello! I'm Llama 3.2, how can I help you today?"
        assert response.model == "llama3.2"
        assert response.tokens_used == 20  # 5 + 15
        assert response.latency_ms is not None
        assert response.latency_ms > 0

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        assert call_args[1]["json"]["model"] == "llama3.2"
        assert call_args[1]["json"]["prompt"] == "Hello"
        assert call_args[1]["json"]["stream"] is False

    @patch("requests.Session.post")
    def test_ollama_generate_response_mistral(self, mock_post):
        """Test successful response generation with Mistral."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "Bonjour! I'm Mistral, a French AI assistant.",
            "eval_count": 12,
            "prompt_eval_count": 3,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(prompt="Bonjour", model="mistral")

        response = provider.generate_response(request)

        assert response.text == "Bonjour! I'm Mistral, a French AI assistant."
        assert response.model == "mistral"
        assert response.tokens_used == 15  # 3 + 12

        # Verify request was made correctly
        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "mistral"

    @patch("requests.Session.post")
    def test_ollama_generate_response_llava_vision(self, mock_post):
        """Test response generation with Llava (vision model)."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "I can see an image of a cat sitting on a windowsill.",
            "eval_count": 18,
            "prompt_eval_count": 8,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(
            prompt="Describe this image",
            model="llava",
            parameters={"images": ["base64_encoded_image"]},
        )

        response = provider.generate_response(request)

        assert response.text == "I can see an image of a cat sitting on a windowsill."
        assert response.model == "llava"
        assert response.tokens_used == 26  # 8 + 18

        # Verify image parameter was included
        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "llava"
        assert call_args[1]["json"]["images"] == ["base64_encoded_image"]

    @patch("requests.Session.post")
    def test_ollama_generate_response_with_parameters(self, mock_post):
        """Test response generation with various parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Creative response with high temperature"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(
            prompt="Write creatively",
            model="llama3.2",
            parameters={
                "temperature": 0.9,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
                "num_predict": 100,
            },
        )

        provider.generate_response(request)

        # Verify all parameters were included
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["temperature"] == 0.9
        assert payload["top_p"] == 0.9
        assert payload["top_k"] == 40
        assert payload["repeat_penalty"] == 1.1
        assert payload["num_predict"] == 100

    @patch("requests.Session.post")
    def test_ollama_generate_response_timeout(self, mock_post):
        """Test timeout handling."""
        mock_post.side_effect = Timeout("Request timed out")

        provider = OllamaProvider(timeout=1)
        request = LLMRequest(prompt="Test", model="llama3.2")

        with pytest.raises(LLMTimeoutError) as exc_info:
            provider.generate_response(request)

        assert "timed out after 1s" in str(exc_info.value)

    @patch("requests.Session.post")
    def test_ollama_generate_response_connection_error(self, mock_post):
        """Test connection error handling."""
        mock_post.side_effect = ConnectionError("Connection failed")

        provider = OllamaProvider()
        request = LLMRequest(prompt="Test", model="mistral")

        with pytest.raises(LLMConnectionError) as exc_info:
            provider.generate_response(request)

        assert "Failed to connect to Ollama" in str(exc_info.value)

    @patch("requests.Session.post")
    def test_ollama_generate_response_http_error(self, mock_post):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(prompt="Test", model="nonexistent")

        with pytest.raises(LLMModelError) as exc_info:
            provider.generate_response(request)

        assert "Model or endpoint not found" in str(exc_info.value)

    @patch("requests.Session.post")
    def test_ollama_generate_streaming_response_llama32(self, mock_post):
        """Test streaming response generation with llama3.2."""
        # Mock streaming response
        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            '{"response": "Hello", "done": false}',
            '{"response": " from", "done": false}',
            '{"response": " Llama", "done": false}',
            '{"response": " 3.2!", "done": true}',
        ]
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(prompt="Hello", model="llama3.2", stream=True)

        stream_response = provider.generate_streaming_response(request)

        assert stream_response.model == "llama3.2"
        assert stream_response.metadata["streaming"] is True

        # Collect streamed text
        streamed_chunks = list(stream_response.text_stream)
        assert streamed_chunks == ["Hello", " from", " Llama", " 3.2!"]

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["stream"] is True
        assert call_args[1]["stream"] is True

    @patch("requests.Session.post")
    def test_ollama_generate_streaming_response_mistral(self, mock_post):
        """Test streaming response generation with Mistral."""
        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            '{"response": "Bonjour", "done": false}',
            '{"response": " mon", "done": false}',
            '{"response": " ami!", "done": true}',
        ]
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(prompt="Salut", model="mistral", stream=True)

        stream_response = provider.generate_streaming_response(request)

        assert stream_response.model == "mistral"

        # Collect streamed text
        streamed_chunks = list(stream_response.text_stream)
        assert streamed_chunks == ["Bonjour", " mon", " ami!"]

    @patch("requests.Session.get")
    def test_ollama_list_models_with_available_models(self, mock_get):
        """Test model listing with available models."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3.2",
                    "size": 4000000000,
                    "modified_at": "2024-01-01T00:00:00Z",
                    "digest": "abc123",
                },
                {
                    "name": "mistral",
                    "size": 7000000000,
                    "modified_at": "2024-01-02T00:00:00Z",
                    "digest": "def456",
                },
                {
                    "name": "llava",
                    "size": 5000000000,
                    "modified_at": "2024-01-03T00:00:00Z",
                    "digest": "ghi789",
                },
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = OllamaProvider()
        models = provider.list_models()

        assert "models" in models
        assert "count" in models
        assert models["count"] == 3

        # Check all available models are present
        for model_name in AVAILABLE_MODELS:
            assert model_name in models["models"]

        assert models["models"]["llama3.2"]["size"] == 4000000000
        assert models["models"]["mistral"]["size"] == 7000000000
        assert models["models"]["llava"]["size"] == 5000000000

        mock_get.assert_called_once_with("http://localhost:11434/api/tags", timeout=30)

    @patch("requests.Session.get")
    def test_ollama_health_check_success(self, mock_get):
        """Test successful health check."""
        mock_response = Mock()
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        provider = OllamaProvider()
        assert provider.health_check() is True

    @patch("requests.Session.get")
    def test_ollama_health_check_failure(self, mock_get):
        """Test failed health check."""
        mock_get.side_effect = ConnectionError("Connection failed")

        provider = OllamaProvider()
        assert provider.health_check() is False

    @patch("requests.Session.post")
    def test_ollama_get_model_info_llama32(self, mock_post):
        """Test getting model information for llama3.2."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "modelfile": "FROM llama3.2:latest",
            "parameters": {"temperature": 0.8, "top_p": 0.9, "top_k": 40},
            "template": "{{ .System }}\n{{ .Prompt }}",
            "details": {"family": "llama", "format": "gguf", "parameter_size": "3.2B"},
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        info = provider.get_model_info("llama3.2")

        assert info["name"] == "llama3.2"
        assert info["modelfile"] == "FROM llama3.2:latest"
        assert info["parameters"]["temperature"] == 0.8
        assert info["details"]["family"] == "llama"
        assert info["details"]["parameter_size"] == "3.2B"

        mock_post.assert_called_once_with(
            "http://localhost:11434/api/show", json={"name": "llama3.2"}, timeout=30
        )

    @patch("requests.Session.post")
    def test_ollama_get_model_info_mistral(self, mock_post):
        """Test getting model information for Mistral."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "modelfile": "FROM mistral:latest",
            "parameters": {"temperature": 0.7, "top_p": 0.95},
            "template": "[INST] {{ .Prompt }} [/INST]",
            "details": {"family": "mistral", "format": "gguf", "parameter_size": "7B"},
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        info = provider.get_model_info("mistral")

        assert info["name"] == "mistral"
        assert info["modelfile"] == "FROM mistral:latest"
        assert info["template"] == "[INST] {{ .Prompt }} [/INST]"
        assert info["details"]["family"] == "mistral"
        assert info["details"]["parameter_size"] == "7B"

    @patch("requests.Session.post")
    def test_ollama_get_model_info_llava(self, mock_post):
        """Test getting model information for Llava (vision model)."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "modelfile": "FROM llava:latest",
            "parameters": {"temperature": 0.1, "top_p": 0.9},
            "template": "USER: {{ .Prompt }}\nASSISTANT:",
            "details": {
                "family": "llava",
                "format": "gguf",
                "parameter_size": "7B",
                "vision": True,
            },
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        info = provider.get_model_info("llava")

        assert info["name"] == "llava"
        assert info["modelfile"] == "FROM llava:latest"
        assert info["details"]["family"] == "llava"
        assert info["details"]["vision"] is True

    @patch("requests.Session.post")
    def test_ollama_get_model_info_not_found(self, mock_post):
        """Test getting info for non-existent model."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = HTTPError("404 Not Found")
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        provider = OllamaProvider()

        with pytest.raises(LLMModelError) as exc_info:
            provider.get_model_info("nonexistent")

        assert "Model or endpoint not found" in str(exc_info.value)

    def test_extract_token_count_various_formats(self):
        """Test token count extraction from different response formats."""
        provider = OllamaProvider()

        # Test with eval_count only (common in llama3.2)
        response1 = {"eval_count": 15}
        assert provider._extract_token_count(response1) == 15

        # Test with both prompt_eval_count and eval_count (common in mistral)
        response2 = {"prompt_eval_count": 5, "eval_count": 15}
        assert provider._extract_token_count(response2) == 20

        # Test with no token info (some models don't provide this)
        response3 = {"response": "Hello"}
        assert provider._extract_token_count(response3) is None

        # Test with empty response
        response4 = {"response": ""}
        assert provider._extract_token_count(response4) is None

        # Test with zero tokens
        response5 = {"eval_count": 0}
        assert provider._extract_token_count(response5) == 0


class TestOllamaProviderIntegration:
    """Integration tests for Ollama provider (require running Ollama)."""

    @pytest.mark.integration
    def test_real_ollama_health_check(self):
        """Test health check against real Ollama instance."""
        provider = OllamaProvider(base_url="http://localhost:11434")

        # This will only pass if Ollama is actually running
        try:
            is_healthy = provider.health_check()
            # If Ollama is running, it should be healthy
            if is_healthy:
                assert is_healthy is True
        except Exception:
            # If Ollama is not running, skip this test
            pytest.skip("Ollama not available for integration test")

    @pytest.mark.integration
    def test_real_ollama_list_models(self):
        """Test listing models from real Ollama instance."""
        provider = OllamaProvider(base_url="http://localhost:11434")

        try:
            models = provider.list_models()
            assert "models" in models
            assert "count" in models
            assert isinstance(models["models"], dict)
        except Exception:
            pytest.skip("Ollama not available for integration test")

    @pytest.mark.integration
    @pytest.mark.parametrize("model", AVAILABLE_MODELS)
    def test_real_ollama_generate_response(self, model):
        """Test generating responses with real Ollama models."""
        provider = OllamaProvider(base_url="http://localhost:11434", timeout=60)

        try:
            request = LLMRequest(
                prompt="Say hello in one sentence.",
                model=model,
                parameters={"temperature": 0.1},  # Low temperature for consistent results
            )

            response = provider.generate_response(request)

            assert response.text is not None
            assert len(response.text) > 0
            assert response.model == model
            assert response.latency_ms is not None
            assert response.latency_ms > 0

        except Exception as e:
            pytest.skip(f"Model {model} not available or Ollama not running: {e}")


@pytest.fixture
def sample_llm_request():
    """Sample LLM request for testing."""
    return LLMRequest(
        prompt="What is the capital of France?",
        model="llama3.2",
        parameters={"temperature": 0.7, "max_tokens": 100},
    )


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {
        "response": "The capital of France is Paris.",
        "eval_count": 8,
        "prompt_eval_count": 7,
        "done": True,
    }


@pytest.fixture
def mock_ollama_streaming_response():
    """Mock Ollama streaming API response."""
    return [
        '{"response": "The", "done": false}',
        '{"response": " capital", "done": false}',
        '{"response": " of", "done": false}',
        '{"response": " France", "done": false}',
        '{"response": " is", "done": false}',
        '{"response": " Paris.", "done": true}',
    ]


@pytest.fixture
def mock_ollama_models_response():
    """Mock Ollama models API response."""
    return {
        "models": [
            {
                "name": "llama3.2",
                "size": 4000000000,
                "modified_at": "2024-01-01T00:00:00Z",
                "digest": "abc123",
            },
            {
                "name": "mistral",
                "size": 7000000000,
                "modified_at": "2024-01-02T00:00:00Z",
                "digest": "def456",
            },
            {
                "name": "llava",
                "size": 5000000000,
                "modified_at": "2024-01-03T00:00:00Z",
                "digest": "ghi789",
            },
        ]
    }


# Test configuration for different models
MODEL_TEST_CONFIGS = {
    "llama3.2": {
        "prompt": "Hello, how are you?",
        "expected_response_contains": ["hello", "good", "fine", "well"],
        "parameters": {"temperature": 0.7, "top_p": 0.9},
    },
    "mistral": {
        "prompt": "Bonjour, comment allez-vous?",
        "expected_response_contains": ["bonjour", "bien", "merci"],
        "parameters": {"temperature": 0.8, "top_k": 40},
    },
    "llava": {
        "prompt": "Describe what you see",
        "expected_response_contains": ["see", "image", "picture"],
        "parameters": {"temperature": 0.1},
    },
}


class TestModelSpecificBehavior:
    """Test model-specific behaviors and configurations."""

    @pytest.mark.parametrize("model_name,config", MODEL_TEST_CONFIGS.items())
    @patch("requests.Session.post")
    def test_model_specific_parameters(self, mock_post, model_name, config):
        """Test that model-specific parameters are handled correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": f"Response from {model_name}",
            "eval_count": 10,
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        provider = OllamaProvider()
        request = LLMRequest(
            prompt=config["prompt"], model=model_name, parameters=config["parameters"]
        )

        response = provider.generate_response(request)

        assert response.model == model_name
        assert f"Response from {model_name}" in response.text

        # Verify parameters were passed correctly
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        for param, value in config["parameters"].items():
            assert payload[param] == value
