"""
Unified Survey Service
Single entry-point service for survey data persistence with proper transaction handling.
Includes dynamic survey loading from Excel/CSV files.
"""

import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from src.utils.jsonify import to_jsonable
from src.data.models import SurveyResponse

logger = logging.getLogger(__name__)


class SurveyService:
    """Unified service for survey data persistence with single transaction handling and dynamic survey loading."""
    
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
    
    def parse_survey_file(self, file_path: str) -> List['SurveyQuestion']:
        """
        Parse survey definition from Excel/CSV file.
        
        Expected schema: question_id, question_text, type, options, required
        
        Args:
            file_path: Path to survey file
            
        Returns:
            List of SurveyQuestion objects
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        try:
            # Import here to avoid circular imports
            from src.logic.survey_logic import SurveyQuestion
            
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"Survey file not found: {file_path}")
            
            # Read file based on extension
            if file_path_obj.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            elif file_path_obj.suffix.lower() in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_path_obj.suffix}")
            
            # Validate required columns
            required_columns = ['question_id', 'question_text', 'type', 'required']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            questions = []
            for _, row in df.iterrows():
                # Parse options (can be comma-separated string or empty)
                options = None
                if 'options' in df.columns and pd.notna(row['options']):
                    options_str = str(row['options']).strip()
                    if options_str:
                        options = [opt.strip() for opt in options_str.split(',')]
                
                # Parse required field (handle various formats)
                required = self._parse_boolean_field(row['required'])
                
                # Validate question type
                question_type = str(row['type']).lower().strip()
                valid_types = ['text', 'number', 'choice', 'multi-choice']
                if question_type not in valid_types:
                    raise ValueError(f"Invalid question type '{question_type}' for question '{row['question_id']}'. Must be one of: {valid_types}")
                
                question = SurveyQuestion(
                    question_id=str(row['question_id']).strip(),
                    question_text=str(row['question_text']).strip(),
                    type=question_type,
                    options=options,
                    required=required
                )
                questions.append(question)
            
            logger.info(f"Successfully parsed {len(questions)} questions from {file_path}")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to parse survey file {file_path}: {e}")
            raise
    
    def store_survey_responses(
        self, 
        pseudonym_id: UUID, 
        responses: dict[str, Any],
        survey_version: str = "1.0"
    ) -> bool:
        """
        Store survey responses under pseudonym ID for study participation.
        
        Args:
            pseudonym_id: Participant pseudonym ID
            responses: Survey responses dictionary
            survey_version: Survey version
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import here to avoid circular imports
            from src.data.models import StudySurveyResponse
            
            # Serialize responses
            serialized_responses = to_jsonable(responses)
            
            # Begin transaction
            with self.db_session.begin():
                # Check if pseudonym already has survey responses
                existing = self.db_session.query(StudySurveyResponse).filter(
                    StudySurveyResponse.pseudonym_id == pseudonym_id
                ).first()
                
                if existing:
                    # Update existing response
                    existing.responses = serialized_responses
                    existing.survey_version = survey_version
                    existing.completed_at = datetime.utcnow()
                else:
                    # Create new response
                    survey_response = StudySurveyResponse(
                        pseudonym_id=pseudonym_id,
                        survey_version=survey_version,
                        responses=serialized_responses
                    )
                    self.db_session.add(survey_response)
                
                # Flush to ensure data is written
                self.db_session.flush()
            
            logger.info(f"Successfully stored survey responses for pseudonym {pseudonym_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store survey responses for pseudonym {pseudonym_id}: {e}")
            return False
    
    def get_survey_responses(self, pseudonym_id: UUID) -> 'StudySurveyResponse | None':
        """
        Retrieve survey responses for a pseudonym.
        
        Args:
            pseudonym_id: Participant pseudonym ID
            
        Returns:
            StudySurveyResponse object or None if not found
        """
        try:
            from src.data.models import StudySurveyResponse
            
            return self.db_session.query(StudySurveyResponse).filter(
                StudySurveyResponse.pseudonym_id == pseudonym_id
            ).first()
            
        except Exception as e:
            logger.error(f"Failed to retrieve survey responses for pseudonym {pseudonym_id}: {e}")
            return None
    
    def _parse_boolean_field(self, value: Any) -> bool:
        """
        Parse boolean field from various formats.
        
        Args:
            value: Value to parse as boolean
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in ['true', 'yes', '1', 'y', 't']:
                return True
            elif value_lower in ['false', 'no', '0', 'n', 'f']:
                return False
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        # Default to True for required field if unclear
        return True