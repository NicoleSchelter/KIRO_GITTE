"""
Configuration migration utilities for UX enhancements.
Helps migrate existing configurations to include new UX features.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class UXConfigMigration:
    """Handles migration of configuration files for UX enhancements."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration migration.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config_path = config_path or self._find_config_file()
        self.backup_path = None

    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in common locations."""
        possible_paths = [
            "config.json",
            "config/config.json",
            ".env",
            "docker-compose.yml",
            "docker-compose.override.yml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None

    def create_backup(self) -> bool:
        """
        Create a backup of the current configuration.
        
        Returns:
            bool: True if backup was created successfully
        """
        if not self.config_path or not os.path.exists(self.config_path):
            logger.warning("No configuration file found to backup")
            return False

        try:
            backup_name = f"{self.config_path}.backup.{int(os.path.getmtime(self.config_path))}"
            self.backup_path = backup_name
            
            with open(self.config_path, 'r') as src, open(backup_name, 'w') as dst:
                dst.write(src.read())
            
            logger.info(f"Configuration backup created: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create configuration backup: {e}")
            return False

    def migrate_environment_variables(self) -> Dict[str, str]:
        """
        Generate environment variables for UX enhancements.
        
        Returns:
            Dict of environment variables to set
        """
        env_vars = {
            # Image isolation settings
            "IMAGE_ISOLATION_ENABLED": "true",
            "IMAGE_ISOLATION_CONFIDENCE_THRESHOLD": "0.7",
            
            # Image correction settings
            "IMAGE_CORRECTION_ENABLED": "true",
            "IMAGE_CORRECTION_TIMEOUT": "300",
            
            # Tooltip settings
            "TOOLTIP_ENABLED": "true",
            "TOOLTIP_SHOW_DELAY": "500",
            
            # Prerequisite settings
            "PREREQUISITE_CHECKS_ENABLED": "true",
            "PREREQUISITE_CACHE_TTL": "300",
            
            # UX audit settings
            "UX_AUDIT_ENABLED": "true",
            "UX_AUDIT_RETENTION_DAYS": "90",
            
            # Feature flags
            "FEATURE_ENABLE_IMAGE_ISOLATION": "true",
            "FEATURE_ENABLE_IMAGE_QUALITY_DETECTION": "true",
            "FEATURE_ENABLE_IMAGE_CORRECTION_DIALOG": "true",
            "FEATURE_ENABLE_TOOLTIP_SYSTEM": "true",
            "FEATURE_ENABLE_PREREQUISITE_CHECKS": "true",
            "FEATURE_ENABLE_UX_AUDIT_LOGGING": "true",
        }
        
        return env_vars

    def migrate_docker_compose(self, compose_path: str) -> bool:
        """
        Add UX enhancement environment variables to docker-compose file.
        
        Args:
            compose_path: Path to docker-compose file
            
        Returns:
            bool: True if migration was successful
        """
        try:
            import yaml
            
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            # Find the main service (usually 'app' or 'gitte')
            service_name = None
            for name in ['app', 'gitte', 'web', 'api']:
                if name in compose_data.get('services', {}):
                    service_name = name
                    break
            
            if not service_name:
                logger.error("Could not find main service in docker-compose file")
                return False
            
            service = compose_data['services'][service_name]
            
            # Add environment variables
            if 'environment' not in service:
                service['environment'] = {}
            
            env_vars = self.migrate_environment_variables()
            service['environment'].update(env_vars)
            
            # Write back to file
            with open(compose_path, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False)
            
            logger.info(f"Updated docker-compose file: {compose_path}")
            return True
            
        except ImportError:
            logger.error("PyYAML is required to migrate docker-compose files")
            return False
        except Exception as e:
            logger.error(f"Failed to migrate docker-compose file: {e}")
            return False

    def migrate_env_file(self, env_path: str = ".env") -> bool:
        """
        Add UX enhancement variables to .env file.
        
        Args:
            env_path: Path to .env file
            
        Returns:
            bool: True if migration was successful
        """
        try:
            # Read existing .env file if it exists
            existing_vars = {}
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            existing_vars[key.strip()] = value.strip()
            
            # Add new UX enhancement variables
            new_vars = self.migrate_environment_variables()
            
            # Only add variables that don't already exist
            vars_to_add = {}
            for key, value in new_vars.items():
                if key not in existing_vars:
                    vars_to_add[key] = value
            
            if not vars_to_add:
                logger.info("All UX enhancement variables already exist in .env file")
                return True
            
            # Append new variables to .env file
            with open(env_path, 'a') as f:
                f.write("\n# UX Enhancement Configuration\n")
                for key, value in vars_to_add.items():
                    f.write(f"{key}={value}\n")
            
            logger.info(f"Added {len(vars_to_add)} UX enhancement variables to {env_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate .env file: {e}")
            return False

    def generate_config_template(self, output_path: str = "ux_config_template.json") -> bool:
        """
        Generate a JSON configuration template for UX enhancements.
        
        Args:
            output_path: Path to write the template file
            
        Returns:
            bool: True if template was generated successfully
        """
        try:
            template = {
                "image_isolation": {
                    "enabled": True,
                    "detection_confidence_threshold": 0.7,
                    "edge_refinement_enabled": True,
                    "background_removal_method": "rembg",
                    "fallback_to_original": True,
                    "max_processing_time": 10,
                    "output_format": "PNG",
                    "uniform_background_color": [255, 255, 255]
                },
                "image_correction": {
                    "enabled": True,
                    "auto_show_dialog": True,
                    "timeout_seconds": 300,
                    "allow_manual_crop": True,
                    "allow_regeneration": True,
                    "save_correction_history": True,
                    "learning_from_corrections": True
                },
                "tooltip": {
                    "enabled": True,
                    "show_delay_ms": 500,
                    "hide_delay_ms": 200,
                    "max_width": 300,
                    "position": "auto",
                    "theme": "default",
                    "track_interactions": True,
                    "accessibility_mode": False
                },
                "prerequisite": {
                    "enabled": True,
                    "cache_ttl_seconds": 300,
                    "parallel_execution": True,
                    "timeout_seconds": 30,
                    "retry_attempts": 2,
                    "fail_on_required": True,
                    "warn_on_recommended": True,
                    "ignore_optional": False
                },
                "ux_audit": {
                    "enabled": True,
                    "log_tooltip_interactions": True,
                    "log_correction_actions": True,
                    "log_prerequisite_checks": True,
                    "log_workflow_events": True,
                    "retention_days": 90,
                    "anonymize_data": False
                },
                "feature_flags": {
                    "enable_image_isolation": True,
                    "enable_image_quality_detection": True,
                    "enable_image_correction_dialog": True,
                    "enable_tooltip_system": True,
                    "enable_prerequisite_checks": True,
                    "enable_ux_audit_logging": True
                }
            }
            
            with open(output_path, 'w') as f:
                json.dump(template, f, indent=2)
            
            logger.info(f"Configuration template generated: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate configuration template: {e}")
            return False

    def validate_migration(self) -> Dict[str, Any]:
        """
        Validate that migration was successful.
        
        Returns:
            Dict with validation results
        """
        results = {
            "valid": True,
            "issues": [],
            "recommendations": []
        }
        
        # Check if backup was created
        if self.backup_path and os.path.exists(self.backup_path):
            results["backup_created"] = True
        else:
            results["backup_created"] = False
            results["recommendations"].append("Consider creating a configuration backup")
        
        # Check environment variables
        env_vars = self.migrate_environment_variables()
        missing_vars = []
        
        for var_name in env_vars.keys():
            if not os.getenv(var_name):
                missing_vars.append(var_name)
        
        if missing_vars:
            results["valid"] = False
            results["issues"].append(f"Missing environment variables: {missing_vars}")
        
        # Check for common configuration issues
        if os.getenv("IMAGE_ISOLATION_ENABLED") == "true" and not os.getenv("FEATURE_ENABLE_IMAGE_ISOLATION"):
            results["issues"].append(
                "Image isolation is enabled but feature flag is not set"
            )
        
        return results

    def rollback(self) -> bool:
        """
        Rollback configuration changes using backup.
        
        Returns:
            bool: True if rollback was successful
        """
        if not self.backup_path or not os.path.exists(self.backup_path):
            logger.error("No backup file found for rollback")
            return False
        
        try:
            with open(self.backup_path, 'r') as src, open(self.config_path, 'w') as dst:
                dst.write(src.read())
            
            logger.info(f"Configuration rolled back from backup: {self.backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback configuration: {e}")
            return False


def migrate_ux_config(config_type: str = "env", config_path: Optional[str] = None) -> bool:
    """
    Convenience function to migrate UX configuration.
    
    Args:
        config_type: Type of configuration to migrate ("env", "docker", "template")
        config_path: Optional path to configuration file
        
    Returns:
        bool: True if migration was successful
    """
    migration = UXConfigMigration(config_path)
    
    # Create backup first
    migration.create_backup()
    
    try:
        if config_type == "env":
            return migration.migrate_env_file()
        elif config_type == "docker":
            return migration.migrate_docker_compose(config_path or "docker-compose.yml")
        elif config_type == "template":
            return migration.generate_config_template()
        else:
            logger.error(f"Unknown configuration type: {config_type}")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Attempt rollback
        migration.rollback()
        return False