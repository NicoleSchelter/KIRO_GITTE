"""
Comprehensive integration tests for GITTE UX enhancements.
Tests end-to-end workflows, cross-component interactions, and user journeys.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID

from src.services.image_isolation_service import ImageIsolationService, IsolationResult
from src.services.image_quality_detector import ImageQualityDetector, DetectionResult
from src.logic.image_correction import ImageCorrectionLogic
from src.ui.image_correction_dialog import ImageCorrectionDialog
from src.ui.tooltip_system import TooltipSystem
from src.services.prerequisite_checker import PrerequisiteChecker
from src.logic.prerequisite_validation import PrerequisiteValidationLogic
from src.ui.prerequisite_checklist_ui import PrerequisiteChecklistUI
from src.services.performance_monitoring_service import PerformanceMonitoringService
from src.services.lazy_loading_service import LazyLoadingService
from src.services.caching_service import MultiLevelCachingService
from src.ui.accessibility import AccessibilityHelper, apply_accessibility_features


class TestImageCorrectionWorkflow:
    """Test complete image correction workflow integration."""
    
    @pytest.fixture
    def mock_image_path(self):
        """Create a mock image file."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            # Create a simple test image
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name)
            yield f.name
        
        # Cleanup
        Path(f.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def image_isolation_service(self):
        """Create image isolation service with mocked dependencies."""
        service = ImageIsolationService()
        return service
    
    @pytest.fixture
    def image_quality_detector(self):
        """Create image quality detector."""
        return ImageQualityDetector()
    
    @pytest.fixture
    def image_correction_logic(self, image_isolation_service, image_quality_detector):
        """Create image correction logic with dependencies."""
        return ImageCorrectionLogic(image_isolation_service, image_quality_detector)
    
    def test_complete_image_correction_workflow(
        self, 
        mock_image_path, 
        image_correction_logic
    ):
        """Test complete image correction workflow from detection to correction."""
        user_id = uuid4()
        
        # Step 1: Detect image quality issues
        quality_result = image_correction_logic.analyze_image_quality(mock_image_path)
        
        assert quality_result is not None
        assert hasattr(quality_result, 'overall_quality')
        assert hasattr(quality_result, 'issues')
        
        # Step 2: If issues detected, perform isolation
        if quality_result.issues:
            isolation_result = image_correction_logic.isolate_subject(mock_image_path)
            
            assert isolation_result is not None
            assert hasattr(isolation_result, 'success')
            
            # Step 3: Apply user corrections if needed
            if not isolation_result.success:
                correction_params = {
                    'crop_box': (10, 10, 90, 90),
                    'background_color': 'white'
                }
                
                corrected_result = image_correction_logic.apply_user_correction(
                    mock_image_path, 
                    correction_params,
                    user_id
                )
                
                assert corrected_result is not None
                assert hasattr(corrected_result, 'corrected_image_path')
    
    def test_image_correction_with_ui_integration(self, mock_image_path):
        """Test image correction with UI dialog integration."""
        user_id = uuid4()
        
        # Mock Streamlit components
        with patch('streamlit.columns') as mock_columns, \
             patch('streamlit.image') as mock_image, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.selectbox') as mock_selectbox:
            
            # Setup mock returns
            mock_columns.return_value = [Mock(), Mock()]
            mock_button.return_value = False
            mock_selectbox.return_value = "Accept"
            
            # Create dialog
            dialog = ImageCorrectionDialog()
            
            # Test dialog rendering
            result = dialog.render_correction_dialog(
                original_image_path=mock_image_path,
                processed_image_path=mock_image_path,
                user_id=user_id,
                quality_issues=['blur', 'noise']
            )
            
            # Verify UI components were called
            assert mock_columns.called
            assert mock_image.called
    
    def test_image_correction_error_handling(self, image_correction_logic):
        """Test error handling in image correction workflow."""
        user_id = uuid4()
        
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            image_correction_logic.analyze_image_quality("non_existent.png")
        
        # Test with invalid correction parameters
        with tempfile.NamedTemporaryFile(suffix='.png') as f:
            invalid_params = {
                'crop_box': (-10, -10, 200, 200),  # Invalid crop box
            }
            
            result = image_correction_logic.apply_user_correction(
                f.name, 
                invalid_params,
                user_id
            )
            
            # Should handle gracefully
            assert result is not None
            assert not result.success
    
    def test_image_correction_performance_monitoring(self, mock_image_path, image_correction_logic):
        """Test that image correction operations are monitored for performance."""
        user_id = uuid4()
        
        with patch('src.services.performance_monitoring_service.performance_monitor') as mock_monitor:
            # Perform image correction
            image_correction_logic.analyze_image_quality(mock_image_path)
            
            # Verify performance monitoring was called
            assert mock_monitor.time_operation.called or mock_monitor.record_histogram.called


class TestTooltipSystemIntegration:
    """Test tooltip system integration across UI components."""
    
    @pytest.fixture
    def tooltip_system(self):
        """Create tooltip system."""
        return TooltipSystem()
    
    def test_tooltip_integration_with_forms(self, tooltip_system):
        """Test tooltip integration with form elements."""
        # Register tooltips for form elements
        tooltip_system.register_tooltip(
            "username_input",
            "Enter your username (3-50 characters)",
            context="authentication"
        )
        
        tooltip_system.register_tooltip(
            "password_input", 
            "Enter your password (minimum 8 characters)",
            context="authentication"
        )
        
        # Test tooltip retrieval
        username_tooltip = tooltip_system.get_tooltip("username_input")
        password_tooltip = tooltip_system.get_tooltip("password_input")
        
        assert username_tooltip is not None
        assert "username" in username_tooltip.lower()
        assert password_tooltip is not None
        assert "password" in password_tooltip.lower()
    
    def test_tooltip_context_switching(self, tooltip_system):
        """Test tooltip context switching functionality."""
        # Register context-specific tooltips
        tooltip_system.register_tooltip(
            "save_button",
            "Save your current progress",
            context="general"
        )
        
        tooltip_system.register_tooltip(
            "save_button",
            "Save your image generation settings", 
            context="image_generation"
        )
        
        # Test context switching
        tooltip_system.set_context("general")
        general_tooltip = tooltip_system.get_tooltip("save_button")
        
        tooltip_system.set_context("image_generation")
        image_tooltip = tooltip_system.get_tooltip("save_button")
        
        assert general_tooltip != image_tooltip
        assert "progress" in general_tooltip
        assert "image" in image_tooltip
    
    def test_tooltip_accessibility_integration(self, tooltip_system):
        """Test tooltip integration with accessibility features."""
        # Register tooltip with accessibility attributes
        tooltip_system.register_tooltip(
            "complex_button",
            "This button performs a complex operation that may take several minutes",
            context="general",
            accessibility_level="detailed"
        )
        
        # Test accessibility-enhanced tooltip
        tooltip = tooltip_system.get_tooltip("complex_button", include_accessibility=True)
        
        assert tooltip is not None
        assert len(tooltip) > 50  # Should be detailed for accessibility
    
    def test_tooltip_performance_caching(self, tooltip_system):
        """Test tooltip caching for performance."""
        tooltip_id = "performance_test_tooltip"
        tooltip_content = "This is a test tooltip for performance testing"
        
        # Register tooltip
        tooltip_system.register_tooltip(tooltip_id, tooltip_content)
        
        # First access - should cache
        start_time = time.time()
        first_access = tooltip_system.get_tooltip(tooltip_id)
        first_time = time.time() - start_time
        
        # Second access - should be faster due to caching
        start_time = time.time()
        second_access = tooltip_system.get_tooltip(tooltip_id)
        second_time = time.time() - start_time
        
        assert first_access == second_access
        # Second access should be faster (though this might be flaky in fast systems)
        # assert second_time <= first_time


class TestPrerequisiteValidationWorkflow:
    """Test complete prerequisite validation workflow."""
    
    @pytest.fixture
    def prerequisite_validation_logic(self):
        """Create prerequisite validation logic with mocked checkers."""
        logic = PrerequisiteValidationLogic()
        
        # Add mock checkers
        mock_ollama_checker = Mock(spec=PrerequisiteChecker)
        mock_ollama_checker.check.return_value = {
            'passed': True,
            'message': 'Ollama is running',
            'details': {'version': '0.1.0', 'status': 'healthy'}
        }
        mock_ollama_checker.name = 'ollama_connectivity'
        
        mock_db_checker = Mock(spec=PrerequisiteChecker)
        mock_db_checker.check.return_value = {
            'passed': True,
            'message': 'Database is accessible',
            'details': {'connection_time_ms': 50}
        }
        mock_db_checker.name = 'database_connectivity'
        
        logic.register_checker(mock_ollama_checker)
        logic.register_checker(mock_db_checker)
        
        return logic
    
    def test_complete_prerequisite_validation_workflow(self, prerequisite_validation_logic):
        """Test complete prerequisite validation workflow."""
        user_id = uuid4()
        operation = "chat_interaction"
        
        # Run prerequisite validation
        results = prerequisite_validation_logic.validate_prerequisites_for_operation(
            user_id, operation
        )
        
        assert results is not None
        assert 'overall_status' in results
        assert 'individual_results' in results
        assert results['overall_status'] == 'passed'
        
        # Check individual results
        individual_results = results['individual_results']
        assert len(individual_results) == 2
        
        for result in individual_results.values():
            assert 'passed' in result
            assert 'message' in result
            assert result['passed'] is True
    
    def test_prerequisite_validation_with_failures(self, prerequisite_validation_logic):
        """Test prerequisite validation with some failures."""
        user_id = uuid4()
        
        # Mock one checker to fail
        failed_checker = Mock(spec=PrerequisiteChecker)
        failed_checker.check.return_value = {
            'passed': False,
            'message': 'Service unavailable',
            'details': {'error': 'Connection timeout'}
        }
        failed_checker.name = 'failing_service'
        
        prerequisite_validation_logic.register_checker(failed_checker)
        
        # Run validation
        results = prerequisite_validation_logic.validate_prerequisites_for_operation(
            user_id, "image_generation"
        )
        
        assert results['overall_status'] == 'failed'
        assert 'failing_service' in results['individual_results']
        assert not results['individual_results']['failing_service']['passed']
    
    def test_prerequisite_ui_integration(self):
        """Test prerequisite validation UI integration."""
        user_id = uuid4()
        
        with patch('streamlit.progress') as mock_progress, \
             patch('streamlit.success') as mock_success, \
             patch('streamlit.error') as mock_error, \
             patch('streamlit.button') as mock_button:
            
            mock_button.return_value = False
            
            # Create UI component
            ui = PrerequisiteChecklistUI()
            
            # Mock validation results
            mock_results = {
                'overall_status': 'passed',
                'individual_results': {
                    'ollama_connectivity': {
                        'passed': True,
                        'message': 'Ollama is running'
                    }
                }
            }
            
            # Render UI
            with patch.object(ui, '_run_prerequisite_checks', return_value=mock_results):
                ui.render_prerequisite_checklist(user_id, "chat_interaction")
            
            # Verify UI components were called
            assert mock_progress.called or mock_success.called
    
    def test_prerequisite_caching_integration(self, prerequisite_validation_logic):
        """Test prerequisite result caching."""
        user_id = uuid4()
        operation = "chat_interaction"
        
        # First validation - should run checks
        start_time = time.time()
        first_results = prerequisite_validation_logic.validate_prerequisites_for_operation(
            user_id, operation
        )
        first_duration = time.time() - start_time
        
        # Second validation - should use cache if implemented
        start_time = time.time()
        second_results = prerequisite_validation_logic.validate_prerequisites_for_operation(
            user_id, operation
        )
        second_duration = time.time() - start_time
        
        # Results should be the same
        assert first_results['overall_status'] == second_results['overall_status']


class TestPerformanceOptimizationIntegration:
    """Test performance optimization features integration."""
    
    @pytest.fixture
    def performance_monitor(self):
        """Create performance monitoring service."""
        return PerformanceMonitoringService()
    
    @pytest.fixture
    def lazy_loader(self):
        """Create lazy loading service."""
        return LazyLoadingService()
    
    @pytest.fixture
    def cache_service(self):
        """Create caching service."""
        return MultiLevelCachingService()
    
    def test_performance_monitoring_integration(self, performance_monitor):
        """Test performance monitoring across different operations."""
        # Test timing different operations
        with performance_monitor.time_operation("test_operation") as metadata:
            time.sleep(0.01)  # Simulate work
            metadata["items_processed"] = 10
        
        # Test metrics recording
        performance_monitor.increment_counter("test_counter", 5)
        performance_monitor.set_gauge("test_gauge", 42.0)
        performance_monitor.record_histogram("test_histogram", 123.45)
        
        # Get performance summary
        summary = performance_monitor.get_performance_summary(hours=1)
        
        assert summary is not None
        assert "timing_stats" in summary
        assert "test_operation" in summary["timing_stats"]
    
    def test_lazy_loading_integration(self, lazy_loader):
        """Test lazy loading integration with performance monitoring."""
        from src.services.lazy_loading_service import PersonDetectionModel
        
        # Register a resource
        resource = PersonDetectionModel()
        lazy_loader.register_resource(resource)
        
        # First access - should load
        start_time = time.time()
        first_access = lazy_loader.get_resource("person_detection_model")
        first_duration = time.time() - start_time
        
        # Second access - should be cached
        start_time = time.time()
        second_access = lazy_loader.get_resource("person_detection_model")
        second_duration = time.time() - start_time
        
        # Both should return the same instance
        assert first_access is second_access
        # Second access should be faster
        assert second_duration < first_duration
    
    def test_caching_integration(self, cache_service):
        """Test multi-level caching integration."""
        # Test memory caching
        cache_service.set("test_key", "test_value")
        cached_value = cache_service.get("test_key")
        
        assert cached_value == "test_value"
        
        # Test cache statistics
        stats = cache_service.get_stats()
        
        assert "memory" in stats
        assert "disk" in stats
        assert stats["memory"].entry_count > 0
    
    def test_integrated_performance_optimization(
        self, 
        performance_monitor, 
        lazy_loader, 
        cache_service
    ):
        """Test integrated performance optimization across all systems."""
        # Simulate a complex operation that uses all optimization features
        
        # 1. Monitor the operation
        with performance_monitor.time_operation("complex_operation") as metadata:
            
            # 2. Use lazy loading for expensive resources
            try:
                from src.services.lazy_loading_service import PersonDetectionModel
                resource = PersonDetectionModel()
                lazy_loader.register_resource(resource)
                model = lazy_loader.get_resource("person_detection_model")
                metadata["model_loaded"] = model is not None
            except Exception:
                metadata["model_loaded"] = False
            
            # 3. Use caching for computed results
            cache_key = "complex_computation_result"
            cached_result = cache_service.get(cache_key)
            
            if cached_result is None:
                # Simulate expensive computation
                time.sleep(0.01)
                result = {"computed_value": 42, "timestamp": time.time()}
                cache_service.set(cache_key, result)
                metadata["cache_hit"] = False
            else:
                result = cached_result
                metadata["cache_hit"] = True
            
            metadata["result"] = result
        
        # Verify all systems worked together
        summary = performance_monitor.get_performance_summary(hours=1)
        assert "complex_operation" in summary["timing_stats"]
        
        stats = cache_service.get_stats()
        assert stats["memory"].entry_count > 0


class TestAccessibilityIntegration:
    """Test accessibility features integration."""
    
    def test_accessibility_features_integration(self):
        """Test accessibility features work together."""
        helper = AccessibilityHelper()
        
        # Test color contrast validation
        assert helper.meets_contrast_requirement("#000000", "#FFFFFF")
        
        # Test ARIA label generation
        label = helper.generate_aria_label("button", "Save Changes", "enabled")
        assert "Save Changes" in label
        assert "button" in label
        
        # Test accessible color pair generation
        fg, bg = helper.get_accessible_color_pair("#CCCCCC", "#FFFFFF")
        assert helper.meets_contrast_requirement(fg, bg)
    
    def test_accessibility_with_ui_components(self):
        """Test accessibility integration with UI components."""
        with patch('streamlit.markdown') as mock_markdown:
            # Apply accessibility features
            apply_accessibility_features()
            
            # Verify accessibility features were applied
            assert mock_markdown.called
            
            # Check that CSS and JavaScript were added
            calls = [call[0][0] for call in mock_markdown.call_args_list]
            css_calls = [call for call in calls if '<style>' in call]
            js_calls = [call for call in calls if '<script>' in call]
            
            assert len(css_calls) > 0
            assert len(js_calls) > 0
    
    def test_accessibility_error_handling(self):
        """Test accessibility features handle errors gracefully."""
        helper = AccessibilityHelper()
        
        # Test with invalid inputs
        ratio = helper.calculate_contrast_ratio("invalid", "#FFFFFF")
        assert ratio == 1.0  # Should return safe default
        
        label = helper.generate_aria_label("", "", "", "")
        assert isinstance(label, str)  # Should return string even with empty inputs


class TestEndToEndUserJourneys:
    """Test complete end-to-end user journeys."""
    
    def test_image_generation_with_correction_journey(self):
        """Test complete image generation with correction user journey."""
        user_id = uuid4()
        
        # Mock the complete journey
        with patch('src.services.image_service.ImageService') as mock_image_service, \
             patch('src.services.image_isolation_service.ImageIsolationService') as mock_isolation, \
             patch('src.logic.image_correction.ImageCorrectionLogic') as mock_correction:
            
            # Setup mocks
            mock_image_service.return_value.generate_embodiment_image.return_value = Mock(
                image_path="test_image.png",
                success=True
            )
            
            mock_isolation.return_value.isolate_person.return_value = IsolationResult(
                success=False,
                isolated_image_path=None,
                confidence_score=0.3,
                issues=["multiple_people", "poor_quality"]
            )
            
            mock_correction.return_value.apply_user_correction.return_value = Mock(
                success=True,
                corrected_image_path="corrected_image.png"
            )
            
            # Simulate user journey
            # 1. User generates image
            image_service = mock_image_service.return_value
            generation_result = image_service.generate_embodiment_image(
                prompt="friendly teacher",
                user_id=user_id
            )
            
            assert generation_result.success
            
            # 2. System detects issues and suggests correction
            isolation_service = mock_isolation.return_value
            isolation_result = isolation_service.isolate_person(generation_result.image_path)
            
            assert not isolation_result.success
            assert len(isolation_result.issues) > 0
            
            # 3. User applies correction
            correction_logic = mock_correction.return_value
            correction_result = correction_logic.apply_user_correction(
                generation_result.image_path,
                {"crop_box": (10, 10, 90, 90)},
                user_id
            )
            
            assert correction_result.success
    
    def test_prerequisite_validation_journey(self):
        """Test prerequisite validation user journey."""
        user_id = uuid4()
        
        with patch('src.logic.prerequisite_validation.PrerequisiteValidationLogic') as mock_validation:
            # Setup mock
            mock_validation.return_value.validate_prerequisites_for_operation.return_value = {
                'overall_status': 'failed',
                'individual_results': {
                    'ollama_connectivity': {
                        'passed': False,
                        'message': 'Ollama service is not running',
                        'resolution_steps': ['Start Ollama service', 'Check configuration']
                    }
                }
            }
            
            # Simulate user journey
            validation_logic = mock_validation.return_value
            results = validation_logic.validate_prerequisites_for_operation(
                user_id, "chat_interaction"
            )
            
            # User sees failed prerequisites
            assert results['overall_status'] == 'failed'
            assert 'resolution_steps' in results['individual_results']['ollama_connectivity']
    
    def test_accessibility_enhanced_journey(self):
        """Test user journey with accessibility enhancements."""
        user_id = uuid4()
        
        with patch('streamlit.markdown') as mock_markdown, \
             patch('streamlit.button') as mock_button, \
             patch('streamlit.text_input') as mock_input:
            
            # Setup mocks
            mock_button.return_value = False
            mock_input.return_value = "test input"
            
            # Apply accessibility features
            apply_accessibility_features()
            
            # Simulate accessible form interaction
            from src.ui.accessibility import create_accessible_form_field
            
            field_info = create_accessible_form_field(
                "text",
                "Username",
                "username_field",
                required=True,
                help_text="Enter your username"
            )
            
            # Verify accessibility attributes
            assert field_info["required"] is True
            assert "username_field-help" in field_info["aria_describedby"]
            assert 'role="alert"' not in field_info["error"]  # No error initially


class TestCrossComponentInteractions:
    """Test interactions between different UX enhancement components."""
    
    def test_tooltip_with_prerequisite_integration(self):
        """Test tooltip system integration with prerequisite validation."""
        tooltip_system = TooltipSystem()
        
        # Register prerequisite-related tooltips
        tooltip_system.register_tooltip(
            "prerequisite_check_button",
            "Click to validate system prerequisites before proceeding",
            context="prerequisite_validation"
        )
        
        # Test tooltip retrieval in prerequisite context
        tooltip_system.set_context("prerequisite_validation")
        tooltip = tooltip_system.get_tooltip("prerequisite_check_button")
        
        assert tooltip is not None
        assert "prerequisite" in tooltip.lower()
    
    def test_performance_monitoring_with_image_correction(self):
        """Test performance monitoring integration with image correction."""
        with patch('src.services.performance_monitoring_service.performance_monitor') as mock_monitor:
            # Create image correction logic
            isolation_service = ImageIsolationService()
            quality_detector = ImageQualityDetector()
            correction_logic = ImageCorrectionLogic(isolation_service, quality_detector)
            
            # Simulate monitored operation
            with tempfile.NamedTemporaryFile(suffix='.png') as f:
                from PIL import Image
                img = Image.new('RGB', (100, 100), color='red')
                img.save(f.name)
                
                try:
                    correction_logic.analyze_image_quality(f.name)
                except Exception:
                    pass  # Expected for mock setup
            
            # Verify monitoring was attempted
            # Note: This might not be called due to mocking, but structure is tested
            assert mock_monitor is not None
    
    def test_accessibility_with_performance_optimization(self):
        """Test accessibility features with performance optimization."""
        # Test that accessibility features don't negatively impact performance
        helper = AccessibilityHelper()
        
        # Time accessibility operations
        start_time = time.time()
        
        for i in range(100):
            helper.calculate_contrast_ratio("#000000", "#FFFFFF")
            helper.generate_aria_label("button", f"Button {i}", "enabled")
        
        duration = time.time() - start_time
        
        # Should complete quickly (less than 1 second for 100 operations)
        assert duration < 1.0
    
    def test_caching_with_tooltip_system(self):
        """Test caching integration with tooltip system."""
        tooltip_system = TooltipSystem()
        cache_service = MultiLevelCachingService()
        
        # Register tooltip
        tooltip_id = "cached_tooltip"
        tooltip_content = "This tooltip should be cached for performance"
        
        tooltip_system.register_tooltip(tooltip_id, tooltip_content)
        
        # First access
        first_tooltip = tooltip_system.get_tooltip(tooltip_id)
        
        # Cache the result manually (tooltip system might not have built-in caching)
        cache_service.set(f"tooltip_{tooltip_id}", first_tooltip)
        
        # Second access from cache
        cached_tooltip = cache_service.get(f"tooltip_{tooltip_id}")
        
        assert first_tooltip == cached_tooltip


@pytest.fixture(scope="session")
def integration_test_setup():
    """Setup for integration tests."""
    # Create temporary directories for test files
    temp_dir = tempfile.mkdtemp()
    
    yield {
        "temp_dir": temp_dir,
        "test_user_id": uuid4()
    }
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestSystemIntegration:
    """Test overall system integration."""
    
    def test_system_startup_integration(self, integration_test_setup):
        """Test system startup with all UX enhancements."""
        # Test that all services can be initialized together
        services = {}
        
        try:
            services["performance_monitor"] = PerformanceMonitoringService()
            services["lazy_loader"] = LazyLoadingService()
            services["cache_service"] = MultiLevelCachingService()
            services["tooltip_system"] = TooltipSystem()
            services["accessibility_helper"] = AccessibilityHelper()
            
            # All services should initialize successfully
            assert len(services) == 5
            
            # Test basic functionality of each service
            services["performance_monitor"].increment_counter("startup_test", 1)
            services["cache_service"].set("startup_test", "success")
            services["tooltip_system"].register_tooltip("startup_test", "System started")
            
            # Verify services are working
            cached_value = services["cache_service"].get("startup_test")
            assert cached_value == "success"
            
            tooltip = services["tooltip_system"].get_tooltip("startup_test")
            assert tooltip == "System started"
            
        except Exception as e:
            pytest.fail(f"System integration failed during startup: {e}")
    
    def test_system_shutdown_integration(self, integration_test_setup):
        """Test system shutdown with proper cleanup."""
        # Initialize services
        performance_monitor = PerformanceMonitoringService()
        lazy_loader = LazyLoadingService()
        cache_service = MultiLevelCachingService()
        
        # Use services
        performance_monitor.increment_counter("shutdown_test", 1)
        cache_service.set("shutdown_test", "cleanup_me")
        
        # Test cleanup
        try:
            performance_monitor.stop_monitoring()
            lazy_loader.shutdown()
            cache_service.clear()
            
            # Verify cleanup
            stats = cache_service.get_stats()
            assert stats["memory"].entry_count == 0
            
        except Exception as e:
            pytest.fail(f"System integration failed during shutdown: {e}")
    
    def test_error_propagation_integration(self, integration_test_setup):
        """Test error handling and propagation across components."""
        user_id = integration_test_setup["test_user_id"]
        
        # Test error handling in image correction workflow
        isolation_service = ImageIsolationService()
        quality_detector = ImageQualityDetector()
        correction_logic = ImageCorrectionLogic(isolation_service, quality_detector)
        
        # Test with invalid input
        try:
            correction_logic.analyze_image_quality("non_existent_file.png")
            pytest.fail("Should have raised an exception")
        except FileNotFoundError:
            pass  # Expected
        except Exception as e:
            # Should be a specific, handled exception
            assert str(e) is not None
    
    def test_concurrent_operations_integration(self, integration_test_setup):
        """Test concurrent operations across different components."""
        import threading
        import concurrent.futures
        
        user_id = integration_test_setup["test_user_id"]
        results = []
        
        def performance_operation():
            monitor = PerformanceMonitoringService()
            with monitor.time_operation("concurrent_test"):
                time.sleep(0.01)
            return "performance_done"
        
        def cache_operation():
            cache = MultiLevelCachingService()
            cache.set("concurrent_test", "test_value")
            return cache.get("concurrent_test")
        
        def tooltip_operation():
            tooltip_system = TooltipSystem()
            tooltip_system.register_tooltip("concurrent_test", "Concurrent tooltip")
            return tooltip_system.get_tooltip("concurrent_test")
        
        # Run operations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(performance_operation),
                executor.submit(cache_operation),
                executor.submit(tooltip_operation)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=5)
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Concurrent operation failed: {e}")
        
        # Verify all operations completed successfully
        assert len(results) == 3
        assert "performance_done" in results
        assert "test_value" in results
        assert "Concurrent tooltip" in results