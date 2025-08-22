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
from src.services.image_isolation_service import ImageIsolationService, ImageIsolationConfig
from src.services.image_quality_detector import ImageQualityDetector, QualityDetectionConfig

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
            "isolation_operations": 0,
            "isolation_successes": 0,
            "quality_checks": 0,
            "faulty_images_detected": 0,
        }
        self._health_status: bool | None = None
        
        # Initialize image isolation and quality detection services
        self.isolation_service = self._create_isolation_service()
        self.quality_detector = self._create_quality_detector()

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
    
    def _create_isolation_service(self) -> ImageIsolationService | None:
        """Create image isolation service based on configuration."""
        if not config.feature_flags.enable_image_isolation:
            logger.info("Image isolation is disabled by feature flag")
            return None
        
        try:
            isolation_config = ImageIsolationConfig(
                enabled=config.image_isolation.enabled,
                detection_confidence_threshold=config.image_isolation.detection_confidence_threshold,
                edge_refinement_enabled=config.image_isolation.edge_refinement_enabled,
                background_removal_method=config.image_isolation.background_removal_method,
                fallback_to_original=config.image_isolation.fallback_to_original,
                max_processing_time=config.image_isolation.max_processing_time,
                output_format=config.image_isolation.output_format,
                uniform_background_color=config.image_isolation.uniform_background_color
            )
            return ImageIsolationService(isolation_config)
        except Exception as e:
            logger.warning(f"Failed to initialize ImageIsolationService: {e}")
            return None
    
    def _create_quality_detector(self) -> ImageQualityDetector | None:
        """Create image quality detector based on configuration."""
        if not config.feature_flags.enable_image_quality_detection:
            logger.info("Image quality detection is disabled by feature flag")
            return None
        
        try:
            quality_config = QualityDetectionConfig(
                enabled=config.image_isolation.enabled,  # Use same flag as isolation
                min_person_confidence=0.7,
                max_people_allowed=1,
                min_quality_score=0.6,
                blur_threshold=0.3,
                noise_threshold=0.1
            )
            return ImageQualityDetector(quality_config)
        except Exception as e:
            logger.warning(f"Failed to initialize ImageQualityDetector: {e}")
            return None

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

            # Apply image processing pipeline (isolation and quality detection)
            processed_result = self._process_generated_image(result, user_id)

            # Update performance metrics
            self._update_performance_metrics(result.generation_time or 0.0, success=True)

            logger.info(
                f"Embodiment image generated successfully: {processed_result.image_path}, time={result.generation_time:.2f}s"
            )
            return processed_result

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
                "isolation_service": self.get_isolation_service_status(),
                "quality_detector": self.get_quality_detector_status(),
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
    
    def _process_generated_image(self, result: ImageResult, user_id: UUID | None = None) -> ImageResult:
        """
        Process generated image through isolation and quality detection pipeline.
        
        Args:
            result: Original image generation result
            user_id: User ID for audit logging
            
        Returns:
            ImageResult: Processed image result (may be original if processing fails)
        """
        if not result.image_path:
            logger.warning("No image path in result, skipping processing")
            return result
        
        processed_result = result
        
        # Step 1: Quality detection
        if self.quality_detector:
            try:
                self._performance_metrics["quality_checks"] += 1
                detection_result = self.quality_detector.detect_faulty_image(result.image_path)
                
                if detection_result.is_faulty:
                    self._performance_metrics["faulty_images_detected"] += 1
                    logger.warning(
                        f"Faulty image detected: {result.image_path}, "
                        f"reasons: {[r.value for r in detection_result.reasons]}, "
                        f"confidence: {detection_result.confidence_score:.2f}"
                    )
                    
                    # Add quality information to result metadata
                    if not processed_result.metadata:
                        processed_result.metadata = {}
                    processed_result.metadata.update({
                        "quality_check": {
                            "is_faulty": detection_result.is_faulty,
                            "reasons": [r.value for r in detection_result.reasons],
                            "confidence_score": detection_result.confidence_score,
                            "recommendations": detection_result.recommendations
                        }
                    })
                else:
                    logger.info(f"Image quality check passed: {result.image_path}")
                    
            except Exception as e:
                logger.error(f"Quality detection failed for {result.image_path}: {e}")
        
        # Step 2: Image isolation (only if quality check passed or no quality detector)
        should_isolate = True
        if self.quality_detector and processed_result.metadata:
            quality_check = processed_result.metadata.get("quality_check", {})
            should_isolate = not quality_check.get("is_faulty", False)
        
        if should_isolate and self.isolation_service:
            try:
                self._performance_metrics["isolation_operations"] += 1
                isolation_result = self.isolation_service.isolate_person(result.image_path)
                
                if isolation_result.success and isolation_result.isolated_image_path:
                    self._performance_metrics["isolation_successes"] += 1
                    
                    # Update result with isolated image
                    processed_result = ImageResult(
                        image_path=isolation_result.isolated_image_path,
                        generation_time=result.generation_time,
                        metadata={
                            **(processed_result.metadata or {}),
                            "isolation": {
                                "success": True,
                                "original_path": result.image_path,
                                "method_used": isolation_result.method_used,
                                "confidence_score": isolation_result.confidence_score,
                                "processing_time": isolation_result.processing_time
                            }
                        }
                    )
                    
                    logger.info(
                        f"Image isolation successful: {isolation_result.isolated_image_path}, "
                        f"method: {isolation_result.method_used}, "
                        f"confidence: {isolation_result.confidence_score:.2f}"
                    )
                else:
                    logger.warning(
                        f"Image isolation failed: {isolation_result.error_message}, "
                        f"using original image: {result.image_path}"
                    )
                    
                    # Add isolation failure info to metadata
                    if not processed_result.metadata:
                        processed_result.metadata = {}
                    processed_result.metadata["isolation"] = {
                        "success": False,
                        "error_message": isolation_result.error_message,
                        "fallback_used": True
                    }
                    
            except Exception as e:
                logger.error(f"Image isolation failed for {result.image_path}: {e}")
                
                # Add error info to metadata
                if not processed_result.metadata:
                    processed_result.metadata = {}
                processed_result.metadata["isolation"] = {
                    "success": False,
                    "error_message": str(e),
                    "fallback_used": True
                }
        
        return processed_result
    
    def get_isolation_service_status(self) -> dict[str, Any]:
        """Get status of image isolation service."""
        if not self.isolation_service:
            return {"enabled": False, "reason": "Service not initialized"}
        
        return {
            "enabled": True,
            "config": {
                "background_removal_method": self.isolation_service.config.background_removal_method,
                "detection_confidence_threshold": self.isolation_service.config.detection_confidence_threshold,
                "max_processing_time": self.isolation_service.config.max_processing_time,
                "fallback_to_original": self.isolation_service.config.fallback_to_original
            }
        }
    
    def get_quality_detector_status(self) -> dict[str, Any]:
        """Get status of image quality detector."""
        if not self.quality_detector:
            return {"enabled": False, "reason": "Service not initialized"}
        
        return {
            "enabled": True,
            "config": {
                "min_person_confidence": self.quality_detector.config.min_person_confidence,
                "max_people_allowed": self.quality_detector.config.max_people_allowed,
                "min_quality_score": self.quality_detector.config.min_quality_score,
                "blur_threshold": self.quality_detector.config.blur_threshold,
                "noise_threshold": self.quality_detector.config.noise_threshold
            }
        }
    
    def analyze_image_batch_quality(self, image_paths: list[str]) -> dict[str, Any]:
        """
        Analyze a batch of images for quality issues.
        
        Args:
            image_paths: List of image paths to analyze
            
        Returns:
            Dict with batch analysis results
        """
        if not self.quality_detector:
            return {"error": "Quality detector not available"}
        
        try:
            batch_result = self.quality_detector.analyze_batch_processing(image_paths)
            
            return {
                "total_images": batch_result.total_images,
                "faulty_images": batch_result.faulty_images,
                "faulty_percentage": batch_result.faulty_percentage,
                "should_regenerate": batch_result.should_regenerate,
                "common_issues": [issue.value for issue in batch_result.common_issues],
                "batch_quality_score": batch_result.batch_quality_score,
                "processing_time": batch_result.processing_time
            }
        except Exception as e:
            logger.error(f"Batch quality analysis failed: {e}")
            return {"error": str(e)}


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
