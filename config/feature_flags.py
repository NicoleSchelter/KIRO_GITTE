"""
Advanced feature flag system with runtime toggling and validation.
Provides dynamic feature control without code changes.
"""

import json
import os
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class FeatureFlagType(Enum):
    """Types of feature flags."""

    BOOLEAN = "boolean"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    LIST = "list"


@dataclass
class FeatureFlagDefinition:
    """Definition of a feature flag with metadata."""

    name: str
    flag_type: FeatureFlagType
    default_value: Any
    description: str
    category: str = "general"
    requires_restart: bool = False
    validation_func: Callable[[Any], bool] | None = None
    dependencies: list[str] = field(default_factory=list)
    environments: list[str] = field(
        default_factory=lambda: ["development", "staging", "production"]
    )
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class FeatureFlagValue:
    """Runtime value of a feature flag."""

    name: str
    value: Any
    environment: str
    set_by: str = "system"
    set_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None


class FeatureFlagManager:
    """Advanced feature flag management system."""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.flags_dir = self.config_dir / "feature_flags"
        self.flags_dir.mkdir(exist_ok=True)

        self.definitions: dict[str, FeatureFlagDefinition] = {}
        self.values: dict[str, FeatureFlagValue] = {}
        self.environment = os.getenv("ENVIRONMENT", "development")
        self._lock = threading.RLock()

        self._load_flag_definitions()
        self._load_flag_values()
        self._setup_default_flags()

    def _setup_default_flags(self) -> None:
        """Set up default feature flags for GITTE system."""
        default_flags = [
            FeatureFlagDefinition(
                name="save_llm_logs",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=True,
                description="Enable saving of LLM interaction logs",
                category="logging",
            ),
            FeatureFlagDefinition(
                name="use_federated_learning",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=False,
                description="Enable federated learning functionality",
                category="ml",
                requires_restart=True,
            ),
            FeatureFlagDefinition(
                name="enable_consistency_check",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=False,
                description="Enable consistency checking for data operations",
                category="data",
            ),
            FeatureFlagDefinition(
                name="use_langchain",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=False,
                description="Use LangChain for LLM operations",
                category="llm",
                requires_restart=True,
            ),
            FeatureFlagDefinition(
                name="enable_image_generation",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=True,
                description="Enable image generation functionality",
                category="features",
            ),
            FeatureFlagDefinition(
                name="enable_minio_storage",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=True,
                description="Use MinIO for object storage",
                category="storage",
            ),
            FeatureFlagDefinition(
                name="enable_audit_logging",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=True,
                description="Enable comprehensive audit logging",
                category="logging",
            ),
            FeatureFlagDefinition(
                name="enable_pald_evolution",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=True,
                description="Enable dynamic PALD schema evolution",
                category="ml",
            ),
            FeatureFlagDefinition(
                name="enable_consent_gate",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=True,
                description="Enforce consent gate for all operations",
                category="privacy",
            ),
            FeatureFlagDefinition(
                name="max_image_generation_concurrent",
                flag_type=FeatureFlagType.INTEGER,
                default_value=3,
                description="Maximum concurrent image generation requests",
                category="performance",
                validation_func=lambda x: isinstance(x, int) and 1 <= x <= 10,
            ),
            FeatureFlagDefinition(
                name="llm_timeout_seconds",
                flag_type=FeatureFlagType.INTEGER,
                default_value=30,
                description="Timeout for LLM requests in seconds",
                category="performance",
                validation_func=lambda x: isinstance(x, int) and 5 <= x <= 300,
            ),
            FeatureFlagDefinition(
                name="supported_languages",
                flag_type=FeatureFlagType.LIST,
                default_value=["en", "de", "es"],
                description="List of supported UI languages",
                category="i18n",
            ),
            FeatureFlagDefinition(
                name="maintenance_mode",
                flag_type=FeatureFlagType.BOOLEAN,
                default_value=False,
                description="Enable maintenance mode",
                category="system",
                environments=["production", "staging"],
            ),
        ]

        for flag_def in default_flags:
            if flag_def.name not in self.definitions:
                self.definitions[flag_def.name] = flag_def

    def _load_flag_definitions(self) -> None:
        """Load feature flag definitions from files."""
        definitions_file = self.flags_dir / "definitions.json"
        if definitions_file.exists():
            try:
                with open(definitions_file) as f:
                    data = json.load(f)
                    for flag_data in data:
                        flag_def = FeatureFlagDefinition(
                            name=flag_data["name"],
                            flag_type=FeatureFlagType(flag_data["flag_type"]),
                            default_value=flag_data["default_value"],
                            description=flag_data["description"],
                            category=flag_data.get("category", "general"),
                            requires_restart=flag_data.get("requires_restart", False),
                            dependencies=flag_data.get("dependencies", []),
                            environments=flag_data.get(
                                "environments", ["development", "staging", "production"]
                            ),
                        )
                        self.definitions[flag_def.name] = flag_def
            except Exception as e:
                print(f"Warning: Failed to load flag definitions: {e}")

    def _load_flag_values(self) -> None:
        """Load feature flag values from environment and files."""
        # Load from environment variables first
        for key, value in os.environ.items():
            if key.startswith("FEATURE_"):
                flag_name = key[8:].lower()  # Remove "FEATURE_" prefix
                self._set_value_from_env(flag_name, value)

        # Load from environment-specific file
        values_file = self.flags_dir / f"{self.environment}.json"
        if values_file.exists():
            try:
                with open(values_file) as f:
                    data = json.load(f)
                    for flag_name, flag_data in data.items():
                        if flag_name in self.definitions:
                            self.values[flag_name] = FeatureFlagValue(
                                name=flag_name,
                                value=flag_data["value"],
                                environment=self.environment,
                                set_by=flag_data.get("set_by", "file"),
                                set_at=datetime.fromisoformat(
                                    flag_data.get("set_at", datetime.now().isoformat())
                                ),
                                expires_at=(
                                    datetime.fromisoformat(flag_data["expires_at"])
                                    if flag_data.get("expires_at")
                                    else None
                                ),
                            )
            except Exception as e:
                print(f"Warning: Failed to load flag values: {e}")

    def _set_value_from_env(self, flag_name: str, env_value: str) -> None:
        """Set flag value from environment variable."""
        if flag_name not in self.definitions:
            return

        flag_def = self.definitions[flag_name]

        try:
            if flag_def.flag_type == FeatureFlagType.BOOLEAN:
                value = env_value.lower() in ("true", "1", "yes", "on")
            elif flag_def.flag_type == FeatureFlagType.INTEGER:
                value = int(env_value)
            elif flag_def.flag_type == FeatureFlagType.FLOAT:
                value = float(env_value)
            elif flag_def.flag_type == FeatureFlagType.LIST:
                value = [item.strip() for item in env_value.split(",")]
            else:  # STRING
                value = env_value

            self.values[flag_name] = FeatureFlagValue(
                name=flag_name, value=value, environment=self.environment, set_by="environment"
            )
        except (ValueError, TypeError):
            print(f"Warning: Invalid environment value for flag {flag_name}: {env_value}")

    def get_flag(self, name: str) -> Any:
        """
        Get the current value of a feature flag.

        Args:
            name: Flag name

        Returns:
            Current flag value or default if not set
        """
        with self._lock:
            # Check if value exists and hasn't expired
            if name in self.values:
                flag_value = self.values[name]
                if flag_value.expires_at is None or flag_value.expires_at > datetime.now():
                    return flag_value.value
                else:
                    # Remove expired flag
                    del self.values[name]

            # Return default value
            if name in self.definitions:
                return self.definitions[name].default_value

            return None

    def set_flag(
        self, name: str, value: Any, set_by: str = "runtime", expires_in: timedelta | None = None
    ) -> bool:
        """
        Set a feature flag value at runtime.

        Args:
            name: Flag name
            value: New value
            set_by: Who/what set the flag
            expires_in: Optional expiration time

        Returns:
            True if set successfully, False otherwise
        """
        with self._lock:
            if name not in self.definitions:
                return False

            flag_def = self.definitions[name]

            # Validate value
            if flag_def.validation_func and not flag_def.validation_func(value):
                return False

            # Check environment compatibility
            if self.environment not in flag_def.environments:
                return False

            # Set the value
            expires_at = datetime.now() + expires_in if expires_in else None
            self.values[name] = FeatureFlagValue(
                name=name,
                value=value,
                environment=self.environment,
                set_by=set_by,
                expires_at=expires_at,
            )

            return True

    def is_enabled(self, name: str) -> bool:
        """Check if a boolean feature flag is enabled."""
        value = self.get_flag(name)
        return bool(value) if value is not None else False

    def get_flags_by_category(self, category: str) -> dict[str, Any]:
        """Get all flags in a specific category."""
        result = {}
        for name, definition in self.definitions.items():
            if definition.category == category:
                result[name] = self.get_flag(name)
        return result

    def get_all_flags(self) -> dict[str, Any]:
        """Get all current flag values."""
        result = {}
        for name in self.definitions:
            result[name] = self.get_flag(name)
        return result

    def save_flags_to_file(self) -> bool:
        """Save current flag values to environment-specific file."""
        values_file = self.flags_dir / f"{self.environment}.json"

        try:
            data = {}
            for name, flag_value in self.values.items():
                data[name] = {
                    "value": flag_value.value,
                    "set_by": flag_value.set_by,
                    "set_at": flag_value.set_at.isoformat(),
                    "expires_at": (
                        flag_value.expires_at.isoformat() if flag_value.expires_at else None
                    ),
                }

            with open(values_file, "w") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving flags to file: {e}")
            return False

    def reload_flags(self) -> None:
        """Reload flags from files and environment."""
        with self._lock:
            self.values.clear()
            self._load_flag_values()

    def get_flag_info(self, name: str) -> dict[str, Any] | None:
        """Get detailed information about a flag."""
        if name not in self.definitions:
            return None

        definition = self.definitions[name]
        current_value = self.get_flag(name)
        flag_value = self.values.get(name)

        return {
            "name": name,
            "current_value": current_value,
            "default_value": definition.default_value,
            "type": definition.flag_type.value,
            "description": definition.description,
            "category": definition.category,
            "requires_restart": definition.requires_restart,
            "dependencies": definition.dependencies,
            "environments": definition.environments,
            "set_by": flag_value.set_by if flag_value else "default",
            "set_at": flag_value.set_at.isoformat() if flag_value else None,
            "expires_at": (
                flag_value.expires_at.isoformat() if flag_value and flag_value.expires_at else None
            ),
        }


# Global feature flag manager
feature_flag_manager = FeatureFlagManager()


# Convenience functions
def get_flag(name: str) -> Any:
    """Get feature flag value."""
    return feature_flag_manager.get_flag(name)


def is_enabled(name: str) -> bool:
    """Check if feature flag is enabled."""
    return feature_flag_manager.is_enabled(name)


def set_flag(name: str, value: Any, set_by: str = "runtime") -> bool:
    """Set feature flag value."""
    return feature_flag_manager.set_flag(name, value, set_by)
