"""
Tests for Image Quality Detection Service.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import cv2
import numpy as np
import pytest
from PIL import Image

from src.services.image_quality_detector import (
    ImageQualityDetector,
    QualityDetectionConfig,
    FaultyImageReason,
    DetectionResult,
    BatchProcessingResult
)


class TestImageQualityDetector(unittest.TestCase):
    """Test cases for ImageQualityDetector."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = QualityDetectionConfig(
            enabled=True,
            min_person_confidence=0.7,
            max_people_allowed=1,
            min_quality_score=0.6,
            blur_threshold=0.3,
            noise_threshold=0.1
        )
        self.detector = ImageQualityDetector(self.config)
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary files
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_image(self, filename: str, size: tuple = (512, 512), color: tuple = (128, 128, 128)) -> str:
        """Create a test image file."""
        image_path = self.temp_path / filename
        
        # Create a simple test image
        image = Image.new('RGB', size, color)
        image.save(image_path)
        
        return str(image_path)
    
    def _create_corrupted_image(self, filename: str) -> str:
        """Create a corrupted image file."""
        image_path = self.temp_path / filename
        
        # Write invalid image data
        with open(image_path, 'wb') as f:
            f.write(b'invalid image data')
        
        return str(image_path)
    
    def test_detector_initialization(self):
        """Test detector initialization."""
        self.assertIsInstance(self.detector, ImageQualityDetector)
        self.assertEqual(self.detector.config, self.config)
    
    def test_disabled_detector(self):
        """Test detector when disabled."""
        disabled_config = QualityDetectionConfig(enabled=False)
        disabled_detector = ImageQualityDetector(disabled_config)
        
        image_path = self._create_test_image("test.jpg")
        result = disabled_detector.detect_faulty_image(image_path)
        
        self.assertFalse(result.is_faulty)
        self.assertEqual(result.reasons, [])
        self.assertEqual(result.confidence_score, 1.0)
        self.assertIn("disabled", result.recommendations[0])
    
    def test_corrupted_image_detection(self):
        """Test detection of corrupted images."""
        corrupted_path = self._create_corrupted_image("corrupted.jpg")
        result = self.detector.detect_faulty_image(corrupted_path)
        
        self.assertTrue(result.is_faulty)
        self.assertIn(FaultyImageReason.CORRUPTED_IMAGE, result.reasons)
        self.assertEqual(result.person_count, 0)
        self.assertIn("Regenerate", result.recommendations[0])
    
    def test_nonexistent_image(self):
        """Test handling of nonexistent image files."""
        nonexistent_path = str(self.temp_path / "nonexistent.jpg")
        result = self.detector.detect_faulty_image(nonexistent_path)
        
        self.assertTrue(result.is_faulty)
        self.assertIn(FaultyImageReason.CORRUPTED_IMAGE, result.reasons)
        self.assertIn("not found", result.details)
    
    def test_invalid_format_detection(self):
        """Test detection of invalid image formats."""
        # Create a text file with image extension
        invalid_path = self.temp_path / "invalid.xyz"
        with open(invalid_path, 'w') as f:
            f.write("not an image")
        
        result = self.detector.detect_faulty_image(str(invalid_path))
        
        self.assertTrue(result.is_faulty)
        self.assertIn(FaultyImageReason.INVALID_FORMAT, result.reasons)
    
    def test_small_image_detection(self):
        """Test detection of images that are too small."""
        small_image_path = self._create_test_image("small.jpg", size=(100, 100))
        result = self.detector.detect_faulty_image(small_image_path)
        
        self.assertTrue(result.is_faulty)
        self.assertIn(FaultyImageReason.POOR_QUALITY, result.reasons)
        self.assertIn("too small", result.details)
    
    def test_large_image_detection(self):
        """Test detection of images that are too large."""
        # Temporarily modify config for this test
        original_max_size = self.config.max_image_size
        self.config.max_image_size = (300, 300)
        
        large_image_path = self._create_test_image("large.jpg", size=(500, 500))
        result = self.detector.detect_faulty_image(large_image_path)
        
        self.assertTrue(result.is_faulty)
        self.assertIn(FaultyImageReason.POOR_QUALITY, result.reasons)
        self.assertIn("too large", result.details)
        
        # Restore original config
        self.config.max_image_size = original_max_size
    
    @patch('cv2.imread')
    def test_person_detection_no_person(self, mock_imread):
        """Test person detection when no person is detected."""
        # Mock image loading
        mock_image = np.zeros((512, 512, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image
        
        # Mock HOG detector to return no detections
        with patch.object(self.detector, 'person_classifier') as mock_classifier:
            mock_classifier.detectMultiScale.return_value = ([], [])
            
            image_path = self._create_test_image("no_person.jpg")
            result = self.detector.detect_faulty_image(image_path)
            
            self.assertTrue(result.is_faulty)
            self.assertIn(FaultyImageReason.NO_PERSON_DETECTED, result.reasons)
            self.assertEqual(result.person_count, 0)
    
    @patch('cv2.imread')
    def test_person_detection_multiple_people(self, mock_imread):
        """Test person detection when multiple people are detected."""
        # Mock image loading
        mock_image = np.zeros((512, 512, 3), dtype=np.uint8)
        mock_imread.return_value = mock_image
        
        # Mock HOG detector to return multiple detections
        with patch.object(self.detector, 'person_classifier') as mock_classifier:
            # Simulate detecting 2 people with high confidence
            mock_rects = [np.array([100, 100, 50, 100]), np.array([300, 100, 50, 100])]
            mock_weights = [0.9, 0.85]
            mock_classifier.detectMultiScale.return_value = (mock_rects, mock_weights)
            
            image_path = self._create_test_image("multiple_people.jpg")
            result = self.detector.detect_faulty_image(image_path)
            
            self.assertTrue(result.is_faulty)
            self.assertIn(FaultyImageReason.MULTIPLE_PEOPLE_DETECTED, result.reasons)
            self.assertEqual(result.person_count, 2)
    
    def test_person_detection_success(self):
        """Test successful person detection."""
        image_path = self._create_test_image("good_person.jpg")
        
        # Mock all the detection methods to return good results
        with patch.object(self.detector, 'detect_people') as mock_detect_people:
            mock_detect_people.return_value = {
                "person_detected": True,
                "person_count": 1,
                "confidence": 0.9,
                "bounding_boxes": [],
                "metrics": {"person_detection_confidence": 0.9, "detected_person_count": 1}
            }
            
            with patch.object(self.detector, 'assess_image_quality') as mock_quality:
                mock_quality.return_value = {
                    "blur_score": 0.8,
                    "noise_score": 0.05,
                    "brightness_score": 0.5,
                    "contrast_score": 0.7,
                    "sharpness_score": 0.8,
                    "overall_score": 0.75,
                    "metrics": {
                        "blur_score": 0.8,
                        "noise_score": 0.05,
                        "brightness_score": 0.5,
                        "contrast_score": 0.7,
                        "sharpness_score": 0.8,
                        "overall_quality_score": 0.75
                    }
                }
                
                with patch.object(self.detector, 'validate_subject_type') as mock_subject:
                    mock_subject.return_value = {
                        "is_person": True,
                        "confidence": 0.9,
                        "detected_objects": ["person"],
                        "metrics": {"subject_validation_confidence": 0.9, "composition_score": 0.8}
                    }
                    
                    result = self.detector.detect_faulty_image(image_path)
                    
                    self.assertFalse(result.is_faulty)
                    self.assertEqual(result.person_count, 1)
                    self.assertGreater(result.confidence_score, 0.6)
    
    def test_detect_people_method(self):
        """Test the detect_people method specifically."""
        image_path = self._create_test_image("test_person.jpg")
        
        with patch.object(self.detector, 'person_classifier') as mock_classifier:
            # Mock successful detection
            mock_rects = [np.array([100, 100, 50, 100])]
            mock_weights = [0.9]
            mock_classifier.detectMultiScale.return_value = (mock_rects, mock_weights)
            
            result = self.detector.detect_people(image_path)
            
            self.assertTrue(result["person_detected"])
            self.assertEqual(result["person_count"], 1)
            self.assertEqual(result["confidence"], 0.9)
            self.assertEqual(len(result["bounding_boxes"]), 1)
    
    def test_detect_people_fallback(self):
        """Test fallback person detection when classifier is None."""
        # Set classifier to None to trigger fallback
        self.detector.person_classifier = None
        
        image_path = self._create_test_image("fallback_test.jpg")
        
        with patch('cv2.imread') as mock_imread:
            # Create a mock image with some vertical structures
            mock_image = np.random.randint(0, 255, (512, 512, 3), dtype=np.uint8)
            mock_imread.return_value = mock_image
            
            result = self.detector.detect_people(image_path)
            
            # Should use fallback detection
            self.assertIsInstance(result["person_detected"], bool)
            self.assertIsInstance(result["person_count"], int)
            self.assertIsInstance(result["confidence"], float)
    
    def test_assess_image_quality_method(self):
        """Test the assess_image_quality method."""
        image_path = self._create_test_image("quality_test.jpg")
        
        result = self.detector.assess_image_quality(image_path)
        
        # Check that all expected metrics are present
        expected_keys = ["blur_score", "noise_score", "brightness_score", "contrast_score", "overall_score"]
        for key in expected_keys:
            self.assertIn(key, result)
            self.assertIsInstance(result[key], float)
            self.assertGreaterEqual(result[key], 0.0)
            self.assertLessEqual(result[key], 1.0)
    
    def test_validate_subject_type_method(self):
        """Test the validate_subject_type method."""
        image_path = self._create_test_image("subject_test.jpg")
        
        # Mock person detection
        with patch.object(self.detector, 'detect_people') as mock_detect:
            mock_detect.return_value = {
                "person_detected": True,
                "confidence": 0.9,
                "person_count": 1
            }
            
            result = self.detector.validate_subject_type(image_path)
            
            self.assertIsInstance(result["is_person"], bool)
            self.assertIsInstance(result["confidence"], float)
            self.assertIn("metrics", result)
    
    def test_batch_processing_analysis(self):
        """Test batch processing analysis."""
        # Create multiple test images
        image_paths = []
        for i in range(5):
            path = self._create_test_image(f"batch_{i}.jpg")
            image_paths.append(path)
        
        # Mock detection results - mix of good and bad images
        mock_results = [
            DetectionResult(
                is_faulty=False, reasons=[], confidence_score=0.8,
                quality_metrics={}, person_count=1, processing_time=0.1,
                recommendations=[]
            ),
            DetectionResult(
                is_faulty=True, reasons=[FaultyImageReason.NO_PERSON_DETECTED],
                confidence_score=0.2, quality_metrics={}, person_count=0,
                processing_time=0.1, recommendations=[]
            ),
            DetectionResult(
                is_faulty=True, reasons=[FaultyImageReason.POOR_QUALITY],
                confidence_score=0.3, quality_metrics={}, person_count=1,
                processing_time=0.1, recommendations=[]
            ),
            DetectionResult(
                is_faulty=False, reasons=[], confidence_score=0.9,
                quality_metrics={}, person_count=1, processing_time=0.1,
                recommendations=[]
            ),
            DetectionResult(
                is_faulty=True, reasons=[FaultyImageReason.NO_PERSON_DETECTED],
                confidence_score=0.1, quality_metrics={}, person_count=0,
                processing_time=0.1, recommendations=[]
            )
        ]
        
        with patch.object(self.detector, 'detect_faulty_image', side_effect=mock_results):
            result = self.detector.analyze_batch_processing(image_paths)
            
            self.assertEqual(result.total_images, 5)
            self.assertEqual(result.faulty_images, 3)
            self.assertEqual(result.faulty_percentage, 60.0)
            self.assertIn(FaultyImageReason.NO_PERSON_DETECTED, result.common_issues)
            self.assertIsInstance(result.should_regenerate, bool)
    
    def test_batch_processing_empty_list(self):
        """Test batch processing with empty image list."""
        result = self.detector.analyze_batch_processing([])
        
        self.assertEqual(result.total_images, 0)
        self.assertEqual(result.faulty_images, 0)
        self.assertEqual(result.faulty_percentage, 0.0)
        self.assertFalse(result.should_regenerate)
    
    def test_batch_processing_high_failure_rate(self):
        """Test batch processing with high failure rate triggers regeneration."""
        image_paths = [self._create_test_image(f"fail_{i}.jpg") for i in range(3)]
        
        # Mock all images as faulty
        mock_results = [
            DetectionResult(
                is_faulty=True, reasons=[FaultyImageReason.NO_PERSON_DETECTED],
                confidence_score=0.1, quality_metrics={}, person_count=0,
                processing_time=0.1, recommendations=[]
            ) for _ in range(3)
        ]
        
        with patch.object(self.detector, 'detect_faulty_image', side_effect=mock_results):
            result = self.detector.analyze_batch_processing(image_paths)
            
            self.assertTrue(result.should_regenerate)
            self.assertEqual(result.faulty_percentage, 100.0)
    
    def test_quality_metrics_calculation(self):
        """Test quality metrics calculation with real image."""
        # Create a test image with known characteristics
        image_path = self._create_test_image("metrics_test.jpg", size=(256, 256))
        
        # Load the image and add some noise for testing
        with patch('cv2.imread') as mock_imread:
            # Create image with some texture for realistic metrics
            test_image = np.random.randint(100, 200, (256, 256, 3), dtype=np.uint8)
            mock_imread.return_value = test_image
            
            result = self.detector.assess_image_quality(image_path)
            
            # Verify metrics are reasonable
            self.assertGreater(result["blur_score"], 0.0)
            self.assertLess(result["noise_score"], 1.0)
            self.assertGreater(result["brightness_score"], 0.0)
            self.assertLess(result["brightness_score"], 1.0)
    
    def test_confidence_score_calculation(self):
        """Test confidence score calculation with various scenarios."""
        # Test with no issues
        quality_metrics = {"overall_quality_score": 0.8}
        reasons = []
        score = self.detector._calculate_confidence_score(quality_metrics, reasons)
        self.assertEqual(score, 0.8)
        
        # Test with major issues
        reasons = [FaultyImageReason.NO_PERSON_DETECTED]
        score = self.detector._calculate_confidence_score(quality_metrics, reasons)
        self.assertEqual(score, 0.4)  # 0.8 - 0.4 penalty
        
        # Test with multiple minor issues
        reasons = [FaultyImageReason.POOR_BRIGHTNESS, FaultyImageReason.LOW_CONTRAST]
        score = self.detector._calculate_confidence_score(quality_metrics, reasons)
        self.assertAlmostEqual(score, 0.6, places=5)  # 0.8 - 0.2 penalty
        
        # Test minimum score
        reasons = [FaultyImageReason.NO_PERSON_DETECTED, FaultyImageReason.CORRUPTED_IMAGE]
        score = self.detector._calculate_confidence_score(quality_metrics, reasons)
        self.assertEqual(score, 0.0)  # Can't go below 0
    
    def test_error_handling_in_detection(self):
        """Test error handling during detection process."""
        image_path = self._create_test_image("error_test.jpg")
        
        # Mock cv2.imread to raise an exception
        with patch('cv2.imread', side_effect=Exception("Mock error")):
            result = self.detector.detect_faulty_image(image_path)
            
            self.assertTrue(result.is_faulty)
            self.assertIn(FaultyImageReason.CORRUPTED_IMAGE, result.reasons)
            self.assertIn("Mock error", result.details)
    
    def test_processing_time_tracking(self):
        """Test that processing time is tracked correctly."""
        image_path = self._create_test_image("timing_test.jpg")
        
        result = self.detector.detect_faulty_image(image_path)
        
        self.assertGreater(result.processing_time, 0.0)
        self.assertIsInstance(result.processing_time, float)
    
    def test_recommendations_generation(self):
        """Test that appropriate recommendations are generated."""
        image_path = self._create_test_image("recommendations_test.jpg")
        
        # Mock detection to return specific issues
        with patch.object(self.detector, 'detect_people') as mock_detect:
            mock_detect.return_value = {
                "person_detected": False,
                "person_count": 0,
                "confidence": 0.1,
                "metrics": {}
            }
            
            result = self.detector.detect_faulty_image(image_path)
            
            self.assertTrue(result.is_faulty)
            self.assertGreater(len(result.recommendations), 0)
            self.assertIn("person", result.recommendations[0].lower())


if __name__ == '__main__':
    unittest.main()