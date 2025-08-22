"""
Tests for UX enhancement configuration system.
"""

import os
import pytest
import tempfile
from unittest.mock import patch

from config.config import (
    Config,
    ImageIsolationConfig,
    ImageCorrectionConfig,
    TooltipConfig,
    PrerequisiteConfig,
    UXAuditConfig,
    FeatureFlags
)
from config.ux_config_validator import UXConfigValidator, validate_ux_config
from config.ux_config_migration import UXConfigMigration, migrate_ux_config


class TestUXConfigurations:
    """Test UX enhancement configuration classes."""

    def test_image_isolation_config_defaults(self):
        """Test ImageIsolationConfig default values."""
        config = ImageIsolationConfig()
        
        assert config.enabled is True
        assert config.detection_confidence_threshold == 0.7
        assert config.edge_refinement_enabled is True
        assert config.background_removal_method == "rembg"
        assert config.fallback_to_original is True
        assert config.max_processing_time == 10
        assert config.output_format == "PNG"
        assert config.uniform_background_color == (255, 255, 255)

    def test_image_isolation_config_env_override(self):
        """Test ImageIsolationConfig environment variable overrides."""
        with patch.dict(os.environ, {
            'IMAGE_ISOLATION_ENABLED': 'false',
            'IMAGE_ISOLATION_CONFIDENCE_THRESHOLD': '0.8'
        }):
            config = ImageIsolationConfig()
            assert config.enabled is False
            assert config.detection_confidence_threshold == 0.8

    def test_image_correction_config_defaults(self):
        """Test ImageCorrectionConfig default values."""
        config = ImageCorrectionConfig()
        
        assert config.enabled is True
        assert config.auto_show_dialog is True
        assert config.timeout_seconds == 300
        assert config.allow_manual_crop is True
        assert config.allow_regeneration is True
        assert config.save_correction_history is True
        assert config.learning_from_corrections is True

    def test_tooltip_config_defaults(self):
        """Test TooltipConfig default values."""
        config = TooltipConfig()
        
        assert config.enabled is True
        assert config.show_delay_ms == 500
        assert config.hide_delay_ms == 200
        assert config.max_width == 300
        assert config.position == "auto"
        assert config.theme == "default"
        assert config.track_interactions is True
        assert config.accessibility_mode is False

    def test_prerequisite_config_defaults(self):
        """Test PrerequisiteConfig default values."""
        config = PrerequisiteConfig()
        
        assert config.enabled is True
        assert config.cache_ttl_seconds == 300
        assert config.parallel_execution is True
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 2
        assert config.fail_on_required is True
        assert config.warn_on_recommended is True
        assert config.ignore_optional is False

    def test_ux_audit_config_defaults(self):
        """Test UXAuditConfig default values."""
        config = UXAuditConfig()
        
        assert config.enabled is True
        assert config.log_tooltip_interactions is True
        assert config.log_correction_actions is True
        assert config.log_prerequisite_checks is True
        assert config.log_workflow_events is True
        assert config.retention_days == 90
        assert config.anonymize_data is False

    def test_feature_flags_ux_additions(self):
        """Test that FeatureFlags includes UX enhancement flags."""
        flags = FeatureFlags()
        
        assert hasattr(flags, 'enable_image_correction_dialog')
        assert hasattr(flags, 'enable_tooltip_system')
        assert hasattr(flags, 'enable_prerequisite_checks')
        assert hasattr(flags, 'enable_ux_audit_logging')
        
        assert flags.enable_image_correction_dialog is True
        assert flags.enable_tooltip_system is True
        assert flags.enable_prerequisite_checks is True
        assert flags.enable_ux_audit_logging is True

    def test_main_config_includes_ux_sections(self):
        """Test that main Config includes UX enhancement sections."""
        config = Config()
        
        assert hasattr(config, 'image_correction')
        assert hasattr(config, 'tooltip')
        assert hasattr(config, 'prerequisite')
        assert hasattr(config, 'ux_audit')
        
        assert isinstance(config.image_correction, ImageCorrectionConfig)
        assert isinstance(config.tooltip, TooltipConfig)
        assert isinstance(config.prerequisite, PrerequisiteConfig)
        assert isinstance(config.ux_audit, UXAuditConfig)


class TestUXConfigValidator:
    """Test UX configuration validator."""

    def test_valid_configuration(self):
        """Test validation of valid configuration."""
        config = Config()
        validator = UXConfigValidator(config)
        
        result = validator.validate_all()
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_invalid_image_isolation_config(self):
        """Test validation of invalid image isolation configuration."""
        config = Config()
        config.image_isolation.detection_confidence_threshold = 1.5  # Invalid: > 1.0
        config.image_isolation.max_processing_time = -1  # Invalid: negative
        config.image_isolation.background_removal_method = "invalid"  # Invalid method
        
        validator = UXConfigValidator(config)
        result = validator.validate_all()
        
        assert result["valid"] is False
        assert len(result["errors"]) >= 3

    def test_invalid_tooltip_config(self):
        """Test validation of invalid tooltip configuration."""
        config = Config()
        config.tooltip.show_delay_ms = -100  # Invalid: negative
        config.tooltip.max_width = 0  # Invalid: zero
        config.tooltip.position = "invalid"  # Invalid position
        
        validator = UXConfigValidator(config)
        result = validator.validate_all()
        
        assert result["valid"] is False
        assert len(result["errors"]) >= 3

    def test_warning_conditions(self):
        """Test configuration conditions that generate warnings."""
        config = Config()
        config.image_correction.timeout_seconds = 15  # Very short timeout
        config.tooltip.show_delay_ms = 3000  # Very long delay
        config.prerequisite.cache_ttl_seconds = 30  # Very short cache TTL
        
        validator = UXConfigValidator(config)
        result = validator.validate_all()
        
        assert result["valid"] is True  # No errors, just warnings
        assert len(result["warnings"]) >= 3

    def test_feature_flag_conflicts(self):
        """Test detection of conflicting feature flags."""
        config = Config()
        config.feature_flags.enable_image_correction_dialog = True
        config.feature_flags.enable_image_isolation = False  # Conflict
        
        validator = UXConfigValidator(config)
        result = validator.validate_all()
        
        assert len(result["warnings"]) >= 1
        assert any("correction dialog" in warning for warning in result["warnings"])

    def test_config_summary(self):
        """Test configuration summary generation."""
        config = Config()
        validator = UXConfigValidator(config)
        
        summary = validator.get_config_summary()
        
        assert "image_isolation" in summary
        assert "image_correction" in summary
        assert "tooltip_system" in summary
        assert "prerequisite_checks" in summary
        assert "ux_audit" in summary
        assert "feature_flags" in summary

    def test_validate_ux_config_convenience_function(self):
        """Test the convenience function for validation."""
        config = Config()
        result = validate_ux_config(config)
        
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result


class TestUXConfigMigration:
    """Test UX configuration migration utilities."""

    def test_environment_variables_generation(self):
        """Test generation of environment variables."""
        migration = UXConfigMigration()
        env_vars = migration.migrate_environment_variables()
        
        assert "IMAGE_ISOLATION_ENABLED" in env_vars
        assert "IMAGE_CORRECTION_ENABLED" in env_vars
        assert "TOOLTIP_ENABLED" in env_vars
        assert "PREREQUISITE_CHECKS_ENABLED" in env_vars
        assert "UX_AUDIT_ENABLED" in env_vars
        
        # Check feature flags
        assert "FEATURE_ENABLE_IMAGE_ISOLATION" in env_vars
        assert "FEATURE_ENABLE_TOOLTIP_SYSTEM" in env_vars

    def test_env_file_migration(self):
        """Test migration of .env file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("EXISTING_VAR=value\n")
            env_path = f.name
        
        try:
            migration = UXConfigMigration()
            result = migration.migrate_env_file(env_path)
            
            assert result is True
            
            # Check that new variables were added
            with open(env_path, 'r') as f:
                content = f.read()
                assert "IMAGE_ISOLATION_ENABLED" in content
                assert "TOOLTIP_ENABLED" in content
                assert "EXISTING_VAR=value" in content  # Original content preserved
                
        finally:
            os.unlink(env_path)

    def test_config_template_generation(self):
        """Test generation of configuration template."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            template_path = f.name
        
        try:
            migration = UXConfigMigration()
            result = migration.generate_config_template(template_path)
            
            assert result is True
            assert os.path.exists(template_path)
            
            # Check template content
            import json
            with open(template_path, 'r') as f:
                template = json.load(f)
                
            assert "image_isolation" in template
            assert "image_correction" in template
            assert "tooltip" in template
            assert "prerequisite" in template
            assert "ux_audit" in template
            assert "feature_flags" in template
            
        finally:
            os.unlink(template_path)

    def test_migration_validation(self):
        """Test migration validation."""
        migration = UXConfigMigration()
        
        # Test without any environment variables set
        result = migration.validate_migration()
        
        assert "valid" in result
        assert "issues" in result
        assert "recommendations" in result

    def test_migrate_ux_config_convenience_function(self):
        """Test the convenience function for migration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            env_path = f.name
        
        try:
            result = migrate_ux_config("env", env_path)
            assert result is True
            
        finally:
            os.unlink(env_path)


class TestConfigIntegration:
    """Test integration between configuration components."""

    def test_config_validation_integration(self):
        """Test that configuration and validation work together."""
        config = Config()
        
        # Modify some settings
        config.image_isolation.detection_confidence_threshold = 0.9
        config.tooltip.show_delay_ms = 1000
        config.prerequisite.cache_ttl_seconds = 600
        
        # Validate the modified configuration
        result = validate_ux_config(config)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_feature_flag_integration(self):
        """Test that feature flags properly control functionality."""
        config = Config()
        
        # Test that feature flags can be accessed
        assert config.get_feature_flag("enable_image_isolation") is True
        assert config.get_feature_flag("enable_tooltip_system") is True
        assert config.get_feature_flag("nonexistent_flag") is False

    def test_environment_override_integration(self):
        """Test that environment variables properly override defaults."""
        with patch.dict(os.environ, {
            'IMAGE_ISOLATION_ENABLED': 'false',
            'TOOLTIP_SHOW_DELAY': '1000',
            'PREREQUISITE_CACHE_TTL': '600',
            'FEATURE_ENABLE_IMAGE_ISOLATION': 'false'
        }):
            config = Config()
            
            assert config.image_isolation.enabled is False
            assert config.tooltip.show_delay_ms == 1000
            assert config.prerequisite.cache_ttl_seconds == 600
            assert config.feature_flags.enable_image_isolation is False