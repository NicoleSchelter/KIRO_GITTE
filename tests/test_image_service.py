"""
Tests for image service layer.
Tests image generation operations with performance monitoring and error handling.
"""

import contextlib
import shutil
import tempfile
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.services.image_provider import (
    DummyImageProvider,
    ImageGenerationError,
    ImageProviderError,
    ImageRequest,
    ImageResult,
    MockImageProvider,
    ModelLoadError,
    Text2ImageProvider,
)
from src.services.image_service import ImageService, get_image_service, set_image_service


class TestImageService:
    """Test image service."""

    def test_image_service_creation_with_provider(self):
        """Test creating image service with custom provider."""
        mock_provider = MockImageProvider()
        service = ImageService(provider=mock_provider)

        assert service.provider == mock_provider
        assert service._performance_metrics["total_generations"] == 0
        assert service._health_status is None

    def test_image_service_creation_default_provider(self):
        """Test creating image service with default provider."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.environment = "production"
            mock_config.image_provider_type = "stable_diffusion"

            # Mock StableDiffusionProvider to avoid loading actual model
            with patch("src.services.image_service.StableDiffusionProvider") as mock_sd:
                mock_sd.return_value = MockImageProvider()
                service = ImageService()
                assert service.provider is not None

    def test_image_service_creation_test_environment(self):
        """Test creating image service in test environment."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.environment = "test"

            service = ImageService()
            assert isinstance(service.provider, MockImageProvider)

    def test_image_service_creation_dummy_provider(self):
        """Test creating image service with dummy provider."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.environment = "production"
            mock_config.image_provider_type = "dummy"

            service = ImageService()
            assert isinstance(service.provider, DummyImageProvider)

    def test_image_service_creation_fallback_to_dummy(self):
        """Test fallback to dummy provider when StableDiffusion fails."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.environment = "production"
            mock_config.image_provider_type = "stable_diffusion"

            # Mock StableDiffusionProvider to raise ModelLoadError
            with patch("src.services.image_service.StableDiffusionProvider") as mock_sd:
                mock_sd.side_effect = ModelLoadError("Failed to load model")

                service = ImageService()
                assert isinstance(service.provider, DummyImageProvider)

    def test_generate_embodiment_image_success(self):
        """Test successful embodiment image generation."""
        mock_provider = MockImageProvider(generation_time=2.0)
        service = ImageService(provider=mock_provider)
        user_id = uuid4()

        result = service.generate_embodiment_image(
            prompt="A friendly teacher avatar",
            user_id=user_id,
            parameters={"width": 256, "height": 256},
        )

        assert result.image_path is not None
        assert result.generation_time == 2.0
        assert result.model_used == "mock-stable-diffusion"
        assert mock_provider.call_count == 1

        # Check performance metrics were updated
        metrics = service.get_performance_metrics()
        assert metrics["total_generations"] == 1
        assert metrics["failed_generations"] == 0
        assert metrics["average_generation_time"] == 2.0

    def test_generate_embodiment_image_with_defaults(self):
        """Test embodiment image generation with default parameters."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_result = ImageResult(image_path="test.png", generation_time=1.0)
        mock_provider.generate_image.return_value = mock_result
        service = ImageService(provider=mock_provider)

        service.generate_embodiment_image(prompt="Test prompt")

        # Check that the provider was called with correct defaults
        mock_provider.generate_image.assert_called_once()
        call_args = mock_provider.generate_image.call_args[0][0]  # Get the ImageRequest
        assert call_args.negative_prompt == "blurry, low quality, distorted, deformed"
        assert call_args.width == 512
        assert call_args.height == 512
        assert call_args.num_inference_steps == 20
        assert call_args.guidance_scale == 7.5

    def test_generate_embodiment_image_provider_error(self):
        """Test embodiment image generation with provider error."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.generate_image.side_effect = ImageGenerationError("Generation failed")
        service = ImageService(provider=mock_provider)

        with pytest.raises(ImageGenerationError):
            service.generate_embodiment_image(prompt="Test prompt")

        # Check that failure was recorded in metrics
        metrics = service.get_performance_metrics()
        assert metrics["total_generations"] == 1
        assert metrics["failed_generations"] == 1

    def test_generate_embodiment_image_unexpected_error(self):
        """Test embodiment image generation with unexpected error."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.generate_image.side_effect = Exception("Unexpected error")
        service = ImageService(provider=mock_provider)

        with pytest.raises(ImageProviderError) as exc_info:
            service.generate_embodiment_image(prompt="Test prompt")

        assert "Unexpected error" in str(exc_info.value)

    def test_generate_avatar_variations_success(self):
        """Test successful avatar variations generation."""
        mock_provider = MockImageProvider()
        service = ImageService(provider=mock_provider)
        user_id = uuid4()

        variations = ["smiling", "professional", "casual"]
        results = service.generate_avatar_variations(
            base_prompt="A teacher avatar", variations=variations, user_id=user_id
        )

        assert len(results) == 3
        for result in results:
            assert result.image_path is not None
            assert result.model_used == "mock-stable-diffusion"

        # Check performance metrics
        metrics = service.get_performance_metrics()
        assert metrics["total_generations"] == 3
        assert metrics["failed_generations"] == 0

    def test_generate_avatar_variations_provider_error(self):
        """Test avatar variations generation with provider error."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.generate_avatar_variations.side_effect = ImageGenerationError(
            "Generation failed"
        )
        service = ImageService(provider=mock_provider)

        with pytest.raises(ImageGenerationError):
            service.generate_avatar_variations("Base prompt", ["variation1"])

        # Check that failure was recorded
        metrics = service.get_performance_metrics()
        assert metrics["failed_generations"] == 1

    def test_create_embodiment_prompt_basic(self):
        """Test creating embodiment prompt from basic PALD data."""
        service = ImageService(provider=MockImageProvider())

        pald_data = {
            "appearance": {"gender": "female", "age_range": "young adult", "style": "modern"},
            "personality": {"approachability": "high", "formality": "casual"},
        }

        prompt = service.create_embodiment_prompt(pald_data)

        assert "friendly educational assistant avatar" in prompt
        assert "female appearance" in prompt
        assert "young adult looking" in prompt
        assert "modern style" in prompt
        assert "warm and approachable expression" in prompt
        assert "casual and relaxed pose" in prompt
        assert "high quality" in prompt

    def test_create_embodiment_prompt_with_context(self):
        """Test creating embodiment prompt with learning context."""
        service = ImageService(provider=MockImageProvider())

        pald_data = {"context": {"subject_area": "science"}, "personality": {"formality": "formal"}}

        prompt = service.create_embodiment_prompt(pald_data)

        assert "intelligent and analytical look" in prompt
        assert "professional and composed" in prompt

    def test_create_embodiment_prompt_arts_context(self):
        """Test creating embodiment prompt for arts context."""
        service = ImageService(provider=MockImageProvider())

        pald_data = {"context": {"subject_area": "arts"}}

        prompt = service.create_embodiment_prompt(pald_data)

        assert "creative and expressive demeanor" in prompt

    def test_create_embodiment_prompt_empty_data(self):
        """Test creating embodiment prompt with empty PALD data."""
        service = ImageService(provider=MockImageProvider())

        prompt = service.create_embodiment_prompt({})

        # Should still create a valid prompt with defaults
        assert "friendly educational assistant avatar" in prompt
        assert "high quality" in prompt

    def test_health_check_success(self):
        """Test successful health check."""
        mock_provider = MockImageProvider()
        service = ImageService(provider=mock_provider)

        is_healthy = service.health_check()

        assert is_healthy is True
        assert service._health_status is True

    def test_health_check_failure(self):
        """Test failed health check."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.health_check.return_value = False
        service = ImageService(provider=mock_provider)

        is_healthy = service.health_check()

        assert is_healthy is False
        assert service._health_status is False

    def test_health_check_exception(self):
        """Test health check with exception."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.health_check.side_effect = Exception("Health check failed")
        service = ImageService(provider=mock_provider)

        is_healthy = service.health_check()

        assert is_healthy is False
        assert service._health_status is False

    def test_get_performance_metrics(self):
        """Test getting performance metrics."""
        mock_provider = MockImageProvider(generation_time=1.5)
        service = ImageService(provider=mock_provider)

        # Generate some images to populate metrics
        service.generate_embodiment_image("Test prompt 1")
        service.generate_embodiment_image("Test prompt 2")

        metrics = service.get_performance_metrics()

        assert metrics["total_generations"] == 2
        assert metrics["failed_generations"] == 0
        assert metrics["total_generation_time"] == 3.0
        assert metrics["average_generation_time"] == 1.5

    def test_get_performance_metrics_with_failures(self):
        """Test performance metrics with some failures."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.generate_image.side_effect = [
            ImageResult(image_path="test1.png", generation_time=2.0),
            ImageGenerationError("Failed"),
            ImageResult(image_path="test2.png", generation_time=3.0),
        ]
        service = ImageService(provider=mock_provider)

        # First generation succeeds
        service.generate_embodiment_image("Test 1")

        # Second generation fails
        with contextlib.suppress(ImageGenerationError):
            service.generate_embodiment_image("Test 2")

        # Third generation succeeds
        service.generate_embodiment_image("Test 3")

        metrics = service.get_performance_metrics()
        assert metrics["total_generations"] == 3
        assert metrics["failed_generations"] == 1
        assert metrics["total_generation_time"] == 5.0
        assert metrics["average_generation_time"] == 2.5  # (2.0 + 3.0) / 2

    def test_get_service_status_healthy(self):
        """Test getting service status when healthy."""
        mock_provider = MockImageProvider()
        service = ImageService(provider=mock_provider)

        status = service.get_service_status()

        assert status["healthy"] is True
        assert status["provider_type"] == "MockImageProvider"
        assert "model_info" in status
        assert "performance_metrics" in status

    def test_get_service_status_unhealthy(self):
        """Test getting service status when unhealthy."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.health_check.return_value = False
        mock_provider.get_model_info.return_value = {"model": "test"}
        service = ImageService(provider=mock_provider)

        status = service.get_service_status()

        assert status["healthy"] is False
        assert status["provider_type"] == "Mock"

    def test_get_service_status_exception(self):
        """Test getting service status with exception."""
        mock_provider = Mock(spec=Text2ImageProvider)
        mock_provider.health_check.side_effect = Exception("Status error")
        mock_provider.get_model_info.side_effect = Exception("Model info error")
        service = ImageService(provider=mock_provider)

        status = service.get_service_status()

        assert status["healthy"] is False
        assert "error" in status
        # The error message could be from either health_check or get_model_info
        assert (
            "error" in status["error"]
            or "Status error" in status["error"]
            or "Model info error" in status["error"]
        )

    def test_is_service_available_cached(self):
        """Test service availability check with cached status."""
        service = ImageService(provider=MockImageProvider())
        service._health_status = True

        assert service.is_service_available() is True

    def test_is_service_available_check_required(self):
        """Test service availability check requiring health check."""
        mock_provider = MockImageProvider()
        service = ImageService(provider=mock_provider)

        assert service.is_service_available() is True
        assert service._health_status is True


class TestImageServiceGlobalFunctions:
    """Test global image service functions."""

    def test_get_image_service_singleton(self):
        """Test that get_image_service returns singleton."""
        service1 = get_image_service()
        service2 = get_image_service()

        assert service1 is service2

    def test_set_image_service(self):
        """Test setting custom image service."""
        custom_service = ImageService(provider=MockImageProvider())
        set_image_service(custom_service)

        retrieved_service = get_image_service()
        assert retrieved_service is custom_service

        # Reset to None for other tests
        set_image_service(None)

    def test_convenience_functions(self):
        """Test convenience functions."""
        # Set up mock service
        mock_provider = MockImageProvider()
        custom_service = ImageService(provider=mock_provider)
        set_image_service(custom_service)

        # Test convenience functions
        from src.services.image_service import (
            create_embodiment_prompt,
            generate_avatar_variations,
            generate_embodiment_image,
            get_service_status,
            health_check,
        )

        # Test generate_embodiment_image
        result = generate_embodiment_image("Test prompt")
        assert result.image_path is not None

        # Test generate_avatar_variations
        variations = generate_avatar_variations("Base", ["var1", "var2"])
        assert len(variations) == 2

        # Test create_embodiment_prompt
        prompt = create_embodiment_prompt({"test": "data"})
        assert isinstance(prompt, str)

        # Test health_check
        is_healthy = health_check()
        assert is_healthy is True

        # Test get_service_status
        status = get_service_status()
        assert "healthy" in status

        # Reset
        set_image_service(None)


@pytest.fixture
def temp_image_dir():
    """Create temporary directory for image tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_pald_data():
    """Sample PALD data for testing."""
    return {
        "appearance": {"gender": "neutral", "age_range": "adult", "style": "professional"},
        "personality": {"approachability": "high", "formality": "moderate"},
        "context": {"subject_area": "mathematics", "formality_level": "formal"},
    }


@pytest.fixture
def sample_image_request():
    """Sample image request for testing."""
    return ImageRequest(
        prompt="A friendly educational assistant",
        width=512,
        height=512,
        num_inference_steps=20,
        guidance_scale=7.5,
    )
