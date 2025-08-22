"""
PALD Schema Registry Service
Service for managing PALD schema loading, caching, and versioning with runtime file support.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class PALDSchemaRegistryService:
    """Service for managing PALD schema loading, caching, and versioning."""
    
    def __init__(self, db_session: Session = None, config=None):
        self.db_session = db_session
        self.config = config
        self._schema_cache: dict[str, Any] = {}
        self._cache_timestamps: dict[str, float] = {}
        self._file_checksums: dict[str, str] = {}
    
    def get_active_schema(self) -> tuple[str, dict[str, Any]]:
        """Get the currently active PALD schema with caching."""
        schema_file_path = self._get_schema_file_path()
        
        # Try to load from file first
        try:
            if self.detect_schema_file_changes(schema_file_path):
                schema = self.load_schema_from_file(schema_file_path)
                version = self._generate_version_from_file(schema_file_path)
                
                # Cache the schema
                self.cache_schema(version, schema)
                
                # Log schema loading
                checksum = self.get_schema_checksum(schema)
                logger.info(f"Loaded PALD schema version {version} from file, checksum: {checksum}")
                
                return version, schema
                
        except Exception as e:
            logger.warning(f"Failed to load schema from file {schema_file_path}: {e}")
            
        # Fallback to database or embedded schema
        return self._get_fallback_schema()
    
    def load_schema_from_file(self, file_path: str) -> dict[str, Any]:
        """Load schema from external JSON file with validation."""
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Schema file not found: {file_path}")
            
            with open(path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            # Validate schema structure
            validation_result = self.validate_schema_structure(schema)
            if not validation_result["is_valid"]:
                raise ValueError(f"Invalid schema structure: {validation_result['errors']}")
            
            # Update file checksum
            checksum = self.get_schema_checksum(schema)
            self._file_checksums[file_path] = checksum
            
            return schema
            
        except Exception as e:
            logger.error(f"Error loading schema from {file_path}: {e}")
            raise
    
    def validate_schema_structure(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Validate schema structure and content."""
        errors = []
        
        # Check required top-level properties
        if not isinstance(schema, dict):
            errors.append("Schema must be a dictionary")
            return {"is_valid": False, "errors": errors}
        
        if "$schema" not in schema:
            errors.append("Schema must have $schema property")
        
        if "properties" not in schema:
            errors.append("Schema must have properties")
        
        # Validate that it's embodiment-focused
        properties = schema.get("properties", {})
        embodiment_keys = {
            "global_design_level", "middle_design_level", "detailed_level", 
            "design_elements_not_in_PALD"
        }
        
        if not any(key in properties for key in embodiment_keys):
            errors.append("Schema must contain embodiment-related properties")
        
        return {"is_valid": len(errors) == 0, "errors": errors}
    
    def cache_schema(self, version: str, schema: dict[str, Any]) -> None:
        """Cache schema with TTL and modification detection."""
        self._schema_cache[version] = schema
        self._cache_timestamps[version] = time.time()
        
        # Store in database for persistence if available
        if self.db_session:
            try:
                # Import here to avoid circular imports
                from src.data.models import SchemaVersion
                
                existing = self.db_session.query(SchemaVersion).filter(
                    SchemaVersion.version == version
                ).first()
                
                if not existing:
                    checksum = self.get_schema_checksum(schema)
                    schema_version = SchemaVersion(
                        version=version,
                        schema_content=schema,
                        checksum=checksum,
                        is_active=True
                    )
                    
                    # Deactivate other versions
                    self.db_session.query(SchemaVersion).update({"is_active": False})
                    
                    self.db_session.add(schema_version)
                    self.db_session.commit()
            except Exception as e:
                logger.warning(f"Failed to store schema in database: {e}")
    
    def get_schema_checksum(self, schema: dict[str, Any]) -> str:
        """Calculate schema checksum for integrity verification."""
        schema_str = json.dumps(schema, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(schema_str.encode('utf-8')).hexdigest()
    
    def detect_schema_file_changes(self, file_path: str) -> bool:
        """Detect if schema file has been modified since last load."""
        try:
            path = Path(file_path)
            if not path.exists():
                return False
            
            current_mtime = path.stat().st_mtime
            cached_mtime = self._cache_timestamps.get(file_path, 0)
            
            return current_mtime > cached_mtime
            
        except Exception as e:
            logger.warning(f"Error checking file modification time: {e}")
            return True  # Assume changed to trigger reload
    
    def get_fallback_schema(self) -> dict[str, Any]:
        """Return embedded fallback schema if file loading fails."""
        # Return the current embodiment-only schema as embedded fallback
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": ["object", "null"],
            "properties": {
                "global_design_level": {
                    "type": ["object", "null"],
                    "properties": {
                        "type": {
                            "type": ["string", "null"],
                            "enum": ["human", "cartoon", "human_video", "object", "animal", "fantasy_figure"]
                        }
                    },
                    "required": ["type"],
                    "additionalProperties": False
                },
                "middle_design_level": {
                    "type": ["object", "null"],
                    "properties": {
                        "lifelikeness": {"type": ["integer", "null"], "minimum": 1, "maximum": 7},
                        "realism": {"type": ["integer", "null"], "minimum": 1, "maximum": 7}
                    },
                    "additionalProperties": False
                },
                "detailed_level": {
                    "type": ["object", "null"],
                    "properties": {
                        "age": {"type": ["string", "integer", "null"]},
                        "gender": {"type": ["string", "null"]},
                        "clothing": {"type": ["string", "null"]}
                    },
                    "additionalProperties": False
                },
                "design_elements_not_in_PALD": {
                    "type": ["array", "null"],
                    "items": {"type": ["string", "null"]}
                }
            },
            "additionalProperties": False
        }
    
    def _get_fallback_schema(self) -> tuple[str, dict[str, Any]]:
        """Get fallback schema from database or embedded."""
        # Try database first if available
        if self.db_session:
            try:
                from src.data.models import SchemaVersion
                db_schema = self.db_session.query(SchemaVersion).filter(
                    SchemaVersion.is_active == True
                ).first()
                
                if db_schema:
                    return db_schema.version, db_schema.schema_content
            except Exception as e:
                logger.warning(f"Failed to get schema from database: {e}")
        
        # Use embedded fallback
        fallback_schema = self.get_fallback_schema()
        fallback_version = "embedded_v1.0"
        
        logger.info(f"Using embedded fallback schema version {fallback_version}")
        return fallback_version, fallback_schema
    
    def _generate_version_from_file(self, file_path: str) -> str:
        """Generate version string from file path and modification time."""
        try:
            path = Path(file_path)
            mtime = path.stat().st_mtime
            return f"file_{path.stem}_{int(mtime)}"
        except Exception:
            return f"file_{Path(file_path).stem}_unknown"
    
    def _get_schema_file_path(self) -> str:
        """Get schema file path from config or default."""
        if self.config and hasattr(self.config, 'pald_boundary'):
            return self.config.pald_boundary.pald_schema_file_path
        elif self.config and hasattr(self.config, 'pald_schema_file_path'):
            return self.config.pald_schema_file_path
        else:
            return "config/pald_schema.json"