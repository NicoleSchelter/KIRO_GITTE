"""
Pytest configuration and fixtures for GITTE tests.
"""

import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.config import Config, FeatureFlags


@pytest.fixture
def test_config():
    """Provide a test configuration instance."""
    config = Config()
    config.environment = "test"
    config.debug = True
    config.database.dsn = "postgresql://test:test@localhost:5432/test_db"
    config.feature_flags = FeatureFlags()
    return config


@pytest.fixture
def mock_feature_flags():
    """Provide mock feature flags for testing."""
    return FeatureFlags(
        save_llm_logs=False,
        use_federated_learning=False,
        enable_consistency_check=False,
        use_langchain=False,
        enable_image_generation=False,
        enable_minio_storage=False,
        enable_audit_logging=True,
        enable_pald_evolution=False,
        enable_consent_gate=True,
    )
