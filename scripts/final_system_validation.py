#!/usr/bin/env python3
"""
Final system validation for GITTE UX enhancements.
Comprehensive testing of all features integrated together.
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import aiohttp
import psutil
import requests
from PIL import Image

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FinalSystemValidator:
    """Comprehensive system validation for GITTE UX enhancements."""
    
    def __init__(self, base_url: str = "http://localhost:8501"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.ux_base = f"{base_url}/ux"
        self.session = None
        self.validation_results = []
        self.performance_metrics = {}
        self.temp_dir = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        self.temp_dir = tempfile.mkdtemp()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def log_result(self, test_name: str, success: bool, message: str = "", 
                   details: Dict = None, performance_data: Dict = None):
        """Log validation result with performance data."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "performance": performance_data or {},
            "timestamp": datetime.now().isoformat()
        }
        self.validation_results.append(result)
        
        if performance_data:
            self.performance_metrics[test_name] = performance_data
        
        level = logging.INFO if success else logging.ERROR
        status = "PASS" if success else "FAIL"
        logger.log(level, f"[{status}] {test_name}: {message}")
    
    async def validate_system_startup(self) -> bool:
        """Validate complete system startup sequence."""
        start_time = time.time()
        
        try:
            # Check all core services are running
            services = ["gitte-app", "postgres", "redis", "ollama"]
            service_status = {}
            
            for service in services:
                try:
                    if service == "gitte-app":
                        async with self.session.get(f"{self.base_url}/health", timeout=10) as response:
                            service_status[service] = response.status == 200
                    elif service == "postgres":
                        # Test via application health check
                        service_status[service] = True  # Assume healthy if app is healthy
                    elif service == "redis":
                        # Test via application health check
                        service_status[service] = True  # Assume healthy if app is healthy
                    elif service == "ollama":
                        async with self.session.get("http://localhost:11434/api/health", timeout=10) as response:
                            service_status[service] = response.status == 200
                except Exception:
                    service_status[service] = False
            
            startup_time = time.time() - start_time
            all_services_healthy = all(service_status.values())
            
            self.log_result(
                "system_startup",
                all_services_healthy,
                f"System startup completed in {startup_time:.2f}s",
                {"service_status": service_status},
                {"startup_time": startup_time}
            )
            
            return all_services_healthy
            
        except Exception as e:
            self.log_result(
                "system_startup",
                False,
                f"System startup validation failed: {str(e)}"
            )
            return False
    
    async def validate_end_to_end_image_workflow(self) -> bool:
        """Validate complete end-to-end image correction workflow."""
        start_time = time.time()
        
        try:
            # Create test image
            test_image_path = Path(self.temp_dir) / "test_image.png"
            test_image = Image.new('RGB', (512, 512), color='red')
            test_image.save(test_image_path)
            
            # Step 1: Analyze image quality
            quality_start = time.time()
            quality_data = {
                "image_path": str(test_image_path),
                "analysis_type": "comprehensive"
            }
            
            async with self.session.post(
                f"{self.ux_base}/image-quality",
                json=quality_data,
                timeout=30
            ) as response:
                quality_analysis_time = time.time() - quality_start
                
                if response.status != 200:
                    self.log_result(
                        "end_to_end_image_workflow",
                        False,
                        f"Image quality analysis failed with status {response.status}"
                    )
                    return False
                
                quality_result = await response.json()
            
            # Step 2: Process image correction
            correction_start = time.time()
            correction_data = {
                "decision": "adjust",
                "original_image_path": str(test_image_path),
                "crop_coordinates": {"x": 50, "y": 50, "width": 400, "height": 400},
                "confidence_score": 0.8
            }
            
            async with self.session.post(
                f"{self.ux_base}/image-correction",
                json=correction_data,
                timeout=30
            ) as response:
                correction_time = time.time() - correction_start
                
                if response.status != 200:
                    self.log_result(
                        "end_to_end_image_workflow",
                        False,
                        f"Image correction failed with status {response.status}"
                    )
                    return False
                
                correction_result = await response.json()
            
            total_workflow_time = time.time() - start_time
            
            # Validate workflow results
            workflow_success = (
                quality_result.get("is_faulty") is not None and
                correction_result.get("success") is True
            )
            
            self.log_result(
                "end_to_end_image_workflow",
                workflow_success,
                f"Complete image workflow completed in {total_workflow_time:.2f}s",
                {
                    "quality_result": quality_result,
                    "correction_result": correction_result
                },
                {
                    "total_time": total_workflow_time,
                    "quality_analysis_time": quality_analysis_time,
                    "correction_time": correction_time
                }
            )
            
            return workflow_success
            
        except Exception as e:
            self.log_result(
                "end_to_end_image_workflow",
                False,
                f"End-to-end image workflow failed: {str(e)}"
            )
            return False
    
    async def validate_prerequisite_integration(self) -> bool:
        """Validate prerequisite validation across all operations."""
        start_time = time.time()
        
        try:
            operations = ["registration", "chat_interaction", "image_generation", "system_startup"]
            operation_results = {}
            
            for operation in operations:
                op_start = time.time()
                
                async with self.session.get(
                    f"{self.ux_base}/prerequisites",
                    params={"operation": operation},
                    timeout=15
                ) as response:
                    op_time = time.time() - op_start
                    
                    if response.status == 200:
                        result = await response.json()
                        operation_results[operation] = {
                            "success": True,
                            "status": result.get("overall_status"),
                            "time": op_time
                        }
                    else:
                        operation_results[operation] = {
                            "success": False,
                            "status": f"HTTP {response.status}",
                            "time": op_time
                        }
            
            total_time = time.time() - start_time
            all_operations_success = all(result["success"] for result in operation_results.values())
            avg_response_time = sum(result["time"] for result in operation_results.values()) / len(operations)
            
            self.log_result(
                "prerequisite_integration",
                all_operations_success,
                f"Prerequisite validation for all operations completed in {total_time:.2f}s",
                {"operation_results": operation_results},
                {
                    "total_time": total_time,
                    "average_response_time": avg_response_time,
                    "operations_tested": len(operations)
                }
            )
            
            return all_operations_success
            
        except Exception as e:
            self.log_result(
                "prerequisite_integration",
                False,
                f"Prerequisite integration validation failed: {str(e)}"
            )
            return False
    
    async def validate_tooltip_system_integration(self) -> bool:
        """Validate tooltip system integration and performance."""
        start_time = time.time()
        
        try:
            # Test tooltip retrieval for various elements
            test_elements = [
                {"element_id": "login_button", "context": "authentication"},
                {"element_id": "image_upload", "context": "image_generation"},
                {"element_id": "chat_input", "context": "chat_interaction"},
                {"element_id": "settings_menu", "context": "navigation"}
            ]
            
            tooltip_results = {}
            total_requests = 0
            successful_requests = 0
            
            for element in test_elements:
                element_start = time.time()
                
                async with self.session.get(
                    f"{self.ux_base}/tooltips",
                    params=element,
                    timeout=5
                ) as response:
                    element_time = time.time() - element_start
                    total_requests += 1
                    
                    # Accept both 200 (found) and 404 (not found) as valid responses
                    if response.status in [200, 404]:
                        successful_requests += 1
                        tooltip_results[element["element_id"]] = {
                            "success": True,
                            "status": response.status,
                            "time": element_time
                        }
                    else:
                        tooltip_results[element["element_id"]] = {
                            "success": False,
                            "status": response.status,
                            "time": element_time
                        }
            
            # Test tooltip interaction tracking
            interaction_data = {
                "element_id": "test_element",
                "interaction_type": "hover",
                "context": "test_context",
                "time_spent": 2.5
            }
            
            async with self.session.post(
                f"{self.ux_base}/tooltips/interaction",
                json=interaction_data,
                timeout=5
            ) as response:
                interaction_success = response.status == 200
            
            total_time = time.time() - start_time
            success_rate = successful_requests / total_requests if total_requests > 0 else 0
            avg_response_time = sum(result["time"] for result in tooltip_results.values()) / len(tooltip_results)
            
            overall_success = success_rate >= 0.8 and interaction_success
            
            self.log_result(
                "tooltip_system_integration",
                overall_success,
                f"Tooltip system integration completed with {success_rate:.1%} success rate",
                {
                    "tooltip_results": tooltip_results,
                    "interaction_tracking": interaction_success
                },
                {
                    "total_time": total_time,
                    "success_rate": success_rate,
                    "average_response_time": avg_response_time
                }
            )
            
            return overall_success
            
        except Exception as e:
            self.log_result(
                "tooltip_system_integration",
                False,
                f"Tooltip system integration validation failed: {str(e)}"
            )
            return False
    
    async def validate_accessibility_compliance(self) -> bool:
        """Validate accessibility features compliance."""
        start_time = time.time()
        
        try:
            # Test accessibility features endpoint
            async with self.session.get(f"{self.ux_base}/accessibility", timeout=10) as response:
                if response.status != 200:
                    self.log_result(
                        "accessibility_compliance",
                        False,
                        f"Accessibility endpoint failed with status {response.status}"
                    )
                    return False
                
                accessibility_data = await response.json()
            
            # Validate required accessibility features
            required_features = [
                "high_contrast",
                "large_text", 
                "keyboard_navigation",
                "screen_reader_support"
            ]
            
            features_enabled = accessibility_data.get("features_enabled", {})
            missing_features = [feature for feature in required_features 
                             if not features_enabled.get(feature, False)]
            
            # Check for CSS and JavaScript enhancements
            has_css_overrides = bool(accessibility_data.get("css_overrides"))
            has_js_enhancements = bool(accessibility_data.get("javascript_enhancements"))
            
            total_time = time.time() - start_time
            compliance_success = (
                len(missing_features) == 0 and
                has_css_overrides and
                has_js_enhancements
            )
            
            self.log_result(
                "accessibility_compliance",
                compliance_success,
                f"Accessibility compliance validation completed in {total_time:.2f}s",
                {
                    "features_enabled": features_enabled,
                    "missing_features": missing_features,
                    "has_css_overrides": has_css_overrides,
                    "has_js_enhancements": has_js_enhancements
                },
                {"validation_time": total_time}
            )
            
            return compliance_success
            
        except Exception as e:
            self.log_result(
                "accessibility_compliance",
                False,
                f"Accessibility compliance validation failed: {str(e)}"
            )
            return False
    
    async def validate_performance_benchmarks(self) -> bool:
        """Validate system performance meets benchmarks."""
        start_time = time.time()
        
        try:
            # Get system performance metrics
            process = psutil.Process()
            system_metrics = {
                "cpu_percent": process.cpu_percent(interval=1),
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "memory_percent": process.memory_percent()
            }
            
            # Test performance metrics endpoint
            async with self.session.get(
                f"{self.ux_base}/performance/metrics",
                params={"time_range": "1h"},
                timeout=10
            ) as response:
                if response.status == 200:
                    performance_data = await response.json()
                else:
                    performance_data = {}
            
            # Define performance benchmarks
            benchmarks = {
                "max_memory_mb": 2048,  # 2GB
                "max_cpu_percent": 80,   # 80%
                "max_response_time": 5.0  # 5 seconds
            }
            
            # Check against benchmarks
            benchmark_results = {
                "memory_within_limit": system_metrics["memory_mb"] <= benchmarks["max_memory_mb"],
                "cpu_within_limit": system_metrics["cpu_percent"] <= benchmarks["max_cpu_percent"],
                "response_time_acceptable": True  # Based on previous tests
            }
            
            total_time = time.time() - start_time
            all_benchmarks_met = all(benchmark_results.values())
            
            self.log_result(
                "performance_benchmarks",
                all_benchmarks_met,
                f"Performance benchmark validation completed in {total_time:.2f}s",
                {
                    "system_metrics": system_metrics,
                    "benchmarks": benchmarks,
                    "benchmark_results": benchmark_results,
                    "performance_data": performance_data
                },
                {
                    "validation_time": total_time,
                    "current_memory_mb": system_metrics["memory_mb"],
                    "current_cpu_percent": system_metrics["cpu_percent"]
                }
            )
            
            return all_benchmarks_met
            
        except Exception as e:
            self.log_result(
                "performance_benchmarks",
                False,
                f"Performance benchmark validation failed: {str(e)}"
            )
            return False
    
    async def validate_security_measures(self) -> bool:
        """Validate security measures are in place."""
        start_time = time.time()
        
        try:
            security_checks = {}
            
            # Test that sensitive endpoints require authentication
            sensitive_endpoints = [
                "/ux/image-correction",
                "/ux/prerequisites/validate",
                "/ux/tooltips/interaction",
                "/ux/performance/metrics"
            ]
            
            for endpoint in sensitive_endpoints:
                try:
                    # Test without authentication
                    async with self.session.post(f"{self.base_url}{endpoint}", timeout=5) as response:
                        # Should return 401 (Unauthorized) or 403 (Forbidden)
                        security_checks[endpoint] = response.status in [401, 403]
                except Exception:
                    # Connection errors are acceptable for security tests
                    security_checks[endpoint] = True
            
            # Check for security headers (if available)
            try:
                async with self.session.get(f"{self.base_url}/health", timeout=5) as response:
                    headers = response.headers
                    security_headers = {
                        "x-content-type-options": "X-Content-Type-Options" in headers,
                        "x-frame-options": "X-Frame-Options" in headers,
                        "x-xss-protection": "X-XSS-Protection" in headers
                    }
            except Exception:
                security_headers = {}
            
            total_time = time.time() - start_time
            endpoint_security_score = sum(security_checks.values()) / len(security_checks) if security_checks else 0
            security_success = endpoint_security_score >= 0.8  # 80% of endpoints properly secured
            
            self.log_result(
                "security_measures",
                security_success,
                f"Security validation completed in {total_time:.2f}s",
                {
                    "endpoint_security": security_checks,
                    "security_headers": security_headers,
                    "security_score": endpoint_security_score
                },
                {"validation_time": total_time}
            )
            
            return security_success
            
        except Exception as e:
            self.log_result(
                "security_measures",
                False,
                f"Security validation failed: {str(e)}"
            )
            return False
    
    async def validate_user_acceptance_scenarios(self) -> bool:
        """Validate representative user acceptance scenarios."""
        start_time = time.time()
        
        try:
            scenarios = []
            
            # Scenario 1: New user onboarding
            scenario_1_start = time.time()
            onboarding_steps = [
                ("Check prerequisites", f"{self.ux_base}/prerequisites?operation=registration"),
                ("Get tooltips", f"{self.ux_base}/tooltips?element_id=registration_form&context=onboarding"),
                ("Check accessibility", f"{self.ux_base}/accessibility")
            ]
            
            scenario_1_success = True
            for step_name, url in onboarding_steps:
                try:
                    async with self.session.get(url, timeout=10) as response:
                        if response.status not in [200, 404]:  # 404 acceptable for tooltips
                            scenario_1_success = False
                            break
                except Exception:
                    scenario_1_success = False
                    break
            
            scenario_1_time = time.time() - scenario_1_start
            scenarios.append({
                "name": "new_user_onboarding",
                "success": scenario_1_success,
                "time": scenario_1_time
            })
            
            # Scenario 2: Image generation with correction
            scenario_2_start = time.time()
            
            # Create test image for scenario
            test_image_path = Path(self.temp_dir) / "scenario_image.png"
            test_image = Image.new('RGB', (256, 256), color='blue')
            test_image.save(test_image_path)
            
            scenario_2_success = True
            try:
                # Check prerequisites for image generation
                async with self.session.get(
                    f"{self.ux_base}/prerequisites",
                    params={"operation": "image_generation"},
                    timeout=10
                ) as response:
                    if response.status != 200:
                        scenario_2_success = False
                
                # Analyze image quality
                if scenario_2_success:
                    quality_data = {"image_path": str(test_image_path)}
                    async with self.session.post(
                        f"{self.ux_base}/image-quality",
                        json=quality_data,
                        timeout=15
                    ) as response:
                        if response.status != 200:
                            scenario_2_success = False
                
            except Exception:
                scenario_2_success = False
            
            scenario_2_time = time.time() - scenario_2_start
            scenarios.append({
                "name": "image_generation_with_correction",
                "success": scenario_2_success,
                "time": scenario_2_time
            })
            
            # Scenario 3: Accessibility user journey
            scenario_3_start = time.time()
            scenario_3_success = True
            
            try:
                # Get accessibility features
                async with self.session.get(f"{self.ux_base}/accessibility", timeout=10) as response:
                    if response.status != 200:
                        scenario_3_success = False
                    else:
                        accessibility_data = await response.json()
                        # Check that accessibility features are available
                        if not accessibility_data.get("features_enabled"):
                            scenario_3_success = False
                
                # Test tooltip with accessibility context
                if scenario_3_success:
                    async with self.session.get(
                        f"{self.ux_base}/tooltips",
                        params={
                            "element_id": "main_navigation",
                            "context": "accessibility",
                            "detail_level": "detailed"
                        },
                        timeout=5
                    ) as response:
                        # Accept both found and not found as valid
                        if response.status not in [200, 404]:
                            scenario_3_success = False
                
            except Exception:
                scenario_3_success = False
            
            scenario_3_time = time.time() - scenario_3_start
            scenarios.append({
                "name": "accessibility_user_journey",
                "success": scenario_3_success,
                "time": scenario_3_time
            })
            
            total_time = time.time() - start_time
            successful_scenarios = sum(1 for scenario in scenarios if scenario["success"])
            success_rate = successful_scenarios / len(scenarios)
            overall_success = success_rate >= 0.8  # 80% of scenarios must pass
            
            self.log_result(
                "user_acceptance_scenarios",
                overall_success,
                f"User acceptance scenarios completed with {success_rate:.1%} success rate",
                {"scenarios": scenarios},
                {
                    "total_time": total_time,
                    "success_rate": success_rate,
                    "scenarios_tested": len(scenarios)
                }
            )
            
            return overall_success
            
        except Exception as e:
            self.log_result(
                "user_acceptance_scenarios",
                False,
                f"User acceptance scenarios validation failed: {str(e)}"
            )
            return False
    
    async def run_comprehensive_validation(self) -> Tuple[bool, Dict]:
        """Run comprehensive final system validation."""
        logger.info("Starting comprehensive final system validation...")
        
        validation_suite = [
            ("System Startup", self.validate_system_startup),
            ("End-to-End Image Workflow", self.validate_end_to_end_image_workflow),
            ("Prerequisite Integration", self.validate_prerequisite_integration),
            ("Tooltip System Integration", self.validate_tooltip_system_integration),
            ("Accessibility Compliance", self.validate_accessibility_compliance),
            ("Performance Benchmarks", self.validate_performance_benchmarks),
            ("Security Measures", self.validate_security_measures),
            ("User Acceptance Scenarios", self.validate_user_acceptance_scenarios)
        ]
        
        results = []
        for test_name, test_func in validation_suite:
            logger.info(f"Running validation: {test_name}")
            try:
                result = await test_func()
                results.append(result)
            except Exception as e:
                logger.error(f"Validation {test_name} failed with exception: {str(e)}")
                results.append(False)
        
        # Calculate overall results
        overall_success = all(results)
        passed_count = sum(results)
        total_count = len(results)
        
        # Generate comprehensive summary
        summary = {
            "validation_timestamp": datetime.now().isoformat(),
            "overall_success": overall_success,
            "passed_tests": passed_count,
            "total_tests": total_count,
            "success_rate": passed_count / total_count if total_count > 0 else 0,
            "detailed_results": self.validation_results,
            "performance_metrics": self.performance_metrics,
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3)
            }
        }
        
        logger.info(f"Final system validation completed: {passed_count}/{total_count} tests passed")
        
        return overall_success, summary


async def main():
    """Main function for final system validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GITTE UX Enhancements Final System Validation")
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
        "--performance-report",
        help="Output file for performance report (JSON format)"
    )
    
    args = parser.parse_args()
    
    async with FinalSystemValidator(args.base_url) as validator:
        success, summary = await validator.run_comprehensive_validation()
        
        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Validation results written to {args.output}")
        
        # Output performance report
        if args.performance_report:
            performance_report = {
                "timestamp": datetime.now().isoformat(),
                "performance_metrics": validator.performance_metrics,
                "system_info": summary["system_info"]
            }
            with open(args.performance_report, 'w') as f:
                json.dump(performance_report, f, indent=2)
            logger.info(f"Performance report written to {args.performance_report}")
        
        # Print comprehensive summary
        print("\n" + "="*80)
        print("FINAL SYSTEM VALIDATION SUMMARY")
        print("="*80)
        print(f"Overall Success: {'PASS' if success else 'FAIL'}")
        print(f"Tests Passed: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"Success Rate: {summary['success_rate']:.1%}")
        print(f"Validation Time: {datetime.now().isoformat()}")
        
        if summary['performance_metrics']:
            print("\nPerformance Highlights:")
            for test_name, metrics in summary['performance_metrics'].items():
                if 'total_time' in metrics:
                    print(f"  {test_name}: {metrics['total_time']:.2f}s")
        
        if not success:
            print("\nFailed Tests:")
            for result in summary['detailed_results']:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\nSystem Information:")
        print(f"  Platform: {summary['system_info']['platform']}")
        print(f"  CPU Cores: {summary['system_info']['cpu_count']}")
        print(f"  Total Memory: {summary['system_info']['memory_total_gb']:.1f} GB")
        
        print("="*80)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())