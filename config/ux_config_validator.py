"""
Configuration validation for UX enhancement features.
Validates configuration settings and provides helpful error messages.
"""

import logging
from typing import List, Dict, Any

from .config import Config

logger = logging.getLogger(__name__)


class UXConfigValidator:
    """Validator for UX enhancement configuration settings."""

    def __init__(self, config: Config):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> Dict[str, Any]:
        """
        Validate all UX enhancement configurations.
        
        Returns:
            Dict with validation results
        """
        self.errors.clear()
        self.warnings.clear()

        # Validate each configuration section
        self._validate_image_isolation()
        self._validate_image_correction()
        self._validate_tooltip_config()
        self._validate_prerequisite_config()
        self._validate_ux_audit_config()
        self._validate_feature_flags()

        return {
            "valid": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
            "total_issues": len(self.errors) + len(self.warnings)
        }

    def _validate_image_isolation(self):
        """Validate image isolation configuration."""
        config = self.config.image_isolation

        if config.enabled:
            # Validate confidence threshold
            if not 0.0 <= config.detection_confidence_threshold <= 1.0:
                self.errors.append(
                    f"Image isolation confidence threshold must be between 0.0 and 1.0, "
                    f"got {config.detection_confidence_threshold}"
                )

            # Validate processing time
            if config.max_processing_time <= 0:
                self.errors.append(
                    f"Image isolation max processing time must be positive, "
                    f"got {config.max_processing_time}"
                )

            # Validate background removal method
            valid_methods = ["rembg", "opencv", "transparent", "uniform"]
            if config.background_removal_method not in valid_methods:
                self.errors.append(
                    f"Invalid background removal method '{config.background_removal_method}'. "
                    f"Valid options: {valid_methods}"
                )

            # Validate output format
            valid_formats = ["PNG", "JPEG", "WEBP"]
            if config.output_format not in valid_formats:
                self.errors.append(
                    f"Invalid output format '{config.output_format}'. "
                    f"Valid options: {valid_formats}"
                )

            # Validate background color
            if len(config.uniform_background_color) != 3:
                self.errors.append(
                    f"Uniform background color must be RGB tuple with 3 values, "
                    f"got {len(config.uniform_background_color)} values"
                )
            else:
                for i, value in enumerate(config.uniform_background_color):
                    if not 0 <= value <= 255:
                        self.errors.append(
                            f"Background color value {i} must be between 0 and 255, got {value}"
                        )

    def _validate_image_correction(self):
        """Validate image correction configuration."""
        config = self.config.image_correction

        if config.enabled:
            # Validate timeout
            if config.timeout_seconds <= 0:
                self.errors.append(
                    f"Image correction timeout must be positive, got {config.timeout_seconds}"
                )

            # Warn about very short timeouts
            if config.timeout_seconds < 30:
                self.warnings.append(
                    f"Image correction timeout is very short ({config.timeout_seconds}s). "
                    "Users may not have enough time to make corrections."
                )

            # Warn about very long timeouts
            if config.timeout_seconds > 600:  # 10 minutes
                self.warnings.append(
                    f"Image correction timeout is very long ({config.timeout_seconds}s). "
                    "This may impact system resources."
                )

    def _validate_tooltip_config(self):
        """Validate tooltip configuration."""
        config = self.config.tooltip

        if config.enabled:
            # Validate delays
            if config.show_delay_ms < 0:
                self.errors.append(
                    f"Tooltip show delay must be non-negative, got {config.show_delay_ms}"
                )

            if config.hide_delay_ms < 0:
                self.errors.append(
                    f"Tooltip hide delay must be non-negative, got {config.hide_delay_ms}"
                )

            # Validate max width
            if config.max_width <= 0:
                self.errors.append(
                    f"Tooltip max width must be positive, got {config.max_width}"
                )

            # Validate position
            valid_positions = ["auto", "top", "bottom", "left", "right"]
            if config.position not in valid_positions:
                self.errors.append(
                    f"Invalid tooltip position '{config.position}'. "
                    f"Valid options: {valid_positions}"
                )

            # Validate theme
            valid_themes = ["default", "dark", "light", "high-contrast"]
            if config.theme not in valid_themes:
                self.warnings.append(
                    f"Unknown tooltip theme '{config.theme}'. "
                    f"Recommended themes: {valid_themes}"
                )

            # Warn about very long delays
            if config.show_delay_ms > 2000:
                self.warnings.append(
                    f"Tooltip show delay is very long ({config.show_delay_ms}ms). "
                    "This may impact user experience."
                )

    def _validate_prerequisite_config(self):
        """Validate prerequisite checking configuration."""
        config = self.config.prerequisite

        if config.enabled:
            # Validate cache TTL
            if config.cache_ttl_seconds <= 0:
                self.errors.append(
                    f"Prerequisite cache TTL must be positive, got {config.cache_ttl_seconds}"
                )

            # Validate timeout
            if config.timeout_seconds <= 0:
                self.errors.append(
                    f"Prerequisite timeout must be positive, got {config.timeout_seconds}"
                )

            # Validate retry attempts
            if config.retry_attempts < 0:
                self.errors.append(
                    f"Prerequisite retry attempts must be non-negative, got {config.retry_attempts}"
                )

            # Warn about very short cache TTL
            if config.cache_ttl_seconds < 60:
                self.warnings.append(
                    f"Prerequisite cache TTL is very short ({config.cache_ttl_seconds}s). "
                    "This may cause excessive prerequisite checks."
                )

            # Warn about very long timeout
            if config.timeout_seconds > 60:
                self.warnings.append(
                    f"Prerequisite timeout is very long ({config.timeout_seconds}s). "
                    "This may impact user experience."
                )

    def _validate_ux_audit_config(self):
        """Validate UX audit configuration."""
        config = self.config.ux_audit

        if config.enabled:
            # Validate retention days
            if config.retention_days <= 0:
                self.errors.append(
                    f"UX audit retention days must be positive, got {config.retention_days}"
                )

            # Warn about very short retention
            if config.retention_days < 7:
                self.warnings.append(
                    f"UX audit retention is very short ({config.retention_days} days). "
                    "This may not provide enough data for analysis."
                )

            # Warn about very long retention
            if config.retention_days > 365:
                self.warnings.append(
                    f"UX audit retention is very long ({config.retention_days} days). "
                    "This may impact storage requirements."
                )

    def _validate_feature_flags(self):
        """Validate feature flag consistency."""
        flags = self.config.feature_flags

        # Check for conflicting feature flags
        if flags.enable_image_correction_dialog and not flags.enable_image_isolation:
            self.warnings.append(
                "Image correction dialog is enabled but image isolation is disabled. "
                "The correction dialog may not function properly without isolation."
            )

        if flags.enable_image_quality_detection and not flags.enable_image_isolation:
            self.warnings.append(
                "Image quality detection is enabled but image isolation is disabled. "
                "Quality detection works best with isolation enabled."
            )

        if flags.enable_prerequisite_checks and not self.config.prerequisite.enabled:
            self.errors.append(
                "Prerequisite checks feature flag is enabled but prerequisite config is disabled. "
                "Enable prerequisite.enabled or disable the feature flag."
            )

        if flags.enable_tooltip_system and not self.config.tooltip.enabled:
            self.errors.append(
                "Tooltip system feature flag is enabled but tooltip config is disabled. "
                "Enable tooltip.enabled or disable the feature flag."
            )

    def validate_runtime_dependencies(self) -> Dict[str, Any]:
        """
        Validate runtime dependencies for UX features.
        
        Returns:
            Dict with dependency validation results
        """
        dependencies = {
            "valid": True,
            "missing_dependencies": [],
            "warnings": []
        }

        # Check for image processing dependencies
        if self.config.feature_flags.enable_image_isolation:
            try:
                import rembg
            except ImportError:
                dependencies["missing_dependencies"].append(
                    "rembg library required for image isolation"
                )
                dependencies["valid"] = False

            try:
                import cv2
            except ImportError:
                dependencies["missing_dependencies"].append(
                    "opencv-python required for image processing"
                )
                dependencies["valid"] = False

        # Check for UI dependencies
        if self.config.feature_flags.enable_tooltip_system:
            try:
                import streamlit
            except ImportError:
                dependencies["missing_dependencies"].append(
                    "streamlit required for tooltip system"
                )
                dependencies["valid"] = False

        return dependencies

    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of UX enhancement configuration.
        
        Returns:
            Dict with configuration summary
        """
        return {
            "image_isolation": {
                "enabled": self.config.image_isolation.enabled,
                "method": self.config.image_isolation.background_removal_method,
                "confidence_threshold": self.config.image_isolation.detection_confidence_threshold
            },
            "image_correction": {
                "enabled": self.config.image_correction.enabled,
                "timeout_seconds": self.config.image_correction.timeout_seconds,
                "allow_manual_crop": self.config.image_correction.allow_manual_crop
            },
            "tooltip_system": {
                "enabled": self.config.tooltip.enabled,
                "show_delay_ms": self.config.tooltip.show_delay_ms,
                "track_interactions": self.config.tooltip.track_interactions
            },
            "prerequisite_checks": {
                "enabled": self.config.prerequisite.enabled,
                "cache_ttl_seconds": self.config.prerequisite.cache_ttl_seconds,
                "parallel_execution": self.config.prerequisite.parallel_execution
            },
            "ux_audit": {
                "enabled": self.config.ux_audit.enabled,
                "retention_days": self.config.ux_audit.retention_days,
                "anonymize_data": self.config.ux_audit.anonymize_data
            },
            "feature_flags": {
                "image_isolation": self.config.feature_flags.enable_image_isolation,
                "image_correction": self.config.feature_flags.enable_image_correction_dialog,
                "tooltip_system": self.config.feature_flags.enable_tooltip_system,
                "prerequisite_checks": self.config.feature_flags.enable_prerequisite_checks,
                "ux_audit": self.config.feature_flags.enable_ux_audit_logging
            }
        }


def validate_ux_config(config: Config) -> Dict[str, Any]:
    """
    Convenience function to validate UX configuration.
    
    Args:
        config: Configuration instance to validate
        
    Returns:
        Dict with validation results
    """
    validator = UXConfigValidator(config)
    return validator.validate_all()


def get_ux_config_summary(config: Config) -> Dict[str, Any]:
    """
    Convenience function to get UX configuration summary.
    
    Args:
        config: Configuration instance to summarize
        
    Returns:
        Dict with configuration summary
    """
    validator = UXConfigValidator(config)
    return validator.get_config_summary()