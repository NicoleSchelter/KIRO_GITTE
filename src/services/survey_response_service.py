"""
Survey Response Service
Service for managing survey response data separate from PALD.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SurveyResponseService:
    """Service for managing survey response data."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def save_survey_response(
        self, 
        user_id: UUID, 
        survey_data: dict[str, Any],
        survey_version: str = "1.0"
    ) -> 'SurveyResponse':
        """Save user survey response data."""
        try:
            # Import here to avoid circular imports
            from src.data.models import SurveyResponse
            
            # Check if user already has a survey response
            existing = self.db_session.query(SurveyResponse).filter(
                SurveyResponse.user_id == user_id
            ).first()
            
            if existing:
                # Update existing response
                existing.survey_data = survey_data
                existing.survey_version = survey_version
                existing.updated_at = datetime.utcnow()
                response = existing
            else:
                # Create new response
                response = SurveyResponse(
                    user_id=user_id,
                    survey_data=survey_data,
                    survey_version=survey_version
                )
                self.db_session.add(response)
            
            self.db_session.commit()
            logger.info(f"Saved survey response for user {user_id}")
            return response
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error saving survey response for user {user_id}: {e}")
            raise
    
    def get_user_survey_data(self, user_id: UUID) -> 'SurveyResponse | None':
        """Retrieve user's survey response data."""
        try:
            from src.data.models import SurveyResponse
            return self.db_session.query(SurveyResponse).filter(
                SurveyResponse.user_id == user_id
            ).first()
        except Exception as e:
            logger.error(f"Error retrieving survey data for user {user_id}: {e}")
            return None
    
    def update_survey_response(
        self, 
        user_id: UUID, 
        updates: dict[str, Any]
    ) -> 'SurveyResponse':
        """Update existing survey response."""
        existing = self.get_user_survey_data(user_id)
        if not existing:
            raise ValueError(f"No survey response found for user {user_id}")
        
        # Merge updates with existing data
        updated_data = {**existing.survey_data, **updates}
        
        return self.save_survey_response(
            user_id=user_id,
            survey_data=updated_data,
            survey_version=existing.survey_version
        )