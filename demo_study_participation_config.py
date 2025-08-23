#!/usr/bin/env python3
"""
Demonstration script for study participation configuration management.
Shows how to use the configuration system for study participation features.
"""

import os
from config.config import config, StudyParticipationConfig, initialize_config


def demonstrate_basic_configuration():
    """Demonstrate basic configuration access."""
    print("=== Basic Configuration Access ===")
    print(f"Study participation enabled: {config.study_participation.study_participation_enabled}")
    print(f"Max feedback rounds: {config.study_participation.max_feedback_rounds}")
    print(f"PALD consistency threshold: {config.study_participation.pald_consistency_threshold}")
    print(f"Required consents: {config.study_participation.required_consents}")
    print(f"Survey file path: {config.study_participation.survey_file_path}")
    print()


def demonstrate_feature_flags():
    """Demonstrate feature flag access."""
    print("=== Feature Flags ===")
    study_flags = [
        'enable_study_participation', 'enable_pseudonym_management',
        'enable_consent_collection', 'enable_dynamic_surveys',
        'enable_chat_pald_pipeline', 'enable_feedback_loops'
    ]
    
    for flag in study_flags:
        enabled = config.get_feature_flag(flag)
        print(f"{flag}: {enabled}")
    print()


def demonstrate_environment_overrides():
    """Demonstrate environment-specific overrides."""
    print("=== Environment Overrides ===")
    
    # Show current environment
    print(f"Current environment: {config.environment}")
    
    # Show environment-specific values
    print(f"Database reset enabled: {config.study_participation.database_reset_enabled}")
    print(f"Survey validation strict: {config.study_participation.survey_validation_strict}")
    print(f"Log performance metrics: {config.study_participation.log_performance_metrics}")
    print()


def demonstrate_validation():
    """Demonstrate configuration validation."""
    print("=== Configuration Validation ===")
    
    # Test valid configuration
    valid_config = StudyParticipationConfig()
    errors = valid_config.validate()
    print(f"Valid configuration errors: {len(errors)} ({errors})")
    
    # Test invalid configuration
    invalid_config = StudyParticipationConfig()
    invalid_config.pseudonym_min_length = 0
    invalid_config.max_feedback_rounds = 0
    invalid_config.required_consents = []
    
    errors = invalid_config.validate()
    print(f"Invalid configuration errors: {len(errors)}")
    for error in errors:
        print(f"  - {error}")
    print()


def demonstrate_environment_variables():
    """Demonstrate environment variable overrides."""
    print("=== Environment Variable Overrides ===")
    
    # Set some environment variables
    test_env_vars = {
        "MAX_FEEDBACK_ROUNDS": "5",
        "PALD_ANALYSIS_DEFERRED": "true",
        "SURVEY_VALIDATION_STRICT": "false",
    }
    
    print("Setting environment variables:")
    for var, value in test_env_vars.items():
        print(f"  {var}={value}")
        os.environ[var] = value
    
    # Create new configuration with environment overrides
    test_config = StudyParticipationConfig()
    
    print("\nConfiguration with environment overrides:")
    print(f"  Max feedback rounds: {test_config.max_feedback_rounds}")
    print(f"  PALD analysis deferred: {test_config.pald_analysis_deferred}")
    print(f"  Survey validation strict: {test_config.survey_validation_strict}")
    
    # Clean up environment variables
    for var in test_env_vars:
        del os.environ[var]
    print()


def demonstrate_configuration_usage_patterns():
    """Demonstrate common configuration usage patterns."""
    print("=== Common Usage Patterns ===")
    
    # Pattern 1: Check if feature is enabled
    if config.get_feature_flag('enable_study_participation'):
        print("✓ Study participation feature is enabled")
        
        # Pattern 2: Get configuration values for business logic
        max_rounds = config.study_participation.max_feedback_rounds
        print(f"  Using max feedback rounds: {max_rounds}")
        
        # Pattern 3: Check consistency settings
        if config.study_participation.enable_consistency_check:
            threshold = config.study_participation.pald_consistency_threshold
            print(f"  Consistency checking enabled with threshold: {threshold}")
    
    # Pattern 4: Environment-specific behavior
    if config.environment == "development":
        print("✓ Development mode: Database reset is allowed")
    elif config.environment == "production":
        print("✓ Production mode: Enhanced security and logging")
    
    # Pattern 5: Validation before use
    errors = config.study_participation.validate()
    if errors:
        print(f"⚠ Configuration validation errors: {errors}")
    else:
        print("✓ Configuration is valid")
    print()


def main():
    """Main demonstration function."""
    print("Study Participation Configuration Management Demo")
    print("=" * 50)
    print()
    
    demonstrate_basic_configuration()
    demonstrate_feature_flags()
    demonstrate_environment_overrides()
    demonstrate_validation()
    demonstrate_environment_variables()
    demonstrate_configuration_usage_patterns()
    
    print("Demo completed successfully!")


if __name__ == "__main__":
    main()