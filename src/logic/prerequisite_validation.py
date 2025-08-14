"""
Prerequisite Validation Logic for GITTE system.
Orchestrates prerequisite checking with parallel execution and timeout handling.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID

from src.services.prerequisite_checker import (
    PrerequisiteValidationService,
    PrerequisiteChecker,
    PrerequisiteCheckSuite,
    PrerequisiteResult,
    PrerequisiteStatus,
    PrerequisiteType,
    create_default_prerequisite_service
)
from src.services.consent_service import ConsentService

logger = logging.getLogger(__name__)


@dataclass
class OperationPrerequisites:
    """Configuration for operation-specific prerequisite requirements."""
    operation_name: str
    required_checkers: Set[str]
    recommended_checkers: Set[str]
    optional_checkers: Set[str]
    timeout_seconds: int = 30
    allow_partial_failure: bool = False


@dataclass
class PrerequisiteRecommendation:
    """Recommendation for resolving prerequisite issues."""
    checker_name: str
    issue_description: str
    priority: str  # "critical", "high", "medium", "low"
    resolution_steps: List[str]
    estimated_time: str
    automation_available: bool = False


class PrerequisiteValidationLogic:
    """Logic layer for prerequisite validation with advanced orchestration."""
    
    def __init__(
        self,
        prerequisite_service: Optional[PrerequisiteValidationService] = None,
        consent_service: Optional[ConsentService] = None
    ):
        """
        Initialize prerequisite validation logic.
        
        Args:
            prerequisite_service: Optional prerequisite service instance
            consent_service: Optional consent service for user-specific checks
        """
        self.prerequisite_service = prerequisite_service
        self.consent_service = consent_service
        self.operation_configs: Dict[str, OperationPrerequisites] = {}
        self._initialize_operation_configs()
    
    def validate_for_operation(
        self,
        operation_name: str,
        user_id: Optional[UUID] = None,
        use_cache: bool = True,
        parallel_execution: bool = True
    ) -> PrerequisiteCheckSuite:
        """
        Validate prerequisites for a specific operation.
        
        Args:
            operation_name: Name of the operation to validate for
            user_id: Optional user ID for user-specific checks
            use_cache: Whether to use cached results
            parallel_execution: Whether to run checks in parallel
            
        Returns:
            PrerequisiteCheckSuite with operation-specific results
        """
        logger.info(f"Validating prerequisites for operation: {operation_name}")
        
        # Get or create prerequisite service
        service = self._get_prerequisite_service(user_id)
        
        # Get operation configuration
        operation_config = self.operation_configs.get(operation_name)
        if not operation_config:
            logger.warning(f"No configuration found for operation: {operation_name}")
            # Fall back to all checks
            return service.run_all_checks(use_cache=use_cache)
        
        # Get required checker names
        required_checkers = list(
            operation_config.required_checkers |
            operation_config.recommended_checkers |
            operation_config.optional_checkers
        )
        
        if parallel_execution:
            return self._run_parallel_checks(
                service,
                required_checkers,
                operation_config.timeout_seconds,
                use_cache
            )
        else:
            return service.run_specific_checks(required_checkers, use_cache=use_cache)
    
    def analyze_prerequisite_failures(
        self,
        check_suite: PrerequisiteCheckSuite
    ) -> List[PrerequisiteRecommendation]:
        """
        Analyze failed prerequisites and generate recommendations.
        
        Args:
            check_suite: Results from prerequisite checks
            
        Returns:
            List of recommendations for resolving issues
        """
        recommendations = []
        
        for result in check_suite.results:
            if result.status in [PrerequisiteStatus.FAILED, PrerequisiteStatus.WARNING]:
                recommendation = self._create_recommendation(result)
                recommendations.append(recommendation)
        
        # Sort by priority (critical first)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.priority, 4))
        
        logger.info(f"Generated {len(recommendations)} recommendations for prerequisite issues")
        
        return recommendations
    
    def check_operation_readiness(
        self,
        operation_name: str,
        user_id: Optional[UUID] = None
    ) -> Dict[str, any]:
        """
        Quick check if operation is ready to proceed.
        
        Args:
            operation_name: Name of the operation
            user_id: Optional user ID
            
        Returns:
            Dict with readiness status and blocking issues
        """
        check_suite = self.validate_for_operation(
            operation_name,
            user_id,
            use_cache=True,
            parallel_execution=True
        )
        
        operation_config = self.operation_configs.get(operation_name)
        
        # Check if required prerequisites are met
        required_failed = []
        recommended_failed = []
        
        for result in check_suite.results:
            if result.status == PrerequisiteStatus.FAILED:
                if operation_config and result.name in operation_config.required_checkers:
                    required_failed.append(result.name)
                elif operation_config and result.name in operation_config.recommended_checkers:
                    recommended_failed.append(result.name)
            elif result.status == PrerequisiteStatus.WARNING:
                if operation_config and result.name in operation_config.recommended_checkers:
                    recommended_failed.append(result.name)
        
        is_ready = len(required_failed) == 0
        can_proceed_with_warnings = len(required_failed) == 0
        
        return {
            "ready": is_ready,
            "can_proceed_with_warnings": can_proceed_with_warnings,
            "required_failures": required_failed,
            "recommended_failures": recommended_failed,
            "total_check_time": check_suite.total_check_time,
            "cached": check_suite.cached
        }
    
    def register_operation_config(self, config: OperationPrerequisites):
        """
        Register prerequisite configuration for an operation.
        
        Args:
            config: Operation prerequisite configuration
        """
        self.operation_configs[config.operation_name] = config
        logger.info(f"Registered prerequisite config for operation: {config.operation_name}")
    
    def get_fallback_behavior(
        self,
        operation_name: str,
        failed_prerequisites: List[str]
    ) -> Dict[str, any]:
        """
        Get fallback behavior configuration for failed prerequisites.
        
        Args:
            operation_name: Name of the operation
            failed_prerequisites: List of failed prerequisite names
            
        Returns:
            Dict with fallback behavior options
        """
        operation_config = self.operation_configs.get(operation_name)
        if not operation_config:
            return {"fallback_available": False}
        
        # Determine what fallbacks are available
        fallback_options = {}
        
        for failed_prereq in failed_prerequisites:
            if failed_prereq == "Ollama LLM Service":
                fallback_options["llm"] = {
                    "available": True,
                    "description": "Use cached responses or simplified interactions",
                    "limitations": ["No real-time AI responses", "Limited personalization"]
                }
            elif failed_prereq == "PostgreSQL Database":
                fallback_options["database"] = {
                    "available": False,
                    "description": "Database is required for core functionality",
                    "limitations": ["Cannot save user data", "No persistent state"]
                }
            elif failed_prereq == "User Consent Status":
                fallback_options["consent"] = {
                    "available": False,
                    "description": "Consent is required for AI features",
                    "limitations": ["Cannot use AI features", "Limited functionality"]
                }
            elif failed_prereq == "System Health":
                fallback_options["system"] = {
                    "available": True,
                    "description": "Continue with performance warnings",
                    "limitations": ["Slower response times", "Potential instability"]
                }
        
        return {
            "fallback_available": len(fallback_options) > 0,
            "allow_partial_failure": operation_config.allow_partial_failure,
            "fallback_options": fallback_options
        }
    
    def _get_prerequisite_service(self, user_id: Optional[UUID]) -> PrerequisiteValidationService:
        """Get or create prerequisite service with appropriate checkers."""
        if self.prerequisite_service:
            return self.prerequisite_service
        
        # Create default service
        return create_default_prerequisite_service(
            user_id=user_id,
            consent_service=self.consent_service
        )
    
    def _run_parallel_checks(
        self,
        service: PrerequisiteValidationService,
        checker_names: List[str],
        timeout_seconds: int,
        use_cache: bool
    ) -> PrerequisiteCheckSuite:
        """
        Run prerequisite checks in parallel with timeout handling.
        
        Args:
            service: Prerequisite validation service
            checker_names: Names of checkers to run
            timeout_seconds: Timeout for parallel execution
            use_cache: Whether to use cached results
            
        Returns:
            PrerequisiteCheckSuite with results
        """
        start_time = datetime.now()
        
        # Filter checkers to run
        checkers_to_run = [
            checker for checker in service.checkers
            if checker.name in checker_names
        ]
        
        results = []
        
        try:
            max_workers = min(len(checkers_to_run), 5)
            if max_workers == 0:
                max_workers = 1  # Ensure at least 1 worker
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all checks
                future_to_checker = {}
                
                for checker in checkers_to_run:
                    if use_cache and service._is_cached_valid(checker.name):
                        # Use cached result immediately
                        results.append(service.cache[checker.name])
                    else:
                        # Submit for parallel execution
                        future = executor.submit(checker.check)
                        future_to_checker[future] = checker
                
                # Collect results with timeout
                for future in future_to_checker:
                    try:
                        result = future.result(timeout=timeout_seconds)
                        checker = future_to_checker[future]
                        
                        # Cache the result
                        service.cache[checker.name] = result
                        service.cache_timestamps[checker.name] = datetime.now()
                        
                        results.append(result)
                        
                    except FutureTimeoutError:
                        checker = future_to_checker[future]
                        logger.warning(f"Prerequisite check timed out: {checker.name}")
                        
                        # Create timeout result
                        timeout_result = PrerequisiteResult(
                            name=checker.name,
                            status=PrerequisiteStatus.FAILED,
                            message=f"Check timed out after {timeout_seconds}s",
                            details="Prerequisite check did not complete within timeout",
                            resolution_steps=[
                                "Check if service is responsive",
                                "Increase timeout configuration",
                                "Contact system administrator"
                            ],
                            check_time=timeout_seconds,
                            prerequisite_type=checker.prerequisite_type
                        )
                        results.append(timeout_result)
                        
                    except Exception as e:
                        checker = future_to_checker[future]
                        logger.error(f"Prerequisite check failed: {checker.name}: {e}")
                        
                        # Create error result
                        error_result = PrerequisiteResult(
                            name=checker.name,
                            status=PrerequisiteStatus.FAILED,
                            message=f"Check failed with error: {str(e)}",
                            details=f"Exception during parallel execution: {type(e).__name__}",
                            check_time=0.0,
                            prerequisite_type=checker.prerequisite_type
                        )
                        results.append(error_result)
        
        except Exception as e:
            logger.error(f"Parallel prerequisite execution failed: {e}")
            # Fall back to sequential execution
            return service.run_specific_checks(checker_names, use_cache=use_cache)
        
        # Analyze overall status
        required_results = [r for r in results if r.prerequisite_type == PrerequisiteType.REQUIRED]
        recommended_results = [r for r in results if r.prerequisite_type == PrerequisiteType.RECOMMENDED]
        
        required_passed = all(r.status == PrerequisiteStatus.PASSED for r in required_results)
        recommended_passed = all(r.status == PrerequisiteStatus.PASSED for r in recommended_results)
        
        if not required_passed:
            overall_status = PrerequisiteStatus.FAILED
        elif not recommended_passed:
            overall_status = PrerequisiteStatus.WARNING
        else:
            overall_status = PrerequisiteStatus.PASSED
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        return PrerequisiteCheckSuite(
            overall_status=overall_status,
            required_passed=required_passed,
            recommended_passed=recommended_passed,
            results=results,
            total_check_time=total_time,
            timestamp=datetime.now().isoformat(),
            cached=any(service._is_cached_valid(r.name) for r in results)
        )
    
    def _create_recommendation(self, result: PrerequisiteResult) -> PrerequisiteRecommendation:
        """Create recommendation for a failed prerequisite."""
        # Determine priority based on prerequisite type and status
        if result.prerequisite_type == PrerequisiteType.REQUIRED:
            priority = "critical" if result.status == PrerequisiteStatus.FAILED else "high"
        elif result.prerequisite_type == PrerequisiteType.RECOMMENDED:
            priority = "medium"
        else:
            priority = "low"
        
        # Estimate resolution time based on checker type
        time_estimates = {
            "Ollama LLM Service": "5-10 minutes",
            "PostgreSQL Database": "2-5 minutes",
            "User Consent Status": "1-2 minutes",
            "System Health": "Variable (depends on issue)"
        }
        
        estimated_time = time_estimates.get(result.name, "Unknown")
        
        # Check if automation is available
        automation_available = result.name in [
            "User Consent Status"  # Can redirect to consent page
        ]
        
        return PrerequisiteRecommendation(
            checker_name=result.name,
            issue_description=result.message,
            priority=priority,
            resolution_steps=result.resolution_steps or [],
            estimated_time=estimated_time,
            automation_available=automation_available
        )
    
    def _initialize_operation_configs(self):
        """Initialize default operation prerequisite configurations."""
        # Registration operation
        self.operation_configs["registration"] = OperationPrerequisites(
            operation_name="registration",
            required_checkers={"PostgreSQL Database"},
            recommended_checkers={"System Health"},
            optional_checkers=set(),
            timeout_seconds=15,
            allow_partial_failure=True
        )
        
        # Chat operation
        self.operation_configs["chat"] = OperationPrerequisites(
            operation_name="chat",
            required_checkers={"Ollama LLM Service", "PostgreSQL Database", "User Consent Status"},
            recommended_checkers={"System Health"},
            optional_checkers=set(),
            timeout_seconds=30,
            allow_partial_failure=False
        )
        
        # Image generation operation
        self.operation_configs["image_generation"] = OperationPrerequisites(
            operation_name="image_generation",
            required_checkers={"PostgreSQL Database", "User Consent Status"},
            recommended_checkers={"System Health"},
            optional_checkers=set(),
            timeout_seconds=25,
            allow_partial_failure=False
        )
        
        # System startup
        self.operation_configs["system_startup"] = OperationPrerequisites(
            operation_name="system_startup",
            required_checkers={"PostgreSQL Database"},
            recommended_checkers={"Ollama LLM Service", "System Health"},
            optional_checkers=set(),
            timeout_seconds=45,
            allow_partial_failure=True
        )
        
        logger.info(f"Initialized {len(self.operation_configs)} operation configurations")


def create_prerequisite_validation_logic(
    user_id: Optional[UUID] = None,
    consent_service: Optional[ConsentService] = None
) -> PrerequisiteValidationLogic:
    """
    Create prerequisite validation logic with default configuration.
    
    Args:
        user_id: Optional user ID for user-specific checks
        consent_service: Optional consent service instance
        
    Returns:
        PrerequisiteValidationLogic instance
    """
    prerequisite_service = create_default_prerequisite_service(
        user_id=user_id,
        consent_service=consent_service
    )
    
    return PrerequisiteValidationLogic(
        prerequisite_service=prerequisite_service,
        consent_service=consent_service
    )