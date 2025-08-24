"""
Health check endpoints for GITTE system.
Provides system status, version information, and health monitoring.
"""

import logging
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.services.startup_service import get_startup_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health_check() -> Dict:
    """
    Basic health check endpoint.
    
    Returns:
        Dict with basic health status
    """
    try:
        startup_service = get_startup_service()
        
        # Perform basic database health check
        from src.data.database_factory import health_check as db_health_check
        db_healthy = db_health_check()
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "healthy" if db_healthy else "unhealthy",
            "service": "gitte"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@router.get("/version")
async def version_info() -> Dict:
    """
    Version and build information endpoint.
    
    Returns:
        Dict with version information
    """
    try:
        startup_service = get_startup_service()
        version_info = startup_service.get_version_info()
        
        return {
            "git_sha": version_info["git_sha"],
            "build_ts": version_info["build_ts"],
            "config_hash": version_info["config_hash"],
            "python_version": version_info["python_version"],
            "platform": version_info["platform"],
            "service": "gitte"
        }
        
    except Exception as e:
        logger.error(f"Version info failed: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve version information")


@router.get("/detailed")
async def detailed_health() -> Dict:
    """
    Detailed health check with component status.
    
    Returns:
        Dict with detailed health information
    """
    try:
        startup_service = get_startup_service()
        
        # Get comprehensive health check
        health_results = startup_service.health_check()
        
        # Add current database status
        from src.data.database_factory import health_check as db_health_check
        health_results["database_status"] = {
            "healthy": db_health_check(),
            "checked_at": datetime.utcnow().isoformat()
        }
        
        # Add hook status
        try:
            from src.services.hook_loader import get_hook_loader
            hook_loader = get_hook_loader()
            hook_status = hook_loader.get_hook_status()
            health_results["hook_status"] = hook_status
        except Exception as e:
            health_results["hook_status"] = {"error": str(e)}
        
        return health_results
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/metrics")
async def metrics() -> Dict:
    """
    Basic metrics endpoint for monitoring.
    
    Returns:
        Dict with system metrics
    """
    try:
        import psutil
        import time
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        # Get database metrics
        db_metrics = {}
        try:
            from src.data.database_factory import _db_factory
            if _db_factory._initialized and _db_factory.engine:
                pool = _db_factory.engine.pool
                db_metrics = {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                }
        except Exception as e:
            db_metrics = {"error": str(e)}
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available // (1024 * 1024),
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free_mb": disk.free // (1024 * 1024)
            },
            "database": db_metrics,
            "uptime_seconds": time.time() - get_startup_service().build_timestamp.timestamp()
        }
        
    except ImportError:
        # psutil not available, return basic metrics
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {"status": "metrics_unavailable"},
            "database": {},
            "uptime_seconds": time.time() - get_startup_service().build_timestamp.timestamp()
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics collection failed")


# Add router to main FastAPI app
def setup_health_routes(app):
    """Setup health check routes on FastAPI app."""
    app.include_router(router)