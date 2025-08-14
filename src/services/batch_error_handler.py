"""
Batch Error Handler Service for GITTE UX enhancements.
Provides specialized error handling for batch image processing and bulk operations.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.exceptions import (
    BatchProcessingError,
    ImageProcessingError,
    RetryExhaustedError,
)
from src.utils.ux_error_handler import RetryConfig, ux_error_handler

logger = logging.getLogger(__name__)


@dataclass
class BatchProcessingConfig:
    """Configuration for batch processing operations."""
    
    max_concurrent_operations: int = 3
    max_retries_per_item: int = 2
    failure_threshold_percentage: float = 50.0  # Fail batch if >50% items fail
    timeout_per_item_seconds: int = 30
    enable_partial_success: bool = True
    collect_detailed_errors: bool = True


@dataclass
class BatchResult:
    """Result of batch processing operation."""
    
    total_items: int
    successful_items: int
    failed_items: int
    success_rate: float
    processing_time: float
    successful_results: List[Any]
    failed_results: List[Dict[str, Any]]
    partial_success: bool
    error_summary: Dict[str, int]


class BatchErrorHandler:
    """Handles errors and retries for batch processing operations."""
    
    def __init__(self, config: BatchProcessingConfig = None):
        """
        Initialize batch error handler.
        
        Args:
            config: Configuration for batch processing
        """
        self.config = config or BatchProcessingConfig()
        self.processing_stats = {
            "total_batches": 0,
            "successful_batches": 0,
            "failed_batches": 0,
            "partial_success_batches": 0,
            "total_items_processed": 0,
            "total_items_failed": 0,
        }
    
    def process_batch(
        self,
        items: List[Any],
        processing_func: Callable,
        item_name: str = "item",
        **processing_kwargs
    ) -> BatchResult:
        """
        Process a batch of items with comprehensive error handling.
        
        Args:
            items: List of items to process
            processing_func: Function to process each item
            item_name: Name for items (for logging/error messages)
            **processing_kwargs: Additional kwargs for processing function
            
        Returns:
            BatchResult with detailed processing results
        """
        start_time = time.time()
        self.processing_stats["total_batches"] += 1
        self.processing_stats["total_items_processed"] += len(items)
        
        logger.info(f"Starting batch processing of {len(items)} {item_name}s")
        
        successful_results = []
        failed_results = []
        error_counts = {}
        
        # Process items with controlled concurrency
        with ThreadPoolExecutor(max_workers=self.config.max_concurrent_operations) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(
                    self._process_single_item_with_retry,
                    item,
                    processing_func,
                    item_name,
                    **processing_kwargs
                ): item
                for item in items
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                
                try:
                    result = future.result(timeout=self.config.timeout_per_item_seconds)
                    
                    if result["success"]:
                        successful_results.append(result["data"])
                    else:
                        failed_results.append({
                            "item": item,
                            "error": result["error"],
                            "attempts": result["attempts"],
                            "error_type": result["error_type"]
                        })
                        
                        # Count error types
                        error_type = result["error_type"]
                        error_counts[error_type] = error_counts.get(error_type, 0) + 1
                        
                except Exception as e:
                    logger.error(f"Unexpected error processing {item_name}: {e}")
                    failed_results.append({
                        "item": item,
                        "error": str(e),
                        "attempts": 1,
                        "error_type": "unexpected_error"
                    })
                    error_counts["unexpected_error"] = error_counts.get("unexpected_error", 0) + 1
        
        # Calculate results
        total_items = len(items)
        successful_items = len(successful_results)
        failed_items = len(failed_results)
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        processing_time = time.time() - start_time
        
        # Update statistics
        self.processing_stats["total_items_failed"] += failed_items
        
        # Determine batch status
        partial_success = (
            successful_items > 0 and 
            failed_items > 0 and 
            self.config.enable_partial_success
        )
        
        batch_failed = success_rate < (100 - self.config.failure_threshold_percentage)
        
        if batch_failed and not partial_success:
            self.processing_stats["failed_batches"] += 1
            logger.error(
                f"Batch processing failed: {success_rate:.1f}% success rate "
                f"(threshold: {100 - self.config.failure_threshold_percentage:.1f}%)"
            )
        elif partial_success:
            self.processing_stats["partial_success_batches"] += 1
            logger.warning(
                f"Batch processing partially successful: {successful_items}/{total_items} items succeeded"
            )
        else:
            self.processing_stats["successful_batches"] += 1
            logger.info(f"Batch processing completed successfully: {successful_items}/{total_items} items")
        
        result = BatchResult(
            total_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            success_rate=success_rate,
            processing_time=processing_time,
            successful_results=successful_results,
            failed_results=failed_results,
            partial_success=partial_success,
            error_summary=error_counts
        )
        
        # Log detailed error summary if enabled
        if self.config.collect_detailed_errors and failed_results:
            self._log_error_summary(result, item_name)
        
        # Raise exception if batch completely failed
        if batch_failed and not partial_success:
            raise BatchProcessingError(
                f"Batch processing failed with {success_rate:.1f}% success rate",
                failed_images=[str(fr["item"]) for fr in failed_results],
                total_images=total_items
            )
        
        return result
    
    def _process_single_item_with_retry(
        self,
        item: Any,
        processing_func: Callable,
        item_name: str,
        **processing_kwargs
    ) -> Dict[str, Any]:
        """
        Process a single item with retry logic.
        
        Args:
            item: Item to process
            processing_func: Processing function
            item_name: Name for the item type
            **processing_kwargs: Additional processing arguments
            
        Returns:
            Dict with processing result and metadata
        """
        last_error = None
        error_type = "unknown"
        
        for attempt in range(self.config.max_retries_per_item + 1):
            try:
                result = processing_func(item, **processing_kwargs)
                
                return {
                    "success": True,
                    "data": result,
                    "attempts": attempt + 1,
                    "error": None,
                    "error_type": None
                }
                
            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)
                
                if attempt < self.config.max_retries_per_item:
                    # Calculate retry delay
                    delay = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries_per_item + 1} failed for {item_name} {item}: {e}. "
                        f"Retrying in {delay}s"
                    )
                    
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.config.max_retries_per_item + 1} attempts failed for {item_name} {item}: {e}"
                    )
        
        return {
            "success": False,
            "data": None,
            "attempts": self.config.max_retries_per_item + 1,
            "error": str(last_error),
            "error_type": error_type
        }
    
    def _classify_error(self, error: Exception) -> str:
        """
        Classify error type for statistics and handling.
        
        Args:
            error: Exception to classify
            
        Returns:
            String classification of error type
        """
        if isinstance(error, ImageProcessingError):
            return error.__class__.__name__
        elif "timeout" in str(error).lower():
            return "timeout_error"
        elif "connection" in str(error).lower():
            return "connection_error"
        elif "memory" in str(error).lower() or "resource" in str(error).lower():
            return "resource_error"
        elif "permission" in str(error).lower() or "access" in str(error).lower():
            return "permission_error"
        else:
            return "unknown_error"
    
    def _log_error_summary(self, result: BatchResult, item_name: str):
        """
        Log detailed error summary for failed batch processing.
        
        Args:
            result: Batch processing result
            item_name: Name of items being processed
        """
        logger.error(f"Batch processing error summary for {item_name}s:")
        logger.error(f"  Total items: {result.total_items}")
        logger.error(f"  Failed items: {result.failed_items}")
        logger.error(f"  Success rate: {result.success_rate:.1f}%")
        logger.error(f"  Processing time: {result.processing_time:.2f}s")
        
        if result.error_summary:
            logger.error("  Error breakdown:")
            for error_type, count in result.error_summary.items():
                percentage = (count / result.failed_items) * 100
                logger.error(f"    {error_type}: {count} ({percentage:.1f}%)")
        
        # Log first few failed items for debugging
        if result.failed_results:
            logger.error("  Sample failed items:")
            for i, failed_result in enumerate(result.failed_results[:3]):
                logger.error(f"    {i+1}. {failed_result['item']}: {failed_result['error']}")
            
            if len(result.failed_results) > 3:
                logger.error(f"    ... and {len(result.failed_results) - 3} more")
    
    async def process_batch_async(
        self,
        items: List[Any],
        processing_func: Callable,
        item_name: str = "item",
        **processing_kwargs
    ) -> BatchResult:
        """
        Process a batch of items asynchronously with error handling.
        
        Args:
            items: List of items to process
            processing_func: Async function to process each item
            item_name: Name for items (for logging/error messages)
            **processing_kwargs: Additional kwargs for processing function
            
        Returns:
            BatchResult with detailed processing results
        """
        start_time = time.time()
        self.processing_stats["total_batches"] += 1
        self.processing_stats["total_items_processed"] += len(items)
        
        logger.info(f"Starting async batch processing of {len(items)} {item_name}s")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.config.max_concurrent_operations)
        
        async def process_with_semaphore(item):
            async with semaphore:
                return await self._process_single_item_with_retry_async(
                    item, processing_func, item_name, **processing_kwargs
                )
        
        # Process all items concurrently
        tasks = [process_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successful and failed results
        successful_results = []
        failed_results = []
        error_counts = {}
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Task raised an exception
                failed_results.append({
                    "item": items[i],
                    "error": str(result),
                    "attempts": 1,
                    "error_type": self._classify_error(result)
                })
                error_type = self._classify_error(result)
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            elif result["success"]:
                successful_results.append(result["data"])
            else:
                failed_results.append({
                    "item": items[i],
                    "error": result["error"],
                    "attempts": result["attempts"],
                    "error_type": result["error_type"]
                })
                error_type = result["error_type"]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Calculate and return results (same logic as sync version)
        total_items = len(items)
        successful_items = len(successful_results)
        failed_items = len(failed_results)
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        processing_time = time.time() - start_time
        
        self.processing_stats["total_items_failed"] += failed_items
        
        partial_success = (
            successful_items > 0 and 
            failed_items > 0 and 
            self.config.enable_partial_success
        )
        
        batch_failed = success_rate < (100 - self.config.failure_threshold_percentage)
        
        if batch_failed and not partial_success:
            self.processing_stats["failed_batches"] += 1
        elif partial_success:
            self.processing_stats["partial_success_batches"] += 1
        else:
            self.processing_stats["successful_batches"] += 1
        
        result = BatchResult(
            total_items=total_items,
            successful_items=successful_items,
            failed_items=failed_items,
            success_rate=success_rate,
            processing_time=processing_time,
            successful_results=successful_results,
            failed_results=failed_results,
            partial_success=partial_success,
            error_summary=error_counts
        )
        
        if self.config.collect_detailed_errors and failed_results:
            self._log_error_summary(result, item_name)
        
        if batch_failed and not partial_success:
            raise BatchProcessingError(
                f"Async batch processing failed with {success_rate:.1f}% success rate",
                failed_images=[str(fr["item"]) for fr in failed_results],
                total_images=total_items
            )
        
        return result
    
    async def _process_single_item_with_retry_async(
        self,
        item: Any,
        processing_func: Callable,
        item_name: str,
        **processing_kwargs
    ) -> Dict[str, Any]:
        """
        Process a single item asynchronously with retry logic.
        
        Args:
            item: Item to process
            processing_func: Async processing function
            item_name: Name for the item type
            **processing_kwargs: Additional processing arguments
            
        Returns:
            Dict with processing result and metadata
        """
        last_error = None
        error_type = "unknown"
        
        for attempt in range(self.config.max_retries_per_item + 1):
            try:
                result = await processing_func(item, **processing_kwargs)
                
                return {
                    "success": True,
                    "data": result,
                    "attempts": attempt + 1,
                    "error": None,
                    "error_type": None
                }
                
            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)
                
                if attempt < self.config.max_retries_per_item:
                    delay = min(2 ** attempt, 10)
                    
                    logger.warning(
                        f"Async attempt {attempt + 1}/{self.config.max_retries_per_item + 1} failed for {item_name} {item}: {e}. "
                        f"Retrying in {delay}s"
                    )
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All async attempts failed for {item_name} {item}: {e}"
                    )
        
        return {
            "success": False,
            "data": None,
            "attempts": self.config.max_retries_per_item + 1,
            "error": str(last_error),
            "error_type": error_type
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        total_batches = self.processing_stats["total_batches"]
        
        return {
            **self.processing_stats,
            "batch_success_rate": (
                (self.processing_stats["successful_batches"] / total_batches) * 100
                if total_batches > 0 else 0
            ),
            "item_success_rate": (
                ((self.processing_stats["total_items_processed"] - self.processing_stats["total_items_failed"]) 
                 / self.processing_stats["total_items_processed"]) * 100
                if self.processing_stats["total_items_processed"] > 0 else 0
            ),
        }
    
    def reset_stats(self):
        """Reset processing statistics."""
        for key in self.processing_stats:
            self.processing_stats[key] = 0


# Global batch error handler instance
batch_error_handler = BatchErrorHandler()


def process_batch_with_error_handling(
    items: List[Any],
    processing_func: Callable,
    item_name: str = "item",
    config: BatchProcessingConfig = None,
    **processing_kwargs
) -> BatchResult:
    """
    Convenience function to process a batch with error handling.
    
    Args:
        items: List of items to process
        processing_func: Function to process each item
        item_name: Name for items (for logging/error messages)
        config: Optional batch processing configuration
        **processing_kwargs: Additional kwargs for processing function
        
    Returns:
        BatchResult with detailed processing results
    """
    handler = BatchErrorHandler(config) if config else batch_error_handler
    return handler.process_batch(items, processing_func, item_name, **processing_kwargs)


async def process_batch_async_with_error_handling(
    items: List[Any],
    processing_func: Callable,
    item_name: str = "item",
    config: BatchProcessingConfig = None,
    **processing_kwargs
) -> BatchResult:
    """
    Convenience function to process a batch asynchronously with error handling.
    
    Args:
        items: List of items to process
        processing_func: Async function to process each item
        item_name: Name for items (for logging/error messages)
        config: Optional batch processing configuration
        **processing_kwargs: Additional kwargs for processing function
        
    Returns:
        BatchResult with detailed processing results
    """
    handler = BatchErrorHandler(config) if config else batch_error_handler
    return await handler.process_batch_async(items, processing_func, item_name, **processing_kwargs)


def get_batch_processing_stats() -> Dict[str, Any]:
    """Get global batch processing statistics."""
    return batch_error_handler.get_processing_stats()


def reset_batch_processing_stats():
    """Reset global batch processing statistics."""
    batch_error_handler.reset_stats()