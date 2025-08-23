"""
Unit tests for Image Generation Service.
Tests data persistence, Stable Diffusion integration, and image description services.
"""

import os
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.orm import Session

from src.data.models import GeneratedImage
from src.exceptions import DatabaseError, ValidationError
from src.services.image_generation_service import ImageGenerationService


class TestImageGenerationService:
    """Test cases for ImageGenerationService class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        mock_session = Mock(spec=Session)
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.rollback = Mock()
        mock_session.query = Mock()
        return mock_session

    @pytest.fixture
    def image_service(self, mock_db_session):
        """Create ImageGenerationService instance with mocked dependencies."""
        return ImageGenerationService(mock_db_session)

    @pytest.fixture
    def sample_generation_params(self):
        """Sample generation parameters for testing."""
        return {
            "model": "stable-diffusion-v1-5",
            "width": 512,
            "height": 512,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
            "device": "cpu"
        }

    def test_store_generated_image_success(self, image_service, mock_db_session, sample_generation_params):
        """Test successful storage of generated image."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        image_path = "generated_images/test_image.png"
        prompt = "friendly teacher with glasses"
        pald_source_id = uuid4()
        
        result = image_service.store_generated_image(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            image_path=image_path,
            prompt=prompt,
            generation_parameters=sample_generation_params,
            pald_source_id=pald_source_id,
        )
        
        assert isinstance(result, GeneratedImage)
        assert result.pseudonym_id == pseudonym_id
        assert result.session_id == session_id
        assert result.image_path == image_path
        assert result.prompt == prompt
        assert result.pald_source_id == pald_source_id
        assert result.generation_parameters == sample_generation_params
        
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_store_generated_image_empty_path(self, image_service, sample_generation_params):
        """Test storage with empty image path."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        with pytest.raises(ValidationError, match="Image path cannot be empty"):
            image_service.store_generated_image(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_path="",
                prompt="test prompt",
                generation_parameters=sample_generation_params,
            )

    def test_store_generated_image_empty_prompt(self, image_service, sample_generation_params):
        """Test storage with empty prompt."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        with pytest.raises(ValidationError, match="Prompt cannot be empty"):
            image_service.store_generated_image(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_path="test.png",
                prompt="",
                generation_parameters=sample_generation_params,
            )

    def test_store_generated_image_empty_parameters(self, image_service):
        """Test storage with empty generation parameters."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        with pytest.raises(ValidationError, match="Generation parameters cannot be empty"):
            image_service.store_generated_image(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_path="test.png",
                prompt="test prompt",
                generation_parameters={},
            )

    def test_store_generated_image_database_error(self, image_service, mock_db_session, sample_generation_params):
        """Test storage with database error."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock database error
        mock_db_session.commit.side_effect = Exception("Database connection failed")
        
        with pytest.raises(DatabaseError, match="Failed to store generated image"):
            image_service.store_generated_image(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_path="test.png",
                prompt="test prompt",
                generation_parameters=sample_generation_params,
            )
        
        mock_db_session.rollback.assert_called_once()

    def test_get_generated_images_success(self, image_service, mock_db_session):
        """Test successful retrieval of generated images."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock query result
        mock_images = [Mock(spec=GeneratedImage), Mock(spec=GeneratedImage)]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_images
        mock_db_session.query.return_value = mock_query
        
        result = image_service.get_generated_images(pseudonym_id, session_id, limit=10)
        
        assert result == mock_images
        mock_db_session.query.assert_called_once_with(GeneratedImage)

    def test_get_generated_images_no_session_filter(self, image_service, mock_db_session):
        """Test retrieval without session ID filter."""
        pseudonym_id = uuid4()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query
        
        result = image_service.get_generated_images(pseudonym_id)
        
        assert result == []
        # Should only filter by pseudonym_id, not session_id
        assert mock_query.filter.call_count == 1

    def test_get_image_by_id_found(self, image_service, mock_db_session):
        """Test retrieval of image by ID when found."""
        image_id = uuid4()
        mock_image = Mock(spec=GeneratedImage)
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_image
        mock_db_session.query.return_value = mock_query
        
        result = image_service.get_image_by_id(image_id)
        
        assert result == mock_image

    def test_get_image_by_id_not_found(self, image_service, mock_db_session):
        """Test retrieval of image by ID when not found."""
        image_id = uuid4()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db_session.query.return_value = mock_query
        
        result = image_service.get_image_by_id(image_id)
        
        assert result is None

    @patch('os.path.exists')
    @patch('os.remove')
    def test_delete_generated_image_success(self, mock_remove, mock_exists, image_service, mock_db_session):
        """Test successful deletion of generated image."""
        image_id = uuid4()
        mock_image = Mock(spec=GeneratedImage)
        mock_image.image_path = "test_image.png"
        
        # Mock file exists
        mock_exists.return_value = True
        
        # Mock get_image_by_id
        image_service.get_image_by_id = Mock(return_value=mock_image)
        
        result = image_service.delete_generated_image(image_id)
        
        assert result is True
        mock_remove.assert_called_once_with("test_image.png")
        mock_db_session.delete.assert_called_once_with(mock_image)
        mock_db_session.commit.assert_called_once()

    def test_delete_generated_image_not_found(self, image_service):
        """Test deletion of non-existent image."""
        image_id = uuid4()
        
        # Mock get_image_by_id to return None
        image_service.get_image_by_id = Mock(return_value=None)
        
        result = image_service.delete_generated_image(image_id)
        
        assert result is False

    @patch('os.path.exists')
    def test_delete_generated_image_file_not_found(self, mock_exists, image_service, mock_db_session):
        """Test deletion when image file doesn't exist."""
        image_id = uuid4()
        mock_image = Mock(spec=GeneratedImage)
        mock_image.image_path = "nonexistent.png"
        
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        # Mock get_image_by_id
        image_service.get_image_by_id = Mock(return_value=mock_image)
        
        result = image_service.delete_generated_image(image_id)
        
        assert result is True
        # Should still delete database record even if file doesn't exist
        mock_db_session.delete.assert_called_once_with(mock_image)
        mock_db_session.commit.assert_called_once()

    def test_call_stable_diffusion_success(self, image_service):
        """Test successful Stable Diffusion call."""
        prompt = "friendly teacher with glasses"
        parameters = {
            "width": 512,
            "height": 512,
            "num_inference_steps": 20,
            "guidance_scale": 7.5
        }
        
        result = image_service.call_stable_diffusion(prompt, parameters)
        
        assert isinstance(result, dict)
        assert "image_path" in result
        assert "prompt" in result
        assert "parameters" in result
        assert "generation_time_ms" in result
        assert "model_used" in result
        assert result["prompt"] == prompt
        assert result["parameters"] == parameters

    def test_call_stable_diffusion_empty_prompt(self, image_service):
        """Test Stable Diffusion call with empty prompt."""
        parameters = {"width": 512, "height": 512, "num_inference_steps": 20, "guidance_scale": 7.5}
        
        with pytest.raises(ValidationError, match="Prompt cannot be empty"):
            image_service.call_stable_diffusion("", parameters)

    def test_call_stable_diffusion_missing_parameters(self, image_service):
        """Test Stable Diffusion call with missing required parameters."""
        prompt = "test prompt"
        parameters = {"width": 512}  # Missing required parameters
        
        with pytest.raises(ValidationError, match="Missing required parameter"):
            image_service.call_stable_diffusion(prompt, parameters)

    @patch('os.path.exists')
    def test_call_image_description_llm_success(self, mock_exists, image_service):
        """Test successful image description LLM call."""
        image_path = "test_image.png"
        description_prompt = "Describe this image focusing on embodiment aspects"
        
        # Mock file exists
        mock_exists.return_value = True
        
        result = image_service.call_image_description_llm(image_path, description_prompt)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "pedagogical agent" in result.lower()

    def test_call_image_description_llm_empty_path(self, image_service):
        """Test image description call with empty image path."""
        description_prompt = "Describe this image"
        
        with pytest.raises(ValidationError, match="Image path cannot be empty"):
            image_service.call_image_description_llm("", description_prompt)

    def test_call_image_description_llm_empty_prompt(self, image_service):
        """Test image description call with empty prompt."""
        image_path = "test_image.png"
        
        with pytest.raises(ValidationError, match="Description prompt cannot be empty"):
            image_service.call_image_description_llm(image_path, "")

    @patch('os.path.exists')
    def test_call_image_description_llm_file_not_found(self, mock_exists, image_service):
        """Test image description call with non-existent file."""
        image_path = "nonexistent.png"
        description_prompt = "Describe this image"
        
        # Mock file doesn't exist
        mock_exists.return_value = False
        
        with pytest.raises(ValidationError, match="Image file not found"):
            image_service.call_image_description_llm(image_path, description_prompt)

    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('os.path.dirname')
    def test_ensure_image_directory_creates_directory(self, mock_dirname, mock_exists, mock_makedirs, image_service):
        """Test directory creation for image path."""
        image_path = "generated_images/subfolder/test.png"
        directory = "generated_images/subfolder"
        
        mock_dirname.return_value = directory
        mock_exists.return_value = False
        
        image_service.ensure_image_directory(image_path)
        
        mock_makedirs.assert_called_once_with(directory, exist_ok=True)

    @patch('os.path.exists')
    @patch('os.path.dirname')
    def test_ensure_image_directory_already_exists(self, mock_dirname, mock_exists, image_service):
        """Test directory creation when directory already exists."""
        image_path = "generated_images/test.png"
        directory = "generated_images"
        
        mock_dirname.return_value = directory
        mock_exists.return_value = True
        
        # Should not raise any exception
        image_service.ensure_image_directory(image_path)

    def test_get_image_statistics_success(self, image_service, mock_db_session):
        """Test successful retrieval of image statistics."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Mock query results
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 10
        mock_db_session.query.return_value = mock_query
        
        result = image_service.get_image_statistics(pseudonym_id, session_id)
        
        assert isinstance(result, dict)
        assert "total_images" in result
        assert "images_with_pald_source" in result
        assert "recent_images_24h" in result
        assert "images_without_pald_source" in result

    def test_get_image_statistics_no_session_filter(self, image_service, mock_db_session):
        """Test image statistics without session filter."""
        pseudonym_id = uuid4()
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        mock_db_session.query.return_value = mock_query
        
        result = image_service.get_image_statistics(pseudonym_id)
        
        assert isinstance(result, dict)
        assert result["total_images"] == 5

    def test_mock_stable_diffusion_call(self, image_service):
        """Test the mock Stable Diffusion implementation."""
        prompt = "friendly teacher"
        parameters = {"model": "test-model", "width": 512, "height": 512}
        
        result = image_service._mock_stable_diffusion_call(prompt, parameters)
        
        assert isinstance(result, dict)
        assert "image_path" in result
        assert "prompt" in result
        assert "parameters" in result
        assert "generation_time_ms" in result
        assert "model_used" in result
        assert "seed" in result
        assert result["prompt"] == prompt
        assert result["parameters"] == parameters

    def test_mock_image_description_call(self, image_service):
        """Test the mock image description implementation."""
        image_path = "test_image.png"
        description_prompt = "Describe this image"
        
        result = image_service._mock_image_description_call(image_path, description_prompt)
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert "pedagogical agent" in result.lower()
        assert "test_image.png" in result


class TestImageGenerationServiceIntegration:
    """Integration tests for ImageGenerationService with realistic scenarios."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a more realistic mock database session."""
        mock_session = Mock(spec=Session)
        
        # Mock successful operations by default
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.rollback = Mock()
        
        return mock_session

    @pytest.fixture
    def image_service(self, mock_db_session):
        """Create ImageGenerationService with realistic mock."""
        return ImageGenerationService(mock_db_session)

    def test_full_image_storage_and_retrieval_workflow(self, image_service, mock_db_session):
        """Test complete workflow of storing and retrieving images."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Store an image
        generation_params = {
            "model": "stable-diffusion-v1-5",
            "width": 512,
            "height": 512,
            "num_inference_steps": 20,
            "guidance_scale": 7.5
        }
        
        stored_image = image_service.store_generated_image(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            image_path="generated_images/test.png",
            prompt="friendly teacher with glasses",
            generation_parameters=generation_params,
        )
        
        assert isinstance(stored_image, GeneratedImage)
        
        # Mock retrieval
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [stored_image]
        mock_db_session.query.return_value = mock_query
        
        retrieved_images = image_service.get_generated_images(pseudonym_id, session_id)
        
        assert len(retrieved_images) == 1
        assert retrieved_images[0] == stored_image

    @patch('os.path.exists')
    def test_stable_diffusion_integration_workflow(self, mock_exists, image_service):
        """Test Stable Diffusion integration workflow."""
        # Mock file existence for the generated image
        mock_exists.return_value = True
        
        prompt = "A friendly pedagogical agent with professional appearance, modern style, wearing glasses"
        parameters = {
            "width": 512,
            "height": 512,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
            "model": "stable-diffusion-v1-5"
        }
        
        # Test generation
        generation_result = image_service.call_stable_diffusion(prompt, parameters)
        
        assert generation_result["prompt"] == prompt
        assert "generated_" in generation_result["image_path"]
        assert generation_result["generation_time_ms"] > 0
        
        # Test description
        description = image_service.call_image_description_llm(
            generation_result["image_path"],
            "Describe the pedagogical agent in this image, focusing on embodiment aspects"
        )
        
        assert len(description) > 0
        assert "pedagogical" in description.lower()

    def test_error_handling_workflow(self, image_service, mock_db_session):
        """Test error handling in various scenarios."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        # Test validation errors
        with pytest.raises(ValidationError):
            image_service.store_generated_image(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_path="",  # Empty path should fail
                prompt="test",
                generation_parameters={"model": "test"},
            )
        
        # Test database errors
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseError):
            image_service.store_generated_image(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_path="test.png",
                prompt="test prompt",
                generation_parameters={"model": "test", "width": 512, "height": 512, "num_inference_steps": 20, "guidance_scale": 7.5},
            )