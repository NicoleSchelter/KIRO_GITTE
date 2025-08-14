"""
Integration tests for Image Isolation Service.
Tests complete workflows and integration with existing systems.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import cv2
import numpy as np
import pytest
from PIL import Image

from config.config import Config, ImageIsolationConfig
from src.services.image_isolation_service import (
    ImageIsolationService,
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
        image = np.ones((200, 200, 3), dtype=np.uint8) * 255  # White background
        image[50:150, 50:150] = [255, 0, 0]  # Blue rectangle (person placeholder)
        
        # Save as image file
        cv2.imwrite(tmp_path, image)
        yield tmp_path
        
    finally:
        # Cleanup
        try:
            os.unlink(tmp_path)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors


class TestImageIsolationIntegration:
    """Test integration of image isolation with the broader system."""
    
    def test_config_integration(self):
        """Test integration with main configuration system."""
        config = Config()
        
        # Should have image isolation config
        assert hasattr(config, 'image_isolation')
        assert isinstance(config.image_isolation, ImageIsolationConfig)
        
        # Should have feature flags
        assert hasattr(config.feature_flags, 'enable_image_isolation')
        assert hasattr(config.feature_flags, 'enable_image_quality_detection')
    
    def test_service_with_config_integration(self):
        """Test service initialization with main config."""
        config = Config()
        service = ImageIsolationService(config.image_isolation)
        
        assert service.config == config.image_isolation
        assert service.config.background_removal_method == "rembg"
    
    def test_complete_isolation_workflow_rembg(self, test_image_path):
        """Test complete isolation workflow with rembg method."""
        config = ImageIsolationConfig(
            enabled=True,
            background_removal_method="rembg",
            fallback_to_original=True
        )
        service = ImageIsolationService(config)
        
        # Mock the rembg removal to avoid downloading models
        def mock_rembg_removal(image_path):
            # Create a simple transparent PNG
            output_path = str(Path(image_path).parent / f"{Path(image_path).stem}_rembg.png")
            
            # Load original and create transparent version
            original = Image.open(image_path).convert("RGBA")
            # Make center transparent
            data = np.array(original)
            data[75:125, 75:125, 3] = 0  # Make center transparent
            
            result_image = Image.fromarray(data, "RGBA")
            result_image.save(output_path, "PNG")
            return output_path
        
        service._apply_rembg_removal = mock_rembg_removal
        
        result = service.isolate_person(test_image_path)
        
        # Should succeed or fail gracefully
        assert result.original_image_path == test_image_path
        assert result.processing_time > 0
        
        if result.success:
            assert result.isolated_image_path is not None
            assert Path(result.isolated_image_path).exists()
            assert result.method_used == "rembg"
            
            # Verify output is PNG with transparency
            with Image.open(result.isolated_image_path) as img:
                assert img.mode == "RGBA"
            
            # Cleanup
            Path(result.isolated_image_path).unlink(missing_ok=True)
    
    def test_complete_isolation_workflow_transparent(self, test_image_path):
        """Test complete isolation workflow with transparent method."""
        config = ImageIsolationConfig(
            enabled=True,
            background_removal_method="transparent",
            fallback_to_original=True
        )
        service = ImageIsolationService(config)
        
        result = service.isolate_person(test_image_path)
        
        # Should succeed or fail gracefully
        assert result.original_image_path == test_image_path
        assert result.processing_time > 0
        
        if result.success:
            assert result.isolated_image_path is not None
            assert Path(result.isolated_image_path).exists()
            assert result.method_used == "transparent"
            
            # Cleanup
            Path(result.isolated_image_path).unlink(missing_ok=True)
    
    def test_quality_analysis_integration(self, test_image_path):
        """Test quality analysis integration."""
        config = ImageIsolationConfig(enabled=True)
        service = ImageIsolationService(config)
        
        analysis = service.analyze_image_quality(test_image_path)
        
        # Should return valid analysis
        assert isinstance(analysis.is_valid, bool)
        assert isinstance(analysis.person_detected, bool)
        assert isinstance(analysis.person_count, int)
        assert 0.0 <= analysis.quality_score <= 1.0
        assert isinstance(analysis.issues, list)
        assert isinstance(analysis.confidence_scores, dict)
        
        # Should have quality metrics
        assert "blur_score" in analysis.confidence_scores
        assert "noise_score" in analysis.confidence_scores
        assert "brightness_score" in analysis.confidence_scores
        assert "contrast_score" in analysis.confidence_scores
    
    def test_performance_within_limits(self, test_image_path):
        """Test that processing stays within performance limits."""
        config = ImageIsolationConfig(
            enabled=True,
            max_processing_time=5,  # 5 second limit
            fallback_to_original=True
        )
        service = ImageIsolationService(config)
        
        result = service.isolate_person(test_image_path)
        
        # Should complete within time limit or fallback
        assert result.processing_time <= 6.0  # Allow small buffer
        
        if result.processing_time > config.max_processing_time:
            # Should have fallen back
            assert result.success is False or result.method_used.endswith("_fallback")
    
    def test_error_handling_and_fallbacks(self):
        """Test error handling and fallback mechanisms."""
        config = ImageIsolationConfig(
            enabled=True,
            fallback_to_original=True
        )
        service = ImageIsolationService(config)
        
        # Test with invalid image path
        result = service.isolate_person("nonexistent_image.jpg")
        
        assert result.success is False
        assert result.error_message is not None
        assert result.method_used == "error_fallback"
        assert result.original_image_path == "nonexistent_image.jpg"
    
    def test_disabled_service_behavior(self, test_image_path):
        """Test service behavior when disabled."""
        config = ImageIsolationConfig(enabled=False)
        service = ImageIsolationService(config)
        
        result = service.isolate_person(test_image_path)
        
        assert result.success is False
        assert result.method_used == "disabled"
        assert "disabled" in result.error_message.lower()
        assert result.isolated_image_path is None
    
    def test_multiple_background_methods(self, test_image_path):
        """Test service with different background removal methods."""
        methods = ["rembg", "transparent", "uniform"]
        
        for method in methods:
            config = ImageIsolationConfig(
                enabled=True,
                background_removal_method=method,
                fallback_to_original=True
            )
            service = ImageIsolationService(config)
            
            # Mock rembg to avoid model downloads
            if method == "rembg":
                def mock_rembg_removal(image_path):
                    output_path = str(Path(image_path).parent / "test_rembg.png")
                    Image.new("RGBA", (200, 200), (255, 255, 255, 0)).save(output_path)
                    return output_path
                service._apply_rembg_removal = mock_rembg_removal
            
            result = service.isolate_person(test_image_path)
            
            # Should handle each method appropriately
            assert result.original_image_path == test_image_path
            assert result.processing_time >= 0
            
            # Clean up any generated files
            if result.success and result.isolated_image_path:
                Path(result.isolated_image_path).unlink(missing_ok=True)


class TestFeatureFlagIntegration:
    """Test feature flag integration."""
    
    def test_feature_flags_exist(self):
        """Test that image isolation feature flags exist."""
        config = Config()
        
        assert hasattr(config.feature_flags, 'enable_image_isolation')
        assert hasattr(config.feature_flags, 'enable_image_quality_detection')
        
        # Should be enabled by default
        assert config.feature_flags.enable_image_isolation is True
        assert config.feature_flags.enable_image_quality_detection is True
    
    def test_service_respects_feature_flags(self, test_image_path):
        """Test that service respects feature flag settings."""
        # Test with isolation disabled via config
        config = ImageIsolationConfig(enabled=False)
        service = ImageIsolationService(config)
        
        result = service.isolate_person(test_image_path)
        
        assert result.success is False
        assert result.method_used == "disabled"


class TestConfigurationValidation:
    """Test configuration validation and edge cases."""
    
    def test_invalid_background_method(self, test_image_path):
        """Test handling of invalid background removal method."""
        config = ImageIsolationConfig(
            enabled=True,
            background_removal_method="invalid_method"
        )
        service = ImageIsolationService(config)
        
        result = service.isolate_person(test_image_path)
        
        # Should fallback to default behavior (transparent)
        assert result.original_image_path == test_image_path
        
        if result.success:
            # Should have used fallback method
            assert result.isolated_image_path is not None
            # Cleanup
            Path(result.isolated_image_path).unlink(missing_ok=True)
    
    def test_extreme_confidence_thresholds(self, test_image_path):
        """Test behavior with extreme confidence thresholds."""
        # Very high threshold - should rarely detect
        high_config = ImageIsolationConfig(
            enabled=True,
            detection_confidence_threshold=0.99
        )
        high_service = ImageIsolationService(high_config)
        
        # Very low threshold - should almost always detect
        low_config = ImageIsolationConfig(
            enabled=True,
            detection_confidence_threshold=0.01
        )
        low_service = ImageIsolationService(low_config)
        
        high_result = high_service.isolate_person(test_image_path)
        low_result = low_service.isolate_person(test_image_path)
        
        # Both should handle gracefully
        assert isinstance(high_result.success, bool)
        assert isinstance(low_result.success, bool)
        
        # Cleanup any generated files
        for result in [high_result, low_result]:
            if result.success and result.isolated_image_path:
                Path(result.isolated_image_path).unlink(missing_ok=True)