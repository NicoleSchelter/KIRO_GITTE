"""
Embodiment Logic Layer for GITTE system.
Handles business logic for embodiment creation, personalization, and image generation.
"""

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.data.models import User
from src.services.image_provider import ImageProviderError, ImageResult
from src.services.image_service import ImageService, get_image_service
from src.services.pald_service import PALDSchemaService

logger = logging.getLogger(__name__)


@dataclass
class EmbodimentProfile:
    """Embodiment profile containing visual and personality characteristics."""

    user_id: UUID
    visual_attributes: dict[str, Any]
    personality_traits: dict[str, Any]
    learning_preferences: dict[str, Any]
    generated_images: list[str] = None

    def __post_init__(self):
        if self.generated_images is None:
            self.generated_images = []


@dataclass
class EmbodimentRequest:
    """Request for embodiment generation."""

    user_id: UUID
    pald_data: dict[str, Any]
    custom_prompt: str | None = None
    variations: list[str] | None = None
    parameters: dict[str, Any] | None = None


class EmbodimentLogic:
    """
    Logic layer for embodiment operations.
    Handles embodiment creation, personalization, and image generation workflows.
    """

    def __init__(
        self,
        image_service: ImageService | None = None,
        pald_service: PALDSchemaService | None = None,
    ):
        """
        Initialize embodiment logic.

        Args:
            image_service: Image service instance
            pald_service: PALD service instance
        """
        self.image_service = image_service or get_image_service()
        self.pald_service = pald_service

    def create_embodiment_profile(
        self, user: User, pald_data: dict[str, Any], preferences: dict[str, Any] | None = None
    ) -> EmbodimentProfile:
        """
        Create an embodiment profile from user data and PALD information.

        Args:
            user: User instance
            pald_data: PALD data containing pedagogical preferences
            preferences: Additional user preferences

        Returns:
            EmbodimentProfile: Created embodiment profile
        """
        logger.info(f"Creating embodiment profile for user {user.id}")

        try:
            # Validate PALD data if service is available
            if self.pald_service:
                validation_result = self.pald_service.validate_pald_data(pald_data)
                if not validation_result.is_valid:
                    logger.warning(f"PALD validation issues: {validation_result.errors}")

            # Extract visual attributes from PALD
            visual_attributes = self._extract_visual_attributes(pald_data)

            # Extract personality traits
            personality_traits = self._extract_personality_traits(pald_data)

            # Extract learning preferences
            learning_preferences = self._extract_learning_preferences(pald_data)

            # Apply user preferences if provided
            if preferences:
                visual_attributes.update(preferences.get("visual", {}))
                personality_traits.update(preferences.get("personality", {}))
                learning_preferences.update(preferences.get("learning", {}))

            profile = EmbodimentProfile(
                user_id=user.id,
                visual_attributes=visual_attributes,
                personality_traits=personality_traits,
                learning_preferences=learning_preferences,
            )

            logger.info(f"Embodiment profile created successfully for user {user.id}")
            return profile

        except Exception as e:
            logger.error(f"Failed to create embodiment profile for user {user.id}: {e}")
            raise

    def generate_embodiment_image(self, request: EmbodimentRequest) -> ImageResult:
        """
        Generate an embodiment image based on user request.

        Args:
            request: Embodiment generation request

        Returns:
            ImageResult: Generated image result
        """
        logger.info(f"Generating embodiment image for user {request.user_id}")

        try:
            # Use custom prompt if provided, otherwise generate from PALD
            if request.custom_prompt:
                prompt = request.custom_prompt
                logger.debug(f"Using custom prompt: '{prompt[:50]}...'")
            else:
                prompt = self.image_service.create_embodiment_prompt(request.pald_data)
                logger.debug(f"Generated prompt from PALD: '{prompt[:50]}...'")

            # Generate image
            result = self.image_service.generate_embodiment_image(
                prompt=prompt, user_id=request.user_id, parameters=request.parameters
            )

            logger.info(f"Embodiment image generated successfully for user {request.user_id}")
            return result

        except ImageProviderError as e:
            logger.error(f"Image generation failed for user {request.user_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embodiment image: {e}")
            raise

    def generate_avatar_variations(
        self, user_id: UUID, base_embodiment: dict[str, Any], variation_requests: list[str]
    ) -> list[ImageResult]:
        """
        Generate multiple avatar variations for a user.

        Args:
            user_id: User ID
            base_embodiment: Base embodiment characteristics
            variation_requests: List of variation descriptions

        Returns:
            List[ImageResult]: Generated variations
        """
        logger.info(f"Generating {len(variation_requests)} avatar variations for user {user_id}")

        try:
            # Create base prompt from embodiment data
            base_prompt = self.image_service.create_embodiment_prompt(base_embodiment)

            # Generate variations
            results = self.image_service.generate_avatar_variations(
                base_prompt=base_prompt, variations=variation_requests, user_id=user_id
            )

            logger.info(f"Generated {len(results)} avatar variations for user {user_id}")
            return results

        except Exception as e:
            logger.error(f"Failed to generate avatar variations for user {user_id}: {e}")
            raise

    def personalize_embodiment(
        self, user_id: UUID, current_embodiment: dict[str, Any], feedback: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Personalize embodiment based on user feedback.

        Args:
            user_id: User ID
            current_embodiment: Current embodiment characteristics
            feedback: User feedback on embodiment

        Returns:
            Dict: Updated embodiment characteristics
        """
        logger.info(f"Personalizing embodiment for user {user_id}")

        try:
            # Start with current embodiment
            updated_embodiment = current_embodiment.copy()

            # Apply feedback to visual attributes
            if "visual_feedback" in feedback:
                visual_feedback = feedback["visual_feedback"]

                # Update appearance preferences
                if "appearance" not in updated_embodiment:
                    updated_embodiment["appearance"] = {}

                for attribute, preference in visual_feedback.items():
                    if attribute in ["style", "formality", "approachability"]:
                        updated_embodiment["appearance"][attribute] = preference

            # Apply feedback to personality traits
            if "personality_feedback" in feedback:
                personality_feedback = feedback["personality_feedback"]

                if "personality" not in updated_embodiment:
                    updated_embodiment["personality"] = {}

                for trait, value in personality_feedback.items():
                    updated_embodiment["personality"][trait] = value

            # Apply learning preference feedback
            if "learning_feedback" in feedback:
                learning_feedback = feedback["learning_feedback"]

                if "learning_preferences" not in updated_embodiment:
                    updated_embodiment["learning_preferences"] = {}

                for preference, value in learning_feedback.items():
                    updated_embodiment["learning_preferences"][preference] = value

            logger.info(f"Embodiment personalized successfully for user {user_id}")
            return updated_embodiment

        except Exception as e:
            logger.error(f"Failed to personalize embodiment for user {user_id}: {e}")
            raise

    def analyze_embodiment_effectiveness(
        self,
        user_id: UUID,
        embodiment_data: dict[str, Any],
        interaction_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Analyze the effectiveness of an embodiment based on user interactions.

        Args:
            user_id: User ID
            embodiment_data: Current embodiment data
            interaction_history: History of user interactions

        Returns:
            Dict: Analysis results and recommendations
        """
        logger.info(f"Analyzing embodiment effectiveness for user {user_id}")

        try:
            analysis = {
                "user_id": str(user_id),
                "total_interactions": len(interaction_history),
                "engagement_metrics": {},
                "effectiveness_score": 0.0,
                "recommendations": [],
            }

            if not interaction_history:
                analysis["recommendations"].append("Insufficient interaction data for analysis")
                return analysis

            # Calculate engagement metrics
            positive_interactions = sum(
                1
                for interaction in interaction_history
                if interaction.get("sentiment", "neutral") == "positive"
            )

            engagement_rate = (
                positive_interactions / len(interaction_history) if interaction_history else 0
            )
            analysis["engagement_metrics"]["positive_interaction_rate"] = engagement_rate

            # Calculate average session length
            session_lengths = [
                interaction.get("duration", 0) for interaction in interaction_history
            ]
            avg_session_length = (
                sum(session_lengths) / len(session_lengths) if session_lengths else 0
            )
            analysis["engagement_metrics"]["average_session_length"] = avg_session_length

            # Calculate effectiveness score (0-1)
            effectiveness_score = (engagement_rate * 0.6) + (
                min(avg_session_length / 300, 1.0) * 0.4
            )
            analysis["effectiveness_score"] = effectiveness_score

            # Generate recommendations
            if effectiveness_score < 0.3:
                analysis["recommendations"].append("Consider major embodiment redesign")
                analysis["recommendations"].append("Gather more specific user feedback")
            elif effectiveness_score < 0.6:
                analysis["recommendations"].append("Fine-tune personality traits")
                analysis["recommendations"].append("Adjust visual appearance based on preferences")
            else:
                analysis["recommendations"].append("Embodiment is performing well")
                analysis["recommendations"].append("Consider minor optimizations")

            logger.info(
                f"Embodiment analysis completed for user {user_id}, score: {effectiveness_score:.2f}"
            )
            return analysis

        except Exception as e:
            logger.error(f"Failed to analyze embodiment effectiveness for user {user_id}: {e}")
            raise

    def _extract_visual_attributes(self, pald_data: dict[str, Any]) -> dict[str, Any]:
        """Extract visual attributes from PALD data."""
        visual_attributes = {}

        # Extract appearance-related attributes
        if "appearance" in pald_data:
            visual_attributes.update(pald_data["appearance"])

        # Extract context-based visual cues
        if "context" in pald_data:
            context = pald_data["context"]
            if "formality_level" in context:
                visual_attributes["formality"] = context["formality_level"]
            if "subject_area" in context:
                visual_attributes["subject_context"] = context["subject_area"]

        # Set defaults if not specified
        visual_attributes.setdefault("style", "professional")
        visual_attributes.setdefault("approachability", "high")
        visual_attributes.setdefault("age_range", "adult")

        return visual_attributes

    def _extract_personality_traits(self, pald_data: dict[str, Any]) -> dict[str, Any]:
        """Extract personality traits from PALD data."""
        personality_traits = {}

        if "personality" in pald_data:
            personality_traits.update(pald_data["personality"])

        # Extract traits from other sections
        if "interaction_style" in pald_data:
            interaction_style = pald_data["interaction_style"]
            if "communication_style" in interaction_style:
                personality_traits["communication_style"] = interaction_style["communication_style"]
            if "feedback_approach" in interaction_style:
                personality_traits["feedback_approach"] = interaction_style["feedback_approach"]

        # Set defaults
        personality_traits.setdefault("friendliness", "high")
        personality_traits.setdefault("patience", "high")
        personality_traits.setdefault("encouragement", "moderate")

        return personality_traits

    def _extract_learning_preferences(self, pald_data: dict[str, Any]) -> dict[str, Any]:
        """Extract learning preferences from PALD data."""
        learning_preferences = {}

        if "learning_preferences" in pald_data:
            learning_preferences.update(pald_data["learning_preferences"])

        if "pedagogical_approach" in pald_data:
            learning_preferences["approach"] = pald_data["pedagogical_approach"]

        if "difficulty_adaptation" in pald_data:
            learning_preferences["difficulty_adaptation"] = pald_data["difficulty_adaptation"]

        return learning_preferences


# Global embodiment logic instance
_embodiment_logic: EmbodimentLogic | None = None


def get_embodiment_logic() -> EmbodimentLogic:
    """Get the global embodiment logic instance."""
    global _embodiment_logic
    if _embodiment_logic is None:
        _embodiment_logic = EmbodimentLogic()
    return _embodiment_logic


def set_embodiment_logic(logic: EmbodimentLogic) -> None:
    """Set the global embodiment logic instance (useful for testing)."""
    global _embodiment_logic
    _embodiment_logic = logic
