"""
Configuration package for GITTE system.
Provides centralized configuration management with environment overrides,
feature flags, text management, and validation.
"""

from .config import (
    Config,
    DatabaseConfig,
    FeatureFlags,
    FederatedLearningConfig,
    ImageGenerationConfig,
    LLMConfig,
    SecurityConfig,
    StorageConfig,
    config,
)

try:
    from .environments import environment_manager
    from .feature_flags import feature_flag_manager, get_flag, is_enabled, set_flag
    from .text_management import get_text, set_language, text_manager
    from .validation import config_validator, validate_configuration, validate_runtime
except ImportError:
    # Fallback functions if components are not available
    def get_text(key: str, language: str = "en", **kwargs) -> str:
        return key

    def get_flag(name: str):
        return getattr(config.feature_flags, name, None)

    def is_enabled(name: str) -> bool:
        return bool(get_flag(name))

    def set_flag(name: str, value, set_by: str = "runtime") -> bool:
        return False


__all__ = [
    # Main configuration
    "config",
    "Config",
    "DatabaseConfig",
    "LLMConfig",
    "ImageGenerationConfig",
    "StorageConfig",
    "SecurityConfig",
    "FederatedLearningConfig",
    "FeatureFlags",
    # Text management
    "get_text",
    "set_language",
    # Feature flags
    "get_flag",
    "is_enabled",
    "set_flag",
    # Validation
    "validate_configuration",
    "validate_runtime",
]
