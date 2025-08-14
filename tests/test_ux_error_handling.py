"""
Tests for UX enhancement error handling and fallback mechanisms.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.exceptions import (
    BackgroundRemovalError,
    BatchProcessingError,
    CircuitBreakerOpenError,
    ImageCorruptionError,
    ImageIsolationError,
    ImageTimeoutError,
    PersonDetectionError,
    PrerequisiteCheckFailedError,
    RequiredPrerequisiteError,
    ServiceUnavailableError,
    TooltipError,
    UnsupportedImageFormatError,
)
from src.utils.ux_error_handler import (
    RetryConfig,
    UXErrorHandler,
    with_image_error_handling,
    with_prerequisite_error_handling,
    with_retry,
    safe_tooltip_execution,
)
from src.services.batch_error_handler import (
    BatchErrorHandler,
    BatchProcessingConfig,
    process_batch_with_error_handling,
)
from src.services.error_monitoring_service import (
    ErrorMonitoringService,
    MonitoringConfig,
    AlertSeverity,
)


class TestUXExceptions:
    """Test UX enhancement specific exceptions."""
    
    def test_image_processing_error_creation(self):
        """Test image processing error creation and attributes."""
        error = ImageIsolationError("Test isolation error", isolation_method="rembg")
        
        assert "rembg" in str(error)
        assert error.details["isolation_method"] == "rembg"
        assert "original image will be used" in error.user_message
    
    def test_prerequisite_error_creation(self):
        """Test prerequisite error creation and attributes."""
        error = RequiredPrerequisiteError(
            "Test Service",
            resolution_steps=["Step 1", "Step 2"]
        )
        
        assert "Test Service" in str(error)
        assert error.details["resolution_steps"] == ["Step 1", "Step 2"]
        assert error.severity.value == "critical"
    
    def test_batch_processing_error_creation(self):
        """Test batch processing error creation."""
        error = BatchProcessingError(
            "Batch failed",
            failed_images=["img1.jpg", "img2.jpg"],
            total_images=5
        )
        
        assert error.details["failed_images"] == ["img1.jpg", "img2.jpg"]
        assert error.details["total_images"] == 5
        assert error.details["failure_rate"] == 0.4


class TestUXErrorHandler:
    """Test UX error handler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = UXErrorHandler()
    
    def test_handle_image_processing_error(self):
        """Test image processing error handling."""
        error = ImageTimeoutError("test_operation", 30)
        
        result = self.error_handler.handle_image_processing_error(
            error=error,
            image_path="/test/image.jpg",
            operation="test_operation"
        )
        
        assert result["fallback_options"]["retry_with_different_params"] is True
        assert result["can_retry"] is True
        assert "timeout" in result["suggested_action"].lower()
    
    def test_handle_prerequisite_error(self):
        """Test prerequisite error handling."""
        error = ServiceUnavailableError("Test Service", "Connection failed")
        
        result = self.error_handler.handle_prerequisite_error(
            error=error,
            checker_name="Test Service",
            required=True
        )
        
        assert result["blocks_operation"] is True
        assert result["can_continue_with_fallback"] is False
        assert "1-5 minutes" in result["resolution_options"]["estimated_time"]
    
    def test_handle_tooltip_error(self):
        """Test tooltip error handling."""
        error = TooltipError("Tooltip failed")
        
        result = self.error_handler.handle_tooltip_error(
            error=error,
            element_id="test_button"
        )
        
        assert result["should_hide_tooltip"] is True
        assert result["fallback_content"] is not None
        assert len(result["fallback_content"]) > 0
    
    def test_processing_stats_tracking(self):
        """Test processing statistics tracking."""
        initial_stats = self.error_handler.get_processing_stats()
        
        # Simulate some errors
        self.error_handler.handle_image_processing_error(
            ImageTimeoutError("test", 30),
            "/test/image.jpg"
        )
        self.error_handler.handle_prerequisite_error(
            ServiceUnavailableError("Test", "Failed"),
            "Test Service"
        )
        
        updated_stats = self.error_handler.get_processing_stats()
        
        assert updated_stats["image_processing_failures"] > initial_stats["image_processing_failures"]
        assert updated_stats["prerequisite_failures"] > initial_stats["prerequisite_failures"]
        assert updated_stats["total_failures"] > initial_stats["total_failures"]


class TestRetryDecorator:
    """Test retry decorator functionality."""
    
    def test_successful_retry_after_failure(self):
        """Test successful operation after initial failure."""
        call_count = 0
        
        @with_retry(
            retry_config=RetryConfig(max_retries=2, base_delay=0.1),
            fallback_func=lambda: "fallback_result"
        )
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ImageTimeoutError("test", 30)
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 2
    
    def test_fallback_after_retry_exhaustion(self):
        """Test fallback activation after all retries fail."""
        @with_retry(
            retry_config=RetryConfig(max_retries=1, base_delay=0.1),
            fallback_func=lambda: "fallback_result"
        )
        def always_failing_function():
            raise ImageTimeoutError("test", 30)
        
        result = always_failing_function()
        assert result == "fallback_result"
    
    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0
        
        @with_retry(
            retry_config=RetryConfig(
                max_retries=2,
                retryable_exceptions=(ImageTimeoutError,)
            )
        )
        def function_with_non_retryable_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        
        with pytest.raises(ValueError):
            function_with_non_retryable_error()
        
        assert call_count == 1  # Should not retry


class TestImageErrorHandlingDecorator:
    """Test image error handling decorator."""
    
    def test_successful_image_processing(self):
        """Test successful image processing."""
        @with_image_error_handling(operation="test_processing")
        def process_image(image_path):
            return {"success": True, "result": "processed"}
        
        result = process_image("/test/image.jpg")
        assert result["success"] is True
    
    def test_image_processing_with_timeout(self):
        """Test image processing timeout handling."""
        @with_image_error_handling(
            operation="test_processing",
            timeout_seconds=1,
            fallback_to_original=True
        )
        def slow_process_image(image_path):
            time.sleep(2)  # Simulate slow processing
            return {"success": True}
        
        result = slow_process_image("/test/image.jpg")
        assert result["fallback_used"] is True
    
    def test_image_processing_with_corruption_error(self):
        """Test handling of image corruption errors."""
        @with_image_error_handling(
            operation="test_processing",
            fallback_to_original=False
        )
        def process_corrupted_image(image_path):
            raise ImageCorruptionError(image_path)
        
        with pytest.raises(ImageCorruptionError):
            process_corrupted_image("/test/corrupted.jpg")


class TestSafeTooltipExecution:
    """Test safe tooltip execution decorator."""
    
    def test_successful_tooltip_generation(self):
        """Test successful tooltip generation."""
        @safe_tooltip_execution(element_id="test_button")
        def generate_tooltip():
            return "This is a helpful tooltip"
        
        result = generate_tooltip()
        assert result == "This is a helpful tooltip"
    
    def test_tooltip_error_fallback(self):
        """Test tooltip error fallback."""
        @safe_tooltip_execution(element_id="register_button")
        def failing_tooltip():
            raise TooltipError("Tooltip generation failed")
        
        result = failing_tooltip()
        assert "account" in result.lower()  # Should get fallback content


class TestBatchErrorHandler:
    """Test batch error handler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = BatchProcessingConfig(
            max_concurrent_operations=2,
            max_retries_per_item=1,
            failure_threshold_percentage=50.0,
            timeout_per_item_seconds=5
        )
        self.handler = BatchErrorHandler(self.config)
    
    def test_successful_batch_processing(self):
        """Test successful batch processing."""
        def process_item(item):
            return f"processed_{item}"
        
        items = ["item1", "item2", "item3"]
        result = self.handler.process_batch(items, process_item, "test_item")
        
        assert result.total_items == 3
        assert result.successful_items == 3
        assert result.failed_items == 0
        assert result.success_rate == 100.0
        assert not result.partial_success
    
    def test_partial_batch_failure(self):
        """Test batch processing with partial failures."""
        def process_item(item):
            if item == "item2":
                raise ImageTimeoutError("processing", 30)
            return f"processed_{item}"
        
        items = ["item1", "item2", "item3"]
        result = self.handler.process_batch(items, process_item, "test_item")
        
        assert result.total_items == 3
        assert result.successful_items == 2
        assert result.failed_items == 1
        assert result.success_rate == pytest.approx(66.67, rel=1e-2)
        assert result.partial_success is True
    
    def test_complete_batch_failure(self):
        """Test complete batch failure."""
        def process_item(item):
            raise ImageCorruptionError(f"/test/{item}")
        
        items = ["item1", "item2"]
        
        with pytest.raises(BatchProcessingError):
            self.handler.process_batch(items, process_item, "test_item")
    
    def test_batch_retry_logic(self):
        """Test retry logic in batch processing."""
        call_counts = {}
        
        def process_item_with_retry(item):
            call_counts[item] = call_counts.get(item, 0) + 1
            if item == "retry_item" and call_counts[item] < 2:
                raise ImageTimeoutError("processing", 30)
            return f"processed_{item}"
        
        items = ["normal_item", "retry_item"]
        result = self.handler.process_batch(items, process_item_with_retry, "test_item")
        
        assert result.successful_items == 2
        assert call_counts["retry_item"] == 2  # Should have been retried once
        assert call_counts["normal_item"] == 1  # Should not have been retried
    
    def test_error_classification(self):
        """Test error classification in batch processing."""
        def process_item(item):
            if item == "timeout_item":
                raise ImageTimeoutError("processing", 30)
            elif item == "corruption_item":
                raise ImageCorruptionError("/test/corrupted.jpg")
            return f"processed_{item}"
        
        items = ["timeout_item", "corruption_item", "success_item"]
        result = self.handler.process_batch(items, process_item, "test_item")
        
        assert "ImageTimeoutError" in result.error_summary
        assert "ImageCorruptionError" in result.error_summary
        assert result.error_summary["ImageTimeoutError"] == 1
        assert result.error_summary["ImageCorruptionError"] == 1


class TestErrorMonitoringService:
    """Test error monitoring service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = MonitoringConfig(
            error_rate_threshold=0.1,
            monitoring_window_minutes=5,
            alert_cooldown_minutes=1
        )
        self.monitoring_service = ErrorMonitoringService(self.config)
    
    def test_health_check_calculation(self):
        """Test system health check calculation."""
        with patch('src.services.error_monitoring_service.get_error_stats') as mock_stats:
            mock_stats.return_value = {"total_errors": 5}
            
            health = self.monitoring_service.check_system_health()
            
            assert 0.0 <= health.overall_health <= 1.0
            assert health.timestamp is not None
            assert health.error_rate >= 0.0
    
    def test_error_recording_and_alerting(self):
        """Test error recording and alert generation."""
        # Record multiple errors of the same type
        for _ in range(6):  # Exceed critical threshold of 5
            self.monitoring_service.record_error("ImageTimeoutError", "image_processing")
        
        active_alerts = self.monitoring_service.get_active_alerts()
        
        # Should have generated an alert for high error rate
        assert len(active_alerts) > 0
        assert any("ImageTimeoutError" in alert.message for alert in active_alerts)
    
    def test_alert_cooldown(self):
        """Test alert cooldown mechanism."""
        # Generate first alert
        for _ in range(6):
            self.monitoring_service.record_error("TestError", "test_component")
        
        initial_alert_count = len(self.monitoring_service.get_active_alerts())
        
        # Try to generate same alert immediately (should be blocked by cooldown)
        for _ in range(6):
            self.monitoring_service.record_error("TestError", "test_component")
        
        # Should not have generated additional alerts due to cooldown
        final_alert_count = len(self.monitoring_service.get_active_alerts())
        assert final_alert_count == initial_alert_count
    
    def test_alert_resolution(self):
        """Test alert resolution functionality."""
        # Generate an alert
        for _ in range(6):
            self.monitoring_service.record_error("TestError", "test_component")
        
        active_alerts = self.monitoring_service.get_active_alerts()
        assert len(active_alerts) > 0
        
        # Resolve the first alert
        alert_id = active_alerts[0].id
        resolved = self.monitoring_service.resolve_alert(alert_id)
        
        assert resolved is True
        
        # Check that alert is now resolved
        updated_active_alerts = self.monitoring_service.get_active_alerts()
        assert len(updated_active_alerts) < len(active_alerts)
    
    def test_monitoring_summary(self):
        """Test monitoring summary generation."""
        # Generate some test data
        self.monitoring_service.record_error("TestError1", "component1")
        self.monitoring_service.record_error("TestError2", "component2")
        
        summary = self.monitoring_service.get_monitoring_summary()
        
        assert "current_health" in summary
        assert "alerts" in summary
        assert "error_tracking" in summary
        assert "monitoring_config" in summary
        
        assert summary["current_health"]["overall_health"] is not None
        assert summary["error_tracking"]["total_error_types"] >= 2
    
    @patch('src.services.error_monitoring_service.psutil')
    def test_resource_health_assessment(self, mock_psutil):
        """Test resource health assessment."""
        # Mock system resource data
        mock_memory = Mock()
        mock_memory.percent = 75.0
        mock_psutil.virtual_memory.return_value = mock_memory
        
        mock_disk = Mock()
        mock_disk.used = 80 * 1024**3  # 80GB
        mock_disk.total = 100 * 1024**3  # 100GB
        mock_psutil.disk_usage.return_value = mock_disk
        
        mock_psutil.cpu_percent.return_value = 60.0
        
        health = self.monitoring_service.check_system_health()
        
        # Resource health should be calculated based on mocked values
        assert 0.0 <= health.resource_health <= 1.0
    
    def test_alert_callback_registration(self):
        """Test alert callback registration and execution."""
        callback_called = False
        received_alert = None
        
        def test_callback(alert):
            nonlocal callback_called, received_alert
            callback_called = True
            received_alert = alert
        
        self.monitoring_service.register_alert_callback(test_callback)
        
        # Generate an alert
        for _ in range(6):
            self.monitoring_service.record_error("CallbackTestError", "test_component")
        
        assert callback_called is True
        assert received_alert is not None
        assert "CallbackTestError" in received_alert.message


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple error handling components."""
    
    def test_image_processing_with_monitoring(self):
        """Test image processing with error monitoring integration."""
        monitoring_service = ErrorMonitoringService()
        
        @with_image_error_handling(operation="integration_test")
        def process_image_with_monitoring(image_path):
            # Simulate processing error
            monitoring_service.record_error("ImageProcessingError", "image_service")
            raise ImageTimeoutError("integration_test", 30)
        
        # Process should use fallback
        result = process_image_with_monitoring("/test/image.jpg")
        assert result["fallback_used"] is True
        
        # Check that error was recorded in monitoring
        health = monitoring_service.check_system_health()
        assert health.processing_health < 1.0
    
    def test_batch_processing_with_circuit_breaker(self):
        """Test batch processing with circuit breaker integration."""
        failure_count = 0
        
        @with_retry(
            retry_config=RetryConfig(max_retries=1),
            circuit_breaker_name="test_batch_processing"
        )
        def process_item_with_circuit_breaker(item):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:  # Fail first 3 attempts
                raise ImageTimeoutError("processing", 30)
            return f"processed_{item}"
        
        # Process batch - should trigger circuit breaker
        items = ["item1", "item2", "item3", "item4"]
        
        try:
            result = process_batch_with_error_handling(
                items,
                process_item_with_circuit_breaker,
                "test_item"
            )
            # Some items should fail due to circuit breaker
            assert result.failed_items > 0
        except BatchProcessingError:
            # Batch might fail completely due to circuit breaker
            pass
    
    def test_prerequisite_check_with_fallback(self):
        """Test prerequisite checking with fallback behavior."""
        @with_prerequisite_error_handling(
            checker_name="Test Service",
            required=False,
            allow_fallback=True
        )
        def check_optional_prerequisite():
            raise ServiceUnavailableError("Test Service", "Connection failed")
        
        # Should return fallback result instead of raising exception
        result = check_optional_prerequisite()
        assert result["fallback_used"] is True
        assert result["status"] == "warning"