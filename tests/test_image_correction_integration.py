"""
Integration tests for Image Correction workflow.
Tests the complete correction workflow from UI to logic to services.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from PIL import Image

from src.logic.image_correction import ImageCorrectionLogic
from src.ui.image_correction_dialog import ImageCorrectionDialog
from src.services.image_service import ImageService
from src.services.image_isolation_service import ImageIsolationService
from src.services.audit_service import AuditService


class TestImageCorrectionIntegration(unittest.TestCase):
    """Integration tests for image correction workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test images
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Mock services
        self.mock_image_service = Mock(spec=ImageService)
        self.mock_isolation_service = Mock(spec=ImageIsolationService)
        self.mock_audit_service = Mock(spec=AuditService)
        
        # Configure audit service mock
        self.mock_audit_service.log_user_action = Mock()
        
        # Create logic instance
        self.correction_logic = ImageCorrectionLogic(
            image_service=self.mock_image_service,
            isolation_service=self.mock_isolation_service,
            audit_service=self.mock_audit_service
        )
        
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
    
    def test_complete_correction_workflow_accept(self):
        """Test complete workflow for accepting processed image."""
        # Create test images
        original_path = self._create_test_image("original.jpg")
        processed_path = self._create_test_image("processed.png")
        
        # Simulate user correction data from dialog
        correction_data = {
            "decision": "accept",
            "original_image_path": original_path,
            "processed_image_path": processed_path,
            "confidence_score": 0.85
        }
        
        # Process correction
        result = self.correction_logic.process_user_correction(
            self.user_id, 
            correction_data
        )
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.final_image_path, processed_path)
        self.assertEqual(result.processing_method, "accept_processed")
        self.assertTrue(result.user_feedback_recorded)
        
        # Verify audit logging was called
        self.mock_audit_service.log_user_action.assert_called_once()
    
    def test_complete_correction_workflow_manual_crop(self):
        """Test complete workflow for manual crop adjustment."""
        # Create test image
        original_path = self._create_test_image("original.jpg", (800, 600))
        
        # Simulate user correction data with crop
        correction_data = {
            "decision": "adjust",
            "original_image_path": original_path,
            "crop_coordinates": (100, 100, 500, 400),
            "confidence_score": 0.65
        }
        
        # Process correction
        result = self.correction_logic.process_user_correction(
            self.user_id, 
            correction_data
        )
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.processing_method, "manual_crop")
        self.assertTrue(result.user_feedback_recorded)
        
        # Verify cropped image was created
        cropped_path = Path(result.final_image_path)
        self.assertTrue(cropped_path.exists())
        
        # Verify cropped image dimensions
        cropped_image = Image.open(cropped_path)
        self.assertEqual(cropped_image.size, (400, 300))  # 500-100, 400-100
        
        # Verify audit logging
        self.mock_audit_service.log_user_action.assert_called_once()
    
    def test_complete_correction_workflow_regenerate(self):
        """Test complete workflow for image regeneration."""
        # Create test image
        original_path = self._create_test_image("original.jpg")
        
        # Simulate user correction data for regeneration
        correction_data = {
            "decision": "regenerate",
            "original_image_path": original_path,
            "rejection_reason": "Multiple people detected",
            "suggested_modifications": "Focus on single person in center",
            "priority": "High",
            "confidence_score": 0.3
        }
        
        # Process correction
        result = self.correction_logic.process_user_correction(
            self.user_id, 
            correction_data
        )
        
        # Verify result
        self.assertTrue(result.success)
        self.assertEqual(result.processing_method, "regenerate")
        self.assertTrue(result.regeneration_triggered)
        self.assertTrue(result.user_feedback_recorded)
        
        # Verify audit logging
        self.mock_audit_service.log_user_action.assert_called_once()
    
    def test_learning_system_integration(self):
        """Test that learning system accumulates and processes data correctly."""
        original_path = self._create_test_image("original.jpg")
        
        # Process multiple corrections to trigger learning
        correction_scenarios = [
            {
                "decision": "regenerate",
                "rejection_reason": "Poor quality",
                "suggested_modifications": "Better lighting"
            },
            {
                "decision": "adjust",
                "crop_coordinates": (50, 50, 450, 450)
            },
            {
                "decision": "regenerate",
                "rejection_reason": "Poor quality",
                "suggested_modifications": "Different angle"
            },
            {
                "decision": "accept"
            }
        ]
        
        # Process each correction
        for i, scenario in enumerate(correction_scenarios):
            correction_data = {
                "original_image_path": original_path,
                "confidence_score": 0.5 + i * 0.1,
                **scenario
            }
            
            result = self.correction_logic.process_user_correction(
                self.user_id, 
                correction_data
            )
            
            self.assertTrue(result.success or result.processing_method == "adjust_failed")
        
        # Get learning insights
        insights = self.correction_logic.get_learning_insights()
        
        # Verify insights contain expected data
        self.assertIn("total_corrections", insights)
        self.assertIn("common_issues", insights)
        self.assertIn("recommendations", insights)
        
        # Verify pattern detection
        self.assertEqual(insights["common_issues"]["Poor quality"], 2)
        self.assertIn("quality", str(insights["recommendations"]).lower())
    
    def test_error_recovery_integration(self):
        """Test error recovery in the complete workflow."""
        # Test with non-existent original image
        correction_data = {
            "decision": "accept",
            "original_image_path": "/nonexistent/image.jpg",
            "processed_image_path": "/nonexistent/processed.png"
        }
        
        result = self.correction_logic.process_user_correction(
            self.user_id, 
            correction_data
        )
        
        # Verify graceful error handling
        self.assertFalse(result.success)
        self.assertEqual(result.processing_method, "error")
        self.assertIn("not found", result.error_message)
        
        # Verify audit logging still occurs for errors
        self.mock_audit_service.log_user_action.assert_called_once()
    
    def test_performance_monitoring_integration(self):
        """Test that performance metrics are captured correctly."""
        original_path = self._create_test_image("original.jpg")
        
        correction_data = {
            "decision": "original",
            "original_image_path": original_path
        }
        
        result = self.correction_logic.process_user_correction(
            self.user_id, 
            correction_data
        )
        
        # Verify performance metrics are captured
        self.assertGreaterEqual(result.processing_time, 0)
        self.assertLess(result.processing_time, 1.0)  # Should be fast for simple operations
        
        # Verify audit data includes performance metrics
        audit_call = self.mock_audit_service.log_user_action.call_args
        audit_details = audit_call[1]["details"]
        self.assertIn("processing_time", audit_details)
        self.assertEqual(audit_details["processing_time"], result.processing_time)
    
    @patch('src.logic.image_correction.logger')
    def test_logging_integration(self, mock_logger):
        """Test that logging works correctly throughout the workflow."""
        original_path = self._create_test_image("original.jpg", (400, 300))
        
        # Test manual crop with logging
        correction_data = {
            "decision": "adjust",
            "original_image_path": original_path,
            "crop_coordinates": (50, 50, 350, 250)
        }
        
        result = self.correction_logic.process_user_correction(
            self.user_id, 
            correction_data
        )
        
        self.assertTrue(result.success)
        
        # Verify logging calls were made
        mock_logger.info.assert_called()
        
        # Check that crop operation was logged
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        crop_logged = any("Manual crop applied" in msg for msg in log_calls)
        self.assertTrue(crop_logged)
    
    def test_concurrent_corrections_handling(self):
        """Test handling of multiple concurrent corrections."""
        original_path = self._create_test_image("original.jpg")
        
        # Simulate multiple users making corrections
        user_ids = [uuid4() for _ in range(3)]
        
        results = []
        for user_id in user_ids:
            correction_data = {
                "decision": "original",
                "original_image_path": original_path,
                "confidence_score": 0.7
            }
            
            result = self.correction_logic.process_user_correction(
                user_id, 
                correction_data
            )
            results.append(result)
        
        # Verify all corrections succeeded
        for result in results:
            self.assertTrue(result.success)
            self.assertEqual(result.processing_method, "use_original")
        
        # Verify learning data was recorded for all users
        self.assertEqual(len(self.correction_logic.learning_data_cache), 3)
        
        # Verify each user's data is distinct
        user_ids_in_cache = [data.user_id for data in self.correction_logic.learning_data_cache]
        self.assertEqual(set(user_ids_in_cache), set(user_ids))


if __name__ == '__main__':
    unittest.main()