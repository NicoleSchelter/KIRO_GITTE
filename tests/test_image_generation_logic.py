"""
Unit tests for Image Generation Logic.
Tests PALD-to-image pipeline, image description, and consistency checking.
"""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

from src.logic.image_generation_logic import (
    ImageGenerationLogic,
    ImageGenerationResult,
    ImageDescriptionResult,
    ConsistencyLoopResult,
)
from src.services.llm_service import LLMResponse


class TestImageGenerationLogic:
    """Test cases for ImageGenerationLogic class."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        mock_service = Mock()
        mock_service.generate_response.return_value = LLMResponse(
            text='{"pald_data": {"global_design_level": {"overall_appearance": "friendly"}}, "confidence": 0.8}',
            model="llama3",
            latency_ms=1000,
            tokens_used={"prompt": 100, "completion": 50},
        )
        return mock_service

    @pytest.fixture
    def image_logic(self, mock_llm_service):
        """Create ImageGenerationLogic instance with mocked dependencies."""
        return ImageGenerationLogic(mock_llm_service)

    @pytest.fixture
    def sample_pald_data(self):
        """Sample PALD data for testing."""
        return {
            "global_design_level": {
                "overall_appearance": "friendly pedagogical agent",
                "style": "modern professional",
                "theme": "educational"
            },
            "middle_design_level": {
                "physical_attributes": "human-like appearance",
                "clothing": "business casual attire",
                "accessories": "glasses"
            },
            "detailed_level": {
                "facial_features": "warm smile, expressive eyes",
                "hair": "short brown hair",
                "colors": "blue and white color scheme"
            }
        }

    def test_compress_pald_to_prompt_basic(self, image_logic, sample_pald_data):
        """Test basic PALD compression to prompt."""
        prompt = image_logic.compress_pald_to_prompt(sample_pald_data)
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "friendly" in prompt.lower()
        assert "professional" in prompt.lower()
        
        # Check token limit (approximately 77 words)
        words = prompt.split()
        assert len(words) <= 77

    def test_compress_pald_to_prompt_empty_data(self, image_logic):
        """Test PALD compression with empty data."""
        prompt = image_logic.compress_pald_to_prompt({})
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        # Should return default prompt
        assert "pedagogical agent" in prompt.lower()

    def test_compress_pald_to_prompt_partial_data(self, image_logic):
        """Test PALD compression with partial data."""
        partial_pald = {
            "global_design_level": {
                "overall_appearance": "friendly teacher"
            }
        }
        
        prompt = image_logic.compress_pald_to_prompt(partial_pald)
        
        assert isinstance(prompt, str)
        assert "friendly teacher" in prompt.lower()

    def test_compress_pald_to_prompt_caching(self, image_logic, sample_pald_data):
        """Test that PALD compression results are cached."""
        prompt1 = image_logic.compress_pald_to_prompt(sample_pald_data)
        prompt2 = image_logic.compress_pald_to_prompt(sample_pald_data)
        
        assert prompt1 == prompt2
        # Check cache was used
        cache_key = f"pald_prompt_{hash(str(sample_pald_data))}"
        assert cache_key in image_logic._prompt_cache

    def test_generate_image_from_pald_success(self, image_logic, sample_pald_data):
        """Test successful image generation from PALD."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        result = image_logic.generate_image_from_pald(
            pseudonym_id, session_id, sample_pald_data
        )
        
        assert isinstance(result, ImageGenerationResult)
        assert result.success is True
        assert result.image_id is not None
        assert result.image_path is not None
        assert len(result.prompt_used) > 0
        assert result.generation_parameters is not None
        assert result.generation_time_ms > 0
        assert result.error_message is None

    def test_generate_image_from_pald_empty_prompt(self, image_logic):
        """Test image generation with empty PALD data."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock compress_pald_to_prompt to return empty string
        image_logic.compress_pald_to_prompt = Mock(return_value="")
        
        result = image_logic.generate_image_from_pald(
            pseudonym_id, session_id, {}
        )
        
        assert isinstance(result, ImageGenerationResult)
        assert result.success is False
        assert result.error_message is not None
        assert "empty" in result.error_message.lower()

    def test_describe_generated_image_success(self, image_logic, mock_llm_service):
        """Test successful image description generation."""
        image_path = "test_image.png"
        
        # Mock LLM response for description
        mock_llm_service.generate_response.return_value = LLMResponse(
            text="A friendly pedagogical agent with professional appearance",
            model="llava",
            latency_ms=2000,
            tokens_used={"prompt": 200, "completion": 100},
        )
        
        result = image_logic.describe_generated_image(image_path)
        
        assert isinstance(result, ImageDescriptionResult)
        assert result.success is True
        assert len(result.description) > 0
        assert result.processing_time_ms > 0
        assert result.error_message is None

    def test_describe_generated_image_with_embodiment_focus(self, image_logic, mock_llm_service):
        """Test image description with embodiment focus."""
        image_path = "test_image.png"
        
        result = image_logic.describe_generated_image(image_path, focus_on_embodiment=True)
        
        # Verify the first call (image description) included embodiment-specific instructions
        first_call_args = mock_llm_service.generate_response.call_args_list[0]
        prompt = first_call_args[1]["prompt"]
        assert "embodiment" in prompt.lower()
        assert "physical characteristics" in prompt.lower()

    def test_extract_pald_from_description_success(self, image_logic, mock_llm_service):
        """Test PALD extraction from image description."""
        description = "A friendly teacher with brown hair and glasses"
        
        # Mock LLM response with valid JSON
        mock_response = {
            "pald_data": {
                "global_design_level": {"overall_appearance": "friendly teacher"},
                "detailed_level": {"hair": "brown hair", "accessories": "glasses"}
            },
            "confidence": 0.9
        }
        mock_llm_service.generate_response.return_value = LLMResponse(
            text=json.dumps(mock_response),
            model="llama3",
            latency_ms=1500,
            tokens_used={"prompt": 150, "completion": 75},
        )
        
        result = image_logic._extract_pald_from_description(description)
        
        assert "pald_data" in result
        assert "confidence" in result
        assert result["confidence"] == 0.9
        assert "global_design_level" in result["pald_data"]

    def test_extract_pald_from_description_invalid_json(self, image_logic, mock_llm_service):
        """Test PALD extraction with invalid JSON response."""
        description = "A friendly teacher"
        
        # Mock LLM response with invalid JSON
        mock_llm_service.generate_response.return_value = LLMResponse(
            text="This is not valid JSON",
            model="llama3",
            latency_ms=1000,
            tokens_used={"prompt": 100, "completion": 50},
        )
        
        result = image_logic._extract_pald_from_description(description)
        
        assert result["pald_data"] == {}
        assert result["confidence"] == 0.0

    def test_calculate_pald_consistency_identical(self, image_logic):
        """Test consistency calculation with identical PALDs."""
        pald1 = {"global_design_level": {"overall_appearance": "friendly"}}
        pald2 = {"global_design_level": {"overall_appearance": "friendly"}}
        
        score = image_logic._calculate_pald_consistency(pald1, pald2)
        
        assert score == 1.0

    def test_calculate_pald_consistency_empty(self, image_logic):
        """Test consistency calculation with empty PALDs."""
        score1 = image_logic._calculate_pald_consistency({}, {})
        score2 = image_logic._calculate_pald_consistency({}, {"key": "value"})
        
        assert score1 == 1.0  # Both empty
        assert score2 == 0.0  # One empty, one not

    def test_calculate_pald_consistency_partial_match(self, image_logic):
        """Test consistency calculation with partial matches."""
        pald1 = {
            "global_design_level": {"overall_appearance": "friendly teacher"},
            "detailed_level": {"hair": "brown"}
        }
        pald2 = {
            "global_design_level": {"overall_appearance": "friendly educator"},
            "detailed_level": {"hair": "brown"}
        }
        
        score = image_logic._calculate_pald_consistency(pald1, pald2)
        
        assert 0.0 < score < 1.0  # Partial match

    def test_calculate_level_similarity_strings(self, image_logic):
        """Test level similarity calculation for string values."""
        level1 = {"appearance": "friendly teacher with glasses"}
        level2 = {"appearance": "friendly educator with glasses"}
        
        similarity = image_logic._calculate_level_similarity(level1, level2)
        
        assert 0.0 < similarity < 1.0  # Partial match due to word overlap

    def test_calculate_level_similarity_identical_dicts(self, image_logic):
        """Test level similarity with identical dictionaries."""
        level1 = {"appearance": "friendly", "style": "professional"}
        level2 = {"appearance": "friendly", "style": "professional"}
        
        similarity = image_logic._calculate_level_similarity(level1, level2)
        
        assert similarity == 1.0

    def test_refine_pald_for_next_iteration_low_consistency(self, image_logic):
        """Test PALD refinement with low consistency score."""
        current_pald = {"global_design_level": {"overall_appearance": "teacher"}}
        description_pald = {
            "global_design_level": {"style": "professional"},
            "detailed_level": {"hair": "brown"}
        }
        
        refined = image_logic._refine_pald_for_next_iteration(
            current_pald, description_pald, 0.2
        )
        
        # Should incorporate elements from description_pald
        assert "global_design_level" in refined
        assert "style" in refined["global_design_level"]
        assert "detailed_level" in refined

    def test_refine_pald_for_next_iteration_high_consistency(self, image_logic):
        """Test PALD refinement with high consistency score."""
        current_pald = {"global_design_level": {"overall_appearance": "teacher"}}
        description_pald = {"global_design_level": {"style": "professional"}}
        
        refined = image_logic._refine_pald_for_next_iteration(
            current_pald, description_pald, 0.8
        )
        
        # Should keep current PALD mostly unchanged
        assert refined == current_pald

    def test_run_consistency_loop_immediate_success(self, image_logic, sample_pald_data):
        """Test consistency loop that succeeds immediately."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock high consistency score
        image_logic._calculate_pald_consistency = Mock(return_value=0.9)
        
        result = image_logic.run_consistency_loop(
            pseudonym_id, session_id, sample_pald_data, max_iterations=3
        )
        
        assert isinstance(result, ConsistencyLoopResult)
        assert result.consistency_achieved is True
        assert result.iterations_performed == 1
        assert result.final_consistency_score == 0.9
        assert result.final_image_id is not None

    def test_run_consistency_loop_max_iterations(self, image_logic, sample_pald_data):
        """Test consistency loop that reaches max iterations."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock low consistency score (never achieves threshold)
        image_logic._calculate_pald_consistency = Mock(return_value=0.3)
        
        result = image_logic.run_consistency_loop(
            pseudonym_id, session_id, sample_pald_data, max_iterations=2
        )
        
        assert isinstance(result, ConsistencyLoopResult)
        assert result.consistency_achieved is False
        assert result.iterations_performed == 2
        assert result.final_consistency_score == 0.3

    def test_run_consistency_loop_generation_failure(self, image_logic, sample_pald_data):
        """Test consistency loop with image generation failure."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock generation failure
        image_logic.generate_image_from_pald = Mock(
            return_value=ImageGenerationResult(
                success=False,
                image_id=None,
                image_path=None,
                prompt_used="test",
                generation_parameters={},
                generation_time_ms=1000,
                error_message="Generation failed"
            )
        )
        
        result = image_logic.run_consistency_loop(
            pseudonym_id, session_id, sample_pald_data, max_iterations=3
        )
        
        assert isinstance(result, ConsistencyLoopResult)
        assert result.consistency_achieved is False
        assert result.iterations_performed == 1
        assert result.final_image_id is None

    def test_compress_text_within_limit(self, image_logic):
        """Test text compression within word limit."""
        text = "friendly professional teacher"
        compressed = image_logic._compress_text(text, 5)
        
        assert compressed == text  # Should be unchanged

    def test_compress_text_exceeds_limit(self, image_logic):
        """Test text compression that exceeds word limit."""
        text = "friendly professional teacher with glasses and brown hair"
        compressed = image_logic._compress_text(text, 3)
        
        words = compressed.split()
        assert len(words) == 3
        assert compressed == "friendly professional teacher"

    def test_compress_text_empty(self, image_logic):
        """Test text compression with empty input."""
        compressed = image_logic._compress_text("", 5)
        assert compressed == ""

    def test_prepare_generation_parameters(self, image_logic):
        """Test generation parameters preparation."""
        params = image_logic._prepare_generation_parameters()
        
        assert isinstance(params, dict)
        assert "model" in params
        assert "width" in params
        assert "height" in params
        assert "num_inference_steps" in params
        assert "guidance_scale" in params
        assert "device" in params

    def test_create_image_description_prompt_embodiment_focus(self, image_logic):
        """Test image description prompt creation with embodiment focus."""
        image_path = "test.png"
        prompt = image_logic._create_image_description_prompt(image_path, True)
        
        assert "embodiment" in prompt.lower()
        assert "physical characteristics" in prompt.lower()
        assert "appearance" in prompt.lower()

    def test_create_image_description_prompt_general(self, image_logic):
        """Test image description prompt creation without embodiment focus."""
        image_path = "test.png"
        prompt = image_logic._create_image_description_prompt(image_path, False)
        
        assert "general description" in prompt.lower()
        assert "subjects and objects" in prompt.lower()


class TestImageGenerationLogicIntegration:
    """Integration tests for ImageGenerationLogic with real-like scenarios."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a more realistic mock LLM service."""
        mock_service = Mock()
        
        def mock_generate_response(prompt, model=None, parameters=None):
            # Return different responses based on the prompt content
            if "extract PALD" in prompt.lower():
                return LLMResponse(
                    text='{"pald_data": {"global_design_level": {"overall_appearance": "professional educator"}}, "confidence": 0.85}',
                    model="llama3",
                    latency_ms=1200,
                    tokens_used={"prompt": 120, "completion": 60},
                )
            else:
                return LLMResponse(
                    text="A professional educator with a warm, approachable appearance. The character has modern styling suitable for educational contexts.",
                    model="llava",
                    latency_ms=2500,
                    tokens_used={"prompt": 200, "completion": 150},
                )
        
        mock_service.generate_response.side_effect = mock_generate_response
        return mock_service

    @pytest.fixture
    def image_logic(self, mock_llm_service):
        """Create ImageGenerationLogic with realistic mock."""
        return ImageGenerationLogic(mock_llm_service)

    def test_full_image_generation_pipeline(self, image_logic):
        """Test the complete image generation pipeline."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        pald_data = {
            "global_design_level": {
                "overall_appearance": "friendly teacher",
                "style": "professional modern"
            },
            "detailed_level": {
                "hair": "short brown hair",
                "colors": "blue and white"
            }
        }
        
        # Test image generation
        generation_result = image_logic.generate_image_from_pald(
            pseudonym_id, session_id, pald_data
        )
        
        assert generation_result.success is True
        assert generation_result.image_path is not None
        
        # Test image description
        description_result = image_logic.describe_generated_image(
            generation_result.image_path
        )
        
        assert description_result.success is True
        assert len(description_result.description) > 0

    def test_consistency_loop_realistic_scenario(self, image_logic):
        """Test consistency loop with realistic PALD data and responses."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        input_pald = {
            "global_design_level": {
                "overall_appearance": "friendly professional educator",
                "style": "modern approachable"
            },
            "middle_design_level": {
                "clothing": "business casual attire"
            },
            "detailed_level": {
                "facial_features": "warm smile, kind eyes",
                "hair": "medium length brown hair"
            }
        }
        
        result = image_logic.run_consistency_loop(
            pseudonym_id, session_id, input_pald, max_iterations=2
        )
        
        assert isinstance(result, ConsistencyLoopResult)
        assert result.iterations_performed > 0
        assert result.total_processing_time_ms > 0
        assert "iterations" in result.loop_metadata
        assert "consistency_scores" in result.loop_metadata