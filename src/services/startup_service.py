"""
Startup service for GITTE system.
Handles cache purging, version checking, and system initialization.
"""

import hashlib
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StartupService:
    """Service for handling application startup tasks."""
    
    def __init__(self):
        self.build_timestamp = datetime.utcnow()
        self.git_sha = self._get_git_sha()
        self.config_hash = self._get_config_hash()
        
    def purge_caches(self) -> Dict[str, bool]:
        """
        Purge various caches to ensure fresh start.
        
        Returns:
            Dict mapping cache types to purge success status
        """
        logger.info("startup: purging caches for fresh build...")
        
        results = {}
        
        # Purge __pycache__ directories
        results["pycache"] = self._purge_pycache()
        
        # Purge pytest cache
        results["pytest_cache"] = self._purge_pytest_cache()
        
        # Purge pip cache (if local vendoring is used)
        results["pip_cache"] = self._purge_pip_cache()
        
        # Purge any local wheels
        results["local_wheels"] = self._purge_local_wheels()
        
        return results
    
    def _purge_pycache(self) -> bool:
        """Purge all __pycache__ directories."""
        try:
            for root, dirs, files in os.walk("."):
                if "__pycache__" in dirs:
                    pycache_path = Path(root) / "__pycache__"
                    shutil.rmtree(pycache_path, ignore_errors=True)
                    logger.debug(f"Purged {pycache_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to purge __pycache__: {e}")
            return False
    
    def _purge_pytest_cache(self) -> bool:
        """Purge .pytest_cache directory."""
        try:
            pytest_cache = Path(".pytest_cache")
            if pytest_cache.exists():
                shutil.rmtree(pytest_cache, ignore_errors=True)
                logger.debug("Purged .pytest_cache")
            return True
        except Exception as e:
            logger.error(f"Failed to purge pytest cache: {e}")
            return False
    
    def _purge_pip_cache(self) -> bool:
        """Purge pip cache if local vendoring is detected."""
        try:
            # Check for common pip cache locations
            cache_dirs = [
                Path.home() / ".cache" / "pip",
                Path.home() / "AppData" / "Local" / "pip" / "Cache",  # Windows
                Path(".pip_cache"),  # Local cache
            ]
            
            purged_any = False
            for cache_dir in cache_dirs:
                if cache_dir.exists():
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    logger.debug(f"Purged pip cache: {cache_dir}")
                    purged_any = True
            
            return True
        except Exception as e:
            logger.error(f"Failed to purge pip cache: {e}")
            return False
    
    def _purge_local_wheels(self) -> bool:
        """Purge any local wheel files."""
        try:
            wheel_files = list(Path(".").glob("**/*.whl"))
            for wheel_file in wheel_files:
                try:
                    wheel_file.unlink()
                    logger.debug(f"Purged wheel: {wheel_file}")
                except Exception:
                    pass
            return True
        except Exception as e:
            logger.error(f"Failed to purge local wheels: {e}")
            return False
    
    def _get_git_sha(self) -> Optional[str]:
        """Get current Git commit SHA."""
        try:
            result = subprocess.run([
                "git", "rev-parse", "HEAD"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.warning("Could not get Git SHA")
                return None
        except Exception as e:
            logger.warning(f"Could not get Git SHA: {e}")
            return None
    
    def _get_config_hash(self) -> str:
        """Get hash of current configuration."""
        try:
            config_files = [
                "config/config.py",
                ".env",
                "pyproject.toml",
                "requirements.txt"
            ]
            
            config_content = ""
            for config_file in config_files:
                config_path = Path(config_file)
                if config_path.exists():
                    config_content += config_path.read_text(encoding='utf-8')
            
            return hashlib.sha256(config_content.encode('utf-8')).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Could not generate config hash: {e}")
            return "unknown"
    
    def validate_import_paths(self) -> Dict[str, bool]:
        """
        Validate that imports resolve to current build directory.
        
        Returns:
            Dict with validation results
        """
        logger.info("startup: validating import paths...")
        
        results = {}
        current_dir = Path.cwd()
        
        # Check key modules
        modules_to_check = [
            "src.data.database_factory",
            "src.logic.consent_logic", 
            "src.ui.consent_ui",
            "config.config"
        ]
        
        for module_name in modules_to_check:
            try:
                module = __import__(module_name, fromlist=[''])
                module_file = getattr(module, '__file__', None)
                
                if module_file:
                    module_path = Path(module_file).resolve()
                    is_in_current_build = current_dir in module_path.parents or module_path.parent == current_dir
                    results[module_name] = is_in_current_build
                    
                    if not is_in_current_build:
                        logger.error(f"Module {module_name} resolves outside current build: {module_path}")
                else:
                    results[module_name] = False
                    logger.warning(f"Module {module_name} has no __file__ attribute")
                    
            except ImportError as e:
                results[module_name] = False
                logger.error(f"Could not import {module_name}: {e}")
            except Exception as e:
                results[module_name] = False
                logger.error(f"Error checking {module_name}: {e}")
        
        return results
    
    def get_version_info(self) -> Dict:
        """
        Get version and build information.
        
        Returns:
            Dict with version information
        """
        return {
            "git_sha": self.git_sha,
            "build_ts": self.build_timestamp.isoformat(),
            "config_hash": self.config_hash,
            "python_version": sys.version,
            "platform": sys.platform
        }
    
    def health_check(self) -> Dict:
        """
        Perform startup health check.
        
        Returns:
            Dict with health check results
        """
        logger.info("startup: performing health check...")
        
        health_results = {
            "cache_purge": self.purge_caches(),
            "import_validation": self.validate_import_paths(),
            "version_info": self.get_version_info(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Overall health status
        cache_ok = all(health_results["cache_purge"].values())
        imports_ok = all(health_results["import_validation"].values())
        
        health_results["overall_status"] = "healthy" if (cache_ok and imports_ok) else "degraded"
        
        # Log results
        if health_results["overall_status"] == "healthy":
            logger.info("startup: health check passed")
        else:
            logger.warning("startup: health check found issues")
            
        logger.info(f"startup: Git commit SHA: {self.git_sha}")
        logger.info(f"startup: Build timestamp: {self.build_timestamp}")
        logger.info(f"startup: Config hash: {self.config_hash}")
        
        return health_results
    
    def initialize_providers(self) -> Dict:
        """
        Initialize service providers and log their versions.
        
        Returns:
            Dict with provider initialization results
        """
        logger.info("startup: initializing service providers...")
        
        results = {}
        
        # Initialize database factory
        try:
            from src.data.database_factory import initialize_database, _db_factory
            initialize_database()
            results["database_factory"] = {
                "status": "initialized",
                "dsn_masked": _db_factory._mask_dsn(_db_factory.engine.url) if _db_factory.engine else "not_available"
            }
            logger.info(f"startup: database factory initialized")
        except Exception as e:
            results["database_factory"] = {"status": "failed", "error": str(e)}
            logger.error(f"startup: database factory initialization failed: {e}")
        
        # Initialize hook loader
        try:
            from src.services.hook_loader import initialize_hooks
            hook_results = initialize_hooks()
            results["hook_loader"] = {
                "status": "initialized",
                "loaded_hooks": len(hook_results["loaded_hooks"]),
                "failed_hooks": len(hook_results["failed_hooks"]),
                "execution_order": hook_results["execution_order"]
            }
            logger.info(f"startup: hook loader initialized with {len(hook_results['loaded_hooks'])} hooks")
        except Exception as e:
            results["hook_loader"] = {"status": "failed", "error": str(e)}
            logger.error(f"startup: hook loader initialization failed: {e}")
        
        return results


# Global startup service instance
_startup_service = None


def get_startup_service() -> StartupService:
    """Get the global startup service instance."""
    global _startup_service
    if _startup_service is None:
        _startup_service = StartupService()
    return _startup_service


def perform_startup_sequence() -> Dict:
    """
    Perform complete startup sequence.
    
    Returns:
        Dict with startup results
    """
    startup_service = get_startup_service()
    
    logger.info("=== GITTE System Startup ===")
    
    # Perform health check (includes cache purging)
    health_results = startup_service.health_check()
    
    # Initialize providers
    provider_results = startup_service.initialize_providers()
    
    # Combine results
    startup_results = {
        "health_check": health_results,
        "providers": provider_results,
        "startup_time": datetime.utcnow().isoformat(),
        "success": health_results["overall_status"] == "healthy"
    }
    
    if startup_results["success"]:
        logger.info("=== GITTE System Startup Complete ===")
    else:
        logger.warning("=== GITTE System Startup Complete (with issues) ===")
    
    return startup_results