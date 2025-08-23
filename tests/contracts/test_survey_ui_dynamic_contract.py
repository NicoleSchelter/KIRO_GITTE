"""
Contract tests for dynamic survey UI.
Tests the contracts between UI layer and Logic/Service layers.
"""

import pytest
import tempfile
import os
from uuid import uuid4
from pathlib import Path

from src.ui.survey_ui import SurveyUI
from src.logic.survey_logic import SurveyLogic, SurveyDefinition, SurveyQuestion
from src.services.survey_service import SurveyService
from src.data.database import get_session


class TestSurveyUILogicContract:
    """Test contract between Survey UI and Survey Logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.survey_ui = SurveyUI()
        self.pseudonym_id = uuid4()
    
    def create_test_survey_file(self) -> str:
        """Create a test survey CSV file."""
        content = """question_id,question_text,type,options,required
name,What is your name?,text,,true
age,What is your age?,number,,true
style,What is your learning style?,choice,"Visual,Auditory,Kinesthetic",true
subjects,Which subjects interest you?,multi-choice,"Math,Science,Art",false"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name
    
    def test_survey_logic_integration_load_definition(self):
        """Test that UI can load survey definition through logic layer."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        try:
            # Act - Use actual logic layer
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                survey_logic = SurveyLogic(survey_service)
                
                # This should work without mocking
                survey_definition = survey_logic.load_survey_definition(survey_file)
                
                # Assert
                assert isinstance(survey_definition, SurveyDefinition)
                assert survey_definition.survey_id == f"survey_{Path(survey_file).stem}"
                assert len(survey_definition.questions) == 4
                
                # Verify question types
                question_types = [q.type for q in survey_definition.questions]
                assert "text" in question_types
                assert "number" in question_types
                assert "choice" in question_types
                assert "multi-choice" in question_types
                
        finally:
            # Cleanup
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    def test_survey_logic_integration_validate_responses(self):
        """Test that UI can validate responses through logic layer."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        try:
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                survey_logic = SurveyLogic(survey_service)
                
                survey_definition = survey_logic.load_survey_definition(survey_file)
                
                # Valid responses
                valid_responses = {
                    "name": "John Doe",
                    "age": 25,
                    "style": "Visual",
                    "subjects": ["Math", "Science"]
                }
                
                # Act
                validation_result = survey_logic.validate_survey_responses(
                    valid_responses, survey_definition
                )
                
                # Assert
                assert validation_result.is_valid is True
                assert len(validation_result.errors) == 0
                
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    def test_survey_logic_integration_validate_invalid_responses(self):
        """Test that UI properly handles validation errors from logic layer."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        try:
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                survey_logic = SurveyLogic(survey_service)
                
                survey_definition = survey_logic.load_survey_definition(survey_file)
                
                # Invalid responses - missing required fields
                invalid_responses = {
                    "age": "not_a_number",  # Invalid type
                    "style": "InvalidStyle",  # Invalid choice
                    # Missing required "name" field
                }
                
                # Act
                validation_result = survey_logic.validate_survey_responses(
                    invalid_responses, survey_definition
                )
                
                # Assert
                assert validation_result.is_valid is False
                assert len(validation_result.errors) > 0
                
                # Check specific error types
                error_messages = " ".join(validation_result.errors)
                assert "name" in error_messages.lower()  # Missing required field
                assert "age" in error_messages.lower()   # Invalid number
                assert "style" in error_messages.lower() # Invalid choice
                
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)


class TestSurveyUIServiceContract:
    """Test contract between Survey UI and Survey Service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.survey_ui = SurveyUI()
        self.pseudonym_id = uuid4()
    
    def test_survey_service_integration_parse_csv_file(self):
        """Test that UI can parse CSV files through service layer."""
        # Arrange
        content = """question_id,question_text,type,options,required
test_q1,Test Question 1,text,,true
test_q2,Test Question 2,choice,"A,B,C",false"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(content)
            survey_file = tmp_file.name
        
        try:
            # Act - Use actual service layer
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                questions = survey_service.parse_survey_file(survey_file)
                
                # Assert
                assert len(questions) == 2
                
                # Check first question
                q1 = questions[0]
                assert q1.question_id == "test_q1"
                assert q1.question_text == "Test Question 1"
                assert q1.type == "text"
                assert q1.required is True
                assert q1.options is None
                
                # Check second question
                q2 = questions[1]
                assert q2.question_id == "test_q2"
                assert q2.question_text == "Test Question 2"
                assert q2.type == "choice"
                assert q2.required is False
                assert q2.options == ["A", "B", "C"]
                
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    def test_survey_service_integration_parse_excel_file(self):
        """Test that UI can parse Excel files through service layer."""
        pytest.skip("Excel parsing requires pandas and openpyxl - integration test")
    
    def test_survey_service_integration_invalid_file_format(self):
        """Test that service layer properly handles invalid file formats."""
        # Arrange
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write("invalid content")
            invalid_file = tmp_file.name
        
        try:
            # Act & Assert
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                
                with pytest.raises(ValueError, match="Unsupported file format"):
                    survey_service.parse_survey_file(invalid_file)
                    
        finally:
            if os.path.exists(invalid_file):
                os.unlink(invalid_file)
    
    def test_survey_service_integration_missing_columns(self):
        """Test that service layer handles missing required columns."""
        # Arrange - CSV missing required columns
        content = """question_id,question_text
q1,Question 1"""  # Missing 'type' and 'required' columns
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(content)
            invalid_file = tmp_file.name
        
        try:
            # Act & Assert
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                
                with pytest.raises(ValueError, match="Missing required columns"):
                    survey_service.parse_survey_file(invalid_file)
                    
        finally:
            if os.path.exists(invalid_file):
                os.unlink(invalid_file)


class TestSurveyUIDataContract:
    """Test contract between Survey UI and Data layer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.survey_ui = SurveyUI()
        self.pseudonym_id = uuid4()
    
    def test_survey_data_storage_contract(self):
        """Test that UI can store survey data through proper data contracts."""
        # This would test actual database storage
        # For now, we verify the contract exists and can be called
        
        # Arrange
        responses = {
            "name": "Test User",
            "age": 30,
            "style": "Visual"
        }
        
        # Act & Assert - Verify the contract exists
        with get_session() as db_session:
            survey_service = SurveyService(db_session)
            
            # This should not raise an exception (method exists)
            # Actual storage would require proper database setup
            assert hasattr(survey_service, 'store_survey_responses')
            assert callable(survey_service.store_survey_responses)


class TestSurveyUIErrorHandlingContract:
    """Test error handling contracts in Survey UI."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.survey_ui = SurveyUI()
    
    def test_file_not_found_error_contract(self):
        """Test that UI properly handles FileNotFoundError from logic layer."""
        # Act & Assert
        with get_session() as db_session:
            survey_service = SurveyService(db_session)
            survey_logic = SurveyLogic(survey_service)
            
            with pytest.raises(FileNotFoundError):
                survey_logic.load_survey_definition("nonexistent_file.csv")
    
    def test_invalid_survey_format_error_contract(self):
        """Test that UI properly handles ValueError from logic layer."""
        # Arrange - Create invalid survey file
        content = """question_id,question_text,type,options,required
q1,Question 1,invalid_type,,true"""  # Invalid question type
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(content)
            invalid_file = tmp_file.name
        
        try:
            # Act & Assert
            with get_session() as db_session:
                survey_service = SurveyService(db_session)
                survey_logic = SurveyLogic(survey_service)
                
                with pytest.raises(ValueError, match="Invalid question type"):
                    survey_logic.load_survey_definition(invalid_file)
                    
        finally:
            if os.path.exists(invalid_file):
                os.unlink(invalid_file)


if __name__ == "__main__":
    pytest.main([__file__])