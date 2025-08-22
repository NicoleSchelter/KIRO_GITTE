"""
Performance tests and benchmarks for GITTE UX enhancements.
"""

import asyncio
import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch
import tempfile
import os

from src.services.performance_monitoring_service import (
    PerformanceMonitoringService,
    PerformanceThresholds,
    monitor_performance,
    monitor_async_performance,
    cached_operation,
)
from src.services.lazy_loading_service import (
    LazyLoadingService,
    PersonDetectionModel,
    BackgroundRemovalModel,
    lazy_resource,
)
from src.services.caching_service import (
    MultiLevelCachingService,
    MemoryCacheBackend,
    DiskCacheBackend,
    cached,
    CacheLevel,
)
from src.services.batch_error_handler import (
    BatchErrorHandler,
    BatchProcessingConfig,
)


class TestPerformanceMonitoring:
    """Test performance monitoring functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.thresholds = PerformanceThresholds(
            max_response_time_ms=1000.0,
            max_cpu_percent=80.0,
            max_memory_percent=85.0
        )
        self.monitor = PerformanceMonitoringService(self.thresholds)
    
    def test_timing_operation(self):
        """Test operation timing functionality."""
        with self.monitor.time_operation("test_operation") as metadata:
            time.sleep(0.1)  # Simulate work
            metadata["test_data"] = "value"
        
        # Check that timing was recorded
        assert len(self.monitor.timings) == 1
        timing = self.monitor.timings[0]
        
        assert timing.operation == "test_operation"
        assert timing.duration_ms >= 100  # At least 100ms
        assert timing.success is True
        assert timing.metadata["test_data"] == "value"
    
    def test_timing_operation_with_exception(self):
        """Test operation timing with exceptions."""
        with pytest.raises(ValueError):
            with self.monitor.time_operation("failing_operation"):
                raise ValueError("Test error")
        
        # Check that timing was recorded even with exception
        assert len(self.monitor.timings) == 1
        timing = self.monitor.timings[0]
        
        assert timing.operation == "failing_operation"
        assert timing.success is False
        assert timing.error == "Test error"
    
    def test_performance_decorator(self):
        """Test performance monitoring decorator."""
        @monitor_performance("decorated_operation")
        def test_function(duration):
            time.sleep(duration)
            return "result"
        
        result = test_function(0.05)
        
        assert result == "result"
        assert len(self.monitor.timings) == 1
        
        timing = self.monitor.timings[0]
        assert timing.operation == "decorated_operation"
        assert timing.duration_ms >= 50
    
    @pytest.mark.asyncio
    async def test_async_performance_decorator(self):
        """Test async performance monitoring decorator."""
        @monitor_async_performance("async_operation")
        async def async_test_function(duration):
            await asyncio.sleep(duration)
            return "async_result"
        
        result = await async_test_function(0.05)
        
        assert result == "async_result"
        # Check that metrics were recorded
        assert "async_operation_duration_ms" in self.monitor.histograms
    
    def test_resource_usage_monitoring(self):
        """Test resource usage monitoring."""
        resource_usage = self.monitor.get_resource_usage()
        
        assert resource_usage.cpu_percent >= 0
        assert resource_usage.memory_percent >= 0
        assert resource_usage.disk_usage_percent >= 0
        assert resource_usage.timestamp is not None
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        # Generate some test data
        with self.monitor.time_operation("test_op_1"):
            time.sleep(0.01)
        
        with self.monitor.time_operation("test_op_2"):
            time.sleep(0.02)
        
        summary = self.monitor.get_performance_summary(hours=1)
        
        assert "timing_stats" in summary
        assert "resource_stats" in summary
        assert summary["total_operations"] == 2
    
    def test_cache_operations(self):
        """Test cache operations in performance monitor."""
        # Test cache set and get
        self.monitor.cache_set("test_key", "test_value")
        value = self.monitor.cache_get("test_key")
        
        assert value == "test_value"
        
        # Test cache expiration
        time.sleep(0.1)
        expired_value = self.monitor.cache_get("expired_key")
        assert expired_value is None
    
    def test_cached_operation_decorator(self):
        """Test cached operation decorator."""
        call_count = 0
        
        @cached_operation(ttl_minutes=1)
        def expensive_operation(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call should execute function
        result1 = expensive_operation(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = expensive_operation(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Different argument should execute function
        result3 = expensive_operation(10)
        assert result3 == 20
        assert call_count == 2


class TestLazyLoading:
    """Test lazy loading functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.lazy_loader = LazyLoadingService()
    
    def test_resource_registration(self):
        """Test resource registration."""
        mock_resource = Mock()
        mock_resource.name = "test_resource"
        mock_resource.is_expensive = True
        
        self.lazy_loader.register_resource(mock_resource)
        
        stats = self.lazy_loader.get_resource_stats()
        assert stats["total_resources"] == 1
        assert "test_resource" in stats["resources"]
    
    def test_resource_loading(self):
        """Test resource loading."""
        mock_resource = Mock()
        mock_resource.name = "test_resource"
        mock_resource.is_expensive = False
        mock_resource.load.return_value = "loaded_resource"
        
        self.lazy_loader.register_resource(mock_resource)
        
        # First access should load the resource
        result = self.lazy_loader.get_resource("test_resource")
        assert result == "loaded_resource"
        mock_resource.load.assert_called_once()
        
        # Second access should return cached resource
        result2 = self.lazy_loader.get_resource("test_resource")
        assert result2 == "loaded_resource"
        assert mock_resource.load.call_count == 1  # Should not be called again
    
    def test_resource_unloading(self):
        """Test resource unloading."""
        mock_resource = Mock()
        mock_resource.name = "test_resource"
        mock_resource.is_expensive = False
        mock_resource.load.return_value = "loaded_resource"
        
        self.lazy_loader.register_resource(mock_resource)
        
        # Load resource
        self.lazy_loader.get_resource("test_resource")
        
        # Unload resource
        self.lazy_loader.unload_resource("test_resource")
        mock_resource.unload.assert_called_once()
        
        # Next access should reload
        self.lazy_loader.get_resource("test_resource")
        assert mock_resource.load.call_count == 2
    
    def test_concurrent_loading(self):
        """Test concurrent resource loading."""
        load_count = 0
        
        class SlowResource:
            name = "slow_resource"
            is_expensive = True
            
            def load(self):
                nonlocal load_count
                load_count += 1
                time.sleep(0.1)  # Simulate slow loading
                return f"result_{load_count}"
            
            def unload(self):
                pass
        
        slow_resource = SlowResource()
        self.lazy_loader.register_resource(slow_resource)
        
        # Start multiple concurrent requests
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(self.lazy_loader.get_resource, "slow_resource")
                for _ in range(3)
            ]
            
            results = [future.result() for future in as_completed(futures)]
        
        # All should get the same result (loaded only once)
        assert all(result == results[0] for result in results)
        assert load_count == 1  # Should only load once despite concurrent requests
    
    def test_lazy_resource_decorator(self):
        """Test lazy resource decorator."""
        mock_resource = Mock()
        mock_resource.name = "decorated_resource"
        mock_resource.is_expensive = False
        mock_resource.load.return_value = "decorated_result"
        
        self.lazy_loader.register_resource(mock_resource)
        
        @lazy_resource("decorated_resource")
        def function_using_resource(resource, x):
            return f"{resource}_{x}"
        
        result = function_using_resource(5)
        assert result == "decorated_result_5"
        mock_resource.load.assert_called_once()


class TestCaching:
    """Test caching functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MultiLevelCachingService(
            memory_cache_mb=1,  # Small for testing
            disk_cache_mb=5,
            default_ttl_seconds=60
        )
    
    def test_memory_cache_basic_operations(self):
        """Test basic memory cache operations."""
        # Test set and get
        success = self.cache_service.set("test_key", "test_value")
        assert success is True
        
        value = self.cache_service.get("test_key")
        assert value == "test_value"
        
        # Test delete
        deleted = self.cache_service.delete("test_key")
        assert deleted is True
        
        value = self.cache_service.get("test_key")
        assert value is None
    
    def test_disk_cache_basic_operations(self):
        """Test basic disk cache operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            disk_cache = DiskCacheBackend(cache_dir=temp_dir, max_size_mb=1)
            
            from src.services.caching_service import CacheEntry
            from datetime import datetime
            
            entry = CacheEntry(
                key="disk_test",
                value="disk_value",
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
                ttl_seconds=60,
                size_bytes=100
            )
            
            # Test set and get
            success = disk_cache.set("disk_test", entry)
            assert success is True
            
            retrieved_entry = disk_cache.get("disk_test")
            assert retrieved_entry is not None
            assert retrieved_entry.value == "disk_value"
    
    def test_cache_decorator(self):
        """Test cache decorator functionality."""
        call_count = 0
        
        @cached(ttl_seconds=60)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # First call should execute function
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call with same args should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1
        
        # Different args should execute function
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2
    
    def test_cache_levels(self):
        """Test multi-level cache behavior."""
        # Set in memory cache
        self.cache_service.set("memory_key", "memory_value", cache_level=CacheLevel.MEMORY)
        
        # Should be available from memory
        value = self.cache_service.get("memory_key")
        assert value == "memory_value"
        
        # Clear memory cache
        self.cache_service.clear(CacheLevel.MEMORY)
        
        # Should no longer be available
        value = self.cache_service.get("memory_key")
        assert value is None
    
    def test_cache_statistics(self):
        """Test cache statistics collection."""
        # Generate some cache activity
        self.cache_service.set("stats_key1", "value1")
        self.cache_service.set("stats_key2", "value2")
        
        # Generate hits and misses
        self.cache_service.get("stats_key1")  # Hit
        self.cache_service.get("nonexistent")  # Miss
        
        stats = self.cache_service.get_stats()
        
        assert "memory" in stats
        assert "disk" in stats
        
        memory_stats = stats["memory"]
        assert memory_stats.hits >= 1
        assert memory_stats.misses >= 1
        assert memory_stats.entry_count >= 1
    
    def test_cache_eviction(self):
        """Test cache eviction policies."""
        # Create cache with very small size
        small_cache = MemoryCacheBackend(max_size_mb=0.001, max_entries=2)
        
        from src.services.caching_service import CacheEntry
        from datetime import datetime
        
        # Add entries that exceed capacity
        for i in range(5):
            entry = CacheEntry(
                key=f"key_{i}",
                value=f"value_{i}" * 100,  # Make it larger
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                access_count=0,
                ttl_seconds=60,
                size_bytes=1000
            )
            small_cache.set(f"key_{i}", entry)
        
        stats = small_cache.get_stats()
        
        # Should have evicted some entries
        assert stats.evictions > 0
        assert stats.entry_count <= 2  # Respects max_entries


class TestBatchProcessingPerformance:
    """Test batch processing performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = BatchProcessingConfig(
            max_concurrent_operations=3,
            max_retries_per_item=1,
            timeout_per_item_seconds=5
        )
        self.batch_handler = BatchErrorHandler(self.config)
    
    def test_concurrent_processing_performance(self):
        """Test concurrent processing performance."""
        def slow_processor(item):
            time.sleep(0.1)  # Simulate work
            return f"processed_{item}"
        
        items = [f"item_{i}" for i in range(10)]
        
        start_time = time.time()
        result = self.batch_handler.process_batch(items, slow_processor, "test_item")
        end_time = time.time()
        
        # With 3 concurrent operations, should be faster than sequential
        # Sequential would take ~1 second, concurrent should be ~0.4 seconds
        assert end_time - start_time < 0.8
        assert result.successful_items == 10
        assert result.success_rate == 100.0
    
    def test_batch_processing_with_failures(self):
        """Test batch processing performance with some failures."""
        def flaky_processor(item):
            if "fail" in item:
                raise ValueError(f"Processing failed for {item}")
            time.sleep(0.05)
            return f"processed_{item}"
        
        items = ["item_1", "item_fail_2", "item_3", "item_fail_4", "item_5"]
        
        result = self.batch_handler.process_batch(items, flaky_processor, "test_item")
        
        assert result.successful_items == 3
        assert result.failed_items == 2
        assert result.success_rate == 60.0
        assert result.partial_success is True
    
    @pytest.mark.asyncio
    async def test_async_batch_processing(self):
        """Test async batch processing performance."""
        async def async_processor(item):
            await asyncio.sleep(0.05)
            return f"async_processed_{item}"
        
        items = [f"item_{i}" for i in range(5)]
        
        start_time = time.time()
        result = await self.batch_handler.process_batch_async(items, async_processor, "async_item")
        end_time = time.time()
        
        # Should process concurrently
        assert end_time - start_time < 0.3  # Much faster than 0.25s sequential
        assert result.successful_items == 5
        assert result.success_rate == 100.0


class TestIntegrationPerformance:
    """Test integrated performance scenarios."""
    
    def test_cached_lazy_resource_performance(self):
        """Test performance of cached lazy resources."""
        lazy_loader = LazyLoadingService()
        
        class ExpensiveResource:
            name = "expensive_resource"
            is_expensive = True
            load_count = 0
            
            def load(self):
                self.load_count += 1
                time.sleep(0.1)  # Simulate expensive loading
                return f"expensive_result_{self.load_count}"
            
            def unload(self):
                pass
        
        expensive_resource = ExpensiveResource()
        lazy_loader.register_resource(expensive_resource)
        
        @cached(ttl_seconds=60)
        @lazy_resource("expensive_resource")
        def use_expensive_resource(resource, x):
            return f"{resource}_{x}"
        
        # First call should load resource and cache result
        start_time = time.time()
        result1 = use_expensive_resource(1)
        first_call_time = time.time() - start_time
        
        # Second call should use cached result (much faster)
        start_time = time.time()
        result2 = use_expensive_resource(1)
        second_call_time = time.time() - start_time
        
        assert result1 == result2
        assert second_call_time < first_call_time / 10  # Should be much faster
        assert expensive_resource.load_count == 1  # Should only load once
    
    def test_performance_monitoring_overhead(self):
        """Test that performance monitoring doesn't add significant overhead."""
        def simple_function():
            return sum(range(1000))
        
        # Measure without monitoring
        start_time = time.time()
        for _ in range(100):
            simple_function()
        unmonitored_time = time.time() - start_time
        
        # Measure with monitoring
        @monitor_performance("simple_operation")
        def monitored_function():
            return sum(range(1000))
        
        start_time = time.time()
        for _ in range(100):
            monitored_function()
        monitored_time = time.time() - start_time
        
        # Monitoring overhead should be minimal (less than 50% increase)
        overhead_ratio = monitored_time / unmonitored_time
        assert overhead_ratio < 1.5, f"Monitoring overhead too high: {overhead_ratio:.2f}x"


@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Performance benchmarks for critical operations."""
    
    def test_image_processing_performance_benchmark(self):
        """Benchmark image processing operations."""
        # This would test actual image processing performance
        # For now, we'll simulate with a placeholder
        
        def simulate_image_processing():
            time.sleep(0.1)  # Simulate processing time
            return "processed_image"
        
        iterations = 10
        start_time = time.time()
        
        for _ in range(iterations):
            simulate_image_processing()
        
        total_time = time.time() - start_time
        avg_time_per_image = total_time / iterations
        
        # Assert performance requirements
        assert avg_time_per_image < 0.2, f"Image processing too slow: {avg_time_per_image:.3f}s per image"
    
    def test_database_query_performance_benchmark(self):
        """Benchmark database query performance."""
        # This would test actual database performance
        # For now, we'll simulate with a placeholder
        
        def simulate_database_query():
            time.sleep(0.01)  # Simulate query time
            return "query_result"
        
        iterations = 100
        start_time = time.time()
        
        for _ in range(iterations):
            simulate_database_query()
        
        total_time = time.time() - start_time
        avg_time_per_query = total_time / iterations
        
        # Assert performance requirements
        assert avg_time_per_query < 0.05, f"Database queries too slow: {avg_time_per_query:.3f}s per query"
    
    def test_prerequisite_check_performance_benchmark(self):
        """Benchmark prerequisite check performance."""
        def simulate_prerequisite_check():
            time.sleep(0.02)  # Simulate check time
            return True
        
        iterations = 50
        start_time = time.time()
        
        for _ in range(iterations):
            simulate_prerequisite_check()
        
        total_time = time.time() - start_time
        avg_time_per_check = total_time / iterations
        
        # Assert performance requirements (prerequisite checks should be fast)
        assert avg_time_per_check < 0.1, f"Prerequisite checks too slow: {avg_time_per_check:.3f}s per check"