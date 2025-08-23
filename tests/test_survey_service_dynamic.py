"""
Tests for dynamic survey service functionality.
"""

import pytest
import pandas as pd
import tempfile
import os
from uuid import uuid4
from unittest.mock import Mock, patch

from src.services.survey_service import SurveyService
from src.logic.survey_logic import SurveyQuestion


class TestSurveyServiceDynamic:
    """Test dynamic survey functionality in SurveyService."""
    
    @pytest.fixture
    def db_session(self):
        """Create mock database session."""
        return Mock()
    
    @pytest.fixture
    def survey_service(self, db_session):
        """Create SurveyService instance."""
        return SurveyService(db_session)
    
    @pytest.fixture
    def sample_survey_csv_content(self):
        """Create sample CSV content for testing."""
        return """question_id,question_text,type,options,required
name,What is your name?,text,,true
age,What is your age?,number,,true
color,Favorite color?,choice,"Red,Blue,Green",false
hobbies,Select hobbies,multi-choice,"Reading,Sports,Music",false
comments,Any comments?,text,,false"""
    
    @pytest.fixture
    def sample_survey_excel_data(self):
        """Create sample Excel data for testing."""
        return pd.DataFrame({
            'question_id': ['name', 'age', 'color', 'hobbies'],
            'question_text': ['What is your name?', 'What is your age?', 'Favorite color?', 'Select hobbies'],
            'type': ['text', 'number', 'choice', 'multi-choice'],
            'options': ['', '', 'Red,Blue,Green', 'Reading,Sports,Music'],
            'required': [True, True, False, False]
        })
    
    def test_parse_survey_file_csv_success(self, survey_service, sample_survey_csv_content):
        """Test successful CSV file parsing."""
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(sample_survey_csv_content)
            tmp_path = tmp_file.name
        
        try:
            # Test parsing
            questions = survey_service.parse_survey_file(tmp_path)
            
            # Verify results
            assert len(questions) == 5
            
            # Check first question (text)
            assert questions[0].question_id == "name"
            assert questions[0].question_text == "What is your name?"
            assert questions[0].type == "text"
            assert questions[0].options is None
            assert questions[0].required is True
            
            # Check choice question
            color_question = next(q for q in questions if q.question_id == "color")
            assert color_question.type == "choice"
            assert color_question.options == ["Red", "Blue", "Green"]
            assert color_question.required is False
            
            # Check multi-choice question
            hobbies_question = next(q for q in questions if q.question_id == "hobbies")
            assert hobbies_question.type == "multi-choice"
            assert hobbies_question.options == ["Reading", "Sports", "Music"]
            
        finally:
            # Cleanup
            os.unlink(tmp_path)
    
    def test_parse_survey_file_excel_success(self, survey_service, sample_survey_excel_data):
        """Test successful Excel file parsing."""
        # Create temporary Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Write Excel data
            sample_survey_excel_data.to_excel(tmp_path, index=False)
            
            # Test parsing
            questions = survey_service.parse_survey_file(tmp_path)
            
            # Verify results
            assert len(questions) == 4
            assert questions[0].question_id == "name"
            assert questions[1].type == "number"
            assert questions[2].options == ["Red", "Blue", "Green"]
            
        finally:
            # Cleanup
            os.unlink(tmp_path)
    
    def test_parse_survey_file_not_found(self, survey_service):
        """Test parsing non-existent file."""
        with pytest.raises(FileNotFoundError):
            survey_service.parse_survey_file("/nonexistent/file.csv")
    
    def test_parse_survey_file_unsupported_format(self, survey_service):
        """Test parsing unsupported file format."""
        # Create temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with pytest.raises(ValueError, match="Unsupported file format"):
                survey_service.parse_survey_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_parse_survey_file_missing_columns(self, survey_service):
        """Test parsing file with missing required columns."""
        csv_content = """question_id,question_text
q1,What is your name?"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(csv_content)
            tmp_path = tmp_file.name
        
        try:
            with pytest.raises(ValueError, match="Missing required columns"):
                survey_service.parse_survey_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_parse_survey_file_invalid_question_type(self, survey_service):
        """Test parsing file with invalid question type."""
        csv_content = """question_id,question_text,type,options,required
q1,What is your name?,invalid_type,,true"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(csv_content)
            tmp_path = tmp_file.name
        
        try:
            with pytest.raises(ValueError, match="Invalid question type"):
                survey_service.parse_survey_file(tmp_path)
        finally:
            os.unlink(tmp_path)
    
    def test_parse_boolean_field_various_formats(self, survey_service):
        """Test parsing boolean field with various input formats."""
        # Test true values
        assert survey_service._parse_boolean_field(True) is True
        assert survey_service._parse_boolean_field("true") is True
        assert survey_service._parse_boolean_field("TRUE") is True
        assert survey_service._parse_boolean_field("yes") is True
        assert survey_service._parse_boolean_field("1") is True
        assert survey_service._parse_boolean_field("y") is True
        assert survey_service._parse_boolean_field("t") is True
        assert survey_service._parse_boolean_field(1) is True
        
        # Test false values
        assert survey_service._parse_boolean_field(False) is False
        assert survey_service._parse_boolean_field("false") is False
        assert survey_service._parse_boolean_field("FALSE") is False
        assert survey_service._parse_boolean_field("no") is False
        assert survey_service._parse_boolean_field("0") is False
        assert survey_service._parse_boolean_field("n") is False
        assert survey_service._parse_boolean_field("f") is False
        assert survey_service._parse_boolean_field(0) is False
        
        # Test default behavior (should default to True)
        assert survey_service._parse_boolean_field("unknown") is True
        assert survey_service._parse_boolean_field(None) is True
    
    @patch('src.services.survey_service.to_jsonable')
    def test_store_survey_responses_success(self, mock_to_jsonable, survey_service, db_session):
        """Test successful survey response storage."""
        pseudonym_id = uuid4()
        responses = {"name": "John Doe", "age": 25}
        survey_version = "1.0"
        
        # Setup mocks
        mock_to_jsonable.return_value = responses
        mock_existing = Mock()
        db_session.query.return_value.filter.return_value.first.return_value = None
        db_session.begin.return_value.__enter__ = Mock()
        db_session.begin.return_value.__exit__ = Mock(return_value=None)
        
        # Test storage
        result = survey_service.store_survey_responses(pseudonym_id, responses, survey_version)
        
        # Verify results
        assert result is True
        db_session.add.assert_called_once()
        db_session.flush.assert_called_once()
    
    @patch('src.services.survey_service.to_jsonable')
    def test_store_survey_responses_update_existing(self, mock_to_jsonable, survey_service, db_session):
        """Test updating existing survey response."""
        pseudonym_id = uuid4()
        responses = {"name": "John Doe", "age": 25}
        survey_version = "2.0"
        
        # Setup mocks
        mock_to_jsonable.return_value = responses
        mock_existing = Mock()
        db_session.query.return_value.filter.return_value.first.return_value = mock_existing
        db_session.begin.return_value.__enter__ = Mock()
        db_session.begin.return_value.__exit__ = Mock(return_value=None)
        
        # Test storage
        result = survey_service.store_survey_responses(pseudonym_id, responses, survey_version)
        
        # Verify results
        assert result is True
        assert mock_existing.responses == responses
        assert mock_existing.survey_version == survey_version
        db_session.add.assert_not_called()  # Should not add new record
        db_session.flush.assert_called_once()
    
    def test_store_survey_responses_failure(self, survey_service, db_session):
        """Test survey response storage failure."""
        pseudonym_id = uuid4()
        responses = {"name": "John Doe"}
        
        # Setup mock to raise exception
        db_session.begin.side_effect = Exception("Database error")
        
        # Test storage
        result = survey_service.store_survey_responses(pseudonym_id, responses)
        
        # Verify failure
        assert result is False
    
    def test_get_survey_responses_success(self, survey_service, db_session):
        """Test successful survey response retrieval."""
        pseudonym_id = uuid4()
        mock_response = Mock()
        
        # Setup mock
        db_session.query.return_value.filter.return_value.first.return_value = mock_response
        
        # Test retrieval
        result = survey_service.get_survey_responses(pseudonym_id)
        
        # Verify results
        assert result == mock_response
        db_session.query.assert_called_once()
    
    def test_get_survey_responses_not_found(self, survey_service, db_session):
        """Test survey response retrieval when not found."""
        pseudonym_id = uuid4()
        
        # Setup mock
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test retrieval
        result = survey_service.get_survey_responses(pseudonym_id)
        
        # Verify results
        assert result is None
    
    def test_get_survey_responses_failure(self, survey_service, db_session):
        """Test survey response retrieval failure."""
        pseudonym_id = uuid4()
        
        # Setup mock to raise exception
        db_session.query.side_effect = Exception("Database error")
        
        # Test retrieval
        result = survey_service.get_survey_responses(pseudonym_id)
        
        # Verify failure
        assert result is None


class TestSurveyServiceIntegration:
    """Integration tests for survey service with real file parsing."""
    
    @pytest.fixture
    def db_session(self):
        """Create mock database session."""
        return Mock()
    
    @pytest.fixture
    def survey_service(self, db_session):
        """Create SurveyService instance."""
        return SurveyService(db_session)
    
    def test_complete_survey_workflow(self, survey_service):
        """Test complete survey workflow from file parsing to validation."""
        # Create comprehensive survey file
        csv_content = """question_id,question_text,type,options,required
personal_name,What is your full name?,text,,true
personal_age,What is your age?,number,,true
learning_style,What is your preferred learning style?,choice,"Visual,Auditory,Kinesthetic,Reading",true
interests,What are your interests?,multi-choice,"Science,Technology,Arts,Sports,Music",false
feedback,Any additional feedback?,text,,false"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(csv_content)
            tmp_path = tmp_file.name
        
        try:
            # Parse survey file
            questions = survey_service.parse_survey_file(tmp_path)
            
            # Verify comprehensive parsing
            assert len(questions) == 5
            
            # Verify question types and properties
            name_q = next(q for q in questions if q.question_id == "personal_name")
            assert name_q.type == "text"
            assert name_q.required is True
            
            age_q = next(q for q in questions if q.question_id == "personal_age")
            assert age_q.type == "number"
            assert age_q.required is True
            
            style_q = next(q for q in questions if q.question_id == "learning_style")
            assert style_q.type == "choice"
            assert len(style_q.options) == 4
            assert "Visual" in style_q.options
            
            interests_q = next(q for q in questions if q.question_id == "interests")
            assert interests_q.type == "multi-choice"
            assert interests_q.required is False
            assert len(interests_q.options) == 5
            
            feedback_q = next(q for q in questions if q.question_id == "feedback")
            assert feedback_q.type == "text"
            assert feedback_q.required is False
            
        finally:
            os.unlink(tmp_path)
    
    def test_edge_cases_in_parsing(self, survey_service):
        """Test edge cases in survey file parsing."""
        # Test with various edge cases
        csv_content = """question_id,question_text,type,options,required
q1,"Question with, comma",text,,yes
q2,Question with empty options,choice,,no
q3,Question with spaces,multi-choice," Option 1 , Option 2 , Option 3 ",1
q4,Question with number type,number,,0"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(csv_content)
            tmp_path = tmp_file.name
        
        try:
            questions = survey_service.parse_survey_file(tmp_path)
            
            # Verify edge case handling
            assert len(questions) == 4
            
            # Check comma in question text
            q1 = questions[0]
            assert "comma" in q1.question_text
            
            # Check empty options handling
            q2 = questions[1]
            assert q2.options is None
            
            # Check options with spaces
            q3 = questions[2]
            assert q3.options == ["Option 1", "Option 2", "Option 3"]
            
            # Check numeric required field
            q4 = questions[3]
            assert q4.required is False  # 0 should be False
            
        finally:
            os.unlink(tmp_path)