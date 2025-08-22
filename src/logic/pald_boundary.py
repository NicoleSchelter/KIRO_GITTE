"""
PALD Boundary Enforcement Logic
Enforces strict boundaries for PALD data to contain only embodiment-related attributes.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PALDBoundaryResult:
    """Result of PALD boundary validation."""
    is_valid: bool
    filtered_data: dict[str, Any]
    rejected_keys: list[str]
    validation_errors: list[str]
    embodiment_detected: bool


class PALDBoundaryEnforcer:
    """Enforces PALD boundaries and validates embodiment-only data."""
    
    def __init__(self, schema_registry=None):
        self.schema_registry = schema_registry
        self._embodiment_deny_list = self._build_deny_list()
    
    def filter_to_pald_attributes(self, data: dict[str, Any]) -> dict[str, Any]:
        """Filter input data to only PALD-valid embodiment attributes."""
        if not isinstance(data, dict):
            return {}
            
        # Get current schema to validate against
        schema = self._get_current_schema()
        
        # Filter out denied keys
        filtered = {}
        for key, value in data.items():
            if key not in self._embodiment_deny_list:
                # Additional validation against schema structure
                if self._is_valid_schema_path(key, schema):
                    filtered[key] = value
                    
        return filtered
    
    def validate_pald_boundary(self, data: dict[str, Any]) -> PALDBoundaryResult:
        """Validate that data contains only embodiment-related attributes."""
        if not isinstance(data, dict):
            return PALDBoundaryResult(
                is_valid=False,
                filtered_data={},
                rejected_keys=[],
                validation_errors=["Input data must be a dictionary"],
                embodiment_detected=False
            )
        
        rejected_keys = []
        validation_errors = []
        embodiment_detected = False
        
        # Check for embodiment indicators
        embodiment_indicators = {
            "global_design_level", "middle_design_level", "detailed_level",
            "design_elements_not_in_PALD", "appearance", "physical_attributes",
            "visual_characteristics", "embodiment_description", "image_caption"
        }
        
        if any(key in data for key in embodiment_indicators):
            embodiment_detected = True
        
        # Check for denied keys
        for key in data.keys():
            if key in self._embodiment_deny_list:
                rejected_keys.append(key)
                validation_errors.append(f"Key '{key}' is not allowed in PALD data (non-embodiment)")
        
        # Filter to valid data
        filtered_data = self.filter_to_pald_attributes(data)
        
        is_valid = len(rejected_keys) == 0 and embodiment_detected
        
        if not embodiment_detected and len(data) > 0:
            validation_errors.append("No embodiment-related attributes detected in data")
        
        return PALDBoundaryResult(
            is_valid=is_valid,
            filtered_data=filtered_data,
            rejected_keys=rejected_keys,
            validation_errors=validation_errors,
            embodiment_detected=embodiment_detected
        )
    
    def is_embodiment_data(self, data: dict[str, Any]) -> bool:
        """Determine if data represents embodiment description/image."""
        result = self.validate_pald_boundary(data)
        return result.embodiment_detected and result.is_valid
    
    def get_embodiment_deny_list(self) -> list[str]:
        """Get list of non-embodiment keys that should be rejected."""
        return list(self._embodiment_deny_list)
    
    def _build_deny_list(self) -> set[str]:
        """Build comprehensive deny list for non-embodiment attributes."""
        return {
            # Survey-related keys
            "survey_completed_at", "survey_version", "survey_skipped",
            "learning_preferences", "interaction_style", "subject_areas",
            "goals", "privacy", "survey_metadata", "learning_style",
            "difficulty_preference", "feedback_style", "pace_preference",
            "communication_style", "personalization_level", "data_sharing_comfort",
            
            # Onboarding-related keys  
            "onboarding_completed_at", "completion_version", "all_steps_completed",
            "step", "step_data", "step_completed", "onboarding_data",
            "current_step", "completed_steps", "progress", "workflow_state",
            
            # User preference keys
            "notification_preferences", "ui_preferences", "accessibility_settings",
            "theme_preferences", "language_preferences", "timezone_preferences",
            
            # System metadata keys
            "data_type", "collected_at", "processing_metadata", "session_metadata",
            "transformation_version", "original_survey_data", "system_generated",
            
            # Non-embodiment content keys
            "chat_history", "conversation_data", "user_messages", "system_responses",
            "session_data", "interaction_logs", "usage_statistics", "performance_metrics"
        }
    
    def _get_current_schema(self) -> dict[str, Any]:
        """Get current schema from registry or fallback."""
        if self.schema_registry:
            try:
                _, schema = self.schema_registry.get_active_schema()
                return schema
            except Exception as e:
                logger.warning(f"Failed to get schema from registry: {e}")
        
        # Fallback to basic embodiment schema
        return {
            "properties": {
                "global_design_level": {"type": "object"},
                "middle_design_level": {"type": "object"},
                "detailed_level": {"type": "object"},
                "design_elements_not_in_PALD": {"type": "array"}
            }
        }
    
    def _is_valid_schema_path(self, key: str, schema: dict[str, Any]) -> bool:
        """Check if key represents a valid path in the PALD schema."""
        if not schema or "properties" not in schema:
            return False
            
        # Check if key is a top-level property in schema
        return key in schema.get("properties", {})