"""
Survey Logic for Dynamic Survey System
Handles survey definition loading, response validation, and processing with comprehensive error handling.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from src.utils.study_error_handler import (
    ErrorContext,
    StudyErrorCategory,
    StudyErrorHandler,
    StudyRetryConfig,
    with_study_error_handling
)

logger = logging.getLogger(__name__)


@dataclass
class SurveyQuestion:
    """Survey question definition."""
    question_id: str
    question_text: str
    type: Literal["text", "number", "choice", "multi-choice"]
    options: Optional[List[str]] = None
    required: bool = True


@dataclass
class SurveyDefinition:
    """Complete survey definition with questions."""
    survey_id: str
    title: str
    description: str
    version: str
    questions: List[SurveyQuestion]


@dataclass
class ValidationResult:
    """Survey validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class SurveyResult:
    """Survey processing result."""
    success: bool
    survey_response_id: Optional[UUID] = None
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class SurveyLogic:
    """Logic layer for dynamic survey system with comprehensive error handling."""
    
    def __init__(self, survey_service):
        """Initialize with survey service dependency and error handling."""
        self.survey_service = survey_service
        self.error_handler = StudyErrorHandler()
        self.retry_config = StudyRetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=10.0,
            retryable_exceptions=(FileNotFoundError, ConnectionError, TimeoutError)
        )
    
    def load_survey_definition(self, survey_file_path: str) -> SurveyDefinition:
        """
        Load survey definition from Excel/CSV file with comprehensive error handling.
        
        Args:
            survey_file_path: Path to survey definition file
            
        Returns:
            SurveyDefinition object
            
        Raises:
            FileNotFoundError: If survey file doesn't exist
            ValueError: If survey file format is invalid
        """
        context = ErrorContext(
            operation="load_survey_definition",
            component="survey_logic",
            metadata={"file_path": survey_file_path}
        )
        
        with self.error_handler.error_boundary(StudyErrorCategory.SURVEY_LOADING, context, self.retry_config):
            try:
                # Validate file exists with fallback strategy
                file_path = Path(survey_file_path)
                if not file_path.exists():
                    # Try to load default survey as fallback
                    default_survey = self._load_default_survey()
                    if default_survey:
                        logger.warning(f"Survey file not found: {survey_file_path}, using default survey")
                        return default_survey
                    else:
                        raise FileNotFoundError(f"Survey file not found: {survey_file_path}")
                
                # Parse survey file using service layer with retry
                questions = self._parse_survey_with_retry(survey_file_path)
                
                # Create survey definition
                survey_definition = SurveyDefinition(
                    survey_id=f"survey_{file_path.stem}",
                    title=f"Survey from {file_path.name}",
                    description="Dynamically loaded survey",
                    version="1.0",
                    questions=questions
                )
                
                # Validate survey definition
                validation_result = self._validate_survey_definition(survey_definition)
                if not validation_result.is_valid:
                    raise ValueError(f"Invalid survey definition: {validation_result.errors}")
                
                logger.info(f"Successfully loaded survey definition with {len(questions)} questions from {survey_file_path}")
                return survey_definition
                
            except Exception as e:
                logger.error(f"Failed to load survey definition from {survey_file_path}: {e}")
                raise
    
    def _parse_survey_with_retry(self, survey_file_path: str, max_retries: int = 3) -> List[SurveyQuestion]:
        """Parse survey file with retry logic for robustness."""
        
        for attempt in range(max_retries):
            try:
                return self.survey_service.parse_survey_file(survey_file_path)
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Failed to parse survey file after {max_retries} attempts: {e}")
                    raise ValueError(f"Survey parsing failed after {max_retries} attempts")
                else:
                    logger.warning(f"Survey parsing attempt {attempt + 1} failed, retrying: {e}")
                    continue
    
    def _load_default_survey(self) -> Optional[SurveyDefinition]:
        """Load a default survey as fallback when main survey file is unavailable."""
        
        try:
            # Create a minimal default survey
            default_questions = [
                SurveyQuestion(
                    question_id="default_1",
                    question_text="How would you rate your overall experience?",
                    type="choice",
                    options=["Excellent", "Good", "Fair", "Poor"],
                    required=True
                ),
                SurveyQuestion(
                    question_id="default_2",
                    question_text="Any additional comments?",
                    type="text",
                    options=None,
                    required=False
                )
            ]
            
            return SurveyDefinition(
                survey_id="default_survey",
                title="Default Survey",
                description="Fallback survey when main survey is unavailable",
                version="1.0",
                questions=default_questions
            )
            
        except Exception as e:
            logger.error(f"Failed to create default survey: {e}")
            return None
    
    def validate_survey_responses(
        self, 
        responses: Dict[str, Any], 
        definition: SurveyDefinition
    ) -> ValidationResult:
        """
        Validate survey responses against survey definition.
        
        Args:
            responses: User responses dictionary
            definition: Survey definition to validate against
            
        Returns:
            ValidationResult with validation status and errors
        """
        errors = []
        warnings = []
        
        try:
            # Check for required questions
            for question in definition.questions:
                if question.required and question.question_id not in responses:
                    errors.append(f"Required question '{question.question_id}' is missing")
                    continue
                
                # Skip validation if question not answered (and not required)
                if question.question_id not in responses:
                    continue
                
                response_value = responses[question.question_id]
                
                # Validate based on question type
                validation_error = self._validate_question_response(question, response_value)
                if validation_error:
                    errors.append(validation_error)
            
            # Check for unexpected responses
            valid_question_ids = {q.question_id for q in definition.questions}
            for response_id in responses:
                if response_id not in valid_question_ids:
                    warnings.append(f"Unexpected response for question '{response_id}'")
            
            is_valid = len(errors) == 0
            
            logger.info(f"Survey response validation completed: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}")
            
            return ValidationResult(
                is_valid=is_valid,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"Error during survey response validation: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=warnings
            )
    
    def process_survey_submission(
        self, 
        pseudonym_id: UUID, 
        responses: Dict[str, Any],
        survey_definition: SurveyDefinition
    ) -> SurveyResult:
        """
        Process survey submission with validation and storage.
        
        Args:
            pseudonym_id: Participant pseudonym ID
            responses: Survey responses
            survey_definition: Survey definition for validation
            
        Returns:
            SurveyResult with processing status
        """
        try:
            # Validate responses
            validation_result = self.validate_survey_responses(responses, survey_definition)
            if not validation_result.is_valid:
                return SurveyResult(
                    success=False,
                    errors=validation_result.errors
                )
            
            # Store survey responses using service layer
            success = self.survey_service.store_survey_responses(
                pseudonym_id=pseudonym_id,
                responses=responses,
                survey_version=survey_definition.version
            )
            
            if success:
                logger.info(f"Successfully processed survey submission for pseudonym {pseudonym_id}")
                return SurveyResult(success=True)
            else:
                return SurveyResult(
                    success=False,
                    errors=["Failed to store survey responses"]
                )
                
        except Exception as e:
            logger.error(f"Error processing survey submission for pseudonym {pseudonym_id}: {e}")
            return SurveyResult(
                success=False,
                errors=[f"Processing error: {str(e)}"]
            )
    
    def _validate_survey_definition(self, definition: SurveyDefinition) -> ValidationResult:
        """
        Validate survey definition structure.
        
        Args:
            definition: Survey definition to validate
            
        Returns:
            ValidationResult with validation status
        """
        errors = []
        warnings = []
        
        # Check basic structure
        if not definition.questions:
            errors.append("Survey must have at least one question")
        
        # Check question IDs are unique
        question_ids = [q.question_id for q in definition.questions]
        if len(question_ids) != len(set(question_ids)):
            errors.append("Question IDs must be unique")
        
        # Validate individual questions
        for question in definition.questions:
            question_errors = self._validate_question_definition(question)
            errors.extend(question_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_question_definition(self, question: SurveyQuestion) -> List[str]:
        """
        Validate individual question definition.
        
        Args:
            question: Question to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required fields
        if not question.question_id:
            errors.append("Question ID is required")
        
        if not question.question_text:
            errors.append(f"Question text is required for question '{question.question_id}'")
        
        # Validate question type
        valid_types = ["text", "number", "choice", "multi-choice"]
        if question.type not in valid_types:
            errors.append(f"Invalid question type '{question.type}' for question '{question.question_id}'")
        
        # Validate options for choice questions
        if question.type in ["choice", "multi-choice"]:
            if not question.options or len(question.options) == 0:
                errors.append(f"Choice question '{question.question_id}' must have options")
            elif len(question.options) < 2:
                errors.append(f"Choice question '{question.question_id}' must have at least 2 options")
        
        return errors
    
    def _validate_question_response(self, question: SurveyQuestion, response_value: Any) -> Optional[str]:
        """
        Validate individual question response.
        
        Args:
            question: Question definition
            response_value: User response value
            
        Returns:
            Error message if validation fails, None if valid
        """
        try:
            if question.type == "text":
                if not isinstance(response_value, str):
                    return f"Question '{question.question_id}' expects text response"
                if len(response_value.strip()) == 0:
                    return f"Question '{question.question_id}' cannot be empty"
            
            elif question.type == "number":
                try:
                    float(response_value)
                except (ValueError, TypeError):
                    return f"Question '{question.question_id}' expects numeric response"
            
            elif question.type == "choice":
                if not isinstance(response_value, str):
                    return f"Question '{question.question_id}' expects single choice response"
                if question.options and response_value not in question.options:
                    return f"Question '{question.question_id}' response must be one of: {question.options}"
            
            elif question.type == "multi-choice":
                if not isinstance(response_value, list):
                    return f"Question '{question.question_id}' expects multiple choice response (list)"
                if question.options:
                    for choice in response_value:
                        if choice not in question.options:
                            return f"Question '{question.question_id}' invalid choice '{choice}'. Must be one of: {question.options}"
            
            return None
            
        except Exception as e:
            return f"Validation error for question '{question.question_id}': {str(e)}"