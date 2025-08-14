"""
Performance Monitoring Service for GITTE UX enhancements.
Provides comprehensive performance monitoring, metrics collection, and optimization.
"""

import logging
import time
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union
import psutil
import asyncio

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of performance metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    metric_type: MetricType
    value: Union[int, float]
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class TimingResult:
    """Result of timing measurement."""
    operation: str
    duration_ms: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    """System resource usage snapshot."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0


@dataclass
class PerformanceThresholds:
    """Performance thresholds for alerting."""
    max_response_time_ms: float = 5000.0
    max_cpu_percent: float = 80.0
    max_memory_percent: float = 85.0
    max_disk_usage_percent: float = 90.0
    min_success_rate: float = 0.95


class PerformanceMonitoringService:
    """Service for monitoring and optimizing system performance."""
    
    def __init__(self, thresholds: PerformanceThresholds = None):
        """
        Initialize performance monitoring service.
        
        Args:
            thresholds: Performance thresholds for alerting
        """
        self.thresholds = thresholds or PerformanceThresholds()
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.timings: deque = deque(maxlen=10000)
        self.resource_history: deque = deque(maxlen=1440)  # 24 hours at 1-minute intervals
        
        # Performance counters
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread = None
        self._lock = threading.Lock()
        
        # Cache for expensive operations
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)
        
        logger.info("Performance monitoring service initialized")
    
    def start_monitoring(self, interval_seconds: int = 60):
        """
        Start continuous performance monitoring.
        
        Args:
            interval_seconds: Monitoring interval in seconds
        """
        if self._monitoring_active:
            logger.warning("Performance monitoring already active")
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info(f"Started performance monitoring with {interval_seconds}s interval")
    
    def stop_monitoring(self):
        """Stop continuous performance monitoring."""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        logger.info("Stopped performance monitoring")
    
    def record_metric(
        self,
        name: str,
        value: Union[int, float],
        metric_type: MetricType,
        labels: Dict[str, str] = None,
        unit: str = ""
    ):
        """
        Record a performance metric.
        
        Args:
            name: Metric name
            value: Metric value
            metric_type: Type of metric
            labels: Optional labels for the metric
            unit: Unit of measurement
        """
        metric = PerformanceMetric(
            name=name,
            metric_type=metric_type,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            unit=unit
        )
        
        with self._lock:
            self.metrics[name].append(metric)
            
            # Update aggregated metrics
            if metric_type == MetricType.COUNTER:
                self.counters[name] += value
            elif metric_type == MetricType.GAUGE:
                self.gauges[name] = value
            elif metric_type == MetricType.HISTOGRAM:
                self.histograms[name].append(value)
                # Keep only last 1000 values
                if len(self.histograms[name]) > 1000:
                    self.histograms[name] = self.histograms[name][-1000:]
    
    def increment_counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, labels)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None, unit: str = ""):
        """Set a gauge metric."""
        self.record_metric(name, value, MetricType.GAUGE, labels, unit)
    
    def record_histogram(self, name: str, value: float, labels: Dict[str, str] = None, unit: str = ""):
        """Record a histogram value."""
        self.record_metric(name, value, MetricType.HISTOGRAM, labels, unit)
    
    @contextmanager
    def time_operation(self, operation: str, labels: Dict[str, str] = None):
        """
        Context manager for timing operations.
        
        Args:
            operation: Name of the operation being timed
            labels: Optional labels for the timing metric
        """
        start_time = time.time()
        success = True
        error = None
        metadata = {}
        
        try:
            yield metadata
        except Exception as e:
            success = False
            error = str(e)
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            timing_result = TimingResult(
                operation=operation,
                duration_ms=duration_ms,
                success=success,
                error=error,
                metadata=metadata
            )
            
            with self._lock:
                self.timings.append(timing_result)
            
            # Record as histogram metric
            self.record_histogram(
                f"{operation}_duration_ms",
                duration_ms,
                labels,
                "milliseconds"
            )
            
            # Record success/failure counter
            status_labels = {**(labels or {}), "success": str(success)}
            self.increment_counter(f"{operation}_total", 1, status_labels)
            
            # Check performance thresholds
            if duration_ms > self.thresholds.max_response_time_ms:
                logger.warning(
                    f"Operation {operation} exceeded response time threshold: "
                    f"{duration_ms:.2f}ms > {self.thresholds.max_response_time_ms}ms"
                )
    
    def get_resource_usage(self) -> ResourceUsage:
        """Get current system resource usage."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024 ** 3)
            
            # Network usage (if available)
            network_bytes_sent = 0
            network_bytes_recv = 0
            try:
                network = psutil.net_io_counters()
                network_bytes_sent = network.bytes_sent
                network_bytes_recv = network.bytes_recv
            except Exception:
                pass  # Network stats not available on all systems
            
            return ResourceUsage(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv
            )
            
        except Exception as e:
            logger.error(f"Failed to get resource usage: {e}")
            return ResourceUsage(
                timestamp=datetime.now(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                disk_usage_percent=0.0,
                disk_free_gb=0.0
            )
    
    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """
        Get performance summary for the specified time period.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dict with performance summary
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Filter recent timings
        recent_timings = [
            t for t in self.timings 
            if t.metadata.get('timestamp', datetime.now()) > cutoff_time
        ]
        
        # Calculate timing statistics
        timing_stats = {}
        if recent_timings:
            operations = defaultdict(list)
            for timing in recent_timings:
                operations[timing.operation].append(timing.duration_ms)
            
            for operation, durations in operations.items():
                timing_stats[operation] = {
                    "count": len(durations),
                    "avg_ms": sum(durations) / len(durations),
                    "min_ms": min(durations),
                    "max_ms": max(durations),
                    "p95_ms": self._percentile(durations, 95),
                    "p99_ms": self._percentile(durations, 99)
                }
        
        # Get recent resource usage
        recent_resources = [
            r for r in self.resource_history 
            if r.timestamp > cutoff_time
        ]
        
        resource_stats = {}
        if recent_resources:
            cpu_values = [r.cpu_percent for r in recent_resources]
            memory_values = [r.memory_percent for r in recent_resources]
            
            resource_stats = {
                "cpu": {
                    "avg_percent": sum(cpu_values) / len(cpu_values),
                    "max_percent": max(cpu_values),
                    "current_percent": recent_resources[-1].cpu_percent
                },
                "memory": {
                    "avg_percent": sum(memory_values) / len(memory_values),
                    "max_percent": max(memory_values),
                    "current_percent": recent_resources[-1].memory_percent,
                    "current_used_mb": recent_resources[-1].memory_used_mb
                },
                "disk": {
                    "current_usage_percent": recent_resources[-1].disk_usage_percent,
                    "current_free_gb": recent_resources[-1].disk_free_gb
                }
            }
        
        return {
            "time_period_hours": hours,
            "timing_stats": timing_stats,
            "resource_stats": resource_stats,
            "total_operations": len(recent_timings),
            "cache_stats": self.get_cache_stats(),
            "thresholds": {
                "max_response_time_ms": self.thresholds.max_response_time_ms,
                "max_cpu_percent": self.thresholds.max_cpu_percent,
                "max_memory_percent": self.thresholds.max_memory_percent
            }
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        now = datetime.now()
        valid_entries = 0
        expired_entries = 0
        
        for key, timestamp in self._cache_timestamps.items():
            if now - timestamp < self._cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_minutes": self._cache_ttl.total_seconds() / 60
        }
    
    def cache_get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None
        
        timestamp = self._cache_timestamps.get(key)
        if not timestamp or datetime.now() - timestamp > self._cache_ttl:
            # Cache expired
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            return None
        
        return self._cache[key]
    
    def cache_set(self, key: str, value: Any):
        """Set value in cache with timestamp."""
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.now()
    
    def cache_clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop running in background thread."""
        while self._monitoring_active:
            try:
                # Collect resource usage
                resource_usage = self.get_resource_usage()
                
                with self._lock:
                    self.resource_history.append(resource_usage)
                
                # Record resource metrics
                self.set_gauge("cpu_percent", resource_usage.cpu_percent, unit="percent")
                self.set_gauge("memory_percent", resource_usage.memory_percent, unit="percent")
                self.set_gauge("memory_used_mb", resource_usage.memory_used_mb, unit="megabytes")
                self.set_gauge("disk_usage_percent", resource_usage.disk_usage_percent, unit="percent")
                self.set_gauge("disk_free_gb", resource_usage.disk_free_gb, unit="gigabytes")
                
                # Check thresholds and log warnings
                if resource_usage.cpu_percent > self.thresholds.max_cpu_percent:
                    logger.warning(f"High CPU usage: {resource_usage.cpu_percent:.1f}%")
                
                if resource_usage.memory_percent > self.thresholds.max_memory_percent:
                    logger.warning(f"High memory usage: {resource_usage.memory_percent:.1f}%")
                
                if resource_usage.disk_usage_percent > self.thresholds.max_disk_usage_percent:
                    logger.warning(f"High disk usage: {resource_usage.disk_usage_percent:.1f}%")
                
                # Clean up expired cache entries
                self._cleanup_expired_cache()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            time.sleep(interval_seconds)
    
    def _cleanup_expired_cache(self):
        """Clean up expired cache entries."""
        now = datetime.now()
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if now - timestamp > self._cache_ttl
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


# Global performance monitoring service instance
performance_monitor = PerformanceMonitoringService()


def monitor_performance(operation: str, labels: Dict[str, str] = None):
    """
    Decorator to monitor performance of functions.
    
    Args:
        operation: Name of the operation being monitored
        labels: Optional labels for the metric
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with performance_monitor.time_operation(operation, labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def monitor_async_performance(operation: str, labels: Dict[str, str] = None):
    """
    Decorator to monitor performance of async functions.
    
    Args:
        operation: Name of the operation being monitored
        labels: Optional labels for the metric
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error = None
            
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                # Record timing
                performance_monitor.record_histogram(
                    f"{operation}_duration_ms",
                    duration_ms,
                    labels,
                    "milliseconds"
                )
                
                # Record success/failure
                status_labels = {**(labels or {}), "success": str(success)}
                performance_monitor.increment_counter(f"{operation}_total", 1, status_labels)
        
        return wrapper
    return decorator


def cached_operation(cache_key_func: Callable = None, ttl_minutes: int = 5):
    """
    Decorator to cache expensive operations.
    
    Args:
        cache_key_func: Function to generate cache key from args/kwargs
        ttl_minutes: Time to live for cache entries in minutes
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                cache_key = cache_key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = performance_monitor.cache_get(cache_key)
            if cached_result is not None:
                performance_monitor.increment_counter("cache_hits", 1, {"operation": func.__name__})
                return cached_result
            
            # Execute function and cache result
            performance_monitor.increment_counter("cache_misses", 1, {"operation": func.__name__})
            result = func(*args, **kwargs)
            performance_monitor.cache_set(cache_key, result)
            
            return result
        return wrapper
    return decorator


def get_performance_summary(hours: int = 1) -> Dict[str, Any]:
    """Get performance summary for the specified time period."""
    return performance_monitor.get_performance_summary(hours)


def start_performance_monitoring(interval_seconds: int = 60):
    """Start continuous performance monitoring."""
    performance_monitor.start_monitoring(interval_seconds)


def stop_performance_monitoring():
    """Stop continuous performance monitoring."""
    performance_monitor.stop_monitoring()