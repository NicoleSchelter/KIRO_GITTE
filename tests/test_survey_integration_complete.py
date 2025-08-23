"""
Complete integration test for dynamic survey system.
Tests the full workflow from file loading to response processing.
"""

import pytest
import tempfile
import os
from uuid import uuid4
from unittest.mock import Mock

from src.logic.survey_logic import SurveyLogic
from src.services.survey_service import SurveyService


class TestSurveySystemIntegration:
    """Integration tests for complete survey system."""
    
    @pytest.fixture
    def db_session(self):
        """Create mock database session."""
        session = Mock()
        session.begin.return_value.__enter__ = Mock()
        session.begin.return_value.__exit__ = Mock(return_value=None)
        return session
    
    @pytest.fixture
    def survey_service(self, db_session):
        """Create SurveyService instance."""
        return SurveyService(db_session)
    
    @pytest.fixture
    def survey_logic(self, survey_service):
        """Create SurveyLogic instance."""
        return SurveyLogic(survey_service)
    
    @pytest.fixture
    def comprehensive_survey_csv(self):
        """Create comprehensive survey CSV content."""
        return """question_id,question_text,type,options,required
name,What is your full name?,text,,true
age,What is your age?,number,,true
learning_style,What is your preferred learning style?,choice,"Visual,Auditory,Kinesthetic,Reading/Writing",true
interests,Which subjects interest you?,multi-choice,"Math,Science,Art,Music,Sports",false
goals,What are your learning goals?,text,,false
feedback_style,How do you prefer feedback?,choice,"Encouraging,Direct,Detailed",false"""
    
    def test_complete_survey_workflow(self, survey_logic, survey_service, db_session, comprehensive_survey_csv):
        """Test complete survey workflow from loading to processing."""
        # Create temporary survey file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(comprehensive_survey_csv)
            tmp_path = tmp_file.name
        
        try:
            # Step 1: Load survey definition
            survey_definition = survey_logic.load_survey_definition(tmp_path)
            
            # Verify survey definition
            assert survey_definition.survey_id == f"survey_{os.path.basename(tmp_path).split('.')[0]}"
            assert len(survey_definition.questions) == 6
            
            # Step 2: Prepare valid responses
            valid_responses = {
                "name": "John Doe",
                "age": "25",
                "learning_style": "Visual",
                "interests": ["Math", "Science"],
                "goals": "Improve problem-solving skills",
                "feedback_style": "Encouraging"
            }
            
            # Step 3: Validate responses
            validation_result = survey_logic.validate_survey_responses(valid_responses, survey_definition)
            assert validation_result.is_valid is True
            assert len(validation_result.errors) == 0
            
            # Step 4: Process survey submission
            pseudonym_id = uuid4()
            
            # Mock successful storage
            survey_service.store_survey_responses = Mock(return_value=True)
            
            submission_result = survey_logic.process_survey_submission(
                pseudonym_id, valid_responses, survey_definition
            )
            
            # Verify successful processing
            assert submission_result.success is True
            assert len(submission_result.errors) == 0
            
            # Verify service was called correctly
            survey_service.store_survey_responses.assert_called_once_with(
                pseudonym_id=pseudonym_id,
                responses=valid_responses,
                survey_version="1.0"
            )
            
        finally:
            os.unlink(tmp_path)
    
    def test_survey_workflow_with_validation_errors(self, survey_logic, comprehensive_survey_csv):
        """Test survey workflow with validation errors."""
        # Create temporary survey file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(comprehensive_survey_csv)
            tmp_path = tmp_file.name
        
        try:
            # Load survey definition
            survey_definition = survey_logic.load_survey_definition(tmp_path)
            
            # Prepare invalid responses (missing required fields)
            invalid_responses = {
                "age": "not_a_number",  # Invalid number
                "learning_style": "InvalidStyle",  # Invalid choice
                "interests": ["InvalidSubject"]  # Invalid multi-choice
                # Missing required "name" field
            }
            
            # Validate responses
            validation_result = survey_logic.validate_survey_responses(invalid_responses, survey_definition)
            
            # Verify validation failures
            assert validation_result.is_valid is False
            assert len(validation_result.errors) >= 3  # At least 3 errors expected
            
            # Check specific error types
            error_messages = " ".join(validation_result.errors)
            assert "Required question 'name' is missing" in error_messages
            assert "expects numeric response" in error_messages
            assert "must be one of" in error_messages
            
        finally:
            os.unlink(tmp_path)
    
    def test_survey_workflow_with_optional_fields(self, survey_logic, comprehensive_survey_csv):
        """Test survey workflow with only required fields filled."""
        # Create temporary survey file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(comprehensive_survey_csv)
            tmp_path = tmp_file.name
        
        try:
            # Load survey definition
            survey_definition = survey_logic.load_survey_definition(tmp_path)
            
            # Prepare minimal valid responses (only required fields)
            minimal_responses = {
                "name": "Jane Smith",
                "age": "30",
                "learning_style": "Auditory"
                # Optional fields omitted
            }
            
            # Validate responses
            validation_result = survey_logic.validate_survey_responses(minimal_responses, survey_definition)
            
            # Should be valid even with optional fields missing
            assert validation_result.is_valid is True
            assert len(validation_result.errors) == 0
            
        finally:
            os.unlink(tmp_path)
    
    def test_survey_workflow_with_storage_failure(self, survey_logic, survey_service, comprehensive_survey_csv):
        """Test survey workflow with storage failure."""
        # Create temporary survey file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(comprehensive_survey_csv)
            tmp_path = tmp_file.name
        
        try:
            # Load survey definition
            survey_definition = survey_logic.load_survey_definition(tmp_path)
            
            # Prepare valid responses
            valid_responses = {
                "name": "Test User",
                "age": "25",
                "learning_style": "Visual"
            }
            
            # Mock storage failure
            survey_service.store_survey_responses = Mock(return_value=False)
            
            # Process survey submission
            pseudonym_id = uuid4()
            submission_result = survey_logic.process_survey_submission(
                pseudonym_id, valid_responses, survey_definition
            )
            
            # Verify failure handling
            assert submission_result.success is False
            assert "Failed to store survey responses" in submission_result.errors
            
        finally:
            os.unlink(tmp_path)
    
    def test_survey_question_type_validation_comprehensive(self, survey_logic):
        """Test comprehensive question type validation."""
        # Create survey with all question types
        all_types_csv = """question_id,question_text,type,options,required
text_q,Enter text,text,,true
number_q,Enter number,number,,true
choice_q,Choose one,choice,"A,B,C",true
multi_q,Choose multiple,multi-choice,"X,Y,Z",true"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(all_types_csv)
            tmp_path = tmp_file.name
        
        try:
            # Load survey definition
            survey_definition = survey_logic.load_survey_definition(tmp_path)
            
            # Test valid responses for all types
            valid_responses = {
                "text_q": "Sample text response",
                "number_q": "42",
                "choice_q": "B",
                "multi_q": ["X", "Z"]
            }
            
            validation_result = survey_logic.validate_survey_responses(valid_responses, survey_definition)
            assert validation_result.is_valid is True
            
            # Test invalid responses for all types
            invalid_responses = {
                "text_q": "",  # Empty text
                "number_q": "not_a_number",  # Invalid number
                "choice_q": "D",  # Invalid choice
                "multi_q": "not_a_list"  # Invalid multi-choice format
            }
            
            validation_result = survey_logic.validate_survey_responses(invalid_responses, survey_definition)
            assert validation_result.is_valid is False
            assert len(validation_result.errors) == 4  # One error per question
            
        finally:
            os.unlink(tmp_path)
    
    def test_survey_definition_validation_edge_cases(self, survey_logic, survey_service):
        """Test survey definition validation with edge cases."""
        # Test survey with invalid structure
        invalid_csv = """question_id,question_text,type,options,required
,Missing ID,text,,true
q2,,invalid_type,,true
choice_no_opts,Choose,choice,,true"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(invalid_csv)
            tmp_path = tmp_file.name
        
        try:
            # Should raise ValueError due to validation failures (either from parsing or validation)
            with pytest.raises(ValueError):
                survey_logic.load_survey_definition(tmp_path)
                
        finally:
            os.unlink(tmp_path)