"""
System integration tests with external dependencies for GITTE UX enhancements.
Tests integration with external services and dependencies.
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.services.image_isolation_service import ImageIsolationService
from src.services.image_quality_detector import ImageQualityDetector
from src.logic.prerequisite_validation import PrerequisiteValidationLogic
from src.services.prerequisite_checker import (
    OllamaConnectivityChecker,
    DatabaseConnectivityChecker,
    ConsentStatusChecker
)


class TestExternalDependencyIntegration:
    """Test integration with external dependencies."""
    
    @pytest.fixture
    def mock_external_services(self):
        """Mock external services for testing."""
        return {
            "ollama": {
                "health_endpoint": "http://localhost:11434/api/health",
                "expected_response": {"status": "ok", "version": "0.1.0"},
                "timeout": 5.0
            },
            "database": {
                "connection_string": "postgresql://test:test@localhost:5432/test_db",
                "expected_tables": ["users", "sessions", "audit_logs"],
                "timeout": 3.0
            },
            "rembg_service": {
                "model_path": "/models/u2net.onnx",
                "expected_models": ["u2net", "silueta"],
                "timeout": 10.0
            }
        }
    
    def test_ollama_connectivity_integration(self, mock_external_services):
        """Test Ollama connectivity checker with external service."""
        checker = OllamaConnectivityChecker()
        
        # Test with mocked successful response
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_external_services["ollama"]["expected_response"]
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_get.return_value = mock_response
            
            result = checker.check()
            
            assert result["passed"] is True
            assert "version" in result["details"]
            assert result["details"]["response_time_ms"] < 1000
            
            # Verify correct endpoint was called
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert mock_external_services["ollama"]["health_endpoint"] in call_args[0][0]
    
    def test_ollama_connectivity_failure_scenarios(self, mock_external_services):
        """Test Ollama connectivity checker failure scenarios."""
        checker = OllamaConnectivityChecker()
        
        # Test connection timeout
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError("Connection timeout")
            
            result = checker.check()
            
            assert result["passed"] is False
            assert "timeout" in result["message"].lower()
            assert "resolution_steps" in result
            assert len(result["resolution_steps"]) > 0
        
        # Test service unavailable
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 503
            mock_response.text = "Service Unavailable"
            mock_get.return_value = mock_response
            
            result = checker.check()
            
            assert result["passed"] is False
            assert "503" in result["message"] or "unavailable" in result["message"].lower()
        
        # Test invalid response format
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response
            
            result = checker.check()
            
            assert result["passed"] is False
            assert "invalid response" in result["message"].lower()
    
    def test_database_connectivity_integration(self, mock_external_services):
        """Test database connectivity checker with external database."""
        checker = DatabaseConnectivityChecker()
        
        # Test with mocked successful connection
        with patch('src.data.database.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.execute.return_value.fetchone.return_value = (1,)
            mock_get_session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = Mock(return_value=None)
            
            result = checker.check()
            
            assert result["passed"] is True
            assert "connection_time_ms" in result["details"]
            assert result["details"]["connection_time_ms"] < 5000
    
    def test_database_connectivity_failure_scenarios(self, mock_external_services):
        """Test database connectivity checker failure scenarios."""
        checker = DatabaseConnectivityChecker()
        
        # Test connection failure
        with patch('src.data.database.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Connection failed")
            
            result = checker.check()
            
            assert result["passed"] is False
            assert "connection failed" in result["message"].lower()
            assert "resolution_steps" in result
        
        # Test query execution failure
        with patch('src.data.database.get_session') as mock_get_session:
            mock_session = Mock()
            mock_session.execute.side_effect = Exception("Query failed")
            mock_get_session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_get_session.return_value.__exit__ = Mock(return_value=None)
            
            result = checker.check()
            
            assert result["passed"] is False
            assert "query" in result["message"].lower()
    
    def test_consent_status_integration(self, mock_external_services):
        """Test consent status checker with user data."""
        checker = ConsentStatusChecker()
        user_id = uuid4()
        
        # Test with mocked user consent data
        with patch('src.services.consent_service.ConsentService') as mock_consent_service:
            mock_service = mock_consent_service.return_value
            mock_service.get_user_consent_status.return_value = {
                "data_processing": True,
                "analytics": False,
                "marketing": False,
                "last_updated": "2024-01-01T00:00:00Z"
            }
            
            result = checker.check(user_id=user_id)
            
            assert result["passed"] is True
            assert "consent_status" in result["details"]
            assert result["details"]["consent_status"]["data_processing"] is True
    
    def test_image_isolation_external_models(self, mock_external_services):
        """Test image isolation service with external ML models."""
        service = ImageIsolationService()
        
        # Create test image
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            from PIL import Image
            img = Image.new('RGB', (512, 512), color='red')
            img.save(f.name)
            test_image_path = f.name
        
        try:
            # Test with mocked rembg service
            with patch('rembg.remove') as mock_remove:
                # Mock successful background removal
                mock_remove.return_value = Image.new('RGBA', (512, 512), (255, 0, 0, 255))
                
                result = service.isolate_person(test_image_path)
                
                # Should attempt to use external model
                mock_remove.assert_called_once()
                
                # Result should indicate success or provide fallback
                assert hasattr(result, 'success')
                assert hasattr(result, 'isolated_image_path') or hasattr(result, 'error_message')
        
        finally:
            Path(test_image_path).unlink(missing_ok=True)
    
    def test_image_isolation_model_loading_failure(self, mock_external_services):
        """Test image isolation service when external models fail to load."""
        service = ImageIsolationService()
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            from PIL import Image
            img = Image.new('RGB', (512, 512), color='red')
            img.save(f.name)
            test_image_path = f.name
        
        try:
            # Test with model loading failure
            with patch('rembg.remove') as mock_remove:
                mock_remove.side_effect = Exception("Model loading failed")
                
                result = service.isolate_person(test_image_path)
                
                # Should handle failure gracefully
                assert result.success is False
                assert "model" in result.error_message.lower() or "failed" in result.error_message.lower()
                assert hasattr(result, 'fallback_used')
        
        finally:
            Path(test_image_path).unlink(missing_ok=True)
    
    def test_prerequisite_validation_with_all_external_services(self, mock_external_services):
        """Test prerequisite validation with all external services."""
        logic = PrerequisiteValidationLogic()
        user_id = uuid4()
        
        # Register all external service checkers
        ollama_checker = OllamaConnectivityChecker()
        db_checker = DatabaseConnectivityChecker()
        consent_checker = ConsentStatusChecker()
        
        logic.register_checker(ollama_checker)
        logic.register_checker(db_checker)
        logic.register_checker(consent_checker)
        
        # Mock all external services as healthy
        with patch('requests.get') as mock_ollama_get, \
             patch('src.data.database.get_session') as mock_db_session, \
             patch('src.services.consent_service.ConsentService') as mock_consent:
            
            # Setup Ollama mock
            mock_ollama_response = Mock()
            mock_ollama_response.status_code = 200
            mock_ollama_response.json.return_value = {"status": "ok"}
            mock_ollama_response.elapsed.total_seconds.return_value = 0.1
            mock_ollama_get.return_value = mock_ollama_response
            
            # Setup database mock
            mock_session = Mock()
            mock_session.execute.return_value.fetchone.return_value = (1,)
            mock_db_session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_db_session.return_value.__exit__ = Mock(return_value=None)
            
            # Setup consent mock
            mock_consent.return_value.get_user_consent_status.return_value = {
                "data_processing": True
            }
            
            # Run validation
            results = logic.validate_prerequisites_for_operation(user_id, "chat_interaction")
            
            # All checks should pass
            assert results["overall_status"] == "passed"
            assert len(results["individual_results"]) == 3
            
            for checker_name, result in results["individual_results"].items():
                assert result["passed"] is True, f"Checker {checker_name} failed: {result.get('message')}"
    
    def test_external_service_timeout_handling(self, mock_external_services):
        """Test handling of external service timeouts."""
        logic = PrerequisiteValidationLogic()
        user_id = uuid4()
        
        # Create checker with short timeout
        ollama_checker = OllamaConnectivityChecker(timeout=0.1)
        logic.register_checker(ollama_checker)
        
        # Mock slow external service
        with patch('requests.get') as mock_get:
            def slow_response(*args, **kwargs):
                time.sleep(0.2)  # Longer than timeout
                return Mock(status_code=200)
            
            mock_get.side_effect = slow_response
            
            results = logic.validate_prerequisites_for_operation(user_id, "test_operation")
            
            # Should handle timeout gracefully
            assert results["overall_status"] == "failed"
            ollama_result = results["individual_results"]["ollama_connectivity"]
            assert ollama_result["passed"] is False
            assert "timeout" in ollama_result["message"].lower()
    
    def test_external_service_circuit_breaker(self, mock_external_services):
        """Test circuit breaker pattern for external services."""
        from src.utils.circuit_breaker import CircuitBreaker
        
        # Create circuit breaker for external service
        circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5,
            expected_exception=Exception
        )
        
        # Simulate multiple failures
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Service unavailable")
            
            # First few calls should attempt the service
            for i in range(3):
                try:
                    with circuit_breaker:
                        mock_get("http://test-service/health")
                except Exception:
                    pass
            
            # Circuit should now be open
            assert circuit_breaker.state == "open"
            
            # Next call should fail fast without calling service
            call_count_before = mock_get.call_count
            try:
                with circuit_breaker:
                    mock_get("http://test-service/health")
            except Exception:
                pass
            
            # Should not have made additional call
            assert mock_get.call_count == call_count_before
    
    def test_external_service_health_monitoring(self, mock_external_services):
        """Test continuous health monitoring of external services."""
        from src.services.monitoring_service import MonitoringService
        
        monitor = MonitoringService()
        
        # Register external services for monitoring
        monitor.register_external_service(
            "ollama",
            health_check_url=mock_external_services["ollama"]["health_endpoint"],
            check_interval=1.0
        )
        
        monitor.register_external_service(
            "database",
            health_check_function=lambda: {"status": "healthy"},
            check_interval=2.0
        )
        
        # Mock health check responses
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_get.return_value = mock_response
            
            # Start monitoring
            monitor.start_health_monitoring()
            
            # Wait for health checks
            time.sleep(1.5)
            
            # Get health status
            health_status = monitor.get_health_status()
            
            assert "ollama" in health_status
            assert health_status["ollama"]["status"] == "healthy"
            
            # Stop monitoring
            monitor.stop_health_monitoring()
    
    def test_external_service_failover(self, mock_external_services):
        """Test failover mechanisms for external services."""
        service = ImageIsolationService()
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            from PIL import Image
            img = Image.new('RGB', (512, 512), color='red')
            img.save(f.name)
            test_image_path = f.name
        
        try:
            # Test primary service failure with fallback
            with patch('rembg.remove') as mock_primary, \
                 patch('src.services.image_isolation_service.fallback_isolation') as mock_fallback:
                
                # Primary service fails
                mock_primary.side_effect = Exception("Primary service failed")
                
                # Fallback succeeds
                mock_fallback.return_value = {
                    "success": True,
                    "isolated_image_path": "fallback_result.png",
                    "method": "fallback"
                }
                
                result = service.isolate_person(test_image_path)
                
                # Should have attempted primary first
                mock_primary.assert_called_once()
                
                # Should have used fallback
                mock_fallback.assert_called_once()
                
                # Result should indicate fallback was used
                assert result.success is True
                assert hasattr(result, 'method') and result.method == "fallback"
        
        finally:
            Path(test_image_path).unlink(missing_ok=True)
    
    @pytest.mark.slow
    def test_external_service_load_testing(self, mock_external_services):
        """Test external service integration under load."""
        import concurrent.futures
        
        logic = PrerequisiteValidationLogic()
        ollama_checker = OllamaConnectivityChecker()
        logic.register_checker(ollama_checker)
        
        # Mock external service
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.elapsed.total_seconds.return_value = 0.1
            mock_get.return_value = mock_response
            
            # Run concurrent prerequisite checks
            def run_check():
                user_id = uuid4()
                return logic.validate_prerequisites_for_operation(user_id, "test_operation")
            
            # Execute multiple concurrent checks
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(run_check) for _ in range(20)]
                results = [f.result() for f in futures]
            
            # All checks should succeed
            for result in results:
                assert result["overall_status"] == "passed"
            
            # External service should have been called for each check
            assert mock_get.call_count >= 20
    
    def test_external_service_configuration_validation(self, mock_external_services):
        """Test validation of external service configurations."""
        from src.config.config import Config
        
        # Test with valid configuration
        valid_config = {
            "external_services": {
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "timeout": 5.0,
                    "retry_attempts": 3
                },
                "database": {
                    "connection_string": "postgresql://user:pass@localhost:5432/db",
                    "pool_size": 10,
                    "timeout": 3.0
                }
            }
        }
        
        config = Config(valid_config)
        validation_result = config.validate_external_services()
        
        assert validation_result["valid"] is True
        assert len(validation_result["errors"]) == 0
        
        # Test with invalid configuration
        invalid_config = {
            "external_services": {
                "ollama": {
                    "base_url": "invalid-url",  # Invalid URL
                    "timeout": -1  # Invalid timeout
                }
            }
        }
        
        config = Config(invalid_config)
        validation_result = config.validate_external_services()
        
        assert validation_result["valid"] is False
        assert len(validation_result["errors"]) > 0
        assert any("url" in error.lower() for error in validation_result["errors"])
        assert any("timeout" in error.lower() for error in validation_result["errors"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])