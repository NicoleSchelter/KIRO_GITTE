"""
PALD Enhancement configuration and schema loading infrastructure.
Provides runtime schema loading, bias analysis configuration, and enhanced form controls.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class PALDEnhancementConfig:
    """Configuration for PALD enhancement features."""
    
    # Schema management
    schema_file_path: str = "Basic files/pald_schema.json"
    schema_cache_ttl: int = 300  # 5 minutes
    enable_schema_evolution: bool = True
    
    # PALD processing
    mandatory_pald_extraction: bool = True  # Always true
    pald_analysis_deferred: bool = True
    enable_bias_analysis: bool = True
    
    # Bias analysis
    bias_job_batch_size: int = 10
    bias_analysis_timeout: int = 30  # seconds
    enable_age_shift_analysis: bool = True
    enable_gender_conformity_analysis: bool = True
    enable_ethnicity_analysis: bool = True
    enable_occupational_stereotype_analysis: bool = True
    enable_ambivalent_stereotype_analysis: bool = True
    enable_multiple_stereotyping_analysis: bool = True
    
    # Performance
    max_concurrent_bias_jobs: int = 5
    queue_processing_interval: int = 60  # seconds
    
    # Privacy
    data_retention_days: int = 90
    enable_pseudonymization: bool = True
    
    def __post_init__(self):
        """Override with environment variables if provided."""
        # Schema management
        if env_schema_path := os.getenv("PALD_SCHEMA_FILE_PATH"):
            self.schema_file_path = env_schema_path
        if env_schema_ttl := os.getenv("PALD_SCHEMA_CACHE_TTL"):
            self.schema_cache_ttl = int(env_schema_ttl)
        if env_schema_evolution := os.getenv("PALD_ENABLE_SCHEMA_EVOLUTION"):
            self.enable_schema_evolution = env_schema_evolution.lower() == "true"
            
        # PALD processing - mandatory_pald_extraction is always True
        if env_deferred := os.getenv("PALD_ANALYSIS_DEFERRED"):
            self.pald_analysis_deferred = env_deferred.lower() == "true"
        if env_bias_analysis := os.getenv("ENABLE_BIAS_ANALYSIS"):
            self.enable_bias_analysis = env_bias_analysis.lower() == "true"
            
        # Bias analysis settings
        if env_batch_size := os.getenv("BIAS_JOB_BATCH_SIZE"):
            self.bias_job_batch_size = int(env_batch_size)
        if env_timeout := os.getenv("BIAS_ANALYSIS_TIMEOUT"):
            self.bias_analysis_timeout = int(env_timeout)
            
        # Individual bias analysis types
        if env_age_shift := os.getenv("ENABLE_AGE_SHIFT_ANALYSIS"):
            self.enable_age_shift_analysis = env_age_shift.lower() == "true"
        if env_gender := os.getenv("ENABLE_GENDER_CONFORMITY_ANALYSIS"):
            self.enable_gender_conformity_analysis = env_gender.lower() == "true"
        if env_ethnicity := os.getenv("ENABLE_ETHNICITY_ANALYSIS"):
            self.enable_ethnicity_analysis = env_ethnicity.lower() == "true"
        if env_occupational := os.getenv("ENABLE_OCCUPATIONAL_STEREOTYPE_ANALYSIS"):
            self.enable_occupational_stereotype_analysis = env_occupational.lower() == "true"
        if env_ambivalent := os.getenv("ENABLE_AMBIVALENT_STEREOTYPE_ANALYSIS"):
            self.enable_ambivalent_stereotype_analysis = env_ambivalent.lower() == "true"
        if env_multiple := os.getenv("ENABLE_MULTIPLE_STEREOTYPING_ANALYSIS"):
            self.enable_multiple_stereotyping_analysis = env_multiple.lower() == "true"
            
        # Performance settings
        if env_concurrent := os.getenv("MAX_CONCURRENT_BIAS_JOBS"):
            self.max_concurrent_bias_jobs = int(env_concurrent)
        if env_interval := os.getenv("QUEUE_PROCESSING_INTERVAL"):
            self.queue_processing_interval = int(env_interval)
            
        # Privacy settings
        if env_retention := os.getenv("DATA_RETENTION_DAYS"):
            self.data_retention_days = int(env_retention)
        if env_pseudonymization := os.getenv("ENABLE_PSEUDONYMIZATION"):
            self.enable_pseudonymization = env_pseudonymization.lower() == "true"
    
    def validate(self) -> list[str]:
        """Validate configuration settings."""
        errors = []
        
        if not self.mandatory_pald_extraction:
            errors.append("mandatory_pald_extraction must always be True")
            
        if not Path(self.schema_file_path).exists():
            errors.append(f"Schema file not found: {self.schema_file_path}")
            
        if self.bias_job_batch_size <= 0:
            errors.append("bias_job_batch_size must be positive")
            
        if self.bias_analysis_timeout <= 0:
            errors.append("bias_analysis_timeout must be positive")
            
        if self.max_concurrent_bias_jobs <= 0:
            errors.append("max_concurrent_bias_jobs must be positive")
            
        if self.queue_processing_interval <= 0:
            errors.append("queue_processing_interval must be positive")
            
        if self.data_retention_days <= 0:
            errors.append("data_retention_days must be positive")
            
        return errors


class PALDSchemaLoader:
    """Handles runtime loading and validation of PALD schemas."""
    
    def __init__(self, schema_path: str):
        self.schema_path = Path(schema_path)
        self.cached_schema: dict[str, Any] | None = None
        self.last_modified: float | None = None
        self.cache_ttl = 300  # 5 minutes default
        
    def load_schema(self) -> dict[str, Any]:
        """Load schema from file with caching and validation."""
        try:
            # Check if we need to reload the schema
            if self._should_reload_schema():
                logger.info(f"Loading PALD schema from {self.schema_path}")
                
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    schema_data = json.load(f)
                
                # Validate the loaded schema
                if self.validate_schema(schema_data):
                    self.cached_schema = schema_data
                    self.last_modified = self.schema_path.stat().st_mtime
                    logger.info("PALD schema loaded and validated successfully")
                else:
                    logger.error("Schema validation failed, using default schema")
                    return self.get_default_schema()
            
            return self.cached_schema or self.get_default_schema()
            
        except FileNotFoundError:
            logger.error(f"Schema file not found: {self.schema_path}")
            return self.get_default_schema()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema file: {e}")
            return self.get_default_schema()
        except Exception as e:
            logger.error(f"Error loading schema: {e}")
            return self.get_default_schema()
    
    def validate_schema(self, schema: dict[str, Any]) -> bool:
        """Validate schema structure and content."""
        try:
            # Check for required top-level structure
            required_sections = ["global_design_level", "middle_design_level", "detailed_level"]
            
            if not isinstance(schema, dict):
                logger.error("Schema must be a dictionary")
                return False
            
            # Check if schema has properties section (JSON Schema format)
            if "properties" in schema:
                properties = schema["properties"]
                for section in required_sections:
                    if section not in properties:
                        logger.error(f"Missing required section: {section}")
                        return False
            else:
                # Direct schema format
                for section in required_sections:
                    if section not in schema:
                        logger.error(f"Missing required section: {section}")
                        return False
            
            logger.debug("Schema validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Schema validation error: {e}")
            return False
    
    def get_default_schema(self) -> dict[str, Any]:
        """Return fallback schema if file loading fails."""
        logger.info("Using default PALD schema")
        return {
            "global_design_level": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["human", "cartoon", "human_video", "object", "animal", "fantasy_figure"]
                    },
                    "other_characteristics": {
                        "type": "string"
                    }
                }
            },
            "middle_design_level": {
                "type": "object", 
                "properties": {
                    "lifelikeness": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 7
                    },
                    "realism": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 7
                    },
                    "role": {
                        "type": "string"
                    },
                    "competence": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 7
                    }
                }
            },
            "detailed_level": {
                "type": "object",
                "properties": {
                    "age": {
                        "type": ["string", "integer"]
                    },
                    "gender": {
                        "type": "string"
                    },
                    "clothing": {
                        "type": "string"
                    },
                    "weight": {
                        "type": "string"
                    }
                }
            }
        }
    
    def detect_schema_changes(self) -> bool:
        """Check if schema file has been modified."""
        try:
            if not self.schema_path.exists():
                return False
                
            current_mtime = self.schema_path.stat().st_mtime
            return self.last_modified is None or current_mtime > self.last_modified
            
        except Exception as e:
            logger.error(f"Error checking schema file modification: {e}")
            return False
    
    def _should_reload_schema(self) -> bool:
        """Determine if schema should be reloaded."""
        if self.cached_schema is None:
            return True
            
        if self.detect_schema_changes():
            return True
            
        # Check cache TTL
        if self.last_modified is not None:
            cache_age = datetime.now().timestamp() - self.last_modified
            return cache_age > self.cache_ttl
            
        return False
    
    def set_cache_ttl(self, ttl_seconds: int):
        """Set cache time-to-live in seconds."""
        self.cache_ttl = ttl_seconds


class SchemaEvolutionManager:
    """Manages schema evolution and new field integration."""
    
    def __init__(self, schema_loader: PALDSchemaLoader):
        self.schema_loader = schema_loader
        self.field_candidates: list[dict[str, Any]] = []
        
    def queue_new_field(self, field_name: str, field_data: Any, context: str):
        """Queue new field for review and integration."""
        candidate = {
            "field_name": field_name,
            "field_data": field_data,
            "context": context,
            "detected_at": datetime.now().isoformat(),
            "detection_count": 1
        }
        
        # Check if field already exists in candidates
        existing = next((c for c in self.field_candidates if c["field_name"] == field_name), None)
        if existing:
            existing["detection_count"] += 1
            existing["context"] += f"; {context}"
        else:
            self.field_candidates.append(candidate)
            
        logger.info(f"Queued new field candidate: {field_name}")
    
    def validate_against_baseline(self, new_schema: dict[str, Any]) -> dict[str, Any]:
        """Validate evolved schema against baseline."""
        baseline_schema = self.schema_loader.get_default_schema()
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "new_fields": [],
            "modified_fields": []
        }
        
        try:
            # Compare structure
            self._compare_schema_structure(baseline_schema, new_schema, validation_result)
            
        except Exception as e:
            validation_result["is_valid"] = False
            validation_result["errors"].append(f"Schema validation error: {e}")
            
        return validation_result
    
    def apply_governance_rules(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Apply governance rules to field candidates."""
        approved_candidates = []
        
        for candidate in candidates:
            # Simple governance rules - can be extended
            if candidate["detection_count"] >= 3:  # Auto-approve if detected 3+ times
                candidate["auto_approved"] = True
                approved_candidates.append(candidate)
            elif candidate["field_name"].startswith("other_"):  # Auto-approve "other_" fields
                candidate["auto_approved"] = True
                approved_candidates.append(candidate)
            else:
                candidate["requires_manual_review"] = True
                
        return approved_candidates
    
    def _compare_schema_structure(self, baseline: dict[str, Any], new_schema: dict[str, Any], result: dict[str, Any]):
        """Compare schema structures and identify changes."""
        # This is a simplified comparison - can be enhanced for more sophisticated schema evolution
        baseline_fields = self._extract_field_paths(baseline)
        new_fields = self._extract_field_paths(new_schema)
        
        # Find new fields
        for field_path in new_fields:
            if field_path not in baseline_fields:
                result["new_fields"].append(field_path)
                
        # Find modified fields (simplified check)
        for field_path in baseline_fields:
            if field_path in new_fields:
                baseline_field = self._get_field_by_path(baseline, field_path)
                new_field = self._get_field_by_path(new_schema, field_path)
                if baseline_field != new_field:
                    result["modified_fields"].append(field_path)
    
    def _extract_field_paths(self, schema: dict[str, Any], prefix: str = "") -> list[str]:
        """Extract all field paths from schema."""
        paths = []
        
        if isinstance(schema, dict):
            for key, value in schema.items():
                current_path = f"{prefix}.{key}" if prefix else key
                paths.append(current_path)
                
                if isinstance(value, dict) and "properties" in value:
                    paths.extend(self._extract_field_paths(value["properties"], current_path))
                    
        return paths
    
    def _get_field_by_path(self, schema: dict[str, Any], path: str) -> Any:
        """Get field value by dot-separated path."""
        parts = path.split(".")
        current = schema
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
                
        return current


# Initialize PALD enhancement configuration
pald_enhancement_config = PALDEnhancementConfig()

# Initialize schema loader
schema_loader = PALDSchemaLoader(pald_enhancement_config.schema_file_path)

# Initialize schema evolution manager
schema_evolution_manager = SchemaEvolutionManager(schema_loader)