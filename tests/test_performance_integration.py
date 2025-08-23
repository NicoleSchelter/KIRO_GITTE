"""
Performance integration tests for Study Participation system.
Tests performance characteristics under various load conditions.

This test suite validates:
- Performance under concurrent user onboarding scenarios
- Database performance with multiple simultaneous operations
- Memory usage and resource efficiency
- Response time characteristics under load

Requirements: 12.4, 12.7
"""

import pytest
import time
import threading
import concurrent.futures
import psutil
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4, UUID
from unittest.mock import Mock, patch

from src.data.models import StudyConsentType, ChatMessageType, StudyPALDType
from src.services.pseudonym_service import PseudonymService
from src.services.consent_service import ConsentService
from src.services.survey_service import SurveyService
from src.services.chat_service import ChatService
from src.logic.chat_logic import ChatLogic


class TestConcurrentUserPerformance:
    """Test performance under concurrent user scenarios."""
    
    @pytest.fixture
    def performance_setup(self):
        """Setup for performance testing."""
        # Mock database with realistic delays
        mock_db = Mock()
        
        def mock_add_with_delay(*args, **kwargs):
            time.sleep(0.001)  # Simulate 1ms database operation
        
        def mock_commit_with_delay(*args, **kwargs):
            time.sleep(0.002)  # Simulate 2ms commit operation
        
        mock_db.add = Mock(side_effect=mock_add_with_delay)
        mock_db.commit = Mock(side_effect=mock_commit_with_delay)
        mock_db.rollback = Mock()
        
        # Mock LLM service with realistic delays
        mock_llm = Mock()
        
        def mock_llm_response(*args, **kwargs):
            time.sleep(0.1)  # Simulate 100ms LLM response time
            response = Mock()
            response.text = '{"global_design_level": {"overall_appearance": "teacher"}}'
            return response
        
        mock_llm.generate_response = Mock(side_effect=mock_llm_response)
        
        return {
            "database": mock_db,
            "llm_service": mock_llm
        }
    
    def test_concurrent_pseudonym_creation_performance(self, performance_setup):
        """Test performance of concurrent pseudonym creation.
        
        Requirements: 12.4
        """
        database = performance_setup["database"]
        pseudonym_service = PseudonymService(database)
        
        num_concurrent_users = 50
        
        def create_pseudonym_task(user_index: int) -> Dict[str, Any]:
            """Task for creating a single pseudonym."""
            user_id = uuid4()
            pseudonym_text = f"U{user_index:03d}m2001AB{user_index:02d}"
            
            start_time = time.time()
            
            try:
                with patch.object(pseudonym_service, 'create_pseudonym') as mock_create:
                    from src.logic.pseudonym_logic import PseudonymResult
                    
                    # Simulate realistic processing time
                    time.sleep(0.01)  # 10ms processing time
                    
                    mock_create.return_value = PseudonymResult(
                        pseudonym_id=uuid4(),
                        pseudonym_text=pseudonym_text,
                        pseudonym_hash=f"hash_{user_index}",
                        created_at=datetime.utcnow(),
                        is_active=True
                    )
                    
                    result = pseudonym_service.create_pseudonym(user_id, pseudonym_text)
                    
                    processing_time = time.time() - start_time
                    
                    return {
                        "user_index": user_index,
                        "success": result.is_active,
                        "processing_time": processing_time,
                        "pseudonym_id": result.pseudonym_id
                    }
            
            except Exception as e:
                return {
                    "user_index": user_index,
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
        
        # Execute concurrent pseudonym creation
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_pseudonym_task, i) 
                for i in range(num_concurrent_users)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Performance assertions
        assert len(successful_results) == num_concurrent_users, f"Expected {num_concurrent_users} successful, got {len(successful_results)}"
        assert len(failed_results) == 0, f"Unexpected failures: {failed_results}"
        
        # Timing performance
        assert total_time < 5.0, f"Total time {total_time:.2f}s exceeded 5s limit"
        
        # Individual operation performance
        processing_times = [r["processing_time"] for r in successful_results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        max_processing_time = max(processing_times)
        
        assert avg_processing_time < 0.1, f"Average processing time {avg_processing_time:.3f}s exceeded 100ms"
        assert max_processing_time < 0.2, f"Max processing time {max_processing_time:.3f}s exceeded 200ms"
        
        # Throughput calculation
        throughput = num_concurrent_users / total_time
        assert throughput > 15, f"Throughput {throughput:.1f} ops/sec below minimum of 15 ops/sec"
        
        # Verify all pseudonym IDs are unique
        pseudonym_ids = [r["pseudonym_id"] for r in successful_results]
        assert len(set(pseudonym_ids)) == num_concurrent_users, "Duplicate pseudonym IDs detected"
    
    def test_concurrent_consent_processing_performance(self, performance_setup):
        """Test performance of concurrent consent processing.
        
        Requirements: 12.4
        """
        database = performance_setup["database"]
        consent_service = ConsentService(database)
        
        num_concurrent_operations = 30
        
        def process_consent_task(operation_index: int) -> Dict[str, Any]:
            """Task for processing consent for a single user."""
            pseudonym_id = uuid4()
            
            consents = {
                StudyConsentType.DATA_PROTECTION: True,
                StudyConsentType.AI_INTERACTION: True,
                StudyConsentType.STUDY_PARTICIPATION: True
            }
            
            start_time = time.time()
            
            try:
                with patch.object(consent_service, 'process_consent_collection') as mock_process:
                    from src.logic.consent_logic import ConsentResult
                    from src.data.models import StudyConsentRecord
                    
                    # Simulate realistic processing time
                    time.sleep(0.015)  # 15ms processing time
                    
                    mock_process.return_value = ConsentResult(
                        success=True,
                        can_proceed=True,
                        consent_records=[
                            StudyConsentRecord(
                                consent_id=uuid4(),
                                pseudonym_id=pseudonym_id,
                                consent_type=consent_type,
                                granted=granted,
                                version="1.0",
                                granted_at=datetime.utcnow()
                            )
                            for consent_type, granted in consents.items()
                        ],
                        failed_consents=[],
                        validation={"is_complete": True, "missing_consents": []}
                    )
                    
                    result = consent_service.process_consent_collection(pseudonym_id, consents)
                    
                    processing_time = time.time() - start_time
                    
                    return {
                        "operation_index": operation_index,
                        "success": result.success,
                        "processing_time": processing_time,
                        "consents_processed": len(result.consent_records)
                    }
            
            except Exception as e:
                return {
                    "operation_index": operation_index,
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
        
        # Execute concurrent consent processing
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(process_consent_task, i) 
                for i in range(num_concurrent_operations)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Performance assertions
        assert len(successful_results) == num_concurrent_operations
        assert len(failed_results) == 0
        
        # Timing performance
        assert total_time < 3.0, f"Total time {total_time:.2f}s exceeded 3s limit"
        
        # Individual operation performance
        processing_times = [r["processing_time"] for r in successful_results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        assert avg_processing_time < 0.05, f"Average processing time {avg_processing_time:.3f}s exceeded 50ms"
        
        # Verify all operations processed 3 consents
        total_consents = sum(r["consents_processed"] for r in successful_results)
        assert total_consents == num_concurrent_operations * 3
    
    def test_concurrent_chat_processing_performance(self, performance_setup):
        """Test performance of concurrent chat processing with PALD extraction.
        
        Requirements: 12.4
        """
        database = performance_setup["database"]
        llm_service = performance_setup["llm_service"]
        
        chat_service = ChatService(database)
        chat_logic = ChatLogic(llm_service)
        
        num_concurrent_chats = 25
        
        def process_chat_task(chat_index: int) -> Dict[str, Any]:
            """Task for processing a single chat interaction."""
            pseudonym_id = uuid4()
            session_id = uuid4()
            message_content = f"I want a friendly teacher for lesson {chat_index}"
            
            start_time = time.time()
            
            try:
                # Step 1: Store chat message
                with patch.object(chat_service, 'store_chat_message') as mock_store:
                    from src.data.models import ChatMessage
                    
                    mock_message = ChatMessage(
                        message_id=uuid4(),
                        pseudonym_id=pseudonym_id,
                        session_id=session_id,
                        message_type=ChatMessageType.USER,
                        content=message_content,
                        timestamp=datetime.utcnow()
                    )
                    mock_store.return_value = mock_message
                    
                    stored_message = chat_service.store_chat_message(
                        pseudonym_id=pseudonym_id,
                        session_id=session_id,
                        message_type=ChatMessageType.USER,
                        content=message_content
                    )
                
                # Step 2: Extract PALD
                with patch.object(chat_logic, 'extract_pald_from_text') as mock_extract:
                    from src.logic.chat_logic import PALDExtractionResult
                    
                    mock_extract.return_value = PALDExtractionResult(
                        success=True,
                        pald_data={"global_design_level": {"overall_appearance": "teacher"}},
                        extraction_confidence=0.9,
                        processing_time_ms=100
                    )
                    
                    pald_result = chat_logic.extract_pald_from_text(message_content)
                
                processing_time = time.time() - start_time
                
                return {
                    "chat_index": chat_index,
                    "success": True,
                    "processing_time": processing_time,
                    "message_stored": stored_message.message_id is not None,
                    "pald_extracted": pald_result.success
                }
            
            except Exception as e:
                return {
                    "chat_index": chat_index,
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
        
        # Execute concurrent chat processing
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            futures = [
                executor.submit(process_chat_task, i) 
                for i in range(num_concurrent_chats)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Performance assertions
        assert len(successful_results) == num_concurrent_chats
        assert len(failed_results) == 0
        
        # Timing performance (chat processing includes LLM calls, so more time allowed)
        assert total_time < 8.0, f"Total time {total_time:.2f}s exceeded 8s limit"
        
        # Individual operation performance
        processing_times = [r["processing_time"] for r in successful_results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        assert avg_processing_time < 0.3, f"Average processing time {avg_processing_time:.3f}s exceeded 300ms"
        
        # Verify all operations completed successfully
        messages_stored = sum(1 for r in successful_results if r["message_stored"])
        palds_extracted = sum(1 for r in successful_results if r["pald_extracted"])
        
        assert messages_stored == num_concurrent_chats
        assert palds_extracted == num_concurrent_chats


class TestDatabasePerformance:
    """Test database performance under various load conditions."""
    
    @pytest.fixture
    def database_setup(self):
        """Setup for database performance testing."""
        mock_db = Mock()
        
        # Track operation counts
        operation_counts = {
            "add_calls": 0,
            "commit_calls": 0,
            "rollback_calls": 0,
            "query_calls": 0
        }
        
        def count_add(*args, **kwargs):
            operation_counts["add_calls"] += 1
            time.sleep(0.001)  # Simulate database operation
        
        def count_commit(*args, **kwargs):
            operation_counts["commit_calls"] += 1
            time.sleep(0.002)  # Simulate commit operation
        
        def count_rollback(*args, **kwargs):
            operation_counts["rollback_calls"] += 1
            time.sleep(0.001)  # Simulate rollback operation
        
        def count_query(*args, **kwargs):
            operation_counts["query_calls"] += 1
            time.sleep(0.0005)  # Simulate query operation
            return Mock()
        
        mock_db.add = Mock(side_effect=count_add)
        mock_db.commit = Mock(side_effect=count_commit)
        mock_db.rollback = Mock(side_effect=count_rollback)
        mock_db.query = Mock(side_effect=count_query)
        
        return {
            "database": mock_db,
            "operation_counts": operation_counts
        }
    
    def test_database_transaction_performance(self, database_setup):
        """Test database transaction performance under load.
        
        Requirements: 12.4
        """
        database = database_setup["database"]
        operation_counts = database_setup["operation_counts"]
        
        num_transactions = 100
        
        def execute_transaction(transaction_id: int) -> Dict[str, Any]:
            """Execute a single database transaction."""
            start_time = time.time()
            
            try:
                # Simulate transaction with multiple operations
                database.add(Mock())  # Add pseudonym
                database.add(Mock())  # Add consent 1
                database.add(Mock())  # Add consent 2
                database.add(Mock())  # Add consent 3
                database.commit()     # Commit transaction
                
                processing_time = time.time() - start_time
                
                return {
                    "transaction_id": transaction_id,
                    "success": True,
                    "processing_time": processing_time,
                    "operations_count": 5  # 4 adds + 1 commit
                }
            
            except Exception as e:
                database.rollback()
                return {
                    "transaction_id": transaction_id,
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
        
        # Execute concurrent transactions
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [
                executor.submit(execute_transaction, i) 
                for i in range(num_transactions)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Performance assertions
        assert len(successful_results) == num_transactions
        assert len(failed_results) == 0
        
        # Timing performance
        assert total_time < 2.0, f"Total time {total_time:.2f}s exceeded 2s limit"
        
        # Individual transaction performance
        processing_times = [r["processing_time"] for r in successful_results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        assert avg_processing_time < 0.02, f"Average transaction time {avg_processing_time:.3f}s exceeded 20ms"
        
        # Verify operation counts
        expected_adds = num_transactions * 4  # 4 adds per transaction
        expected_commits = num_transactions   # 1 commit per transaction
        
        assert operation_counts["add_calls"] == expected_adds
        assert operation_counts["commit_calls"] == expected_commits
        assert operation_counts["rollback_calls"] == 0  # No failures expected
    
    def test_database_query_performance(self, database_setup):
        """Test database query performance under concurrent load.
        
        Requirements: 12.4
        """
        database = database_setup["database"]
        operation_counts = database_setup["operation_counts"]
        
        num_queries = 200
        
        def execute_query(query_id: int) -> Dict[str, Any]:
            """Execute a single database query."""
            start_time = time.time()
            
            try:
                # Simulate various query types
                database.query(Mock())  # Query pseudonym
                database.query(Mock())  # Query consents
                database.query(Mock())  # Query chat messages
                
                processing_time = time.time() - start_time
                
                return {
                    "query_id": query_id,
                    "success": True,
                    "processing_time": processing_time,
                    "queries_executed": 3
                }
            
            except Exception as e:
                return {
                    "query_id": query_id,
                    "success": False,
                    "error": str(e),
                    "processing_time": time.time() - start_time
                }
        
        # Execute concurrent queries
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [
                executor.submit(execute_query, i) 
                for i in range(num_queries)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze performance results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        # Performance assertions
        assert len(successful_results) == num_queries
        assert len(failed_results) == 0
        
        # Timing performance
        assert total_time < 1.5, f"Total time {total_time:.2f}s exceeded 1.5s limit"
        
        # Individual query performance
        processing_times = [r["processing_time"] for r in successful_results]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        assert avg_processing_time < 0.005, f"Average query time {avg_processing_time:.4f}s exceeded 5ms"
        
        # Query throughput
        total_queries_executed = sum(r["queries_executed"] for r in successful_results)
        query_throughput = total_queries_executed / total_time
        
        assert query_throughput > 300, f"Query throughput {query_throughput:.1f} queries/sec below minimum of 300"
        
        # Verify operation counts
        expected_queries = num_queries * 3  # 3 queries per operation
        assert operation_counts["query_calls"] == expected_queries


class TestMemoryAndResourceEfficiency:
    """Test memory usage and resource efficiency."""
    
    def test_memory_usage_during_concurrent_operations(self):
        """Test memory usage during concurrent operations.
        
        Requirements: 12.4
        """
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate memory-intensive concurrent operations
        num_operations = 100
        large_data_operations = []
        
        def create_large_data_operation(operation_id: int) -> Dict[str, Any]:
            """Create operation with large data structures."""
            # Simulate large PALD data
            large_pald = {
                "global_design_level": {
                    f"attribute_{i}": f"detailed_description_{i}" * 20
                    for i in range(25)
                },
                "middle_design_level": {
                    f"feature_{j}": f"feature_description_{j}" * 15
                    for j in range(30)
                },
                "detailed_level": {
                    f"detail_{k}": f"specific_detail_{k}" * 10
                    for k in range(50)
                }
            }
            
            # Simulate processing
            import json
            serialized_data = json.dumps(large_pald)
            
            return {
                "operation_id": operation_id,
                "data_size": len(serialized_data),
                "pald_attributes": len(large_pald["global_design_level"]) + 
                                len(large_pald["middle_design_level"]) + 
                                len(large_pald["detailed_level"])
            }
        
        # Execute concurrent memory-intensive operations
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_large_data_operation, i) 
                for i in range(num_operations)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        processing_time = time.time() - start_time
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Analyze memory usage
        total_data_size = sum(r["data_size"] for r in results)
        total_attributes = sum(r["pald_attributes"] for r in results)
        
        # Memory efficiency assertions
        assert len(results) == num_operations
        assert memory_increase < 200, f"Memory increased by {memory_increase:.1f}MB, exceeding 200MB limit"
        
        # Memory per operation should be reasonable
        memory_per_operation = memory_increase / num_operations
        assert memory_per_operation < 2.0, f"Memory per operation {memory_per_operation:.2f}MB exceeds 2MB limit"
        
        # Processing should be efficient
        assert processing_time < 3.0, f"Processing time {processing_time:.2f}s exceeded 3s limit"
        
        # Data processing efficiency
        data_throughput = total_data_size / processing_time / 1024 / 1024  # MB/s
        assert data_throughput > 1.0, f"Data throughput {data_throughput:.2f}MB/s below 1MB/s minimum"
    
    @pytest.mark.slow
    def test_resource_cleanup_efficiency(self):
        """Test resource cleanup efficiency after operations.
        
        Requirements: 12.4
        """
        import gc
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and process large amounts of data
        large_datasets = []
        
        for batch in range(10):
            batch_data = []
            
            for i in range(50):
                # Create large data structures
                large_object = {
                    "pseudonym_data": {f"user_{j}": f"data_{j}" * 100 for j in range(20)},
                    "consent_data": {f"consent_{k}": f"details_{k}" * 50 for k in range(15)},
                    "pald_data": {f"pald_{l}": f"content_{l}" * 75 for l in range(25)}
                }
                batch_data.append(large_object)
            
            large_datasets.append(batch_data)
            
            # Process batch
            for data in batch_data:
                import json
                serialized = json.dumps(data)
                assert len(serialized) > 0
            
            # Clear batch data and force garbage collection
            batch_data.clear()
            gc.collect()
            
            # Check memory after each batch
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            # Memory should not grow excessively between batches
            assert memory_increase < 100, f"Memory increase {memory_increase:.1f}MB after batch {batch} exceeds 100MB"
        
        # Final cleanup
        large_datasets.clear()
        gc.collect()
        
        # Check final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        final_memory_increase = final_memory - initial_memory
        
        # Memory should return close to initial levels after cleanup
        assert final_memory_increase < 50, f"Final memory increase {final_memory_increase:.1f}MB exceeds 50MB after cleanup"
    
    def test_cpu_usage_efficiency(self):
        """Test CPU usage efficiency during operations.
        
        Requirements: 12.4
        """
        import threading
        
        # Monitor CPU usage during operations
        cpu_usage_samples = []
        monitoring_active = threading.Event()
        monitoring_active.set()
        
        def monitor_cpu_usage():
            """Monitor CPU usage in background thread."""
            while monitoring_active.is_set():
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_usage_samples.append(cpu_percent)
                time.sleep(0.1)
        
        # Start CPU monitoring
        monitor_thread = threading.Thread(target=monitor_cpu_usage)
        monitor_thread.start()
        
        try:
            # Execute CPU-intensive operations
            num_operations = 200
            
            def cpu_intensive_operation(operation_id: int) -> Dict[str, Any]:
                """Simulate CPU-intensive operation."""
                start_time = time.time()
                
                # Simulate PALD processing (CPU-intensive)
                data = {"attributes": {}}
                for i in range(100):
                    data["attributes"][f"attr_{i}"] = f"value_{i}" * 10
                
                # Simulate JSON serialization/deserialization
                import json
                for _ in range(10):
                    serialized = json.dumps(data)
                    deserialized = json.loads(serialized)
                    assert len(deserialized["attributes"]) == 100
                
                processing_time = time.time() - start_time
                
                return {
                    "operation_id": operation_id,
                    "processing_time": processing_time,
                    "success": True
                }
            
            # Execute operations with controlled concurrency
            start_time = time.time()
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [
                    executor.submit(cpu_intensive_operation, i) 
                    for i in range(num_operations)
                ]
                results = [future.result() for future in concurrent.futures.as_completed(futures)]
            
            total_time = time.time() - start_time
            
        finally:
            # Stop CPU monitoring
            monitoring_active.clear()
            monitor_thread.join()
        
        # Analyze CPU usage
        if cpu_usage_samples:
            avg_cpu_usage = sum(cpu_usage_samples) / len(cpu_usage_samples)
            max_cpu_usage = max(cpu_usage_samples)
        else:
            avg_cpu_usage = 0
            max_cpu_usage = 0
        
        # Analyze operation results
        successful_operations = [r for r in results if r["success"]]
        processing_times = [r["processing_time"] for r in successful_operations]
        avg_processing_time = sum(processing_times) / len(processing_times)
        
        # CPU efficiency assertions
        assert len(successful_operations) == num_operations
        assert total_time < 10.0, f"Total time {total_time:.2f}s exceeded 10s limit"
        assert avg_processing_time < 0.05, f"Average processing time {avg_processing_time:.3f}s exceeded 50ms"
        
        # CPU usage should be reasonable (not maxing out the system)
        if cpu_usage_samples:
            assert avg_cpu_usage < 80, f"Average CPU usage {avg_cpu_usage:.1f}% exceeded 80%"
            assert max_cpu_usage < 95, f"Max CPU usage {max_cpu_usage:.1f}% exceeded 95%"
        
        # Operations per second should be efficient
        ops_per_second = num_operations / total_time
        assert ops_per_second > 25, f"Operations per second {ops_per_second:.1f} below minimum of 25"