"""
Unit tests for prerequisite validation logic.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from uuid import uuid4

from src.logic.prerequisite_validation import (
    PrerequisiteValidationLogic,
    OperationPrerequisites,
    PrerequisiteRecommendation,
    create_prerequisite_validation_logic
)
from src.services.prerequisite_checker import (
    PrerequisiteValidationService,
    PrerequisiteCheckSuite,
    PrerequisiteResult,
    PrerequisiteStatus,
    PrerequisiteType,
    OllamaConnectivityChecker,
    DatabaseConnectivityChecker
)


class TestPrerequisiteValidationLogic:
    """Test cases for PrerequisiteValidationLogic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock(spec=PrerequisiteValidationService)
        self.mock_consent_service = Mock()
        self.user_id = uuid4()
        
        self.logic = PrerequisiteValidationLogic(
            prerequisite_service=self.mock_service,
            consent_service=self.mock_consent_service
        )
    
    def test_initialization(self):
        """Test logic initialization."""
        assert self.logic.prerequisite_service == self.mock_service
        assert self.logic.consent_service == self.mock_consent_service
        assert len(self.logic.operation_configs) > 0
        
        # Check default operation configs are loaded
        assert "registration" in self.logic.operation_configs
        assert "chat" in self.logic.operation_configs
        assert "image_generation" in self.logic.operation_configs
        assert "system_startup" in self.logic.operation_configs
    
    def test_validate_for_operation_with_config(self):
        """Test validation for operation with specific configuration."""
        # Mock check suite result
        mock_result = PrerequisiteResult(
            name="PostgreSQL Database",
            status=PrerequisiteStatus.PASSED,
            message="Database connected",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        mock_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[mock_result],
            total_check_time=1.5,
            timestamp=datetime.now().isoformat()
        )
        
        self.mock_service.run_specific_checks.return_value = mock_suite
        
        # Test registration operation
        result = self.logic.validate_for_operation(
            "registration",
            user_id=self.user_id,
            parallel_execution=False
        )
        
        assert result == mock_suite
        self.mock_service.run_specific_checks.assert_called_once()
    
    def test_validate_for_operation_unknown_operation(self):
        """Test validation for unknown operation falls back to all checks."""
        mock_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[],
            total_check_time=1.0,
            timestamp=datetime.now().isoformat()
        )
        
        self.mock_service.run_all_checks.return_value = mock_suite
        
        result = self.logic.validate_for_operation("unknown_operation")
        
        assert result == mock_suite
        self.mock_service.run_all_checks.assert_called_once_with(use_cache=True)
    
    def test_analyze_prerequisite_failures(self):
        """Test analysis of prerequisite failures."""
        failed_result = PrerequisiteResult(
            name="Ollama LLM Service",
            status=PrerequisiteStatus.FAILED,
            message="Cannot connect to Ollama",
            resolution_steps=["Start Ollama service", "Check configuration"],
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        warning_result = PrerequisiteResult(
            name="System Health",
            status=PrerequisiteStatus.WARNING,
            message="High memory usage",
            resolution_steps=["Close applications"],
            prerequisite_type=PrerequisiteType.RECOMMENDED
        )
        
        passed_result = PrerequisiteResult(
            name="PostgreSQL Database",
            status=PrerequisiteStatus.PASSED,
            message="Database connected",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.FAILED,
            required_passed=False,
            recommended_passed=False,
            results=[failed_result, warning_result, passed_result],
            total_check_time=2.0,
            timestamp=datetime.now().isoformat()
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
        passed_result = PrerequisiteResult(
            name="PostgreSQL Database",
            status=PrerequisiteStatus.PASSED,
            message="Database connected",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.PASSED,
            required_passed=True,
            recommended_passed=True,
            results=[passed_result],
            total_check_time=1.0,
            timestamp=datetime.now().isoformat(),
            cached=True
        )
        
        with patch.object(self.logic, 'validate_for_operation', return_value=check_suite):
            readiness = self.logic.check_operation_readiness("registration")
        
        assert readiness["ready"] is True
        assert readiness["can_proceed_with_warnings"] is True
        assert len(readiness["required_failures"]) == 0
        assert len(readiness["recommended_failures"]) == 0
        assert readiness["cached"] is True
    
    def test_check_operation_readiness_not_ready(self):
        """Test operation readiness check when not ready."""
        failed_result = PrerequisiteResult(
            name="PostgreSQL Database",
            status=PrerequisiteStatus.FAILED,
            message="Cannot connect",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        check_suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.FAILED,
            required_passed=False,
            recommended_passed=True,
            results=[failed_result],
            total_check_time=2.0,
            timestamp=datetime.now().isoformat()
        )
        
        with patch.object(self.logic, 'validate_for_operation', return_value=check_suite):
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
    
    @patch('src.logic.prerequisite_validation.create_default_prerequisite_service')
    def test_get_prerequisite_service_creates_default(self, mock_create_service):
        """Test that prerequisite service is created when not provided."""
        mock_service = Mock()
        mock_create_service.return_value = mock_service
        
        logic = PrerequisiteValidationLogic(consent_service=self.mock_consent_service)
        
        result_service = logic._get_prerequisite_service(self.user_id)
        
        assert result_service == mock_service
        mock_create_service.assert_called_once_with(
            user_id=self.user_id,
            consent_service=self.mock_consent_service
        )
    
    def test_parallel_execution_timeout_handling(self):
        """Test parallel execution with timeout handling."""
        # Create mock checkers
        mock_checker1 = Mock()
        mock_checker1.name = "Fast Checker"
        mock_checker1.prerequisite_type = PrerequisiteType.REQUIRED
        mock_checker1.check.return_value = PrerequisiteResult(
            name="Fast Checker",
            status=PrerequisiteStatus.PASSED,
            message="Fast check passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        mock_checker2 = Mock()
        mock_checker2.name = "Slow Checker"
        mock_checker2.prerequisite_type = PrerequisiteType.REQUIRED
        
        # Mock slow checker that times out
        def slow_check():
            import time
            time.sleep(2)  # Simulate slow operation
            return PrerequisiteResult(
                name="Slow Checker",
                status=PrerequisiteStatus.PASSED,
                message="Slow check passed",
                prerequisite_type=PrerequisiteType.REQUIRED
            )
        
        mock_checker2.check.side_effect = slow_check
        
        self.mock_service.checkers = [mock_checker1, mock_checker2]
        self.mock_service.cache = {}
        self.mock_service.cache_timestamps = {}
        self.mock_service._is_cached_valid.return_value = False
        
        # Run with short timeout
        result = self.logic._run_parallel_checks(
            self.mock_service,
            ["Fast Checker", "Slow Checker"],
            timeout_seconds=1,  # Short timeout
            use_cache=False
        )
        
        assert len(result.results) == 2
        
        # Fast checker should pass
        fast_result = next(r for r in result.results if r.name == "Fast Checker")
        assert fast_result.status == PrerequisiteStatus.PASSED
        
        # Slow checker should timeout
        slow_result = next(r for r in result.results if r.name == "Slow Checker")
        assert slow_result.status == PrerequisiteStatus.FAILED
        assert "timed out" in slow_result.message
    
    def test_create_recommendation_critical_priority(self):
        """Test creating recommendation with critical priority."""
        failed_result = PrerequisiteResult(
            name="Ollama LLM Service",
            status=PrerequisiteStatus.FAILED,
            message="Service unavailable",
            resolution_steps=["Start service", "Check config"],
            prerequisite_type=PrerequisiteType.REQUIRED
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
        failed_result = PrerequisiteResult(
            name="User Consent Status",
            status=PrerequisiteStatus.FAILED,
            message="Missing consent",
            resolution_steps=["Go to consent page"],
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        recommendation = self.logic._create_recommendation(failed_result)
        
        assert recommendation.automation_available is True
        assert recommendation.priority == "critical"


class TestCreatePrerequisiteValidationLogic:
    """Test cases for factory function."""
    
    @patch('src.logic.prerequisite_validation.create_default_prerequisite_service')
    def test_create_with_user_id(self, mock_create_service):
        """Test creating logic with user ID."""
        mock_service = Mock()
        mock_create_service.return_value = mock_service
        mock_consent_service = Mock()
        user_id = uuid4()
        
        logic = create_prerequisite_validation_logic(
            user_id=user_id,
            consent_service=mock_consent_service
        )
        
        assert isinstance(logic, PrerequisiteValidationLogic)
        assert logic.prerequisite_service == mock_service
        assert logic.consent_service == mock_consent_service
        
        mock_create_service.assert_called_once_with(
            user_id=user_id,
            consent_service=mock_consent_service
        )
    
    @patch('src.logic.prerequisite_validation.create_default_prerequisite_service')
    def test_create_without_user_id(self, mock_create_service):
        """Test creating logic without user ID."""
        mock_service = Mock()
        mock_create_service.return_value = mock_service
        
        logic = create_prerequisite_validation_logic()
        
        assert isinstance(logic, PrerequisiteValidationLogic)
        assert logic.prerequisite_service == mock_service
        assert logic.consent_service is None
        
        mock_create_service.assert_called_once_with(
            user_id=None,
            consent_service=None
        )


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