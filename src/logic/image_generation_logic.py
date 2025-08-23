"""
Image Generation Logic for Study Participation
Handles PALD-to-image pipeline, image description generation, and consistency checking.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from config.config import config

# Note: GeneratedImage, StudyPALDData, StudyPALDType would be used in actual implementation
from src.exceptions import ValidationError
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class ImageGenerationResult:
    """Result of image generation from PALD data."""
    success: bool
    image_id: UUID | None
    image_path: str | None
    prompt_used: str
    generation_parameters: dict[str, Any]
    generation_time_ms: int
    error_message: str | None = None


@dataclass
class ImageDescriptionResult:
    """Result of image description generation."""
    success: bool
    description: str
    pald_data: dict[str, Any] | None
    description_confidence: float
    processing_time_ms: int
    error_message: str | None = None


@dataclass
class ConsistencyLoopResult:
    """Result of PALD consistency loop processing."""
    final_image_id: UUID | None
    iterations_performed: int
    consistency_achieved: bool
    final_consistency_score: float
    total_processing_time_ms: int
    loop_metadata: dict[str, Any]


class ImageGenerationLogic:
    """Logic layer for image generation and PALD consistency processing."""

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self._prompt_cache: dict[str, str] = {}

    def generate_image_from_pald(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        pald_data: dict[str, Any],
        pald_source_id: UUID | None = None,
    ) -> ImageGenerationResult:
        """
        Generate an image from PALD data using Stable Diffusion.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            pald_data: PALD data to convert to image
            pald_source_id: Optional source PALD data ID
            
        Returns:
            ImageGenerationResult: Generation result with image details
        """
        start_time = datetime.now()
        image_id = uuid4()
        
        logger.info(f"Generating image from PALD for pseudonym {pseudonym_id}")
        
        try:
            # Convert PALD to compressed prompt
            prompt = self.compress_pald_to_prompt(pald_data)
            
            if not prompt.strip():
                raise ValidationError("Generated prompt is empty")
            
            # Note: In a real implementation, this would test LLM service availability
            # For now, we proceed directly to image generation
            
            # Prepare generation parameters
            generation_params = self._prepare_generation_parameters()
            
            # Generate image (placeholder - would integrate with Stable Diffusion)
            image_path = self._generate_image_with_stable_diffusion(
                prompt, generation_params, image_id
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ImageGenerationResult(
                success=True,
                image_id=image_id,
                image_path=image_path,
                prompt_used=prompt,
                generation_parameters=generation_params,
                generation_time_ms=max(1, int(processing_time)),  # Ensure at least 1ms
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Image generation failed: {e}")
            
            return ImageGenerationResult(
                success=False,
                image_id=None,
                image_path=None,
                prompt_used=prompt if 'prompt' in locals() else "",
                generation_parameters={},
                generation_time_ms=int(processing_time),
                error_message=str(e),
            )

    def describe_generated_image(
        self,
        image_path: str,
        focus_on_embodiment: bool = True,
    ) -> ImageDescriptionResult:
        """
        Generate a description of an image and extract PALD data from it.
        
        Args:
            image_path: Path to the generated image
            focus_on_embodiment: Whether to focus on embodiment aspects
            
        Returns:
            ImageDescriptionResult: Description and extracted PALD data
        """
        start_time = datetime.now()
        
        logger.info(f"Describing image: {image_path}")
        
        try:
            # Generate image description using LLM
            description_prompt = self._create_image_description_prompt(
                image_path, focus_on_embodiment
            )
            
            llm_response = self.llm_service.generate_response(
                prompt=description_prompt,
                model=config.llm.models.get("vision", "llava"),
                parameters={
                    "temperature": 0.3,
                    "max_tokens": 500,
                }
            )
            
            description = llm_response.text.strip()
            
            # Extract PALD data from description
            pald_extraction_result = self._extract_pald_from_description(description)
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ImageDescriptionResult(
                success=True,
                description=description,
                pald_data=pald_extraction_result.get("pald_data"),
                description_confidence=pald_extraction_result.get("confidence", 0.8),
                processing_time_ms=max(1, int(processing_time)),  # Ensure at least 1ms
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Image description failed: {e}")
            
            return ImageDescriptionResult(
                success=False,
                description="",
                pald_data=None,
                description_confidence=0.0,
                processing_time_ms=int(processing_time),
                error_message=str(e),
            )

    def compress_pald_to_prompt(self, pald_data: dict[str, Any]) -> str:
        """
        Compress PALD data into a 77-token image generation prompt.
        
        Args:
            pald_data: PALD data to compress
            
        Returns:
            str: Compressed prompt suitable for Stable Diffusion
        """
        # Check cache first
        cache_key = f"pald_prompt_{hash(str(pald_data))}"
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]
        
        try:
            # Extract key visual elements from PALD structure
            prompt_parts = []
            
            # Global design level
            if global_design := pald_data.get("global_design_level", {}):
                if appearance := global_design.get("overall_appearance"):
                    prompt_parts.append(self._compress_text(appearance, 15))
                if style := global_design.get("style"):
                    prompt_parts.append(self._compress_text(style, 10))
                if theme := global_design.get("theme"):
                    prompt_parts.append(self._compress_text(theme, 8))
            
            # Middle design level
            if middle_design := pald_data.get("middle_design_level", {}):
                if physical := middle_design.get("physical_attributes"):
                    prompt_parts.append(self._compress_text(physical, 12))
                if clothing := middle_design.get("clothing"):
                    prompt_parts.append(self._compress_text(clothing, 10))
                if accessories := middle_design.get("accessories"):
                    prompt_parts.append(self._compress_text(accessories, 8))
            
            # Detailed level
            if detailed := pald_data.get("detailed_level", {}):
                if facial := detailed.get("facial_features"):
                    prompt_parts.append(self._compress_text(facial, 8))
                if hair := detailed.get("hair"):
                    prompt_parts.append(self._compress_text(hair, 6))
                if colors := detailed.get("colors"):
                    prompt_parts.append(self._compress_text(colors, 6))
            
            # Join and ensure it fits within token limit
            prompt = ", ".join(filter(None, prompt_parts))
            
            # If no prompt parts, use default
            if not prompt.strip():
                prompt = "pedagogical agent, friendly appearance, professional style"
            
            # Ensure prompt is within 77 tokens (approximately 77 words)
            words = prompt.split()
            if len(words) > 77:
                prompt = " ".join(words[:77])
            
            # Add quality modifiers if space allows
            if len(words) < 70:
                prompt += ", high quality, detailed, professional"
            
            # Cache the result
            self._prompt_cache[cache_key] = prompt
            
            return prompt
            
        except Exception as e:
            logger.error(f"PALD compression failed: {e}")
            return "pedagogical agent, friendly appearance, professional style"

    def run_consistency_loop(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        input_pald: dict[str, Any],
        max_iterations: int | None = None,
    ) -> ConsistencyLoopResult:
        """
        Run the PALD consistency loop until consistent or max iterations reached.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            input_pald: Original PALD data from user input
            max_iterations: Maximum iterations (defaults to config value)
            
        Returns:
            ConsistencyLoopResult: Final result of consistency loop
        """
        start_time = datetime.now()
        max_iterations = max_iterations or config.pald_boundary.pald_consistency_max_iterations
        threshold = config.pald_boundary.pald_consistency_threshold
        
        logger.info(
            f"Starting consistency loop for pseudonym {pseudonym_id}, "
            f"max_iterations={max_iterations}"
        )
        
        current_pald = input_pald.copy()
        final_image_id = None
        iterations = 0
        consistency_achieved = False
        final_score = 0.0
        
        loop_metadata = {
            "iterations": [],
            "consistency_scores": [],
            "generation_times": [],
        }
        
        try:
            while iterations < max_iterations and not consistency_achieved:
                iterations += 1
                iteration_start = datetime.now()
                
                logger.info(f"Consistency loop iteration {iterations}/{max_iterations}")
                
                # Generate image from current PALD
                generation_result = self.generate_image_from_pald(
                    pseudonym_id, session_id, current_pald
                )
                
                if not generation_result.success:
                    logger.warning(f"Image generation failed in iteration {iterations}")
                    break
                
                final_image_id = generation_result.image_id
                
                # Describe the generated image
                description_result = self.describe_generated_image(
                    generation_result.image_path
                )
                
                if not description_result.success or not description_result.pald_data:
                    logger.warning(f"Image description failed in iteration {iterations}")
                    break
                
                # Check consistency
                consistency_score = self._calculate_pald_consistency(
                    input_pald, description_result.pald_data
                )
                
                final_score = consistency_score
                consistency_achieved = consistency_score >= threshold
                
                iteration_time = (datetime.now() - iteration_start).total_seconds() * 1000
                
                # Record iteration metadata
                loop_metadata["iterations"].append({
                    "iteration": iterations,
                    "consistency_score": consistency_score,
                    "generation_time_ms": generation_result.generation_time_ms,
                    "description_time_ms": description_result.processing_time_ms,
                    "total_time_ms": int(iteration_time),
                })
                loop_metadata["consistency_scores"].append(consistency_score)
                loop_metadata["generation_times"].append(int(iteration_time))
                
                logger.info(
                    f"Iteration {iterations}: consistency_score={consistency_score:.3f}, "
                    f"threshold={threshold}, achieved={consistency_achieved}"
                )
                
                if not consistency_achieved and iterations < max_iterations:
                    # Update PALD for next iteration (could implement refinement logic here)
                    current_pald = self._refine_pald_for_next_iteration(
                        current_pald, description_result.pald_data, consistency_score
                    )
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            
            logger.info(
                f"Consistency loop completed: iterations={iterations}, "
                f"achieved={consistency_achieved}, final_score={final_score:.3f}"
            )
            
            return ConsistencyLoopResult(
                final_image_id=final_image_id,
                iterations_performed=iterations,
                consistency_achieved=consistency_achieved,
                final_consistency_score=final_score,
                total_processing_time_ms=max(1, int(total_time)),  # Ensure at least 1ms
                loop_metadata=loop_metadata,
            )
            
        except Exception as e:
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Consistency loop failed: {e}")
            
            return ConsistencyLoopResult(
                final_image_id=final_image_id,
                iterations_performed=iterations,
                consistency_achieved=False,
                final_consistency_score=final_score,
                total_processing_time_ms=int(total_time),
                loop_metadata=loop_metadata,
            )

    def _prepare_generation_parameters(self) -> dict[str, Any]:
        """Prepare parameters for image generation."""
        return {
            "model": config.image_generation.model_name,
            "width": config.image_generation.image_size[0],
            "height": config.image_generation.image_size[1],
            "num_inference_steps": config.image_generation.num_inference_steps,
            "guidance_scale": config.image_generation.guidance_scale,
            "device": config.image_generation.device,
        }

    def _generate_image_with_stable_diffusion(
        self,
        prompt: str,
        parameters: dict[str, Any],
        image_id: UUID,
    ) -> str:
        """
        Generate image using Stable Diffusion (placeholder implementation).
        
        In a real implementation, this would:
        1. Load the Stable Diffusion model
        2. Generate the image from the prompt
        3. Save the image to the configured path
        4. Return the image path
        """
        # Placeholder implementation - would integrate with actual Stable Diffusion
        image_filename = f"generated_{image_id}.png"
        image_path = f"generated_images/{image_filename}"
        
        # In real implementation, this would call Stable Diffusion API/library
        logger.info(f"[PLACEHOLDER] Generating image with prompt: {prompt[:100]}...")
        logger.info(f"[PLACEHOLDER] Image would be saved to: {image_path}")
        
        return image_path

    def _create_image_description_prompt(
        self,
        image_path: str,
        focus_on_embodiment: bool,
    ) -> str:
        """Create a prompt for image description."""
        base_prompt = f"""
Analyze the image at {image_path} and provide a detailed description.
"""
        
        if focus_on_embodiment:
            base_prompt += """
Focus specifically on embodiment-related aspects such as:
- Overall appearance and visual style
- Physical characteristics and attributes
- Clothing, accessories, and visual elements
- Facial features, hair, and colors
- Any design elements that describe how this character/agent looks

Provide a comprehensive description that captures all visual embodiment details.
"""
        else:
            base_prompt += """
Provide a general description of what you see in the image, including:
- Main subjects and objects
- Visual style and composition
- Colors, lighting, and atmosphere
- Any notable details or characteristics
"""
        
        return base_prompt

    def _extract_pald_from_description(self, description: str) -> dict[str, Any]:
        """Extract PALD data from image description."""
        try:
            # Create PALD extraction prompt
            extraction_prompt = f"""
Extract PALD (Pedagogical Agent Level of Design) information from this image description.
Focus on embodiment-related attributes and organize them into the PALD structure.

Description:
{description}

Please return a JSON object with this structure:
{{
    "pald_data": {{
        "global_design_level": {{
            "overall_appearance": "description",
            "style": "description", 
            "theme": "description"
        }},
        "middle_design_level": {{
            "physical_attributes": "description",
            "clothing": "description",
            "accessories": "description"
        }},
        "detailed_level": {{
            "facial_features": "description",
            "hair": "description",
            "colors": "description"
        }}
    }},
    "confidence": 0.8
}}

Only include attributes that are clearly described in the text.
"""
            
            llm_response = self.llm_service.generate_response(
                prompt=extraction_prompt,
                model=config.llm.models.get("default", "llama3"),
                parameters={
                    "temperature": 0.2,
                    "max_tokens": 800,
                    "format": "json",
                }
            )
            
            # Parse JSON response
            response_text = llm_response.text.strip()
            
            # Handle JSON extraction
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                return json.loads(json_text)
            else:
                logger.warning("No JSON found in PALD extraction response")
                return {"pald_data": {}, "confidence": 0.0}
                
        except Exception as e:
            logger.error(f"PALD extraction from description failed: {e}")
            return {"pald_data": {}, "confidence": 0.0}

    def _calculate_pald_consistency(
        self,
        input_pald: dict[str, Any],
        description_pald: dict[str, Any],
    ) -> float:
        """Calculate consistency score between input and description PALDs."""
        # Simplified consistency calculation
        # In a real implementation, this would be more sophisticated
        
        # Handle empty PALDs
        if not input_pald and not description_pald:
            return 1.0  # Both empty, perfectly consistent
        if not input_pald or not description_pald:
            return 0.0  # One empty, one not - inconsistent
        
        # Get all keys from both PALDs
        all_keys = set(input_pald.keys()) | set(description_pald.keys())
        
        if not all_keys:
            return 1.0
        
        matching_score = 0.0
        total_weight = 0.0
        
        # Weight different levels
        level_weights = {
            "global_design_level": 0.4,
            "middle_design_level": 0.35,
            "detailed_level": 0.25,
        }
        
        for key in all_keys:
            weight = level_weights.get(key, 0.1)
            total_weight += weight
            
            if key in input_pald and key in description_pald:
                # Calculate similarity for this level
                similarity = self._calculate_level_similarity(
                    input_pald[key], description_pald[key]
                )
                matching_score += similarity * weight
            elif key in input_pald or key in description_pald:
                # Partial penalty for missing keys
                matching_score += 0.3 * weight
        
        return matching_score / total_weight if total_weight > 0 else 0.0

    def _calculate_level_similarity(self, level1: Any, level2: Any) -> float:
        """Calculate similarity between two PALD levels."""
        if level1 == level2:
            return 1.0
        
        if isinstance(level1, dict) and isinstance(level2, dict):
            all_subkeys = set(level1.keys()) | set(level2.keys())
            if not all_subkeys:
                return 1.0
            
            similarity_sum = 0.0
            for subkey in all_subkeys:
                if subkey in level1 and subkey in level2:
                    # Simple word overlap for string values
                    if isinstance(level1[subkey], str) and isinstance(level2[subkey], str):
                        words1 = set(level1[subkey].lower().split())
                        words2 = set(level2[subkey].lower().split())
                        
                        if words1 and words2:
                            intersection = words1 & words2
                            union = words1 | words2
                            similarity_sum += len(intersection) / len(union)
                        else:
                            similarity_sum += 1.0 if not words1 and not words2 else 0.0
                    else:
                        similarity_sum += 1.0 if level1[subkey] == level2[subkey] else 0.0
                else:
                    similarity_sum += 0.3  # Partial match for missing keys
            
            return similarity_sum / len(all_subkeys)
        
        return 0.0

    def _refine_pald_for_next_iteration(
        self,
        current_pald: dict[str, Any],
        description_pald: dict[str, Any],
        consistency_score: float,
    ) -> dict[str, Any]:
        """
        Refine PALD data for the next iteration based on consistency analysis.
        
        This is a placeholder for more sophisticated refinement logic.
        """
        # Simple refinement: blend current and description PALDs
        refined_pald = current_pald.copy()
        
        # If consistency is very low, try to incorporate more from description
        if consistency_score < 0.3:
            for level_key in ["global_design_level", "middle_design_level", "detailed_level"]:
                if level_key in description_pald:
                    if level_key not in refined_pald:
                        refined_pald[level_key] = {}
                    
                    # Merge attributes from description
                    for attr_key, attr_value in description_pald[level_key].items():
                        if attr_key not in refined_pald[level_key] and attr_value:
                            refined_pald[level_key][attr_key] = attr_value
        
        return refined_pald

    def _compress_text(self, text: str, max_words: int) -> str:
        """Compress text to a maximum number of words."""
        if not text:
            return ""
        
        words = text.split()
        if len(words) <= max_words:
            return text
        
        # Take the most important words (simple approach)
        return " ".join(words[:max_words])