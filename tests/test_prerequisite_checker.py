"""
Tests for Prerequisite Checker Service.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

import pytest
import requests

from src.services.prerequisite_checker import (
    PrerequisiteChecker,
    PrerequisiteValidationService,
    OllamaConnectivityChecker,
    DatabaseConnectivityChecker,
    ConsentStatusChecker,
    SystemHealthChecker,
    PrerequisiteResult,
    PrerequisiteCheckSuite,
    PrerequisiteStatus,
    PrerequisiteType,
    create_default_prerequisite_service
)
from src.services.consent_service import ConsentType


class TestPrerequisiteResult(unittest.TestCase):
    """Test cases for PrerequisiteResult dataclass."""
    
    def test_prerequisite_result_creation(self):
        """Test creating prerequisite result."""
        result = PrerequisiteResult(
            name="Test Check",
            status=PrerequisiteStatus.PASSED,
            message="Test passed",
            details="Additional details",
            resolution_steps=["Step 1", "Step 2"],
            check_time=1.5
        )
        
        self.assertEqual(result.name, "Test Check")
        self.assertEqual(result.status, PrerequisiteStatus.PASSED)
        self.assertEqual(result.message, "Test passed")
        self.assertEqual(result.details, "Additional details")
        self.assertEqual(result.resolution_steps, ["Step 1", "Step 2"])
        self.assertEqual(result.check_time, 1.5)
        self.assertEqual(result.prerequisite_type, PrerequisiteType.REQUIRED)


class TestOllamaConnectivityChecker(unittest.TestCase):
    """Test cases for OllamaConnectivityChecker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "llm": {
                "ollama_url": "http://localhost:11434",
                "connection_timeout": 5
            }
        }
        self.checker = OllamaConnectivityChecker(self.config)
    
    @patch('requests.get')
    def test_ollama_check_success_with_models(self, mock_get):
        """Test successful Ollama check with models available."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama2:latest"},
                {"name": "codellama:7b"},
                {"name": "mistral:latest"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.PASSED)
        self.assertIn("3 models available", result.message)
        self.assertIn("llama2:latest", result.details)
        self.assertEqual(result.name, "Ollama LLM Service")
        self.assertEqual(result.prerequisite_type, PrerequisiteType.REQUIRED)
    
    @patch('requests.get')
    def test_ollama_check_success_no_models(self, mock_get):
        """Test Ollama check when service is running but no models."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_get.return_value = mock_response
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("no models are available", result.message)
        self.assertIn("ollama pull", result.resolution_steps[0])
    
    @patch('requests.get')
    def test_ollama_check_http_error(self, mock_get):
        """Test Ollama check with HTTP error response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("status 500", result.message)
        self.assertIn("Internal Server Error", result.details)
    
    @patch('requests.get')
    def test_ollama_check_connection_error(self, mock_get):
        """Test Ollama check with connection error."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("Cannot connect", result.message)
        self.assertIn("ollama serve", result.resolution_steps[0])
    
    @patch('requests.get')
    def test_ollama_check_timeout(self, mock_get):
        """Test Ollama check with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("timed out", result.message)
        self.assertIn("5s", result.message)
    
    @patch('requests.get')
    def test_ollama_check_unexpected_error(self, mock_get):
        """Test Ollama check with unexpected error."""
        mock_get.side_effect = ValueError("Unexpected error")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("Unexpected error", result.message)
        self.assertIn("ValueError", result.details)


class TestDatabaseConnectivityChecker(unittest.TestCase):
    """Test cases for DatabaseConnectivityChecker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = {
            "database": {
                "dsn": "postgresql://test:test@localhost/test_db",
                "connection_timeout": 5
            }
        }
        self.checker = DatabaseConnectivityChecker(self.config)
    
    @patch('sqlalchemy.create_engine')
    def test_database_check_success(self, mock_create_engine):
        """Test successful database check."""
        # Mock engine and connection
        mock_engine = Mock()
        mock_conn = Mock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_conn
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        
        # Mock version query
        version_result = Mock()
        version_result.fetchone.return_value = ["PostgreSQL 13.7 on x86_64-pc-linux-gnu"]
        mock_conn.execute.return_value = version_result
        
        # Mock table count query (second call)
        table_result = Mock()
        table_result.fetchone.return_value = [2]  # Both tables exist
        mock_conn.execute.side_effect = [version_result, table_result]
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.PASSED)
        self.assertIn("connected successfully", result.message)
        self.assertIn("PostgreSQL 13.7", result.details)
        self.assertEqual(result.name, "PostgreSQL Database")
    
    @patch('sqlalchemy.create_engine')
    def test_database_check_incomplete_schema(self, mock_create_engine):
        """Test database check with incomplete schema."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_create_engine.return_value = mock_engine
        mock_engine.connect.return_value = mock_conn
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        
        # Mock version query
        version_result = Mock()
        version_result.fetchone.return_value = ["PostgreSQL 13.7"]
        
        # Mock table count query - only 1 table found
        table_result = Mock()
        table_result.fetchone.return_value = [1]
        mock_conn.execute.side_effect = [version_result, table_result]
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.WARNING)
        self.assertIn("schema may be incomplete", result.message)
        self.assertIn("1/2 expected tables", result.details)
        self.assertIn("alembic upgrade", result.resolution_steps[0])
    
    @patch('sqlalchemy.create_engine')
    def test_database_check_connection_error(self, mock_create_engine):
        """Test database check with connection error."""
        mock_create_engine.side_effect = Exception("Connection failed")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("connection failed", result.message)
        self.assertIn("Connection failed", result.details)
    
    @patch('sqlalchemy.create_engine')
    def test_database_check_timeout_error(self, mock_create_engine):
        """Test database check with timeout error."""
        mock_create_engine.side_effect = Exception("timeout expired")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("timed out", result.message)
        self.assertIn("PostgreSQL is running", result.resolution_steps[0])
    
    @patch('sqlalchemy.create_engine')
    def test_database_check_auth_error(self, mock_create_engine):
        """Test database check with authentication error."""
        mock_create_engine.side_effect = Exception("authentication failed for user")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("authentication failed", result.message)
        self.assertIn("username and password", result.resolution_steps[0])


class TestConsentStatusChecker(unittest.TestCase):
    """Test cases for ConsentStatusChecker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user_id = uuid4()
        self.mock_consent_service = Mock()
        self.checker = ConsentStatusChecker(self.user_id, self.mock_consent_service)
    
    def test_consent_check_all_granted(self):
        """Test consent check when all consents are granted."""
        # Mock all consents as granted
        self.mock_consent_service.check_consent.return_value = True
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.PASSED)
        self.assertIn("All required consents provided", result.message)
        self.assertEqual(result.name, "User Consent Status")
        
        # Verify all consent types were checked
        expected_calls = len([ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION, ConsentType.IMAGE_GENERATION])
        self.assertEqual(self.mock_consent_service.check_consent.call_count, expected_calls)
    
    def test_consent_check_missing_consents(self):
        """Test consent check when some consents are missing."""
        # Mock mixed consent status
        consent_responses = {
            ConsentType.DATA_PROCESSING: True,
            ConsentType.AI_INTERACTION: False,
            ConsentType.IMAGE_GENERATION: False
        }
        
        def mock_check_consent(user_id, consent_type):
            return consent_responses.get(consent_type, False)
        
        self.mock_consent_service.check_consent.side_effect = mock_check_consent
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("Missing required consents", result.message)
        self.assertIn("ai_interaction", result.message)
        self.assertIn("image_generation", result.message)
        self.assertIn("Consent Settings", result.resolution_steps[0])
    
    def test_consent_check_service_error(self):
        """Test consent check when service raises error."""
        self.mock_consent_service.check_consent.side_effect = Exception("Service unavailable")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("Error checking consent", result.message)
        self.assertIn("Service unavailable", result.message)


class TestSystemHealthChecker(unittest.TestCase):
    """Test cases for SystemHealthChecker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = SystemHealthChecker()
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_percent')
    def test_system_health_check_healthy(self, mock_cpu, mock_disk, mock_memory):
        """Test system health check with healthy resources."""
        # Mock healthy system resources
        mock_memory.return_value = Mock(percent=45.0)
        mock_disk.return_value = Mock(used=50*1024**3, total=100*1024**3)  # 50% used
        mock_cpu.return_value = 25.0
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.PASSED)
        self.assertIn("resources are healthy", result.message)
        self.assertIn("Memory: 45.0%", result.details)
        self.assertIn("Disk: 50.0%", result.details)
        self.assertIn("CPU: 25.0%", result.details)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_percent')
    def test_system_health_check_warning(self, mock_cpu, mock_disk, mock_memory):
        """Test system health check with warning conditions."""
        # Mock high memory usage
        mock_memory.return_value = Mock(percent=92.0)
        mock_disk.return_value = Mock(used=50*1024**3, total=100*1024**3)  # 50% used
        mock_cpu.return_value = 25.0
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.WARNING)
        self.assertIn("under pressure", result.message)
        self.assertIn("High memory usage: 92.0%", result.details)
        self.assertIn("Close unnecessary applications", result.resolution_steps[0])
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_percent')
    def test_system_health_check_critical(self, mock_cpu, mock_disk, mock_memory):
        """Test system health check with critical conditions."""
        # Mock critical resource usage
        mock_memory.return_value = Mock(percent=95.0)
        mock_disk.return_value = Mock(used=95*1024**3, total=100*1024**3)  # 95% used
        mock_cpu.return_value = 98.0
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.FAILED)
        self.assertIn("critically low", result.message)
        self.assertIn("High memory usage", result.details)
        self.assertIn("Low disk space", result.details)
        self.assertIn("High CPU usage", result.details)
    
    @patch('builtins.__import__')
    def test_system_health_check_psutil_missing(self, mock_import):
        """Test system health check when psutil is not available."""
        def mock_import_func(name, *args, **kwargs):
            if name == 'psutil':
                raise ImportError("No module named 'psutil'")
            return __import__(name, *args, **kwargs)
        
        mock_import.side_effect = mock_import_func
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.WARNING)
        self.assertIn("monitoring unavailable", result.message)
        self.assertIn("psutil not installed", result.message)
    
    @patch('psutil.virtual_memory')
    def test_system_health_check_error(self, mock_memory):
        """Test system health check with unexpected error."""
        mock_memory.side_effect = Exception("System error")
        
        result = self.checker.check()
        
        self.assertEqual(result.status, PrerequisiteStatus.WARNING)
        self.assertIn("health check failed", result.message)
        self.assertIn("System error", result.message)


class TestPrerequisiteValidationService(unittest.TestCase):
    """Test cases for PrerequisiteValidationService."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = PrerequisiteValidationService()
        
        # Create mock checkers
        self.mock_checker1 = Mock(spec=PrerequisiteChecker)
        self.mock_checker1.name = "Test Checker 1"
        self.mock_checker1.prerequisite_type = PrerequisiteType.REQUIRED
        
        self.mock_checker2 = Mock(spec=PrerequisiteChecker)
        self.mock_checker2.name = "Test Checker 2"
        self.mock_checker2.prerequisite_type = PrerequisiteType.RECOMMENDED
    
    def test_register_checker(self):
        """Test registering prerequisite checkers."""
        self.service.register_checker(self.mock_checker1)
        
        self.assertIn(self.mock_checker1, self.service.checkers)
        self.assertEqual(len(self.service.checkers), 1)
    
    def test_run_all_checks_success(self):
        """Test running all checks with successful results."""
        # Setup mock results
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        result2 = PrerequisiteResult(
            name="Test Checker 2", 
            status=PrerequisiteStatus.PASSED,
            message="Test 2 passed",
            prerequisite_type=PrerequisiteType.RECOMMENDED
        )
        
        self.mock_checker1.check.return_value = result1
        self.mock_checker2.check.return_value = result2
        
        # Register checkers and run
        self.service.register_checker(self.mock_checker1)
        self.service.register_checker(self.mock_checker2)
        
        suite = self.service.run_all_checks(use_cache=False)
        
        self.assertEqual(suite.overall_status, PrerequisiteStatus.PASSED)
        self.assertTrue(suite.required_passed)
        self.assertTrue(suite.recommended_passed)
        self.assertEqual(len(suite.results), 2)
        self.assertFalse(suite.cached)
    
    def test_run_all_checks_required_failure(self):
        """Test running all checks with required failure."""
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.FAILED,
            message="Test 1 failed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        result2 = PrerequisiteResult(
            name="Test Checker 2",
            status=PrerequisiteStatus.PASSED,
            message="Test 2 passed",
            prerequisite_type=PrerequisiteType.RECOMMENDED
        )
        
        self.mock_checker1.check.return_value = result1
        self.mock_checker2.check.return_value = result2
        
        self.service.register_checker(self.mock_checker1)
        self.service.register_checker(self.mock_checker2)
        
        suite = self.service.run_all_checks(use_cache=False)
        
        self.assertEqual(suite.overall_status, PrerequisiteStatus.FAILED)
        self.assertFalse(suite.required_passed)
        self.assertTrue(suite.recommended_passed)
    
    def test_run_all_checks_recommended_failure(self):
        """Test running all checks with recommended failure."""
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        result2 = PrerequisiteResult(
            name="Test Checker 2",
            status=PrerequisiteStatus.FAILED,
            message="Test 2 failed",
            prerequisite_type=PrerequisiteType.RECOMMENDED
        )
        
        self.mock_checker1.check.return_value = result1
        self.mock_checker2.check.return_value = result2
        
        self.service.register_checker(self.mock_checker1)
        self.service.register_checker(self.mock_checker2)
        
        suite = self.service.run_all_checks(use_cache=False)
        
        self.assertEqual(suite.overall_status, PrerequisiteStatus.WARNING)
        self.assertTrue(suite.required_passed)
        self.assertFalse(suite.recommended_passed)
    
    def test_run_specific_checks(self):
        """Test running specific checks by name."""
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        self.mock_checker1.check.return_value = result1
        self.service.register_checker(self.mock_checker1)
        self.service.register_checker(self.mock_checker2)
        
        suite = self.service.run_specific_checks(["Test Checker 1"], use_cache=False)
        
        self.assertEqual(len(suite.results), 1)
        self.assertEqual(suite.results[0].name, "Test Checker 1")
        self.mock_checker1.check.assert_called_once()
        self.mock_checker2.check.assert_not_called()
    
    def test_caching_functionality(self):
        """Test caching of prerequisite results."""
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        self.mock_checker1.check.return_value = result1
        self.service.register_checker(self.mock_checker1)
        
        # First run - should execute check
        suite1 = self.service.run_all_checks(use_cache=True)
        self.mock_checker1.check.assert_called_once()
        
        # Second run - should use cache
        suite2 = self.service.run_all_checks(use_cache=True)
        self.mock_checker1.check.assert_called_once()  # Still only called once
        self.assertTrue(suite2.cached)
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        # Set very short TTL for testing
        self.service.cache_ttl = 0.1  # 100ms
        
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        self.mock_checker1.check.return_value = result1
        self.service.register_checker(self.mock_checker1)
        
        # First run
        self.service.run_all_checks(use_cache=True)
        self.mock_checker1.check.assert_called_once()
        
        # Wait for cache to expire
        import time
        time.sleep(0.2)
        
        # Second run - should execute check again
        self.service.run_all_checks(use_cache=True)
        self.assertEqual(self.mock_checker1.check.call_count, 2)
    
    def test_clear_cache(self):
        """Test clearing cache functionality."""
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        self.mock_checker1.check.return_value = result1
        self.service.register_checker(self.mock_checker1)
        
        # Run to populate cache
        self.service.run_all_checks(use_cache=True)
        self.assertEqual(len(self.service.cache), 1)
        
        # Clear cache
        self.service.clear_cache()
        self.assertEqual(len(self.service.cache), 0)
        self.assertEqual(len(self.service.cache_timestamps), 0)
    
    def test_clear_specific_cache(self):
        """Test clearing specific checker cache."""
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        result2 = PrerequisiteResult(
            name="Test Checker 2",
            status=PrerequisiteStatus.PASSED,
            message="Test 2 passed",
            prerequisite_type=PrerequisiteType.RECOMMENDED
        )
        
        self.mock_checker1.check.return_value = result1
        self.mock_checker2.check.return_value = result2
        
        self.service.register_checker(self.mock_checker1)
        self.service.register_checker(self.mock_checker2)
        
        # Run to populate cache
        self.service.run_all_checks(use_cache=True)
        self.assertEqual(len(self.service.cache), 2)
        
        # Clear specific cache
        self.service.clear_cache("Test Checker 1")
        self.assertEqual(len(self.service.cache), 1)
        self.assertNotIn("Test Checker 1", self.service.cache)
        self.assertIn("Test Checker 2", self.service.cache)
    
    def test_get_cache_status(self):
        """Test getting cache status information."""
        result1 = PrerequisiteResult(
            name="Test Checker 1",
            status=PrerequisiteStatus.PASSED,
            message="Test 1 passed",
            prerequisite_type=PrerequisiteType.REQUIRED
        )
        
        self.mock_checker1.check.return_value = result1
        self.service.register_checker(self.mock_checker1)
        
        # Run to populate cache
        self.service.run_all_checks(use_cache=True)
        
        cache_status = self.service.get_cache_status()
        
        self.assertIn("cache_ttl_seconds", cache_status)
        self.assertIn("cached_checkers", cache_status)
        self.assertIn("total_checkers", cache_status)
        self.assertIn("cache_details", cache_status)
        
        self.assertEqual(cache_status["cached_checkers"], 1)
        self.assertEqual(cache_status["total_checkers"], 1)
        self.assertIn("Test Checker 1", cache_status["cache_details"])
    
    def test_get_registered_checkers(self):
        """Test getting list of registered checkers."""
        self.service.register_checker(self.mock_checker1)
        self.service.register_checker(self.mock_checker2)
        
        checker_names = self.service.get_registered_checkers()
        
        self.assertEqual(len(checker_names), 2)
        self.assertIn("Test Checker 1", checker_names)
        self.assertIn("Test Checker 2", checker_names)


class TestCreateDefaultPrerequisiteService(unittest.TestCase):
    """Test cases for create_default_prerequisite_service function."""
    
    def test_create_default_service_without_user(self):
        """Test creating default service without user-specific checkers."""
        service = create_default_prerequisite_service()
        
        checker_names = service.get_registered_checkers()
        
        # Should have system-level checkers
        self.assertIn("Ollama LLM Service", checker_names)
        self.assertIn("PostgreSQL Database", checker_names)
        self.assertIn("System Health", checker_names)
        
        # Should not have user-specific checkers
        self.assertNotIn("User Consent Status", checker_names)
    
    def test_create_default_service_with_user(self):
        """Test creating default service with user-specific checkers."""
        user_id = uuid4()
        mock_consent_service = Mock()
        
        service = create_default_prerequisite_service(user_id, mock_consent_service)
        
        checker_names = service.get_registered_checkers()
        
        # Should have all checkers including user-specific
        self.assertIn("Ollama LLM Service", checker_names)
        self.assertIn("PostgreSQL Database", checker_names)
        self.assertIn("System Health", checker_names)
        self.assertIn("User Consent Status", checker_names)


class TestPrerequisiteCheckSuite(unittest.TestCase):
    """Test cases for PrerequisiteCheckSuite dataclass."""
    
    def test_prerequisite_check_suite_creation(self):
        """Test creating prerequisite check suite."""
        results = [
            PrerequisiteResult(
                name="Test 1",
                status=PrerequisiteStatus.PASSED,
                message="Passed",
                prerequisite_type=PrerequisiteType.REQUIRED
            ),
            PrerequisiteResult(
                name="Test 2",
                status=PrerequisiteStatus.WARNING,
                message="Warning",
                prerequisite_type=PrerequisiteType.RECOMMENDED
            )
        ]
        
        suite = PrerequisiteCheckSuite(
            overall_status=PrerequisiteStatus.WARNING,
            required_passed=True,
            recommended_passed=False,
            results=results,
            total_check_time=2.5,
            timestamp="2024-01-01T12:00:00",
            cached=True
        )
        
        self.assertEqual(suite.overall_status, PrerequisiteStatus.WARNING)
        self.assertTrue(suite.required_passed)
        self.assertFalse(suite.recommended_passed)
        self.assertEqual(len(suite.results), 2)
        self.assertEqual(suite.total_check_time, 2.5)
        self.assertTrue(suite.cached)


if __name__ == '__main__':
    unittest.main()