"""
Environment-specific configuration management for GITTE.
Provides configuration overrides for different deployment environments.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import Config


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration overrides."""

    name: str
    overrides: dict[str, Any] = field(default_factory=dict)

    def apply_to_config(self, config: Config) -> Config:
        """Apply environment-specific overrides to the base configuration."""
        for key, value in self.overrides.items():
            if hasattr(config, key):
                if isinstance(value, dict) and hasattr(getattr(config, key), "__dict__"):
                    # Handle nested configuration objects
                    nested_config = getattr(config, key)
                    for nested_key, nested_value in value.items():
                        if hasattr(nested_config, nested_key):
                            setattr(nested_config, nested_key, nested_value)
                else:
                    setattr(config, key, value)
        return config


class EnvironmentManager:
    """Manages environment-specific configurations."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.environments: dict[str, EnvironmentConfig] = {}
        self._load_environment_configs()

    def _load_environment_configs(self) -> None:
        """Load environment-specific configuration files."""
        env_dir = self.config_dir / "environments"
        if not env_dir.exists():
            return

        for env_file in env_dir.glob("*.json"):
            env_name = env_file.stem
            try:
                with open(env_file) as f:
                    overrides = json.load(f)
                self.environments[env_name] = EnvironmentConfig(name=env_name, overrides=overrides)
            except Exception as e:
                print(f"Warning: Failed to load environment config {env_file}: {e}")

        for env_file in env_dir.glob("*.yaml"):
            env_name = env_file.stem
            try:
                with open(env_file) as f:
                    overrides = yaml.safe_load(f)
                self.environments[env_name] = EnvironmentConfig(
                    name=env_name, overrides=overrides or {}
                )
            except Exception as e:
                print(f"Warning: Failed to load environment config {env_file}: {e}")

    def get_environment_config(self, environment: str) -> EnvironmentConfig | None:
        """Get configuration for a specific environment."""
        return self.environments.get(environment)

    def apply_environment(self, config: Config, environment: str) -> Config:
        """Apply environment-specific configuration to base config."""
        env_config = self.get_environment_config(environment)
        if env_config:
            return env_config.apply_to_config(config)
        return config

    def list_environments(self) -> list[str]:
        """List available environment configurations."""
        return list(self.environments.keys())


def create_environment_configs() -> None:
    """Create default environment configuration files."""
    env_dir = Path("config/environments")
    env_dir.mkdir(exist_ok=True)

    # Development environment
    dev_config = {
        "debug": True,
        "log_level": "DEBUG",
        "database": {"echo": True, "pool_size": 5},
        "security": {"session_timeout_hours": 48},
        "feature_flags": {"save_llm_logs": True, "enable_audit_logging": True},
    }

    with open(env_dir / "development.json", "w") as f:
        json.dump(dev_config, f, indent=2)

    # Testing environment
    test_config = {
        "debug": False,
        "log_level": "WARNING",
        "database": {
            "dsn": "postgresql://test:test@localhost:5432/test_kiro_test",
            "echo": False,
            "pool_size": 2,
        },
        "storage": {"use_minio": False, "local_storage_path": "./test_images"},
        "feature_flags": {"save_llm_logs": False, "enable_minio_storage": False},
    }

    with open(env_dir / "testing.json", "w") as f:
        json.dump(test_config, f, indent=2)

    # Production environment
    prod_config = {
        "debug": False,
        "log_level": "INFO",
        "database": {"echo": False, "pool_size": 20, "max_overflow": 30},
        "security": {"session_timeout_hours": 8, "password_hash_rounds": 14},
        "llm": {"timeout_seconds": 60, "max_retries": 5},
        "feature_flags": {
            "save_llm_logs": True,
            "enable_audit_logging": True,
            "enable_consent_gate": True,
        },
    }

    with open(env_dir / "production.json", "w") as f:
        json.dump(prod_config, f, indent=2)

    # Staging environment
    staging_config = {
        "debug": False,
        "log_level": "INFO",
        "database": {"echo": False, "pool_size": 10},
        "feature_flags": {
            "save_llm_logs": True,
            "use_federated_learning": True,
            "enable_audit_logging": True,
        },
    }

    with open(env_dir / "staging.json", "w") as f:
        json.dump(staging_config, f, indent=2)


# Global environment manager
environment_manager = EnvironmentManager()
