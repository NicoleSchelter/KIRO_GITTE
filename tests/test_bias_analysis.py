"""
Unit tests for bias analysis engine and job management system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.logic.bias_analysis import (
    BiasAnalysisEngine,
    BiasJobManager,
    BiasType,
    JobStatus,
    BiasResult,
    BiasAnalysisJob,
    BiasJobResult
)


class TestBiasAnalysisEngine:
    """Test bias analysis engine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.engine = BiasAnalysisEngine()
        
        # Sample PALD data for testing
        self.sample_description_pald = {
            "global_design_level": {
                "type": "human"
            },
            "middle_design_level": {
                "role": "teacher",
                "competence": 7,
                "lifelikeness": 6
            },
            "detailed_level": {
                "age": 30,
                "gender": "female",
                "clothing": "professional suit"
            }
        }
        
        self.sample_embodiment_pald = {
            "global_design_level": {
                "type": "human"
            },
            "middle_design_level": {
                "role": "teacher",
                "competence": 5,
                "lifelikeness": 6
            },
            "detailed_level": {
                "age": 25,
                "gender": "female",
                "clothing": "casual dress"
            }
        }
    
    def test_analyze_age_shift_detected(self):
        """Test age shift detection when shift exists."""
        # Create PALDs with different ages
        desc_pald = self.sample_description_pald.copy()
        emb_pald = self.sample_embodiment_pald.copy()
        
        desc_pald["detailed_level"]["age"] = 40
        emb_pald["detailed_level"]["age"] = 25
        
        result = self.engine.analyze_age_shift(desc_pald, emb_pald)
        
        assert isinstance(result, BiasResult)
        assert result.analysis_type == BiasType.AGE_SHIFT
        assert result.findings["age_shift"]["shift_detected"] is True
        assert len(result.indicators) > 0
        assert "Age shift detected" in result.indicators[0]
        assert result.confidence_score > 0.5
    
    def test_analyze_age_shift_no_shift(self):
        """Test age shift analysis when no shift exists."""
        # Create PALDs with same age
        desc_pald = self.sample_description_pald.copy()
        emb_pald = self.sample_embodiment_pald.copy()
        
        desc_pald["detailed_level"]["age"] = 30
        emb_pald["detailed_level"]["age"] = 30
        
        result = self.engine.analyze_age_shift(desc_pald, emb_pald)
        
        assert result.findings["consistent"] is True
        assert result.confidence_score > 0.8
    
    def test_analyze_age_shift_insufficient_data(self):
        """Test age shift analysis with insufficient data."""
        desc_pald = {"detailed_level": {}}  # No age data
        emb_pald = {"detailed_level": {}}
        
        result = self.engine.analyze_age_shift(desc_pald, emb_pald)
        
        assert result.findings["insufficient_data"] is True
        assert "Insufficient age data" in result.indicators[0]
        assert result.confidence_score < 0.2
    
    def test_analyze_gender_conformity(self):
        """Test gender conformity analysis."""
        result = self.engine.analyze_gender_conformity(
            self.sample_description_pald, 
            self.sample_embodiment_pald
        )
        
        assert isinstance(result, BiasResult)
        assert result.analysis_type == BiasType.GENDER_CONFORMITY
        assert "description_gender" in result.findings
        assert "embodiment_gender" in result.findings
        assert "clothing_analysis" in result.findings
        assert result.confidence_score >= 0.0
    
    def test_analyze_ethnicity_consistency(self):
        """Test ethnicity consistency analysis."""
        result = self.engine.analyze_ethnicity_consistency(
            self.sample_description_pald,
            self.sample_embodiment_pald
        )
        
        assert isinstance(result, BiasResult)
        assert result.analysis_type == BiasType.ETHNICITY_CONSISTENCY
        assert "analysis_note" in result.findings
        assert "no ethnic profiling performed" in result.findings["analysis_note"]
        assert result.confidence_score >= 0.0
    
    def test_analyze_occupational_stereotypes(self):
        """Test occupational stereotype analysis."""
        result = self.engine.analyze_occupational_stereotypes(
            self.sample_description_pald,
            self.sample_embodiment_pald
        )
        
        assert isinstance(result, BiasResult)
        assert result.analysis_type == BiasType.OCCUPATIONAL_STEREOTYPES
        assert "role_information" in result.findings
        assert "stereotype_analysis" in result.findings
        assert result.confidence_score >= 0.0
    
    def test_analyze_ambivalent_stereotypes(self):
        """Test ambivalent stereotype analysis."""
        result = self.engine.analyze_ambivalent_stereotypes(
            self.sample_description_pald,
            self.sample_embodiment_pald
        )
        
        assert isinstance(result, BiasResult)
        assert result.analysis_type == BiasType.AMBIVALENT_STEREOTYPES
        assert "competence_markers" in result.findings
        assert "presentation_markers" in result.findings
        assert result.confidence_score >= 0.0
    
    def test_analyze_multiple_stereotyping(self):
        """Test multiple stereotyping analysis."""
        # Create some sample bias results
        bias_results = [
            BiasResult(
                analysis_type=BiasType.AGE_SHIFT,
                findings={"shift_detected": True},
                confidence_score=0.8,
                indicators=["Age shift detected"],
                recommendations=["Review age consistency"]
            ),
            BiasResult(
                analysis_type=BiasType.GENDER_CONFORMITY,
                findings={"stereotypes_found": True},
                confidence_score=0.7,
                indicators=["Gender stereotypes detected"],
                recommendations=["Review gender representation"]
            )
        ]
        
        result = self.engine.analyze_multiple_stereotyping(bias_results)
        
        assert isinstance(result, BiasResult)
        assert result.analysis_type == BiasType.MULTIPLE_STEREOTYPING
        assert "bias_summary" in result.findings
        assert result.findings["bias_summary"]["total_analyses"] == 2
        assert result.confidence_score > 0.0
    
    def test_categorize_age_numeric(self):
        """Test age categorization with numeric values."""
        assert self.engine._categorize_age(8) == "child"
        assert self.engine._categorize_age(16) == "teenager"
        assert self.engine._categorize_age(25) == "young_adult"
        assert self.engine._categorize_age(40) == "adult"
        assert self.engine._categorize_age(70) == "elderly"
    
    def test_categorize_age_string(self):
        """Test age categorization with string values."""
        assert self.engine._categorize_age("child") == "child"
        assert self.engine._categorize_age("young person") == "teenager"
        assert self.engine._categorize_age("adult") == "adult"
        assert self.engine._categorize_age("elderly") == "elderly"
        assert self.engine._categorize_age("unknown") == "unknown"
    
    def test_estimate_numeric_age(self):
        """Test numeric age estimation."""
        assert self.engine._estimate_numeric_age(25) == 25
        assert self.engine._estimate_numeric_age("child") == 8
        assert self.engine._estimate_numeric_age("teenager") == 16
        assert self.engine._estimate_numeric_age("adult") == 40
        assert self.engine._estimate_numeric_age("elderly") == 70
        assert self.engine._estimate_numeric_age("unknown") is None
    
    def test_extract_age_info(self):
        """Test age information extraction."""
        pald_data = {
            "detailed_level": {
                "age": 30
            }
        }
        
        age_info = self.engine._extract_age_info(pald_data)
        
        assert age_info["raw_value"] == 30
        assert age_info["category"] == "adult"
        assert age_info["numeric_estimate"] == 30
    
    def test_extract_gender_info(self):
        """Test gender information extraction."""
        pald_data = {
            "detailed_level": {
                "gender": "female"
            }
        }
        
        gender_info = self.engine._extract_gender_info(pald_data)
        
        assert gender_info["gender"] == "female"
    
    def test_analyze_clothing_conformity(self):
        """Test clothing conformity analysis."""
        desc_pald = {
            "detailed_level": {
                "clothing": "dress and high heels"
            }
        }
        emb_pald = {
            "detailed_level": {
                "clothing": "pink frilly outfit"
            }
        }
        
        analysis = self.engine._analyze_clothing_conformity(desc_pald, emb_pald)
        
        assert analysis["data_available"] is True
        assert analysis["stereotypical_clothing"] is True
        assert "dress" in analysis["patterns_found"]
        assert "pink" in analysis["patterns_found"]
    
    def test_check_sexualization_indicators(self):
        """Test sexualization indicator detection."""
        desc_pald = {
            "detailed_level": {
                "clothing": "revealing tight dress"
            }
        }
        emb_pald = {
            "detailed_level": {
                "clothing": "low-cut top"
            }
        }
        
        check = self.engine._check_sexualization_indicators(desc_pald, emb_pald)
        
        assert check["indicators_found"] is True
        assert "revealing" in check["indicators"]
        assert "tight" in check["indicators"]
    
    def test_extract_role_information(self):
        """Test role information extraction."""
        role_info = self.engine._extract_role_information(
            self.sample_description_pald,
            self.sample_embodiment_pald
        )
        
        assert role_info["description_role"] == "teacher"
        assert role_info["embodiment_role"] == "teacher"
        assert role_info["description_competence"] == 7
        assert role_info["embodiment_competence"] == 5
        assert role_info["data_completeness"] == 1.0
    
    def test_extract_competence_markers(self):
        """Test competence marker extraction."""
        markers = self.engine._extract_competence_markers(
            self.sample_description_pald,
            self.sample_embodiment_pald
        )
        
        assert len(markers) > 0
        assert any("competence: 7" in marker for marker in markers)
        assert any("role: teacher" in marker for marker in markers)
    
    def test_extract_presentation_markers(self):
        """Test presentation marker extraction."""
        markers = self.engine._extract_presentation_markers(
            self.sample_description_pald,
            self.sample_embodiment_pald
        )
        
        assert len(markers) > 0
        assert any("clothing:" in marker for marker in markers)
        assert any("lifelikeness:" in marker for marker in markers)


class TestBiasJobManager:
    """Test bias job manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = BiasJobManager()
        
        self.sample_description_pald = {
            "detailed_level": {"age": 30, "gender": "female"}
        }
        
        self.sample_embodiment_pald = {
            "detailed_level": {"age": 25, "gender": "female"}
        }
    
    def test_create_bias_job(self):
        """Test bias job creation."""
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald
        )
        
        assert job_id is not None
        assert job_id in self.manager.jobs
        
        job = self.manager.jobs[job_id]
        assert job.session_id == "test_session"
        assert job.status == JobStatus.PENDING
        assert job.description_pald == self.sample_description_pald
        assert job.embodiment_pald == self.sample_embodiment_pald
        assert len(job.analysis_types) == len(BiasType)  # All types by default
    
    def test_create_bias_job_with_specific_types(self):
        """Test bias job creation with specific analysis types."""
        analysis_types = [BiasType.AGE_SHIFT, BiasType.GENDER_CONFORMITY]
        
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald,
            analysis_types=analysis_types,
            priority=2
        )
        
        job = self.manager.jobs[job_id]
        assert job.analysis_types == analysis_types
        assert job.priority == 2
    
    def test_process_bias_job_success(self):
        """Test successful bias job processing."""
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald,
            analysis_types=[BiasType.AGE_SHIFT]
        )
        
        result = self.manager.process_bias_job(job_id)
        
        assert isinstance(result, BiasJobResult)
        assert result.job_id == job_id
        assert result.status == JobStatus.COMPLETED
        assert len(result.results) == 1
        assert result.results[0].analysis_type == BiasType.AGE_SHIFT
        assert result.processing_time_seconds > 0
        
        # Check job status was updated
        job = self.manager.jobs[job_id]
        assert job.status == JobStatus.COMPLETED
        assert job.processed_at is not None
        assert len(job.results) == 1
    
    def test_process_bias_job_with_multiple_stereotyping(self):
        """Test bias job processing including multiple stereotyping analysis."""
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald,
            analysis_types=[BiasType.AGE_SHIFT, BiasType.GENDER_CONFORMITY, BiasType.MULTIPLE_STEREOTYPING]
        )
        
        result = self.manager.process_bias_job(job_id)
        
        assert result.status == JobStatus.COMPLETED
        assert len(result.results) == 3
        
        # Multiple stereotyping should be last
        assert result.results[-1].analysis_type == BiasType.MULTIPLE_STEREOTYPING
    
    def test_process_bias_job_not_found(self):
        """Test processing non-existent job."""
        with pytest.raises(ValueError, match="Job .* not found"):
            self.manager.process_bias_job("nonexistent_job")
    
    def test_process_bias_job_failure(self):
        """Test bias job processing failure handling."""
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald,
            analysis_types=[BiasType.AGE_SHIFT]  # Only test one type to ensure mock works
        )
        
        # Mock the analysis methods dictionary to raise an exception
        original_method = self.manager.bias_engine.analysis_methods[BiasType.AGE_SHIFT]
        self.manager.bias_engine.analysis_methods[BiasType.AGE_SHIFT] = lambda desc, emb: (_ for _ in ()).throw(Exception("Test error"))
        
        try:
            result = self.manager.process_bias_job(job_id)
            
            assert result.status == JobStatus.FAILED
            assert result.error_message == "Test error"
            assert len(result.results) == 0
            
            # Check job status was updated
            job = self.manager.jobs[job_id]
            assert job.status == JobStatus.FAILED
            assert job.error_message == "Test error"
        finally:
            # Restore original method
            self.manager.bias_engine.analysis_methods[BiasType.AGE_SHIFT] = original_method
    
    def test_process_bias_queue(self):
        """Test processing bias job queue."""
        # Create multiple jobs
        job_ids = []
        for i in range(3):
            job_id = self.manager.create_bias_job(
                session_id=f"session_{i}",
                description_pald=self.sample_description_pald,
                embodiment_pald=self.sample_embodiment_pald,
                analysis_types=[BiasType.AGE_SHIFT],
                priority=i + 1
            )
            job_ids.append(job_id)
        
        # Process queue with batch size 2
        results = self.manager.process_bias_queue(batch_size=2)
        
        assert len(results) == 2
        
        # Check that higher priority jobs were processed first
        processed_jobs = [self.manager.jobs[r.job_id] for r in results]
        priorities = [job.priority for job in processed_jobs]
        assert priorities == sorted(priorities, reverse=True)  # Higher priority first
        
        # Check remaining job is still pending
        remaining_jobs = [job for job in self.manager.jobs.values() if job.status == JobStatus.PENDING]
        assert len(remaining_jobs) == 1
    
    def test_get_job_status(self):
        """Test getting job status."""
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald
        )
        
        # Initially pending
        assert self.manager.get_job_status(job_id) == JobStatus.PENDING
        
        # Process job
        self.manager.process_bias_job(job_id)
        
        # Should be completed
        assert self.manager.get_job_status(job_id) == JobStatus.COMPLETED
    
    def test_get_job_status_not_found(self):
        """Test getting status of non-existent job."""
        with pytest.raises(ValueError, match="Job .* not found"):
            self.manager.get_job_status("nonexistent_job")
    
    def test_get_job_results(self):
        """Test getting job results."""
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald,
            analysis_types=[BiasType.AGE_SHIFT]
        )
        
        # Process job
        self.manager.process_bias_job(job_id)
        
        # Get results
        results = self.manager.get_job_results(job_id)
        
        assert len(results) == 1
        assert results[0].analysis_type == BiasType.AGE_SHIFT
    
    def test_get_job_results_not_completed(self):
        """Test getting results of non-completed job."""
        job_id = self.manager.create_bias_job(
            session_id="test_session",
            description_pald=self.sample_description_pald,
            embodiment_pald=self.sample_embodiment_pald
        )
        
        # Job is still pending
        with pytest.raises(ValueError, match="Job .* is not completed"):
            self.manager.get_job_results(job_id)
    
    def test_get_pending_job_count(self):
        """Test getting pending job count."""
        assert self.manager.get_pending_job_count() == 0
        
        # Create some jobs
        for i in range(3):
            self.manager.create_bias_job(
                session_id=f"session_{i}",
                description_pald=self.sample_description_pald,
                embodiment_pald=self.sample_embodiment_pald
            )
        
        assert self.manager.get_pending_job_count() == 3
        
        # Process one job
        job_id = list(self.manager.jobs.keys())[0]
        self.manager.process_bias_job(job_id)
        
        assert self.manager.get_pending_job_count() == 2
    
    def test_clear_completed_jobs(self):
        """Test clearing old completed jobs."""
        # Create and process some jobs
        job_ids = []
        for i in range(3):
            job_id = self.manager.create_bias_job(
                session_id=f"session_{i}",
                description_pald=self.sample_description_pald,
                embodiment_pald=self.sample_embodiment_pald,
                analysis_types=[BiasType.AGE_SHIFT]
            )
            job_ids.append(job_id)
            self.manager.process_bias_job(job_id)
        
        # Manually set processed_at to old time for some jobs
        old_time = datetime.now() - timedelta(hours=25)
        for job_id in job_ids[:2]:
            self.manager.jobs[job_id].processed_at = old_time
        
        # Clear old jobs
        cleared_count = self.manager.clear_completed_jobs(older_than_hours=24)
        
        assert cleared_count == 2
        assert len(self.manager.jobs) == 1
        assert job_ids[2] in self.manager.jobs  # Recent job should remain


if __name__ == "__main__":
    pytest.main([__file__])