#!/usr/bin/env python3
"""
Smoke test for survey save functionality.
Tests both complete survey and skip survey flows.
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


def create_sample_survey_data(completed: bool = True):
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
        "survey_skipped": not completed,
    }


def test_complete_survey_flow():
    """Test the complete survey flow."""
    logger.info("Testing complete survey flow...")
    
    try:
        with get_session() as db_session:
            # Create test user
            test_user = create_test_user(db_session)
            
            # Create survey service
            survey_service = SurveyService(db_session)
            
            # Create sample survey data
            survey_data = create_sample_survey_data(completed=True)
            
            # Save complete survey
            result = survey_service.save_complete_survey(
                user_id=test_user.id,
                survey_data=survey_data,
                survey_version="1.0"
            )
            
            logger.info(f"Complete survey saved successfully with ID: {result.id}")
            
            # Verify the data was saved
            retrieved = survey_service.get_user_survey_data(test_user.id)
            if retrieved:
                logger.info(f"Survey data retrieved successfully: {retrieved.survey_version}")
                logger.info(f"Survey skipped: {retrieved.survey_data.get('survey_skipped', False)}")
                return True
            else:
                logger.error("Failed to retrieve saved survey data")
                return False
                
    except Exception as e:
        logger.exception(f"Complete survey flow test failed: {e}")
        return False


def test_skip_survey_flow():
    """Test the skip survey flow."""
    logger.info("Testing skip survey flow...")
    
    try:
        with get_session() as db_session:
            # Create test user
            test_user = create_test_user(db_session)
            
            # Create survey service
            survey_service = SurveyService(db_session)
            
            # Create default survey data
            survey_data = create_sample_survey_data(completed=False)
            
            # Stage survey data for skip (no DB persistence)
            staged_data = survey_service.stage_survey_data_for_skip(
                user_id=test_user.id,
                survey_data=survey_data
            )
            
            logger.info("Skip survey flow completed successfully")
            logger.info(f"Staged data contains survey_skipped: {staged_data.get('survey_skipped', False)}")
            
            # Verify no survey data was persisted to DB
            retrieved = survey_service.get_user_survey_data(test_user.id)
            if retrieved is None:
                logger.info("Confirmed: No survey data persisted to DB for skip flow")
                return True
            else:
                logger.error("Unexpected: Survey data was persisted for skip flow")
                return False
                
    except Exception as e:
        logger.exception(f"Skip survey flow test failed: {e}")
        return False


def test_uuid_datetime_serialization():
    """Test UUID and datetime serialization."""
    logger.info("Testing UUID and datetime serialization...")
    
    try:
        from src.utils.jsonify import to_jsonable
        
        test_data = {
            "user_id": uuid4(),
            "created_at": datetime.now(),
            "nested": {
                "another_uuid": uuid4(),
                "another_date": datetime.now().date(),
                "list_with_uuids": [uuid4(), uuid4()]
            }
        }
        
        serialized = to_jsonable(test_data)
        
        # Check that UUIDs and datetimes were converted to strings
        assert isinstance(serialized["user_id"], str)
        assert isinstance(serialized["created_at"], str)
        assert isinstance(serialized["nested"]["another_uuid"], str)
        assert isinstance(serialized["nested"]["another_date"], str)
        assert all(isinstance(item, str) for item in serialized["nested"]["list_with_uuids"])
        
        logger.info("UUID and datetime serialization test passed")
        return True
        
    except Exception as e:
        logger.exception(f"Serialization test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    logger.info("Starting survey save smoke tests...")
    
    try:
        # Initialize database
        initialize_database()
        create_all_tables()
        
        # Run tests
        tests = [
            ("UUID/DateTime Serialization", test_uuid_datetime_serialization),
            ("Complete Survey Flow", test_complete_survey_flow),
            ("Skip Survey Flow", test_skip_survey_flow),
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            success = test_func()
            results.append((test_name, success))
            
            if success:
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        
        # Summary
        logger.info(f"\n{'='*50}")
        logger.info("SMOKE TEST SUMMARY")
        logger.info(f"{'='*50}")
        
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