"""
Configuration management system for GITTE.
Provides centralized configuration with environment variable overrides and feature flags.
"""

import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    dsn: str = "postgresql://gitte:password@localhost:5432/data_collector"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    def __post_init__(self):
        # Override with environment variable if provided
        if env_dsn := os.getenv("POSTGRES_DSN"):
            self.dsn = env_dsn


@dataclass
class LLMConfig:
    """LLM service configuration."""

    ollama_url: str = "http://localhost:11434"
    models: dict[str, str] = field(
        default_factory=lambda: {"default": "llama3", "creative": "mistral", "vision": "llava"}
    )
    timeout_seconds: int = 30
    max_retries: int = 3

    def __post_init__(self):
        if env_url := os.getenv("OLLAMA_URL"):
            self.ollama_url = env_url


@dataclass
class ImageGenerationConfig:
    """Image generation configuration."""

    model_name: str = "runwayml/stable-diffusion-v1-5"
    device: str = "auto"  # auto, cuda, cpu
    image_size: tuple = (512, 512)
    num_inference_steps: int = 20
    guidance_scale: float = 7.5

    def __post_init__(self):
        if env_model := os.getenv("SD_MODEL_NAME"):
            self.model_name = env_model


@dataclass
class ImageIsolationConfig:
    """Image isolation and quality detection configuration."""

    enabled: bool = True
    detection_confidence_threshold: float = 0.7
    edge_refinement_enabled: bool = True
    background_removal_method: str = "rembg"  # rembg, opencv, transparent, uniform
    fallback_to_original: bool = True
    max_processing_time: int = 10  # seconds
    output_format: str = "PNG"  # PNG for transparency support
    uniform_background_color: tuple = (255, 255, 255)

    def __post_init__(self):
        if env_enabled := os.getenv("IMAGE_ISOLATION_ENABLED"):
            self.enabled = env_enabled.lower() == "true"
        if env_threshold := os.getenv("IMAGE_ISOLATION_CONFIDENCE_THRESHOLD"):
            self.detection_confidence_threshold = float(env_threshold)


@dataclass
class StorageConfig:
    """Storage configuration for MinIO and local filesystem."""

    use_minio: bool = True
    minio_endpoint: str | None = "localhost:9000"
    minio_access_key: str | None = "minioadmin"
    minio_secret_key: str | None = "minioadmin"
    minio_bucket: str = "gitte-images"
    local_storage_path: str = "./generated_images"

    def __post_init__(self):
        if env_endpoint := os.getenv("MINIO_ENDPOINT"):
            self.minio_endpoint = env_endpoint
        if env_access_key := os.getenv("MINIO_ACCESS_KEY"):
            self.minio_access_key = env_access_key
        if env_secret_key := os.getenv("MINIO_SECRET_KEY"):
            self.minio_secret_key = env_secret_key


@dataclass
class SecurityConfig:
    """Security and encryption configuration."""

    secret_key: str = "dev-secret-key-change-in-production"
    encryption_key: str = "dev-encryption-key-change-in-production"
    password_hash_rounds: int = 12
    session_timeout_hours: int = 24

    def __post_init__(self):
        if env_secret := os.getenv("SECRET_KEY"):
            self.secret_key = env_secret
        if env_encryption := os.getenv("ENCRYPTION_KEY"):
            self.encryption_key = env_encryption


@dataclass
class FederatedLearningConfig:
    """Federated learning configuration."""

    enabled: bool = False
    server_url: str | None = None
    client_id: str | None = None
    aggregation_rounds: int = 10
    differential_privacy_epsilon: float = 1.0
    differential_privacy_delta: float = 1e-5

    def __post_init__(self):
        if env_enabled := os.getenv("FL_ENABLED"):
            self.enabled = env_enabled.lower() == "true"
        if env_server := os.getenv("FL_SERVER_URL"):
            self.server_url = env_server


@dataclass
class ImageCorrectionConfig:
    """Image correction dialog configuration."""

    enabled: bool = True
    auto_show_dialog: bool = True
    timeout_seconds: int = 300  # 5 minutes
    allow_manual_crop: bool = True
    allow_regeneration: bool = True
    save_correction_history: bool = True
    learning_from_corrections: bool = True

    def __post_init__(self):
        if env_enabled := os.getenv("IMAGE_CORRECTION_ENABLED"):
            self.enabled = env_enabled.lower() == "true"
        if env_timeout := os.getenv("IMAGE_CORRECTION_TIMEOUT"):
            self.timeout_seconds = int(env_timeout)


@dataclass
class TooltipConfig:
    """Tooltip system configuration."""

    enabled: bool = True
    show_delay_ms: int = 500
    hide_delay_ms: int = 200
    max_width: int = 300
    position: str = "auto"  # auto, top, bottom, left, right
    theme: str = "default"
    track_interactions: bool = True
    accessibility_mode: bool = False

    def __post_init__(self):
        if env_enabled := os.getenv("TOOLTIP_ENABLED"):
            self.enabled = env_enabled.lower() == "true"
        if env_delay := os.getenv("TOOLTIP_SHOW_DELAY"):
            self.show_delay_ms = int(env_delay)


@dataclass
class PrerequisiteConfig:
    """Prerequisite checking configuration."""

    enabled: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    parallel_execution: bool = True
    timeout_seconds: int = 30
    retry_attempts: int = 2
    fail_on_required: bool = True
    warn_on_recommended: bool = True
    ignore_optional: bool = False

    def __post_init__(self):
        if env_enabled := os.getenv("PREREQUISITE_CHECKS_ENABLED"):
            self.enabled = env_enabled.lower() == "true"
        if env_cache_ttl := os.getenv("PREREQUISITE_CACHE_TTL"):
            self.cache_ttl_seconds = int(env_cache_ttl)


@dataclass
class UXAuditConfig:
    """UX audit logging configuration."""

    enabled: bool = True
    log_tooltip_interactions: bool = True
    log_correction_actions: bool = True
    log_prerequisite_checks: bool = True
    log_workflow_events: bool = True
    retention_days: int = 90
    anonymize_data: bool = False

    def __post_init__(self):
        if env_enabled := os.getenv("UX_AUDIT_ENABLED"):
            self.enabled = env_enabled.lower() == "true"
        if env_retention := os.getenv("UX_AUDIT_RETENTION_DAYS"):
            self.retention_days = int(env_retention)


@dataclass
class FeatureFlags:
    """Feature flags for controlling system behavior."""

    save_llm_logs: bool = True
    use_federated_learning: bool = False
    enable_consistency_check: bool = False
    use_langchain: bool = False
    enable_image_generation: bool = True
    enable_image_isolation: bool = True
    enable_image_quality_detection: bool = True
    enable_image_correction_dialog: bool = True
    enable_minio_storage: bool = True
    enable_audit_logging: bool = True
    enable_pald_evolution: bool = True
    enable_consent_gate: bool = True
    enable_tooltip_system: bool = True
    enable_prerequisite_checks: bool = True
    enable_ux_audit_logging: bool = True

    def __post_init__(self):
        """Override feature flags from environment variables."""
        for flag_name in self.__dataclass_fields__:
            env_var = f"FEATURE_{flag_name.upper()}"
            if env_value := os.getenv(env_var):
                setattr(self, flag_name, env_value.lower() == "true")


@dataclass
class Config:
    """Main configuration class that aggregates all configuration sections."""

    # Environment
    environment: str = "development"
    debug: bool = True

    # Configuration sections
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    image_generation: ImageGenerationConfig = field(default_factory=ImageGenerationConfig)
    image_isolation: ImageIsolationConfig = field(default_factory=ImageIsolationConfig)
    image_correction: ImageCorrectionConfig = field(default_factory=ImageCorrectionConfig)
    tooltip: TooltipConfig = field(default_factory=TooltipConfig)
    prerequisite: PrerequisiteConfig = field(default_factory=PrerequisiteConfig)
    ux_audit: UXAuditConfig = field(default_factory=UXAuditConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    federated_learning: FederatedLearningConfig = field(default_factory=FederatedLearningConfig)
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)

    # Application settings
    app_name: str = "GITTE"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    def __post_init__(self):
        """Override main config from environment variables."""
        if env_environment := os.getenv("ENVIRONMENT"):
            self.environment = env_environment
            self.debug = env_environment == "development"

        if env_log_level := os.getenv("LOG_LEVEL"):
            self.log_level = env_log_level

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"

    def get_feature_flag(self, flag_name: str) -> bool:
        """Get a feature flag value by name."""
        return getattr(self.feature_flags, flag_name, False)

    def validate(self) -> None:
        """Validate configuration settings."""
        if self.is_production:
            if self.security.secret_key == "dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be set in production")
            if self.security.encryption_key == "dev-encryption-key-change-in-production":
                raise ValueError("ENCRYPTION_KEY must be set in production")


# Initialize configuration with environment-specific overrides
def initialize_config() -> Config:
    """Initialize configuration with environment-specific settings."""
    base_config = Config()

    # Apply environment-specific overrides
    try:
        from .environments import environment_manager

        environment = os.getenv("ENVIRONMENT", "development")
        config_with_env = environment_manager.apply_environment(base_config, environment)

        # Validate configuration
        config_with_env.validate()

        return config_with_env
    except ImportError:
        # Fallback if environment management is not available
        base_config.validate()
        return base_config


# Global configuration instance
config = initialize_config()

# Import and initialize other configuration components
try:
    from .feature_flags import feature_flag_manager, get_flag, is_enabled, set_flag
    from .text_management import get_text, set_language, text_manager
    from .validation import config_validator, validate_configuration, validate_runtime

    # Validate configuration on startup
    validation_result = validate_configuration(config)
    if not validation_result.is_valid:
        print("Configuration validation errors:")
        for error in validation_result.errors:
            print(f"  ERROR: {error}")

    if validation_result.warnings:
        print("Configuration warnings:")
        for warning in validation_result.warnings:
            print(f"  WARNING: {warning}")

except ImportError as e:
    print(f"Warning: Could not import configuration components: {e}")

    # Fallback text management
    def get_text(key: str, language: str = "en") -> str:
        """Fallback text function."""
        return key

    def get_flag(name: str) -> Any:
        """Fallback feature flag function."""
        return getattr(config.feature_flags, name, None)

    def is_enabled(name: str) -> bool:
        """Fallback feature flag check."""
        return bool(get_flag(name))
