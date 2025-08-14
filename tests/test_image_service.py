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


class TestImageServiceIntegration:
    """Test image service integration with isolation and quality detection."""

    def test_image_service_with_isolation_enabled(self):
        """Test image service with isolation service enabled."""
        with patch("src.services.image_service.config") as mock_config:
            # Mock config to enable isolation
            mock_config.feature_flags.enable_image_isolation = True
            mock_config.feature_flags.enable_image_quality_detection = True
            mock_config.image_isolation.enabled = True
            mock_config.image_isolation.detection_confidence_threshold = 0.7
            mock_config.image_isolation.background_removal_method = "rembg"
            mock_config.image_isolation.fallback_to_original = True
            mock_config.image_isolation.max_processing_time = 10
            mock_config.image_isolation.output_format = "PNG"
            mock_config.image_isolation.uniform_background_color = (255, 255, 255)
            mock_config.image_isolation.edge_refinement_enabled = True

            # Mock the isolation service creation
            with patch("src.services.image_service.ImageIsolationService") as mock_isolation_class:
                with patch("src.services.image_service.ImageQualityDetector") as mock_detector_class:
                    mock_isolation = Mock()
                    mock_detector = Mock()
                    mock_isolation_class.return_value = mock_isolation
                    mock_detector_class.return_value = mock_detector

                    service = ImageService(provider=MockImageProvider())

                    assert service.isolation_service is mock_isolation
                    assert service.quality_detector is mock_detector

    def test_image_service_with_isolation_disabled(self):
        """Test image service with isolation service disabled."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = False
            mock_config.feature_flags.enable_image_quality_detection = False

            service = ImageService(provider=MockImageProvider())

            assert service.isolation_service is None
            assert service.quality_detector is None

    def test_generate_embodiment_image_with_processing_pipeline(self):
        """Test image generation with full processing pipeline."""
        mock_provider = MockImageProvider()
        
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = True
            mock_config.feature_flags.enable_image_quality_detection = True
            mock_config.image_isolation.enabled = True

            with patch("src.services.image_service.ImageIsolationService") as mock_isolation_class:
                with patch("src.services.image_service.ImageQualityDetector") as mock_detector_class:
                    # Set up mocks
                    mock_isolation = Mock()
                    mock_detector = Mock()
                    mock_isolation_class.return_value = mock_isolation
                    mock_detector_class.return_value = mock_detector

                    # Mock quality detection - image passes
                    from src.services.image_quality_detector import DetectionResult
                    mock_detector.detect_faulty_image.return_value = DetectionResult(
                        is_faulty=False,
                        reasons=[],
                        confidence_score=0.9,
                        quality_metrics={},
                        person_count=1,
                        processing_time=0.1,
                        recommendations=[]
                    )

                    # Mock isolation - successful
                    from src.services.image_isolation_service import IsolationResult
                    mock_isolation.isolate_person.return_value = IsolationResult(
                        success=True,
                        isolated_image_path="/path/to/isolated.png",
                        original_image_path="/path/to/original.png",
                        confidence_score=0.8,
                        processing_time=0.5,
                        method_used="rembg"
                    )

                    service = ImageService(provider=mock_provider)
                    result = service.generate_embodiment_image("Test prompt")

                    # Should return isolated image
                    assert result.image_path == "/path/to/isolated.png"
                    assert result.metadata is not None
                    assert "isolation" in result.metadata
                    assert result.metadata["isolation"]["success"] is True

                    # Check that both services were called
                    mock_detector.detect_faulty_image.assert_called_once()
                    mock_isolation.isolate_person.assert_called_once()

    def test_generate_embodiment_image_with_faulty_detection(self):
        """Test image generation when quality detection finds issues."""
        mock_provider = MockImageProvider()
        
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = True
            mock_config.feature_flags.enable_image_quality_detection = True

            with patch("src.services.image_service.ImageIsolationService") as mock_isolation_class:
                with patch("src.services.image_service.ImageQualityDetector") as mock_detector_class:
                    mock_isolation = Mock()
                    mock_detector = Mock()
                    mock_isolation_class.return_value = mock_isolation
                    mock_detector_class.return_value = mock_detector

                    # Mock quality detection - image is faulty
                    from src.services.image_quality_detector import DetectionResult, FaultyImageReason
                    mock_detector.detect_faulty_image.return_value = DetectionResult(
                        is_faulty=True,
                        reasons=[FaultyImageReason.NO_PERSON_DETECTED],
                        confidence_score=0.2,
                        quality_metrics={},
                        person_count=0,
                        processing_time=0.1,
                        recommendations=["Adjust prompt to emphasize person generation"]
                    )

                    service = ImageService(provider=mock_provider)
                    result = service.generate_embodiment_image("Test prompt")

                    # Should skip isolation and return original
                    assert result.metadata is not None
                    assert "quality_check" in result.metadata
                    assert result.metadata["quality_check"]["is_faulty"] is True

                    # Isolation should not be called for faulty images
                    mock_isolation.isolate_person.assert_not_called()

    def test_generate_embodiment_image_with_isolation_failure(self):
        """Test image generation when isolation fails."""
        mock_provider = MockImageProvider()
        
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = True
            mock_config.feature_flags.enable_image_quality_detection = True

            with patch("src.services.image_service.ImageIsolationService") as mock_isolation_class:
                with patch("src.services.image_service.ImageQualityDetector") as mock_detector_class:
                    mock_isolation = Mock()
                    mock_detector = Mock()
                    mock_isolation_class.return_value = mock_isolation
                    mock_detector_class.return_value = mock_detector

                    # Mock quality detection - image passes
                    from src.services.image_quality_detector import DetectionResult
                    mock_detector.detect_faulty_image.return_value = DetectionResult(
                        is_faulty=False,
                        reasons=[],
                        confidence_score=0.9,
                        quality_metrics={},
                        person_count=1,
                        processing_time=0.1,
                        recommendations=[]
                    )

                    # Mock isolation - fails
                    from src.services.image_isolation_service import IsolationResult
                    mock_isolation.isolate_person.return_value = IsolationResult(
                        success=False,
                        isolated_image_path=None,
                        original_image_path="/path/to/original.png",
                        confidence_score=0.1,
                        processing_time=0.5,
                        method_used="rembg",
                        error_message="No person detected"
                    )

                    service = ImageService(provider=mock_provider)
                    result = service.generate_embodiment_image("Test prompt")

                    # Should return original image with failure metadata
                    assert result.metadata is not None
                    assert "isolation" in result.metadata
                    assert result.metadata["isolation"]["success"] is False
                    assert result.metadata["isolation"]["fallback_used"] is True

    def test_get_isolation_service_status(self):
        """Test getting isolation service status."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = True

            with patch("src.services.image_service.ImageIsolationService") as mock_isolation_class:
                mock_isolation = Mock()
                mock_isolation.config.background_removal_method = "rembg"
                mock_isolation.config.detection_confidence_threshold = 0.7
                mock_isolation.config.max_processing_time = 10
                mock_isolation.config.fallback_to_original = True
                mock_isolation_class.return_value = mock_isolation

                service = ImageService(provider=MockImageProvider())
                status = service.get_isolation_service_status()

                assert status["enabled"] is True
                assert status["config"]["background_removal_method"] == "rembg"
                assert status["config"]["detection_confidence_threshold"] == 0.7

    def test_get_isolation_service_status_disabled(self):
        """Test getting isolation service status when disabled."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = False

            service = ImageService(provider=MockImageProvider())
            status = service.get_isolation_service_status()

            assert status["enabled"] is False
            assert "reason" in status

    def test_get_quality_detector_status(self):
        """Test getting quality detector status."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_quality_detection = True

            with patch("src.services.image_service.ImageQualityDetector") as mock_detector_class:
                mock_detector = Mock()
                mock_detector.config.min_person_confidence = 0.7
                mock_detector.config.max_people_allowed = 1
                mock_detector.config.min_quality_score = 0.6
                mock_detector.config.blur_threshold = 0.3
                mock_detector.config.noise_threshold = 0.1
                mock_detector_class.return_value = mock_detector

                service = ImageService(provider=MockImageProvider())
                status = service.get_quality_detector_status()

                assert status["enabled"] is True
                assert status["config"]["min_person_confidence"] == 0.7
                assert status["config"]["max_people_allowed"] == 1

    def test_analyze_image_batch_quality(self):
        """Test batch quality analysis."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_quality_detection = True

            with patch("src.services.image_service.ImageQualityDetector") as mock_detector_class:
                mock_detector = Mock()
                
                # Mock batch analysis result
                from src.services.image_quality_detector import BatchProcessingResult, FaultyImageReason
                mock_batch_result = BatchProcessingResult(
                    total_images=5,
                    faulty_images=2,
                    faulty_percentage=40.0,
                    should_regenerate=False,
                    common_issues=[FaultyImageReason.POOR_QUALITY],
                    batch_quality_score=0.7,
                    processing_time=1.5
                )
                mock_detector.analyze_batch_processing.return_value = mock_batch_result
                mock_detector_class.return_value = mock_detector

                service = ImageService(provider=MockImageProvider())
                result = service.analyze_image_batch_quality(["/path/1.jpg", "/path/2.jpg"])

                assert result["total_images"] == 5
                assert result["faulty_images"] == 2
                assert result["faulty_percentage"] == 40.0
                assert result["should_regenerate"] is False
                assert "poor_quality" in result["common_issues"]

    def test_analyze_image_batch_quality_no_detector(self):
        """Test batch quality analysis when detector is not available."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_quality_detection = False

            service = ImageService(provider=MockImageProvider())
            result = service.analyze_image_batch_quality(["/path/1.jpg"])

            assert "error" in result
            assert "not available" in result["error"]

    def test_performance_metrics_include_new_operations(self):
        """Test that performance metrics include isolation and quality operations."""
        mock_provider = MockImageProvider()
        
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = True
            mock_config.feature_flags.enable_image_quality_detection = True

            with patch("src.services.image_service.ImageIsolationService") as mock_isolation_class:
                with patch("src.services.image_service.ImageQualityDetector") as mock_detector_class:
                    mock_isolation = Mock()
                    mock_detector = Mock()
                    mock_isolation_class.return_value = mock_isolation
                    mock_detector_class.return_value = mock_detector

                    # Mock successful operations
                    from src.services.image_quality_detector import DetectionResult
                    from src.services.image_isolation_service import IsolationResult
                    
                    mock_detector.detect_faulty_image.return_value = DetectionResult(
                        is_faulty=False, reasons=[], confidence_score=0.9,
                        quality_metrics={}, person_count=1, processing_time=0.1,
                        recommendations=[]
                    )
                    
                    mock_isolation.isolate_person.return_value = IsolationResult(
                        success=True, isolated_image_path="/isolated.png",
                        original_image_path="/original.png", confidence_score=0.8,
                        processing_time=0.5, method_used="rembg"
                    )

                    service = ImageService(provider=mock_provider)
                    service.generate_embodiment_image("Test prompt")

                    metrics = service.get_performance_metrics()
                    
                    # Check new metrics are present
                    assert "isolation_operations" in metrics
                    assert "isolation_successes" in metrics
                    assert "quality_checks" in metrics
                    assert "faulty_images_detected" in metrics
                    
                    # Check values
                    assert metrics["isolation_operations"] == 1
                    assert metrics["isolation_successes"] == 1
                    assert metrics["quality_checks"] == 1
                    assert metrics["faulty_images_detected"] == 0

    def test_service_status_includes_new_services(self):
        """Test that service status includes isolation and quality detection services."""
        with patch("src.services.image_service.config") as mock_config:
            mock_config.feature_flags.enable_image_isolation = True
            mock_config.feature_flags.enable_image_quality_detection = True

            with patch("src.services.image_service.ImageIsolationService"):
                with patch("src.services.image_service.ImageQualityDetector"):
                    service = ImageService(provider=MockImageProvider())
                    status = service.get_service_status()

                    assert "isolation_service" in status
                    assert "quality_detector" in status
                    assert status["isolation_service"]["enabled"] is True
                    assert status["quality_detector"]["enabled"] is True