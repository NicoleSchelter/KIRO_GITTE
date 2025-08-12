"""
Configuration validation system for GITTE.
Provides comprehensive validation of configuration settings and environment setup.
"""

import os
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from .config import Config


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    info: list[str]

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Add an info message."""
        self.info.append(message)

    def has_issues(self) -> bool:
        """Check if there are any errors or warnings."""
        return len(self.errors) > 0 or len(self.warnings) > 0


class ConfigurationValidator:
    """Validates GITTE configuration settings."""

    def __init__(self):
        self.required_env_vars_production = ["SECRET_KEY", "ENCRYPTION_KEY", "POSTGRES_DSN"]

        self.recommended_env_vars = [
            "OLLAMA_URL",
            "MINIO_ENDPOINT",
            "MINIO_ACCESS_KEY",
            "MINIO_SECRET_KEY",
        ]

    def validate_config(self, config: Config) -> ValidationResult:
        """
        Perform comprehensive configuration validation.

        Args:
            config: Configuration object to validate

        Returns:
            ValidationResult with errors, warnings, and info
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])

        # Validate by category
        self._validate_environment(config, result)
        self._validate_security(config, result)
        self._validate_database(config, result)
        self._validate_llm(config, result)
        self._validate_storage(config, result)
        self._validate_feature_flags(config, result)
        self._validate_paths(config, result)
        self._validate_network_endpoints(config, result)

        return result

    def _validate_environment(self, config: Config, result: ValidationResult) -> None:
        """Validate environment-specific settings."""
        if config.environment not in ["development", "testing", "staging", "production"]:
            result.add_error(f"Invalid environment: {config.environment}")

        if config.is_production:
            # Production-specific validations
            for env_var in self.required_env_vars_production:
                if not os.getenv(env_var):
                    result.add_error(
                        f"Required environment variable {env_var} not set in production"
                    )

            if config.debug:
                result.add_warning("Debug mode is enabled in production")

            if config.log_level == "DEBUG":
                result.add_warning("Debug logging is enabled in production")

        result.add_info(f"Environment: {config.environment}")
        result.add_info(f"Debug mode: {config.debug}")
        result.add_info(f"Log level: {config.log_level}")

    def _validate_security(self, config: Config, result: ValidationResult) -> None:
        """Validate security configuration."""
        # Check secret key
        if config.security.secret_key == "dev-secret-key-change-in-production":
            if config.is_production:
                result.add_error("Default secret key used in production")
            else:
                result.add_warning("Using default secret key (change for production)")
        elif len(config.security.secret_key) < 32:
            result.add_warning("Secret key should be at least 32 characters long")

        # Check encryption key
        if config.security.encryption_key == "dev-encryption-key-change-in-production":
            if config.is_production:
                result.add_error("Default encryption key used in production")
            else:
                result.add_warning("Using default encryption key (change for production)")
        elif len(config.security.encryption_key) < 32:
            result.add_warning("Encryption key should be at least 32 characters long")

        # Check password hash rounds
        if config.security.password_hash_rounds < 10:
            result.add_warning("Password hash rounds should be at least 10 for security")
        elif config.security.password_hash_rounds > 15:
            result.add_warning("High password hash rounds may impact performance")

        # Check session timeout
        if config.security.session_timeout_hours > 72:
            result.add_warning("Very long session timeout may be a security risk")

        result.add_info(f"Password hash rounds: {config.security.password_hash_rounds}")
        result.add_info(f"Session timeout: {config.security.session_timeout_hours} hours")

    def _validate_database(self, config: Config, result: ValidationResult) -> None:
        """Validate database configuration."""
        try:
            parsed = urllib.parse.urlparse(config.database.dsn)

            if parsed.scheme != "postgresql":
                result.add_error("Only PostgreSQL databases are supported")

            if not parsed.hostname:
                result.add_error("Database hostname is required")

            if not parsed.port and parsed.hostname != "localhost":
                result.add_warning("Database port not specified, using default 5432")

            if not parsed.username:
                result.add_error("Database username is required")

            if not parsed.password and config.is_production:
                result.add_error("Database password is required in production")

            if not parsed.path or parsed.path == "/":
                result.add_error("Database name is required")

        except Exception as e:
            result.add_error(f"Invalid database DSN format: {e}")

        # Check connection pool settings
        if config.database.pool_size < 1:
            result.add_error("Database pool size must be at least 1")
        elif config.database.pool_size > 50:
            result.add_warning("Very large database pool size may consume excessive resources")

        if config.database.max_overflow < 0:
            result.add_error("Database max overflow cannot be negative")

        result.add_info(f"Database pool size: {config.database.pool_size}")
        result.add_info(f"Database max overflow: {config.database.max_overflow}")

    def _validate_llm(self, config: Config, result: ValidationResult) -> None:
        """Validate LLM configuration."""
        try:
            parsed = urllib.parse.urlparse(config.llm.ollama_url)
            if not parsed.scheme or not parsed.hostname:
                result.add_error("Invalid Ollama URL format")
        except Exception:
            result.add_error("Invalid Ollama URL")

        if config.llm.timeout_seconds < 5:
            result.add_warning("Very short LLM timeout may cause frequent failures")
        elif config.llm.timeout_seconds > 300:
            result.add_warning("Very long LLM timeout may impact user experience")

        if config.llm.max_retries < 1:
            result.add_warning("LLM max retries should be at least 1")
        elif config.llm.max_retries > 10:
            result.add_warning("Too many LLM retries may cause long delays")

        if not config.llm.models:
            result.add_error("No LLM models configured")
        elif "default" not in config.llm.models:
            result.add_warning("No default LLM model specified")

        result.add_info(f"Ollama URL: {config.llm.ollama_url}")
        result.add_info(f"LLM timeout: {config.llm.timeout_seconds}s")
        result.add_info(f"Configured models: {list(config.llm.models.keys())}")

    def _validate_storage(self, config: Config, result: ValidationResult) -> None:
        """Validate storage configuration."""
        if config.storage.use_minio:
            if not config.storage.minio_endpoint:
                result.add_error("MinIO endpoint is required when MinIO is enabled")

            if not config.storage.minio_access_key or not config.storage.minio_secret_key:
                if config.is_production:
                    result.add_error("MinIO credentials are required in production")
                else:
                    result.add_warning("MinIO credentials not set, using defaults")

            if config.storage.minio_access_key == "minioadmin" and config.is_production:
                result.add_error("Default MinIO credentials used in production")

        # Check local storage path
        local_path = Path(config.storage.local_storage_path)
        if not local_path.exists():
            result.add_warning(f"Local storage path does not exist: {local_path}")
        elif not os.access(local_path, os.W_OK):
            result.add_error(f"Local storage path is not writable: {local_path}")

        result.add_info(f"Using MinIO: {config.storage.use_minio}")
        result.add_info(f"Local storage path: {config.storage.local_storage_path}")

    def _validate_feature_flags(self, config: Config, result: ValidationResult) -> None:
        """Validate feature flag configuration."""
        flags = config.feature_flags

        # Check for conflicting flags
        if not flags.enable_consent_gate and config.is_production:
            result.add_error("Consent gate must be enabled in production for GDPR compliance")

        if flags.use_federated_learning and not flags.enable_audit_logging:
            result.add_warning("Federated learning should have audit logging enabled")

        if (
            flags.enable_image_generation
            and not flags.enable_minio_storage
            and config.is_production
        ):
            result.add_warning("Image generation in production should use MinIO storage")

        # Check federated learning config
        if flags.use_federated_learning and not config.federated_learning.server_url:
            result.add_error("Federated learning server URL is required when FL is enabled")

        enabled_flags = [name for name, value in flags.__dict__.items() if value is True]
        result.add_info(f"Enabled feature flags: {enabled_flags}")

    def _validate_paths(self, config: Config, result: ValidationResult) -> None:
        """Validate file system paths."""
        paths_to_check = [
            ("Local storage", config.storage.local_storage_path),
        ]

        for name, path_str in paths_to_check:
            path = Path(path_str)
            if not path.exists():
                result.add_warning(f"{name} path does not exist: {path}")
            elif not path.is_dir():
                result.add_error(f"{name} path is not a directory: {path}")
            elif not os.access(path, os.R_OK | os.W_OK):
                result.add_error(f"{name} path is not readable/writable: {path}")

    def _validate_network_endpoints(self, config: Config, result: ValidationResult) -> None:
        """Validate network endpoint configurations."""
        endpoints = [
            ("Ollama", config.llm.ollama_url),
        ]

        if config.storage.use_minio and config.storage.minio_endpoint:
            endpoints.append(("MinIO", f"http://{config.storage.minio_endpoint}"))

        for name, url in endpoints:
            try:
                parsed = urllib.parse.urlparse(url)
                if not parsed.scheme:
                    result.add_error(f"{name} URL missing scheme: {url}")
                elif parsed.scheme not in ["http", "https"]:
                    result.add_warning(f"{name} URL uses non-HTTP scheme: {parsed.scheme}")

                if not parsed.hostname:
                    result.add_error(f"{name} URL missing hostname: {url}")

                if parsed.scheme == "http" and config.is_production:
                    result.add_warning(f"{name} uses HTTP in production (consider HTTPS): {url}")

            except Exception as e:
                result.add_error(f"Invalid {name} URL format: {e}")

    def validate_runtime_requirements(self) -> ValidationResult:
        """Validate runtime requirements and dependencies."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[], info=[])

        # Check Python version
        import sys

        result.add_info(f"Python version: {sys.version}")

        # Check required packages
        required_packages = ["streamlit", "sqlalchemy", "psycopg2", "bcrypt", "requests", "pillow"]

        for package in required_packages:
            try:
                __import__(package)
                result.add_info(f"Package {package}: OK")
            except ImportError:
                result.add_error(f"Required package not found: {package}")

        # Check optional packages
        optional_packages = [
            ("torch", "Required for image generation"),
            ("diffusers", "Required for Stable Diffusion"),
            ("minio", "Required for MinIO storage"),
        ]

        for package, description in optional_packages:
            try:
                __import__(package)
                result.add_info(f"Optional package {package}: OK")
            except ImportError:
                result.add_warning(f"Optional package not found: {package} - {description}")

        return result


# Global validator instance
config_validator = ConfigurationValidator()


def validate_configuration(config: Config) -> ValidationResult:
    """Validate configuration and return results."""
    return config_validator.validate_config(config)


def validate_runtime() -> ValidationResult:
    """Validate runtime requirements."""
    return config_validator.validate_runtime_requirements()
