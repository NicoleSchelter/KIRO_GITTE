"""
Unified Survey Service
Single entry-point service for survey data persistence with proper transaction handling.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.utils.jsonify import to_jsonable
from src.data.models import SurveyResponse

logger = logging.getLogger(__name__)


class SurveyService:
    """Unified service for survey data persistence with single transaction handling."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def save_complete_survey(
        self, 
        user_id: UUID, 
        survey_data: dict[str, Any],
        survey_version: str = "1.0"
    ) -> SurveyResponse:
        """
        Save completed survey data with single transaction.
        
        Args:
            user_id: User identifier
            survey_data: Survey response data
            survey_version: Survey version
            
        Returns:
            SurveyResponse object
            
        Raises:
            Exception: If save operation fails
        """
        try:
            # Serialize UUID and datetime objects in survey data
            serialized_data = to_jsonable(survey_data)
            
            # Import here to avoid circular imports
            from src.data.models import User
            
            # Begin transaction
            with self.db_session.begin():
                # Verify user exists
                user = self.db_session.query(User).filter(User.id == user_id).first()
                if not user:
                    raise ValueError(f"User {user_id} not found in database")
                
                # Check if user already has a survey response
                existing = self.db_session.query(SurveyResponse).filter(
                    SurveyResponse.user_id == user_id
                ).first()
                
                if existing:
                    # Update existing response
                    existing.survey_data = serialized_data
                    existing.survey_version = survey_version
                    existing.updated_at = datetime.utcnow()
                    response = existing
                else:
                    # Create new response
                    response = SurveyResponse(
                        user_id=user_id,
                        survey_data=serialized_data,
                        survey_version=survey_version
                    )
                    self.db_session.add(response)
                
                # Flush to get the ID
                self.db_session.flush()
                
                logger.info(f"Successfully saved complete survey for user {user_id}")
                return response
                
        except Exception as e:
            logger.exception(f"Failed to save complete survey for user {user_id}: {e}")
            raise
    
    def stage_survey_data_for_skip(
        self, 
        user_id: UUID, 
        survey_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Stage survey data for skip flow without DB persistence.
        Sets default preferences and returns staged data for session storage.
        
        Args:
            user_id: User identifier
            survey_data: Default survey data
            
        Returns:
            Staged survey data for session storage
        """
        try:
            # Serialize UUID and datetime objects
            serialized_data = to_jsonable(survey_data)
            
            # Set default preferences (non-DB operation)
            self._set_default_preferences(user_id, serialized_data)
            
            logger.info(f"Staged survey data for skip flow for user {user_id}")
            return serialized_data
            
        except Exception as e:
            logger.exception(f"Failed to stage survey data for user {user_id}: {e}")
            raise
    
    def _set_default_preferences(self, user_id: UUID, survey_data: dict[str, Any]) -> None:
        """
        Set default user preferences based on survey data.
        This is a placeholder for preference setting logic.
        
        Args:
            user_id: User identifier
            survey_data: Survey data to extract preferences from
        """
        # Extract preference-relevant data from survey
        preferences = {
            "learning_style": survey_data.get("learning_preferences", {}).get("learning_style"),
            "difficulty_preference": survey_data.get("learning_preferences", {}).get("difficulty_preference"),
            "communication_style": survey_data.get("interaction_style", {}).get("communication_style"),
            "personalization_level": survey_data.get("privacy", {}).get("personalization_level"),
        }
        
        # Log preference setting (actual implementation would set preferences)
        logger.info(f"Set default preferences for user {user_id}: {preferences}")
    
    def get_user_survey_data(self, user_id: UUID) -> SurveyResponse | None:
        """
        Retrieve user's survey response data.
        
        Args:
            user_id: User identifier
            
        Returns:
            SurveyResponse object or None if not found
        """
        try:
            return self.db_session.query(SurveyResponse).filter(
                SurveyResponse.user_id == user_id
            ).first()
        except Exception as e:
            logger.exception(f"Error retrieving survey data for user {user_id}: {e}")
            return None
    
    def upsert_user_preferences(
        self, 
        user_id: UUID, 
        preferences: dict[str, Any],
        category: str = "onboarding_step_survey"
    ) -> bool:
        """
        Upsert user preferences using centralized service.
        
        Args:
            user_id: User identifier
            preferences: Preferences data
            category: Preference category
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from src.services.user_preferences_service import UserPreferencesService
            
            prefs_service = UserPreferencesService(self.db_session)
            return prefs_service.upsert_preferences(
                user_id=user_id,
                category=category,
                prefs=preferences
            )
                
        except Exception as e:
            logger.exception(f"Failed to upsert preferences for user {user_id}, category {category}: {e}")
            return False