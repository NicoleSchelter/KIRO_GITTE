"""
Performance regression tests for GITTE UX enhancements.
Tests to ensure new features don't negatively impact system performance.
"""

import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from src.services.image_isolation_service import ImageIsolationService
from src.services.image_quality_detector import ImageQualityDetector
from src.logic.image_correction import ImageCorrectionLogic
from src.ui.tooltip_system import TooltipSystem
from src.logic.prerequisite_validation import PrerequisiteValidationLogic
from src.services.performance_monitoring_service import PerformanceMonitoringService
from src.services.lazy_loading_service import LazyLoadingService
from src.services.caching_service import MultiLevelCachingService


class TestPerformanceRegression:
    """Test performance regression for UX enhancements."""
    
    @pytest.fixture
    def performance_baseline(self):
        """Define performance baselines for operations."""
        return {
            "image_quality_analysis": 2.0,  # seconds
            "tooltip_retrieval": 0.1,  # seconds
            "prerequisite_validation": 1.0,  # seconds
            "cache_operations": 0.05,  # seconds
            "ui_rendering": 0.5,  # seconds
        }
    
    @pytest.fixture
    def test_image_path(self):
        """Create a test image for performance testing."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            from PIL import Image
            # Create a realistic test image (512x512)
            img = Image.new('RGB', (512, 512), color='red')
            img.save(f.name)
            yield f.name
        
        Path(f.name).unlink(missing_ok=True)
    
    def test_image_quality_analysis_performance(self, test_image_path, performance_baseline):
        """Test image quality analysis performance doesn't regress."""
        detector = ImageQualityDetector()
        
        # Warm up
        detector.analyze_quality(test_image_path)
        
        # Measure performance
        start_time = time.time()
        for _ in range(5):  # Run multiple times for average
            detector.analyze_quality(test_image_path)
        duration = (time.time() - start_time) / 5
        
        assert duration < performance_baseline["image_quality_analysis"], \
            f"Image quality analysis took {duration:.2f}s, baseline is {performance_baseline['image_quality_analysis']}s"
    
    def test_image_isolation_performance(self, test_image_path, performance_baseline):
        """Test image isolation performance doesn't regress."""
        service = ImageIsolationService()
        
        # Warm up
        try:
            service.isolate_person(test_image_path)
        except Exception:
            pass  # Expected for test setup
        
        # Measure performance
        start_time = time.time()
        for _ in range(3):  # Fewer iterations due to complexity
            try:
                service.isolate_person(test_image_path)
            except Exception:
                pass  # Expected for test setup
        duration = (time.time() - start_time) / 3
        
        # Allow more time for isolation as it's computationally intensive
        assert duration < performance_baseline["image_quality_analysis"] * 2, \
            f"Image isolation took {duration:.2f}s, which exceeds acceptable threshold"
    
    def test_tooltip_system_performance(self, performance_baseline):
        """Test tooltip system performance doesn't regress."""
        tooltip_system = TooltipSystem()
        
        # Register many tooltips
        for i in range(100):
            tooltip_system.register_tooltip(f"tooltip_{i}", f"Tooltip content {i}")
        
        # Measure retrieval performance
        start_time = time.time()
        for i in range(100):
            tooltip_system.get_tooltip(f"tooltip_{i}")
        duration = (time.time() - start_time) / 100
        
        assert duration < performance_baseline["tooltip_retrieval"], \
            f"Tooltip retrieval took {duration:.4f}s per tooltip, baseline is {performance_baseline['tooltip_retrieval']}s"
    
    def test_prerequisite_validation_performance(self, performance_baseline):
        """Test prerequisite validation performance doesn't regress."""
        logic = PrerequisiteValidationLogic()
        user_id = uuid4()
        
        # Add mock checkers
        for i in range(5):
            mock_checker = Mock()
            mock_checker.check.return_value = {
                'passed': True,
                'message': f'Check {i} passed'
            }
            mock_checker.name = f'checker_{i}'
            logic.register_checker(mock_checker)
        
        # Warm up
        logic.validate_prerequisites_for_operation(user_id, "test_operation")
        
        # Measure performance
        start_time = time.time()
        for _ in range(10):
            logic.validate_prerequisites_for_operation(user_id, "test_operation")
        duration = (time.time() - start_time) / 10
        
        assert duration < performance_baseline["prerequisite_validation"], \
            f"Prerequisite validation took {duration:.2f}s, baseline is {performance_baseline['prerequisite_validation']}s"
    
    def test_caching_service_performance(self, performance_baseline):
        """Test caching service performance doesn't regress."""
        cache_service = MultiLevelCachingService()
        
        # Test set operations
        start_time = time.time()
        for i in range(1000):
            cache_service.set(f"key_{i}", f"value_{i}")
        set_duration = (time.time() - start_time) / 1000
        
        # Test get operations
        start_time = time.time()
        for i in range(1000):
            cache_service.get(f"key_{i}")
        get_duration = (time.time() - start_time) / 1000
        
        assert set_duration < performance_baseline["cache_operations"], \
            f"Cache set took {set_duration:.4f}s per operation, baseline is {performance_baseline['cache_operations']}s"
        
        assert get_duration < performance_baseline["cache_operations"], \
            f"Cache get took {get_duration:.4f}s per operation, baseline is {performance_baseline['cache_operations']}s"
    
    def test_lazy_loading_performance(self, performance_baseline):
        """Test lazy loading service performance doesn't regress."""
        lazy_loader = LazyLoadingService()
        
        # Register multiple resources
        for i in range(10):
            mock_resource = Mock()
            mock_resource.name = f"resource_{i}"
            mock_resource.load.return_value = f"loaded_resource_{i}"
            lazy_loader.register_resource(mock_resource)
        
        # Test first access (should load)
        start_time = time.time()
        for i in range(10):
            lazy_loader.get_resource(f"resource_{i}")
        first_access_duration = (time.time() - start_time) / 10
        
        # Test second access (should be cached)
        start_time = time.time()
        for i in range(10):
            lazy_loader.get_resource(f"resource_{i}")
        second_access_duration = (time.time() - start_time) / 10
        
        # Second access should be significantly faster
        assert second_access_duration < first_access_duration / 2, \
            "Lazy loading cache is not providing expected performance improvement"
        
        assert second_access_duration < performance_baseline["cache_operations"], \
            f"Cached resource access took {second_access_duration:.4f}s, baseline is {performance_baseline['cache_operations']}s"
    
    def test_memory_usage_regression(self):
        """Test memory usage doesn't regress with new features."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple service instances
        services = []
        for _ in range(10):
            services.append(ImageIsolationService())
            services.append(TooltipSystem())
            services.append(PrerequisiteValidationLogic())
            services.append(MultiLevelCachingService())
        
        # Use services to trigger memory allocation
        for service in services:
            if hasattr(service, 'register_tooltip'):
                service.register_tooltip("test", "test content")
            elif hasattr(service, 'set'):
                service.set("test", "test value")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB for test)
        assert memory_increase < 100, \
            f"Memory usage increased by {memory_increase:.1f}MB, which may indicate a memory leak"
    
    def test_concurrent_performance(self, performance_baseline):
        """Test performance under concurrent load."""
        import concurrent.futures
        import threading
        
        tooltip_system = TooltipSystem()
        cache_service = MultiLevelCachingService()
        
        # Register test data
        for i in range(50):
            tooltip_system.register_tooltip(f"concurrent_tooltip_{i}", f"Content {i}")
            cache_service.set(f"concurrent_key_{i}", f"value_{i}")
        
        def tooltip_worker():
            start_time = time.time()
            for i in range(50):
                tooltip_system.get_tooltip(f"concurrent_tooltip_{i}")
            return time.time() - start_time
        
        def cache_worker():
            start_time = time.time()
            for i in range(50):
                cache_service.get(f"concurrent_key_{i}")
            return time.time() - start_time
        
        # Run concurrent operations
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            tooltip_futures = [executor.submit(tooltip_worker) for _ in range(2)]
            cache_futures = [executor.submit(cache_worker) for _ in range(2)]
            
            tooltip_times = [f.result() for f in tooltip_futures]
            cache_times = [f.result() for f in cache_futures]
        
        # Average time per operation should still be reasonable
        avg_tooltip_time = sum(tooltip_times) / len(tooltip_times) / 50
        avg_cache_time = sum(cache_times) / len(cache_times) / 50
        
        assert avg_tooltip_time < performance_baseline["tooltip_retrieval"] * 2, \
            f"Concurrent tooltip access took {avg_tooltip_time:.4f}s per operation"
        
        assert avg_cache_time < performance_baseline["cache_operations"] * 2, \
            f"Concurrent cache access took {avg_cache_time:.4f}s per operation"
    
    @pytest.mark.slow
    def test_sustained_load_performance(self, performance_baseline):
        """Test performance under sustained load over time."""
        tooltip_system = TooltipSystem()
        cache_service = MultiLevelCachingService()
        
        # Register initial data
        for i in range(100):
            tooltip_system.register_tooltip(f"sustained_tooltip_{i}", f"Content {i}")
            cache_service.set(f"sustained_key_{i}", f"value_{i}")
        
        performance_samples = []
        
        # Run sustained operations for 30 seconds
        end_time = time.time() + 30
        while time.time() < end_time:
            start_time = time.time()
            
            # Perform mixed operations
            for i in range(10):
                tooltip_system.get_tooltip(f"sustained_tooltip_{i % 100}")
                cache_service.get(f"sustained_key_{i % 100}")
            
            sample_time = (time.time() - start_time) / 20  # 20 operations total
            performance_samples.append(sample_time)
            
            time.sleep(0.1)  # Brief pause between samples
        
        # Check that performance doesn't degrade over time
        first_half = performance_samples[:len(performance_samples)//2]
        second_half = performance_samples[len(performance_samples)//2:]
        
        avg_first_half = sum(first_half) / len(first_half)
        avg_second_half = sum(second_half) / len(second_half)
        
        # Performance shouldn't degrade by more than 50%
        assert avg_second_half < avg_first_half * 1.5, \
            f"Performance degraded from {avg_first_half:.4f}s to {avg_second_half:.4f}s over time"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])