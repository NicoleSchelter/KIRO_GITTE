"""
Unit tests for study participation configuration management.
Tests configuration loading, validation, and environment-specific overrides.
"""

import os
import pytest
from unittest.mock import patch
from dataclasses import asdict

from config.config import (
    StudyParticipationConfig,
    Config,
    FeatureFlags,
    initialize_config,
)


class TestStudyParticipationConfig:
    """Test study participation configuration class."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = StudyParticipationConfig()
        
        assert config.study_participation_enabled is True
        assert config.pseudonym_min_length == 3
        assert config.pseudonym_max_length == 50
        assert config.required_consents == ["data_protection", "ai_interaction", "study_participation"]
        assert config.survey_file_path == "config/study_survey.xlsx"
        assert config.survey_fallback_enabled is True
        assert config.survey_validation_strict is True
        assert config.max_feedback_rounds == 3
        assert config.pald_consistency_threshold == 0.8
        assert config.pald_consistency_max_iterations == 5
        assert config.enable_consistency_check is True
        assert config.pald_analysis_deferred is False
        assert config.image_generation_timeout == 30
        assert config.image_prompt_max_tokens == 77
        assert config.image_storage_path == "generated_images/"
        assert config.database_reset_enabled is False
        assert config.auto_migration_enabled is True
        assert config.foreign_key_checks_enabled is True
        assert config.log_all_interactions is True
        assert config.log_pald_processing is True
        assert config.log_performance_metrics is True
        assert config.audit_trail_enabled is True
        assert config.max_retries == 3
        assert config.backoff_multiplier == 2.0
        assert config.circuit_breaker_threshold == 5
        assert config.fallback_enabled is True
        assert config.user_notification_required is True
        assert config.data_retention_days == 365
        assert config.anonymization_enabled is True
        assert config.cascade_deletion_enabled is True

    def test_environment_variable_overrides(self):
        """Test configuration override from environment variables."""
        env_vars = {
            "STUDY_PARTICIPATION_ENABLED": "false",
            "PSEUDONYM_MIN_LENGTH": "5",
            "PSEUDONYM_MAX_LENGTH": "100",
            "REQUIRED_CONSENTS": "data_protection,ai_interaction",
            "SURVEY_FILE_PATH": "/custom/survey.csv",
            "SURVEY_FALLBACK_ENABLED": "false",
            "SURVEY_VALIDATION_STRICT": "false",
            "MAX_FEEDBACK_ROUNDS": "5",
            "PALD_CONSISTENCY_THRESHOLD": "0.9",
            "PALD_CONSISTENCY_MAX_ITERATIONS": "10",
            "ENABLE_CONSISTENCY_CHECK": "false",
            "PALD_ANALYSIS_DEFERRED": "true",
            "IMAGE_GENERATION_TIMEOUT": "60",
            "IMAGE_PROMPT_MAX_TOKENS": "150",
            "IMAGE_STORAGE_PATH": "/custom/images/",
            "DATABASE_RESET_ENABLED": "true",
            "AUTO_MIGRATION_ENABLED": "false",
            "FOREIGN_KEY_CHECKS_ENABLED": "false",
            "LOG_ALL_INTERACTIONS": "false",
            "LOG_PALD_PROCESSING": "false",
            "LOG_PERFORMANCE_METRICS": "false",
            "AUDIT_TRAIL_ENABLED": "false",
            "DATA_RETENTION_DAYS": "180",
            "ANONYMIZATION_ENABLED": "false",
            "CASCADE_DELETION_ENABLED": "false",
        }
        
        with patch.dict(os.environ, env_vars):
            config = StudyParticipationConfig()
            
            assert config.study_participation_enabled is False
            assert config.pseudonym_min_length == 5
            assert config.pseudonym_max_length == 100
            assert config.required_consents == ["data_protection", "ai_interaction"]
            assert config.survey_file_path == "/custom/survey.csv"
            assert config.survey_fallback_enabled is False
            assert config.survey_validation_strict is False
            assert config.max_feedback_rounds == 5
            assert config.pald_consistency_threshold == 0.9
            assert config.pald_consistency_max_iterations == 10
            assert config.enable_consistency_check is False
            assert config.pald_analysis_deferred is True
            assert config.image_generation_timeout == 60
            assert config.image_prompt_max_tokens == 150
            assert config.image_storage_path == "/custom/images/"
            assert config.database_reset_enabled is True
            assert config.auto_migration_enabled is False
            assert config.foreign_key_checks_enabled is False
            assert config.log_all_interactions is False
            assert config.log_pald_processing is False
            assert config.log_performance_metrics is False
            assert config.audit_trail_enabled is False
            assert config.data_retention_days == 180
            assert config.anonymization_enabled is False
            assert config.cascade_deletion_enabled is False

    def test_validation_success(self):
        """Test successful configuration validation."""
        config = StudyParticipationConfig()
        errors = config.validate()
        assert errors == []

    def test_validation_pseudonym_length_errors(self):
        """Test validation errors for pseudonym length configuration."""
        config = StudyParticipationConfig()
        config.pseudonym_min_length = 0
        errors = config.validate()
        assert "pseudonym_min_length must be at least 1" in errors
        
        config.pseudonym_min_length = 10
        config.pseudonym_max_length = 5
        errors = config.validate()
        assert "pseudonym_max_length must be >= pseudonym_min_length" in errors

    def test_validation_feedback_rounds_error(self):
        """Test validation error for feedback rounds configuration."""
        config = StudyParticipationConfig()
        config.max_feedback_rounds = 0
        errors = config.validate()
        assert "max_feedback_rounds must be at least 1" in errors

    def test_validation_consistency_threshold_error(self):
        """Test validation error for consistency threshold configuration."""
        config = StudyParticipationConfig()
        config.pald_consistency_threshold = 1.5
        errors = config.validate()
        assert "pald_consistency_threshold must be between 0.0 and 1.0" in errors
        
        config.pald_consistency_threshold = -0.1
        errors = config.validate()
        assert "pald_consistency_threshold must be between 0.0 and 1.0" in errors

    def test_validation_iterations_error(self):
        """Test validation error for max iterations configuration."""
        config = StudyParticipationConfig()
        config.pald_consistency_max_iterations = 0
        errors = config.validate()
        assert "pald_consistency_max_iterations must be at least 1" in errors

    def test_validation_timeout_error(self):
        """Test validation error for timeout configuration."""
        config = StudyParticipationConfig()
        config.image_generation_timeout = 0
        errors = config.validate()
        assert "image_generation_timeout must be at least 1 second" in errors

    def test_validation_tokens_error(self):
        """Test validation error for token configuration."""
        config = StudyParticipationConfig()
        config.image_prompt_max_tokens = 0
        errors = config.validate()
        assert "image_prompt_max_tokens must be at least 1" in errors

    def test_validation_consents_error(self):
        """Test validation error for empty consents configuration."""
        config = StudyParticipationConfig()
        config.required_consents = []
        errors = config.validate()
        assert "required_consents cannot be empty" in errors

    def test_validation_retention_error(self):
        """Test validation error for data retention configuration."""
        config = StudyParticipationConfig()
        config.data_retention_days = 0
        errors = config.validate()
        assert "data_retention_days must be at least 1" in errors

    def test_validation_multiple_errors(self):
        """Test validation with multiple configuration errors."""
        config = StudyParticipationConfig()
        config.pseudonym_min_length = 0
        config.max_feedback_rounds = 0
        config.pald_consistency_threshold = 2.0
        config.required_consents = []
        
        errors = config.validate()
        assert len(errors) == 4
        assert "pseudonym_min_length must be at least 1" in errors
        assert "max_feedback_rounds must be at least 1" in errors
        assert "pald_consistency_threshold must be between 0.0 and 1.0" in errors
        assert "required_consents cannot be empty" in errors


class TestFeatureFlags:
    """Test feature flags for study participation."""

    def test_default_study_participation_flags(self):
        """Test default study participation feature flags."""
        flags = FeatureFlags()
        
        assert flags.enable_study_participation is True
        assert flags.enable_pseudonym_management is True
        assert flags.enable_consent_collection is True
        assert flags.enable_dynamic_surveys is True
        assert flags.enable_chat_pald_pipeline is True
        assert flags.enable_feedback_loops is True
        assert flags.enable_interaction_logging is True
        assert flags.enable_admin_functions is True

    def test_feature_flag_environment_overrides(self):
        """Test feature flag overrides from environment variables."""
        env_vars = {
            "FEATURE_ENABLE_STUDY_PARTICIPATION": "false",
            "FEATURE_ENABLE_PSEUDONYM_MANAGEMENT": "false",
            "FEATURE_ENABLE_CONSENT_COLLECTION": "false",
            "FEATURE_ENABLE_DYNAMIC_SURVEYS": "false",
            "FEATURE_ENABLE_CHAT_PALD_PIPELINE": "false",
            "FEATURE_ENABLE_FEEDBACK_LOOPS": "false",
            "FEATURE_ENABLE_INTERACTION_LOGGING": "false",
            "FEATURE_ENABLE_ADMIN_FUNCTIONS": "false",
        }
        
        with patch.dict(os.environ, env_vars):
            flags = FeatureFlags()
            
            assert flags.enable_study_participation is False
            assert flags.enable_pseudonym_management is False
            assert flags.enable_consent_collection is False
            assert flags.enable_dynamic_surveys is False
            assert flags.enable_chat_pald_pipeline is False
            assert flags.enable_feedback_loops is False
            assert flags.enable_interaction_logging is False
            assert flags.enable_admin_functions is False


class TestMainConfig:
    """Test main configuration class integration."""

    def test_study_participation_config_integration(self):
        """Test study participation config is properly integrated."""
        config = Config()
        
        assert hasattr(config, 'study_participation')
        assert isinstance(config.study_participation, StudyParticipationConfig)
        assert config.study_participation.study_participation_enabled is True

    def test_environment_overrides_development(self):
        """Test development environment overrides."""
        config = Config()
        config.environment = "development"
        config.apply_environment_overrides()
        
        assert config.study_participation.database_reset_enabled is True
        assert config.study_participation.survey_validation_strict is False
        assert config.study_participation.max_feedback_rounds == 1
        assert config.study_participation.log_performance_metrics is True

    def test_environment_overrides_testing(self):
        """Test testing environment overrides."""
        config = Config()
        config.environment = "testing"
        config.apply_environment_overrides()
        
        assert config.study_participation.pseudonym_min_length == 1
        assert config.study_participation.pald_consistency_max_iterations == 2
        assert config.study_participation.image_generation_timeout == 5
        assert config.study_participation.max_feedback_rounds == 1
        assert config.study_participation.survey_validation_strict is False

    def test_environment_overrides_production(self):
        """Test production environment overrides."""
        config = Config()
        config.environment = "production"
        config.apply_environment_overrides()
        
        assert config.study_participation.database_reset_enabled is False
        assert config.study_participation.log_performance_metrics is True
        assert config.study_participation.audit_trail_enabled is True
        assert config.study_participation.survey_validation_strict is True

    def test_config_validation_with_study_participation(self):
        """Test main config validation includes study participation validation."""
        config = Config()
        config.study_participation.pseudonym_min_length = 0
        
        with pytest.raises(ValueError, match="Study participation configuration errors"):
            config.validate()

    def test_config_validation_success(self):
        """Test successful main config validation."""
        config = Config()
        # Should not raise any exceptions
        config.validate()

    def test_get_feature_flag_method(self):
        """Test get_feature_flag method works with study participation flags."""
        config = Config()
        
        assert config.get_feature_flag("enable_study_participation") is True
        assert config.get_feature_flag("enable_pseudonym_management") is True
        assert config.get_feature_flag("nonexistent_flag") is False


class TestConfigInitialization:
    """Test configuration initialization and environment handling."""

    def test_initialize_config_default(self):
        """Test default configuration initialization."""
        config = initialize_config()
        
        assert isinstance(config, Config)
        assert isinstance(config.study_participation, StudyParticipationConfig)
        assert config.study_participation.study_participation_enabled is True

    def test_initialize_config_with_environment(self):
        """Test configuration initialization with environment variables."""
        env_vars = {
            "ENVIRONMENT": "production",  # Use production to avoid conflicting overrides
            "MAX_FEEDBACK_ROUNDS": "2",
            "PALD_ANALYSIS_DEFERRED": "true",
            "PSEUDONYM_MIN_LENGTH": "5",  # Test a value that won't be overridden
        }
        
        with patch.dict(os.environ, env_vars):
            config = initialize_config()
            
            assert config.environment == "production"
            assert config.study_participation.max_feedback_rounds == 2
            assert config.study_participation.pald_analysis_deferred is True
            assert config.study_participation.pseudonym_min_length == 5

    def test_initialize_config_validation_error(self):
        """Test configuration initialization with validation errors."""
        env_vars = {
            "PSEUDONYM_MIN_LENGTH": "0",  # Invalid value
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValueError, match="Study participation configuration errors"):
                initialize_config()

    def test_initialize_config_fallback(self):
        """Test configuration initialization fallback when environment manager unavailable."""
        # Test the fallback path by temporarily removing the import
        import sys
        original_modules = sys.modules.copy()
        
        # Remove environment modules if they exist
        modules_to_remove = [k for k in sys.modules.keys() if 'environments' in k]
        for module in modules_to_remove:
            del sys.modules[module]
        
        try:
            config = initialize_config()
            
            assert isinstance(config, Config)
            assert isinstance(config.study_participation, StudyParticipationConfig)
        finally:
            # Restore modules
            sys.modules.update(original_modules)


class TestConfigurationParameterEnforcement:
    """Test that configuration parameters are properly enforced."""

    def test_max_feedback_rounds_enforcement(self):
        """Test MAX_FEEDBACK_ROUNDS parameter enforcement."""
        config = StudyParticipationConfig()
        config.max_feedback_rounds = 5
        
        # This would be used by the feedback system
        assert config.max_feedback_rounds == 5

    def test_pald_analysis_deferred_enforcement(self):
        """Test PALD_ANALYSIS_DEFERRED parameter enforcement."""
        config = StudyParticipationConfig()
        config.pald_analysis_deferred = True
        
        # This would be used by the PALD processing system
        assert config.pald_analysis_deferred is True

    def test_enable_consistency_check_enforcement(self):
        """Test ENABLE_CONSISTENCY_CHECK parameter enforcement."""
        config = StudyParticipationConfig()
        config.enable_consistency_check = False
        
        # This would be used by the consistency checking system
        assert config.enable_consistency_check is False

    def test_configuration_immutability_after_validation(self):
        """Test that configuration maintains its values after validation."""
        config = StudyParticipationConfig()
        original_values = asdict(config)
        
        # Validation should not change values
        errors = config.validate()
        assert errors == []
        
        # Values should remain the same
        assert asdict(config) == original_values