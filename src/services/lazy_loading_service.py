"""
Lazy Loading Service for GITTE UX enhancements.
Provides lazy initialization of expensive resources like ML models and external dependencies.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
from functools import wraps

logger = logging.getLogger(__name__)


class ResourceState(Enum):
    """States of lazy-loaded resources."""
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    FAILED = "failed"


@dataclass
class ResourceInfo:
    """Information about a lazy-loaded resource."""
    name: str
    state: ResourceState
    instance: Optional[Any] = None
    error: Optional[str] = None
    load_time: Optional[float] = None
    last_accessed: Optional[float] = None
    access_count: int = 0


class LazyResource(ABC):
    """Abstract base class for lazy-loaded resources."""
    
    @abstractmethod
    def load(self) -> Any:
        """Load and return the resource."""
        pass
    
    @abstractmethod
    def unload(self):
        """Unload the resource to free memory."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the resource."""
        pass
    
    @property
    def is_expensive(self) -> bool:
        """Whether this resource is expensive to load."""
        return True


class PersonDetectionModel(LazyResource):
    """Lazy-loaded person detection model."""
    
    def __init__(self):
        self._model = None
        self._hog_descriptor = None
    
    @property
    def name(self) -> str:
        return "person_detection_model"
    
    def load(self) -> Any:
        """Load person detection models."""
        try:
            import cv2
            
            # Load HOG descriptor for person detection
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            self._hog_descriptor = hog
            
            logger.info("Person detection model loaded successfully")
            return self._hog_descriptor
            
        except Exception as e:
            logger.error(f"Failed to load person detection model: {e}")
            raise
    
    def unload(self):
        """Unload person detection model."""
        self._hog_descriptor = None
        logger.info("Person detection model unloaded")
    
    def get_hog_descriptor(self):
        """Get the HOG descriptor instance."""
        return self._hog_descriptor


class BackgroundRemovalModel(LazyResource):
    """Lazy-loaded background removal model."""
    
    def __init__(self, model_name: str = "u2net"):
        self.model_name = model_name
        self._session = None
    
    @property
    def name(self) -> str:
        return f"background_removal_{self.model_name}"
    
    def load(self) -> Any:
        """Load background removal model."""
        try:
            from rembg import new_session
            
            self._session = new_session(self.model_name)
            logger.info(f"Background removal model '{self.model_name}' loaded successfully")
            return self._session
            
        except ImportError:
            logger.warning("rembg library not available, background removal will use fallback")
            return None
        except Exception as e:
            logger.error(f"Failed to load background removal model '{self.model_name}': {e}")
            raise
    
    def unload(self):
        """Unload background removal model."""
        self._session = None
        logger.info(f"Background removal model '{self.model_name}' unloaded")
    
    def get_session(self):
        """Get the rembg session instance."""
        return self._session


class DatabaseConnectionPool(LazyResource):
    """Lazy-loaded database connection pool."""
    
    def __init__(self, dsn: str, pool_size: int = 5):
        self.dsn = dsn
        self.pool_size = pool_size
        self._engine = None
    
    @property
    def name(self) -> str:
        return "database_connection_pool"
    
    @property
    def is_expensive(self) -> bool:
        return False  # Database connections are not as expensive as ML models
    
    def load(self) -> Any:
        """Create database connection pool."""
        try:
            from sqlalchemy import create_engine
            
            self._engine = create_engine(
                self.dsn,
                pool_size=self.pool_size,
                pool_pre_ping=True,
                pool_recycle=3600  # Recycle connections every hour
            )
            
            logger.info(f"Database connection pool created with {self.pool_size} connections")
            return self._engine
            
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise
    
    def unload(self):
        """Close database connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            logger.info("Database connection pool closed")
    
    def get_engine(self):
        """Get the SQLAlchemy engine instance."""
        return self._engine


class LazyLoadingService:
    """Service for managing lazy-loaded resources."""
    
    def __init__(self):
        self._resources: Dict[str, ResourceInfo] = {}
        self._resource_instances: Dict[str, LazyResource] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._global_lock = threading.Lock()
        
        # Configuration
        self.auto_unload_after_seconds = 300  # 5 minutes
        self.max_concurrent_loads = 2
        self._currently_loading = 0
        
        logger.info("Lazy loading service initialized")
    
    def register_resource(self, resource: LazyResource):
        """
        Register a lazy-loaded resource.
        
        Args:
            resource: LazyResource instance to register
        """
        name = resource.name
        
        with self._global_lock:
            self._resource_instances[name] = resource
            self._resources[name] = ResourceInfo(name=name, state=ResourceState.NOT_LOADED)
            self._locks[name] = threading.Lock()
        
        logger.info(f"Registered lazy resource: {name}")
    
    def get_resource(self, name: str, timeout_seconds: int = 30) -> Any:
        """
        Get a lazy-loaded resource, loading it if necessary.
        
        Args:
            name: Name of the resource
            timeout_seconds: Maximum time to wait for loading
            
        Returns:
            The loaded resource instance
            
        Raises:
            ValueError: If resource is not registered
            TimeoutError: If loading takes too long
            RuntimeError: If loading fails
        """
        if name not in self._resource_instances:
            raise ValueError(f"Resource '{name}' is not registered")
        
        resource_info = self._resources[name]
        resource_instance = self._resource_instances[name]
        
        # Update access statistics
        resource_info.last_accessed = time.time()
        resource_info.access_count += 1
        
        # If already loaded, return immediately
        if resource_info.state == ResourceState.LOADED and resource_info.instance is not None:
            return resource_info.instance
        
        # If failed previously, try to reload
        if resource_info.state == ResourceState.FAILED:
            logger.info(f"Retrying failed resource: {name}")
            resource_info.state = ResourceState.NOT_LOADED
        
        # Load the resource
        with self._locks[name]:
            # Double-check after acquiring lock
            if resource_info.state == ResourceState.LOADED and resource_info.instance is not None:
                return resource_info.instance
            
            if resource_info.state == ResourceState.LOADING:
                # Another thread is loading, wait for it
                start_time = time.time()
                while (resource_info.state == ResourceState.LOADING and 
                       time.time() - start_time < timeout_seconds):
                    time.sleep(0.1)
                
                if resource_info.state == ResourceState.LOADED:
                    return resource_info.instance
                elif resource_info.state == ResourceState.LOADING:
                    raise TimeoutError(f"Timeout waiting for resource '{name}' to load")
                else:
                    raise RuntimeError(f"Failed to load resource '{name}': {resource_info.error}")
            
            # Check if we can start loading (respect concurrent load limit)
            if resource_instance.is_expensive:
                while self._currently_loading >= self.max_concurrent_loads:
                    time.sleep(0.1)
                    if time.time() - resource_info.last_accessed > timeout_seconds:
                        raise TimeoutError(f"Timeout waiting to start loading resource '{name}'")
            
            # Start loading
            resource_info.state = ResourceState.LOADING
            if resource_instance.is_expensive:
                self._currently_loading += 1
            
            try:
                logger.info(f"Loading resource: {name}")
                start_time = time.time()
                
                instance = resource_instance.load()
                
                load_time = time.time() - start_time
                resource_info.instance = instance
                resource_info.state = ResourceState.LOADED
                resource_info.load_time = load_time
                resource_info.error = None
                
                logger.info(f"Resource '{name}' loaded successfully in {load_time:.2f}s")
                return instance
                
            except Exception as e:
                resource_info.state = ResourceState.FAILED
                resource_info.error = str(e)
                resource_info.instance = None
                
                logger.error(f"Failed to load resource '{name}': {e}")
                raise RuntimeError(f"Failed to load resource '{name}': {e}") from e
                
            finally:
                if resource_instance.is_expensive:
                    self._currently_loading -= 1
    
    def unload_resource(self, name: str):
        """
        Unload a resource to free memory.
        
        Args:
            name: Name of the resource to unload
        """
        if name not in self._resource_instances:
            logger.warning(f"Cannot unload unknown resource: {name}")
            return
        
        resource_info = self._resources[name]
        resource_instance = self._resource_instances[name]
        
        with self._locks[name]:
            if resource_info.state == ResourceState.LOADED:
                try:
                    resource_instance.unload()
                    resource_info.state = ResourceState.NOT_LOADED
                    resource_info.instance = None
                    logger.info(f"Resource '{name}' unloaded successfully")
                except Exception as e:
                    logger.error(f"Error unloading resource '{name}': {e}")
    
    def unload_unused_resources(self, max_idle_seconds: int = None):
        """
        Unload resources that haven't been accessed recently.
        
        Args:
            max_idle_seconds: Maximum idle time before unloading (uses default if None)
        """
        if max_idle_seconds is None:
            max_idle_seconds = self.auto_unload_after_seconds
        
        current_time = time.time()
        unloaded_count = 0
        
        for name, resource_info in self._resources.items():
            if (resource_info.state == ResourceState.LOADED and 
                resource_info.last_accessed and
                current_time - resource_info.last_accessed > max_idle_seconds):
                
                self.unload_resource(name)
                unloaded_count += 1
        
        if unloaded_count > 0:
            logger.info(f"Unloaded {unloaded_count} unused resources")
    
    def get_resource_stats(self) -> Dict[str, Any]:
        """Get statistics about registered resources."""
        stats = {
            "total_resources": len(self._resources),
            "loaded_resources": 0,
            "failed_resources": 0,
            "loading_resources": 0,
            "currently_loading": self._currently_loading,
            "resources": {}
        }
        
        for name, resource_info in self._resources.items():
            if resource_info.state == ResourceState.LOADED:
                stats["loaded_resources"] += 1
            elif resource_info.state == ResourceState.FAILED:
                stats["failed_resources"] += 1
            elif resource_info.state == ResourceState.LOADING:
                stats["loading_resources"] += 1
            
            stats["resources"][name] = {
                "state": resource_info.state.value,
                "access_count": resource_info.access_count,
                "load_time": resource_info.load_time,
                "last_accessed": resource_info.last_accessed,
                "error": resource_info.error
            }
        
        return stats
    
    def preload_resources(self, resource_names: List[str] = None):
        """
        Preload specified resources or all registered resources.
        
        Args:
            resource_names: List of resource names to preload (all if None)
        """
        if resource_names is None:
            resource_names = list(self._resource_instances.keys())
        
        logger.info(f"Preloading {len(resource_names)} resources")
        
        for name in resource_names:
            try:
                self.get_resource(name)
            except Exception as e:
                logger.error(f"Failed to preload resource '{name}': {e}")
    
    def shutdown(self):
        """Shutdown the lazy loading service and unload all resources."""
        logger.info("Shutting down lazy loading service")
        
        for name in list(self._resource_instances.keys()):
            self.unload_resource(name)
        
        self._resources.clear()
        self._resource_instances.clear()
        self._locks.clear()


# Global lazy loading service instance
lazy_loader = LazyLoadingService()


def lazy_resource(resource_name: str, timeout_seconds: int = 30):
    """
    Decorator to inject lazy-loaded resources into functions.
    
    Args:
        resource_name: Name of the resource to inject
        timeout_seconds: Maximum time to wait for loading
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            resource = lazy_loader.get_resource(resource_name, timeout_seconds)
            return func(resource, *args, **kwargs)
        return wrapper
    return decorator


def register_default_resources():
    """Register default lazy-loaded resources."""
    # Register person detection model
    lazy_loader.register_resource(PersonDetectionModel())
    
    # Register background removal models
    lazy_loader.register_resource(BackgroundRemovalModel("u2net"))
    lazy_loader.register_resource(BackgroundRemovalModel("silueta"))
    
    logger.info("Default lazy resources registered")


def get_resource_stats() -> Dict[str, Any]:
    """Get statistics about lazy-loaded resources."""
    return lazy_loader.get_resource_stats()


def preload_critical_resources():
    """Preload critical resources for better performance."""
    critical_resources = ["person_detection_model"]
    lazy_loader.preload_resources(critical_resources)


def cleanup_unused_resources():
    """Clean up unused resources to free memory."""
    lazy_loader.unload_unused_resources()