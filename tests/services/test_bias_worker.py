"""
Integration tests for bias worker: job lifecycle, retry logic, DLQ handling, status transitions.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.data.models import BiasAnalysisJob, BiasAnalysisResult, BiasAnalysisJobStatus
from src.services.bias_worker import BiasWorker
from src.services.job_queue import JobQueue


@pytest.fixture
async def async_session():
    """Create async database session for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    
    # Create tables (simplified for testing)
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: None)  # Would create tables in real implementation
    
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    yield async_session_factory
    
    await engine.dispose()


@pytest.fixture
def job_queue(async_session):
    """Create job queue instance."""
    return JobQueue(async_session)


@pytest.fixture
def bias_worker(job_queue):
    """Create bias worker instance."""
    return BiasWorker(job_queue, batch_size=5, max_concurrent=2)


@pytest.fixture
def sample_job():
    """Create a sample bias analysis job."""
    return BiasAnalysisJob(
        id=uuid4(),
        session_id="test-session-123",
        pald_data={"agent_description": "A helpful teacher with stereotypical views"},
        analysis_types=["age_shift", "gender_conformity"],
        priority=5,
        status=BiasAnalysisJobStatus.PENDING,
        retry_count=0,
        max_retries=3,
        scheduled_at=datetime.utcnow()
    )


class TestBiasWorkerJobLifecycle:
    """Test complete job lifecycle processing."""
    
    @pytest.mark.asyncio
    async def test_successful_job_processing(self, bias_worker, sample_job):
        """Test successful processing of a bias analysis job."""
        # Mock job queue methods
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=[sample_job])
        bias_worker.job_queue.lock_job = AsyncMock(return_value=True)
        bias_worker.job_queue.update_job_status = AsyncMock()
        bias_worker.job_queue.store_results = AsyncMock()
        bias_worker.job_queue.release_job = AsyncMock()
        
        # Process batch
        processed_count = await bias_worker.process_batch()
        
        # Verify job was processed
        assert processed_count == 1
        
        # Verify status updates
        # Robust gegen Microseconds und Mock-Matching:
        calls = bias_worker.job_queue.update_job_status.call_args_list

        # RUNNING prüfen
        running_calls = [
            c for c in calls
            if len(c.args) >= 2
            and c.args[0] == sample_job.id
            and c.args[1] == BiasAnalysisJobStatus.RUNNING
        ]
        assert running_calls, "Expected at least one RUNNING status update"
        _, run_kwargs = running_calls[0]
        assert "started_at" in run_kwargs, "RUNNING call must include started_at"
        assert isinstance(run_kwargs["started_at"], datetime)
        assert abs(run_kwargs["started_at"] - datetime.utcnow()) <= timedelta(seconds=5)

        # COMPLETED prüfen
        completed_calls = [
            c for c in calls
            if len(c.args) >= 2
            and c.args[0] == sample_job.id
            and c.args[1] == BiasAnalysisJobStatus.COMPLETED
        ]
        assert completed_calls, "Expected at least one COMPLETED status update"
        _, comp_kwargs = completed_calls[0]
        assert "completed_at" in comp_kwargs, "COMPLETED call must include completed_at"
        assert isinstance(comp_kwargs["completed_at"], datetime)
        assert abs(comp_kwargs["completed_at"] - datetime.utcnow()) <= timedelta(seconds=5)
        
        # Verify results were stored
        bias_worker.job_queue.store_results.assert_called_once()
        
        # Verify job was released
        bias_worker.job_queue.release_job.assert_called_once_with(sample_job.id)
    
    @pytest.mark.asyncio
    async def test_job_already_locked(self, bias_worker, sample_job):
        """Test handling when job is already locked by another worker."""
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=[sample_job])
        bias_worker.job_queue.lock_job = AsyncMock(return_value=False)  # Already locked
        bias_worker.job_queue.release_job = AsyncMock()
        
        processed_count = await bias_worker.process_batch()
        
        # Job should not be processed
        assert processed_count == 0
        bias_worker.job_queue.release_job.assert_called_once_with(sample_job.id)
    
    @pytest.mark.asyncio
    async def test_empty_job_queue(self, bias_worker):
        """Test processing when no jobs are available."""
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=[])
        
        processed_count = await bias_worker.process_batch()
        
        assert processed_count == 0


class TestBiasWorkerRetryLogic:
    """Test retry logic and exponential backoff."""
    
    @pytest.mark.asyncio
    async def test_job_retry_on_failure(self, bias_worker, sample_job):
        """Test job is retried on failure with exponential backoff."""
        # Setup job with retry capacity
        sample_job.retry_count = 1
        sample_job.max_retries = 3
        
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=[sample_job])
        bias_worker.job_queue.lock_job = AsyncMock(return_value=True)
        bias_worker.job_queue.update_job_status = AsyncMock()
        bias_worker.job_queue.schedule_retry = AsyncMock()
        bias_worker.job_queue.release_job = AsyncMock()
        
        # Mock analysis to fail
        with patch.object(bias_worker, '_analyze_bias', side_effect=Exception("Analysis failed")):
            processed_count = await bias_worker.process_batch()
        
        # Job should not be counted as processed due to failure
        assert processed_count == 0
        
        # Verify retry was scheduled
        bias_worker.job_queue.schedule_retry.assert_called_once()
        call_args = bias_worker.job_queue.schedule_retry.call_args
        
        assert call_args[0][0] == sample_job.id  # job_id
        assert isinstance(call_args[0][1], datetime)  # scheduled_at
        assert "Analysis failed" in call_args[0][2]  # error_message
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self, bias_worker, sample_job):
        """Test exponential backoff delay calculation."""
        sample_job.retry_count = 2  # Third attempt
        sample_job.max_retries = 3
        
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=[sample_job])
        bias_worker.job_queue.lock_job = AsyncMock(return_value=True)
        bias_worker.job_queue.update_job_status = AsyncMock()
        bias_worker.job_queue.schedule_retry = AsyncMock()
        bias_worker.job_queue.release_job = AsyncMock()
        
        with patch.object(bias_worker, '_analyze_bias', side_effect=Exception("Analysis failed")):
            await bias_worker.process_batch()
        
        # Verify exponential backoff (2^2 * 10 = 40 seconds)
        call_args = bias_worker.job_queue.schedule_retry.call_args
        scheduled_at = call_args[0][1]
        expected_delay = timedelta(seconds=40)
        actual_delay = scheduled_at - datetime.utcnow()
        
        assert abs(actual_delay - expected_delay) < timedelta(seconds=5)


class TestBiasWorkerDLQHandling:
    """Test Dead Letter Queue handling."""
    
    @pytest.mark.asyncio
    async def test_move_to_dlq_after_max_retries(self, bias_worker, sample_job):
        """Test job is moved to DLQ after exceeding max retries."""
        # Setup job at max retries
        sample_job.retry_count = 3
        sample_job.max_retries = 3
        
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=[sample_job])
        bias_worker.job_queue.lock_job = AsyncMock(return_value=True)
        bias_worker.job_queue.update_job_status = AsyncMock()
        bias_worker.job_queue.move_to_dlq = AsyncMock()
        bias_worker.job_queue.release_job = AsyncMock()
        
        with patch.object(bias_worker, '_analyze_bias', side_effect=Exception("Final failure")):
            processed_count = await bias_worker.process_batch()
        
        assert processed_count == 0
        
        # Verify job was moved to DLQ
        bias_worker.job_queue.move_to_dlq.assert_called_once_with(
            sample_job.id,
            "Final failure"
        )


class TestBiasWorkerStatusTransitions:
    """Test job status transitions during processing."""
    
    @pytest.mark.asyncio
    async def test_status_transition_sequence(self, bias_worker, sample_job):
        """Test correct sequence of status transitions."""
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=[sample_job])
        bias_worker.job_queue.lock_job = AsyncMock(return_value=True)
        bias_worker.job_queue.update_job_status = AsyncMock()
        bias_worker.job_queue.store_results = AsyncMock()
        bias_worker.job_queue.release_job = AsyncMock()
        
        await bias_worker.process_batch()
        
        # Verify status transition calls
        calls = bias_worker.job_queue.update_job_status.call_args_list
        
        # First call: PENDING -> RUNNING
        assert calls[0][0][1] == BiasAnalysisJobStatus.RUNNING
        assert calls[0][1]['started_at'] is not None
        
        # Second call: RUNNING -> COMPLETED
        assert calls[1][0][1] == BiasAnalysisJobStatus.COMPLETED
        assert calls[1][1]['completed_at'] is not None


class TestBiasWorkerConcurrency:
    """Test concurrent job processing."""
    
    @pytest.mark.asyncio
    async def test_concurrent_job_processing(self, bias_worker):
        """Test multiple jobs are processed concurrently."""
        jobs = [
            BiasAnalysisJob(
                id=uuid4(),
                session_id=f"session-{i}",
                pald_data={"test": f"data-{i}"},
                analysis_types=["age_shift"],
                status=BiasAnalysisJobStatus.PENDING,
                scheduled_at=datetime.utcnow()
            )
            for i in range(3)
        ]
        
        bias_worker.job_queue.fetch_jobs = AsyncMock(return_value=jobs)
        bias_worker.job_queue.lock_job = AsyncMock(return_value=True)
        bias_worker.job_queue.update_job_status = AsyncMock()
        bias_worker.job_queue.store_results = AsyncMock()
        bias_worker.job_queue.release_job = AsyncMock()
        
        # Add delay to analysis to test concurrency
        async def slow_analysis(job):
            await asyncio.sleep(0.1)
            return []
        
        with patch.object(bias_worker, '_analyze_bias', side_effect=slow_analysis):
            start_time = datetime.utcnow()
            processed_count = await bias_worker.process_batch()
            end_time = datetime.utcnow()
        
        # All jobs should be processed
        assert processed_count == 3
        
        # Should take less time than sequential processing (3 * 0.1 = 0.3s)
        processing_time = (end_time - start_time).total_seconds()
        assert processing_time < 0.25  # Allow for some overhead
