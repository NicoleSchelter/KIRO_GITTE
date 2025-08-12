"""
Test configuration and utilities.
Provides test fixtures, mocks, and configuration for different test environments.
"""

import os
import tempfile
from collections.abc import Generator
from typing import Any
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

# Test environment configuration
TEST_CONFIG = {
    "database": {"url": "sqlite:///:memory:", "echo": False},  # In-memory database for tests
    "llm": {"ollama_url": "http://localhost:11434", "default_model": "test-model", "timeout": 30},
    "image": {"provider": "mock", "max_resolution": "512x512", "timeout": 60},
    "storage": {"provider": "local", "base_path": "/tmp/gitte_test"},
    "security": {
        "encryption_key": "test_key_32_bytes_long_for_aes256",
        "jwt_secret": "test_jwt_secret_key",
    },
    "feature_flags": {
        "enable_federated_learning": True,
        "enable_image_generation": True,
        "enable_audit_logging": True,
        "enable_personalization": True,
    },
}


@pytest.fixture(scope="session")
def test_config() -> dict[str, Any]:
    """Provide test configuration."""
    return TEST_CONFIG


@pytest.fixture(scope="function")
def temp_dir() -> Generator[str, None, None]:
    """Provide temporary directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
def mock_database():
    """Mock database session."""
    with patch("src.data.database.get_session") as mock_get_session:
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None
        yield mock_session


@pytest.fixture(scope="function")
def mock_llm_service():
    """Mock LLM service."""
    with patch("src.services.llm_service.LLMService") as mock_service:
        mock_instance = Mock()
        mock_instance.generate_response.return_value = Mock(
            text="Test response", model_used="test-model", generation_time=1.0
        )
        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_image_service():
    """Mock image service."""
    with patch("src.services.image_service.ImageService") as mock_service:
        mock_instance = Mock()
        mock_instance.generate_embodiment_image.return_value = Mock(
            image_data=b"fake_image_data",
            image_url="http://test.com/image.jpg",
            metadata={"style": "test"},
        )
        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_storage_service():
    """Mock storage service."""
    with patch("src.services.storage_service.StorageService") as mock_service:
        mock_instance = Mock()
        mock_instance.store_file.return_value = "http://test.com/file.jpg"
        mock_instance.get_file.return_value = b"fake_file_data"
        mock_service.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def test_user():
    """Provide test user data."""
    from src.data.models import User, UserRole

    return User(
        id=uuid4(),
        username="test_user",
        password_hash="hashed_password",
        role=UserRole.PARTICIPANT,
        pseudonym="test_pseudo",
    )


@pytest.fixture(scope="function")
def test_admin_user():
    """Provide test admin user data."""
    from src.data.models import User, UserRole

    return User(
        id=uuid4(),
        username="admin_user",
        password_hash="hashed_admin_password",
        role=UserRole.ADMIN,
        pseudonym="admin_pseudo",
    )


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response_text: str = "Mock response", generation_time: float = 1.0):
        self.response_text = response_text
        self.generation_time = generation_time
        self.call_count = 0

    def generate_response(self, prompt: str, **kwargs) -> Mock:
        """Generate mock response."""
        self.call_count += 1
        return Mock(
            text=self.response_text,
            metadata={"model": "mock-model", "generation_time": self.generation_time},
        )


class MockImageProvider:
    """Mock image provider for testing."""

    def __init__(self, image_data: bytes = b"fake_image", generation_time: float = 5.0):
        self.image_data = image_data
        self.generation_time = generation_time
        self.call_count = 0

    def generate_image(self, prompt: str, **kwargs) -> Mock:
        """Generate mock image."""
        self.call_count += 1
        return Mock(image_data=self.image_data, metadata={"generation_time": self.generation_time})


class MockStorageProvider:
    """Mock storage provider for testing."""

    def __init__(self):
        self.stored_files = {}
        self.call_count = 0

    def store_file(self, data: bytes, filename: str, content_type: str) -> str:
        """Store mock file."""
        self.call_count += 1
        file_id = f"mock_file_{len(self.stored_files)}"
        self.stored_files[file_id] = {
            "data": data,
            "filename": filename,
            "content_type": content_type,
        }
        return f"http://mock.storage.com/{file_id}"

    def get_file(self, file_id: str) -> bytes:
        """Get mock file."""
        if file_id in self.stored_files:
            return self.stored_files[file_id]["data"]
        raise FileNotFoundError(f"File {file_id} not found")


def create_test_environment():
    """Set up test environment variables."""
    test_env = {
        "ENVIRONMENT": "test",
        "DATABASE_URL": "sqlite:///:memory:",
        "LLM_OLLAMA_URL": "http://localhost:11434",
        "MINIO_ENDPOINT": "localhost:9000",
        "MINIO_ACCESS_KEY": "testuser",
        "MINIO_SECRET_KEY": "testpass",
        "ENCRYPTION_KEY": "test_key_32_bytes_long_for_aes256",
        "JWT_SECRET": "test_jwt_secret",
    }

    for key, value in test_env.items():
        os.environ[key] = value


def cleanup_test_environment():
    """Clean up test environment."""
    test_keys = [
        "ENVIRONMENT",
        "DATABASE_URL",
        "LLM_OLLAMA_URL",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "ENCRYPTION_KEY",
        "JWT_SECRET",
    ]

    for key in test_keys:
        if key in os.environ:
            del os.environ[key]


# Test markers for different test categories
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "gpu: Tests requiring GPU")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file names."""
    for item in items:
        # Add markers based on test file names
        if "test_performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        elif "test_e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        elif "test_security" in item.nodeid:
            item.add_marker(pytest.mark.security)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


# Test data factories
class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_user_data(role: str = "participant") -> dict[str, Any]:
        """Create test user data."""
        return {
            "username": f"test_user_{uuid4().hex[:8]}",
            "password": "TestPass123!",
            "role": role,
            "pseudonym": f"pseudo_{uuid4().hex[:8]}",
        }

    @staticmethod
    def create_survey_data() -> dict[str, Any]:
        """Create test survey data."""
        return {
            "learning_preferences": {
                "learning_style": "visual",
                "difficulty_preference": "intermediate",
                "pace_preference": "moderate",
            },
            "interests": ["technology", "science"],
            "goals": ["learn new skills", "improve knowledge"],
            "accessibility_needs": [],
        }

    @staticmethod
    def create_embodiment_data() -> dict[str, Any]:
        """Create test embodiment data."""
        return {
            "appearance_style": "professional",
            "personality": "friendly and knowledgeable",
            "communication_style": "clear and encouraging",
            "visual_preferences": {"color_scheme": "blue", "style": "modern"},
        }

    @staticmethod
    def create_chat_data() -> dict[str, Any]:
        """Create test chat interaction data."""
        return {
            "user_message": "Hello, I want to learn about Python",
            "assistant_response": "Great! Let's start with Python basics.",
            "context": {"topic": "programming", "difficulty": "beginner"},
            "feedback": "positive",
        }

    @staticmethod
    def create_pald_data() -> dict[str, Any]:
        """Create test PALD data."""
        return {
            "learning_style": "visual",
            "difficulty_preference": "intermediate",
            "topic_interests": ["programming", "data_science"],
            "interaction_patterns": {"preferred_time": "morning", "session_length": "30_minutes"},
            "feedback_patterns": {
                "positive_topics": ["tutorials", "examples"],
                "negative_topics": ["theory_heavy"],
            },
        }


# Performance testing utilities
class PerformanceTimer:
    """Utility for measuring performance in tests."""

    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        """Start timing."""
        import time

        self.start_time = time.time()

    def stop(self):
        """Stop timing."""
        import time

        self.end_time = time.time()

    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None or self.end_time is None:
            raise ValueError("Timer not properly started/stopped")
        return self.end_time - self.start_time

    def assert_under(self, max_seconds: float, message: str = ""):
        """Assert that elapsed time is under threshold."""
        elapsed = self.elapsed()
        assert elapsed < max_seconds, f"{message} Took {elapsed:.2f}s, expected < {max_seconds}s"


# Test database utilities
def create_test_database():
    """Create test database schema."""
    from src.data.database import engine
    from src.data.models import Base

    Base.metadata.create_all(bind=engine)


def cleanup_test_database():
    """Clean up test database."""
    from src.data.database import engine
    from src.data.models import Base

    Base.metadata.drop_all(bind=engine)


# Test assertion helpers
def assert_valid_uuid(uuid_string: str):
    """Assert that string is a valid UUID."""
    from uuid import UUID

    try:
        UUID(uuid_string)
    except ValueError:
        pytest.fail(f"'{uuid_string}' is not a valid UUID")


def assert_valid_timestamp(timestamp_string: str):
    """Assert that string is a valid ISO timestamp."""
    from datetime import datetime

    try:
        datetime.fromisoformat(timestamp_string.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"'{timestamp_string}' is not a valid ISO timestamp")


def assert_response_structure(response: dict[str, Any], required_fields: list):
    """Assert that response has required structure."""
    for field in required_fields:
        assert field in response, f"Response missing required field: {field}"


def assert_error_response(response: dict[str, Any]):
    """Assert that response is a proper error response."""
    assert "success" in response
    assert response["success"] is False
    assert "error" in response
    assert "message" in response


def assert_success_response(response: dict[str, Any]):
    """Assert that response is a proper success response."""
    assert "success" in response
    assert response["success"] is True
