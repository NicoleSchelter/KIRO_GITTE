"""
Unit tests for PALD enhancement configuration and schema loading.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from config.pald_enhancement import (
    PALDEnhancementConfig,
    PALDSchemaLoader,
    SchemaEvolutionManager
)


class TestPALDEnhancementConfig:
    """Test PALD enhancement configuration."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = PALDEnhancementConfig()
        
        assert config.mandatory_pald_extraction is True
        assert config.pald_analysis_deferred is True
        assert config.enable_bias_analysis is True
        assert config.bias_job_batch_size == 10
        assert config.enable_schema_evolution is True
        
    def test_environment_variable_overrides(self):
        """Test configuration override from environment variables."""
        env_vars = {
            "PALD_SCHEMA_FILE_PATH": "/custom/path/schema.json",
            "PALD_SCHEMA_CACHE_TTL": "600",
            "ENABLE_BIAS_ANALYSIS": "false",
            "BIAS_JOB_BATCH_SIZE": "20",
            "MAX_CONCURRENT_BIAS_JOBS": "10"
        }
        
        with patch.dict(os.environ, env_vars):
            config = PALDEnhancementConfig()
            
            assert config.schema_file_path == "/custom/path/schema.json"
            assert config.schema_cache_ttl == 600
            assert config.enable_bias_analysis is False
            assert config.bias_job_batch_size == 20
            assert config.max_concurrent_bias_jobs == 10
    
    def test_mandatory_pald_extraction_always_true(self):
        """Test that mandatory_pald_extraction cannot be disabled."""
        config = PALDEnhancementConfig()
        config.mandatory_pald_extraction = False
        
        errors = config.validate()
        assert "mandatory_pald_extraction must always be True" in errors
    
    def test_configuration_validation_missing_schema_file(self):
        """Test validation with missing schema file."""
        config = PALDEnhancementConfig()
        config.schema_file_path = "/nonexistent/path/schema.json"
        
        errors = config.validate()
        assert any("Schema file not found" in error for error in errors)
    
    def test_configuration_validation_invalid_values(self):
        """Test validation with invalid configuration values."""
        config = PALDEnhancementConfig()
        config.bias_job_batch_size = -1
        config.bias_analysis_timeout = 0
        config.max_concurrent_bias_jobs = -5
        config.data_retention_days = 0
        
        errors = config.validate()
        
        assert "bias_job_batch_size must be positive" in errors
        assert "bias_analysis_timeout must be positive" in errors
        assert "max_concurrent_bias_jobs must be positive" in errors
        assert "data_retention_days must be positive" in errors


class TestPALDSchemaLoader:
    """Test PALD schema loader functionality."""
    
    def test_load_valid_schema_file(self):
        """Test loading a valid schema file."""
        valid_schema = {
            "global_design_level": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"}
                }
            },
            "middle_design_level": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"}
                }
            },
            "detailed_level": {
                "type": "object",
                "properties": {
                    "age": {"type": "string"}
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_schema, f)
            temp_path = f.name
        
        try:
            loader = PALDSchemaLoader(temp_path)
            loaded_schema = loader.load_schema()
            
            assert loaded_schema == valid_schema
            assert loader.cached_schema == valid_schema
            
        finally:
            os.unlink(temp_path)
    
    def test_load_schema_with_json_schema_format(self):
        """Test loading schema in JSON Schema format."""
        json_schema_format = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "global_design_level": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"}
                    }
                },
                "middle_design_level": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"}
                    }
                },
                "detailed_level": {
                    "type": "object",
                    "properties": {
                        "age": {"type": "string"}
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_schema_format, f)
            temp_path = f.name
        
        try:
            loader = PALDSchemaLoader(temp_path)
            loaded_schema = loader.load_schema()
            
            assert loaded_schema == json_schema_format
            
        finally:
            os.unlink(temp_path)
    
    def test_fallback_to_default_schema_on_file_not_found(self):
        """Test fallback to default schema when file is not found."""
        loader = PALDSchemaLoader("/nonexistent/path/schema.json")
        schema = loader.load_schema()
        
        # Should return default schema
        assert "global_design_level" in schema
        assert "middle_design_level" in schema
        assert "detailed_level" in schema
    
    def test_fallback_to_default_schema_on_invalid_json(self):
        """Test fallback to default schema when JSON is invalid."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content")
            temp_path = f.name
        
        try:
            loader = PALDSchemaLoader(temp_path)
            schema = loader.load_schema()
            
            # Should return default schema
            assert "global_design_level" in schema
            assert "middle_design_level" in schema
            assert "detailed_level" in schema
            
        finally:
            os.unlink(temp_path)
    
    def test_schema_validation_success(self):
        """Test successful schema validation."""
        valid_schema = {
            "global_design_level": {"type": "object"},
            "middle_design_level": {"type": "object"},
            "detailed_level": {"type": "object"}
        }
        
        loader = PALDSchemaLoader("dummy_path")
        assert loader.validate_schema(valid_schema) is True
    
    def test_schema_validation_failure_missing_sections(self):
        """Test schema validation failure with missing required sections."""
        invalid_schema = {
            "global_design_level": {"type": "object"}
            # Missing middle_design_level and detailed_level
        }
        
        loader = PALDSchemaLoader("dummy_path")
        assert loader.validate_schema(invalid_schema) is False
    
    def test_schema_validation_failure_not_dict(self):
        """Test schema validation failure when schema is not a dictionary."""
        loader = PALDSchemaLoader("dummy_path")
        assert loader.validate_schema("not a dict") is False
        assert loader.validate_schema([]) is False
        assert loader.validate_schema(None) is False
    
    def test_detect_schema_changes(self):
        """Test schema file modification detection."""
        valid_schema = {
            "global_design_level": {"type": "object"},
            "middle_design_level": {"type": "object"},
            "detailed_level": {"type": "object"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(valid_schema, f)
            temp_path = f.name
        
        try:
            loader = PALDSchemaLoader(temp_path)
            
            # Initially no cached schema
            assert loader.detect_schema_changes() is True
            
            # Load schema to set last_modified
            loader.load_schema()
            
            # No changes detected immediately after loading
            assert loader.detect_schema_changes() is False
            
            # Modify file
            modified_schema = {
                "global_design_level": {"type": "object"},
                "middle_design_level": {"type": "object"},
                "detailed_level": {"type": "object"},
                "new_field": {"type": "string"}
            }
            with open(temp_path, 'w') as f:
                json.dump(modified_schema, f)
            
            # Changes should be detected
            assert loader.detect_schema_changes() is True
            
        finally:
            os.unlink(temp_path)
    
    def test_cache_ttl_functionality(self):
        """Test cache TTL functionality."""
        loader = PALDSchemaLoader("dummy_path")
        
        # Set short TTL
        loader.set_cache_ttl(1)
        assert loader.cache_ttl == 1
        
        # Test TTL affects reload decision
        loader.cached_schema = {"test": "cached"}
        loader.last_modified = 0  # Very old timestamp
        
        assert loader._should_reload_schema() is True


class TestSchemaEvolutionManager:
    """Test schema evolution manager functionality."""
    
    def test_queue_new_field(self):
        """Test queuing new fields for review."""
        loader = PALDSchemaLoader("dummy_path")
        manager = SchemaEvolutionManager(loader)
        
        manager.queue_new_field("new_field", "string", "test context")
        
        assert len(manager.field_candidates) == 1
        candidate = manager.field_candidates[0]
        assert candidate["field_name"] == "new_field"
        assert candidate["field_data"] == "string"
        assert candidate["context"] == "test context"
        assert candidate["detection_count"] == 1
    
    def test_queue_duplicate_field_increments_count(self):
        """Test that queuing the same field multiple times increments count."""
        loader = PALDSchemaLoader("dummy_path")
        manager = SchemaEvolutionManager(loader)
        
        manager.queue_new_field("duplicate_field", "string", "context 1")
        manager.queue_new_field("duplicate_field", "string", "context 2")
        
        assert len(manager.field_candidates) == 1
        candidate = manager.field_candidates[0]
        assert candidate["detection_count"] == 2
        assert "context 1; context 2" in candidate["context"]
    
    def test_apply_governance_rules_auto_approval(self):
        """Test governance rules for auto-approval."""
        loader = PALDSchemaLoader("dummy_path")
        manager = SchemaEvolutionManager(loader)
        
        candidates = [
            {"field_name": "frequent_field", "detection_count": 5},
            {"field_name": "other_custom_field", "detection_count": 1},
            {"field_name": "rare_field", "detection_count": 1}
        ]
        
        approved = manager.apply_governance_rules(candidates)
        
        # Should auto-approve frequent field and other_ field
        assert len(approved) == 2
        approved_names = [c["field_name"] for c in approved]
        assert "frequent_field" in approved_names
        assert "other_custom_field" in approved_names
    
    def test_validate_against_baseline(self):
        """Test schema validation against baseline."""
        loader = PALDSchemaLoader("dummy_path")
        manager = SchemaEvolutionManager(loader)
        
        new_schema = {
            "global_design_level": {"type": "object"},
            "middle_design_level": {"type": "object"},
            "detailed_level": {"type": "object"},
            "new_section": {"type": "object"}  # New field
        }
        
        result = manager.validate_against_baseline(new_schema)
        
        assert result["is_valid"] is True
        assert "new_section" in result["new_fields"]


if __name__ == "__main__":
    pytest.main([__file__])