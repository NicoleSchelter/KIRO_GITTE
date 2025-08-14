"""
Tests for Image Correction Logic.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

import pytest
from PIL import Image

from src.logic.image_correction import (
    ImageCorrectionLogic,
    CorrectionResult,
    LearningData
)


class TestImageCorrectionLogic(unittest.TestCase):
    """Test cases for ImageCorrectionLogic."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock services
        self.mock_image_service = Mock()
        self.mock_isolation_service = Mock()
        self.mock_audit_service = Mock()
        
        # Create logic instance
        self.logic = ImageCorrectionLogic(
            image_service=self.mock_image_service,
            isolation_service=self.mock_isolation_service,
            audit_service=self.mock_audit_service
        )
        
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Test user ID
        self.user_id = uuid4()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_image(self, filename: str, size: tuple = (512, 512)) -> str:
        """Create a test image file."""
        image_path = self.temp_path / filename
        image = Image.new('RGB', size, (128, 128, 128))
        image.save(image_path)
        return str(image_path)
    
    def test_process_accept_decision(self):
        """Test processing accept decision with processed image."""
        original_path = self._create_test_image("original.jpg")
        processed_path = self._create_test_image("processed.png")
        
        correction_data = {
            "decision": "accept",
            "original_image_path": original_path,
            "processed_image_path": processed_path
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(result.final_image_path, processed_path)
        self.assertEqual(result.processing_method, "accept_processed")
        self.assertTrue(result.user_feedback_recorded)
    
    def test_process_accept_decision_fallback(self):
        """Test processing accept decision with fallback to original."""
        original_path = self._create_test_image("original.jpg")
        
        correction_data = {
            "decision": "accept",
            "original_image_path": original_path,
            "processed_image_path": "nonexistent.png"
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(result.final_image_path, original_path)
        self.assertEqual(result.processing_method, "accept_fallback")
        self.assertIn("not available", result.error_message)
    
    def test_process_original_decision(self):
        """Test processing decision to use original image."""
        original_path = self._create_test_image("original.jpg")
        
        correction_data = {
            "decision": "original",
            "original_image_path": original_path
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(result.final_image_path, original_path)
        self.assertEqual(result.processing_method, "use_original")
        self.assertTrue(result.user_feedback_recorded)
    
    def test_process_adjust_decision_success(self):
        """Test processing manual crop adjustment successfully."""
        original_path = self._create_test_image("original.jpg", (800, 600))
        
        correction_data = {
            "decision": "adjust",
            "original_image_path": original_path,
            "crop_coordinates": (100, 100, 400, 400)
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(result.processing_method, "manual_crop")
        self.assertTrue(result.user_feedback_recorded)
        
        # Check that cropped image was created
        cropped_path = Path(result.final_image_path)
        self.assertTrue(cropped_path.exists())
        self.assertIn("cropped", cropped_path.name)
    
    def test_process_adjust_decision_no_coordinates(self):
        """Test processing adjust decision without crop coordinates."""
        original_path = self._create_test_image("original.jpg")
        
        correction_data = {
            "decision": "adjust",
            "original_image_path": original_path
            # No crop_coordinates
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertFalse(result.success)
        self.assertEqual(result.processing_method, "adjust_failed")
        self.assertIn("No crop coordinates", result.error_message)
    
    def test_process_regenerate_decision(self):
        """Test processing regenerate decision."""
        original_path = self._create_test_image("original.jpg")
        
        correction_data = {
            "decision": "regenerate",
            "original_image_path": original_path,
            "rejection_reason": "Poor image quality",
            "suggested_modifications": "Better lighting and composition",
            "priority": "High"
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertTrue(result.success)
        self.assertEqual(result.processing_method, "regenerate")
        self.assertTrue(result.regeneration_triggered)
        self.assertTrue(result.user_feedback_recorded)
    
    def test_apply_manual_crop_success(self):
        """Test applying manual crop successfully."""
        original_path = self._create_test_image("test.jpg", (800, 600))
        crop_coords = (100, 100, 400, 400)
        
        cropped_path = self.logic._apply_manual_crop(original_path, crop_coords, self.user_id)
        
        self.assertIsNotNone(cropped_path)
        self.assertTrue(Path(cropped_path).exists())
        
        # Verify cropped image dimensions
        cropped_image = Image.open(cropped_path)
        self.assertEqual(cropped_image.size, (300, 300))  # 400-100, 400-100
    
    def test_apply_manual_crop_coordinate_validation(self):
        """Test manual crop with coordinate validation."""
        original_path = self._create_test_image("test.jpg", (200, 200))
        
        # Test coordinates outside image bounds
        crop_coords = (-50, -50, 300, 300)
        
        cropped_path = self.logic._apply_manual_crop(original_path, crop_coords, self.user_id)
        
        self.assertIsNotNone(cropped_path)
        
        # Verify coordinates were clamped to image bounds
        cropped_image = Image.open(cropped_path)
        self.assertEqual(cropped_image.size, (200, 200))  # Full image since coords were clamped
    
    def test_build_regeneration_parameters(self):
        """Test building regeneration parameters from user feedback."""
        params = self.logic._build_regeneration_parameters(
            rejection_reason="Poor image quality",
            modifications="Better lighting",
            priority="High"
        )
        
        self.assertEqual(params["rejection_reason"], "Poor image quality")
        self.assertEqual(params["modifications"], "Better lighting")
        self.assertEqual(params["priority"], "High")
        self.assertTrue(params["enhanced_quality"])
        self.assertTrue(params["quality_boost"])
    
    def test_build_regeneration_parameters_multiple_people(self):
        """Test regeneration parameters for multiple people issue."""
        params = self.logic._build_regeneration_parameters(
            rejection_reason="Multiple people detected",
            modifications="Focus on single person",
            priority="Medium"
        )
        
        self.assertTrue(params["single_person_emphasis"])
        self.assertEqual(params["composition_guidance"], "single subject focus")
    
    def test_build_regeneration_parameters_background_issues(self):
        """Test regeneration parameters for background issues."""
        params = self.logic._build_regeneration_parameters(
            rejection_reason="Background issues",
            modifications="Simpler background",
            priority="Low"
        )
        
        self.assertTrue(params["background_simplification"])
        self.assertTrue(params["isolation_priority"])
    
    def test_record_user_feedback(self):
        """Test recording user feedback for learning."""
        correction_data = {
            "decision": "adjust",
            "original_image_path": "/test/path.jpg",
            "crop_coordinates": (100, 100, 400, 400),
            "confidence_score": 0.75
        }
        
        initial_cache_size = len(self.logic.learning_data_cache)
        
        self.logic._record_user_feedback(self.user_id, correction_data)
        
        self.assertEqual(len(self.logic.learning_data_cache), initial_cache_size + 1)
        
        learning_data = self.logic.learning_data_cache[-1]
        self.assertEqual(learning_data.user_id, self.user_id)
        self.assertEqual(learning_data.correction_type, "adjust")
        self.assertEqual(learning_data.crop_coordinates, (100, 100, 400, 400))
    
    def test_analyze_correction_patterns(self):
        """Test analyzing patterns in correction data."""
        # Add some test learning data
        self.logic.learning_data_cache = [
            LearningData(
                user_id=self.user_id,
                original_image_path="/test1.jpg",
                correction_type="regenerate",
                user_decision="regenerate",
                crop_coordinates=None,
                rejection_reason="Poor quality",
                suggested_modifications="Better lighting",
                processing_confidence=0.3,
                timestamp="2024-01-01 12:00:00"
            ),
            LearningData(
                user_id=self.user_id,
                original_image_path="/test2.jpg",
                correction_type="adjust",
                user_decision="adjust",
                crop_coordinates=(100, 100, 400, 400),
                rejection_reason=None,
                suggested_modifications=None,
                processing_confidence=0.6,
                timestamp="2024-01-01 12:05:00"
            ),
            LearningData(
                user_id=self.user_id,
                original_image_path="/test3.jpg",
                correction_type="regenerate",
                user_decision="regenerate",
                crop_coordinates=None,
                rejection_reason="Poor quality",
                suggested_modifications="Different style",
                processing_confidence=0.4,
                timestamp="2024-01-01 12:10:00"
            )
        ]
        
        patterns = self.logic._analyze_correction_patterns()
        
        self.assertIn("common_rejections", patterns)
        self.assertIn("frequent_crops", patterns)
        self.assertIn("quality_issues", patterns)
        
        # Check rejection patterns
        self.assertEqual(patterns["common_rejections"]["Poor quality"], 2)
        
        # Check crop patterns
        self.assertEqual(len(patterns["frequent_crops"]), 1)
        self.assertEqual(patterns["frequent_crops"][0], (100, 100, 400, 400))
        
        # Check quality issues
        self.assertIn("adjust", patterns["quality_issues"])
        self.assertIn("regenerate", patterns["quality_issues"])
    
    def test_get_learning_insights(self):
        """Test getting learning insights."""
        # Add some test data
        self.logic.learning_data_cache = [
            LearningData(
                user_id=self.user_id,
                original_image_path="/test.jpg",
                correction_type="regenerate",
                user_decision="regenerate",
                crop_coordinates=None,
                rejection_reason="Multiple people",
                suggested_modifications="Single person focus",
                processing_confidence=0.5,
                timestamp="2024-01-01 12:00:00"
            )
        ]
        
        insights = self.logic.get_learning_insights()
        
        self.assertIn("total_corrections", insights)
        self.assertIn("common_issues", insights)
        self.assertIn("recommendations", insights)
        
        self.assertEqual(insights["total_corrections"], 1)
        self.assertIn("Multiple people", insights["common_issues"])
    
    def test_get_learning_insights_empty(self):
        """Test getting insights with no learning data."""
        insights = self.logic.get_learning_insights()
        
        self.assertIn("message", insights)
        self.assertEqual(insights["message"], "No learning data available")
    
    def test_process_learning_data_batch(self):
        """Test processing learning data batch."""
        # Fill cache with test data
        for i in range(5):
            self.logic.learning_data_cache.append(
                LearningData(
                    user_id=self.user_id,
                    original_image_path=f"/test{i}.jpg",
                    correction_type="adjust",
                    user_decision="adjust",
                    crop_coordinates=(i*10, i*10, i*10+100, i*10+100),
                    rejection_reason=None,
                    suggested_modifications=None,
                    processing_confidence=0.5 + i*0.1,
                    timestamp=f"2024-01-01 12:0{i}:00"
                )
            )
        
        initial_cache_size = len(self.logic.learning_data_cache)
        
        self.logic._process_learning_data_batch()
        
        # Cache should be cleared after processing
        self.assertEqual(len(self.logic.learning_data_cache), 0)
    
    def test_error_handling_missing_image(self):
        """Test error handling when original image is missing."""
        correction_data = {
            "decision": "accept",
            "original_image_path": "/nonexistent/image.jpg"
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertFalse(result.success)
        self.assertEqual(result.processing_method, "error")
        self.assertIn("not found", result.error_message)
    
    def test_error_handling_unknown_decision(self):
        """Test error handling for unknown decision type."""
        original_path = self._create_test_image("original.jpg")
        
        correction_data = {
            "decision": "unknown_decision",
            "original_image_path": original_path
        }
        
        result = self.logic.process_user_correction(self.user_id, correction_data)
        
        self.assertFalse(result.success)
        self.assertEqual(result.processing_method, "fallback")
        self.assertIn("Unknown decision", result.error_message)
    
    def test_audit_logging(self):
        """Test that audit logging is called correctly."""
        original_path = self._create_test_image("original.jpg")
        
        correction_data = {
            "decision": "original",
            "original_image_path": original_path
        }
        
        self.logic.process_user_correction(self.user_id, correction_data)
        
        # Verify audit service was called
        self.mock_audit_service.log_user_action.assert_called_once()
        
        # Check audit call parameters
        call_args = self.mock_audit_service.log_user_action.call_args
        self.assertEqual(call_args[1]["user_id"], self.user_id)
        self.assertEqual(call_args[1]["action"], "image_correction_processed")
    
    def test_crop_coordinate_edge_cases(self):
        """Test crop coordinate handling for edge cases."""
        original_path = self._create_test_image("test.jpg", (100, 100))
        
        # Test coordinates that would result in zero or negative dimensions
        edge_cases = [
            (50, 50, 50, 50),  # Zero width and height
            (60, 60, 50, 50),  # Negative dimensions
            (0, 0, 1, 1),      # Minimal crop
            (99, 99, 100, 100) # Single pixel crop
        ]
        
        for coords in edge_cases:
            cropped_path = self.logic._apply_manual_crop(original_path, coords, self.user_id)
            
            if cropped_path:
                # Verify cropped image is valid
                cropped_image = Image.open(cropped_path)
                self.assertGreater(cropped_image.size[0], 0)
                self.assertGreater(cropped_image.size[1], 0)
    
    def test_learning_data_batch_processing_threshold(self):
        """Test that learning data is processed when cache reaches threshold."""
        # Fill cache to just below threshold
        for i in range(9):
            self.logic.learning_data_cache.append(
                LearningData(
                    user_id=self.user_id,
                    original_image_path=f"/test{i}.jpg",
                    correction_type="accept",
                    user_decision="accept",
                    crop_coordinates=None,
                    rejection_reason=None,
                    suggested_modifications=None,
                    processing_confidence=0.8,
                    timestamp=f"2024-01-01 12:0{i}:00"
                )
            )
        
        self.assertEqual(len(self.logic.learning_data_cache), 9)
        
        # Add one more to trigger batch processing
        correction_data = {
            "decision": "accept",
            "original_image_path": self._create_test_image("trigger.jpg")
        }
        
        self.logic._record_user_feedback(self.user_id, correction_data)
        
        # Cache should be cleared after reaching threshold
        self.assertEqual(len(self.logic.learning_data_cache), 0)


if __name__ == '__main__':
    unittest.main()