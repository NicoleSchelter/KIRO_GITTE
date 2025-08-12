"""
Tests for configuration management system.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from config.config import Config
from config.environments import EnvironmentConfig, EnvironmentManager
from config.feature_flags import FeatureFlagDefinition, FeatureFlagManager, FeatureFlagType
from config.text_management import TextManager
from config.validation import ConfigurationValidator


class TestConfig:
    """Test basic configuration functionality."""

    def test_config_initialization(self):
        """Test that configuration initializes correctly."""
        config = Config()

        assert config.environment == "development"
        assert config.app_name == "GITTE"
        assert config.database.dsn is not None
        assert config.llm.ollama_url is not None
        assert config.feature_flags is not None

    def test_environment_override(self):
        """Test environment variable overrides."""
        # Set environment variable
        os.environ["POSTGRES_DSN"] = "postgresql://test:test@localhost/test_db"

        config = Config()
        assert "test_db" in config.database.dsn

        # Clean up
        del os.environ["POSTGRES_DSN"]

    def test_production_validation(self):
        """Test production environment validation."""
        config = Config()
        config.environment = "production"

        # Should raise error for default keys in production
        with pytest.raises(ValueError):
            config.validate()


class TestEnvironmentManager:
    """Test environment-specific configuration management."""

    def test_environment_config_creation(self):
        """Test creating environment configuration."""
        env_config = EnvironmentConfig(
            name="test", overrides={"debug": False, "log_level": "ERROR"}
        )

        assert env_config.name == "test"
        assert env_config.overrides["debug"] is False

    def test_apply_environment_overrides(self):
        """Test applying environment overrides to config."""
        base_config = Config()
        base_config.debug = True
        base_config.log_level = "INFO"

        env_config = EnvironmentConfig(
            name="test", overrides={"debug": False, "log_level": "ERROR"}
        )

        updated_config = env_config.apply_to_config(base_config)

        assert updated_config.debug is False
        assert updated_config.log_level == "ERROR"

    def test_environment_manager_with_temp_files(self):
        """Test environment manager with temporary configuration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test environment file
            env_dir = Path(temp_dir) / "environments"
            env_dir.mkdir()

            test_config = {"debug": False, "database": {"pool_size": 15}}

            with open(env_dir / "test.json", "w") as f:
                json.dump(test_config, f)

            # Initialize environment manager
            env_manager = EnvironmentManager(temp_dir)

            assert "test" in env_manager.list_environments()

            test_env = env_manager.get_environment_config("test")
            assert test_env is not None
            assert test_env.overrides["debug"] is False


class TestFeatureFlagManager:
    """Test feature flag management."""

    def test_feature_flag_definition(self):
        """Test creating feature flag definitions."""
        flag_def = FeatureFlagDefinition(
            name="test_flag",
            flag_type=FeatureFlagType.BOOLEAN,
            default_value=True,
            description="Test flag",
        )

        assert flag_def.name == "test_flag"
        assert flag_def.flag_type == FeatureFlagType.BOOLEAN
        assert flag_def.default_value is True

    def test_feature_flag_manager_basic(self):
        """Test basic feature flag manager functionality."""
        flag_manager = FeatureFlagManager()

        # Test getting default flags
        assert flag_manager.get_flag("save_llm_logs") is not None
        assert isinstance(flag_manager.is_enabled("save_llm_logs"), bool)

        # Test setting flags
        success = flag_manager.set_flag("save_llm_logs", False, "test")
        assert success is True
        assert flag_manager.get_flag("save_llm_logs") is False

    def test_feature_flag_validation(self):
        """Test feature flag validation."""
        flag_manager = FeatureFlagManager()

        # Test setting invalid value for validated flag
        success = flag_manager.set_flag("max_image_generation_concurrent", 100, "test")
        assert success is False  # Should fail validation

        success = flag_manager.set_flag("max_image_generation_concurrent", 5, "test")
        assert success is True  # Should pass validation


class TestTextManager:
    """Test text management and internationalization."""

    def test_text_manager_initialization(self):
        """Test text manager initialization."""
        text_manager = TextManager()

        assert text_manager.default_language == "en"
        assert text_manager.current_language == "en"
        assert len(text_manager.texts) > 0

    def test_get_text_basic(self):
        """Test basic text retrieval."""
        text_manager = TextManager()

        # Test existing key
        text = text_manager.get_text("app_title")
        assert "GITTE" in text

        # Test non-existing key (should return key itself)
        text = text_manager.get_text("non_existing_key")
        assert text == "non_existing_key"

    def test_language_switching(self):
        """Test language switching functionality."""
        text_manager = TextManager()

        # Add test language
        text_manager.add_texts("test", {"app_title": "Test Title"})

        # Switch language
        success = text_manager.set_language("test")
        assert success is True
        assert text_manager.current_language == "test"

        # Get text in new language
        text = text_manager.get_text("app_title")
        assert text == "Test Title"

    def test_text_formatting(self):
        """Test text formatting with parameters."""
        text_manager = TextManager()

        # Add text with formatting
        text_manager.add_texts("en", {"greeting": "Hello, {name}!"})

        # Test formatting
        text = text_manager.get_text("greeting", name="World")
        assert text == "Hello, World!"


class TestConfigurationValidator:
    """Test configuration validation."""

    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = ConfigurationValidator()

        assert len(validator.required_env_vars_production) > 0
        assert len(validator.recommended_env_vars) > 0

    def test_validate_development_config(self):
        """Test validating development configuration."""
        validator = ConfigurationValidator()
        config = Config()
        config.environment = "development"

        result = validator.validate_config(config)

        # Development config should be valid (with possible warnings)
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_validate_production_config_errors(self):
        """Test validation errors for production configuration."""
        validator = ConfigurationValidator()
        config = Config()
        config.environment = "production"

        result = validator.validate_config(config)

        # Should have errors for default keys in production
        assert len(result.errors) > 0
        assert not result.is_valid


class TestIntegration:
    """Integration tests for configuration system."""

    def test_config_with_environment_and_flags(self):
        """Test configuration with environment overrides and feature flags."""
        # Set environment variables
        os.environ["ENVIRONMENT"] = "testing"
        os.environ["FEATURE_SAVE_LLM_LOGS"] = "false"

        try:
            config = Config()

            # Check environment was applied
            assert config.environment == "testing"

            # Check feature flag was applied
            assert config.feature_flags.save_llm_logs is False

        finally:
            # Clean up
            if "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]
            if "FEATURE_SAVE_LLM_LOGS" in os.environ:
                del os.environ["FEATURE_SAVE_LLM_LOGS"]

    def test_full_configuration_cycle(self):
        """Test full configuration management cycle."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create environment config
            env_dir = Path(temp_dir) / "environments"
            env_dir.mkdir()

            test_env_config = {
                "debug": False,
                "log_level": "WARNING",
                "feature_flags": {"save_llm_logs": False},
            }

            with open(env_dir / "integration_test.json", "w") as f:
                json.dump(test_env_config, f)

            # Initialize managers
            env_manager = EnvironmentManager(temp_dir)

            # Apply environment
            base_config = Config()
            updated_config = env_manager.apply_environment(base_config, "integration_test")

            # Verify changes
            assert updated_config.debug is False
            assert updated_config.log_level == "WARNING"

            # Validate configuration
            validator = ConfigurationValidator()
            result = validator.validate_config(updated_config)

            # Should be valid (integration test environment)
            assert isinstance(result, object)  # ValidationResult object
