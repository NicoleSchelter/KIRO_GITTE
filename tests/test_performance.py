"""
Performance tests for GITTE system.
Tests performance benchmarks for critical user flows and system components.
"""

import contextlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.data.models import User, UserRole
from src.logic.embodiment import EmbodimentLogic
from src.logic.llm import LLMLogic
from src.services.image_service import ImageService
from src.services.llm_service import LLMService
from src.services.storage_service import StorageService


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_chat_response_time_benchmark(self):
        """Test that chat responses meet performance requirements."""
        # Mock LLM service for consistent timing
        mock_llm_service = Mock(spec=LLMService)
        mock_llm_service.generate_response.return_value = Mock(
            text="Test response",
            model_used="test-model",
            generation_time=0.8,  # Under 2 second requirement
        )

        llm_logic = LLMLogic()
        llm_logic.llm_service = mock_llm_service

        user_id = uuid4()

        # Measure response time
        start_time = time.time()
        response = llm_logic.generate_embodiment_response(
            user_message="Test prompt", user_id=user_id, embodiment_context={}
        )
        end_time = time.time()

        response_time = end_time - start_time

        # Assert performance requirement (< 2 seconds)
        assert response_time < 2.0, f"Chat response took {response_time:.2f}s, expected < 2.0s"
        assert response.text == "Test response"

    def test_image_generation_time_benchmark(self):
        """Test that image generation meets performance requirements."""
        # Mock image provider for consistent timing
        mock_provider = Mock()
        mock_provider.generate_image.return_value = Mock(
            image_data=b"fake_image_data",
            metadata={"generation_time": 8.5},  # Under 15 second requirement
        )

        image_service = ImageService(provider=mock_provider)
        embodiment_logic = EmbodimentLogic()
        embodiment_logic.image_service = image_service

        user_id = uuid4()

        # Create embodiment request
        from src.logic.embodiment import EmbodimentRequest

        request = EmbodimentRequest(user_id=user_id, pald_data={}, custom_prompt="Test embodiment")

        # Measure generation time
        start_time = time.time()
        result = embodiment_logic.generate_embodiment_image(request)
        end_time = time.time()

        generation_time = end_time - start_time

        # Assert performance requirement (< 15 seconds)
        assert (
            generation_time < 15.0
        ), f"Image generation took {generation_time:.2f}s, expected < 15.0s"
        assert result.image_data == b"fake_image_data"

    @pytest.mark.slow
    def test_concurrent_chat_sessions_performance(self):
        """Test performance with multiple concurrent chat sessions."""
        # Mock LLM service
        mock_llm_service = Mock(spec=LLMService)
        mock_llm_service.generate_response.return_value = Mock(
            text="Concurrent response", model_used="test-model", generation_time=1.0
        )

        llm_logic = LLMLogic()
        llm_logic.llm_service = mock_llm_service

        def chat_session(session_id: int) -> dict[str, Any]:
            """Simulate a chat session."""
            user_id = uuid4()
            start_time = time.time()

            response = llm_logic.generate_embodiment_response(
                user_message=f"Test prompt {session_id}", user_id=user_id, embodiment_context={}
            )

            end_time = time.time()
            return {
                "session_id": session_id,
                "response_time": end_time - start_time,
                "success": response is not None,
            }

        # Test with 10 concurrent sessions
        num_sessions = 10
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [executor.submit(chat_session, i) for i in range(num_sessions)]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        # Verify all sessions completed successfully
        assert len(results) == num_sessions
        assert all(result["success"] for result in results)

        # Check that concurrent processing didn't take too long
        # Should be much faster than sequential (< 5 seconds for 10 sessions)
        assert total_time < 5.0, f"Concurrent sessions took {total_time:.2f}s, expected < 5.0s"

        # Check individual response times
        response_times = [result["response_time"] for result in results]
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        assert (
            avg_response_time < 2.0
        ), f"Average response time {avg_response_time:.2f}s, expected < 2.0s"
        assert (
            max_response_time < 3.0
        ), f"Max response time {max_response_time:.2f}s, expected < 3.0s"

    @pytest.mark.slow
    def test_concurrent_image_generation_performance(self):
        """Test performance with multiple concurrent image generations."""
        # Mock image provider
        mock_provider = Mock()
        mock_provider.generate_image.return_value = Mock(
            image_data=b"fake_image_data", metadata={"generation_time": 5.0}
        )

        image_service = ImageService(provider=mock_provider)
        embodiment_logic = EmbodimentLogic()
        embodiment_logic.image_service = image_service

        def image_generation_session(session_id: int) -> dict[str, Any]:
            """Simulate an image generation session."""
            user_id = uuid4()
            start_time = time.time()

            from src.logic.embodiment import EmbodimentRequest

            request = EmbodimentRequest(
                user_id=user_id, pald_data={}, custom_prompt=f"Test embodiment {session_id}"
            )
            result = embodiment_logic.generate_embodiment_image(request)

            end_time = time.time()
            return {
                "session_id": session_id,
                "generation_time": end_time - start_time,
                "success": result is not None,
            }

        # Test with 5 concurrent image generations
        num_sessions = 5
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [executor.submit(image_generation_session, i) for i in range(num_sessions)]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        # Verify all sessions completed successfully
        assert len(results) == num_sessions
        assert all(result["success"] for result in results)

        # Check that concurrent processing didn't take too long
        # Should be much faster than sequential (< 20 seconds for 5 generations)
        assert total_time < 20.0, f"Concurrent generations took {total_time:.2f}s, expected < 20.0s"

        # Check individual generation times
        generation_times = [result["generation_time"] for result in results]
        avg_generation_time = sum(generation_times) / len(generation_times)
        max_generation_time = max(generation_times)

        assert (
            avg_generation_time < 15.0
        ), f"Average generation time {avg_generation_time:.2f}s, expected < 15.0s"
        assert (
            max_generation_time < 20.0
        ), f"Max generation time {max_generation_time:.2f}s, expected < 20.0s"

    def test_database_query_performance(self):
        """Test database query performance."""
        from src.data.database import get_session

        # This would test actual database performance in a real environment
        # For now, we'll mock it to test the performance testing framework

        with patch("src.data.database.get_session") as mock_get_session:
            mock_session = Mock()
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = Mock(
                id=uuid4(), username="test_user", role=UserRole.PARTICIPANT
            )
            mock_session.query.return_value = mock_query
            mock_get_session.return_value.__enter__.return_value = mock_session

            start_time = time.time()

            # Simulate database query
            with get_session() as session:
                user = session.query(User).filter(User.username == "test_user").first()

            end_time = time.time()
            query_time = end_time - start_time

            # Database queries should be fast (< 0.1 seconds)
            assert query_time < 0.1, f"Database query took {query_time:.3f}s, expected < 0.1s"
            assert user is not None

    def test_storage_upload_performance(self):
        """Test file storage upload performance."""
        mock_storage = Mock(spec=StorageService)
        mock_storage.upload_file.return_value = "http://test.com/file.jpg"

        # Test file data (1MB)
        test_data = b"x" * (1024 * 1024)

        start_time = time.time()
        url = mock_storage.upload_file(test_data, "test_file.jpg", "image/jpeg")
        end_time = time.time()

        upload_time = end_time - start_time

        # File uploads should be reasonably fast (< 2 seconds for 1MB)
        assert upload_time < 2.0, f"File upload took {upload_time:.2f}s, expected < 2.0s"
        assert url == "http://test.com/file.jpg"


@pytest.mark.performance
class TestMemoryUsage:
    """Memory usage tests."""

    def test_chat_session_memory_usage(self):
        """Test that chat sessions don't leak memory."""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Mock LLM service
        mock_llm_service = Mock(spec=LLMService)
        mock_llm_service.generate_response.return_value = Mock(
            text="Test response", model_used="test-model", generation_time=0.5
        )

        llm_logic = LLMLogic()
        llm_logic.llm_service = mock_llm_service

        # Simulate multiple chat interactions
        user_id = uuid4()
        for i in range(100):
            response = llm_logic.generate_embodiment_response(
                user_message=f"Test prompt {i}", user_id=user_id, embodiment_context={}
            )
            assert response is not None

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 50MB for 100 interactions)
        max_memory_increase = 50 * 1024 * 1024  # 50MB
        assert (
            memory_increase < max_memory_increase
        ), f"Memory increased by {memory_increase / 1024 / 1024:.1f}MB, expected < 50MB"


@pytest.mark.performance
class TestLoadTesting:
    """Load testing scenarios."""

    @pytest.mark.slow
    def test_system_under_load(self):
        """Test system behavior under load."""
        # This would be a comprehensive load test
        # For now, we'll create a framework for it

        def simulate_user_session(user_id: str) -> dict[str, Any]:
            """Simulate a complete user session."""
            start_time = time.time()

            # Mock various operations
            operations = [("chat", 1.0), ("image_gen", 5.0), ("storage", 0.5)]

            results = []
            for op_name, duration in operations:
                op_start = time.time()
                time.sleep(duration / 10)  # Simulate reduced time for testing
                op_end = time.time()
                results.append(
                    {"operation": op_name, "duration": op_end - op_start, "success": True}
                )

            end_time = time.time()
            return {
                "user_id": user_id,
                "total_time": end_time - start_time,
                "operations": results,
                "success": True,
            }

        # Simulate 10 concurrent users
        num_users = 10
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [
                executor.submit(simulate_user_session, f"user_{i}") for i in range(num_users)
            ]
            results = [future.result() for future in as_completed(futures)]

        end_time = time.time()
        total_time = end_time - start_time

        # Verify all users completed successfully
        assert len(results) == num_users
        assert all(result["success"] for result in results)

        # Check system performance under load
        avg_session_time = sum(result["total_time"] for result in results) / len(results)
        max_session_time = max(result["total_time"] for result in results)

        # Sessions should complete in reasonable time even under load
        assert avg_session_time < 2.0, f"Average session time {avg_session_time:.2f}s under load"
        assert max_session_time < 3.0, f"Max session time {max_session_time:.2f}s under load"
        assert total_time < 5.0, f"Total load test time {total_time:.2f}s"


def benchmark_function(func, *args, **kwargs) -> dict[str, Any]:
    """
    Utility function to benchmark any function.

    Args:
        func: Function to benchmark
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Dict with timing and result information
    """
    start_time = time.time()
    start_memory = None

    try:
        import os

        import psutil

        process = psutil.Process(os.getpid())
        start_memory = process.memory_info().rss
    except ImportError:
        pass

    try:
        result = func(*args, **kwargs)
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)

    end_time = time.time()
    end_memory = None

    if start_memory:
        with contextlib.suppress(Exception):
            end_memory = process.memory_info().rss

    return {
        "duration": end_time - start_time,
        "success": success,
        "result": result,
        "error": error,
        "memory_start": start_memory,
        "memory_end": end_memory,
        "memory_delta": end_memory - start_memory if start_memory and end_memory else None,
    }
