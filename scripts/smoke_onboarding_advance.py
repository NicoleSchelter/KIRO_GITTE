#!/usr/bin/env python3
"""
Smoke test for onboarding advance functionality.
Tests the complete survey flow including preferences and onboarding step advancement.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.data.database import get_session, initialize_database, create_all_tables
from src.services.survey_service import SurveyService
from src.services.preferences_service import PreferencesService
from src.services.onboarding_service import OnboardingService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_user(db_session):
    """Create a test user for the smoke test."""
    from src.data.models import User
    
    test_user = User(
        id=uuid4(),
        username=f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        password_hash="test_hash",
        pseudonym=f"test_pseudo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        role="participant"
    )
    
    db_session.add(test_user)
    db_session.flush()  # Get the ID
    
    logger.info(f"Created test user: {test_user.id}")
    return test_user


def create_sample_survey_data():
    """Create sample survey data for testing."""
    return {
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
        "appearance": {
            "style": "Friendly and approachable", 
            "age_preference": "Adult (30-45)"
        },
        "subject_areas": ["Mathematics", "Science", "Technology"],
        "goals": {
            "learning_goals": "Improve problem-solving skills",
            "motivation_factors": ["Personal growth", "Curiosity and interest"],
        },
        "privacy": {
            "personalization_level": "Moderate",
            "data_sharing_comfort": "Somewhat comfortable",
        },
        "survey_completed_at": datetime.now(),
        "survey_version": "1.0",
        "survey_skipped": False,
    }


def test_complete_survey_flow():
    """Test the complete survey flow with all steps."""
    logger.info("Testing complete survey flow with onboarding advance...")
    
    writes_occurred = []
    
    try:
        with get_session() as db_session:
            # Create test user
            test_user = create_test_user(db_session)
            writes_occurred.append("INSERT users")
            
            # Create sample survey data
            survey_data = create_sample_survey_data()
            
            # Step 1: Save survey response
            survey_service = SurveyService(db_session)
            survey_result = survey_service.save_complete_survey(
                user_id=test_user.id,
                survey_data=survey_data,
                survey_version="1.0"
            )
            writes_occurred.append("INSERT survey_responses")
            logger.info(f"✓ Survey saved with ID: {survey_result.id}")
            
            # Step 2: Save preferences
            preferences_service = PreferencesService(db_session)
            preferences = {
                "learning_style": survey_data.get("learning_preferences", {}).get("learning_style"),
                "difficulty_preference": survey_data.get("learning_preferences", {}).get("difficulty_preference"),
                "communication_style": survey_data.get("interaction_style", {}).get("communication_style"),
                "personalization_level": survey_data.get("privacy", {}).get("personalization_level"),
                "appearance_style": survey_data.get("appearance", {}).get("style"),
                "age_preference": survey_data.get("appearance", {}).get("age_preference"),
                "subject_areas": survey_data.get("subject_areas", []),
                "learning_goals": survey_data.get("goals", {}).get("learning_goals"),
                "motivation_factors": survey_data.get("goals", {}).get("motivation_factors", []),
            }
            
            prefs_result = preferences_service.upsert_preferences(
                user_id=test_user.id,
                preferences=preferences,
                category="onboarding_step_survey"
            )
            writes_occurred.append("INSERT user_preferences")
            logger.info(f"✓ Preferences saved with ID: {prefs_result.id}")
            
            # Step 3: Advance onboarding step
            onboarding_service = OnboardingService(db_session)
            onboarding_result = onboarding_service.advance_onboarding_step(
                user_id=test_user.id,
                completed_step="survey"
            )
            writes_occurred.append("INSERT/UPDATE onboarding_progress")
            logger.info(f"✓ Onboarding advanced: survey -> {onboarding_result.current_step} ({onboarding_result.progress_percentage}%)")
            
            # Verify all data was saved correctly
            logger.info("\n--- Verification ---")
            
            # Check survey response
            retrieved_survey = survey_service.get_user_survey_data(test_user.id)
            if retrieved_survey:
                logger.info(f"✓ Survey data verified: version {retrieved_survey.survey_version}")
            else:
                logger.error("✗ Survey data not found")
                return False, writes_occurred
            
            # Check preferences
            retrieved_prefs = preferences_service.get_user_preferences(test_user.id, "onboarding_step_survey")
            if retrieved_prefs:
                logger.info(f"✓ Preferences verified: {len(retrieved_prefs)} records")
            else:
                logger.error("✗ Preferences not found")
                return False, writes_occurred
            
            # Check onboarding progress
            retrieved_progress = onboarding_service.get_user_progress(test_user.id)
            if retrieved_progress:
                logger.info(f"✓ Onboarding progress verified: {retrieved_progress.current_step} ({retrieved_progress.progress_percentage}%)")
                logger.info(f"✓ Completed steps: {retrieved_progress.completed_steps}")
            else:
                logger.error("✗ Onboarding progress not found")
                return False, writes_occurred
            
            return True, writes_occurred
            
    except Exception as e:
        logger.exception(f"Complete survey flow test failed: {e}")
        return False, writes_occurred


def test_idempotency():
    """Test that re-running the survey completion is idempotent."""
    logger.info("Testing idempotency of survey completion...")
    
    try:
        with get_session() as db_session:
            # Create test user
            test_user = create_test_user(db_session)
            survey_data = create_sample_survey_data()
            
            # Run the flow twice
            for i in range(2):
                logger.info(f"--- Run {i+1} ---")
                
                # Save survey
                survey_service = SurveyService(db_session)
                survey_result = survey_service.save_complete_survey(
                    user_id=test_user.id,
                    survey_data=survey_data,
                    survey_version="1.0"
                )
                
                # Save preferences
                preferences_service = PreferencesService(db_session)
                preferences = {"test": f"run_{i+1}"}
                prefs_result = preferences_service.upsert_preferences(
                    user_id=test_user.id,
                    preferences=preferences,
                    category="onboarding_step_survey"
                )
                
                # Advance onboarding
                onboarding_service = OnboardingService(db_session)
                onboarding_result = onboarding_service.advance_onboarding_step(
                    user_id=test_user.id,
                    completed_step="survey"
                )
                
                logger.info(f"Run {i+1}: Survey ID {survey_result.id}, Prefs ID {prefs_result.id}, Progress {onboarding_result.progress_percentage}%")
            
            # Verify final state
            final_progress = onboarding_service.get_user_progress(test_user.id)
            completed_steps = final_progress.completed_steps or []
            
            if completed_steps.count("survey") == 1:
                logger.info("✓ Idempotency verified: 'survey' appears only once in completed_steps")
                return True
            else:
                logger.error(f"✗ Idempotency failed: 'survey' appears {completed_steps.count('survey')} times")
                return False
                
    except Exception as e:
        logger.exception(f"Idempotency test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    logger.info("Starting onboarding advance smoke tests...")
    
    try:
        # Initialize database
        initialize_database()
        create_all_tables()
        
        # Run tests
        tests = [
            ("Complete Survey Flow", test_complete_survey_flow),
            ("Idempotency Test", test_idempotency),
        ]
        
        results = []
        all_writes = []
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*60}")
            
            if test_name == "Complete Survey Flow":
                success, writes = test_func()
                all_writes.extend(writes)
            else:
                success = test_func()
            
            results.append((test_name, success))
            
            if success:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("SMOKE TEST SUMMARY")
        logger.info(f"{'='*60}")
        
        logger.info("Database writes that occurred:")
        for write in all_writes:
            logger.info(f"  • {write}")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All smoke tests passed!")
            return 0
        else:
            logger.error("💥 Some smoke tests failed!")
            return 1
            
    except Exception as e:
        logger.exception(f"Smoke test setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())