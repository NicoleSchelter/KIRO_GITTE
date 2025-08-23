"""
Contract tests for study participation configuration management.
Tests the configuration interface contracts and adapter behavior.
"""

import os
import pytest
from unittest.mock import patch
from typing import Any, Dict

from config.config import StudyParticipationConfig, Config, initialize_config


class TestStudyParticipationConfigContract:
    """Contract tests for StudyParticipationConfig interface."""

    def test_config_initialization_contract(self):
        """Test that configuration initialization follows expected contract."""
        config = StudyParticipationConfig()
        
        # Contract: All boolean flags should have boolean type
        boolean_fields = [
            'study_participation_enabled', 'survey_fallback_enabled', 
            'survey_validation_strict', 'enable_consistency_check',
            'pald_analysis_deferred', 'database_reset_enabled',
            'auto_migration_enabled', 'foreign_key_checks_enabled',
            'log_all_interactions', 'log_pald_processing',
            'log_performance_metrics', 'audit_trail_enabled',
            'fallback_enabled', 'user_notification_required',
            'anonymization_enabled', 'cascade_deletion_enabled'
        ]
        
        for field in boolean_fields:
            assert isinstance(getattr(config, field), bool), f"{field} should be boolean"
    
    def test_config_numeric_contract(self):
        """Test that numeric configuration fields follow expected contract."""
        config = StudyParticipationConfig()
        
        # Contract: All numeric fields should have appropriate numeric types
        int_fields = [
            'pseudonym_min_length', 'pseudonym_max_length', 'max_feedback_rounds',
            'pald_consistency_max_iterations', 'image_generation_timeout',
            'image_prompt_max_tokens', 'max_retries', 'circuit_breaker_threshold',
            'data_retention_days'
        ]
        
        for field in int_fields:
            assert isinstance(getattr(config, field), int), f"{field} should be integer"
            assert getattr(config, field) >= 0, f"{field} should be non-negative"
        
        float_fields = ['pald_consistency_threshold', 'backoff_multiplier']
        
        for field in float_fields:
            assert isinstance(getattr(config, field), float), f"{field} should be float"
            assert getattr(config, field) >= 0.0, f"{field} should be non-negative"

    def test_config_string_contract(self):
        """Test that string configuration fields follow expected contract."""
        config = StudyParticipationConfig()
        
        # Contract: All string fields should have string type and not be empty
        string_fields = [
            'survey_file_path', 'image_storage_path'
        ]
        
        for field in string_fields:
            value = getattr(config, field)
            assert isinstance(value, str), f"{field} should be string"
            assert len(value) > 0, f"{field} should not be empty"

    def test_config_list_contract(self):
        """Test that list configuration fields follow expected contract."""
        config = StudyParticipationConfig()
        
        # Contract: required_consents should be a list of strings
        assert isinstance(config.required_consents, list)
        assert len(config.required_consents) > 0
        for consent in config.required_consents:
            assert isinstance(consent, str)
            assert len(consent) > 0

    def test_validation_contract(self):
        """Test that validation method follows expected contract."""
        config = StudyParticipationConfig()
        
        # Contract: validate() should return a list of strings
        errors = config.validate()
        assert isinstance(errors, list)
        for error in errors:
            assert isinstance(error, str)
            assert len(error) > 0

    def test_environment_override_contract(self):
        """Test that environment variable overrides follow expected contract."""
        # Contract: Environment variables should override default values
        env_vars = {
            "STUDY_PARTICIPATION_ENABLED": "false",
            "PSEUDONYM_MIN_LENGTH": "10",
            "MAX_FEEDBACK_ROUNDS": "5",
            "PALD_CONSISTENCY_THRESHOLD": "0.9",
        }
        
        with patch.dict(os.environ, env_vars):
            config = StudyParticipationConfig()
            
            # Contract: Boolean env vars should be properly parsed
            assert config.study_participation_enabled is False
            
            # Contract: Numeric env vars should be properly converted
            assert config.pseudonym_min_length == 10
            assert config.max_feedback_rounds == 5
            assert config.pald_consistency_threshold == 0.9


class TestMainConfigContract:
    """Contract tests for main Config class integration."""

    def test_config_aggregation_contract(self):
        """Test that main Config properly aggregates all configuration sections."""
        config = Config()
        
        # Contract: Config should have study_participation attribute
        assert hasattr(config, 'study_participation')
        assert isinstance(config.study_participation, StudyParticipationConfig)
        
        # Contract: Config should maintain all existing sections
        required_sections = [
            'database', 'llm', 'image_generation', 'image_isolation',
            'image_correction', 'tooltip', 'prerequisite', 'ux_audit',
            'storage', 'security', 'federated_learning', 'persistence',
            'feature_flags', 'pald_boundary', 'pald_enhancement',
            'study_participation'
        ]
        
        for section in required_sections:
            assert hasattr(config, section), f"Config should have {section} section"

    def test_validation_integration_contract(self):
        """Test that main Config validation integrates study participation validation."""
        config = Config()
        
        # Contract: validate() should not raise exception for valid config
        try:
            config.validate()
        except Exception as e:
            pytest.fail(f"Valid configuration should not raise exception: {e}")
        
        # Contract: validate() should raise exception for invalid study participation config
        config.study_participation.pseudonym_min_length = 0
        
        with pytest.raises(ValueError, match="Study participation configuration errors"):
            config.validate()

    def test_environment_override_integration_contract(self):
        """Test that environment overrides are properly integrated."""
        config = Config()
        
        # Contract: apply_environment_overrides should modify config based on environment
        original_reset_enabled = config.study_participation.database_reset_enabled
        
        config.environment = "development"
        config.apply_environment_overrides()
        
        # Development should enable database reset
        assert config.study_participation.database_reset_enabled is True
        
        config.environment = "production"
        config.apply_environment_overrides()
        
        # Production should disable database reset
        assert config.study_participation.database_reset_enabled is False

    def test_feature_flag_contract(self):
        """Test that feature flag access follows expected contract."""
        config = Config()
        
        # Contract: get_feature_flag should return boolean for existing flags
        study_flags = [
            'enable_study_participation', 'enable_pseudonym_management',
            'enable_consent_collection', 'enable_dynamic_surveys',
            'enable_chat_pald_pipeline', 'enable_feedback_loops',
            'enable_interaction_logging', 'enable_admin_functions'
        ]
        
        for flag in study_flags:
            result = config.get_feature_flag(flag)
            assert isinstance(result, bool), f"Feature flag {flag} should return boolean"
        
        # Contract: get_feature_flag should return False for non-existent flags
        assert config.get_feature_flag("nonexistent_flag") is False


class TestConfigInitializationContract:
    """Contract tests for configuration initialization process."""

    def test_initialize_config_contract(self):
        """Test that initialize_config follows expected contract."""
        config = initialize_config()
        
        # Contract: Should return Config instance
        assert isinstance(config, Config)
        
        # Contract: Should have all required sections initialized
        assert isinstance(config.study_participation, StudyParticipationConfig)
        
        # Contract: Should be validated (no exceptions during initialization)
        # This is tested by the fact that initialize_config completed successfully

    def test_initialize_config_environment_contract(self):
        """Test that initialize_config respects environment variables."""
        env_vars = {
            "ENVIRONMENT": "testing",
            "STUDY_PARTICIPATION_ENABLED": "false",
        }
        
        with patch.dict(os.environ, env_vars):
            config = initialize_config()
            
            # Contract: Environment should be set from env var
            assert config.environment == "testing"
            
            # Contract: Study participation config should respect env vars
            assert config.study_participation.study_participation_enabled is False
            
            # Contract: Environment-specific overrides should be applied
            assert config.study_participation.pseudonym_min_length == 1  # testing override

    def test_initialize_config_validation_contract(self):
        """Test that initialize_config validates configuration."""
        env_vars = {
            "PSEUDONYM_MIN_LENGTH": "0",  # Invalid value
        }
        
        with patch.dict(os.environ, env_vars):
            # Contract: Should raise ValueError for invalid configuration
            with pytest.raises(ValueError, match="Study participation configuration errors"):
                initialize_config()


class TestConfigurationParameterEnforcementContract:
    """Contract tests for configuration parameter enforcement."""

    def test_parameter_type_enforcement_contract(self):
        """Test that configuration parameters maintain their expected types."""
        config = StudyParticipationConfig()
        
        # Contract: Parameters should maintain their types after initialization
        type_map = {
            'max_feedback_rounds': int,
            'pald_analysis_deferred': bool,
            'enable_consistency_check': bool,
            'pald_consistency_threshold': float,
            'survey_file_path': str,
            'required_consents': list,
        }
        
        for param, expected_type in type_map.items():
            value = getattr(config, param)
            assert isinstance(value, expected_type), f"{param} should be {expected_type.__name__}"

    def test_parameter_range_enforcement_contract(self):
        """Test that configuration parameters enforce expected ranges."""
        config = StudyParticipationConfig()
        
        # Contract: Threshold should be between 0.0 and 1.0
        assert 0.0 <= config.pald_consistency_threshold <= 1.0
        
        # Contract: Positive integers should be positive
        positive_int_params = [
            'pseudonym_min_length', 'pseudonym_max_length', 'max_feedback_rounds',
            'pald_consistency_max_iterations', 'image_generation_timeout',
            'image_prompt_max_tokens', 'data_retention_days'
        ]
        
        for param in positive_int_params:
            value = getattr(config, param)
            assert value > 0, f"{param} should be positive"

    def test_parameter_consistency_contract(self):
        """Test that configuration parameters maintain internal consistency."""
        config = StudyParticipationConfig()
        
        # Contract: max_length should be >= min_length
        assert config.pseudonym_max_length >= config.pseudonym_min_length
        
        # Contract: required_consents should not be empty
        assert len(config.required_consents) > 0
        
        # Contract: All required consents should be valid strings
        for consent in config.required_consents:
            assert isinstance(consent, str)
            assert len(consent.strip()) > 0