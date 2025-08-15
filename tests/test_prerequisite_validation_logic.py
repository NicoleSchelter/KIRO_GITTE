"""
Unit tests for prerequisite validation logic.
"""

from uuid import uuid4

import pytest

from src.logic.prerequisite_validation import (
    OperationPrerequisites,
    PrerequisiteRecommendation,
    PrerequisiteValidationLogic,
    create_prerequisite_validation_logic,
)
from src.services.prerequisite_checker import (
    PrerequisiteCheckSuite,
    PrerequisiteStatus,
    PrerequisiteType,
)
from tests.factories.prerequisite_factories import (
    FakeConsentService,
    FakePrerequisiteValidationService,
    create_failed_prerequisite_result,
    create_prerequisite_check_suite,
    create_prerequisite_result,
    create_warning_prerequisite_result,
)


class ControllablePrerequisiteValidationLogic(PrerequisiteValidationLogic):
    """
    Testable version of PrerequisiteValidationLogic that allows controlling parallel execution.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parallel_execution_result = None
    
    def set_parallel_execution_result(self, result: PrerequisiteCheckSuite):
        """Set the result that parallel execution should return."""
        self._parallel_execution_result = result
    
    def _run_parallel_checks(self, service, checker_names, timeout_seconds, use_cache):
        """Override parallel execution for testing."""
        if self._parallel_execution_result:
            return self._parallel_execution_result
        # Fall back to sequential execution for testing
        return service.run_specific_checks(checker_names, use_cache=use_cache)


class TestPrerequisiteValidationLogic:
    """Test cases for PrerequisiteValidationLogic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.fake_service = FakePrerequisiteValidationService()
        self.fake_consent_service = FakeConsentService()
        self.user_id = uuid4()
        
        self.logic = ControllablePrerequisiteValidationLogic(
            prerequisite_service=self.fake_service,
            consent_service=self.fake_consent_service
        )
    
    def test_initialization(self):
        """Test logic initialization."""
        assert self.logic.prerequisite_service == self.fake_service
        assert self.logic.consent_service == self.fake_consent_service
        assert len(self.logic.operation_configs) > 0
        
        # Check default operation configs are loaded
        assert "registration" in self.logic.operation_configs
        assert "chat" in self.logic.operation_configs
        assert "image_generation" in self.logic.operation_configs
        assert "system_startup" in self.logic.operation_configs
    
    def test_validate_for_operation_with_config(self):
        """Test validation for operation with specific configuration."""
        # Create test result
        test_result = create_prerequisite_result(
            name="PostgreSQL Database",
            status=PrerequisiteStatus.PASSED,
            message="Database connected",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        test_suite = create_prerequisite_check_suite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[test_result],
            total_check_time=1.5
        )
        
        self.fake_service.set_run_specific_checks_result(test_suite)
        
        # Test registration operation
        result = self.logic.validate_for_operation(
            "registration",
            user_id=self.user_id,
            parallel_execution=False
        )
        
        assert result == test_suite
    
    def test_validate_for_operation_unknown_operation(self):
        """Test validation for unknown operation falls back to all checks."""
        test_suite = create_prerequisite_check_suite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[],
            total_check_time=1.0
        )
        
        self.fake_service.set_run_all_checks_result(test_suite)
        
        result = self.logic.validate_for_operation("unknown_operation")
        
        assert result == test_suite
    
    def test_analyze_prerequisite_failures(self):
        """Test analysis of prerequisite failures."""
        failed_result = create_failed_prerequisite_result(
            name="Ollama LLM Service",
            message="Cannot connect to Ollama",
            prerequisite_type=PrerequisiteType.REQUIRED,
            resolution_steps=["Start Ollama service", "Check configuration"]
        )
        
        warning_result = create_warning_prerequisite_result(
            name="System Health",
            message="High memory usage",
            prerequisite_type=PrerequisiteType.RECOMMENDED
        )
        
        passed_result = create_prerequisite_result(
            name="PostgreSQL Database",
            status=PrerequisiteStatus.PASSED,
            message="Database connected",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = create_prerequisite_check_suite(
            overall_status=PrerequisiteStatus.FAILED,
            required_passed=False,
            recommended_passed=False,
            results=[failed_result, warning_result, passed_result],
            total_check_time=2.0
        )
        
        recommendations = self.logic.analyze_prerequisite_failures(check_suite)
        
        assert len(recommendations) == 2  # Only failed and warning results
        
        # Check critical recommendation (required failure)
        critical_rec = next(r for r in recommendations if r.priority == "critical")
        assert critical_rec.checker_name == "Ollama LLM Service"
        assert critical_rec.issue_description == "Cannot connect to Ollama"
        assert len(critical_rec.resolution_steps) == 2
        
        # Check medium recommendation (recommended warning)
        medium_rec = next(r for r in recommendations if r.priority == "medium")
        assert medium_rec.checker_name == "System Health"
        assert medium_rec.issue_description == "High memory usage"
    
    def test_check_operation_readiness_ready(self):
        """Test operation readiness check when ready."""
        passed_result = create_prerequisite_result(
            name="PostgreSQL Database",
            status=PrerequisiteStatus.PASSED,
            message="Database connected",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = create_prerequisite_check_suite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[passed_result],
            total_check_time=1.0,
            cached=True
        )
        
        # Set up the fake service to return our test suite
        self.fake_service.set_run_specific_checks_result(check_suite)
        self.logic.set_parallel_execution_result(check_suite)
        
        readiness = self.logic.check_operation_readiness("registration")
        
        assert readiness["ready"] is True
        assert readiness["can_proceed_with_warnings"] is True
        assert len(readiness["required_failures"]) == 0
        assert len(readiness["recommended_failures"]) == 0
        assert readiness["cached"] is True
    
    def test_check_operation_readiness_not_ready(self):
        """Test operation readiness check when not ready."""
        failed_result = create_failed_prerequisite_result(
            name="PostgreSQL Database",
            message="Cannot connect",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = create_prerequisite_check_suite(
            overall_status=PrerequisiteStatus.FAILED,
            required_passed=False,
            recommended_passed=True,
            results=[failed_result],
            total_check_time=2.0
        )
        
        # Set up the fake service to return our test suite
        self.fake_service.set_run_specific_checks_result(check_suite)
        self.logic.set_parallel_execution_result(check_suite)
        
        readiness = self.logic.check_operation_readiness("registration")
        
        assert readiness["ready"] is False
        assert readiness["can_proceed_with_warnings"] is False
        assert "PostgreSQL Database" in readiness["required_failures"]
        assert len(readiness["recommended_failures"]) == 0
    
    def test_register_operation_config(self):
        """Test registering custom operation configuration."""
        custom_config = OperationPrerequisites(
            operation_name="custom_operation",
            required_checkers={"Custom Checker"},
            recommended_checkers=set(),
            optional_checkers=set(),
            timeout_seconds=20
        )
        
        self.logic.register_operation_config(custom_config)
        
        assert "custom_operation" in self.logic.operation_configs
        assert self.logic.operation_configs["custom_operation"] == custom_config
    
    def test_get_fallback_behavior_with_options(self):
        """Test getting fallback behavior for failed prerequisites."""
        failed_prerequisites = ["Ollama LLM Service", "System Health"]
        
        fallback = self.logic.get_fallback_behavior("chat", failed_prerequisites)
        
        assert fallback["fallback_available"] is True
        assert "llm" in fallback["fallback_options"]
        assert "system" in fallback["fallback_options"]
        
        # Check LLM fallback details
        llm_fallback = fallback["fallback_options"]["llm"]
        assert llm_fallback["available"] is True
        assert "cached responses" in llm_fallback["description"]
        assert len(llm_fallback["limitations"]) > 0
    
    def test_get_fallback_behavior_no_fallback(self):
        """Test getting fallback behavior when no fallback available."""
        failed_prerequisites = ["PostgreSQL Database"]
        
        fallback = self.logic.get_fallback_behavior("chat", failed_prerequisites)
        
        assert "database" in fallback["fallback_options"]
        database_fallback = fallback["fallback_options"]["database"]
        assert database_fallback["available"] is False
    
    def test_get_fallback_behavior_unknown_operation(self):
        """Test getting fallback behavior for unknown operation."""
        fallback = self.logic.get_fallback_behavior("unknown", ["Any Checker"])
        
        assert fallback["fallback_available"] is False
    
    def test_get_prerequisite_service_uses_provided_service(self):
        """Test that provided prerequisite service is used."""
        result_service = self.logic._get_prerequisite_service(self.user_id)
        
        assert result_service == self.fake_service
    
    def test_parallel_execution_timeout_behavior(self):
        """Test parallel execution timeout behavior with fake service."""
        # This test focuses on the logic behavior rather than actual parallel execution
        # We test that the method handles timeout scenarios correctly
        
        # Create a test suite that simulates timeout results
        timeout_result = create_failed_prerequisite_result(
            name="Slow Checker",
            message="Check timed out after 1s",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        fast_result = create_prerequisite_result(
            name="Fast Checker",
            status=PrerequisiteStatus.PASSED,
            message="Fast check passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        test_suite = create_prerequisite_check_suite(
            overall_status=PrerequisiteStatus.FAILED,
            required_passed=False,
            recommended_passed=True,
            results=[fast_result, timeout_result],
            total_check_time=1.0
        )
        
        self.fake_service.set_run_specific_checks_result(test_suite)
        
        # Test that the logic handles timeout results appropriately
        result = self.logic.validate_for_operation("chat", parallel_execution=False)
        
        assert len(result.results) == 2
        assert result.overall_status == PrerequisiteStatus.FAILED
        
        # Verify timeout result is handled
        timeout_found = any("timed out" in r.message for r in result.results)
        assert timeout_found
    
    def test_create_recommendation_critical_priority(self):
        """Test creating recommendation with critical priority."""
        failed_result = create_failed_prerequisite_result(
            name="Ollama LLM Service",
            message="Service unavailable",
            prerequisite_type=PrerequisiteType.REQUIRED,
            resolution_steps=["Start service", "Check config"]
        )
        
        recommendation = self.logic._create_recommendation(failed_result)
        
        assert recommendation.checker_name == "Ollama LLM Service"
        assert recommendation.priority == "critical"
        assert recommendation.issue_description == "Service unavailable"
        assert len(recommendation.resolution_steps) == 2
        assert recommendation.estimated_time == "5-10 minutes"
        assert recommendation.automation_available is False
    
    def test_create_recommendation_with_automation(self):
        """Test creating recommendation with automation available."""
        failed_result = create_failed_prerequisite_result(
            name="User Consent Status",
            message="Missing consent",
            prerequisite_type=PrerequisiteType.REQUIRED,
            resolution_steps=["Go to consent page"]
        )
        
        recommendation = self.logic._create_recommendation(failed_result)
        
        assert recommendation.automation_available is True
        assert recommendation.priority == "critical"


class TestPureLogicFunctions:
    """Test pure logic functions extracted from PrerequisiteValidationLogic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logic = PrerequisiteValidationLogic()
    
    def test_create_recommendation_priority_mapping(self):
        """Test recommendation priority mapping for different prerequisite types."""
        # Test required failed -> critical
        required_failed = create_failed_prerequisite_result(
            name="Test Required",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        rec = self.logic._create_recommendation(required_failed)
        assert rec.priority == "critical"
        
        # Test required warning -> high
        required_warning = create_warning_prerequisite_result(
            name="Test Required Warning",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        rec = self.logic._create_recommendation(required_warning)
        assert rec.priority == "high"
        
        # Test recommended -> medium
        recommended_failed = create_failed_prerequisite_result(
            name="Test Recommended",
            prerequisite_type=PrerequisiteType.RECOMMENDED
        )
        rec = self.logic._create_recommendation(recommended_failed)
        assert rec.priority == "medium"
    
    def test_fallback_behavior_analysis(self):
        """Test fallback behavior analysis for different failed prerequisites."""
        # Test LLM service fallback
        llm_fallback = self.logic.get_fallback_behavior("chat", ["Ollama LLM Service"])
        assert llm_fallback["fallback_available"] is True
        assert "llm" in llm_fallback["fallback_options"]
        assert llm_fallback["fallback_options"]["llm"]["available"] is True
        
        # Test database fallback (not available)
        db_fallback = self.logic.get_fallback_behavior("chat", ["PostgreSQL Database"])
        assert "database" in db_fallback["fallback_options"]
        assert db_fallback["fallback_options"]["database"]["available"] is False
        
        # Test system health fallback
        system_fallback = self.logic.get_fallback_behavior("chat", ["System Health"])
        assert system_fallback["fallback_available"] is True
        assert "system" in system_fallback["fallback_options"]
        assert system_fallback["fallback_options"]["system"]["available"] is True
    
    def test_operation_config_registration(self):
        """Test operation configuration registration."""
        custom_config = OperationPrerequisites(
            operation_name="test_operation",
            required_checkers={"Test Checker"},
            recommended_checkers=set(),
            optional_checkers=set(),
            timeout_seconds=15
        )
        
        self.logic.register_operation_config(custom_config)
        
        assert "test_operation" in self.logic.operation_configs
        registered_config = self.logic.operation_configs["test_operation"]
        assert registered_config.operation_name == "test_operation"
        assert "Test Checker" in registered_config.required_checkers
        assert registered_config.timeout_seconds == 15


class TestCreatePrerequisiteValidationLogic:
    """Test cases for factory function."""
    
    def test_create_with_user_id(self):
        """Test creating logic with user ID."""
        fake_consent_service = FakeConsentService()
        user_id = uuid4()
        
        logic = create_prerequisite_validation_logic(
            user_id=user_id,
            consent_service=fake_consent_service
        )
        
        assert isinstance(logic, PrerequisiteValidationLogic)
        assert logic.consent_service == fake_consent_service
        # The factory function creates a real service, so we just verify the type
        assert logic.prerequisite_service is not None
    
    def test_create_without_user_id(self):
        """Test creating logic without user ID."""
        logic = create_prerequisite_validation_logic()
        
        assert isinstance(logic, PrerequisiteValidationLogic)
        assert logic.consent_service is None
        # The factory function creates a real service, so we just verify the type
        assert logic.prerequisite_service is not None


class TestOperationPrerequisites:
    """Test cases for OperationPrerequisites dataclass."""
    
    def test_operation_prerequisites_creation(self):
        """Test creating operation prerequisites configuration."""
        config = OperationPrerequisites(
            operation_name="test_operation",
            required_checkers={"Checker1", "Checker2"},
            recommended_checkers={"Checker3"},
            optional_checkers={"Checker4"},
            timeout_seconds=25,
            allow_partial_failure=True
        )
        
        assert config.operation_name == "test_operation"
        assert len(config.required_checkers) == 2
        assert len(config.recommended_checkers) == 1
        assert len(config.optional_checkers) == 1
        assert config.timeout_seconds == 25
        assert config.allow_partial_failure is True
    
    def test_operation_prerequisites_defaults(self):
        """Test default values for operation prerequisites."""
        config = OperationPrerequisites(
            operation_name="test",
            required_checkers=set(),
            recommended_checkers=set(),
            optional_checkers=set()
        )
        
        assert config.timeout_seconds == 30  # Default
        assert config.allow_partial_failure is False  # Default


class TestPrerequisiteRecommendation:
    """Test cases for PrerequisiteRecommendation dataclass."""
    
    def test_prerequisite_recommendation_creation(self):
        """Test creating prerequisite recommendation."""
        recommendation = PrerequisiteRecommendation(
            checker_name="Test Checker",
            issue_description="Test issue",
            priority="high",
            resolution_steps=["Step 1", "Step 2"],
            estimated_time="5 minutes",
            automation_available=True
        )
        
        assert recommendation.checker_name == "Test Checker"
        assert recommendation.issue_description == "Test issue"
        assert recommendation.priority == "high"
        assert len(recommendation.resolution_steps) == 2
        assert recommendation.estimated_time == "5 minutes"
        assert recommendation.automation_available is True
    
    def test_prerequisite_recommendation_defaults(self):
        """Test default values for prerequisite recommendation."""
        recommendation = PrerequisiteRecommendation(
            checker_name="Test",
            issue_description="Issue",
            priority="medium",
            resolution_steps=[],
            estimated_time="Unknown"
        )
        
        assert recommendation.automation_available is False  # Default


if __name__ == "__main__":
    pytest.main([__file__])