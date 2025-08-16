"""
Contract tests for enhanced PALD processing components.
Verifies the contracts between PALDManager and enhanced components.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from src.logic.pald import PALDManager, PALDProcessingRequest
from src.logic.pald_light_extraction import PALDLightExtractor, PALDLightResult
from src.logic.bias_analysis import BiasAnalysisEngine, BiasJobManager, BiasType
from src.logic.pald_diff_calculation import PALDDiffCalculator, PALDPersistenceManager
from src.services.pald_service import EnhancedPALDService


class TestEnhancedPALDContracts:
    """Test contracts for enhanced PALD components."""
    
    def test_pald_light_extractor_contract(self):
        """Test PALDLightExtractor contract."""
        extractor = PALDLightExtractor()
        
        # Test basic extraction
        result = extractor.extract_from_text(
            description_text="A friendly teacher",
            embodiment_caption="A smiling person"
        )
        
        # Verify contract
        assert isinstance(result, PALDLightResult)
        assert isinstance(result.pald_light, dict)
        assert isinstance(result.extraction_confidence, float)
        assert isinstance(result.filled_fields, list)
        assert isinstance(result.missing_fields, list)
        assert isinstance(result.validation_errors, list)
        assert isinstance(result.compressed_prompt, str)
        assert isinstance(result.processing_metadata, dict)
        
        # Verify confidence is in valid range
        assert 0.0 <= result.extraction_confidence <= 1.0
        
        # Verify compressed prompt is not empty
        assert len(result.compressed_prompt) > 0
    
    def test_bias_analysis_engine_contract(self):
        """Test BiasAnalysisEngine contract."""
        engine = BiasAnalysisEngine()
        
        # Sample PALD data
        description_pald = {
            "detailed_level": {"age": "adult", "gender": "female"},
            "middle_design_level": {"role": "teacher", "competence": 6}
        }
        embodiment_pald = {
            "detailed_level": {"age": "young", "gender": "female"},
            "middle_design_level": {"role": "teacher", "competence": 5}
        }
        
        # Test age shift analysis
        result = engine.analyze_age_shift(description_pald, embodiment_pald)
        
        # Verify contract
        assert result.analysis_type == BiasType.AGE_SHIFT
        assert isinstance(result.findings, dict)
        assert isinstance(result.confidence_score, float)
        assert isinstance(result.indicators, list)
        assert isinstance(result.recommendations, list)
        assert isinstance(result.metadata, dict)
        
        # Verify confidence is in valid range
        assert 0.0 <= result.confidence_score <= 1.0
    
    def test_bias_job_manager_contract(self):
        """Test BiasJobManager contract."""
        manager = BiasJobManager()
        
        # Test job creation
        job_id = manager.create_bias_job(
            session_id="test_session",
            description_pald={"detailed_level": {"gender": "male"}},
            embodiment_pald={"detailed_level": {"gender": "female"}},
            analysis_types=[BiasType.AGE_SHIFT, BiasType.GENDER_CONFORMITY],
            priority=1
        )
        
        # Verify contract
        assert isinstance(job_id, str)
        assert len(job_id) > 0
        
        # Test job status retrieval
        status = manager.get_job_status(job_id)
        assert status is not None
        
        # Test queue processing
        results = manager.process_bias_queue(batch_size=1)
        assert isinstance(results, list)
        
        if results:
            result = results[0]
            assert hasattr(result, 'job_id')
            assert hasattr(result, 'status')
            assert hasattr(result, 'results')
            assert hasattr(result, 'processing_time_seconds')
    
    def test_pald_diff_calculator_contract(self):
        """Test PALDDiffCalculator contract."""
        calculator = PALDDiffCalculator()
        
        # Sample PALD data
        description_pald = {
            "global_design_level": {"type": "human"},
            "detailed_level": {"age": "adult", "gender": "female"}
        }
        embodiment_pald = {
            "global_design_level": {"type": "human"},
            "detailed_level": {"age": "young", "gender": "female"}
        }
        
        # Test diff calculation
        result = calculator.calculate_diff(description_pald, embodiment_pald)
        
        # Verify contract
        assert isinstance(result.matches, dict)
        assert isinstance(result.hallucinations, dict)
        assert isinstance(result.missing_fields, dict)
        assert isinstance(result.similarity_score, float)
        assert isinstance(result.field_classifications, dict)
        assert isinstance(result.summary, str)
        assert isinstance(result.metadata, dict)
        
        # Verify similarity score is in valid range
        assert 0.0 <= result.similarity_score <= 1.0
        
        # Verify summary is not empty
        assert len(result.summary) > 0
    
    def test_pald_persistence_manager_contract(self):
        """Test PALDPersistenceManager contract."""
        manager = PALDPersistenceManager()
        
        # Test artifact creation
        artifact_id = manager.create_artifact(
            session_id="test_session",
            user_id="test_user",
            description_text="A teacher",
            embodiment_caption="A person",
            pald_light={"global_design_level": {"type": "human"}},
            pald_diff=None,
            processing_metadata={"test": "data"}
        )
        
        # Verify contract
        assert isinstance(artifact_id, str)
        assert len(artifact_id) > 0
        
        # Test artifact retrieval
        artifact = manager.get_artifact(artifact_id)
        assert artifact is not None
        assert artifact.artifact_id == artifact_id
        assert artifact.session_id == "test_session"
        assert isinstance(artifact.created_at, datetime)
        
        # Test statistics
        stats = manager.get_statistics()
        assert isinstance(stats, dict)
        assert "total_artifacts" in stats
        assert "unique_sessions" in stats
        assert "unique_users" in stats
    
    def test_enhanced_pald_service_contract(self):
        """Test EnhancedPALDService contract."""
        from unittest.mock import Mock
        
        service = EnhancedPALDService(Mock())
        mock_manager = Mock()
        service.set_pald_manager(mock_manager)
        
        # Mock response
        from src.logic.pald import PALDProcessingResponse
        mock_response = PALDProcessingResponse(
            pald_light={"global_design_level": {"type": "human"}},
            pald_diff_summary="Test summary",
            defer_notice=None,
            validation_errors=[],
            processing_metadata={}
        )
        mock_manager.process_enhanced_pald.return_value = mock_response
        
        # Test request processing
        request_data = {
            "user_id": str(uuid4()),
            "session_id": "test_session",
            "description_text": "A teacher",
            "embodiment_caption": "A person",
            "defer_bias_scan": True,
            "processing_options": {}
        }
        
        result = service.process_pald_request(request_data)
        
        # Verify contract
        assert isinstance(result, dict)
        assert "pald_light" in result
        assert "pald_diff_summary" in result
        assert "defer_notice" in result
        assert "validation_errors" in result
        assert "processing_metadata" in result
        
        # Verify types
        assert isinstance(result["pald_light"], dict)
        assert isinstance(result["validation_errors"], list)
        assert isinstance(result["processing_metadata"], dict)
    
    def test_pald_processing_request_contract(self):
        """Test PALDProcessingRequest contract."""
        request = PALDProcessingRequest(
            user_id=uuid4(),
            session_id="test_session",
            description_text="A teacher",
            embodiment_caption="A person",
            defer_bias_scan=True,
            processing_options={"test": "option"}
        )
        
        # Verify contract
        assert hasattr(request, 'user_id')
        assert hasattr(request, 'session_id')
        assert hasattr(request, 'description_text')
        assert hasattr(request, 'embodiment_caption')
        assert hasattr(request, 'defer_bias_scan')
        assert hasattr(request, 'processing_options')
        
        # Verify types
        assert isinstance(request.session_id, str)
        assert isinstance(request.description_text, str)
        assert isinstance(request.defer_bias_scan, bool)
        assert isinstance(request.processing_options, dict)