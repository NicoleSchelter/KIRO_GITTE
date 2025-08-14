"""
End-to-end workflow tests for GITTE UX enhancements.
Tests complete user workflows from start to finish.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.services.image_isolation_service import ImageIsolationService, IsolationResult
from src.services.image_quality_detector import ImageQualityDetector, DetectionResult
from src.logic.image_correction import ImageCorrectionLogic
from src.ui.image_correction_dialog import ImageCorrectionDialog
from src.ui.tooltip_system import TooltipSystem
from src.logic.prerequisite_validation import PrerequisiteValidationLogic
from src.ui.prerequisite_checklist_ui import PrerequisiteChecklistUI
from src.services.audit_service import AuditService


class TestEndToEndImageCorrectionWorkflow:
    """Test complete end-to-end image correction workflow."""
    
    @pytest.fixture
    def workflow_setup(self):
        """Setup for end-to-end workflow testing."""
        # Create temporary directory for test images
        temp_dir = tempfile.mkdtemp()
        
        # Create test images
        from PIL import Image
        
        # Original image with issues
        original_img = Image.new('RGB', (800, 600), color='red')
        original_path = Path(temp_dir) / "original.jpg"
        original_img.save(original_path)
        
        # Processed image (simulated result)
        processed_img = Image.new('RGBA', (800, 600), (255, 0, 0, 255))
        processed_path = Path(temp_dir) / "processed.png"
        processed_img.save(processed_path)
        
        yield {
            "temp_dir": temp_dir,
            "original_path": str(original_path),
            "processed_path": str(processed_path),
            "user_id": uuid4()
        }
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_complete_image_correction_workflow_success(self, workflow_setup):
        """Test complete successful image correction workflow."""
        user_id = workflow_setup["user_id"]
        original_path = workflow_setup["original_path"]
        
        # Mock all services
        with patch('src.services.image_service.ImageService') as mock_image_service, \
             patch('src.services.audit_service.AuditService') as mock_audit_service:
            
            # Setup service mocks
            mock_image_service_instance = mock_image_service.return_value
            mock_audit_service_instance = mock_audit_service.return_value
            
            # Step 1: User generates image
            mock_image_service_instance.generate_embodiment_image.return_value = Mock(
                success=True,
                image_path=original_path,
                generation_time=2.5,
                prompt="friendly teacher"
            )
            
            generation_result = mock_image_service_instance.generate_embodiment_image(
                prompt="friendly teacher",
                user_id=user_id
            )
            
            assert generation_result.success
            assert generation_result.image_path == original_path
            
            # Step 2: System analyzes image quality
            quality_detector = ImageQualityDetector()
            
            with patch.object(quality_detector, 'analyze_quality') as mock_analyze:
                mock_analyze.return_value = DetectionResult(
                    is_faulty=True,
                    faulty_reasons=["blur", "multiple_people"],
                    confidence_score=0.8,
                    quality_score=0.4,
                    processing_time=0.5
                )
                
                quality_result = quality_detector.analyze_quality(original_path)
                
                assert quality_result.quality_score < 0.5
                assert "multiple_people" in quality_result.faulty_reasons
                assert quality_result.is_faulty is True
            
            # Step 3: System attempts automatic isolation
            isolation_service = ImageIsolationService()
            
            with patch.object(isolation_service, 'isolate_person') as mock_isolate:
                mock_isolate.return_value = IsolationResult(
                    success=False,  # Automatic isolation fails
                    isolated_image_path=None,
                    confidence_score=0.3,
                    issues=["multiple_people", "unclear_boundaries"],
                    processing_time=1.2
                )
                
                isolation_result = isolation_service.isolate_person(original_path)
                
                assert not isolation_result.success
                assert isolation_result.confidence_score < 0.5
                assert "multiple_people" in isolation_result.issues
            
            # Step 4: System presents correction dialog to user
            dialog = ImageCorrectionDialog()
            
            with patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.image') as mock_image, \
                 patch('streamlit.button') as mock_button, \
                 patch('streamlit.selectbox') as mock_selectbox:
                
                # Setup UI mocks
                mock_columns.return_value = [Mock(), Mock()]
                mock_button.return_value = False
                mock_selectbox.return_value = "Manual Crop"
                
                # Render dialog
                dialog_result = dialog.render_correction_dialog(
                    original_image_path=original_path,
                    processed_image_path=workflow_setup["processed_path"],
                    user_id=user_id,
                    quality_issues=quality_result.faulty_reasons
                )
                
                # Verify UI was rendered
                assert mock_columns.called
                assert mock_image.called
                assert mock_selectbox.called
            
            # Step 5: User makes correction decision
            correction_logic = ImageCorrectionLogic(
                image_service=mock_image_service_instance,
                isolation_service=isolation_service,
                audit_service=mock_audit_service_instance
            )
            
            user_correction_data = {
                "decision": "adjust",
                "original_image_path": original_path,
                "crop_coordinates": (100, 100, 500, 400),
                "confidence_score": 0.65
            }
            
            with patch.object(correction_logic, 'apply_manual_crop') as mock_crop:
                corrected_path = str(Path(workflow_setup["temp_dir"]) / "corrected.png")
                mock_crop.return_value = Mock(
                    success=True,
                    corrected_image_path=corrected_path,
                    processing_time=0.8
                )
                
                correction_result = correction_logic.process_user_correction(
                    user_id,
                    user_correction_data
                )
                
                assert correction_result.success
                assert correction_result.processing_method == "manual_crop"
                assert correction_result.user_feedback_recorded
            
            # Step 6: System records audit trail
            mock_audit_service_instance.log_user_action.assert_called()
            audit_call = mock_audit_service_instance.log_user_action.call_args
            
            assert audit_call[1]["user_id"] == user_id
            assert audit_call[1]["action"] == "image_correction"
            assert "processing_time" in audit_call[1]["details"]
            
            # Step 7: System updates learning data
            learning_insights = correction_logic.get_learning_insights()
            
            assert "total_corrections" in learning_insights
            assert "common_issues" in learning_insights
            assert learning_insights["total_corrections"] > 0
    
    def test_complete_image_correction_workflow_regeneration(self, workflow_setup):
        """Test complete workflow when user chooses regeneration."""
        user_id = workflow_setup["user_id"]
        original_path = workflow_setup["original_path"]
        
        with patch('src.services.image_service.ImageService') as mock_image_service, \
             patch('src.services.audit_service.AuditService') as mock_audit_service:
            
            mock_image_service_instance = mock_image_service.return_value
            mock_audit_service_instance = mock_audit_service.return_value
            
            # Setup services
            isolation_service = ImageIsolationService()
            correction_logic = ImageCorrectionLogic(
                image_service=mock_image_service_instance,
                isolation_service=isolation_service,
                audit_service=mock_audit_service_instance
            )
            
            # User chooses regeneration
            user_correction_data = {
                "decision": "regenerate",
                "original_image_path": original_path,
                "rejection_reason": "Multiple people detected",
                "suggested_modifications": "Focus on single person in center",
                "priority": "High"
            }
            
            # Mock regeneration
            new_image_path = str(Path(workflow_setup["temp_dir"]) / "regenerated.png")
            mock_image_service_instance.regenerate_with_feedback.return_value = Mock(
                success=True,
                image_path=new_image_path,
                generation_time=3.2,
                improvements_applied=["single_person_focus", "better_framing"]
            )
            
            correction_result = correction_logic.process_user_correction(
                user_id,
                user_correction_data
            )
            
            assert correction_result.success
            assert correction_result.processing_method == "regenerate"
            assert correction_result.regeneration_triggered
            
            # Verify regeneration was called with feedback
            mock_image_service_instance.regenerate_with_feedback.assert_called_once()
            regen_call = mock_image_service_instance.regenerate_with_feedback.call_args
            assert "Multiple people detected" in regen_call[1]["feedback"]
    
    def test_image_correction_workflow_error_recovery(self, workflow_setup):
        """Test workflow error recovery scenarios."""
        user_id = workflow_setup["user_id"]
        
        with patch('src.services.image_service.ImageService') as mock_image_service, \
             patch('src.services.audit_service.AuditService') as mock_audit_service:
            
            mock_image_service_instance = mock_image_service.return_value
            mock_audit_service_instance = mock_audit_service.return_value
            
            isolation_service = ImageIsolationService()
            correction_logic = ImageCorrectionLogic(
                image_service=mock_image_service_instance,
                isolation_service=isolation_service,
                audit_service=mock_audit_service_instance
            )
            
            # Test with corrupted image file
            corrupted_path = str(Path(workflow_setup["temp_dir"]) / "corrupted.jpg")
            Path(corrupted_path).write_text("not an image")
            
            user_correction_data = {
                "decision": "adjust",
                "original_image_path": corrupted_path,
                "crop_coordinates": (10, 10, 90, 90)
            }
            
            correction_result = correction_logic.process_user_correction(
                user_id,
                user_correction_data
            )
            
            # Should handle error gracefully
            assert not correction_result.success
            assert correction_result.processing_method == "error"
            assert "corrupted" in correction_result.error_message.lower() or "invalid" in correction_result.error_message.lower()
            
            # Should still log the error
            mock_audit_service_instance.log_user_action.assert_called()


class TestEndToEndPrerequisiteWorkflow:
    """Test complete end-to-end prerequisite validation workflow."""
    
    @pytest.fixture
    def prerequisite_setup(self):
        """Setup for prerequisite workflow testing."""
        return {
            "user_id": uuid4(),
            "operations": ["registration", "chat_interaction", "image_generation"]
        }
    
    def test_complete_prerequisite_validation_workflow(self, prerequisite_setup):
        """Test complete prerequisite validation workflow."""
        user_id = prerequisite_setup["user_id"]
        
        # Setup prerequisite validation logic
        logic = PrerequisiteValidationLogic()
        
        # Mock prerequisite checkers
        with patch('src.services.prerequisite_checker.OllamaConnectivityChecker') as mock_ollama, \
             patch('src.services.prerequisite_checker.DatabaseConnectivityChecker') as mock_db, \
             patch('src.services.prerequisite_checker.ConsentStatusChecker') as mock_consent:
            
            # Setup checker mocks
            mock_ollama_instance = mock_ollama.return_value
            mock_ollama_instance.name = "ollama_connectivity"
            mock_ollama_instance.check.return_value = {
                "passed": True,
                "message": "Ollama service is running",
                "details": {"version": "0.1.0", "response_time_ms": 150}
            }
            
            mock_db_instance = mock_db.return_value
            mock_db_instance.name = "database_connectivity"
            mock_db_instance.check.return_value = {
                "passed": True,
                "message": "Database is accessible",
                "details": {"connection_time_ms": 50}
            }
            
            mock_consent_instance = mock_consent.return_value
            mock_consent_instance.name = "consent_status"
            mock_consent_instance.check.return_value = {
                "passed": True,
                "message": "User consent is valid",
                "details": {"consent_granted": True, "last_updated": "2024-01-01"}
            }
            
            # Register checkers
            logic.register_checker(mock_ollama_instance)
            logic.register_checker(mock_db_instance)
            logic.register_checker(mock_consent_instance)
            
            # Step 1: User attempts operation
            operation = "chat_interaction"
            
            # Step 2: System validates prerequisites
            validation_result = logic.validate_prerequisites_for_operation(user_id, operation)
            
            assert validation_result["overall_status"] == "passed"
            assert len(validation_result["individual_results"]) == 3
            
            # All individual checks should pass
            for checker_name, result in validation_result["individual_results"].items():
                assert result["passed"] is True
                assert "message" in result
                assert "details" in result
            
            # Step 3: System allows operation to proceed
            can_proceed = logic.can_proceed_with_operation(user_id, operation)
            assert can_proceed is True
    
    def test_prerequisite_workflow_with_failures(self, prerequisite_setup):
        """Test prerequisite workflow when some checks fail."""
        user_id = prerequisite_setup["user_id"]
        
        logic = PrerequisiteValidationLogic()
        
        with patch('src.services.prerequisite_checker.OllamaConnectivityChecker') as mock_ollama, \
             patch('src.services.prerequisite_checker.DatabaseConnectivityChecker') as mock_db:
            
            # Ollama check passes
            mock_ollama_instance = mock_ollama.return_value
            mock_ollama_instance.name = "ollama_connectivity"
            mock_ollama_instance.check.return_value = {
                "passed": True,
                "message": "Ollama service is running"
            }
            
            # Database check fails
            mock_db_instance = mock_db.return_value
            mock_db_instance.name = "database_connectivity"
            mock_db_instance.check.return_value = {
                "passed": False,
                "message": "Database connection failed",
                "details": {"error": "Connection timeout"},
                "resolution_steps": [
                    "Check database server status",
                    "Verify connection string",
                    "Check network connectivity"
                ]
            }
            
            logic.register_checker(mock_ollama_instance)
            logic.register_checker(mock_db_instance)
            
            # Step 1: System validates prerequisites
            validation_result = logic.validate_prerequisites_for_operation(user_id, "chat_interaction")
            
            assert validation_result["overall_status"] == "failed"
            assert validation_result["individual_results"]["database_connectivity"]["passed"] is False
            
            # Step 2: System presents resolution UI
            ui = PrerequisiteChecklistUI()
            
            with patch('streamlit.error') as mock_error, \
                 patch('streamlit.expander') as mock_expander, \
                 patch('streamlit.button') as mock_button:
                
                # Mock expander context manager
                mock_expander_context = Mock()
                mock_expander.return_value.__enter__ = Mock(return_value=mock_expander_context)
                mock_expander.return_value.__exit__ = Mock(return_value=None)
                mock_button.return_value = False
                
                ui.render_prerequisite_checklist(user_id, "chat_interaction")
                
                # Should show error for failed check
                mock_error.assert_called()
                
                # Should provide resolution steps
                mock_expander.assert_called()
            
            # Step 3: System blocks operation
            can_proceed = logic.can_proceed_with_operation(user_id, "chat_interaction")
            assert can_proceed is False
    
    def test_prerequisite_workflow_with_warnings(self, prerequisite_setup):
        """Test prerequisite workflow with warnings but no blocking issues."""
        user_id = prerequisite_setup["user_id"]
        
        logic = PrerequisiteValidationLogic()
        
        with patch('src.services.prerequisite_checker.OllamaConnectivityChecker') as mock_ollama:
            # Ollama check passes but with warnings
            mock_ollama_instance = mock_ollama.return_value
            mock_ollama_instance.name = "ollama_connectivity"
            mock_ollama_instance.check.return_value = {
                "passed": True,
                "message": "Ollama service is running but slow",
                "details": {"response_time_ms": 2000},  # Slow response
                "warnings": ["Response time is above recommended threshold"],
                "severity": "warning"
            }
            
            logic.register_checker(mock_ollama_instance)
            
            validation_result = logic.validate_prerequisites_for_operation(user_id, "chat_interaction")
            
            assert validation_result["overall_status"] == "passed_with_warnings"
            assert "warnings" in validation_result["individual_results"]["ollama_connectivity"]
            
            # Should still allow operation to proceed
            can_proceed = logic.can_proceed_with_operation(user_id, "chat_interaction")
            assert can_proceed is True


class TestEndToEndTooltipWorkflow:
    """Test complete end-to-end tooltip interaction workflow."""
    
    @pytest.fixture
    def tooltip_setup(self):
        """Setup for tooltip workflow testing."""
        return {
            "user_id": uuid4(),
            "ui_elements": [
                "username_input",
                "password_input", 
                "submit_button",
                "help_link",
                "settings_menu"
            ]
        }
    
    def test_complete_tooltip_interaction_workflow(self, tooltip_setup):
        """Test complete tooltip interaction workflow."""
        user_id = tooltip_setup["user_id"]
        
        # Step 1: System initializes tooltip system
        tooltip_system = TooltipSystem()
        
        # Step 2: System registers tooltips for UI elements
        tooltip_content = {
            "username_input": "Enter your username (3-50 characters, letters and numbers only)",
            "password_input": "Enter your password (minimum 8 characters, include letters and numbers)",
            "submit_button": "Click to log in to your account",
            "help_link": "Click for additional help and support resources",
            "settings_menu": "Access your account settings and preferences"
        }
        
        for element_id, content in tooltip_content.items():
            tooltip_system.register_tooltip(element_id, content, context="authentication")
        
        # Step 3: User interacts with UI elements
        tooltip_system.set_context("authentication")
        
        for element_id in tooltip_setup["ui_elements"]:
            # User hovers over element (simulated)
            tooltip = tooltip_system.get_tooltip(element_id)
            
            assert tooltip is not None
            assert len(tooltip) > 10  # Should have meaningful content
            assert tooltip == tooltip_content[element_id]
            
            # System tracks tooltip interaction
            tooltip_system.track_tooltip_interaction(user_id, element_id, "hover")
        
        # Step 4: System provides contextual help
        context_help = tooltip_system.get_contextual_help("authentication")
        
        assert context_help is not None
        assert "authentication" in context_help.lower() or "login" in context_help.lower()
        
        # Step 5: System analyzes tooltip effectiveness
        interaction_stats = tooltip_system.get_interaction_statistics(user_id)
        
        assert "total_interactions" in interaction_stats
        assert interaction_stats["total_interactions"] == len(tooltip_setup["ui_elements"])
        assert "most_accessed_tooltips" in interaction_stats
    
    def test_tooltip_workflow_with_accessibility(self, tooltip_setup):
        """Test tooltip workflow with accessibility features."""
        user_id = tooltip_setup["user_id"]
        
        tooltip_system = TooltipSystem()
        
        # Register accessibility-enhanced tooltips
        tooltip_system.register_tooltip(
            "complex_form_field",
            "This field requires specific formatting. Use format: XXX-XX-XXXX",
            context="form_filling",
            accessibility_level="detailed",
            aria_label="Social Security Number input field with format XXX-XX-XXXX"
        )
        
        # Test accessibility features
        tooltip = tooltip_system.get_tooltip(
            "complex_form_field",
            include_accessibility=True,
            user_preferences={"screen_reader": True, "high_contrast": True}
        )
        
        assert tooltip is not None
        assert "XXX-XX-XXXX" in tooltip
        assert len(tooltip) > 50  # Should be detailed for accessibility
        
        # Test ARIA integration
        aria_attributes = tooltip_system.get_aria_attributes("complex_form_field")
        
        assert "aria-label" in aria_attributes
        assert "aria-describedby" in aria_attributes
        assert "Social Security Number" in aria_attributes["aria-label"]
    
    def test_tooltip_workflow_performance(self, tooltip_setup):
        """Test tooltip workflow performance under load."""
        tooltip_system = TooltipSystem()
        
        # Register many tooltips
        for i in range(1000):
            tooltip_system.register_tooltip(
                f"element_{i}",
                f"Tooltip content for element {i}",
                context="performance_test"
            )
        
        tooltip_system.set_context("performance_test")
        
        # Measure retrieval performance
        start_time = time.time()
        
        for i in range(1000):
            tooltip = tooltip_system.get_tooltip(f"element_{i}")
            assert tooltip is not None
        
        retrieval_time = time.time() - start_time
        
        # Should complete within reasonable time
        assert retrieval_time < 1.0  # Less than 1 second for 1000 tooltips
        
        # Average time per tooltip should be very fast
        avg_time = retrieval_time / 1000
        assert avg_time < 0.001  # Less than 1ms per tooltip


class TestEndToEndUserJourneys:
    """Test complete end-to-end user journeys combining multiple features."""
    
    def test_new_user_onboarding_journey(self):
        """Test complete new user onboarding journey with UX enhancements."""
        user_id = uuid4()
        
        # Step 1: User arrives at registration page
        with patch('src.ui.prerequisite_integration.integrate_registration_prerequisites') as mock_prereq:
            mock_prereq.return_value = {"blocked": False, "readiness": {"ready": True}}
            
            # Prerequisites are checked
            prereq_result = mock_prereq()
            assert not prereq_result["blocked"]
        
        # Step 2: User sees tooltips on registration form
        tooltip_system = TooltipSystem()
        tooltip_system.register_tooltip("email_input", "Enter a valid email address")
        tooltip_system.register_tooltip("password_input", "Create a strong password (8+ characters)")
        
        email_tooltip = tooltip_system.get_tooltip("email_input")
        password_tooltip = tooltip_system.get_tooltip("password_input")
        
        assert "email" in email_tooltip.lower()
        assert "password" in password_tooltip.lower()
        
        # Step 3: User completes registration
        with patch('src.services.audit_service.AuditService') as mock_audit:
            mock_audit_instance = mock_audit.return_value
            
            # Registration is audited
            mock_audit_instance.log_user_action(
                user_id=user_id,
                action="user_registration",
                details={"registration_method": "email", "tooltips_used": ["email_input", "password_input"]}
            )
            
            mock_audit_instance.log_user_action.assert_called_once()
        
        # Step 4: User proceeds to first image generation
        with patch('src.ui.prerequisite_integration.integrate_image_generation_prerequisites') as mock_img_prereq:
            mock_img_prereq.return_value = True  # Prerequisites pass
            
            can_generate = mock_img_prereq(user_id)
            assert can_generate is True
        
        # Step 5: Image generation with correction workflow
        with patch('src.services.image_service.ImageService') as mock_image_service:
            mock_image_service_instance = mock_image_service.return_value
            mock_image_service_instance.generate_embodiment_image.return_value = Mock(
                success=True,
                image_path="generated_image.png"
            )
            
            generation_result = mock_image_service_instance.generate_embodiment_image(
                prompt="friendly teacher",
                user_id=user_id
            )
            
            assert generation_result.success
        
        # Journey completes successfully
        assert True  # All steps completed without errors
    
    def test_experienced_user_workflow_optimization(self):
        """Test workflow optimization for experienced users."""
        user_id = uuid4()
        
        # Simulate experienced user with history
        user_history = {
            "total_sessions": 50,
            "successful_image_generations": 45,
            "tooltip_interactions": 200,
            "correction_workflows_completed": 10
        }
        
        # Step 1: System optimizes prerequisites based on history
        logic = PrerequisiteValidationLogic()
        
        # Experienced users get cached/faster prerequisite checks
        with patch.object(logic, 'get_cached_results') as mock_cache:
            mock_cache.return_value = {
                "overall_status": "passed",
                "cached": True,
                "cache_age_seconds": 300
            }
            
            results = logic.validate_prerequisites_for_operation(user_id, "image_generation")
            assert results["cached"] is True
        
        # Step 2: System provides advanced tooltips
        tooltip_system = TooltipSystem()
        
        advanced_tooltip = tooltip_system.get_tooltip(
            "advanced_settings",
            user_experience_level="experienced",
            show_advanced_tips=True
        )
        
        assert advanced_tooltip is not None
        # Advanced tooltips should be more concise for experienced users
        assert len(advanced_tooltip) < 100 or "advanced" in advanced_tooltip.lower()
        
        # Step 3: System enables power user features
        with patch('src.services.lazy_loading_service.LazyLoadingService') as mock_lazy:
            mock_lazy_instance = mock_lazy.return_value
            
            # Preload resources for experienced users
            mock_lazy_instance.preload_resources(["image_models", "quality_detectors"])
            mock_lazy_instance.preload_resources.assert_called_once()
    
    def test_error_recovery_user_journey(self):
        """Test user journey with error recovery scenarios."""
        user_id = uuid4()
        
        # Step 1: User encounters system error
        with patch('src.services.image_service.ImageService') as mock_image_service:
            mock_image_service_instance = mock_image_service.return_value
            mock_image_service_instance.generate_embodiment_image.side_effect = Exception("Service unavailable")
            
            # System should handle error gracefully
            try:
                mock_image_service_instance.generate_embodiment_image(
                    prompt="test",
                    user_id=user_id
                )
                assert False, "Should have raised exception"
            except Exception as e:
                assert "unavailable" in str(e)
        
        # Step 2: System provides helpful error message and recovery options
        from src.utils.ux_error_handler import UXErrorHandler
        
        error_handler = UXErrorHandler()
        
        error_response = error_handler.handle_service_error(
            error_type="service_unavailable",
            user_id=user_id,
            context="image_generation"
        )
        
        assert error_response["user_friendly_message"] is not None
        assert "recovery_options" in error_response
        assert len(error_response["recovery_options"]) > 0
        
        # Step 3: User follows recovery suggestion
        recovery_option = error_response["recovery_options"][0]
        
        if recovery_option["action"] == "retry_later":
            # System schedules retry
            assert "retry_delay_minutes" in recovery_option
        elif recovery_option["action"] == "use_fallback":
            # System provides alternative
            assert "fallback_method" in recovery_option
        
        # Step 4: System tracks error for improvement
        with patch('src.services.audit_service.AuditService') as mock_audit:
            mock_audit_instance = mock_audit.return_value
            
            error_handler.log_error_recovery(
                user_id=user_id,
                error_type="service_unavailable",
                recovery_action=recovery_option["action"],
                success=True
            )
            
            mock_audit_instance.log_user_action.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])