"""
Tests for Image Isolation Prerequisite Checker.
Tests the ImageIsolationPrereqChecker functionality and integration.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.services.prerequisite_checker import ImageIsolationPrereqChecker, PrerequisiteStatus, PrerequisiteType


class TestImageIsolationPrereqChecker(unittest.TestCase):
    """Test cases for ImageIsolationPrereqChecker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.checker = ImageIsolationPrereqChecker()
    
    def test_checker_initialization(self):
        """Test checker is properly initialized."""
        assert self.checker.name == "Image Isolation Service"
        assert self.checker.prerequisite_type == PrerequisiteType.RECOMMENDED
    
    @patch('src.services.prerequisite_checker.config')
    def test_check_endpoint_not_configured(self, mock_config):
        """Test checker fails when endpoint is not configured."""
        # Mock config without endpoint
        mock_config.image_isolation.endpoint = ""
        
        result = self.checker.check()
        
        assert result.status == PrerequisiteStatus.FAILED
        assert "endpoint not configured" in result.message
        assert len(result.resolution_steps) > 0
        assert "ISOLATION_ENDPOINT" in result.resolution_steps[0]
    
    @patch('src.services.prerequisite_checker.config')
    @patch('src.services.prerequisite_checker.requests.head')
    def test_check_endpoint_responds_successfully(self, mock_head, mock_config):
        """Test checker passes when endpoint responds successfully."""
        # Mock config with endpoint
        mock_config.image_isolation.endpoint = "http://localhost:8080/isolate"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_head.return_value = mock_response
        
        result = self.checker.check()
        
        assert result.status == PrerequisiteStatus.PASSED
        assert "service is available" in result.message
        assert result.details["endpoint"] == "http://localhost:8080/isolate"
        assert "response_time" in result.details
    
    @patch('src.services.prerequisite_checker.config')
    @patch('src.services.prerequisite_checker.requests.head')
    def test_check_endpoint_method_not_allowed(self, mock_head, mock_config):
        """Test checker passes when endpoint returns 405 (method not allowed)."""
        # Mock config with endpoint
        mock_config.image_isolation.endpoint = "http://localhost:8080/isolate"
        
        # Mock response with 405 (method not allowed but service is up)
        mock_response = Mock()
        mock_response.status_code = 405
        mock_response.elapsed.total_seconds.return_value = 0.1
        mock_head.return_value = mock_response
        
        result = self.checker.check()
        
        assert result.status == PrerequisiteStatus.PASSED
        assert "service is available" in result.message
    
    @patch('src.services.prerequisite_checker.config')
    @patch('src.services.prerequisite_checker.requests.head')
    def test_check_endpoint_returns_error_status(self, mock_head, mock_config):
        """Test checker fails when endpoint returns error status."""
        # Mock config with endpoint
        mock_config.image_isolation.endpoint = "http://localhost:8080/isolate"
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response
        
        result = self.checker.check()
        
        assert result.status == PrerequisiteStatus.FAILED
        assert "status 500" in result.message
        assert len(result.resolution_steps) > 0
        assert result.details["status_code"] == 500
    
    @patch('src.services.prerequisite_checker.config')
    @patch('src.services.prerequisite_checker.requests.head')
    def test_check_connection_error(self, mock_head, mock_config):
        """Test checker fails with connection error."""
        # Mock config with endpoint
        mock_config.image_isolation.endpoint = "http://localhost:8080/isolate"
        
        # Mock connection error
        from requests.exceptions import ConnectionError
        mock_head.side_effect = ConnectionError("Connection refused")
        
        result = self.checker.check()
        
        assert result.status == PrerequisiteStatus.FAILED
        assert "Cannot connect" in result.message
        assert len(result.resolution_steps) > 0
        assert "network connectivity" in result.resolution_steps[1]
    
    @patch('src.services.prerequisite_checker.config')
    @patch('src.services.prerequisite_checker.requests.head')
    def test_check_timeout_error(self, mock_head, mock_config):
        """Test checker fails with timeout error."""
        # Mock config with endpoint
        mock_config.image_isolation.endpoint = "http://localhost:8080/isolate"
        
        # Mock timeout error
        from requests.exceptions import Timeout
        mock_head.side_effect = Timeout("Request timed out")
        
        result = self.checker.check()
        
        assert result.status == PrerequisiteStatus.FAILED
        assert "timeout" in result.message
        assert len(result.resolution_steps) > 0
        assert "timeout settings" in result.resolution_steps[1]
    
    @patch('src.services.prerequisite_checker.config')
    @patch('src.services.prerequisite_checker.requests.head')
    def test_check_unexpected_exception(self, mock_head, mock_config):
        """Test checker fails with unexpected exception."""
        # Mock config with endpoint
        mock_config.image_isolation.endpoint = "http://localhost:8080/isolate"
        
        # Mock unexpected exception
        mock_head.side_effect = Exception("Unexpected error")
        
        result = self.checker.check()
        
        assert result.status == PrerequisiteStatus.FAILED
        assert "Failed to check" in result.message
        assert len(result.resolution_steps) > 0
        assert "service configuration" in result.resolution_steps[0]


if __name__ == '__main__':
    unittest.main()
