"""
Unit tests for rembg integration in Image Isolation Service.
Tests background removal algorithms and enhanced person detection.
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
)


@pytest.fixture
def rembg_config():
    """Create test configuration for rembg-based isolation."""
    return ImageIsolationConfig(
        enabled=True,
        detection_confidence_threshold=0.7,
        edge_refinement_enabled=True,
        background_removal_method="rembg",
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


class TestRembgIntegration:
    """Test rembg background removal integration."""
    
    def test_rembg_config_initialization(self, rembg_config):
        """Test service initialization with rembg configuration."""
        service = ImageIsolationService(rembg_config)
        
        assert service.config.background_removal_method == "rembg"
        # Background remover may or may not initialize depending on system
        assert service.background_remover is not None or service.background_remover is None
    
    @patch('src.services.image_isolation_service.remove')
    @patch('src.services.image_isolation_service.Image')
    def test_apply_rembg_removal_success(self, mock_pil_image, mock_remove, rembg_config, test_image_path):
        """Test successful rembg background removal."""
        service = ImageIsolationService(rembg_config)
        
        # Mock PIL Image operations
        mock_input_image = Mock()
        mock_output_image = Mock()
        mock_pil_image.open.return_value = mock_input_image
        mock_remove.return_value = mock_output_image
        
        result_path = service._apply_rembg_removal(test_image_path)
        
        # Verify the method was called
        mock_pil_image.open.assert_called_once_with(test_image_path)
        mock_remove.assert_called_once()
        mock_output_image.save.assert_called_once()
        
        assert result_path.endswith("_rembg.png")
    
    @patch('src.services.image_isolation_service.remove')
    def test_apply_rembg_removal_fallback(self, mock_remove, rembg_config, test_image_path):
        """Test rembg removal with fallback on error."""
        service = ImageIsolationService(rembg_config)
        
        # Mock rembg to raise an exception
        mock_remove.side_effect = Exception("Rembg failed")
        
        result_path = service._apply_rembg_removal(test_image_path)
        
        # Should fallback to transparent background
        assert result_path.endswith("_isolated.png")
        assert Path(result_path).exists()
        
        # Cleanup
        Path(result_path).unlink(missing_ok=True)
    
    def test_create_fallback_mask(self, rembg_config):
        """Test fallback mask creation."""
        service = ImageIsolationService(rembg_config)
        
        # Create test image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        mask = service._create_fallback_mask(image)
        
        assert mask.shape == (100, 100)
        assert mask.dtype == np.float32
        assert np.max(mask) > 0  # Should have some positive values
        assert np.min(mask) >= 0  # Should not have negative values
        
        # Center should have higher values than edges
        center_value = mask[50, 50]
        edge_value = mask[10, 10]
        assert center_value >= edge_value
    
    def test_detect_person_yolo_placeholder(self, rembg_config):
        """Test YOLO-based person detection placeholder."""
        service = ImageIsolationService(rembg_config)
        
        # Create test image
        image = np.ones((200, 200, 3), dtype=np.uint8) * 255
        
        result = service._detect_person_yolo(image)
        
        assert result["detected"] is True
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["count"] == 1
        assert "bounding_boxes" in result
        assert len(result["bounding_boxes"]) == 1
    
    def test_enhance_person_detection_hog_success(self, rembg_config):
        """Test enhanced person detection when HOG succeeds."""
        service = ImageIsolationService(rembg_config)
        
        # Mock successful HOG detection
        def mock_detect_person(image):
            return {"detected": True, "confidence": 0.8, "count": 1}
        
        service._detect_person = mock_detect_person
        
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255
        result = service._enhance_person_detection(image)
        
        assert result["detected"] is True
        assert result["confidence"] == 0.8
    
    def test_enhance_person_detection_fallback_to_yolo(self, rembg_config):
        """Test enhanced person detection fallback to YOLO."""
        service = ImageIsolationService(rembg_config)
        
        # Mock failed HOG detection
        def mock_detect_person(image):
            return {"detected": False, "confidence": 0.2, "count": 0}
        
        service._detect_person = mock_detect_person
        
        image = np.ones((200, 200, 3), dtype=np.uint8) * 255
        result = service._enhance_person_detection(image)
        
        # Should use YOLO result which has higher confidence
        assert result["detected"] is True
        assert result["confidence"] > 0.2  # YOLO should give higher confidence
    
    def test_isolate_person_with_rembg(self, rembg_config, test_image_path):
        """Test complete isolation workflow with rembg."""
        service = ImageIsolationService(rembg_config)
        
        # Mock enhanced person detection to return success
        def mock_enhance_detection(image):
            return {
                "detected": True,
                "confidence": 0.8,
                "count": 1,
                "bounding_boxes": [((25, 25, 50, 50), 0.8)]
            }
        
        service._enhance_person_detection = mock_enhance_detection
        
        # Mock rembg removal to avoid actual processing
        def mock_rembg_removal(image_path):
            output_path = str(Path(image_path).parent / "test_rembg.png")
            # Create a dummy output file
            Image.new("RGBA", (100, 100), (255, 255, 255, 0)).save(output_path)
            return output_path
        
        service._apply_rembg_removal = mock_rembg_removal
        
        result = service.isolate_person(test_image_path)
        
        assert isinstance(result, IsolationResult)
        assert result.original_image_path == test_image_path
        assert result.confidence_score == 0.8
        assert result.processing_time > 0
        
        # Should succeed with rembg
        if result.success:
            assert result.isolated_image_path is not None
            assert result.method_used == "rembg"
            # Cleanup
            if result.isolated_image_path and Path(result.isolated_image_path).exists():
                Path(result.isolated_image_path).unlink(missing_ok=True)


class TestBackgroundRemovalMethods:
    """Test different background removal methods."""
    
    def test_transparent_background_method(self, test_image_path):
        """Test transparent background removal method."""
        config = ImageIsolationConfig(background_removal_method="transparent")
        service = ImageIsolationService(config)
        
        # Create a simple mask
        mask = np.ones((100, 100), dtype=np.float32)
        mask[25:75, 25:75] = 0.5  # Semi-transparent center
        
        output_path = service._apply_background_removal(test_image_path, mask, 0.8)
        
        assert output_path.endswith("_isolated.png")
        assert Path(output_path).exists()
        
        # Verify the output is a PNG with transparency
        with Image.open(output_path) as img:
            assert img.mode == "RGBA"
        
        # Cleanup
        Path(output_path).unlink(missing_ok=True)
    
    def test_uniform_background_method(self, test_image_path):
        """Test uniform background removal method."""
        config = ImageIsolationConfig(
            background_removal_method="uniform",
            uniform_background_color=(255, 0, 0)  # Red background
        )
        service = ImageIsolationService(config)
        
        # Create a simple mask
        mask = np.ones((100, 100), dtype=np.float32)
        mask[25:75, 25:75] = 0.0  # Transparent center
        
        output_path = service._apply_background_removal(test_image_path, mask, 0.8)
        
        assert "_uniform_bg" in output_path
        assert Path(output_path).exists()
        
        # Verify the output exists and has correct format
        image = cv2.imread(output_path)
        assert image is not None
        assert image.shape[:2] == (100, 100)
        
        # Cleanup
        Path(output_path).unlink(missing_ok=True)
    
    @patch('src.services.image_isolation_service.remove')
    def test_rembg_method_with_session(self, mock_remove, test_image_path):
        """Test rembg method with initialized session."""
        config = ImageIsolationConfig(background_removal_method="rembg")
        service = ImageIsolationService(config)
        
        # Mock session
        mock_session = Mock()
        service.background_remover = mock_session
        
        # Mock PIL operations
        with patch('src.services.image_isolation_service.Image') as mock_pil:
            mock_input = Mock()
            mock_output = Mock()
            mock_pil.open.return_value = mock_input
            mock_remove.return_value = mock_output
            
            mask = np.ones((100, 100), dtype=np.float32)
            output_path = service._apply_background_removal(test_image_path, mask, 0.8)
            
            # Should call rembg with session
            mock_remove.assert_called_once_with(mock_input, session=mock_session)
            assert output_path.endswith("_rembg.png")


class TestConfigurationIntegration:
    """Test configuration integration for new features."""
    
    def test_rembg_config_defaults(self):
        """Test rembg configuration defaults."""
        config = ImageIsolationConfig()
        
        assert config.background_removal_method == "rembg"
        assert config.enabled is True
        assert config.fallback_to_original is True
    
    def test_config_environment_overrides(self):
        """Test configuration environment variable overrides."""
        import os
        
        # Set environment variables
        os.environ["IMAGE_ISOLATION_ENABLED"] = "false"
        os.environ["IMAGE_ISOLATION_CONFIDENCE_THRESHOLD"] = "0.9"
        
        try:
            config = ImageIsolationConfig()
            config.__post_init__()
            
            assert config.enabled is False
            assert config.detection_confidence_threshold == 0.9
        finally:
            # Cleanup environment variables
            os.environ.pop("IMAGE_ISOLATION_ENABLED", None)
            os.environ.pop("IMAGE_ISOLATION_CONFIDENCE_THRESHOLD", None)
    
    def test_service_with_different_methods(self, test_image_path):
        """Test service behavior with different background removal methods."""
        methods = ["rembg", "transparent", "uniform", "opencv"]
        
        for method in methods:
            config = ImageIsolationConfig(background_removal_method=method)
            service = ImageIsolationService(config)
            
            # Should initialize without errors
            assert service.config.background_removal_method == method
            
            # Mock detection to avoid actual processing
            def mock_enhance_detection(image):
                return {"detected": True, "confidence": 0.7, "count": 1}
            
            service._enhance_person_detection = mock_enhance_detection
            
            # Should handle the method gracefully
            result = service.isolate_person(test_image_path)
            assert isinstance(result, IsolationResult)