#!/usr/bin/env python3
"""
Test script for survey integration with onboarding flow.
"""

import logging
from uuid import uuid4

from src.data.database import get_session
from src.data.repositories import get_user_repository
from src.logic.onboarding import get_onboarding_logic, OnboardingStep
from src.services.survey_response_service import SurveyResponseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_survey_integration():
    """Test survey completion and skipping in onboarding flow."""
    print("🧪 Testing Survey Integration with Onboarding Flow...")
    
    try:
        # Create test user
        from src.data.schemas import UserCreate
        user_repo = get_user_repository()
        
        user_data = UserCreate(
            username=f"test_survey_user_{uuid4().hex[:8]}",
            password="test_password123",
            role="participant"
        )
        test_user = user_repo.create(
            user_data=user_data,
            password_hash="test_hash",
            pseudonym=f"test_survey_pseudo_{uuid4().hex[:8]}"
        )
        print(f"✅ Created test user: {test_user.id}")
        
        # Get onboarding logic
        onboarding_logic = get_onboarding_logic()
        
        # Test 1: Complete survey and advance
        print("\n1. Testing survey completion...")
        
        survey_data = {
            "learning_preferences": {
                "learning_style": "Visual (diagrams, images, charts)",
                "difficulty_preference": "Intermediate",
                "feedback_style": "Encouraging and supportive",
                "pace_preference": "Moderate",
            },
            "interaction_style": {
                "communication_style": "Friendly and casual",
                "personalization_level": "Moderate",
            },
            "appearance": {"style": "Friendly and approachable", "age_preference": "Adult (30-45)"},
            "subject_areas": ["Mathematics", "Science"],
            "goals": {
                "learning_goals": "Improve problem-solving skills",
                "motivation_factors": ["Personal growth", "Curiosity and interest"],
            },
            "privacy": {
                "personalization_level": "Moderate",
                "data_sharing_comfort": "Somewhat comfortable",
            },
            "survey_version": "1.0",
            "survey_skipped": False,
        }
        
        # Save survey data first
        with get_session() as db_session:
            survey_service = SurveyResponseService(db_session)
            survey_response = survey_service.save_survey_response(
                user_id=test_user.id,
                survey_data=survey_data,
                survey_version="1.0"
            )
            print(f"✅ Survey data saved with ID: {survey_response.id}")
        
        # Advance from survey step
        try:
            next_step = onboarding_logic.advance_to_next_step(
                user_id=test_user.id,
                current_step=OnboardingStep.SURVEY,
                step_data=survey_data
            )
            print(f"✅ Advanced to next step: {next_step}")
        except Exception as e:
            print(f"❌ Error advancing from survey step: {e}")
            logger.error(f"Survey advancement error: {e}")
        
        # Test 2: Skip survey and advance
        print("\n2. Testing survey skipping...")
        
        # Create another test user
        user_data_2 = UserCreate(
            username=f"test_skip_user_{uuid4().hex[:8]}",
            role="participant"
        )
        test_user_2 = user_repo.create(
            user_data=user_data_2,
            password_hash="test_hash",
            pseudonym=f"test_skip_pseudo_{uuid4().hex[:8]}"
        )
        print(f"✅ Created second test user: {test_user_2.id}")
        
        # Create default survey data (skipped)
        default_survey_data = {
            "learning_preferences": {
                "learning_style": "Mixed (combination of styles)",
                "difficulty_preference": "Intermediate",
                "feedback_style": "Encouraging and supportive",
                "pace_preference": "Moderate",
            },
            "interaction_style": {
                "communication_style": "Friendly and casual",
                "personalization_level": "Moderate",
            },
            "appearance": {"style": "Friendly and approachable", "age_preference": "Adult (30-45)"},
            "subject_areas": ["General"],
            "goals": {
                "learning_goals": "General learning and improvement",
                "motivation_factors": ["Personal growth", "Curiosity and interest"],
            },
            "privacy": {
                "personalization_level": "Moderate",
                "data_sharing_comfort": "Somewhat comfortable",
            },
            "survey_version": "1.0",
            "survey_skipped": True,
        }
        
        # Save default survey data
        with get_session() as db_session:
            survey_service = SurveyResponseService(db_session)
            survey_response_2 = survey_service.save_survey_response(
                user_id=test_user_2.id,
                survey_data=default_survey_data,
                survey_version="1.0"
            )
            print(f"✅ Default survey data saved with ID: {survey_response_2.id}")
        
        # Advance from survey step (skipped)
        try:
            next_step_2 = onboarding_logic.advance_to_next_step(
                user_id=test_user_2.id,
                current_step=OnboardingStep.SURVEY,
                step_data=default_survey_data
            )
            print(f"✅ Advanced to next step after skip: {next_step_2}")
        except Exception as e:
            print(f"❌ Error advancing from skipped survey step: {e}")
            logger.error(f"Survey skip advancement error: {e}")
        
        # Test 3: Check onboarding state
        print("\n3. Testing onboarding state retrieval...")
        
        try:
            state_1 = onboarding_logic.get_user_onboarding_state(test_user.id)
            print(f"✅ User 1 onboarding state: {state_1['status']} - {state_1['current_step']}")
            
            state_2 = onboarding_logic.get_user_onboarding_state(test_user_2.id)
            print(f"✅ User 2 onboarding state: {state_2['status']} - {state_2['current_step']}")
        except Exception as e:
            print(f"❌ Error getting onboarding state: {e}")
            logger.error(f"Onboarding state error: {e}")
        
        print("\n🎉 Survey integration tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        logger.error(f"Survey integration test error: {e}")
        raise


if __name__ == "__main__":
    test_survey_integration()