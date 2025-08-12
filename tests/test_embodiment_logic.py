"""
Tests for embodiment logic layer.
Tests embodiment creation, personalization, and image generation workflows.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.data.models import User
from src.data.schemas import PALDValidationResult
from src.logic.embodiment import EmbodimentLogic, EmbodimentProfile, EmbodimentRequest
from src.services.image_provider import ImageResult
from src.services.image_service import ImageService
from src.services.pald_service import PALDSchemaService


class TestEmbodimentProfile:
    """Test embodiment profile data class."""

    def test_embodiment_profile_creation(self):
        """Test creating embodiment profile."""
        user_id = uuid4()
        visual_attrs = {"style": "modern", "gender": "neutral"}
        personality_traits = {"friendliness": "high"}
        learning_prefs = {"approach": "interactive"}

        profile = EmbodimentProfile(
            user_id=user_id,
            visual_attributes=visual_attrs,
            personality_traits=personality_traits,
            learning_preferences=learning_prefs,
        )

        assert profile.user_id == user_id
        assert profile.visual_attributes == visual_attrs
        assert profile.personality_traits == personality_traits
        assert profile.learning_preferences == learning_prefs
        assert profile.generated_images == []

    def test_embodiment_profile_with_images(self):
        """Test embodiment profile with generated images."""
        user_id = uuid4()
        images = ["image1.png", "image2.png"]

        profile = EmbodimentProfile(
            user_id=user_id,
            visual_attributes={},
            personality_traits={},
            learning_preferences={},
            generated_images=images,
        )

        assert profile.generated_images == images


class TestEmbodimentRequest:
    """Test embodiment request data class."""

    def test_embodiment_request_creation(self):
        """Test creating embodiment request."""
        user_id = uuid4()
        pald_data = {"appearance": {"style": "casual"}}
        custom_prompt = "A casual teacher"
        variations = ["smiling", "serious"]
        parameters = {"width": 256}

        request = EmbodimentRequest(
            user_id=user_id,
            pald_data=pald_data,
            custom_prompt=custom_prompt,
            variations=variations,
            parameters=parameters,
        )

        assert request.user_id == user_id
        assert request.pald_data == pald_data
        assert request.custom_prompt == custom_prompt
        assert request.variations == variations
        assert request.parameters == parameters

    def test_embodiment_request_defaults(self):
        """Test embodiment request with defaults."""
        user_id = uuid4()
        pald_data = {"test": "data"}

        request = EmbodimentRequest(user_id=user_id, pald_data=pald_data)

        assert request.custom_prompt is None
        assert request.variations is None
        assert request.parameters is None


class TestEmbodimentLogic:
    """Test embodiment logic."""

    def test_embodiment_logic_creation(self):
        """Test creating embodiment logic with services."""
        mock_image_service = Mock(spec=ImageService)
        mock_pald_service = Mock(spec=PALDSchemaService)

        logic = EmbodimentLogic(image_service=mock_image_service, pald_service=mock_pald_service)

        assert logic.image_service == mock_image_service
        assert logic.pald_service == mock_pald_service

    def test_embodiment_logic_default_services(self):
        """Test creating embodiment logic with default services."""
        with patch("src.logic.embodiment.get_image_service") as mock_get_image:
            mock_image_service = Mock(spec=ImageService)
            mock_get_image.return_value = mock_image_service

            logic = EmbodimentLogic()

            assert logic.image_service == mock_image_service
            assert logic.pald_service is None

    def test_create_embodiment_profile_success(self):
        """Test successful embodiment profile creation."""
        # Setup mocks
        mock_image_service = Mock(spec=ImageService)
        mock_pald_service = Mock(spec=PALDSchemaService)
        mock_pald_service.validate_pald_data.return_value = PALDValidationResult(
            is_valid=True, errors=[], warnings=[], coverage_percentage=85.0
        )

        logic = EmbodimentLogic(image_service=mock_image_service, pald_service=mock_pald_service)

        # Create test data
        user = Mock(spec=User)
        user.id = uuid4()

        pald_data = {
            "appearance": {"gender": "female", "age_range": "adult", "style": "professional"},
            "personality": {"approachability": "high", "formality": "moderate"},
            "interaction_style": {
                "communication_style": "friendly",
                "feedback_approach": "encouraging",
            },
            "learning_preferences": {"difficulty_level": "adaptive"},
            "pedagogical_approach": "constructivist",
        }

        preferences = {"visual": {"color_preference": "blue"}, "personality": {"humor": "moderate"}}

        # Create profile
        profile = logic.create_embodiment_profile(user, pald_data, preferences)

        # Verify profile
        assert profile.user_id == user.id
        assert profile.visual_attributes["gender"] == "female"
        assert profile.visual_attributes["style"] == "professional"
        assert profile.visual_attributes["color_preference"] == "blue"  # From preferences
        assert profile.personality_traits["approachability"] == "high"
        assert profile.personality_traits["communication_style"] == "friendly"
        assert profile.personality_traits["humor"] == "moderate"  # From preferences
        assert profile.learning_preferences["difficulty_level"] == "adaptive"
        assert profile.learning_preferences["approach"] == "constructivist"

        # Verify PALD validation was called
        mock_pald_service.validate_pald_data.assert_called_once_with(pald_data)

    def test_create_embodiment_profile_validation_warnings(self):
        """Test embodiment profile creation with PALD validation warnings."""
        mock_image_service = Mock(spec=ImageService)
        mock_pald_service = Mock(spec=PALDSchemaService)
        mock_pald_service.validate_pald_data.return_value = PALDValidationResult(
            is_valid=False,
            errors=["Missing required field"],
            warnings=["Deprecated field"],
            coverage_percentage=60.0,
        )

        logic = EmbodimentLogic(image_service=mock_image_service, pald_service=mock_pald_service)

        user = Mock(spec=User)
        user.id = uuid4()
        pald_data = {"incomplete": "data"}

        # Should still create profile despite validation issues
        profile = logic.create_embodiment_profile(user, pald_data)

        assert profile.user_id == user.id
        # Should have defaults applied
        assert profile.visual_attributes["style"] == "professional"
        assert profile.personality_traits["friendliness"] == "high"

    def test_create_embodiment_profile_exception(self):
        """Test embodiment profile creation with exception."""
        mock_image_service = Mock(spec=ImageService)
        mock_pald_service = Mock(spec=PALDSchemaService)
        mock_pald_service.validate_pald_data.side_effect = Exception("Validation error")

        logic = EmbodimentLogic(image_service=mock_image_service, pald_service=mock_pald_service)

        user = Mock(spec=User)
        user.id = uuid4()

        with pytest.raises(Exception):
            logic.create_embodiment_profile(user, {})

    def test_generate_embodiment_image_with_custom_prompt(self):
        """Test embodiment image generation with custom prompt."""
        mock_image_service = Mock(spec=ImageService)
        mock_image_result = ImageResult(
            image_path="test_image.png", generation_time=2.5, model_used="stable-diffusion"
        )
        mock_image_service.generate_embodiment_image.return_value = mock_image_result

        logic = EmbodimentLogic(image_service=mock_image_service)

        user_id = uuid4()
        request = EmbodimentRequest(
            user_id=user_id,
            pald_data={},
            custom_prompt="A friendly robot teacher",
            parameters={"width": 256},
        )

        result = logic.generate_embodiment_image(request)

        assert result == mock_image_result
        mock_image_service.generate_embodiment_image.assert_called_once_with(
            prompt="A friendly robot teacher", user_id=user_id, parameters={"width": 256}
        )

    def test_generate_embodiment_image_from_pald(self):
        """Test embodiment image generation from PALD data."""
        mock_image_service = Mock(spec=ImageService)
        mock_image_service.create_embodiment_prompt.return_value = "Generated prompt from PALD"
        mock_image_result = ImageResult(
            image_path="test_image.png", generation_time=3.0, model_used="stable-diffusion"
        )
        mock_image_service.generate_embodiment_image.return_value = mock_image_result

        logic = EmbodimentLogic(image_service=mock_image_service)

        user_id = uuid4()
        request = EmbodimentRequest(user_id=user_id, pald_data={"appearance": {"style": "modern"}})

        result = logic.generate_embodiment_image(request)

        assert result == mock_image_result
        mock_image_service.create_embodiment_prompt.assert_called_once_with(
            {"appearance": {"style": "modern"}}
        )
        mock_image_service.generate_embodiment_image.assert_called_once_with(
            prompt="Generated prompt from PALD", user_id=user_id, parameters=None
        )
