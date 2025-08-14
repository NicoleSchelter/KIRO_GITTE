"""
Caching Service for GITTE UX enhancements.
Provides multi-level caching with TTL, LRU eviction, and cache warming strategies.
"""

import hashlib
import logging
import pickle
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union
import json

from src.services.performance_monitoring_service import performance_monitor

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache levels with different characteristics."""
    MEMORY = "memory"      # Fast, limited size
    DISK = "disk"         # Slower, larger capacity
    DISTRIBUTED = "distributed"  # Shared across instances


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int
    ttl_seconds: Optional[int]
    size_bytes: int
    
    @property
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    @property
    def age_seconds(self) -> float:
        """Get the age of the cache entry in seconds."""
        return (datetime.now() - self.created_at).total_seconds()


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    entry_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        pass
    
    @abstractmethod
    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete cache entry by key."""
        pass
    
    @abstractmethod
    def clear(self) -> int:
        """Clear all cache entries and return count of cleared entries."""
        pass
    
    @abstractmethod
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        pass


class MemoryCacheBackend(CacheBackend):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size_mb: int = 100, max_entries: int = 10000):
        """
        Initialize memory cache backend.
        
        Args:
            max_size_mb: Maximum cache size in megabytes
            max_entries: Maximum number of cache entries
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_entries = max_entries
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            
            self._stats.hits += 1
            return entry
    
    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry."""
        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                old_entry = self._cache[key]
                self._stats.size_bytes -= old_entry.size_bytes
                self._stats.entry_count -= 1
            
            # Check if we need to evict entries
            self._evict_if_needed(entry.size_bytes)
            
            # Add new entry
            self._cache[key] = entry
            self._stats.size_bytes += entry.size_bytes
            self._stats.entry_count += 1
            
            return True
    
    def delete(self, key: str) -> bool:
        """Delete cache entry by key."""
        with self._lock:
            entry = self._cache.pop(key, None)
            if entry:
                self._stats.size_bytes -= entry.size_bytes
                self._stats.entry_count -= 1
                return True
            return False
    
    def clear(self) -> int:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats = CacheStats()
            return count
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size_bytes=self._stats.size_bytes,
                entry_count=self._stats.entry_count
            )
    
    def _evict_if_needed(self, new_entry_size: int):
        """Evict entries if needed to make room for new entry."""
        # Check size limit
        while (self._stats.size_bytes + new_entry_size > self.max_size_bytes and 
               len(self._cache) > 0):
            self._evict_lru()
        
        # Check entry count limit
        while len(self._cache) >= self.max_entries:
            self._evict_lru()
    
    def _evict_lru(self):
        """Evict least recently used entry."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)  # Remove first (oldest)
            self._stats.size_bytes -= entry.size_bytes
            self._stats.entry_count -= 1
            self._stats.evictions += 1


class DiskCacheBackend(CacheBackend):
    """Disk-based cache backend for larger, persistent storage."""
    
    def __init__(self, cache_dir: str = ".cache", max_size_mb: int = 1000):
        """
        Initialize disk cache backend.
        
        Args:
            cache_dir: Directory to store cache files
            max_size_mb: Maximum cache size in megabytes
        """
        import os
        
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._stats = CacheStats()
        self._lock = threading.RLock()
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Load existing cache metadata
        self._load_metadata()
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key."""
        with self._lock:
            file_path = self._get_file_path(key)
            
            try:
                if not os.path.exists(file_path):
                    self._stats.misses += 1
                    return None
                
                with open(file_path, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_expired:
                    os.remove(file_path)
                    self._stats.misses += 1
                    self._stats.evictions += 1
                    return None
                
                entry.last_accessed = datetime.now()
                entry.access_count += 1
                
                # Update file access time
                os.utime(file_path)
                
                self._stats.hits += 1
                return entry
                
            except Exception as e:
                logger.error(f"Failed to read cache entry {key}: {e}")
                self._stats.misses += 1
                return None
    
    def set(self, key: str, entry: CacheEntry) -> bool:
        """Set cache entry."""
        with self._lock:
            file_path = self._get_file_path(key)
            
            try:
                # Remove existing file if present
                if os.path.exists(file_path):
                    old_size = os.path.getsize(file_path)
                    self._stats.size_bytes -= old_size
                    self._stats.entry_count -= 1
                
                # Check if we need to evict entries
                self._evict_if_needed(entry.size_bytes)
                
                # Write new entry
                with open(file_path, 'wb') as f:
                    pickle.dump(entry, f)
                
                actual_size = os.path.getsize(file_path)
                self._stats.size_bytes += actual_size
                self._stats.entry_count += 1
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to write cache entry {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """Delete cache entry by key."""
        with self._lock:
            file_path = self._get_file_path(key)
            
            try:
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    os.remove(file_path)
                    self._stats.size_bytes -= size
                    self._stats.entry_count -= 1
                    return True
                return False
                
            except Exception as e:
                logger.error(f"Failed to delete cache entry {key}: {e}")
                return False
    
    def clear(self) -> int:
        """Clear all cache entries."""
        import os
        import glob
        
        with self._lock:
            cache_files = glob.glob(os.path.join(self.cache_dir, "*.cache"))
            count = 0
            
            for file_path in cache_files:
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to remove cache file {file_path}: {e}")
            
            self._stats = CacheStats()
            return count
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size_bytes=self._stats.size_bytes,
                entry_count=self._stats.entry_count
            )
    
    def _get_file_path(self, key: str) -> str:
        """Get file path for cache key."""
        import os
        
        # Create safe filename from key
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def _load_metadata(self):
        """Load cache metadata from disk."""
        import os
        import glob
        
        cache_files = glob.glob(os.path.join(self.cache_dir, "*.cache"))
        
        total_size = 0
        for file_path in cache_files:
            try:
                total_size += os.path.getsize(file_path)
            except Exception:
                pass
        
        self._stats.size_bytes = total_size
        self._stats.entry_count = len(cache_files)
    
    def _evict_if_needed(self, new_entry_size: int):
        """Evict entries if needed to make room for new entry."""
        import os
        import glob
        
        while self._stats.size_bytes + new_entry_size > self.max_size_bytes:
            # Find oldest file by access time
            cache_files = glob.glob(os.path.join(self.cache_dir, "*.cache"))
            
            if not cache_files:
                break
            
            oldest_file = min(cache_files, key=lambda f: os.path.getatime(f))
            
            try:
                size = os.path.getsize(oldest_file)
                os.remove(oldest_file)
                self._stats.size_bytes -= size
                self._stats.entry_count -= 1
                self._stats.evictions += 1
            except Exception as e:
                logger.error(f"Failed to evict cache file {oldest_file}: {e}")
                break


class MultiLevelCachingService:
    """Multi-level caching service with memory and disk backends."""
    
    def __init__(
        self,
        memory_cache_mb: int = 100,
        disk_cache_mb: int = 1000,
        default_ttl_seconds: int = 3600
    ):
        """
        Initialize multi-level caching service.
        
        Args:
            memory_cache_mb: Memory cache size in MB
            disk_cache_mb: Disk cache size in MB
            default_ttl_seconds: Default TTL for cache entries
        """
        self.default_ttl_seconds = default_ttl_seconds
        
        # Initialize cache backends
        self.memory_cache = MemoryCacheBackend(memory_cache_mb)
        self.disk_cache = DiskCacheBackend(max_size_mb=disk_cache_mb)
        
        # Cache warming configuration
        self.warm_cache_on_startup = True
        self.warm_cache_patterns: List[str] = []
        
        logger.info(
            f"Multi-level caching service initialized: "
            f"Memory={memory_cache_mb}MB, Disk={disk_cache_mb}MB"
        )
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache, checking memory first, then disk.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        # Try memory cache first
        entry = self.memory_cache.get(key)
        if entry:
            performance_monitor.increment_counter("cache_hits", 1, {"level": "memory"})
            return entry.value
        
        # Try disk cache
        entry = self.disk_cache.get(key)
        if entry:
            # Promote to memory cache
            self.memory_cache.set(key, entry)
            performance_monitor.increment_counter("cache_hits", 1, {"level": "disk"})
            return entry.value
        
        performance_monitor.increment_counter("cache_misses", 1)
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        cache_level: CacheLevel = CacheLevel.MEMORY
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live (uses default if None)
            cache_level: Which cache level to use
            
        Returns:
            True if successfully cached
        """
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl_seconds
        
        # Calculate size
        try:
            size_bytes = len(pickle.dumps(value))
        except Exception:
            size_bytes = 1024  # Estimate if serialization fails
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=0,
            ttl_seconds=ttl_seconds,
            size_bytes=size_bytes
        )
        
        success = False
        
        if cache_level == CacheLevel.MEMORY:
            success = self.memory_cache.set(key, entry)
        elif cache_level == CacheLevel.DISK:
            success = self.disk_cache.set(key, entry)
        else:
            # Store in both levels
            success = (
                self.memory_cache.set(key, entry) and
                self.disk_cache.set(key, entry)
            )
        
        if success:
            performance_monitor.increment_counter("cache_sets", 1, {"level": cache_level.value})
        
        return success
    
    def delete(self, key: str) -> bool:
        """
        Delete value from all cache levels.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted from at least one level
        """
        memory_deleted = self.memory_cache.delete(key)
        disk_deleted = self.disk_cache.delete(key)
        
        return memory_deleted or disk_deleted
    
    def clear(self, cache_level: Optional[CacheLevel] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            cache_level: Specific level to clear (all if None)
            
        Returns:
            Number of entries cleared
        """
        total_cleared = 0
        
        if cache_level is None or cache_level == CacheLevel.MEMORY:
            total_cleared += self.memory_cache.clear()
        
        if cache_level is None or cache_level == CacheLevel.DISK:
            total_cleared += self.disk_cache.clear()
        
        return total_cleared
    
    def get_stats(self) -> Dict[str, CacheStats]:
        """Get statistics for all cache levels."""
        return {
            "memory": self.memory_cache.get_stats(),
            "disk": self.disk_cache.get_stats()
        }
    
    def warm_cache(self, warm_functions: List[Callable] = None):
        """
        Warm cache by pre-loading frequently accessed data.
        
        Args:
            warm_functions: List of functions to call for cache warming
        """
        if not warm_functions:
            return
        
        logger.info(f"Warming cache with {len(warm_functions)} functions")
        
        for func in warm_functions:
            try:
                func()
            except Exception as e:
                logger.error(f"Failed to warm cache with {func.__name__}: {e}")
    
    def cleanup_expired(self) -> int:
        """
        Clean up expired cache entries.
        
        Returns:
            Number of entries cleaned up
        """
        # For now, expired entries are cleaned up on access
        # This could be enhanced with a background cleanup task
        return 0


# Global caching service instance
cache_service = MultiLevelCachingService()


def cached(
    key_func: Optional[Callable] = None,
    ttl_seconds: Optional[int] = None,
    cache_level: CacheLevel = CacheLevel.MEMORY
):
    """
    Decorator to cache function results.
    
    Args:
        key_func: Function to generate cache key from args/kwargs
        ttl_seconds: Time to live for cached result
        cache_level: Which cache level to use
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            with performance_monitor.time_operation(f"cache_miss_{func.__name__}"):
                result = func(*args, **kwargs)
            
            cache_service.set(cache_key, result, ttl_seconds, cache_level)
            return result
        
        return wrapper
    return decorator


def cache_key_from_args(*args, **kwargs) -> str:
    """Generate cache key from function arguments."""
    key_parts = []
    key_parts.extend(str(arg) for arg in args)
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


def get_cache_stats() -> Dict[str, CacheStats]:
    """Get cache statistics."""
    return cache_service.get_stats()


def clear_cache(cache_level: Optional[CacheLevel] = None) -> int:
    """Clear cache entries."""
    return cache_service.clear(cache_level)


def warm_cache(warm_functions: List[Callable]):
    """Warm cache with pre-loaded data."""
    cache_service.warm_cache(warm_functions)