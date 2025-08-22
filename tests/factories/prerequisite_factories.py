"""
Test factories for prerequisite validation testing.
"""

from datetime import datetime

from src.services.prerequisite_checker import (
    PrerequisiteCheckSuite,
    PrerequisiteResult,
    PrerequisiteStatus,
    PrerequisiteType,
)


def create_prerequisite_result(
    name: str = "Test Checker",
    status: PrerequisiteStatus = PrerequisiteStatus.PASSED,
    message: str = "Test message",
    prerequisite_type: PrerequisiteType = PrerequisiteType.REQUIRED,
    resolution_steps: list[str] | None = None,
    details: str | None = None,
    check_time: float = 1.0
) -> PrerequisiteResult:
    """Create a test prerequisite result."""
    return PrerequisiteResult(
        name=name,
        status=status,
        message=message,
        prerequisite_type=prerequisite_type,
        resolution_steps=resolution_steps or [],
        details=details,
        check_time=check_time
    )


def create_prerequisite_check_suite(
    overall_status: PrerequisiteStatus = PrerequisiteStatus.PASSED,
    required_passed: bool = True,
    recommended_passed: bool = True,
    results: list[PrerequisiteResult] | None = None,
    total_check_time: float = 1.0,
    cached: bool = False
) -> PrerequisiteCheckSuite:
    """Create a test prerequisite check suite."""
    if results is None:
        results = [create_prerequisite_result()]
    
    return PrerequisiteCheckSuite(
        overall_status=overall_status,
        required_passed=required_passed,
        recommended_passed=recommended_passed,
        results=results,
        total_check_time=total_check_time,
        timestamp=datetime.now().isoformat(),
        cached=cached
    )


def create_failed_prerequisite_result(
    name: str = "Failed Checker",
    message: str = "Check failed",
    prerequisite_type: PrerequisiteType = PrerequisiteType.REQUIRED,
    resolution_steps: list[str] | None = None
) -> PrerequisiteResult:
    """Create a failed prerequisite result for testing."""
    return create_prerequisite_result(
        name=name,
        status=PrerequisiteStatus.FAILED,
        message=message,
        prerequisite_type=prerequisite_type,
        resolution_steps=resolution_steps or ["Fix the issue"]
    )


def create_warning_prerequisite_result(
    name: str = "Warning Checker",
    message: str = "Check has warnings",
    prerequisite_type: PrerequisiteType = PrerequisiteType.RECOMMENDED
) -> PrerequisiteResult:
    """Create a warning prerequisite result for testing."""
    return create_prerequisite_result(
        name=name,
        status=PrerequisiteStatus.WARNING,
        message=message,
        prerequisite_type=prerequisite_type
    )


class FakePrerequisiteChecker:
    """Fake prerequisite checker for testing."""
    
    def __init__(self, name: str, prerequisite_type: PrerequisiteType = PrerequisiteType.REQUIRED):
        self.name = name
        self.prerequisite_type = prerequisite_type
        self._check_result = None
    
    def set_check_result(self, result: PrerequisiteResult):
        """Set the result this checker should return."""
        self._check_result = result
    
    def check(self) -> PrerequisiteResult:
        """Fake check implementation."""
        if self._check_result:
            return self._check_result
        return create_prerequisite_result(
            name=self.name,
            prerequisite_type=self.prerequisite_type
        )


class FakePrerequisiteValidationService:
    """Fake prerequisite validation service for testing."""
    
    def __init__(self):
        self.checkers = []
        self.cache = {}
        self.cache_timestamps = {}
        self._run_all_checks_result = None
        self._run_specific_checks_result = None
        self._parallel_execution_result = None
    
    def set_run_all_checks_result(self, result: PrerequisiteCheckSuite):
        """Set the result that run_all_checks should return."""
        self._run_all_checks_result = result
    
    def set_run_specific_checks_result(self, result: PrerequisiteCheckSuite):
        """Set the result that run_specific_checks should return."""
        self._run_specific_checks_result = result
        # Also set for parallel execution since that's what the logic uses
        self._parallel_execution_result = result
    
    def run_all_checks(self, use_cache: bool = True) -> PrerequisiteCheckSuite:
        """Fake implementation of run_all_checks."""
        if self._run_all_checks_result:
            return self._run_all_checks_result
        return create_prerequisite_check_suite()
    
    def run_specific_checks(
        self, checker_names: list[str], use_cache: bool = True
    ) -> PrerequisiteCheckSuite:
        """Fake implementation of run_specific_checks."""
        if self._run_specific_checks_result:
            return self._run_specific_checks_result
        return create_prerequisite_check_suite()
    
    def _is_cached_valid(self, checker_name: str) -> bool:
        """Fake implementation of cache validation."""
        return checker_name in self.cache


class FakeConsentService:
    """Fake consent service for testing."""
    
    def __init__(self):
        self.user_consents = {}
    
    def set_user_consent(self, user_id: str, has_consent: bool):
        """Set consent status for a user."""
        self.user_consents[user_id] = has_consent
    
    def has_consent(self, user_id: str) -> bool:
        """Check if user has consent."""
        return self.user_consents.get(user_id, False)