"""
Simple job queue abstraction for bias analysis jobs.
Provides methods for fetching, locking, and releasing jobs.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from src.data.models import BiasAnalysisJob, BiasAnalysisResult, BiasAnalysisJobStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)


class JobQueue:
    """
    Simple job queue for managing bias analysis jobs.
    """
    
    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory
    
    async def fetch_jobs(
        self,
        status: BiasAnalysisJobStatus,
        limit: int = 10
    ) -> List[BiasAnalysisJob]:
        """
        Fetch jobs with the specified status, ordered by priority and scheduled time.
        """
        async with self.session_factory() as session:
            stmt = (
                select(BiasAnalysisJob)
                .where(BiasAnalysisJob.status == status.value)
                .where(BiasAnalysisJob.scheduled_at <= datetime.utcnow())
                .order_by(BiasAnalysisJob.priority.asc(), BiasAnalysisJob.scheduled_at.asc())
                .limit(limit)
            )
            
            result = await session.execute(stmt)
            jobs = result.scalars().all()
            
            logger.debug(
                f"Fetched {len(jobs)} jobs with status {status.value}",
                extra={"status": status.value, "limit": limit, "count": len(jobs)}
            )
            
            return list(jobs)
    
    async def lock_job(self, job_id: UUID) -> bool:
        """
        Attempt to lock a job for processing.
        
        Returns:
            True if job was successfully locked, False if already locked
        """
        async with self.session_factory() as session:
            # Try to update job status from PENDING to RUNNING
            stmt = (
                update(BiasAnalysisJob)
                .where(BiasAnalysisJob.id == job_id)
                .where(BiasAnalysisJob.status == BiasAnalysisJobStatus.PENDING.value)
                .values(
                    status=BiasAnalysisJobStatus.RUNNING.value,
                    started_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            
            result = await session.execute(stmt)
            await session.commit()
            
            locked = result.rowcount > 0
            
            logger.debug(
                f"Job lock attempt",
                extra={"job_id": str(job_id), "locked": locked}
            )
            
            return locked
    
    async def release_job(self, job_id: UUID):
        """Release a job lock (no-op in this simple implementation)."""
        logger.debug(f"Released job {job_id}")
    
    async def update_job_status(
        self,
        job_id: UUID,
        status: BiasAnalysisJobStatus,
        error_message: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        """Update job status and timestamps."""
        async with self.session_factory() as session:
            update_values = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }
            
            if error_message is not None:
                update_values["error_message"] = error_message
            if started_at is not None:
                update_values["started_at"] = started_at
            if completed_at is not None:
                update_values["completed_at"] = completed_at
            
            stmt = (
                update(BiasAnalysisJob)
                .where(BiasAnalysisJob.id == job_id)
                .values(**update_values)
            )
            
            await session.execute(stmt)
            await session.commit()
            
            logger.debug(
                f"Updated job status",
                extra={
                    "job_id": str(job_id),
                    "status": status.value,
                    "error_message": error_message
                }
            )
    
    async def store_results(self, job_id: UUID, results: List[BiasAnalysisResult]):
        """Store bias analysis results."""
        async with self.session_factory() as session:
            session.add_all(results)
            await session.commit()
            
            logger.debug(
                f"Stored {len(results)} results for job {job_id}",
                extra={"job_id": str(job_id), "results_count": len(results)}
            )
    
    async def schedule_retry(self, job_id: UUID, scheduled_at: datetime, error_message: str):
        """Schedule a job for retry with exponential backoff."""
        async with self.session_factory() as session:
            stmt = (
                update(BiasAnalysisJob)
                .where(BiasAnalysisJob.id == job_id)
                .values(
                    status=BiasAnalysisJobStatus.RETRY.value,
                    retry_count=BiasAnalysisJob.retry_count + 1,
                    scheduled_at=scheduled_at,
                    error_message=error_message,
                    updated_at=datetime.utcnow()
                )
            )
            
            await session.execute(stmt)
            await session.commit()
    
    async def move_to_dlq(self, job_id: UUID, error_message: str):
        """Move a job to the dead letter queue."""
        await self.update_job_status(
            job_id,
            BiasAnalysisJobStatus.DLQ,
            error_message=error_message,
            completed_at=datetime.utcnow()
        )
