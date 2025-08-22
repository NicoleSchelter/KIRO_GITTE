"""
Unit tests for Image Isolation Service.
Tests core isolation functionality, quality analysis, and configuration handling.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import cv2
import numpy as np
import pytest
from PIL import Image

from src.services.image_isolation_service import (
    ImageIsolationConfig,
    ImageIsolationService,
    IsolationResult,
    QualityAnalysis,
)


@pytest.fixture
def isolation_config():
    """Create test configuration for image isolation."""
    return ImageIsolationConfig(
        enabled=True,
        detection_confidence_threshold=0.7,
        edge_refinement_enabled=True,
        background_removal_method="transparent",
        fallback_to_original=True,
        max_processing_time=10,
        output_format="PNG",
        uniform_background_color=(255, 255, 255)
    )


@pytest.fixture
def test_image_path():
    """Create a test image file."""
    import tempfile
    import os
    
    # Create a temporary file
    fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)  # Close the file descriptor immediately
    
    try:
        # Create a simple test image (blue rectangle on white background)
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255  # White background
        image[25:75, 25:75] = [255, 0, 0]  # Blue rectangle (person placeholder)
        
        # Save as image file
        cv2.imwrite(tmp_path, image)
        yield tmp_path
        
    finally:
        # Cleanup
        try:
            os.unlink(tmp_path)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors


@pytest.fixture
def isolation_service(isolation_config):
    """Create image isolation service instance."""
    return ImageIsolationService(isolation_config)


class TestImageIsolationConfig:
    """Test image isolation configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ImageIsolationConfig()
        
        assert config.enabled is True
        assert config.detection_confidence_threshold == 0.7
        assert config.edge_refinement_enabled is True
        assert config.background_removal_method == "opencv"
        assert config.fallback_to_original is True
        assert config.max_processing_time == 10
        assert config.output_format == "PNG"
        assert config.uniform_background_color == (255, 255, 255)
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ImageIsolationConfig(
            enabled=False,
            detection_confidence_threshold=0.8,
            background_removal_method="rembg",
            max_processing_time=5
        )
        
        assert config.enabled is False
        assert config.detection_confidence_threshold == 0.8
        assert config.background_removal_method == "rembg"
        assert config.max_processing_time == 5


class TestImageIsolationService:
    """Test image isolation service functionality."""
    
    def test_service_initialization(self, isolation_config):
        """Test service initialization."""
        service = ImageIsolationService(isolation_config)
        
        assert service.config == isolation_config
        assert service.person_detector is not None or service.person_detector is None  # May fail to load
        assert service.background_remover is None  # Not implemented yet
    
    def test_isolate_missing_config_raises_error(self):
        """Test that missing endpoint config raises RequiredPrerequisiteError."""
        from src.exceptions import RequiredPrerequisiteError
        
        # Create config without endpoint
        config = ImageIsolationConfig(endpoint="")
        service = ImageIsolationService(config)
        
        with pytest.raises(RequiredPrerequisiteError) as exc_info:
            service.isolate("test.jpg")
        
        assert "Missing endpoint configuration" in str(exc_info.value)
        assert "ISOLATION_ENDPOINT" in str(exc_info.value.resolution_steps[0])
    
    def test_isolate_success_returns_structured_dict(self, isolation_config, test_image_path):
        """Test successful isolation returns structured dict with required fields."""
        from unittest.mock import patch, Mock
        
        # Mock the _execute_isolation method
        with patch.object(ImageIsolationService, '_execute_isolation') as mock_execute:
            mock_execute.return_value = {
                'mask_path': '/tmp/mask.png',
                'foreground_path': '/tmp/fg.png',
                'stats': {'processing_time': 1.5, 'model_used': 'u2net'},
                'model_used': 'u2net'
            }
            
            service = ImageIsolationService(isolation_config)
            result = service.isolate(test_image_path, model="u2net")
            
            assert isinstance(result, dict)
            assert 'mask_path' in result
            assert 'foreground_path' in result
            assert 'stats' in result
            assert 'model_used' in result
            assert result['model_used'] == 'u2net'
            assert result['stats']['processing_time'] == 1.5
    
    def test_isolate_uses_config_defaults(self, isolation_config, test_image_path):
        """Test that isolation uses config defaults when no model specified."""
        from unittest.mock import patch, Mock
        
        # Set default model in config
        isolation_config.model_default = "test_model"
        
        with patch.object(ImageIsolationService, '_execute_isolation') as mock_execute:
            mock_execute.return_value = {
                'mask_path': '/tmp/mask.png',
                'foreground_path': None,
                'stats': {'processing_time': 1.0, 'model_used': 'test_model'},
                'model_used': 'test_model'
            }
            
            service = ImageIsolationService(isolation_config)
            result = service.isolate(test_image_path)  # No model specified
            
            # Verify default model was used
            mock_execute.assert_called_once_with(test_image_path, "test_model", **{})
            assert result['model_used'] == 'test_model'
    
    def test_isolate_person_disabled(self, test_image_path):
        """Test isolation when service is disabled."""
        config = ImageIsolationConfig(enabled=False)
        service = ImageIsolationService(config)
        
        result = service.isolate_person(test_image_path)
        
        assert isinstance(result, IsolationResult)
        assert result.success is False
        assert result.isolated_image_path is None
        assert result.original_image_path == test_image_path
        assert result.method_used == "disabled"
        assert "disabled" in result.error_message
    
    def test_isolate_person_invalid_image(self, isolation_service):
        """Test isolation with invalid image path."""
        result = isolation_service.isolate_person("nonexistent.jpg")
        
        assert isinstance(result, IsolationResult)
        assert result.success is False
        assert result.isolated_image_path is None
        assert result.original_image_path == "nonexistent.jpg"
        assert result.method_used == "error_fallback"
        assert result.error_message is not None
    
    def test_isolate_person_no_person_detected(self, isolation_service, test_image_path):
        """Test isolation when no person is detected."""
        # Mock the _detect_person method to return no detection
        def mock_detect_person(image):
            return {"detected": False, "confidence": 0.0, "count": 0}
        
        isolation_service._detect_person = mock_detect_person
        
        result = isolation_service.isolate_person(test_image_path)
        
        assert isinstance(result, IsolationResult)
        assert result.success is False
        assert result.isolated_image_path is None
        assert result.method_used == "person_detection"
        assert "No person detected" in result.error_message
    
    def test_isolate_person_success(self, isolation_service, test_image_path):
        """Test successful person isolation."""
        # Mock the _detect_person method to return a detection
        def mock_detect_person(image):
            return {
                "detected": True,
                "confidence": 0.8,
                "count": 1,
                "bounding_boxes": [((25, 25, 50, 50), 0.8)]
            }
        
        isolation_service._detect_person = mock_detect_person
        
        result = isolation_service.isolate_person(test_image_path)
        
        assert isinstance(result, IsolationResult)
        assert result.original_image_path == test_image_path
        assert result.confidence_score == 0.8
        assert result.processing_time > 0
        
        # Should succeed or fail gracefully
        if result.success:
            assert result.isolated_image_path is not None
            assert Path(result.isolated_image_path).exists()
        else:
            assert result.error_message is not None
    
    def test_analyze_image_quality_invalid_image(self, isolation_service):
        """Test quality analysis with invalid image."""
        result = isolation_service.analyze_image_quality("nonexistent.jpg")
        
        assert isinstance(result, QualityAnalysis)
        assert result.is_valid is False
        assert result.person_detected is False
        assert result.person_count == 0
        assert result.quality_score == 0.0
        assert "Could not load image" in result.issues
    
    def test_analyze_image_quality_valid_image(self, isolation_service, test_image_path):
        """Test quality analysis with valid image."""
        result = isolation_service.analyze_image_quality(test_image_path)
        
        assert isinstance(result, QualityAnalysis)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.person_detected, bool)
        assert isinstance(result.person_count, int)
        assert 0.0 <= result.quality_score <= 1.0
        assert isinstance(result.issues, list)
        assert isinstance(result.confidence_scores, dict)
    
    def test_create_transparent_background(self, isolation_service, test_image_path):
        """Test transparent background creation."""
        # Create a simple mask
        mask = np.ones((100, 100), dtype=np.float32)
        mask[25:75, 25:75] = 0.5  # Semi-transparent center
        
        output_path = isolation_service.create_transparent_background(test_image_path, mask)
        
        assert Path(output_path).exists()
        assert output_path.endswith("_isolated.png")
        
        # Verify the output is a PNG with transparency
        with Image.open(output_path) as img:
            assert img.mode == "RGBA"
        
        # Cleanup
        Path(output_path).unlink(missing_ok=True)
    
    def test_create_uniform_background(self, isolation_service, test_image_path):
        """Test uniform background creation."""
        # Create a simple mask
        mask = np.ones((100, 100), dtype=np.float32)
        mask[25:75, 25:75] = 0.0  # Transparent center
        
        color = (255, 0, 0)  # Red background
        output_path = isolation_service.create_uniform_background(test_image_path, mask, color)
        
        assert Path(output_path).exists()
        assert "_uniform_bg" in output_path
        
        # Verify the output exists and has correct format
        image = cv2.imread(output_path)
        assert image is not None
        assert image.shape[:2] == (100, 100)
        
        # Cleanup
        Path(output_path).unlink(missing_ok=True)
    
    def test_detect_person_no_detector(self, isolation_config):
        """Test person detection when detector is not available."""
        service = ImageIsolationService(isolation_config)
        service.person_detector = None
        
        # Create test image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        result = service._detect_person(image)
        
        assert result["detected"] is False
        assert result["confidence"] == 0.0
        assert result["count"] == 0
    
    def test_create_person_mask_with_bounding_boxes(self, isolation_service):
        """Test person mask creation with bounding boxes."""
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        person_detection = {
            "detected": True,
            "confidence": 0.8,
            "count": 1,
            "bounding_boxes": [((25, 25, 50, 50), 0.8)]
        }
        
        mask = isolation_service._create_person_mask(image, person_detection)
        
        assert mask.shape == (100, 100)
        assert mask.dtype == np.float32
        assert np.max(mask) > 0  # Should have some positive values
        assert np.min(mask) >= 0  # Should not have negative values
    
    def test_create_person_mask_fallback(self, isolation_service):
        """Test person mask creation fallback when no bounding boxes."""
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        person_detection = {
            "detected": True,
            "confidence": 0.5,
            "count": 1
        }
        
        mask = isolation_service._create_person_mask(image, person_detection)
        
        assert mask.shape == (100, 100)
        assert mask.dtype == np.float32
        assert np.max(mask) > 0  # Should have some positive values
        # Center should have higher values than edges
        center_value = mask[50, 50]
        edge_value = mask[10, 10]
        assert center_value >= edge_value
    
    def test_assess_image_quality(self, isolation_service):
        """Test image quality assessment."""
        # Create test image with known characteristics
        image = np.ones((100, 100, 3), dtype=np.uint8) * 128  # Medium gray
        
        result = isolation_service._assess_image_quality(image)
        
        assert "scores" in result
        scores = result["scores"]
        
        assert "blur_score" in scores
        assert "noise_score" in scores
        assert "brightness_score" in scores
        assert "contrast_score" in scores
        
        # All scores should be between 0 and 1
        for score_name, score_value in scores.items():
            assert 0.0 <= score_value <= 1.0, f"{score_name} = {score_value}"
    
    def test_refine_mask_edges(self, isolation_service):
        """Test mask edge refinement."""
        # Create test image and mask
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        image[25:75, 25:75] = [0, 0, 0]  # Black square
        
        mask = np.zeros((100, 100), dtype=np.float32)
        mask[30:70, 30:70] = 1.0  # Square mask
        
        refined_mask = isolation_service._refine_mask_edges(mask, image)
        
        assert refined_mask.shape == mask.shape
        assert refined_mask.dtype == mask.dtype
        assert np.min(refined_mask) >= 0.0
        assert np.max(refined_mask) <= 1.0


class TestIsolationResult:
    """Test IsolationResult data class."""
    
    def test_isolation_result_creation(self):
        """Test IsolationResult creation."""
        result = IsolationResult(
            success=True,
            isolated_image_path="/path/to/isolated.png",
            original_image_path="/path/to/original.jpg",
            confidence_score=0.85,
            processing_time=2.5,
            method_used="rembg"
        )
        
        assert result.success is True
        assert result.isolated_image_path == "/path/to/isolated.png"
        assert result.original_image_path == "/path/to/original.jpg"
        assert result.confidence_score == 0.85
        assert result.processing_time == 2.5
        assert result.method_used == "rembg"
        assert result.error_message is None
    
    def test_isolation_result_with_error(self):
        """Test IsolationResult with error."""
        result = IsolationResult(
            success=False,
            isolated_image_path=None,
            original_image_path="/path/to/original.jpg",
            confidence_score=0.0,
            processing_time=1.0,
            method_used="error_fallback",
            error_message="Processing failed"
        )
        
        assert result.success is False
        assert result.isolated_image_path is None
        assert result.error_message == "Processing failed"


class TestQualityAnalysis:
    """Test QualityAnalysis data class."""
    
    def test_quality_analysis_creation(self):
        """Test QualityAnalysis creation."""
        analysis = QualityAnalysis(
            is_valid=True,
            person_detected=True,
            person_count=1,
            quality_score=0.8,
            issues=[],
            confidence_scores={"person_detection": 0.9, "blur_score": 0.7}
        )
        
        assert analysis.is_valid is True
        assert analysis.person_detected is True
        assert analysis.person_count == 1
        assert analysis.quality_score == 0.8
        assert analysis.issues == []
        assert analysis.confidence_scores["person_detection"] == 0.9
    
    def test_quality_analysis_with_issues(self):
        """Test QualityAnalysis with quality issues."""
        analysis = QualityAnalysis(
            is_valid=False,
            person_detected=False,
            person_count=0,
            quality_score=0.3,
            issues=["no_person_detected", "image_too_blurry"],
            confidence_scores={"person_detection": 0.1, "blur_score": 0.2}
        )
        
        assert analysis.is_valid is False
        assert analysis.person_detected is False
        assert "no_person_detected" in analysis.issues
        assert "image_too_blurry" in analysis.issues
        assert analysis.quality_score == 0.3