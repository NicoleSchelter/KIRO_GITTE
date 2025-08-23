"""
Integration tests for dynamic survey UI.
Tests the complete flow from file loading to response processing.
"""

import pytest
import tempfile
import os
from uuid import uuid4
from unittest.mock import patch, Mock

from src.ui.survey_ui import SurveyUI, render_dynamic_survey, render_survey_validation_preview
from src.data.database import get_session


class TestSurveyUIIntegration:
    """Integration tests for survey UI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.survey_ui = SurveyUI()
        self.pseudonym_id = uuid4()
    
    def create_test_survey_file(self) -> str:
        """Create a test survey CSV file."""
        content = """question_id,question_text,type,options,required
name,What is your full name?,text,,true
age,What is your age?,number,,true
learning_style,What is your preferred learning style?,choice,"Visual,Auditory,Kinesthetic,Reading/Writing",true
subjects,Which subjects interest you most?,multi-choice,"Mathematics,Science,Technology,Arts,History",false
goals,What are your main learning goals?,text,,false"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(content)
            return tmp_file.name
    
    def test_end_to_end_survey_loading_and_validation(self):
        """Test complete survey loading and validation flow."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        try:
            # Act - Load survey through UI layer
            with get_session() as db_session:
                survey_logic = self.survey_ui._get_survey_logic()
                survey_definition = survey_logic.load_survey_definition(survey_file)
                
                # Assert - Survey should be loaded correctly
                assert survey_definition is not None
                assert len(survey_definition.questions) == 5
                
                # Verify question types
                question_types = [q.type for q in survey_definition.questions]
                assert "text" in question_types
                assert "number" in question_types
                assert "choice" in question_types
                assert "multi-choice" in question_types
                
                # Verify required fields
                required_questions = [q for q in survey_definition.questions if q.required]
                assert len(required_questions) == 3  # name, age, learning_style
                
                # Verify choice options
                choice_question = next(q for q in survey_definition.questions if q.question_id == "learning_style")
                assert choice_question.options == ["Visual", "Auditory", "Kinesthetic", "Reading/Writing"]
                
                multi_choice_question = next(q for q in survey_definition.questions if q.question_id == "subjects")
                assert multi_choice_question.options == ["Mathematics", "Science", "Technology", "Arts", "History"]
                
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    def test_survey_response_validation_integration(self):
        """Test survey response validation through UI layer."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        try:
            with get_session() as db_session:
                survey_logic = self.survey_ui._get_survey_logic()
                survey_definition = survey_logic.load_survey_definition(survey_file)
                
                # Test valid responses
                valid_responses = {
                    "name": "John Doe",
                    "age": 30,
                    "learning_style": "Visual",
                    "subjects": ["Mathematics", "Science"],
                    "goals": "Learn new skills"
                }
                
                # Act
                validation_result = survey_logic.validate_survey_responses(valid_responses, survey_definition)
                
                # Assert
                assert validation_result.is_valid is True
                assert len(validation_result.errors) == 0
                
                # Test invalid responses
                invalid_responses = {
                    "name": "",  # Empty required field
                    "age": "not_a_number",  # Invalid type
                    "learning_style": "InvalidStyle",  # Invalid choice
                    "subjects": ["InvalidSubject"]  # Invalid multi-choice
                }
                
                # Act
                validation_result = survey_logic.validate_survey_responses(invalid_responses, survey_definition)
                
                # Assert
                assert validation_result.is_valid is False
                assert len(validation_result.errors) > 0
                
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    @patch('src.ui.survey_ui.st')
    def test_render_dynamic_survey_integration(self, mock_st):
        """Test dynamic survey rendering integration."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        # Mock streamlit components
        mock_st.title = Mock()
        mock_st.write = Mock()
        mock_st.form = Mock()
        mock_st.text_area = Mock(return_value="John Doe")
        mock_st.number_input = Mock(return_value=30)
        mock_st.selectbox = Mock(return_value="Visual")
        mock_st.multiselect = Mock(return_value=["Mathematics"])
        mock_st.columns = Mock(return_value=[Mock(), Mock()])
        
        # Mock form context manager
        form_context = Mock()
        form_context.__enter__ = Mock(return_value=form_context)
        form_context.__exit__ = Mock(return_value=None)
        mock_st.form.return_value = form_context
        
        try:
            # Act
            with patch('src.ui.survey_ui.form_submit_button') as mock_submit:
                mock_submit.return_value = False  # No submission
                
                result = self.survey_ui.render_dynamic_survey(self.pseudonym_id, survey_file)
                
                # Assert
                mock_st.title.assert_called()
                assert result is None  # No submission occurred
                
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    @patch('src.ui.survey_ui.st')
    def test_render_survey_validation_preview_integration(self, mock_st):
        """Test survey validation preview integration."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        # Mock streamlit components
        mock_st.subheader = Mock()
        mock_st.success = Mock()
        mock_st.write = Mock()
        
        # Mock columns context manager
        col1, col2 = Mock(), Mock()
        col1.__enter__ = Mock(return_value=col1)
        col1.__exit__ = Mock(return_value=None)
        col2.__enter__ = Mock(return_value=col2)
        col2.__exit__ = Mock(return_value=None)
        mock_st.columns = Mock(return_value=[col1, col2])
        
        # Mock expander context manager
        expander_context = Mock()
        expander_context.__enter__ = Mock(return_value=expander_context)
        expander_context.__exit__ = Mock(return_value=None)
        mock_st.expander = Mock(return_value=expander_context)
        
        try:
            # Act
            result = self.survey_ui.render_survey_validation_preview(survey_file)
            
            # Assert
            assert result is True
            mock_st.subheader.assert_called_with("Survey Validation Preview")
            mock_st.success.assert_called()
            
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    def test_convenience_functions_integration(self):
        """Test convenience functions work with actual survey files."""
        # Arrange
        survey_file = self.create_test_survey_file()
        
        try:
            # Test render_survey_validation_preview convenience function
            with patch('src.ui.survey_ui.st') as mock_st:
                mock_st.subheader = Mock()
                mock_st.success = Mock()
                mock_st.write = Mock()
                
                # Mock columns context manager
                col1, col2 = Mock(), Mock()
                col1.__enter__ = Mock(return_value=col1)
                col1.__exit__ = Mock(return_value=None)
                col2.__enter__ = Mock(return_value=col2)
                col2.__exit__ = Mock(return_value=None)
                mock_st.columns = Mock(return_value=[col1, col2])
                
                expander_context = Mock()
                expander_context.__enter__ = Mock(return_value=expander_context)
                expander_context.__exit__ = Mock(return_value=None)
                mock_st.expander = Mock(return_value=expander_context)
                
                # Act
                result = render_survey_validation_preview(survey_file)
                
                # Assert
                assert result is True
                
            # Test render_dynamic_survey convenience function
            with patch('src.ui.survey_ui.st') as mock_st:
                mock_st.title = Mock()
                mock_st.write = Mock()
                mock_st.form = Mock()
                mock_st.columns = Mock(return_value=[Mock(), Mock()])
                
                form_context = Mock()
                form_context.__enter__ = Mock(return_value=form_context)
                form_context.__exit__ = Mock(return_value=None)
                mock_st.form.return_value = form_context
                
                with patch('src.ui.survey_ui.form_submit_button') as mock_submit:
                    mock_submit.return_value = False
                    
                    # Act
                    result = render_dynamic_survey(self.pseudonym_id, survey_file)
                    
                    # Assert
                    assert result is None  # No submission
                    
        finally:
            if os.path.exists(survey_file):
                os.unlink(survey_file)
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        # Test with non-existent file
        with patch('src.ui.survey_ui.st') as mock_st:
            mock_st.error = Mock()
            mock_st.info = Mock()
            
            with patch('src.ui.survey_ui.config') as mock_config:
                mock_config.SURVEY_FALLBACK_ENABLED = False
                
                # Act
                result = self.survey_ui.render_dynamic_survey(self.pseudonym_id, "nonexistent.csv")
                
                # Assert
                mock_st.error.assert_called()
                assert result is None
        
        # Test with invalid file format
        invalid_file = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_file.write("invalid content")
                invalid_file = tmp_file.name
            
            with patch('src.ui.survey_ui.st') as mock_st:
                mock_st.error = Mock()
                
                # Act
                result = self.survey_ui.render_dynamic_survey(self.pseudonym_id, invalid_file)
                
                # Assert
                mock_st.error.assert_called()
                assert result is None
                
        finally:
            if invalid_file and os.path.exists(invalid_file):
                os.unlink(invalid_file)


if __name__ == "__main__":
    pytest.main([__file__])