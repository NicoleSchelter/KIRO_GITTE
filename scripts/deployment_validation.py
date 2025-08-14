#!/usr/bin/env python3
"""
Deployment validation script for GITTE UX enhancements.
Validates that all UX enhancement features are working correctly after deployment.
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
import psycopg2
import redis
import requests
from PIL import Image

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentValidator:
    """Validates GITTE UX enhancements deployment."""
    
    def __init__(self, base_url: str = "http://localhost:8501"):
        self.base_url = base_url
        self.api_base = urljoin(base_url, "/api/v1")
        self.ux_base = urljoin(base_url, "/ux")
        self.session = None
        self.validation_results = []
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, message: str = "", details: Dict = None):
        """Log validation result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": time.time()
        }
        self.validation_results.append(result)
        
        level = logging.INFO if success else logging.ERROR
        status = "PASS" if success else "FAIL"
        logger.log(level, f"[{status}] {test_name}: {message}")
    
    async def validate_basic_connectivity(self) -> bool:
        """Validate basic application connectivity."""
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.log_result(
                        "basic_connectivity",
                        True,
                        "Application is responding",
                        {"status_code": response.status, "health_data": data}
                    )
                    return True
                else:
                    self.log_result(
                        "basic_connectivity",
                        False,
                        f"Health check failed with status {response.status}"
                    )
                    return False
        except Exception as e:
            self.log_result(
                "basic_connectivity",
                False,
                f"Connection failed: {str(e)}"
            )
            return False
    
    async def validate_database_connectivity(self) -> bool:
        """Validate database connectivity."""
        try:
            postgres_dsn = os.getenv("POSTGRES_DSN", "postgresql://gitte:password@localhost:5432/data_collector")
            
            conn = psycopg2.connect(postgres_dsn)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result and result[0] == 1:
                self.log_result(
                    "database_connectivity",
                    True,
                    "Database connection successful"
                )
                return True
            else:
                self.log_result(
                    "database_connectivity",
                    False,
                    "Database query returned unexpected result"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "database_connectivity",
                False,
                f"Database connection failed: {str(e)}"
            )
            return False
    
    async def validate_redis_connectivity(self) -> bool:
        """Validate Redis connectivity."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            
            # Test basic operations
            test_key = "deployment_validation_test"
            test_value = "test_value"
            
            r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            retrieved_value = r.get(test_key)
            r.delete(test_key)
            
            if retrieved_value and retrieved_value.decode() == test_value:
                self.log_result(
                    "redis_connectivity",
                    True,
                    "Redis connection and operations successful"
                )
                return True
            else:
                self.log_result(
                    "redis_connectivity",
                    False,
                    "Redis operations failed"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "redis_connectivity",
                False,
                f"Redis connection failed: {str(e)}"
            )
            return False
    
    async def validate_ollama_connectivity(self) -> bool:
        """Validate Ollama service connectivity."""
        try:
            ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            
            async with self.session.get(f"{ollama_url}/api/health") as response:
                if response.status == 200:
                    self.log_result(
                        "ollama_connectivity",
                        True,
                        "Ollama service is responding"
                    )
                    return True
                else:
                    self.log_result(
                        "ollama_connectivity",
                        False,
                        f"Ollama health check failed with status {response.status}"
                    )
                    return False
                    
        except Exception as e:
            self.log_result(
                "ollama_connectivity",
                False,
                f"Ollama connection failed: {str(e)}"
            )
            return False
    
    async def validate_ux_features_enabled(self) -> bool:
        """Validate that UX enhancement features are enabled."""
        try:
            # Check environment variables
            ux_enabled = os.getenv("UX_FEATURES_ENABLED", "false").lower() == "true"
            image_correction_enabled = os.getenv("IMAGE_CORRECTION_ENABLED", "false").lower() == "true"
            tooltip_enabled = os.getenv("TOOLTIP_SYSTEM_ENABLED", "false").lower() == "true"
            prerequisite_enabled = os.getenv("PREREQUISITE_VALIDATION_ENABLED", "false").lower() == "true"
            accessibility_enabled = os.getenv("ACCESSIBILITY_FEATURES_ENABLED", "false").lower() == "true"
            
            all_enabled = all([
                ux_enabled,
                image_correction_enabled,
                tooltip_enabled,
                prerequisite_enabled,
                accessibility_enabled
            ])
            
            if all_enabled:
                self.log_result(
                    "ux_features_enabled",
                    True,
                    "All UX enhancement features are enabled",
                    {
                        "ux_features": ux_enabled,
                        "image_correction": image_correction_enabled,
                        "tooltip_system": tooltip_enabled,
                        "prerequisite_validation": prerequisite_enabled,
                        "accessibility": accessibility_enabled
                    }
                )
                return True
            else:
                self.log_result(
                    "ux_features_enabled",
                    False,
                    "Some UX enhancement features are disabled",
                    {
                        "ux_features": ux_enabled,
                        "image_correction": image_correction_enabled,
                        "tooltip_system": tooltip_enabled,
                        "prerequisite_validation": prerequisite_enabled,
                        "accessibility": accessibility_enabled
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                "ux_features_enabled",
                False,
                f"Failed to check UX feature configuration: {str(e)}"
            )
            return False
    
    async def validate_prerequisite_validation_api(self) -> bool:
        """Validate prerequisite validation API endpoints."""
        try:
            # Test prerequisite check endpoint
            async with self.session.get(
                f"{self.ux_base}/prerequisites",
                params={"operation": "system_startup"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Validate response structure
                    required_fields = ["overall_status", "individual_results", "can_proceed"]
                    if all(field in data for field in required_fields):
                        self.log_result(
                            "prerequisite_validation_api",
                            True,
                            "Prerequisite validation API is working",
                            {"response_data": data}
                        )
                        return True
                    else:
                        self.log_result(
                            "prerequisite_validation_api",
                            False,
                            "Prerequisite validation API response missing required fields",
                            {"response_data": data}
                        )
                        return False
                else:
                    self.log_result(
                        "prerequisite_validation_api",
                        False,
                        f"Prerequisite validation API returned status {response.status}"
                    )
                    return False
                    
        except Exception as e:
            self.log_result(
                "prerequisite_validation_api",
                False,
                f"Prerequisite validation API test failed: {str(e)}"
            )
            return False
    
    async def validate_tooltip_system_api(self) -> bool:
        """Validate tooltip system API endpoints."""
        try:
            # Test tooltip retrieval endpoint
            async with self.session.get(
                f"{self.ux_base}/tooltips",
                params={
                    "element_id": "test_element",
                    "context": "test_context",
                    "detail_level": "basic"
                }
            ) as response:
                # Accept both 200 (tooltip found) and 404 (tooltip not found) as valid responses
                # since we're testing with a non-existent element
                if response.status in [200, 404]:
                    self.log_result(
                        "tooltip_system_api",
                        True,
                        "Tooltip system API is responding correctly"
                    )
                    return True
                else:
                    self.log_result(
                        "tooltip_system_api",
                        False,
                        f"Tooltip system API returned unexpected status {response.status}"
                    )
                    return False
                    
        except Exception as e:
            self.log_result(
                "tooltip_system_api",
                False,
                f"Tooltip system API test failed: {str(e)}"
            )
            return False
    
    async def validate_accessibility_features_api(self) -> bool:
        """Validate accessibility features API endpoints."""
        try:
            # Test accessibility features endpoint
            async with self.session.get(f"{self.ux_base}/accessibility") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Validate response structure
                    required_fields = ["features_enabled", "css_overrides"]
                    if all(field in data for field in required_fields):
                        self.log_result(
                            "accessibility_features_api",
                            True,
                            "Accessibility features API is working",
                            {"response_data": data}
                        )
                        return True
                    else:
                        self.log_result(
                            "accessibility_features_api",
                            False,
                            "Accessibility features API response missing required fields",
                            {"response_data": data}
                        )
                        return False
                else:
                    self.log_result(
                        "accessibility_features_api",
                        False,
                        f"Accessibility features API returned status {response.status}"
                    )
                    return False
                    
        except Exception as e:
            self.log_result(
                "accessibility_features_api",
                False,
                f"Accessibility features API test failed: {str(e)}"
            )
            return False
    
    async def validate_performance_metrics_api(self) -> bool:
        """Validate performance metrics API endpoints."""
        try:
            # Test performance metrics endpoint
            async with self.session.get(
                f"{self.ux_base}/performance/metrics",
                params={"time_range": "1h"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Validate response structure
                    expected_metrics = ["tooltip_metrics", "system_metrics"]
                    if any(metric in data for metric in expected_metrics):
                        self.log_result(
                            "performance_metrics_api",
                            True,
                            "Performance metrics API is working",
                            {"response_data": data}
                        )
                        return True
                    else:
                        self.log_result(
                            "performance_metrics_api",
                            False,
                            "Performance metrics API response missing expected metrics",
                            {"response_data": data}
                        )
                        return False
                else:
                    self.log_result(
                        "performance_metrics_api",
                        False,
                        f"Performance metrics API returned status {response.status}"
                    )
                    return False
                    
        except Exception as e:
            self.log_result(
                "performance_metrics_api",
                False,
                f"Performance metrics API test failed: {str(e)}"
            )
            return False
    
    async def validate_image_processing_dependencies(self) -> bool:
        """Validate image processing dependencies are available."""
        try:
            # Test PIL/Pillow
            test_image = Image.new('RGB', (100, 100), color='red')
            
            # Test rembg import (if available)
            try:
                import rembg
                rembg_available = True
            except ImportError:
                rembg_available = False
            
            # Test OpenCV import (if available)
            try:
                import cv2
                opencv_available = True
            except ImportError:
                opencv_available = False
            
            self.log_result(
                "image_processing_dependencies",
                True,
                "Image processing dependencies checked",
                {
                    "pillow": True,
                    "rembg": rembg_available,
                    "opencv": opencv_available
                }
            )
            return True
            
        except Exception as e:
            self.log_result(
                "image_processing_dependencies",
                False,
                f"Image processing dependencies check failed: {str(e)}"
            )
            return False
    
    async def validate_caching_performance(self) -> bool:
        """Validate caching system performance."""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            
            # Test cache performance
            test_data = {"test": "data", "timestamp": time.time()}
            test_key = "performance_test"
            
            # Measure set operation
            start_time = time.time()
            r.set(test_key, json.dumps(test_data), ex=60)
            set_time = time.time() - start_time
            
            # Measure get operation
            start_time = time.time()
            retrieved_data = r.get(test_key)
            get_time = time.time() - start_time
            
            # Cleanup
            r.delete(test_key)
            
            # Validate performance thresholds
            set_threshold = 0.1  # 100ms
            get_threshold = 0.05  # 50ms
            
            if set_time < set_threshold and get_time < get_threshold:
                self.log_result(
                    "caching_performance",
                    True,
                    "Cache performance is within acceptable limits",
                    {
                        "set_time": set_time,
                        "get_time": get_time,
                        "set_threshold": set_threshold,
                        "get_threshold": get_threshold
                    }
                )
                return True
            else:
                self.log_result(
                    "caching_performance",
                    False,
                    "Cache performance exceeds acceptable limits",
                    {
                        "set_time": set_time,
                        "get_time": get_time,
                        "set_threshold": set_threshold,
                        "get_threshold": get_threshold
                    }
                )
                return False
                
        except Exception as e:
            self.log_result(
                "caching_performance",
                False,
                f"Cache performance test failed: {str(e)}"
            )
            return False
    
    async def run_all_validations(self) -> Tuple[bool, Dict]:
        """Run all deployment validations."""
        logger.info("Starting GITTE UX enhancements deployment validation...")
        
        validations = [
            self.validate_basic_connectivity,
            self.validate_database_connectivity,
            self.validate_redis_connectivity,
            self.validate_ollama_connectivity,
            self.validate_ux_features_enabled,
            self.validate_prerequisite_validation_api,
            self.validate_tooltip_system_api,
            self.validate_accessibility_features_api,
            self.validate_performance_metrics_api,
            self.validate_image_processing_dependencies,
            self.validate_caching_performance
        ]
        
        results = []
        for validation in validations:
            try:
                result = await validation()
                results.append(result)
            except Exception as e:
                logger.error(f"Validation {validation.__name__} failed with exception: {str(e)}")
                results.append(False)
        
        # Calculate overall success
        overall_success = all(results)
        passed_count = sum(results)
        total_count = len(results)
        
        summary = {
            "overall_success": overall_success,
            "passed_tests": passed_count,
            "total_tests": total_count,
            "success_rate": passed_count / total_count if total_count > 0 else 0,
            "detailed_results": self.validation_results
        }
        
        logger.info(f"Deployment validation completed: {passed_count}/{total_count} tests passed")
        
        return overall_success, summary


async def main():
    """Main function to run deployment validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GITTE UX Enhancements Deployment Validation")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8501",
        help="Base URL of the GITTE application"
    )
    parser.add_argument(
        "--output",
        help="Output file for validation results (JSON format)"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit on first validation failure"
    )
    
    args = parser.parse_args()
    
    async with DeploymentValidator(args.base_url) as validator:
        success, summary = await validator.run_all_validations()
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Validation results written to {args.output}")
        
        # Print summary
        print("\n" + "="*60)
        print("DEPLOYMENT VALIDATION SUMMARY")
        print("="*60)
        print(f"Overall Success: {'PASS' if success else 'FAIL'}")
        print(f"Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        
        if not success:
            print("\nFailed Tests:")
            for result in summary['detailed_results']:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("="*60)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())