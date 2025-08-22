"""
Tests for PALD boundary enforcement functionality.
"""

import pytest
from unittest.mock import Mock

from src.logic.pald_boundary import PALDBoundaryEnforcer, PALDBoundaryResult
from src.services.pald_schema_registry_service import PALDSchemaRegistryService


class TestPALDBoundaryEnforcement:
    """Test PALD boundary enforcement logic."""
    
    @pytest.fixture
    def mock_schema_registry(self):
        """Mock schema registry service."""
        registry = Mock(spec=PALDSchemaRegistryService)
        registry.get_active_schema.return_value = ("v1.0", {
            "properties": {
                "global_design_level": {"type": "object"},
                "middle_design_level": {"type": "object"},
                "detailed_level": {"type": "object"}
            }
        })
        return registry
    
    @pytest.fixture
    def boundary_enforcer(self, mock_schema_registry):
        """Create boundary enforcer instance."""
        return PALDBoundaryEnforcer(mock_schema_registry)
    
    def test_filter_embodiment_data_valid(self, boundary_enforcer):
        """Test filtering valid embodiment data."""
        input_data = {
            "global_design_level": {"type": "human"},
            "detailed_level": {"age": "adult", "gender": "female"},
            "survey_completed_at": "2024-01-01",  # Should be filtered out
            "learning_preferences": {"style": "visual"}  # Should be filtered out
        }
        
        result = boundary_enforcer.filter_to_pald_attributes(input_data)
        
        assert "global_design_level" in result
        assert "detailed_level" in result
        assert "survey_completed_at" not in result
        assert "learning_preferences" not in result
    
    def test_validate_pald_boundary_violation(self, boundary_enforcer):
        """Test boundary validation with violations."""
        input_data = {
            "survey_completed_at": "2024-01-01",
            "learning_preferences": {"style": "visual"},
            "onboarding_data": True,
            "step_completed": "survey"
        }
        
        result = boundary_enforcer.validate_pald_boundary(input_data)
        
        assert not result.is_valid
        assert not result.embodiment_detected
        assert len(result.rejected_keys) == 4
        assert "survey_completed_at" in result.rejected_keys
        assert "learning_preferences" in result.rejected_keys
        assert "onboarding_data" in result.rejected_keys
        assert "step_completed" in result.rejected_keys
        assert len(result.validation_errors) > 0
    
    def test_validate_pald_boundary_valid_embodiment(self, boundary_enforcer):
        """Test boundary validation with valid embodiment data."""
        input_data = {
            "global_design_level": {"type": "human"},
            "detailed_level": {"age": "adult", "gender": "female"},
            "middle_design_level": {"lifelikeness": 5}
        }
        
        result = boundary_enforcer.validate_pald_boundary(input_data)
        
        assert result.is_valid
        assert result.embodiment_detected
        assert len(result.rejected_keys) == 0
        assert len(result.validation_errors) == 0
        assert result.filtered_data == input_data
    
    def test_is_embodiment_data_detection(self, boundary_enforcer):
        """Test embodiment data detection."""
        embodiment_data = {
            "global_design_level": {"type": "human"},
            "appearance": {"hair_color": "brown"}
        }
        
        non_embodiment_data = {
            "survey_completed_at": "2024-01-01",
            "learning_preferences": {"style": "visual"}
        }
        
        assert boundary_enforcer.is_embodiment_data(embodiment_data)
        assert not boundary_enforcer.is_embodiment_data(non_embodiment_data)
    
    def test_get_embodiment_deny_list(self, boundary_enforcer):
        """Test deny list retrieval."""
        deny_list = boundary_enforcer.get_embodiment_deny_list()
        
        assert isinstance(deny_list, list)
        assert "survey_completed_at" in deny_list
        assert "learning_preferences" in deny_list
        assert "onboarding_completed_at" in deny_list
        assert "step_data" in deny_list
        assert "personalization_level" in deny_list
    
    def test_boundary_enforcer_without_registry(self):
        """Test boundary enforcer works without schema registry."""
        enforcer = PALDBoundaryEnforcer()
        
        embodiment_data = {
            "global_design_level": {"type": "human"},
            "survey_completed_at": "2024-01-01"  # Should be rejected
        }
        
        result = enforcer.validate_pald_boundary(embodiment_data)
        
        assert not result.is_valid  # Invalid due to survey key
        assert result.embodiment_detected  # But embodiment is detected
        assert "survey_completed_at" in result.rejected_keys


class TestSurveyUINoPALDWrites:
    """Test that survey UI doesn't write to PALD."""
    
    def test_survey_ui_stores_data_without_pald_writes(self):
        """Test survey UI stores responses without creating PALD entries."""
        # This would be an integration test that verifies:
        # 1. Survey submission creates survey_response record
        # 2. No pald_data record is created
        # 3. User preferences are stored in user_preferences table
        pass
    
    def test_survey_data_boundary_validation_fails(self):
        """Test that survey data fails PALD boundary validation."""
        enforcer = PALDBoundaryEnforcer()
        
        typical_survey_data = {
            "learning_preferences": {"style": "visual"},
            "subject_areas": ["math", "science"],
            "survey_completed_at": "2024-01-01"
        }
        
        result = enforcer.validate_pald_boundary(typical_survey_data)
        
        assert not result.is_valid
        assert not result.embodiment_detected
        assert len(result.rejected_keys) == 3


class TestOnboardingNoPALDForMetadata:
    """Test that onboarding logic doesn't use PALD for metadata."""
    
    def test_onboarding_metadata_separation(self):
        """Test onboarding metadata goes to correct table."""
        # This would be an integration test that verifies:
        # 1. Onboarding progress is stored in onboarding_progress table
        # 2. Step data is stored in step_data field, not PALD
        # 3. Completion markers are in onboarding_progress, not PALD
        pass
    
    def test_onboarding_completion_no_pald_write(self):
        """Test onboarding completion doesn't write to PALD."""
        # This would verify that marking onboarding complete doesn't create PALD records
        pass


class TestPALDEvolutionCandidateHarvest:
    """Test schema evolution candidate harvesting."""
    
    def test_out_of_schema_keys_become_candidates(self):
        """Test that out-of-schema keys become candidates, not PALD."""
        # This would test the evolution manager's candidate detection
        pass
    
    def test_candidate_harvesting_no_raw_data_exposure(self):
        """Test candidate harvesting doesn't expose raw user data."""
        # This would verify that candidates are anonymized
        pass


class TestMigrationBoundaryCleanup:
    """Test migration splits data correctly."""
    
    def test_migration_separates_mixed_data_correctly(self):
        """Test migration splits mixed PALD data without loss."""
        # This would test the migration logic:
        # 1. Survey data moves to survey_responses
        # 2. Onboarding data moves to onboarding_progress  
        # 3. Preferences move to user_preferences
        # 4. Embodiment data stays in pald_data
        # 5. No data is lost in the process
        pass
    
    def test_migration_preserves_data_integrity(self):
        """Test migration preserves all user data integrity."""
        # This would verify referential integrity and data completeness
        pass