"""
Image Service Layer for GITTE system.
Provides high-level image generation operations with configuration management and error handling.
"""

import logging
import time
from typing import Any
from uuid import UUID

from config.config import config
from src.services.image_provider import (
    DummyImageProvider,
    ImageProviderError,
    ImageRequest,
    ImageResult,
    MockImageProvider,
    ModelLoadError,
    StableDiffusionProvider,
    Text2ImageProvider,
)

logger = logging.getLogger(__name__)


class ImageService:
    """
    Service layer for image generation operations.
    Handles provider management, performance monitoring, and high-level operations.
    """

    def __init__(self, provider: Text2ImageProvider | None = None):
        """
        Initialize image service.

        Args:
            provider: Image provider instance (defaults to StableDiffusionProvider)
        """
        self.provider = provider or self._create_default_provider()
        self._performance_metrics = {
            "total_generations": 0,
            "total_generation_time": 0.0,
            "failed_generations": 0,
            "average_generation_time": 0.0,
        }
        self._health_status: bool | None = None

    def _create_default_provider(self) -> Text2ImageProvider:
        """Create default image provider based on configuration."""
        provider_type = getattr(config, "image_provider_type", "stable_diffusion")

        if config.environment == "test":
            return MockImageProvider()
        elif provider_type == "dummy":
            return DummyImageProvider()
        else:
            try:
                return StableDiffusionProvider(
                    model_name=getattr(config, "sd_model_name", "runwayml/stable-diffusion-v1-5"),
                    output_dir=getattr(config, "image_output_dir", "./generated_images"),
                    enable_cpu_fallback=getattr(config, "enable_cpu_fallback", True),
                )
            except ModelLoadError as e:
                logger.warning(f"Failed to initialize StableDiffusionProvider: {e}")
                logger.info("Falling back to DummyImageProvider")
                return DummyImageProvider()

    def generate_embodiment_image(
        self, prompt: str, user_id: UUID | None = None, parameters: dict[str, Any] | None = None
    ) -> ImageResult:
        """
        Generate an embodiment image from text prompt.

        Args:
            prompt: Text prompt for image generation
            user_id: User ID for audit logging
            parameters: Generation parameters (width, height, etc.)

        Returns:
            ImageResult: Generated image result

        Raises:
            ImageProviderError: If generation fails
        """
        start_time = time.time()

        try:
            # Prepare request with defaults
            params = parameters or {}
            request = ImageRequest(
                prompt=prompt,
                negative_prompt=params.get(
                    "negative_prompt", "blurry, low quality, distorted, deformed"
                ),
                width=params.get("width", 512),
                height=params.get("height", 512),
                num_inference_steps=params.get("num_inference_steps", 20),
                guidance_scale=params.get("guidance_scale", 7.5),
                seed=params.get("seed"),
                num_images=params.get("num_images", 1),
            )

            logger.info(
                f"Generating embodiment image: prompt='{prompt[:50]}...', user_id={user_id}"
            )

            # Generate image
            result = self.provider.generate_image(request)

            # Update performance metrics
            self._update_performance_metrics(result.generation_time or 0.0, success=True)

            logger.info(
                f"Embodiment image generated successfully: {result.image_path}, time={result.generation_time:.2f}s"
            )
            return result

        except ImageProviderError as e:
            generation_time = time.time() - start_time
            self._update_performance_metrics(generation_time, success=False)
            logger.error(f"Embodiment image generation failed: {e}")
            raise
        except Exception as e:
            generation_time = time.time() - start_time
            self._update_performance_metrics(generation_time, success=False)
            logger.error(f"Unexpected error in embodiment image generation: {e}")
            raise ImageProviderError(f"Unexpected error: {e}")

    def generate_avatar_variations(
        self, base_prompt: str, variations: list[str], user_id: UUID | None = None
    ) -> list[ImageResult]:
        """
        Generate multiple avatar variations from a base prompt.

        Args:
            base_prompt: Base prompt for avatar generation
            variations: List of variation descriptions
            user_id: User ID for audit logging

        Returns:
            List[ImageResult]: List of generated variations
        """
        logger.info(f"Generating {len(variations)} avatar variations for user_id={user_id}")

        try:
            results = self.provider.generate_avatar_variations(base_prompt, variations)

            # Update performance metrics for each successful generation
            for result in results:
                self._update_performance_metrics(result.generation_time or 0.0, success=True)

            logger.info(f"Generated {len(results)} avatar variations successfully")
            return results

        except ImageProviderError as e:
            self._update_performance_metrics(0.0, success=False)
            logger.error(f"Avatar variation generation failed: {e}")
            raise
        except Exception as e:
            self._update_performance_metrics(0.0, success=False)
            logger.error(f"Unexpected error in avatar variation generation: {e}")
            raise ImageProviderError(f"Unexpected error: {e}")

    def create_embodiment_prompt(self, pald_data: dict[str, Any]) -> str:
        """
        Create an embodiment image prompt from PALD data.

        Args:
            pald_data: PALD (Pedagogical Agent Level of Design) data

        Returns:
            str: Generated prompt for image generation
        """
        # Base prompt for educational embodiment
        base_prompt = "A friendly educational assistant avatar"

        # Extract relevant attributes from PALD data
        prompt_parts = [base_prompt]

        # Physical appearance
        if "appearance" in pald_data:
            appearance = pald_data["appearance"]
            if "gender" in appearance:
                prompt_parts.append(f"{appearance['gender']} appearance")
            if "age_range" in appearance:
                prompt_parts.append(f"{appearance['age_range']} looking")
            if "style" in appearance:
                prompt_parts.append(f"{appearance['style']} style")

        # Personality traits that affect visual representation
        if "personality" in pald_data:
            personality = pald_data["personality"]
            if "approachability" in personality:
                if personality["approachability"] == "high":
                    prompt_parts.append("warm and approachable expression")
            if "formality" in personality:
                if personality["formality"] == "casual":
                    prompt_parts.append("casual and relaxed pose")
                elif personality["formality"] == "formal":
                    prompt_parts.append("professional and composed")

        # Learning context
        if "context" in pald_data:
            context = pald_data["context"]
            if "subject_area" in context:
                subject = context["subject_area"]
                if subject in ["science", "mathematics"]:
                    prompt_parts.append("intelligent and analytical look")
                elif subject in ["arts", "literature"]:
                    prompt_parts.append("creative and expressive demeanor")

        # Join all parts
        full_prompt = ", ".join(prompt_parts)

        # Add quality modifiers
        full_prompt += ", high quality, detailed, professional illustration, clean background"

        logger.debug(f"Created embodiment prompt from PALD: '{full_prompt}'")
        return full_prompt

    def health_check(self) -> bool:
        """
        Check if the image generation service is healthy.

        Returns:
            bool: True if service is healthy
        """
        try:
            is_healthy = self.provider.health_check()
            self._health_status = is_healthy

            if is_healthy:
                logger.debug("Image service health check passed")
            else:
                logger.warning("Image service health check failed")

            return is_healthy

        except Exception as e:
            logger.error(f"Image service health check error: {e}")
            self._health_status = False
            return False

    def get_performance_metrics(self) -> dict[str, Any]:
        """
        Get performance metrics for image generation.

        Returns:
            Dict containing performance metrics
        """
        return self._performance_metrics.copy()

    def get_service_status(self) -> dict[str, Any]:
        """
        Get comprehensive service status.

        Returns:
            Dict containing service status information
        """
        try:
            is_healthy = self.health_check()
            model_info = self.provider.get_model_info()

            status = {
                "healthy": is_healthy,
                "provider_type": type(self.provider).__name__,
                "model_info": model_info,
                "performance_metrics": self.get_performance_metrics(),
            }

            return status

        except Exception as e:
            logger.error(f"Error getting image service status: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "provider_type": type(self.provider).__name__,
            }

    def is_service_available(self) -> bool:
        """
        Check if the image service is available.

        Returns:
            bool: True if service is available
        """
        if self._health_status is None:
            return self.health_check()
        return self._health_status

    def _update_performance_metrics(self, generation_time: float, success: bool) -> None:
        """Update performance metrics."""
        self._performance_metrics["total_generations"] += 1

        if success:
            self._performance_metrics["total_generation_time"] += generation_time
            # Calculate rolling average
            total_successful = (
                self._performance_metrics["total_generations"]
                - self._performance_metrics["failed_generations"]
            )
            if total_successful > 0:
                self._performance_metrics["average_generation_time"] = (
                    self._performance_metrics["total_generation_time"] / total_successful
                )
        else:
            self._performance_metrics["failed_generations"] += 1


# Global image service instance
_image_service: ImageService | None = None


def get_image_service() -> ImageService:
    """Get the global image service instance."""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service


def set_image_service(service: ImageService) -> None:
    """Set the global image service instance (useful for testing)."""
    global _image_service
    _image_service = service


# Convenience functions for common operations
def generate_embodiment_image(
    prompt: str, user_id: UUID | None = None, parameters: dict[str, Any] | None = None
) -> ImageResult:
    """Generate an embodiment image using the global image service."""
    return get_image_service().generate_embodiment_image(prompt, user_id, parameters)


def generate_avatar_variations(
    base_prompt: str, variations: list[str], user_id: UUID | None = None
) -> list[ImageResult]:
    """Generate avatar variations using the global image service."""
    return get_image_service().generate_avatar_variations(base_prompt, variations, user_id)


def create_embodiment_prompt(pald_data: dict[str, Any]) -> str:
    """Create an embodiment prompt from PALD data using the global image service."""
    return get_image_service().create_embodiment_prompt(pald_data)


def health_check() -> bool:
    """Check image service health using the global image service."""
    return get_image_service().health_check()


def get_service_status() -> dict[str, Any]:
    """Get service status using the global image service."""
    return get_image_service().get_service_status()
