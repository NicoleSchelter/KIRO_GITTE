"""
Image generation provider interfaces and implementations for GITTE system.
Provides abstraction layer for different image generation services with Stable Diffusion implementation.
"""

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import torch
from PIL import Image

try:
    from diffusers import DPMSolverMultistepScheduler, StableDiffusionPipeline

    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False
    StableDiffusionPipeline = None
    DPMSolverMultistepScheduler = None

from config.config import config
from src.utils.circuit_breaker import CircuitBreakerConfig, circuit_breaker
from src.utils.error_handler import handle_errors

logger = logging.getLogger(__name__)


@dataclass
class ImageResult:
    """Result from image generation."""

    image_path: str
    image_data: Image.Image | None = None
    generation_time: float | None = None
    model_used: str | None = None
    parameters: dict[str, Any] | None = None
    request_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid4())


@dataclass
class ImageRequest:
    """Request for image generation."""

    prompt: str
    negative_prompt: str | None = None
    width: int = 512
    height: int = 512
    num_inference_steps: int = 20
    guidance_scale: float = 7.5
    seed: int | None = None
    num_images: int = 1
    request_id: str | None = None

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid4())


# Import exception classes from centralized exceptions module
from src.exceptions import ImageGenerationError, ImageProviderError


class ModelLoadError(ImageProviderError):
    """Model loading error."""

    pass


class Text2ImageProvider(ABC):
    """Abstract base class for text-to-image providers."""

    @abstractmethod
    def generate_image(self, request: ImageRequest) -> ImageResult:
        """
        Generate an image from text prompt.

        Args:
            request: Image generation request

        Returns:
            ImageResult: Generated image result

        Raises:
            ImageProviderError: If generation fails
        """
        pass

    @abstractmethod
    def generate_avatar_variations(
        self, base_prompt: str, variations: list[str]
    ) -> list[ImageResult]:
        """
        Generate multiple avatar variations from a base prompt.

        Args:
            base_prompt: Base prompt for avatar generation
            variations: List of variation descriptions

        Returns:
            List[ImageResult]: List of generated variations
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if the image generation service is healthy.

        Returns:
            bool: True if service is healthy
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the current model.

        Returns:
            Dict containing model information
        """
        pass


class StableDiffusionProvider(Text2ImageProvider):
    """Stable Diffusion image provider implementation using Diffusers."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        output_dir: str | None = None,
        enable_cpu_fallback: bool = True,
    ):
        """
        Initialize Stable Diffusion provider.

        Args:
            model_name: Model name (defaults to config)
            device: Device to use (auto-detected if None)
            output_dir: Output directory for images
            enable_cpu_fallback: Whether to fallback to CPU if GPU fails
        """
        if not DIFFUSERS_AVAILABLE:
            raise ModelLoadError(
                "Diffusers library not available. Install with: pip install diffusers transformers accelerate"
            )

        self.model_name = model_name or getattr(
            config, "sd_model_name", "runwayml/stable-diffusion-v1-5"
        )
        self.enable_cpu_fallback = enable_cpu_fallback
        self.output_dir = Path(
            output_dir or getattr(config, "image_output_dir", "./generated_images")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Device selection
        self.device = self._select_device(device)
        self.pipeline = None
        self._model_loaded = False

        logger.info(
            f"Initialized StableDiffusionProvider with model={self.model_name}, device={self.device}"
        )

    def _select_device(self, preferred_device: str | None = None) -> str:
        """Select the best available device."""
        if preferred_device:
            return preferred_device

        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"

    def _load_model(self) -> None:
        """Load the Stable Diffusion model."""
        if self._model_loaded and self.pipeline is not None:
            return

        try:
            logger.info(f"Loading Stable Diffusion model: {self.model_name}")
            start_time = time.time()

            # Load pipeline
            self.pipeline = StableDiffusionPipeline.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                safety_checker=None,  # Disable safety checker for faster loading
                requires_safety_checker=False,
            )

            # Use DPM solver for faster inference
            self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipeline.scheduler.config
            )

            # Move to device
            self.pipeline = self.pipeline.to(self.device)

            # Enable memory efficient attention if available
            if hasattr(self.pipeline, "enable_attention_slicing"):
                self.pipeline.enable_attention_slicing()

            # Enable CPU offload for CUDA to save memory
            if self.device == "cuda" and hasattr(self.pipeline, "enable_sequential_cpu_offload"):
                self.pipeline.enable_sequential_cpu_offload()

            load_time = time.time() - start_time
            self._model_loaded = True

            logger.info(f"Model loaded successfully in {load_time:.2f}s on device: {self.device}")

        except Exception as e:
            logger.error(f"Failed to load model on {self.device}: {e}")

            # Try CPU fallback if enabled and not already on CPU
            if self.enable_cpu_fallback and self.device != "cpu":
                logger.info("Attempting CPU fallback...")
                self.device = "cpu"
                try:
                    self.pipeline = StableDiffusionPipeline.from_pretrained(
                        self.model_name,
                        torch_dtype=torch.float32,
                        safety_checker=None,
                        requires_safety_checker=False,
                    )
                    self.pipeline = self.pipeline.to(self.device)
                    self._model_loaded = True
                    logger.info("Successfully loaded model on CPU")
                except Exception as cpu_error:
                    logger.error(f"CPU fallback also failed: {cpu_error}")
                    raise ModelLoadError(f"Failed to load model on both {self.device} and CPU: {e}")
            else:
                raise ModelLoadError(f"Failed to load model: {e}")

    @circuit_breaker(
        name="stable_diffusion",
        config=CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=60,
            success_threshold=1,
            timeout=120,
            expected_exceptions=(ImageProviderError, ImageGenerationError, ModelLoadError),
        ),
    )
    @handle_errors(context={"service": "stable_diffusion"})
    def generate_image(self, request: ImageRequest) -> ImageResult:
        """Generate image from text prompt using Stable Diffusion."""
        start_time = time.time()

        try:
            # Ensure model is loaded
            self._load_model()

            if not self._model_loaded or self.pipeline is None:
                raise ImageGenerationError("Model not loaded")

            logger.debug(
                f"Generating image: prompt='{request.prompt[:50]}...', size={request.width}x{request.height}"
            )

            # Set seed for reproducibility
            if request.seed is not None:
                torch.manual_seed(request.seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(request.seed)

            # Generate image
            with torch.inference_mode():
                result = self.pipeline(
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    width=request.width,
                    height=request.height,
                    num_inference_steps=request.num_inference_steps,
                    guidance_scale=request.guidance_scale,
                    num_images_per_prompt=request.num_images,
                )

            # Get the first image
            image = result.images[0]

            # Generate filename
            prompt_hash = hashlib.md5(request.prompt.encode(), usedforsecurity=False).hexdigest()[:8]
            timestamp = int(time.time())
            filename = f"embodiment_{timestamp}_{prompt_hash}.png"
            image_path = self.output_dir / filename

            # Save image
            image.save(image_path, format="PNG")

            generation_time = time.time() - start_time

            # Create result
            image_result = ImageResult(
                image_path=str(image_path),
                image_data=image,
                generation_time=generation_time,
                model_used=self.model_name,
                parameters={
                    "prompt": request.prompt,
                    "negative_prompt": request.negative_prompt,
                    "width": request.width,
                    "height": request.height,
                    "num_inference_steps": request.num_inference_steps,
                    "guidance_scale": request.guidance_scale,
                    "seed": request.seed,
                },
                request_id=request.request_id,
                metadata={
                    "device": self.device,
                    "model_name": self.model_name,
                    "file_size": image_path.stat().st_size,
                    "generation_timestamp": timestamp,
                },
            )

            logger.info(f"Image generated successfully: {filename}, time={generation_time:.2f}s")
            return image_result

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"Image generation failed after {generation_time:.2f}s: {e}")
            raise ImageGenerationError(f"Failed to generate image: {e}")

    def generate_avatar_variations(
        self, base_prompt: str, variations: list[str]
    ) -> list[ImageResult]:
        """Generate multiple avatar variations from a base prompt."""
        results = []

        for i, variation in enumerate(variations):
            try:
                # Combine base prompt with variation
                combined_prompt = f"{base_prompt}, {variation}"

                request = ImageRequest(
                    prompt=combined_prompt,
                    negative_prompt="blurry, low quality, distorted, deformed",
                    width=512,
                    height=512,
                    num_inference_steps=20,
                    guidance_scale=7.5,
                    seed=42 + i,  # Different seed for each variation
                )

                result = self.generate_image(request)
                results.append(result)

                logger.debug(f"Generated variation {i+1}/{len(variations)}: {variation}")

            except Exception as e:
                logger.error(f"Failed to generate variation '{variation}': {e}")
                # Continue with other variations
                continue

        logger.info(f"Generated {len(results)}/{len(variations)} avatar variations")
        return results

    def health_check(self) -> bool:
        """Check if the image generation service is healthy."""
        try:
            # Try to load model if not already loaded
            if not self._model_loaded:
                self._load_model()

            return self._model_loaded and self.pipeline is not None

        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model."""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "model_loaded": self._model_loaded,
            "output_directory": str(self.output_dir),
            "cpu_fallback_enabled": self.enable_cpu_fallback,
            "torch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        }


class MockImageProvider(Text2ImageProvider):
    """Mock image provider for testing."""

    def __init__(self, output_dir: str | None = None, generation_time: float = 1.0):
        """
        Initialize mock provider.

        Args:
            output_dir: Output directory for mock images
            generation_time: Simulated generation time
        """
        self.output_dir = Path(output_dir or "./mock_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.generation_time = generation_time
        self.call_count = 0

    def generate_image(self, request: ImageRequest) -> ImageResult:
        """Generate mock image."""
        self.call_count += 1

        # Simulate generation time
        time.sleep(self.generation_time)

        # Create a simple colored image
        image = Image.new("RGB", (request.width, request.height), color=(100, 150, 200))

        # Generate filename
        timestamp = int(time.time())
        filename = f"mock_embodiment_{timestamp}_{self.call_count}.png"
        image_path = self.output_dir / filename

        # Save mock image
        image.save(image_path, format="PNG")

        return ImageResult(
            image_path=str(image_path),
            image_data=image,
            generation_time=self.generation_time,
            model_used="mock-stable-diffusion",
            parameters={"prompt": request.prompt, "width": request.width, "height": request.height},
            request_id=request.request_id,
            metadata={
                "mock": True,
                "call_count": self.call_count,
                "generation_timestamp": timestamp,
            },
        )

    def generate_avatar_variations(
        self, base_prompt: str, variations: list[str]
    ) -> list[ImageResult]:
        """Generate mock avatar variations."""
        results = []

        for i, variation in enumerate(variations):
            request = ImageRequest(prompt=f"{base_prompt}, {variation}", seed=42 + i)
            result = self.generate_image(request)
            results.append(result)

        return results

    def health_check(self) -> bool:
        """Mock health check."""
        return True

    def get_model_info(self) -> dict[str, Any]:
        """Get mock model info."""
        return {
            "model_name": "mock-stable-diffusion",
            "device": "mock",
            "model_loaded": True,
            "output_directory": str(self.output_dir),
            "mock": True,
            "call_count": self.call_count,
        }


class DummyImageProvider(Text2ImageProvider):
    """Dummy image provider that creates placeholder images without any ML models."""

    def __init__(self, output_dir: str | None = None):
        """Initialize dummy provider."""
        self.output_dir = Path(output_dir or "./dummy_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.call_count = 0

    def generate_image(self, request: ImageRequest) -> ImageResult:
        """Generate dummy placeholder image."""
        self.call_count += 1

        # Create a simple placeholder image with text
        image = Image.new("RGB", (request.width, request.height), color=(200, 200, 200))

        # Generate filename
        timestamp = int(time.time())
        filename = f"dummy_embodiment_{timestamp}_{self.call_count}.png"
        image_path = self.output_dir / filename

        # Save dummy image
        image.save(image_path, format="PNG")

        return ImageResult(
            image_path=str(image_path),
            image_data=image,
            generation_time=0.1,  # Very fast dummy generation
            model_used="dummy-provider",
            parameters={"prompt": request.prompt, "width": request.width, "height": request.height},
            request_id=request.request_id,
            metadata={
                "dummy": True,
                "call_count": self.call_count,
                "generation_timestamp": timestamp,
            },
        )

    def generate_avatar_variations(
        self, base_prompt: str, variations: list[str]
    ) -> list[ImageResult]:
        """Generate dummy avatar variations."""
        results = []

        for variation in variations:
            request = ImageRequest(prompt=f"{base_prompt}, {variation}")
            result = self.generate_image(request)
            results.append(result)

        return results

    def health_check(self) -> bool:
        """Dummy health check."""
        return True

    def get_model_info(self) -> dict[str, Any]:
        """Get dummy model info."""
        return {
            "model_name": "dummy-provider",
            "device": "none",
            "model_loaded": True,
            "output_directory": str(self.output_dir),
            "dummy": True,
            "call_count": self.call_count,
        }
