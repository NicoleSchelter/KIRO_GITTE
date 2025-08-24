"""
Configuration management system for GITTE.
Provides centralized configuration with environment variable overrides and feature flags.
"""

import os
from dataclasses import dataclass, field
from typing import Any
# Pydantic v2+: BaseSettings lives in pydantic-settings.
try:
    from pydantic_settings import BaseSettings  # v2 path
except Exception:  # Fallback for environments still on Pydantic v1
    from pydantic import BaseSettings  # v1 path

# Load .env early so all os.getenv calls see variables
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass  # safe no-op if python-dotenv is missing

class PersistenceSettings(BaseSettings):
    """
    Persistence-related feature flags.
    transactional_register:
        When True, user registration is executed in an explicit DB transaction
        via get_session() context. When False, legacy non-transactional path is used.
    """
    transactional_register: bool = True

@dataclass
class DatabaseConfig:
    """Database configuration settings."""

    dsn: str = "postgresql://gitte:password@localhost:5432/data_collector"
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    def __post_init__(self):
        # Prefer explicit DSN from env; support both POSTGRES_DSN and DATABASE_URL
        env_dsn = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
        if env_dsn:
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
    endpoint: str = "http://localhost:8080/isolate"  # URL or local binary path
    timeout_seconds: int = 20
    retries: int = 2
    model_default: str = "u2net"
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
        if env_endpoint := os.getenv("ISOLATION_ENDPOINT"):
            self.endpoint = env_endpoint
        if env_timeout := os.getenv("ISOLATION_TIMEOUT"):
            self.timeout_seconds = int(env_timeout)
        if env_retries := os.getenv("ISOLATION_RETRIES"):
            self.retries = int(env_retries)
        if env_model := os.getenv("ISOLATION_MODEL"):
            self.model_default = env_model
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
    db_connection_timeout: int = 5
    enable_image_isolation_check: bool = False
    isolation_endpoint: str | None = None

    def __post_init__(self):
        if env_enabled := os.getenv("PREREQUISITE_CHECKS_ENABLED"):
            self.enabled = env_enabled.lower() == "true"
        if env_cache_ttl := os.getenv("PREREQUISITE_CACHE_TTL"):
            self.cache_ttl_seconds = int(env_cache_ttl)
        if env_db_to := os.getenv("DB_CONNECTION_TIMEOUT"):
            self.db_connection_timeout = int(env_db_to)
        if env_iso := os.getenv("ENABLE_IMAGE_ISOLATION_CHECK"):
            self.enable_image_isolation_check = env_iso.lower() == "true"
        if env_iso_ep := os.getenv("ISOLATION_ENDPOINT"):
            self.isolation_endpoint = env_iso_ep


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
    
    # PALD Boundary Enforcement flags
    mandatory_pald_extraction: bool = True
    pald_analysis_deferred: bool = True
    enable_pald_boundary_enforcement: bool = True
    enable_pald_schema_evolution: bool = True
    enable_pald_candidate_harvesting: bool = True
    
    # Study Participation Feature Flags
    enable_study_participation: bool = True
    enable_pseudonym_management: bool = True
    enable_consent_collection: bool = True
    enable_dynamic_surveys: bool = True
    enable_chat_pald_pipeline: bool = True
    enable_feedback_loops: bool = True
    enable_interaction_logging: bool = True
    enable_admin_functions: bool = True

    def __post_init__(self):
        """Override feature flags from environment variables."""
        for flag_name in self.__dataclass_fields__:
            env_var = f"FEATURE_{flag_name.upper()}"
            if env_value := os.getenv(env_var):
                setattr(self, flag_name, env_value.lower() == "true")


@dataclass
class PALDBoundaryConfig:
    """Configuration for PALD boundary enforcement and schema evolution."""
    
    # Schema management
    pald_schema_file_path: str = "config/pald_schema.json"
    pald_schema_cache_ttl: int = 300  # 5 minutes
    pald_schema_checksum_log: bool = True
    
    # Candidate harvesting
    pald_candidate_min_support: int = 5
    candidate_review_required: bool = True
    
    # Migration settings
    migration_batch_size: int = 100
    migration_timeout_minutes: int = 60
    enable_migration_rollback: bool = True
    
    # Chat and PALD Pipeline Configuration
    max_feedback_rounds: int = 3
    pald_consistency_threshold: float = 0.8
    pald_consistency_max_iterations: int = 5
    
    def __post_init__(self):
        """Override from environment variables."""
        if env_path := os.getenv("PALD_SCHEMA_FILE_PATH"):
            self.pald_schema_file_path = env_path
        if env_ttl := os.getenv("PALD_SCHEMA_CACHE_TTL"):
            self.pald_schema_cache_ttl = int(env_ttl)
        if env_support := os.getenv("PALD_CANDIDATE_MIN_SUPPORT"):
            self.pald_candidate_min_support = int(env_support)
        if env_max_rounds := os.getenv("MAX_FEEDBACK_ROUNDS"):
            self.max_feedback_rounds = int(env_max_rounds)
        if env_threshold := os.getenv("PALD_CONSISTENCY_THRESHOLD"):
            self.pald_consistency_threshold = float(env_threshold)
        if env_max_iter := os.getenv("PALD_CONSISTENCY_MAX_ITERATIONS"):
            self.pald_consistency_max_iterations = int(env_max_iter)


@dataclass
class PALDEnhancementConfig:
    """Configuration for PALD enhancement features including bias analysis."""
    
    # Bias analysis settings
    bias_analysis_enabled: bool = True
    bias_job_priority_default: int = 10
    bias_job_max_retries: int = 3
    bias_job_timeout_minutes: int = 30
    
    # Schema evolution settings
    schema_evolution_threshold: int = 5
    schema_evolution_enabled: bool = True
    
    # Analysis settings
    analysis_batch_size: int = 50
    analysis_concurrent_limit: int = 3
    
    def __post_init__(self):
        """Override from environment variables."""
        if env_enabled := os.getenv("BIAS_ANALYSIS_ENABLED"):
            self.bias_analysis_enabled = env_enabled.lower() == "true"
        if env_priority := os.getenv("BIAS_JOB_PRIORITY_DEFAULT"):
            self.bias_job_priority_default = int(env_priority)
        if env_threshold := os.getenv("SCHEMA_EVOLUTION_THRESHOLD"):
            self.schema_evolution_threshold = int(env_threshold)


@dataclass
class StudyParticipationConfig:
    """Configuration for study participation and onboarding flow."""
    
    # Study Flow Configuration
    study_participation_enabled: bool = True
    pseudonym_min_length: int = 3
    pseudonym_max_length: int = 50
    required_consents: list[str] = field(
        default_factory=lambda: ["data_protection", "ai_interaction", "study_participation"]
    )
    
    # Survey Configuration
    survey_file_path: str = "config/study_survey.xlsx"
    survey_fallback_enabled: bool = True
    survey_validation_strict: bool = True
    
    # Chat and PALD Configuration
    max_feedback_rounds: int = 3
    pald_consistency_threshold: float = 0.8
    pald_consistency_max_iterations: int = 5
    enable_consistency_check: bool = True
    pald_analysis_deferred: bool = False
    
    # Image Generation Configuration
    image_generation_timeout: int = 30
    image_prompt_max_tokens: int = 77
    image_storage_path: str = "generated_images/"
    
    # Database Configuration
    database_reset_enabled: bool = False  # Safety flag
    auto_migration_enabled: bool = True
    foreign_key_checks_enabled: bool = True
    
    # Logging Configuration
    log_all_interactions: bool = True
    log_pald_processing: bool = True
    log_performance_metrics: bool = True
    audit_trail_enabled: bool = True
    
    # Error Handling Configuration
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    circuit_breaker_threshold: int = 5
    fallback_enabled: bool = True
    user_notification_required: bool = True
    
    # Data Privacy Configuration
    data_retention_days: int = 365
    anonymization_enabled: bool = True
    cascade_deletion_enabled: bool = True
    
    def __post_init__(self):
        """Override from environment variables."""
        if env_enabled := os.getenv("STUDY_PARTICIPATION_ENABLED"):
            self.study_participation_enabled = env_enabled.lower() == "true"
        if env_min_len := os.getenv("PSEUDONYM_MIN_LENGTH"):
            self.pseudonym_min_length = int(env_min_len)
        if env_max_len := os.getenv("PSEUDONYM_MAX_LENGTH"):
            self.pseudonym_max_length = int(env_max_len)
        if env_consents := os.getenv("REQUIRED_CONSENTS"):
            self.required_consents = env_consents.split(",")
        if env_survey_path := os.getenv("SURVEY_FILE_PATH"):
            self.survey_file_path = env_survey_path
        if env_survey_fallback := os.getenv("SURVEY_FALLBACK_ENABLED"):
            self.survey_fallback_enabled = env_survey_fallback.lower() == "true"
        if env_survey_strict := os.getenv("SURVEY_VALIDATION_STRICT"):
            self.survey_validation_strict = env_survey_strict.lower() == "true"
        if env_max_rounds := os.getenv("MAX_FEEDBACK_ROUNDS"):
            self.max_feedback_rounds = int(env_max_rounds)
        if env_threshold := os.getenv("PALD_CONSISTENCY_THRESHOLD"):
            self.pald_consistency_threshold = float(env_threshold)
        if env_max_iter := os.getenv("PALD_CONSISTENCY_MAX_ITERATIONS"):
            self.pald_consistency_max_iterations = int(env_max_iter)
        if env_consistency := os.getenv("ENABLE_CONSISTENCY_CHECK"):
            self.enable_consistency_check = env_consistency.lower() == "true"
        if env_deferred := os.getenv("PALD_ANALYSIS_DEFERRED"):
            self.pald_analysis_deferred = env_deferred.lower() == "true"
        if env_img_timeout := os.getenv("IMAGE_GENERATION_TIMEOUT"):
            self.image_generation_timeout = int(env_img_timeout)
        if env_img_tokens := os.getenv("IMAGE_PROMPT_MAX_TOKENS"):
            self.image_prompt_max_tokens = int(env_img_tokens)
        if env_img_path := os.getenv("IMAGE_STORAGE_PATH"):
            self.image_storage_path = env_img_path
        if env_db_reset := os.getenv("DATABASE_RESET_ENABLED"):
            self.database_reset_enabled = env_db_reset.lower() == "true"
        if env_auto_migration := os.getenv("AUTO_MIGRATION_ENABLED"):
            self.auto_migration_enabled = env_auto_migration.lower() == "true"
        if env_fk_checks := os.getenv("FOREIGN_KEY_CHECKS_ENABLED"):
            self.foreign_key_checks_enabled = env_fk_checks.lower() == "true"
        if env_log_interactions := os.getenv("LOG_ALL_INTERACTIONS"):
            self.log_all_interactions = env_log_interactions.lower() == "true"
        if env_log_pald := os.getenv("LOG_PALD_PROCESSING"):
            self.log_pald_processing = env_log_pald.lower() == "true"
        if env_log_perf := os.getenv("LOG_PERFORMANCE_METRICS"):
            self.log_performance_metrics = env_log_perf.lower() == "true"
        if env_audit := os.getenv("AUDIT_TRAIL_ENABLED"):
            self.audit_trail_enabled = env_audit.lower() == "true"
        if env_retention := os.getenv("DATA_RETENTION_DAYS"):
            self.data_retention_days = int(env_retention)
        if env_anon := os.getenv("ANONYMIZATION_ENABLED"):
            self.anonymization_enabled = env_anon.lower() == "true"
        if env_cascade := os.getenv("CASCADE_DELETION_ENABLED"):
            self.cascade_deletion_enabled = env_cascade.lower() == "true"
    
    def validate(self) -> list[str]:
        """Validate configuration parameters and return list of errors."""
        errors = []
        
        if self.pseudonym_min_length < 1:
            errors.append("pseudonym_min_length must be at least 1")
        if self.pseudonym_max_length < self.pseudonym_min_length:
            errors.append("pseudonym_max_length must be >= pseudonym_min_length")
        if self.max_feedback_rounds < 1:
            errors.append("max_feedback_rounds must be at least 1")
        if not (0.0 <= self.pald_consistency_threshold <= 1.0):
            errors.append("pald_consistency_threshold must be between 0.0 and 1.0")
        if self.pald_consistency_max_iterations < 1:
            errors.append("pald_consistency_max_iterations must be at least 1")
        if self.image_generation_timeout < 1:
            errors.append("image_generation_timeout must be at least 1 second")
        if self.image_prompt_max_tokens < 1:
            errors.append("image_prompt_max_tokens must be at least 1")
        if not self.required_consents:
            errors.append("required_consents cannot be empty")
        if self.data_retention_days < 1:
            errors.append("data_retention_days must be at least 1")
        
        return errors


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
    # NEW: persistence flags (ENV overrides via PERSISTENCE__TRANSACTIONAL_REGISTER)
    persistence: PersistenceSettings = field(default_factory=PersistenceSettings)
    feature_flags: FeatureFlags = field(default_factory=FeatureFlags)
    pald_boundary: PALDBoundaryConfig = field(default_factory=PALDBoundaryConfig)
    pald_enhancement: PALDEnhancementConfig = field(default_factory=PALDEnhancementConfig)
    study_participation: StudyParticipationConfig = field(default_factory=StudyParticipationConfig)

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
        
        # Validate study participation configuration
        study_errors = self.study_participation.validate()
        if study_errors:
            raise ValueError(f"Study participation configuration errors: {', '.join(study_errors)}")
    
    def apply_environment_overrides(self) -> None:
        """Apply environment-specific configuration overrides."""
        if self.environment == "development":
            self.study_participation.database_reset_enabled = True
            self.study_participation.survey_validation_strict = False
            self.study_participation.max_feedback_rounds = 1
            self.study_participation.log_performance_metrics = True
        
        elif self.environment == "testing":
            self.study_participation.pseudonym_min_length = 1
            self.study_participation.pald_consistency_max_iterations = 2
            self.study_participation.image_generation_timeout = 5
            self.study_participation.max_feedback_rounds = 1
            self.study_participation.survey_validation_strict = False
        
        elif self.environment == "production":
            self.study_participation.database_reset_enabled = False
            self.study_participation.log_performance_metrics = True
            self.study_participation.audit_trail_enabled = True
            self.study_participation.survey_validation_strict = True


# Initialize configuration with environment-specific overrides
def initialize_config() -> Config:
    """Initialize configuration with environment-specific settings."""
    base_config = Config()

    # Apply environment-specific overrides
    try:
        try:
            from .environments import environment_manager  # package import
        except ImportError:
            from environments import environment_manager   # top-level fallback

        environment = os.getenv("ENVIRONMENT", "development")
        config_with_env = environment_manager.apply_environment(base_config, environment)

        # Apply study participation environment overrides
        config_with_env.apply_environment_overrides()

        # Validate configuration
        config_with_env.validate()

        return config_with_env
    except ImportError:
        # Fallback if environment management is not available
        base_config.apply_environment_overrides()
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

# ---------------------------------------------------------------------------
# Consent Configuration (centralized)
# ---------------------------------------------------------------------------
CONSENT_TYPES_UI = [
    ("data_protection", "Data protection (GDPR)"),
    ("ai_interaction", "AI interaction"),
    ("study_participation", "Study participation"),
]

DEBUG_UI_CONSENT_KEYS = True

# ---------------------------------------------------------------------------
# Retry defaults (global) + image-pipeline tuning
# These are imported by utils/services (e.g., ux_error_handler / image isolation)
# ---------------------------------------------------------------------------
RETRY_DEFAULTS = {
    "max_retries": 3,
    "initial_backoff": 0.5,   # seconds
    "max_backoff": 8.0,       # seconds
    "jitter": 0.1,            # seconds added to each sleep (0.0 disables)
    "retry_on": (TimeoutError, ConnectionError, Exception),  # narrow at call sites
}

IMAGE_RETRY = {
    "max_retries": 4,
    "initial_backoff": 0.25,
    "max_backoff": 4.0,
    "jitter": 0.05,
    "retry_on": (TimeoutError, ConnectionError),
}
