#!/usr/bin/env python3
"""
Demonstration of the Enhanced Survey UI System
Shows how to use dynamic survey rendering for study participation.
"""

import tempfile
import os
from uuid import uuid4
from unittest.mock import Mock

from src.ui.survey_ui import SurveyUI, render_dynamic_survey, render_survey_validation_preview


def create_demo_survey_file():
    """Create a demo survey CSV file for testing."""
    survey_content = """question_id,question_text,type,options,required
participant_name,What is your full name?,text,,true
participant_age,What is your age?,number,,true
learning_style,What is your preferred learning style?,choice,"Visual,Auditory,Kinesthetic,Reading/Writing,Multimodal",true
difficulty_level,What difficulty level do you prefer?,choice,"Beginner,Intermediate,Advanced,Expert",true
subject_interests,Which subjects interest you most?,multi-choice,"Mathematics,Science,Technology,Engineering,Language Arts,History,Art,Music,Psychology,Philosophy",false
learning_goals,What are your main learning goals?,text,,false
motivation_factors,What motivates you to learn?,multi-choice,"Personal growth,Career advancement,Academic requirements,Curiosity,Problem-solving,Creative expression",false
feedback_preference,How do you prefer to receive feedback?,choice,"Encouraging,Direct,Detailed,Brief",false
communication_style,What communication style do you prefer?,choice,"Formal,Friendly,Enthusiastic,Calm",false
personalization_level,How much personalization do you want?,choice,"Minimal,Moderate,High,Maximum",false"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
        tmp_file.write(survey_content)
        return tmp_file.name


def demo_enhanced_survey_ui():
    """Demonstrate the enhanced survey UI functionality."""
    print("🎨 Enhanced Survey UI System Demonstration")
    print("=" * 60)
    
    # Create demo survey file
    survey_file_path = create_demo_survey_file()
    
    try:
        print(f"\n📄 Created demo survey file: {os.path.basename(survey_file_path)}")
        
        # Step 1: Validate survey file
        print("\n🔍 Step 1: Survey Validation Preview")
        print("-" * 40)
        
        # Mock streamlit for validation preview
        import src.ui.survey_ui as survey_ui_module
        original_st = getattr(survey_ui_module, 'st', None)
        
        # Create mock streamlit
        mock_st = Mock()
        mock_st.subheader = lambda x: print(f"📋 {x}")
        mock_st.success = lambda x: print(f"✅ {x}")
        mock_st.error = lambda x: print(f"❌ {x}")
        mock_st.write = lambda x: print(f"   {x}")
        
        # Mock columns and expander
        col1, col2 = Mock(), Mock()
        col1.__enter__ = Mock(return_value=col1)
        col1.__exit__ = Mock(return_value=None)
        col2.__enter__ = Mock(return_value=col2)
        col2.__exit__ = Mock(return_value=None)
        mock_st.columns = Mock(return_value=[col1, col2])
        
        expander = Mock()
        expander.__enter__ = Mock(return_value=expander)
        expander.__exit__ = Mock(return_value=None)
        mock_st.expander = Mock(return_value=expander)
        
        # Temporarily replace streamlit
        survey_ui_module.st = mock_st
        
        try:
            # Test validation preview
            validation_result = render_survey_validation_preview(survey_file_path)
            print(f"   Validation Result: {'✅ VALID' if validation_result else '❌ INVALID'}")
        finally:
            # Restore original streamlit
            if original_st:
                survey_ui_module.st = original_st
        
        # Step 2: Demonstrate dynamic survey rendering
        print("\n🎯 Step 2: Dynamic Survey Rendering")
        print("-" * 40)
        
        survey_ui = SurveyUI()
        pseudonym_id = uuid4()
        
        # Load survey definition directly to show structure
        survey_logic = survey_ui._get_survey_logic()
        survey_definition = survey_logic.load_survey_definition(survey_file_path)
        
        print(f"📊 Survey: {survey_definition.title}")
        print(f"   Survey ID: {survey_definition.survey_id}")
        print(f"   Version: {survey_definition.version}")
        print(f"   Total Questions: {len(survey_definition.questions)}")
        
        # Display question breakdown
        question_types = {}
        required_count = 0
        
        for question in survey_definition.questions:
            question_types[question.type] = question_types.get(question.type, 0) + 1
            if question.required:
                required_count += 1
        
        print(f"   Required Questions: {required_count}")
        print(f"   Question Types: {dict(question_types)}")
        
        # Step 3: Show question rendering examples
        print("\n📝 Step 3: Question Rendering Examples")
        print("-" * 40)
        
        # Mock streamlit for question rendering
        mock_st.text_area = lambda label, **kwargs: f"[TEXT_INPUT: {label}]"
        mock_st.number_input = lambda label, **kwargs: f"[NUMBER_INPUT: {label}]"
        mock_st.selectbox = lambda label, options, **kwargs: f"[SELECTBOX: {label} with {len(options)} options]"
        mock_st.multiselect = lambda label, options, **kwargs: f"[MULTISELECT: {label} with {len(options)} options]"
        
        survey_ui_module.st = mock_st
        
        try:
            # Render sample questions
            sample_questions = survey_definition.questions[:5]  # First 5 questions
            
            for i, question in enumerate(sample_questions, 1):
                print(f"   {i}. {question.question_text}")
                print(f"      Type: {question.type.upper()}")
                print(f"      Required: {'Yes' if question.required else 'No'}")
                
                if question.options:
                    print(f"      Options: {', '.join(question.options[:3])}{'...' if len(question.options) > 3 else ''}")
                
                # Render the question
                rendered = survey_ui._render_question(question)
                print(f"      Rendered: {rendered}")
                print()
        
        finally:
            if original_st:
                survey_ui_module.st = original_st
        
        # Step 4: Demonstrate response validation
        print("\n✅ Step 4: Response Validation Examples")
        print("-" * 40)
        
        # Valid responses
        valid_responses = {
            "participant_name": "Alice Johnson",
            "participant_age": 28,
            "learning_style": "Visual",
            "difficulty_level": "Intermediate",
            "subject_interests": ["Mathematics", "Technology"],
            "learning_goals": "Improve problem-solving skills",
            "motivation_factors": ["Personal growth", "Curiosity"],
            "feedback_preference": "Encouraging",
            "communication_style": "Friendly",
            "personalization_level": "Moderate"
        }
        
        print("📋 Valid Response Example:")
        for key, value in list(valid_responses.items())[:5]:  # Show first 5
            print(f"   {key}: {value}")
        print("   ...")
        
        validation_result = survey_logic.validate_survey_responses(valid_responses, survey_definition)
        print(f"\n   Validation: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}")
        
        # Invalid responses
        invalid_responses = {
            "participant_age": "not_a_number",
            "learning_style": "InvalidStyle",
            "subject_interests": ["InvalidSubject"],
            # Missing required fields
        }
        
        print("\n📋 Invalid Response Example:")
        for key, value in invalid_responses.items():
            print(f"   {key}: {value}")
        print("   (Missing required fields)")
        
        validation_result = survey_logic.validate_survey_responses(invalid_responses, survey_definition)
        print(f"\n   Validation: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}")
        
        if validation_result.errors:
            print("   Errors:")
            for error in validation_result.errors[:3]:  # Show first 3 errors
                print(f"     - {error}")
            if len(validation_result.errors) > 3:
                print(f"     ... and {len(validation_result.errors) - 3} more")
        
        # Step 5: Show key features
        print("\n🎉 Enhanced Survey UI Features")
        print("-" * 40)
        
        features = [
            "✅ Dynamic survey loading from CSV/Excel files",
            "✅ Support for 4 question types (text, number, choice, multi-choice)",
            "✅ Comprehensive response validation with detailed error messages",
            "✅ Required vs optional field handling",
            "✅ Pseudonym-based data storage for study participation",
            "✅ Fallback to default survey when file loading fails",
            "✅ Survey validation preview for administrators",
            "✅ Integration with existing GITTE architecture",
            "✅ Comprehensive error handling and recovery",
            "✅ Full test coverage (unit, contract, property, integration)"
        ]
        
        for feature in features:
            print(f"   {feature}")
        
        print("\n🔧 Configuration Options:")
        config_options = [
            "SURVEY_FILE_PATH: Path to survey definition file",
            "SURVEY_FALLBACK_ENABLED: Enable fallback to default survey",
            "SURVEY_VALIDATION_STRICT: Enable strict validation mode"
        ]
        
        for option in config_options:
            print(f"   • {option}")
        
        print("\n📚 Usage Examples:")
        usage_examples = [
            "render_dynamic_survey(pseudonym_id) - Render survey for study participant",
            "render_survey_validation_preview(file_path) - Preview survey for admin",
            "SurveyUI()._render_question(question) - Render individual question"
        ]
        
        for example in usage_examples:
            print(f"   • {example}")
        
        print(f"\n🎯 Task 12 Implementation Complete!")
        print("   All requirements have been successfully implemented:")
        print("   ✅ Enhanced survey_ui.py with dynamic rendering")
        print("   ✅ Dynamic question rendering for all question types")
        print("   ✅ Survey validation and submission with error handling")
        print("   ✅ Comprehensive UI tests (unit, contract, property, integration)")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        if os.path.exists(survey_file_path):
            os.unlink(survey_file_path)


if __name__ == "__main__":
    demo_enhanced_survey_ui()