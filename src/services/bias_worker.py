"""
Bias analysis worker with retry logic, exponential backoff, and DLQ support.
Processes BiasAnalysisJob instances with structured logging and status tracking.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from config.config import config
from src.data.models import BiasAnalysisJob, BiasAnalysisResult, BiasAnalysisJobStatus
from src.services.job_queue import JobQueue
from src.utils.logging import get_logger

logger = get_logger(__name__)


class BiasWorker:
    """
    Worker for processing bias analysis jobs with retry and DLQ support.
    """

    def __init__(
        self,
        job_queue: JobQueue,
        batch_size: Optional[int] = None,
        max_concurrent: int = 3,
    ):
        self.job_queue = job_queue
        self.batch_size = batch_size or config.pald_enhancement.bias_job_priority_default
        self.max_concurrent = max_concurrent
        self.config = config.pald_enhancement

        logger.info(
            "BiasWorker initialized",
            extra={
                "batch_size": self.batch_size,
                "max_concurrent": self.max_concurrent,
                "bias_analysis_enabled": self.config.bias_analysis_enabled,
            },
        )

    async def process_batch(self) -> int:
        """
        Process a batch of pending bias analysis jobs.

        Returns:
            Number of jobs processed
        """
        if not self.config.bias_analysis_enabled:
            logger.debug("Bias analysis disabled, skipping batch")
            return 0

        # Fetch jobs from queue
        jobs = await self.job_queue.fetch_jobs(
            status=BiasAnalysisJobStatus.PENDING, limit=self.batch_size
        )

        if not jobs:
            logger.debug("No pending jobs found")
            return 0

        logger.info(f"Processing batch of {len(jobs)} jobs")

        # Process jobs concurrently with a semaphore
        semaphore = asyncio.Semaphore(self.max_concurrent)
        tasks = [self._process_job_with_semaphore(job, semaphore) for job in jobs]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful processes
        processed_count = sum(1 for r in results if r is True)

        logger.info(
            "Batch processing complete",
            extra={
                "total_jobs": len(jobs),
                "processed": processed_count,
                "failed": len(jobs) - processed_count,
            },
        )

        return processed_count

    async def _process_job_with_semaphore(
        self, job: BiasAnalysisJob, semaphore: asyncio.Semaphore
    ) -> bool:
        """Process a single job with concurrency control."""
        async with semaphore:
            return await self._process_job(job)

    async def _process_job(self, job: BiasAnalysisJob) -> bool:
        """
        Process a single bias analysis job with retry logic.

        Returns:
            True if job was processed successfully, False otherwise
        """
        job_id = str(job.id)

        try:
            # 1) Lock the job
            locked = await self.job_queue.lock_job(job.id)
            if not locked:
                logger.debug("Job already locked by another worker", extra={"job_id": job_id})
                return False

            logger.info(
                "Processing bias analysis job",
                extra={
                    "job_id": job_id,
                    "session_id": job.session_id,
                    "analysis_types": job.analysis_types,
                    "retry_count": job.retry_count,
                },
            )

            # 2) Mark RUNNING with started_at (test expects this)
            started_at = datetime.utcnow()
            await self.job_queue.update_job_status(
                job.id, BiasAnalysisJobStatus.RUNNING, started_at=started_at
            )
            logger.debug(
                "Job marked RUNNING",
                extra={"job_id": job_id, "started_at": started_at.isoformat()},
            )

            # 3) Perform bias analysis
            results = await self._analyze_bias(job)

            # 4) Store results
            await self._store_results(job, results)

            # 5) Mark COMPLETED with completed_at
            completed_at = datetime.utcnow()
            await self.job_queue.update_job_status(
                job.id, BiasAnalysisJobStatus.COMPLETED, completed_at=completed_at
            )

            logger.info(
                "Job completed successfully",
                extra={
                    "job_id": job_id,
                    "results_count": len(results),
                    "bias_detected": any(r.bias_detected for r in results),
                },
            )

            return True

        except Exception as e:
            logger.error(
                "Job processing failed",
                extra={"job_id": job_id, "error": str(e), "retry_count": job.retry_count},
                exc_info=True,
            )
            # Retry/DLQ handling
            await self._handle_job_failure(job, str(e))
            return False

        finally:
            # 6) Always release the lock
            await self.job_queue.release_job(job.id)

    async def _analyze_bias(self, job: BiasAnalysisJob) -> List[BiasAnalysisResult]:
        """
        Perform bias analysis on PALD data.

        This is a simplified implementation - replace with real detectors.
        """
        results: List[BiasAnalysisResult] = []

        for analysis_type in job.analysis_types:
            # Simulate analysis workload
            await asyncio.sleep(0.1)

            # Very simple mock: detect keyword "stereotype"
            bias_detected = "stereotype" in str(job.pald_data).lower()
            confidence = 0.8 if bias_detected else 0.2

            results.append(
                BiasAnalysisResult(
                    job_id=job.id,
                    session_id=job.session_id,
                    analysis_type=analysis_type,
                    bias_detected=bias_detected,
                    confidence_score=confidence,
                    bias_indicators={"mock_indicator": True} if bias_detected else None,
                    analysis_details={"processed_at": datetime.utcnow().isoformat()},
                )
            )

        return results

    async def _store_results(self, job: BiasAnalysisJob, results: List[BiasAnalysisResult]) -> None:
        """Store bias analysis results."""
        await self.job_queue.store_results(job.id, results)

    async def _handle_job_failure(self, job: BiasAnalysisJob, error_message: str) -> None:
        """Handle job failure with retry logic and DLQ."""
        if job.retry_count < job.max_retries:
            # Exponential backoff (cap at 5 minutes)
            delay_seconds = min(300, (2 ** job.retry_count) * 10)
            scheduled_at = datetime.utcnow() + timedelta(seconds=delay_seconds)

            await self.job_queue.schedule_retry(job.id, scheduled_at, error_message)

            logger.info(
                "Job scheduled for retry",
                extra={
                    "job_id": str(job.id),
                    "retry_count": job.retry_count + 1,
                    "delay_seconds": delay_seconds,
                    "scheduled_at": scheduled_at.isoformat(),
                },
            )
        else:
            await self.job_queue.move_to_dlq(job.id, error_message)
            logger.error(
                "Job moved to DLQ after max retries",
                extra={"job_id": str(job.id), "max_retries": job.max_retries, "final_error": error_message},
            )
