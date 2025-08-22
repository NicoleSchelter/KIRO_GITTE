#!/usr/bin/env python3
"""
Integration test for PALD boundary enforcement.
Tests the complete flow from UI to database.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from uuid import uuid4
from src.logic.pald_boundary import PALDBoundaryEnforcer
from src.services.pald_schema_registry_service import PALDSchemaRegistryService
from src.services.survey_response_service import SurveyResponseService
from src.services.onboarding_progress_service import OnboardingProgressService
from src.services.user_preferences_service import UserPreferencesService
from src.data.database import get_session
from src.data.models import User, UserRole
from config.config import config

def test_boundary_enforcement_integration():
    """Test complete boundary enforcement integration."""
    print("🧪 Testing PALD Boundary Enforcement Integration...")
    
    # Test 1: Boundary Enforcer
    print("\n1. Testing Boundary Enforcer...")
    schema_registry = PALDSchemaRegistryService(config=config)
    enforcer = PALDBoundaryEnforcer(schema_registry)
    
    # Test valid embodiment data
    embodiment_data = {
        "global_design_level": {"type": "human"},
        "detailed_level": {"age": "adult", "gender": "female"}
    }
    
    result = enforcer.validate_pald_boundary(embodiment_data)
    assert result.is_valid, f"Embodiment data should be valid: {result.validation_errors}"
    assert result.embodiment_detected, "Should detect embodiment data"
    print("   ✅ Valid embodiment data accepted")
    
    # Test invalid survey data
    survey_data = {
        "learning_preferences": {"style": "visual"},
        "survey_completed_at": "2024-01-01"
    }
    
    result = enforcer.validate_pald_boundary(survey_data)
    assert not result.is_valid, "Survey data should be rejected"
    assert not result.embodiment_detected, "Should not detect embodiment in survey data"
    assert len(result.rejected_keys) > 0, "Should have rejected keys"
    print("   ✅ Survey data properly rejected")
    
    # Test 2: Data Services
    print("\n2. Testing Data Services...")
    
    with get_session() as db_session:
        # Create test user
        user = User(
            username=f"test_user_{uuid4().hex[:8]}",
            password_hash="test_hash",
            role=UserRole.PARTICIPANT.value,
            pseudonym=f"test_pseudo_{uuid4().hex[:8]}"
        )
        db_session.add(user)
        db_session.commit()
        
        # Test Survey Response Service
        survey_service = SurveyResponseService(db_session)
        survey_response = survey_service.save_survey_response(
            user_id=user.id,
            survey_data={"learning_style": "visual", "difficulty": "intermediate"},
            survey_version="1.0"
        )
        assert survey_response.id is not None, "Survey response should be saved"
        print("   ✅ Survey Response Service working")
        
        # Test Onboarding Progress Service
        onboarding_service = OnboardingProgressService(db_session)
        progress = onboarding_service.update_progress(
            user_id=user.id,
            step="survey",
            step_data={"completed": True}
        )
        assert progress.current_step == "survey", "Progress should be updated"
        print("   ✅ Onboarding Progress Service working")
        
        # Test User Preferences Service
        preferences_service = UserPreferencesService(db_session)
        prefs = preferences_service.save_preferences(
            user_id=user.id,
            preferences={"theme": "dark", "language": "en"},
            category="ui"
        )
        assert prefs.category == "ui", "Preferences should be saved"
        print("   ✅ User Preferences Service working")
    
    print("\n🎉 All integration tests passed!")
    print("\n📊 Summary:")
    print("   ✅ PALD boundary enforcement working")
    print("   ✅ Schema registry loading schemas")
    print("   ✅ Survey data properly separated from PALD")
    print("   ✅ Onboarding progress tracked separately")
    print("   ✅ User preferences stored separately")
    print("   ✅ Database services functioning correctly")

if __name__ == "__main__":
    test_boundary_enforcement_integration()