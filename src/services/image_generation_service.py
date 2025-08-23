"""
Image Generation Service Layer for Study Participation
Handles data persistence for generated images and integration with Stable Diffusion.
"""

import logging
import os
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models import GeneratedImage
from src.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Service layer for image generation data persistence and external integrations."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def store_generated_image(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        image_path: str,
        prompt: str,
        generation_parameters: dict[str, Any],
        pald_source_id: UUID | None = None,
    ) -> GeneratedImage:
        """
        Store a generated image record in the database.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            image_path: Path to the generated image file
            prompt: Prompt used for generation
            generation_parameters: Parameters used for generation
            pald_source_id: Optional source PALD data ID
            
        Returns:
            GeneratedImage: Stored image record
            
        Raises:
            DatabaseError: If storage fails
            ValidationError: If input validation fails
        """
        try:
            if not image_path.strip():
                raise ValidationError("Image path cannot be empty")
            
            if not prompt.strip():
                raise ValidationError("Prompt cannot be empty")
            
            if not generation_parameters:
                raise ValidationError("Generation parameters cannot be empty")
            
            image = GeneratedImage(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_path=image_path,
                prompt=prompt,
                pald_source_id=pald_source_id,
                generation_parameters=generation_parameters,
            )
            
            self.db_session.add(image)
            self.db_session.commit()
            
            logger.info(f"Stored generated image {image.image_id} for pseudonym {pseudonym_id}")
            return image
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to store generated image: {e}")
            raise DatabaseError(f"Failed to store generated image: {e}") from e

    def get_generated_images(
        self,
        pseudonym_id: UUID,
        session_id: UUID | None = None,
        limit: int = 50,
    ) -> list[GeneratedImage]:
        """
        Retrieve generated images for a participant.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Optional session ID to filter by
            limit: Maximum number of images to retrieve
            
        Returns:
            list[GeneratedImage]: List of generated image records
        """
        try:
            query = self.db_session.query(GeneratedImage).filter(
                GeneratedImage.pseudonym_id == pseudonym_id
            )
            
            if session_id:
                query = query.filter(GeneratedImage.session_id == session_id)
            
            return (
                query.order_by(GeneratedImage.created_at.desc())
                .limit(limit)
                .all()
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve generated images: {e}")
            raise DatabaseError(f"Failed to retrieve generated images: {e}") from e

    def get_image_by_id(self, image_id: UUID) -> GeneratedImage | None:
        """
        Retrieve a specific generated image by ID.
        
        Args:
            image_id: Image ID to retrieve
            
        Returns:
            GeneratedImage | None: Image record if found
        """
        try:
            return (
                self.db_session.query(GeneratedImage)
                .filter(GeneratedImage.image_id == image_id)
                .first()
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve image {image_id}: {e}")
            raise DatabaseError(f"Failed to retrieve image: {e}") from e

    def delete_generated_image(self, image_id: UUID) -> bool:
        """
        Delete a generated image record and its file.
        
        Args:
            image_id: Image ID to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            DatabaseError: If deletion fails
        """
        try:
            image = self.get_image_by_id(image_id)
            if not image:
                logger.warning(f"Image {image_id} not found for deletion")
                return False
            
            # Delete the physical file if it exists
            if os.path.exists(image.image_path):
                try:
                    os.remove(image.image_path)
                    logger.info(f"Deleted image file: {image.image_path}")
                except OSError as e:
                    logger.warning(f"Failed to delete image file {image.image_path}: {e}")
            
            # Delete the database record
            self.db_session.delete(image)
            self.db_session.commit()
            
            logger.info(f"Deleted generated image {image_id}")
            return True
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to delete generated image {image_id}: {e}")
            raise DatabaseError(f"Failed to delete generated image: {e}") from e

    def call_stable_diffusion(
        self,
        prompt: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call Stable Diffusion API/service to generate an image.
        
        This is a placeholder implementation that would integrate with actual
        Stable Diffusion service (local or remote).
        
        Args:
            prompt: Text prompt for image generation
            parameters: Generation parameters (model, size, steps, etc.)
            
        Returns:
            dict: Generation result with image path and metadata
            
        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If generation service fails
        """
        try:
            if not prompt.strip():
                raise ValidationError("Prompt cannot be empty")
            
            # Validate required parameters
            required_params = ["width", "height", "num_inference_steps", "guidance_scale"]
            for param in required_params:
                if param not in parameters:
                    raise ValidationError(f"Missing required parameter: {param}")
            
            logger.info(f"Calling Stable Diffusion with prompt: {prompt[:100]}...")
            
            # Placeholder implementation - would integrate with actual Stable Diffusion
            # This could be:
            # 1. Local Stable Diffusion installation
            # 2. Hugging Face Diffusers library
            # 3. Remote API service
            # 4. Docker container with Stable Diffusion
            
            generation_result = self._mock_stable_diffusion_call(prompt, parameters)
            
            logger.info(f"Stable Diffusion generation completed: {generation_result['image_path']}")
            
            return generation_result
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Stable Diffusion call failed: {e}")
            raise DatabaseError(f"Image generation service failed: {e}") from e

    def call_image_description_llm(
        self,
        image_path: str,
        description_prompt: str,
    ) -> str:
        """
        Call LLM service to describe an image.
        
        This would integrate with a vision-capable LLM like LLaVA.
        
        Args:
            image_path: Path to the image to describe
            description_prompt: Prompt for the description task
            
        Returns:
            str: Generated image description
            
        Raises:
            ValidationError: If parameters are invalid
            DatabaseError: If description service fails
        """
        try:
            if not image_path.strip():
                raise ValidationError("Image path cannot be empty")
            
            if not description_prompt.strip():
                raise ValidationError("Description prompt cannot be empty")
            
            if not os.path.exists(image_path):
                raise ValidationError(f"Image file not found: {image_path}")
            
            logger.info(f"Describing image: {image_path}")
            
            # Placeholder implementation - would integrate with vision LLM
            # This could be:
            # 1. Local LLaVA model
            # 2. OpenAI GPT-4 Vision API
            # 3. Google Gemini Vision
            # 4. Other vision-capable models
            
            description = self._mock_image_description_call(image_path, description_prompt)
            
            logger.info(f"Image description completed: {len(description)} characters")
            
            return description
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            logger.error(f"Image description call failed: {e}")
            raise DatabaseError(f"Image description service failed: {e}") from e

    def ensure_image_directory(self, image_path: str) -> None:
        """
        Ensure the directory for an image path exists.
        
        Args:
            image_path: Path to the image file
        """
        try:
            directory = os.path.dirname(image_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"Created image directory: {directory}")
                
        except Exception as e:
            logger.error(f"Failed to create image directory: {e}")
            raise DatabaseError(f"Failed to create image directory: {e}") from e

    def get_image_statistics(
        self,
        pseudonym_id: UUID,
        session_id: UUID | None = None,
    ) -> dict[str, Any]:
        """
        Get statistics for generated images.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Optional session ID to filter by
            
        Returns:
            dict: Image generation statistics
        """
        try:
            query = self.db_session.query(GeneratedImage).filter(
                GeneratedImage.pseudonym_id == pseudonym_id
            )
            
            if session_id:
                query = query.filter(GeneratedImage.session_id == session_id)
            
            total_images = query.count()
            
            # Get images with PALD sources
            images_with_pald = query.filter(
                GeneratedImage.pald_source_id.isnot(None)
            ).count()
            
            # Get recent images (last 24 hours)
            recent_cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            recent_images = query.filter(
                GeneratedImage.created_at >= recent_cutoff
            ).count()
            
            return {
                "total_images": total_images,
                "images_with_pald_source": images_with_pald,
                "recent_images_24h": recent_images,
                "images_without_pald_source": total_images - images_with_pald,
            }
            
        except Exception as e:
            logger.error(f"Failed to get image statistics: {e}")
            raise DatabaseError(f"Failed to get image statistics: {e}") from e

    def _mock_stable_diffusion_call(
        self,
        prompt: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Mock implementation of Stable Diffusion call.
        
        In a real implementation, this would:
        1. Load the Stable Diffusion model
        2. Generate the image from the prompt
        3. Save the image to disk
        4. Return the result metadata
        """
        import uuid
        
        # Generate a unique filename
        image_id = uuid.uuid4()
        image_filename = f"generated_{image_id}.png"
        image_path = f"generated_images/{image_filename}"
        
        # Ensure directory exists
        self.ensure_image_directory(image_path)
        
        # Mock generation metadata
        generation_metadata = {
            "image_path": image_path,
            "prompt": prompt,
            "parameters": parameters,
            "generation_time_ms": 5000,  # Mock 5 second generation
            "model_used": parameters.get("model", "stable-diffusion-v1-5"),
            "seed": 42,  # Mock seed
        }
        
        logger.info(f"[MOCK] Generated image: {image_path}")
        
        return generation_metadata

    def _mock_image_description_call(
        self,
        image_path: str,
        description_prompt: str,
    ) -> str:
        """
        Mock implementation of image description call.
        
        In a real implementation, this would:
        1. Load the vision model (e.g., LLaVA)
        2. Process the image and prompt
        3. Generate a detailed description
        4. Return the description text
        """
        # Mock description based on the image path
        mock_description = f"""
This image shows a pedagogical agent with a friendly and professional appearance. 
The character has a modern, approachable design with clean lines and a welcoming expression.
The overall style is contemporary and suitable for educational contexts.

Physical attributes include well-defined facial features with expressive eyes and a warm smile.
The character is dressed in professional attire that conveys competence and approachability.
The color scheme uses calming, educational-friendly tones.

The design emphasizes clarity and visual appeal, making it suitable for learning environments.
All visual elements work together to create a trustworthy and engaging pedagogical presence.

[Mock description generated for: {os.path.basename(image_path)}]
"""
        
        logger.info(f"[MOCK] Generated description for: {image_path}")
        
        return mock_description.strip()