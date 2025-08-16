"""
Integration tests for enhanced PALD processing workflows.
Tests the integration between PALDManager, enhanced components, and service layer.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

from src.logic.pald import PALDManager, PALDProcessingRequest, PALDProcessingResponse
from src.services.pald_service import EnhancedPALDService
from src.logic.pald_light_extraction import PALDLightResult
from src.logic.bias_analysis import BiasType, JobStatus
from src.logic.pald_diff_calculation import PALDDiffResult, FieldStatus
from config.pald_enhancement import PALDEnhancementConfig


class TestEnhancedPALDIntegration:
    """Test enhanced PALD processing integration."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def pald_manager(self, mock_db_session):
        """Create PALDManager instance with mocked dependencies."""
        manager = PALDManager(mock_db_session)
        
        # Mock the enhanced components
        manager.pald_extractor = Mock()
        manager.bias_analyzer = Mock()
        manager.bias_job_manager = Mock()
        manager.diff_calculator = Mock()
        manager.persistence_manager = Mock()
        
        return manager
    
    @pytest.fixture
    def enhanced_service(self, mock_db_session, pald_manager):
        """Create EnhancedPALDService instance."""
        service = EnhancedPALDService(mock_db_session)
        service.set_pald_manager(pald_manager)
        return service
    
    @pytest.fixture
    def sample_request(self):
        """Sample PALD processing request."""
        return PALDProcessingRequest(
            user_id=uuid4(),
            session_id="test_session_123",
            description_text="A friendly teacher with brown hair",
            embodiment_caption="A smiling woman with brown hair wearing a blue shirt",
            defer_bias_scan=True,
            processing_options={}
        )
    
    def test_enhanced_pald_processing_success(self, pald_manager, sample_request):
        """Test successful enhanced PALD processing."""
        # Mock PALD Light extraction
        mock_pald_light = PALDLightResult(
            pald_light={
                "global_design_level": {"type": "human"},
                "detailed_level": {"gender": "female", "clothing": "blue shirt"}
            },
            extraction_confidence=0.85,
            filled_fields=["global_design_level.type", "detailed_level.gender"],
            missing_fields=[],
            validation_errors=[],
            compressed_prompt="female teacher blue shirt"
        )
        pald_manager.pald_extractor.extract_from_text.return_value = mock_pald_light
        
        # Mock diff calculation
        mock_diff_result = PALDDiffResult(
            matches={"detailed_level.gender": {"description": "female", "embodiment": "female"}},
            hallucinations={},
            missing_fields={},
            similarity_score=0.9,
            field_classifications={"detailed_level.gender": FieldStatus.MATCH},
            summary="High consistency between description and embodiment"
        )
        pald_manager.diff_calculator.calculate_diff.return_value = mock_diff_result
        
        # Mock bias job creation
        pald_manager.bias_job_manager.create_bias_job.return_value = "job_123"
        
        # Mock persistence
        pald_manager.persistence_manager.create_artifact.return_value = "artifact_456"
        
        # Process the request
        response = pald_manager.process_enhanced_pald(sample_request)
        
        # Verify response
        assert isinstance(response, PALDProcessingResponse)
        assert response.pald_light == mock_pald_light.pald_light
        assert response.pald_diff_summary == mock_diff_result.summary
        assert "bias analysis queued" in response.defer_notice.lower()
        assert response.validation_errors == []
        assert "artifact_456" in response.processing_metadata["artifact_id"]
        
        # Verify component interactions
        pald_manager.pald_extractor.extract_from_text.assert_called()
        pald_manager.diff_calculator.calculate_diff.assert_called()
        pald_manager.bias_job_manager.create_bias_job.assert_called()
        pald_manager.persistence_manager.create_artifact.assert_called()
    
    def test_enhanced_pald_processing_without_embodiment(self, pald_manager):
        """Test PALD processing without embodiment caption."""
        request = PALDProcessingRequest(
            user_id=uuid4(),
            session_id="test_session_456",
            description_text="A friendly teacher",
            embodiment_caption=None,
            defer_bias_scan=True
        )
        
        # Mock PALD Light extraction
        mock_pald_light = PALDLightResult(
            pald_light={"global_design_level": {"type": "human"}},
            extraction_confidence=0.7,
            filled_fields=["global_design_level.type"],
            missing_fields=[],
            validation_errors=[],
            compressed_prompt="teacher"
        )
        pald_manager.pald_extractor.extract_from_text.return_value = mock_pald_light
        
        # Mock persistence
        pald_manager.persistence_manager.create_artifact.return_value = "artifact_789"
        
        # Process the request
        response = pald_manager.process_enhanced_pald(request)
        
        # Verify response
        assert response.pald_light == mock_pald_light.pald_light
        assert response.pald_diff_summary is None  # No embodiment, no diff
        assert response.validation_errors == []
        
        # Verify diff calculation was not called
        pald_manager.diff_calculator.calculate_diff.assert_not_called()
    
    @patch('src.logic.pald.pald_enhancement_config')
    def test_enhanced_pald_processing_bias_disabled(self, mock_config, pald_manager, sample_request):
        """Test PALD processing with bias analysis disabled."""
        # Configure bias analysis as disabled
        mock_config.enable_bias_analysis = False
        
        # Mock PALD Light extraction
        mock_pald_light = PALDLightResult(
            pald_light={"global_design_level": {"type": "human"}},
            extraction_confidence=0.8,
            filled_fields=["global_design_level.type"],
            missing_fields=[],
            validation_errors=[],
            compressed_prompt="person"
        )
        pald_manager.pald_extractor.extract_from_text.return_value = mock_pald_light
        
        # Mock persistence
        pald_manager.persistence_manager.create_artifact.return_value = "artifact_999"
        
        # Process the request
        response = pald_manager.process_enhanced_pald(sample_request)
        
        # Verify bias analysis was not performed
        assert response.defer_notice is None
        pald_manager.bias_job_manager.create_bias_job.assert_not_called()
    
    def test_enhanced_pald_processing_extraction_failure(self, pald_manager, sample_request):
        """Test PALD processing with extraction failure."""
        # Mock extraction failure
        pald_manager.pald_extractor.extract_from_text.side_effect = Exception("Extraction failed")
        
        # Process the request
        response = pald_manager.process_enhanced_pald(sample_request)
        
        # Verify error handling
        assert response.pald_light == {"global_design_level": {"type": "human"}}  # Fallback
        assert len(response.validation_errors) > 0
        assert "extraction failed" in response.validation_errors[0].lower()
    
    def test_service_layer_integration(self, enhanced_service):
        """Test integration through service layer."""
        # Mock the manager's process_enhanced_pald method
        mock_response = PALDProcessingResponse(
            pald_light={"global_design_level": {"type": "human"}},
            pald_diff_summary="Test summary",
            defer_notice="Bias analysis queued",
            validation_errors=[],
            processing_metadata={"test": "data"}
        )
        enhanced_service.pald_manager.process_enhanced_pald = Mock(return_value=mock_response)
        
        # Prepare request data
        request_data = {
            "user_id": str(uuid4()),
            "session_id": "service_test_123",
            "description_text": "A teacher",
            "embodiment_caption": "A person teaching",
            "defer_bias_scan": True,
            "processing_options": {}
        }
        
        # Process through service
        result = enhanced_service.process_pald_request(request_data)
        
        # Verify result
        assert result["pald_light"] == mock_response.pald_light
        assert result["pald_diff_summary"] == mock_response.pald_diff_summary
        assert result["defer_notice"] == mock_response.defer_notice
        assert result["validation_errors"] == mock_response.validation_errors
        assert result["processing_metadata"] == mock_response.processing_metadata
    
    def test_bias_job_status_integration(self, enhanced_service):
        """Test bias job status retrieval through service."""
        # Mock job status
        mock_status = {
            "job_id": "test_job_123",
            "status": "completed",
            "message": "Job completed successfully"
        }
        enhanced_service.pald_manager.get_bias_job_status = Mock(return_value=mock_status)
        
        # Get status through service
        result = enhanced_service.get_bias_job_status("test_job_123")
        
        # Verify result
        assert result == mock_status
        enhanced_service.pald_manager.get_bias_job_status.assert_called_with("test_job_123")
    
    def test_bias_queue_processing_integration(self, enhanced_service):
        """Test bias queue processing through service."""
        # Mock queue processing result
        mock_result = {
            "processed_jobs": 5,
            "successful_jobs": 4,
            "failed_jobs": 1,
            "processing_timestamp": datetime.now().isoformat()
        }
        enhanced_service.pald_manager.process_bias_job_queue = Mock(return_value=mock_result)
        
        # Process queue through service
        result = enhanced_service.process_bias_queue(batch_size=10)
        
        # Verify result
        assert result == mock_result
        enhanced_service.pald_manager.process_bias_job_queue.assert_called_with(10)
    
    def test_configuration_controlled_processing(self, pald_manager, sample_request):
        """Test that processing respects configuration flags."""
        # Mock configuration
        with patch('src.logic.pald.pald_enhancement_config') as mock_config:
            mock_config.enable_bias_analysis = True
            mock_config.pald_analysis_deferred = False  # Immediate analysis
            mock_config.enable_age_shift_analysis = True
            mock_config.enable_gender_conformity_analysis = False
            
            # Mock PALD Light extraction
            mock_pald_light = PALDLightResult(
                pald_light={"global_design_level": {"type": "human"}},
                extraction_confidence=0.8,
                filled_fields=[],
                missing_fields=[],
                validation_errors=[],
                compressed_prompt="person"
            )
            pald_manager.pald_extractor.extract_from_text.return_value = mock_pald_light
            
            # Mock persistence
            pald_manager.persistence_manager.create_artifact.return_value = "artifact_config"
            
            # Process request with immediate analysis
            sample_request.defer_bias_scan = False
            response = pald_manager.process_enhanced_pald(sample_request)
            
            # Verify that enabled analysis types are used
            enabled_types = pald_manager._get_enabled_analysis_types()
            assert BiasType.AGE_SHIFT in enabled_types
            assert BiasType.GENDER_CONFORMITY not in enabled_types
    
    def test_error_recovery_and_graceful_degradation(self, pald_manager, sample_request):
        """Test error recovery and graceful degradation."""
        # Mock partial failures
        pald_manager.pald_extractor.extract_from_text.return_value = PALDLightResult(
            pald_light={"global_design_level": {"type": "human"}},
            extraction_confidence=0.5,
            filled_fields=[],
            missing_fields=[],
            validation_errors=["Minor extraction warning"],
            compressed_prompt="person"
        )
        
        # Mock diff calculation failure
        pald_manager.diff_calculator.calculate_diff.side_effect = Exception("Diff calculation failed")
        
        # Mock successful bias job creation
        pald_manager.bias_job_manager.create_bias_job.return_value = "job_recovery"
        
        # Mock successful persistence
        pald_manager.persistence_manager.create_artifact.return_value = "artifact_recovery"
        
        # Process request
        response = pald_manager.process_enhanced_pald(sample_request)
        
        # Verify graceful degradation
        assert response.pald_light is not None
        assert response.pald_diff_summary is None  # Failed diff calculation
        assert response.defer_notice is not None  # Bias analysis still works
        assert len(response.validation_errors) > 0  # Contains extraction warning
        assert response.processing_metadata["artifact_id"] == "artifact_recovery"


class TestEnhancedPALDConfigurationIntegration:
    """Test configuration-controlled processing integration."""
    
    def test_mandatory_pald_extraction_always_enabled(self):
        """Test that mandatory PALD extraction cannot be disabled."""
        config = PALDEnhancementConfig()
        
        # Verify mandatory extraction is always True
        assert config.mandatory_pald_extraction is True
        
        # Verify validation catches attempts to disable it
        config.mandatory_pald_extraction = False
        errors = config.validate()
        assert any("mandatory_pald_extraction must always be True" in error for error in errors)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        config = PALDEnhancementConfig()
        config.schema_file_path = "nonexistent_file.json"
        config.bias_job_batch_size = -1
        
        errors = config.validate()
        
        assert len(errors) >= 2
        assert any("Schema file not found" in error for error in errors)
        assert any("bias_job_batch_size must be positive" in error for error in errors)