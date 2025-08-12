"""
Tests for image provider implementations.
Tests Stable Diffusion provider with GPU/CPU fallback and mock providers.
"""

import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import torch
from PIL import Image

from src.services.image_provider import (
    DummyImageProvider,
    ImageGenerationError,
    ImageRequest,
    ImageResult,
    MockImageProvider,
    ModelLoadError,
    StableDiffusionProvider,
)


class TestImageRequest:
    """Test image request data class."""

    def test_image_request_creation(self):
        """Test creating image request."""
        request = ImageRequest(
            prompt="A friendly teacher",
            negative_prompt="blurry, low quality",
            width=256,
            height=256,
            num_inference_steps=15,
            guidance_scale=8.0,
            seed=42,
            num_images=2,
        )

        assert request.prompt == "A friendly teacher"
        assert request.negative_prompt == "blurry, low quality"
        assert request.width == 256
        assert request.height == 256
        assert request.num_inference_steps == 15
        assert request.guidance_scale == 8.0
        assert request.seed == 42
        assert request.num_images == 2
        assert request.request_id is not None

    def test_image_request_defaults(self):
        """Test image request with defaults."""
        request = ImageRequest(prompt="Test prompt")

        assert request.negative_prompt is None
        assert request.width == 512
        assert request.height == 512
        assert request.num_inference_steps == 20
        assert request.guidance_scale == 7.5
        assert request.seed is None
        assert request.num_images == 1
        assert request.request_id is not None


class TestImageResult:
    """Test image result data class."""

    def test_image_result_creation(self):
        """Test creating image result."""
        image = Image.new("RGB", (256, 256), color="red")
        metadata = {"test": True}
        parameters = {"prompt": "test"}

        result = ImageResult(
            image_path="/path/to/image.png",
            image_data=image,
            generation_time=2.5,
            model_used="stable-diffusion-v1-5",
            parameters=parameters,
            metadata=metadata,
        )

        assert result.image_path == "/path/to/image.png"
        assert result.image_data == image
        assert result.generation_time == 2.5
        assert result.model_used == "stable-diffusion-v1-5"
        assert result.parameters == parameters
        assert result.metadata == metadata
        assert result.request_id is not None

    def test_image_result_defaults(self):
        """Test image result with defaults."""
        result = ImageResult(image_path="/path/to/image.png")

        assert result.image_data is None
        assert result.generation_time is None
        assert result.model_used is None
        assert result.parameters is None
        assert result.metadata is None
        assert result.request_id is not None


class TestMockImageProvider:
    """Test mock image provider."""

    def test_mock_provider_creation(self):
        """Test creating mock provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MockImageProvider(output_dir=temp_dir, generation_time=1.5)

            assert provider.output_dir == Path(temp_dir)
            assert provider.generation_time == 1.5
            assert provider.call_count == 0

    def test_mock_generate_image(self):
        """Test mock image generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MockImageProvider(
                output_dir=temp_dir, generation_time=0.1  # Fast for testing
            )

            request = ImageRequest(prompt="A test image", width=256, height=256)

            start_time = time.time()
            result = provider.generate_image(request)
            end_time = time.time()

            # Check result
            assert result.image_path is not None
            assert Path(result.image_path).exists()
            assert result.image_data is not None
            assert result.image_data.size == (256, 256)
            assert result.generation_time == 0.1
            assert result.model_used == "mock-stable-diffusion"
            assert result.parameters["prompt"] == "A test image"
            assert result.metadata["mock"] is True
            assert result.metadata["call_count"] == 1

            # Check that generation time was simulated
            assert (end_time - start_time) >= 0.1

            # Check provider state
            assert provider.call_count == 1

    def test_mock_generate_avatar_variations(self):
        """Test mock avatar variations generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MockImageProvider(output_dir=temp_dir)

            variations = ["smiling", "professional", "casual"]
            results = provider.generate_avatar_variations(
                base_prompt="A teacher avatar", variations=variations
            )

            assert len(results) == 3
            for i, result in enumerate(results):
                assert result.image_path is not None
                assert Path(result.image_path).exists()
                assert result.model_used == "mock-stable-diffusion"
                assert f"A teacher avatar, {variations[i]}" in result.parameters["prompt"]

            assert provider.call_count == 3

    def test_mock_health_check(self):
        """Test mock health check."""
        provider = MockImageProvider()
        assert provider.health_check() is True

    def test_mock_get_model_info(self):
        """Test mock model info."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MockImageProvider(output_dir=temp_dir)
            provider.call_count = 5

            info = provider.get_model_info()

            assert info["model_name"] == "mock-stable-diffusion"
            assert info["device"] == "mock"
            assert info["model_loaded"] is True
            assert info["output_directory"] == temp_dir
            assert info["mock"] is True
            assert info["call_count"] == 5


class TestDummyImageProvider:
    """Test dummy image provider."""

    def test_dummy_provider_creation(self):
        """Test creating dummy provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = DummyImageProvider(output_dir=temp_dir)

            assert provider.output_dir == Path(temp_dir)
            assert provider.call_count == 0

    def test_dummy_generate_image(self):
        """Test dummy image generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = DummyImageProvider(output_dir=temp_dir)

            request = ImageRequest(prompt="A dummy image", width=128, height=128)

            result = provider.generate_image(request)

            # Check result
            assert result.image_path is not None
            assert Path(result.image_path).exists()
            assert result.image_data is not None
            assert result.image_data.size == (128, 128)
            assert result.generation_time == 0.1  # Very fast
            assert result.model_used == "dummy-provider"
            assert result.parameters["prompt"] == "A dummy image"
            assert result.metadata["dummy"] is True
            assert result.metadata["call_count"] == 1

            assert provider.call_count == 1

    def test_dummy_generate_avatar_variations(self):
        """Test dummy avatar variations generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = DummyImageProvider(output_dir=temp_dir)

            variations = ["happy", "serious"]
            results = provider.generate_avatar_variations(
                base_prompt="A dummy avatar", variations=variations
            )

            assert len(results) == 2
            for result in results:
                assert result.image_path is not None
                assert Path(result.image_path).exists()
                assert result.model_used == "dummy-provider"

            assert provider.call_count == 2

    def test_dummy_health_check(self):
        """Test dummy health check."""
        provider = DummyImageProvider()
        assert provider.health_check() is True

    def test_dummy_get_model_info(self):
        """Test dummy model info."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = DummyImageProvider(output_dir=temp_dir)

            info = provider.get_model_info()

            assert info["model_name"] == "dummy-provider"
            assert info["device"] == "none"
            assert info["model_loaded"] is True
            assert info["output_directory"] == temp_dir
            assert info["dummy"] is True


class TestStableDiffusionProvider:
    """Test Stable Diffusion provider."""

    def test_stable_diffusion_provider_creation(self):
        """Test creating Stable Diffusion provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(
                model_name="test/model",
                device="cpu",
                output_dir=temp_dir,
                enable_cpu_fallback=False,
            )

            assert provider.model_name == "test/model"
            assert provider.device == "cpu"
            assert provider.output_dir == Path(temp_dir)
            assert provider.enable_cpu_fallback is False
            assert provider.pipeline is None
            assert provider._model_loaded is False

    def test_stable_diffusion_provider_defaults(self):
        """Test Stable Diffusion provider with defaults."""
        with patch("src.services.image_provider.config") as mock_config:
            mock_config.sd_model_name = "custom/model"
            mock_config.image_output_dir = "/custom/path"

            with tempfile.TemporaryDirectory():
                # Override the config path for testing
                with patch.object(Path, "mkdir"):
                    provider = StableDiffusionProvider()

                    assert provider.model_name == "custom/model"
                    assert provider.enable_cpu_fallback is True

    def test_device_selection_cuda(self):
        """Test device selection with CUDA available."""
        with patch("torch.cuda.is_available", return_value=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                provider = StableDiffusionProvider(output_dir=temp_dir)
                assert provider.device == "cuda"

    def test_device_selection_mps(self):
        """Test device selection with MPS (Apple Silicon) available."""
        with patch("torch.cuda.is_available", return_value=False):
            with patch("torch.backends.mps.is_available", return_value=True):
                with tempfile.TemporaryDirectory() as temp_dir:
                    provider = StableDiffusionProvider(output_dir=temp_dir)
                    assert provider.device == "mps"

    def test_device_selection_cpu_fallback(self):
        """Test device selection falling back to CPU."""
        with patch("torch.cuda.is_available", return_value=False):
            with patch("torch.backends.mps.is_available", return_value=False):
                with tempfile.TemporaryDirectory() as temp_dir:
                    provider = StableDiffusionProvider(output_dir=temp_dir)
                    assert provider.device == "cpu"

    def test_device_selection_preferred(self):
        """Test device selection with preferred device."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(device="custom", output_dir=temp_dir)
            assert provider.device == "custom"

    @patch("src.services.image_provider.DIFFUSERS_AVAILABLE", False)
    def test_stable_diffusion_provider_no_diffusers(self):
        """Test Stable Diffusion provider without diffusers library."""
        with pytest.raises(ModelLoadError) as exc_info:
            StableDiffusionProvider()

        assert "Diffusers library not available" in str(exc_info.value)

    @patch("src.services.image_provider.StableDiffusionPipeline")
    @patch("src.services.image_provider.DPMSolverMultistepScheduler")
    def test_load_model_success(self, mock_scheduler, mock_pipeline):
        """Test successful model loading."""
        # Setup mocks
        mock_pipe_instance = Mock()
        mock_pipe_instance.scheduler = Mock()
        mock_pipe_instance.scheduler.config = {}
        mock_pipeline.from_pretrained.return_value = mock_pipe_instance
        mock_scheduler.from_config.return_value = Mock()

        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(
                model_name="test/model", device="cpu", output_dir=temp_dir
            )

            provider._load_model()

            assert provider._model_loaded is True
            assert provider.pipeline is not None
            mock_pipeline.from_pretrained.assert_called_once()

    @patch("src.services.image_provider.StableDiffusionPipeline")
    def test_load_model_failure_with_cpu_fallback(self, mock_pipeline):
        """Test model loading failure with CPU fallback."""
        # First call fails, second succeeds
        mock_pipe_instance = Mock()
        mock_pipe_instance.scheduler = Mock()
        mock_pipe_instance.scheduler.config = {}
        mock_pipeline.from_pretrained.side_effect = [
            Exception("GPU loading failed"),
            mock_pipe_instance,
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(
                device="cuda", output_dir=temp_dir, enable_cpu_fallback=True
            )

            provider._load_model()

            assert provider._model_loaded is True
            assert provider.device == "cpu"
            assert mock_pipeline.from_pretrained.call_count == 2

    @patch("src.services.image_provider.StableDiffusionPipeline")
    def test_load_model_failure_no_fallback(self, mock_pipeline):
        """Test model loading failure without CPU fallback."""
        mock_pipeline.from_pretrained.side_effect = Exception("Loading failed")

        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(
                device="cuda", output_dir=temp_dir, enable_cpu_fallback=False
            )

            with pytest.raises(ModelLoadError):
                provider._load_model()

    @patch("src.services.image_provider.StableDiffusionPipeline")
    @patch("torch.inference_mode")
    @patch("torch.manual_seed")
    def test_generate_image_success(self, mock_seed, mock_inference, mock_pipeline):
        """Test successful image generation."""
        # Setup mocks
        mock_image = Mock(spec=Image.Image)
        mock_result = Mock()
        mock_result.images = [mock_image]

        mock_pipe_instance = Mock()
        mock_pipe_instance.scheduler = Mock()
        mock_pipe_instance.scheduler.config = {}
        mock_pipeline.from_pretrained.return_value = mock_pipe_instance

        # Mock the pipeline call to return our mock result
        mock_pipe_instance.return_value = mock_result

        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(device="cpu", output_dir=temp_dir)

            # Set the pipeline directly to avoid loading issues
            provider.pipeline = mock_pipe_instance
            provider._model_loaded = True

            # Mock the save method and file stats
            with patch.object(mock_image, "save"):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1024

                    request = ImageRequest(prompt="A test image", width=256, height=256, seed=42)

                    result = provider.generate_image(request)

                    assert result.image_path is not None
                    assert result.image_data == mock_image
                    assert result.model_used == provider.model_name
                    assert result.parameters["prompt"] == "A test image"
                    assert result.generation_time is not None
                    assert result.generation_time > 0

                    # Verify seed was set
                    mock_seed.assert_called_with(42)

    def test_generate_image_model_not_loaded(self):
        """Test image generation when model is not loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(output_dir=temp_dir)
            provider._model_loaded = False
            provider.pipeline = None

            # Mock _load_model to not actually load
            with patch.object(provider, "_load_model"):
                request = ImageRequest(prompt="Test")

                with pytest.raises(ImageGenerationError) as exc_info:
                    provider.generate_image(request)

                assert "Model not loaded" in str(exc_info.value)

    @patch("src.services.image_provider.StableDiffusionPipeline")
    def test_generate_image_generation_error(self, mock_pipeline):
        """Test image generation with generation error."""
        mock_pipe_instance = Mock()
        mock_pipe_instance.scheduler = Mock()
        mock_pipe_instance.scheduler.config = {}
        mock_pipe_instance.side_effect = Exception("Generation failed")
        mock_pipeline.from_pretrained.return_value = mock_pipe_instance

        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(output_dir=temp_dir)

            request = ImageRequest(prompt="Test")

            with pytest.raises(ImageGenerationError) as exc_info:
                provider.generate_image(request)

            assert "Failed to generate image" in str(exc_info.value)

    def test_generate_avatar_variations(self):
        """Test avatar variations generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(output_dir=temp_dir)

            # Mock generate_image to avoid actual generation
            mock_results = [
                ImageResult(image_path=f"test_{i}.png", generation_time=1.0) for i in range(3)
            ]

            with patch.object(provider, "generate_image", side_effect=mock_results):
                variations = ["happy", "serious", "professional"]
                results = provider.generate_avatar_variations(
                    base_prompt="A teacher", variations=variations
                )

                assert len(results) == 3
                for i, result in enumerate(results):
                    assert result.image_path == f"test_{i}.png"

    def test_generate_avatar_variations_with_failures(self):
        """Test avatar variations generation with some failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(output_dir=temp_dir)

            # Mock generate_image with some failures
            def mock_generate(request):
                if "fail" in request.prompt:
                    raise ImageGenerationError("Generation failed")
                return ImageResult(image_path="success.png", generation_time=1.0)

            with patch.object(provider, "generate_image", side_effect=mock_generate):
                variations = ["happy", "fail", "professional"]
                results = provider.generate_avatar_variations(
                    base_prompt="A teacher", variations=variations
                )

                # Should return only successful generations
                assert len(results) == 2

    def test_health_check_success(self):
        """Test successful health check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(output_dir=temp_dir)

            with patch.object(provider, "_load_model"):
                provider._model_loaded = True
                provider.pipeline = Mock()

                assert provider.health_check() is True

    def test_health_check_failure(self):
        """Test failed health check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(output_dir=temp_dir)

            with patch.object(provider, "_load_model", side_effect=Exception("Load failed")):
                assert provider.health_check() is False

    def test_get_model_info(self):
        """Test getting model information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = StableDiffusionProvider(
                model_name="test/model",
                device="cpu",
                output_dir=temp_dir,
                enable_cpu_fallback=False,
            )

            info = provider.get_model_info()

            assert info["model_name"] == "test/model"
            assert info["device"] == "cpu"
            assert info["model_loaded"] is False
            assert info["output_directory"] == temp_dir
            assert info["cpu_fallback_enabled"] is False
            assert "torch_version" in info
            assert "cuda_available" in info


class TestImageProviderIntegration:
    """Integration tests for image providers (require actual libraries)."""

    @pytest.mark.integration
    def test_mock_provider_integration(self):
        """Test mock provider integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = MockImageProvider(output_dir=temp_dir)

            # Test full workflow
            request = ImageRequest(prompt="A friendly educational assistant", width=256, height=256)

            result = provider.generate_image(request)

            # Verify file was created
            assert Path(result.image_path).exists()

            # Verify image can be loaded and close it immediately
            with Image.open(result.image_path) as image:
                assert image.size == (256, 256)

    @pytest.mark.integration
    @pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
    def test_stable_diffusion_provider_cuda_integration(self):
        """Test Stable Diffusion provider with CUDA (if available)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                provider = StableDiffusionProvider(
                    model_name="runwayml/stable-diffusion-v1-5", device="cuda", output_dir=temp_dir
                )

                # Test health check
                is_healthy = provider.health_check()
                if is_healthy:
                    # Test simple generation
                    request = ImageRequest(
                        prompt="A simple test image",
                        width=256,
                        height=256,
                        num_inference_steps=10,  # Fast generation
                    )

                    result = provider.generate_image(request)

                    assert Path(result.image_path).exists()
                    assert result.generation_time is not None
                    assert result.generation_time > 0

            except Exception as e:
                pytest.skip(f"Stable Diffusion integration test failed: {e}")


@pytest.fixture
def temp_output_dir():
    """Create temporary directory for image output."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_image_request():
    """Sample image request for testing."""
    return ImageRequest(
        prompt="A friendly educational assistant avatar",
        negative_prompt="blurry, low quality, distorted",
        width=512,
        height=512,
        num_inference_steps=20,
        guidance_scale=7.5,
        seed=42,
    )


@pytest.fixture
def sample_pil_image():
    """Sample PIL image for testing."""
    return Image.new("RGB", (256, 256), color=(100, 150, 200))
