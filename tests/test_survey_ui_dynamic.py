"""
Unit tests for enhanced dynamic survey UI functionality.
Tests dynamic survey rendering, validation, and submission.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
from pathlib import Path

from src.ui.survey_ui import SurveyUI
from src.logic.survey_logic import SurveyDefinition, SurveyQuestion, ValidationResult, SurveyResult


class TestSurveyUIDynamic:
    """Test cases for dynamic survey UI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.survey_ui = SurveyUI()
        self.pseudonym_id = uuid4()
        
        # Create sample survey definition
        self.sample_questions = [
            SurveyQuestion(
                question_id="name",
                question_text="What is your name?",
                type="text",
                required=True
            ),
            SurveyQuestion(
                question_id="age",
                question_text="What is your age?",
                type="number",
                required=True
            ),
            SurveyQuestion(
                question_id="learning_style",
                question_text="What is your learning style?",
                type="choice",
                options=["Visual", "Auditory", "Kinesthetic"],
                required=True
            ),
            SurveyQuestion(
                question_id="subjects",
                question_text="Which subjects interest you?",
                type="multi-choice",
                options=["Math", "Science", "Art"],
                required=False
            )
        ]
        
        self.sample_definition = SurveyDefinition(
            survey_id="test_survey",
            title="Test Survey",
            description="A test survey",
            version="1.0",
            questions=self.sample_questions
        )
    
    def create_temp_survey_file(self, content: str) -> str:
        """Create temporary survey file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name
    
    @patch('src.ui.survey_ui.SurveyLogic')
    @patch('src.ui.survey_ui.SurveyService')
    @patch('src.ui.survey_ui.get_session')
    def test_get_survey_logic_creates_instances(self, mock_get_session, mock_service_class, mock_logic_class):
        """Test that _get_survey_logic creates proper instances."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        
        # Act
        result = self.survey_ui._get_survey_logic()
        
        # Assert
        mock_get_session.assert_called_once()
        mock_service_class.assert_called_once_with(mock_session)
        mock_logic_class.assert_called_once_with(mock_service)
        assert result == mock_logic
    
    @patch('src.ui.survey_ui.st')
    @patch('src.ui.survey_ui.Path')
    def test_render_dynamic_survey_file_not_found_with_fallback(self, mock_path, mock_st):
        """Test dynamic survey rendering when file not found with fallback enabled."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        with patch('src.ui.survey_ui.config') as mock_config:
            mock_config.SURVEY_FALLBACK_ENABLED = True
            
            with patch.object(self.survey_ui, 'render_personalization_survey') as mock_fallback:
                mock_fallback.return_value = {"fallback": True}
                
                # Act
                result = self.survey_ui.render_dynamic_survey(self.pseudonym_id, "nonexistent.csv")
                
                # Assert
                mock_st.error.assert_called_once()
                mock_st.info.assert_called_once()
                mock_fallback.assert_called_once_with(self.pseudonym_id)
                assert result == {"fallback": True}
    
    @patch('src.ui.survey_ui.st')
    @patch('src.ui.survey_ui.Path')
    def test_render_dynamic_survey_file_not_found_no_fallback(self, mock_path, mock_st):
        """Test dynamic survey rendering when file not found with fallback disabled."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        with patch('src.ui.survey_ui.config') as mock_config:
            mock_config.SURVEY_FALLBACK_ENABLED = False
            
            # Act
            result = self.survey_ui.render_dynamic_survey(self.pseudonym_id, "nonexistent.csv")
            
            # Assert
            mock_st.error.assert_called_once()
            assert result is None
    
    @patch('src.ui.survey_ui.st')
    def test_render_question_text_type(self, mock_st):
        """Test rendering text type question."""
        # Arrange
        question = SurveyQuestion(
            question_id="test_text",
            question_text="Enter text",
            type="text",
            required=True
        )
        mock_st.text_area.return_value = "test response"
        
        # Act
        result = self.survey_ui._render_question(question)
        
        # Assert
        mock_st.text_area.assert_called_once_with(
            "Enter text *",
            key="q_test_text",
            help="This field is required"
        )
        assert result == "test response"
    
    @patch('src.ui.survey_ui.st')
    def test_render_question_number_type(self, mock_st):
        """Test rendering number type question."""
        # Arrange
        question = SurveyQuestion(
            question_id="test_number",
            question_text="Enter number",
            type="number",
            required=False
        )
        mock_st.number_input.return_value = 42
        
        # Act
        result = self.survey_ui._render_question(question)
        
        # Assert
        mock_st.number_input.assert_called_once_with(
            "Enter number",
            key="q_test_number",
            help=None
        )
        assert result == 42
    
    @patch('src.ui.survey_ui.st')
    def test_render_question_choice_type_required(self, mock_st):
        """Test rendering choice type question (required)."""
        # Arrange
        question = SurveyQuestion(
            question_id="test_choice",
            question_text="Select option",
            type="choice",
            options=["Option A", "Option B"],
            required=True
        )
        mock_st.selectbox.return_value = "Option A"
        
        # Act
        result = self.survey_ui._render_question(question)
        
        # Assert
        mock_st.selectbox.assert_called_once_with(
            "Select option *",
            options=["Option A", "Option B"],
            key="q_test_choice",
            help="This field is required"
        )
        assert result == "Option A"
    
    @patch('src.ui.survey_ui.st')
    def test_render_question_choice_type_optional(self, mock_st):
        """Test rendering choice type question (optional)."""
        # Arrange
        question = SurveyQuestion(
            question_id="test_choice",
            question_text="Select option",
            type="choice",
            options=["Option A", "Option B"],
            required=False
        )
        mock_st.selectbox.return_value = "Option A"
        
        # Act
        result = self.survey_ui._render_question(question)
        
        # Assert
        mock_st.selectbox.assert_called_once_with(
            "Select option",
            options=["", "Option A", "Option B"],  # Empty option added for optional
            key="q_test_choice",
            help=None
        )
        assert result == "Option A"
    
    @patch('src.ui.survey_ui.st')
    def test_render_question_multi_choice_type(self, mock_st):
        """Test rendering multi-choice type question."""
        # Arrange
        question = SurveyQuestion(
            question_id="test_multi",
            question_text="Select multiple",
            type="multi-choice",
            options=["Option A", "Option B", "Option C"],
            required=False
        )
        mock_st.multiselect.return_value = ["Option A", "Option C"]
        
        # Act
        result = self.survey_ui._render_question(question)
        
        # Assert
        mock_st.multiselect.assert_called_once_with(
            "Select multiple",
            options=["Option A", "Option B", "Option C"],
            key="q_test_multi",
            help="Select all that apply"
        )
        assert result == ["Option A", "Option C"]
    
    @patch('src.ui.survey_ui.st')
    def test_render_question_choice_no_options_error(self, mock_st):
        """Test rendering choice question without options shows error."""
        # Arrange
        question = SurveyQuestion(
            question_id="test_choice",
            question_text="Select option",
            type="choice",
            options=None,
            required=True
        )
        
        # Act
        result = self.survey_ui._render_question(question)
        
        # Assert
        mock_st.error.assert_called_once()
        assert result is None
    
    @patch('src.ui.survey_ui.st')
    def test_render_question_unsupported_type_error(self, mock_st):
        """Test rendering unsupported question type shows error."""
        # Arrange
        question = SurveyQuestion(
            question_id="test_invalid",
            question_text="Invalid question",
            type="invalid_type",
            required=True
        )
        
        # Act
        result = self.survey_ui._render_question(question)
        
        # Assert
        mock_st.error.assert_called_once_with("Unsupported question type: invalid_type")
        assert result is None
    
    @patch('src.ui.survey_ui.st')
    def test_handle_survey_submission_validation_errors(self, mock_st):
        """Test survey submission with validation errors."""
        # Arrange
        responses = {"name": ""}  # Invalid response
        
        mock_logic = Mock()
        validation_result = ValidationResult(
            is_valid=False,
            errors=["Name is required"],
            warnings=[]
        )
        mock_logic.validate_survey_responses.return_value = validation_result
        
        with patch.object(self.survey_ui, '_get_survey_logic', return_value=mock_logic):
            # Act
            result = self.survey_ui._handle_survey_submission(
                self.pseudonym_id, responses, self.sample_definition
            )
            
            # Assert
            mock_st.error.assert_called()
            assert result is None
    
    @patch('src.ui.survey_ui.st')
    def test_handle_survey_submission_success(self, mock_st):
        """Test successful survey submission."""
        # Arrange
        responses = {"name": "John", "age": 25}
        
        mock_logic = Mock()
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        submission_result = SurveyResult(success=True)
        
        mock_logic.validate_survey_responses.return_value = validation_result
        mock_logic.process_survey_submission.return_value = submission_result
        
        # Mock session state
        mock_st.session_state = {"current_time": "2024-01-01"}
        
        with patch.object(self.survey_ui, '_get_survey_logic', return_value=mock_logic):
            # Act
            result = self.survey_ui._handle_survey_submission(
                self.pseudonym_id, responses, self.sample_definition
            )
            
            # Assert
            mock_st.success.assert_called_once()
            mock_st.balloons.assert_called_once()
            assert result is not None
            assert result["survey_id"] == "test_survey"
            assert result["responses"] == responses
            assert result["survey_skipped"] is False
    
    @patch('src.ui.survey_ui.st')
    def test_handle_survey_submission_with_warnings(self, mock_st):
        """Test survey submission with validation warnings."""
        # Arrange
        responses = {"name": "John", "age": 25, "unexpected": "value"}
        
        mock_logic = Mock()
        validation_result = ValidationResult(
            is_valid=True, 
            errors=[], 
            warnings=["Unexpected field: unexpected"]
        )
        submission_result = SurveyResult(success=True)
        
        mock_logic.validate_survey_responses.return_value = validation_result
        mock_logic.process_survey_submission.return_value = submission_result
        
        # Mock session state
        mock_st.session_state = {"current_time": "2024-01-01"}
        
        with patch.object(self.survey_ui, '_get_survey_logic', return_value=mock_logic):
            # Act
            result = self.survey_ui._handle_survey_submission(
                self.pseudonym_id, responses, self.sample_definition
            )
            
            # Assert
            mock_st.warning.assert_called_once()
            mock_st.success.assert_called_once()
            assert result is not None
    
    @patch('src.ui.survey_ui.st')
    def test_handle_survey_submission_storage_failure(self, mock_st):
        """Test survey submission with storage failure."""
        # Arrange
        responses = {"name": "John", "age": 25}
        
        mock_logic = Mock()
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        submission_result = SurveyResult(success=False, errors=["Storage failed"])
        
        mock_logic.validate_survey_responses.return_value = validation_result
        mock_logic.process_survey_submission.return_value = submission_result
        
        with patch.object(self.survey_ui, '_get_survey_logic', return_value=mock_logic):
            # Act
            result = self.survey_ui._handle_survey_submission(
                self.pseudonym_id, responses, self.sample_definition
            )
            
            # Assert
            mock_st.error.assert_called()
            assert result is None
    
    @patch('src.ui.survey_ui.st')
    def test_handle_survey_skip(self, mock_st):
        """Test survey skip functionality."""
        # Arrange
        mock_st.session_state = {"current_time": "2024-01-01"}
        
        # Act
        result = self.survey_ui._handle_survey_skip(self.pseudonym_id)
        
        # Assert
        mock_st.info.assert_called_once()
        assert result is not None
        assert result["survey_skipped"] is True
        assert result["responses"]["survey_skipped"] is True
    
    @patch('src.ui.survey_ui.st')
    @patch('src.ui.survey_ui.Path')
    def test_render_survey_validation_preview_success(self, mock_path, mock_st):
        """Test survey validation preview with valid survey."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_logic = Mock()
        mock_logic.load_survey_definition.return_value = self.sample_definition
        
        # Mock streamlit columns
        mock_col1, mock_col2 = Mock(), Mock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        
        # Mock expander
        mock_expander = Mock()
        mock_st.expander.return_value = mock_expander
        
        with patch.object(self.survey_ui, '_get_survey_logic', return_value=mock_logic):
            # Mock the context manager behavior
            mock_col1.__enter__ = Mock(return_value=mock_col1)
            mock_col1.__exit__ = Mock(return_value=None)
            mock_col2.__enter__ = Mock(return_value=mock_col2)
            mock_col2.__exit__ = Mock(return_value=None)
            mock_expander.__enter__ = Mock(return_value=mock_expander)
            mock_expander.__exit__ = Mock(return_value=None)
            
            # Act
            result = self.survey_ui.render_survey_validation_preview("test.csv")
            
            # Assert
            mock_st.success.assert_called_once()
            mock_st.subheader.assert_called_once_with("Survey Validation Preview")
            assert result is True
    
    @patch('src.ui.survey_ui.st')
    @patch('src.ui.survey_ui.Path')
    def test_render_survey_validation_preview_file_not_found(self, mock_path, mock_st):
        """Test survey validation preview with missing file."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = False
        mock_path.return_value = mock_path_instance
        
        # Act
        result = self.survey_ui.render_survey_validation_preview("nonexistent.csv")
        
        # Assert
        mock_st.error.assert_called_once()
        assert result is False
    
    @patch('src.ui.survey_ui.st')
    @patch('src.ui.survey_ui.Path')
    def test_render_survey_validation_preview_load_error(self, mock_path, mock_st):
        """Test survey validation preview with load error."""
        # Arrange
        mock_path_instance = Mock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance
        
        mock_logic = Mock()
        mock_logic.load_survey_definition.side_effect = Exception("Load failed")
        
        with patch.object(self.survey_ui, '_get_survey_logic', return_value=mock_logic):
            # Act
            result = self.survey_ui.render_survey_validation_preview("test.csv")
            
            # Assert
            mock_st.error.assert_called_once()
            assert result is False


class TestSurveyUIConvenienceFunctions:
    """Test convenience functions for survey UI."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pseudonym_id = uuid4()
    
    @patch('src.ui.survey_ui.survey_ui')
    def test_render_dynamic_survey_convenience_function(self, mock_survey_ui):
        """Test render_dynamic_survey convenience function."""
        # Arrange
        from src.ui.survey_ui import render_dynamic_survey
        mock_survey_ui.render_dynamic_survey.return_value = {"test": "data"}
        
        # Act
        result = render_dynamic_survey(self.pseudonym_id, "test.csv")
        
        # Assert
        mock_survey_ui.render_dynamic_survey.assert_called_once_with(self.pseudonym_id, "test.csv")
        assert result == {"test": "data"}
    
    @patch('src.ui.survey_ui.survey_ui')
    def test_render_survey_validation_preview_convenience_function(self, mock_survey_ui):
        """Test render_survey_validation_preview convenience function."""
        # Arrange
        from src.ui.survey_ui import render_survey_validation_preview
        mock_survey_ui.render_survey_validation_preview.return_value = True
        
        # Act
        result = render_survey_validation_preview("test.csv")
        
        # Assert
        mock_survey_ui.render_survey_validation_preview.assert_called_once_with("test.csv")
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])