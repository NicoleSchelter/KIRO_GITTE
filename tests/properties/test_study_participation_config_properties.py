"""
Property-based tests for study participation configuration management.
Tests configuration invariants and properties using parameterized tests.
"""

import os
from unittest.mock import patch
import pytest

from config.config import StudyParticipationConfig, Config


# Test data generators
def generate_valid_pseudonym_lengths():
    """Generate valid pseudonym length pairs where max >= min."""
    return [
        (1, 1), (1, 10), (3, 50), (5, 100), (10, 20), (25, 75)
    ]


def generate_valid_consistency_thresholds():
    """Generate valid consistency threshold values."""
    return [0.0, 0.1, 0.5, 0.8, 0.9, 1.0]


def generate_valid_positive_integers():
    """Generate valid positive integers for configuration."""
    return [1, 2, 5, 10, 50, 100, 500]


def generate_valid_boolean_strings():
    """Generate valid boolean string representations."""
    return ["true", "false", "True", "False", "TRUE", "FALSE"]


def generate_valid_consent_lists():
    """Generate valid consent lists."""
    return [
        ["data_protection"],
        ["data_protection", "ai_interaction"],
        ["data_protection", "ai_interaction", "study_participation"],
        ["custom_consent_1", "custom_consent_2"],
    ]


class TestStudyParticipationConfigProperties:
    """Property-based tests for StudyParticipationConfig."""

    @pytest.mark.parametrize("lengths", generate_valid_pseudonym_lengths())
    def test_pseudonym_length_validation_property(self, lengths):
        """Property: Valid pseudonym lengths should always pass validation."""
        min_length, max_length = lengths
        
        config = StudyParticipationConfig()
        config.pseudonym_min_length = min_length
        config.pseudonym_max_length = max_length
        
        errors = config.validate()
        
        # Property: No pseudonym length errors should occur for valid ranges
        pseudonym_errors = [e for e in errors if "pseudonym" in e.lower()]
        assert len(pseudonym_errors) == 0

    @pytest.mark.parametrize("invalid_min", [-100, -10, -1, 0])
    def test_invalid_pseudonym_min_length_property(self, invalid_min):
        """Property: Invalid pseudonym min lengths should always fail validation."""
        config = StudyParticipationConfig()
        config.pseudonym_min_length = invalid_min
        
        errors = config.validate()
        
        # Property: Should always have pseudonym min length error
        assert any("pseudonym_min_length must be at least 1" in error for error in errors)

    @pytest.mark.parametrize("threshold", generate_valid_consistency_thresholds())
    def test_consistency_threshold_validation_property(self, threshold):
        """Property: Valid consistency thresholds should always pass validation."""
        config = StudyParticipationConfig()
        config.pald_consistency_threshold = threshold
        
        errors = config.validate()
        
        # Property: No threshold errors should occur for valid values
        threshold_errors = [e for e in errors if "consistency_threshold" in e]
        assert len(threshold_errors) == 0

    @pytest.mark.parametrize("invalid_threshold", [1.1, 2.0, -0.1, -1.0, 10.0])
    def test_invalid_consistency_threshold_property(self, invalid_threshold):
        """Property: Invalid consistency thresholds should always fail validation."""
        config = StudyParticipationConfig()
        config.pald_consistency_threshold = invalid_threshold
        
        errors = config.validate()
        
        # Property: Should always have threshold error
        assert any("pald_consistency_threshold must be between 0.0 and 1.0" in error for error in errors)

    @pytest.mark.parametrize("value", generate_valid_positive_integers())
    def test_positive_integer_fields_property(self, value):
        """Property: Valid positive integers should pass validation for all positive integer fields."""
        positive_int_fields = [
            'max_feedback_rounds', 'pald_consistency_max_iterations',
            'image_generation_timeout', 'image_prompt_max_tokens',
            'data_retention_days'
        ]
        
        for field in positive_int_fields:
            # Reset config for each field test
            test_config = StudyParticipationConfig()
            setattr(test_config, field, value)
            
            errors = test_config.validate()
            
            # Property: No errors should occur for this field with valid positive value
            field_errors = [e for e in errors if field in e]
            assert len(field_errors) == 0, f"Field {field} should not have errors with value {value}"

    @pytest.mark.parametrize("invalid_value", [-100, -10, -1, 0])
    def test_invalid_positive_integer_fields_property(self, invalid_value):
        """Property: Invalid (non-positive) integers should fail validation."""
        positive_int_fields = [
            ('max_feedback_rounds', 'max_feedback_rounds must be at least 1'),
            ('pald_consistency_max_iterations', 'pald_consistency_max_iterations must be at least 1'),
            ('image_generation_timeout', 'image_generation_timeout must be at least 1 second'),
            ('image_prompt_max_tokens', 'image_prompt_max_tokens must be at least 1'),
            ('data_retention_days', 'data_retention_days must be at least 1'),
        ]
        
        for field, expected_error in positive_int_fields:
            test_config = StudyParticipationConfig()
            setattr(test_config, field, invalid_value)
            
            errors = test_config.validate()
            
            # Property: Should always have the expected error
            assert any(expected_error in error for error in errors), \
                f"Field {field} should have error for value {invalid_value}"

    @pytest.mark.parametrize("consents", generate_valid_consent_lists())
    def test_consent_list_validation_property(self, consents):
        """Property: Non-empty consent lists should always pass validation."""
        config = StudyParticipationConfig()
        config.required_consents = consents
        
        errors = config.validate()
        
        # Property: No consent errors should occur for non-empty lists
        consent_errors = [e for e in errors if "required_consents" in e]
        assert len(consent_errors) == 0

    def test_empty_consent_list_property(self):
        """Property: Empty consent lists should always fail validation."""
        config = StudyParticipationConfig()
        config.required_consents = []
        
        errors = config.validate()
        
        # Property: Should always have consent error
        assert any("required_consents cannot be empty" in error for error in errors)

    @pytest.mark.parametrize("env_value", generate_valid_boolean_strings())
    def test_boolean_environment_override_property(self, env_value):
        """Property: Boolean environment variables should always be properly parsed."""
        env_vars = {
            "STUDY_PARTICIPATION_ENABLED": env_value,
            "SURVEY_FALLBACK_ENABLED": env_value,
        }
        
        with patch.dict(os.environ, env_vars):
            config = StudyParticipationConfig()
            
            expected_value = env_value.lower() == "true"
            
            # Property: Boolean parsing should be consistent
            assert isinstance(config.study_participation_enabled, bool)
            assert config.study_participation_enabled == expected_value
            assert isinstance(config.survey_fallback_enabled, bool)
            assert config.survey_fallback_enabled == expected_value

    @pytest.mark.parametrize("env_value", ["1", "5", "10", "50", "100"])
    def test_integer_environment_override_property(self, env_value):
        """Property: Integer environment variables should always be properly parsed."""
        env_vars = {
            "PSEUDONYM_MIN_LENGTH": env_value,
            "MAX_FEEDBACK_ROUNDS": env_value,
        }
        
        with patch.dict(os.environ, env_vars):
            config = StudyParticipationConfig()
            
            expected_value = int(env_value)
            
            # Property: Integer parsing should be consistent
            assert isinstance(config.pseudonym_min_length, int)
            assert config.pseudonym_min_length == expected_value
            assert isinstance(config.max_feedback_rounds, int)
            assert config.max_feedback_rounds == expected_value


class TestConfigEnvironmentOverrideProperties:
    """Property-based tests for environment-specific configuration overrides."""

    @pytest.mark.parametrize("environment", ["development", "testing", "production"])
    def test_environment_override_consistency_property(self, environment):
        """Property: Environment overrides should be consistent and predictable."""
        config = Config()
        config.environment = environment
        
        # Apply overrides
        config.apply_environment_overrides()
        
        # Property: Environment overrides should be deterministic
        if environment == "development":
            assert config.study_participation.database_reset_enabled is True
            assert config.study_participation.survey_validation_strict is False
            assert config.study_participation.max_feedback_rounds == 1
        elif environment == "testing":
            assert config.study_participation.pseudonym_min_length == 1
            assert config.study_participation.max_feedback_rounds == 1
            assert config.study_participation.survey_validation_strict is False
        elif environment == "production":
            assert config.study_participation.database_reset_enabled is False
            assert config.study_participation.survey_validation_strict is True

    @pytest.mark.parametrize("environment", ["development", "testing", "production"])
    def test_environment_override_idempotency_property(self, environment):
        """Property: Applying environment overrides multiple times should be idempotent."""
        config = Config()
        config.environment = environment
        
        # Apply overrides twice
        config.apply_environment_overrides()
        values_after_first = {
            'database_reset_enabled': config.study_participation.database_reset_enabled,
            'survey_validation_strict': config.study_participation.survey_validation_strict,
            'max_feedback_rounds': config.study_participation.max_feedback_rounds,
        }
        
        config.apply_environment_overrides()
        values_after_second = {
            'database_reset_enabled': config.study_participation.database_reset_enabled,
            'survey_validation_strict': config.study_participation.survey_validation_strict,
            'max_feedback_rounds': config.study_participation.max_feedback_rounds,
        }
        
        # Property: Values should be identical after multiple applications
        assert values_after_first == values_after_second


class TestConfigValidationProperties:
    """Property-based tests for configuration validation properties."""

    @pytest.mark.parametrize("test_data", [
        ((1, 10), 0.5, 5, ["data_protection"]),
        ((3, 50), 0.8, 3, ["data_protection", "ai_interaction"]),
        ((5, 100), 1.0, 10, ["data_protection", "ai_interaction", "study_participation"]),
    ])
    def test_valid_configuration_property(self, test_data):
        """Property: Configurations with all valid values should always pass validation."""
        lengths, threshold, positive_int, consents = test_data
        min_length, max_length = lengths
        
        config = StudyParticipationConfig()
        config.pseudonym_min_length = min_length
        config.pseudonym_max_length = max_length
        config.pald_consistency_threshold = threshold
        config.max_feedback_rounds = positive_int
        config.required_consents = consents
        
        errors = config.validate()
        
        # Property: Valid configuration should have no errors
        assert len(errors) == 0, f"Valid configuration should not have errors: {errors}"

    @pytest.mark.parametrize("invalid_config", [
        (-1, 0),  # Invalid pseudonym_min_length and max_feedback_rounds
        (0, -1),  # Invalid pseudonym_min_length and max_feedback_rounds
        (-5, -3), # Invalid pseudonym_min_length and max_feedback_rounds
    ])
    def test_validation_error_consistency_property(self, invalid_config):
        """Property: Validation should consistently report the same errors for the same configuration."""
        pseudonym_min, feedback_rounds = invalid_config
        
        config = StudyParticipationConfig()
        config.pseudonym_min_length = pseudonym_min
        config.max_feedback_rounds = feedback_rounds
        
        # Run validation multiple times
        errors1 = config.validate()
        errors2 = config.validate()
        errors3 = config.validate()
        
        # Property: Validation should be deterministic
        assert errors1 == errors2 == errors3

    @pytest.mark.parametrize("valid_value", [1, 5, 10, 50])
    def test_validation_error_count_property(self, valid_value):
        """Property: Fixing validation errors should reduce error count."""
        config = StudyParticipationConfig()
        
        # Introduce multiple errors
        config.pseudonym_min_length = 0  # Error 1
        config.max_feedback_rounds = 0   # Error 2
        config.required_consents = []    # Error 3
        
        initial_errors = config.validate()
        initial_count = len(initial_errors)
        
        # Fix one error
        config.pseudonym_min_length = valid_value
        
        fixed_errors = config.validate()
        fixed_count = len(fixed_errors)
        
        # Property: Error count should decrease when fixing errors
        assert fixed_count < initial_count