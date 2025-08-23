"""
Tests for survey logic functionality.
"""

import pytest
from unittest.mock import Mock
from uuid import uuid4
from pathlib import Path
import tempfile
import os

from src.logic.survey_logic import (
    SurveyLogic, 
    SurveyQuestion, 
    SurveyDefinition, 
    ValidationResult, 
    SurveyResult
)


class TestSurveyQuestion:
    """Test SurveyQuestion dataclass."""
    
    def test_survey_question_creation(self):
        """Test creating a survey question."""
        question = SurveyQuestion(
            question_id="q1",
            question_text="What is your name?",
            type="text",
            required=True
        )
        
        assert question.question_id == "q1"
        assert question.question_text == "What is your name?"
        assert question.type == "text"
        assert question.required is True
        assert question.options is None
    
    def test_survey_question_with_options(self):
        """Test creating a choice question with options."""
        question = SurveyQuestion(
            question_id="q2",
            question_text="Choose your favorite color",
            type="choice",
            options=["Red", "Blue", "Green"],
            required=False
        )
        
        assert question.options == ["Red", "Blue", "Green"]
        assert question.required is False


class TestSurveyDefinition:
    """Test SurveyDefinition dataclass."""
    
    def test_survey_definition_creation(self):
        """Test creating a survey definition."""
        questions = [
            SurveyQuestion("q1", "Name?", "text", required=True),
            SurveyQuestion("q2", "Age?", "number", required=True)
        ]
        
        definition = SurveyDefinition(
            survey_id="test_survey",
            title="Test Survey",
            description="A test survey",
            version="1.0",
            questions=questions
        )
        
        assert definition.survey_id == "test_survey"
        assert definition.title == "Test Survey"
        assert len(definition.questions) == 2


class TestSurveyLogic:
    """Test SurveyLogic class."""
    
    @pytest.fixture
    def mock_survey_service(self):
        """Create mock survey service."""
        return Mock()
    
    @pytest.fixture
    def survey_logic(self, mock_survey_service):
        """Create SurveyLogic instance with mock service."""
        return SurveyLogic(mock_survey_service)
    
    @pytest.fixture
    def sample_questions(self):
        """Create sample survey questions."""
        return [
            SurveyQuestion("name", "What is your name?", "text", required=True),
            SurveyQuestion("age", "What is your age?", "number", required=True),
            SurveyQuestion("color", "Favorite color?", "choice", 
                         options=["Red", "Blue", "Green"], required=False),
            SurveyQuestion("hobbies", "Select hobbies", "multi-choice",
                         options=["Reading", "Sports", "Music"], required=False)
        ]
    
    @pytest.fixture
    def sample_survey_definition(self, sample_questions):
        """Create sample survey definition."""
        return SurveyDefinition(
            survey_id="test_survey",
            title="Test Survey",
            description="Test description",
            version="1.0",
            questions=sample_questions
        )
    
    def test_load_survey_definition_success(self, survey_logic, mock_survey_service, sample_questions):
        """Test successful survey definition loading."""
        # Setup mock
        mock_survey_service.parse_survey_file.return_value = sample_questions
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Test loading
            result = survey_logic.load_survey_definition(tmp_path)
            
            # Verify results
            assert isinstance(result, SurveyDefinition)
            assert len(result.questions) == 4
            assert result.version == "1.0"
            mock_survey_service.parse_survey_file.assert_called_once_with(tmp_path)
            
        finally:
            # Cleanup
            os.unlink(tmp_path)
    
    def test_load_survey_definition_file_not_found(self, survey_logic):
        """Test loading survey definition with non-existent file."""
        with pytest.raises(FileNotFoundError):
            survey_logic.load_survey_definition("/nonexistent/file.csv")
    
    def test_load_survey_definition_invalid_questions(self, survey_logic, mock_survey_service):
        """Test loading survey definition with invalid questions."""
        # Setup mock with invalid questions (no question text)
        invalid_questions = [
            SurveyQuestion("", "", "text", required=True)
        ]
        mock_survey_service.parse_survey_file.return_value = invalid_questions
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Test loading should fail validation
            with pytest.raises(ValueError, match="Invalid survey definition"):
                survey_logic.load_survey_definition(tmp_path)
                
        finally:
            # Cleanup
            os.unlink(tmp_path)
    
    def test_validate_survey_responses_valid(self, survey_logic, sample_survey_definition):
        """Test validating valid survey responses."""
        responses = {
            "name": "John Doe",
            "age": "25",
            "color": "Blue",
            "hobbies": ["Reading", "Sports"]
        }
        
        result = survey_logic.validate_survey_responses(responses, sample_survey_definition)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_survey_responses_missing_required(self, survey_logic, sample_survey_definition):
        """Test validating responses with missing required fields."""
        responses = {
            "age": "25"
            # Missing required "name" field
        }
        
        result = survey_logic.validate_survey_responses(responses, sample_survey_definition)
        
        assert result.is_valid is False
        assert any("Required question 'name' is missing" in error for error in result.errors)
    
    def test_validate_survey_responses_invalid_number(self, survey_logic, sample_survey_definition):
        """Test validating responses with invalid number."""
        responses = {
            "name": "John Doe",
            "age": "not_a_number"
        }
        
        result = survey_logic.validate_survey_responses(responses, sample_survey_definition)
        
        assert result.is_valid is False
        assert any("expects numeric response" in error for error in result.errors)
    
    def test_validate_survey_responses_invalid_choice(self, survey_logic, sample_survey_definition):
        """Test validating responses with invalid choice."""
        responses = {
            "name": "John Doe",
            "age": "25",
            "color": "Purple"  # Not in options
        }
        
        result = survey_logic.validate_survey_responses(responses, sample_survey_definition)
        
        assert result.is_valid is False
        assert any("must be one of" in error for error in result.errors)
    
    def test_validate_survey_responses_invalid_multi_choice(self, survey_logic, sample_survey_definition):
        """Test validating responses with invalid multi-choice."""
        responses = {
            "name": "John Doe",
            "age": "25",
            "hobbies": ["Reading", "Invalid_Hobby"]
        }
        
        result = survey_logic.validate_survey_responses(responses, sample_survey_definition)
        
        assert result.is_valid is False
        assert any("invalid choice 'Invalid_Hobby'" in error for error in result.errors)
    
    def test_validate_survey_responses_unexpected_response(self, survey_logic, sample_survey_definition):
        """Test validating responses with unexpected fields."""
        responses = {
            "name": "John Doe",
            "age": "25",
            "unexpected_field": "value"
        }
        
        result = survey_logic.validate_survey_responses(responses, sample_survey_definition)
        
        assert result.is_valid is True  # Should still be valid
        assert any("Unexpected response" in warning for warning in result.warnings)
    
    def test_process_survey_submission_success(self, survey_logic, mock_survey_service, sample_survey_definition):
        """Test successful survey submission processing."""
        pseudonym_id = uuid4()
        responses = {
            "name": "John Doe",
            "age": "25"
        }
        
        # Setup mock
        mock_survey_service.store_survey_responses.return_value = True
        
        # Test processing
        result = survey_logic.process_survey_submission(pseudonym_id, responses, sample_survey_definition)
        
        assert result.success is True
        assert len(result.errors) == 0
        mock_survey_service.store_survey_responses.assert_called_once_with(
            pseudonym_id=pseudonym_id,
            responses=responses,
            survey_version="1.0"
        )
    
    def test_process_survey_submission_validation_failure(self, survey_logic, mock_survey_service, sample_survey_definition):
        """Test survey submission processing with validation failure."""
        pseudonym_id = uuid4()
        responses = {
            # Missing required "name" field
            "age": "25"
        }
        
        # Test processing
        result = survey_logic.process_survey_submission(pseudonym_id, responses, sample_survey_definition)
        
        assert result.success is False
        assert len(result.errors) > 0
        # Should not call store_survey_responses due to validation failure
        mock_survey_service.store_survey_responses.assert_not_called()
    
    def test_process_survey_submission_storage_failure(self, survey_logic, mock_survey_service, sample_survey_definition):
        """Test survey submission processing with storage failure."""
        pseudonym_id = uuid4()
        responses = {
            "name": "John Doe",
            "age": "25"
        }
        
        # Setup mock to return failure
        mock_survey_service.store_survey_responses.return_value = False
        
        # Test processing
        result = survey_logic.process_survey_submission(pseudonym_id, responses, sample_survey_definition)
        
        assert result.success is False
        assert "Failed to store survey responses" in result.errors
    
    def test_validate_question_definition_valid(self, survey_logic):
        """Test validating valid question definition."""
        question = SurveyQuestion("q1", "Test question?", "text", required=True)
        
        errors = survey_logic._validate_question_definition(question)
        
        assert len(errors) == 0
    
    def test_validate_question_definition_missing_id(self, survey_logic):
        """Test validating question definition with missing ID."""
        question = SurveyQuestion("", "Test question?", "text", required=True)
        
        errors = survey_logic._validate_question_definition(question)
        
        assert any("Question ID is required" in error for error in errors)
    
    def test_validate_question_definition_missing_text(self, survey_logic):
        """Test validating question definition with missing text."""
        question = SurveyQuestion("q1", "", "text", required=True)
        
        errors = survey_logic._validate_question_definition(question)
        
        assert any("Question text is required" in error for error in errors)
    
    def test_validate_question_definition_invalid_type(self, survey_logic):
        """Test validating question definition with invalid type."""
        question = SurveyQuestion("q1", "Test?", "invalid_type", required=True)
        
        errors = survey_logic._validate_question_definition(question)
        
        assert any("Invalid question type" in error for error in errors)
    
    def test_validate_question_definition_choice_without_options(self, survey_logic):
        """Test validating choice question without options."""
        question = SurveyQuestion("q1", "Choose?", "choice", options=None, required=True)
        
        errors = survey_logic._validate_question_definition(question)
        
        assert any("must have options" in error for error in errors)
    
    def test_validate_question_definition_choice_insufficient_options(self, survey_logic):
        """Test validating choice question with insufficient options."""
        question = SurveyQuestion("q1", "Choose?", "choice", options=["Only one"], required=True)
        
        errors = survey_logic._validate_question_definition(question)
        
        assert any("must have at least 2 options" in error for error in errors)
    
    def test_validate_question_response_text_valid(self, survey_logic):
        """Test validating valid text response."""
        question = SurveyQuestion("q1", "Name?", "text", required=True)
        
        error = survey_logic._validate_question_response(question, "John Doe")
        
        assert error is None
    
    def test_validate_question_response_text_empty(self, survey_logic):
        """Test validating empty text response."""
        question = SurveyQuestion("q1", "Name?", "text", required=True)
        
        error = survey_logic._validate_question_response(question, "   ")
        
        assert "cannot be empty" in error
    
    def test_validate_question_response_number_valid(self, survey_logic):
        """Test validating valid number response."""
        question = SurveyQuestion("q1", "Age?", "number", required=True)
        
        error = survey_logic._validate_question_response(question, "25")
        assert error is None
        
        error = survey_logic._validate_question_response(question, 25)
        assert error is None
        
        error = survey_logic._validate_question_response(question, 25.5)
        assert error is None
    
    def test_validate_question_response_number_invalid(self, survey_logic):
        """Test validating invalid number response."""
        question = SurveyQuestion("q1", "Age?", "number", required=True)
        
        error = survey_logic._validate_question_response(question, "not_a_number")
        
        assert "expects numeric response" in error
    
    def test_validate_question_response_choice_valid(self, survey_logic):
        """Test validating valid choice response."""
        question = SurveyQuestion("q1", "Color?", "choice", options=["Red", "Blue"], required=True)
        
        error = survey_logic._validate_question_response(question, "Red")
        
        assert error is None
    
    def test_validate_question_response_choice_invalid(self, survey_logic):
        """Test validating invalid choice response."""
        question = SurveyQuestion("q1", "Color?", "choice", options=["Red", "Blue"], required=True)
        
        error = survey_logic._validate_question_response(question, "Green")
        
        assert "must be one of" in error
    
    def test_validate_question_response_multi_choice_valid(self, survey_logic):
        """Test validating valid multi-choice response."""
        question = SurveyQuestion("q1", "Hobbies?", "multi-choice", 
                                options=["Reading", "Sports", "Music"], required=True)
        
        error = survey_logic._validate_question_response(question, ["Reading", "Sports"])
        
        assert error is None
    
    def test_validate_question_response_multi_choice_invalid(self, survey_logic):
        """Test validating invalid multi-choice response."""
        question = SurveyQuestion("q1", "Hobbies?", "multi-choice", 
                                options=["Reading", "Sports", "Music"], required=True)
        
        error = survey_logic._validate_question_response(question, ["Reading", "Invalid"])
        
        assert "invalid choice 'Invalid'" in error
    
    def test_validate_question_response_multi_choice_not_list(self, survey_logic):
        """Test validating multi-choice response that's not a list."""
        question = SurveyQuestion("q1", "Hobbies?", "multi-choice", 
                                options=["Reading", "Sports", "Music"], required=True)
        
        error = survey_logic._validate_question_response(question, "Reading")
        
        assert "expects multiple choice response (list)" in error