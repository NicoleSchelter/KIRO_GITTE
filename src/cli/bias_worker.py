#!/usr/bin/env python3
"""
CLI entrypoint for bias analysis worker.
Provides configurable batch processing with graceful shutdown.
"""

import asyncio
import signal
import sys
from typing import Optional

import click
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.config import config
from src.services.bias_worker import BiasWorker
from src.services.job_queue import JobQueue
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GracefulShutdown:
    """Handle graceful shutdown signals."""
    
    def __init__(self):
        self.shutdown = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.shutdown = True


@click.command()
@click.option(
    "--batch-size",
    default=10,
    help="Number of jobs to process in each batch",
    type=int
)
@click.option(
    "--poll-interval",
    default=5,
    help="Seconds to wait between polling for new jobs",
    type=int
)
@click.option(
    "--max-concurrent",
    default=3,
    help="Maximum number of concurrent job processors",
    type=int
)
def main(batch_size: int, poll_interval: int, max_concurrent: int):
    """Run bias analysis worker with configurable batch processing."""
    logger.info(f"Starting bias worker (batch_size={batch_size}, poll_interval={poll_interval})")
    
    # Setup graceful shutdown
    shutdown_handler = GracefulShutdown()
    
    # Create async database engine
    engine = create_async_engine(config.database.dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Initialize services
    job_queue = JobQueue(async_session)
    worker = BiasWorker(job_queue, batch_size=batch_size, max_concurrent=max_concurrent)
    
    async def run_worker():
        """Main worker loop."""
        try:
            while not shutdown_handler.shutdown:
                await worker.process_batch()
                await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            logger.info("Worker shutdown complete")
            await engine.dispose()
    
    # Run the worker
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")


if __name__ == "__main__":
    main()
