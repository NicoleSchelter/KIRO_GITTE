#!/usr/bin/env python3
"""
Demonstration of the Dynamic Survey System
Shows how to load surveys from CSV/Excel files and process responses.
"""

import tempfile
import os
from uuid import uuid4
from unittest.mock import Mock

from src.logic.survey_logic import SurveyLogic
from src.services.survey_service import SurveyService


def create_demo_survey_file():
    """Create a demo survey CSV file."""
    survey_content = """question_id,question_text,type,options,required
name,What is your full name?,text,,true
age,What is your age?,number,,true
learning_style,What is your preferred learning style?,choice,"Visual,Auditory,Kinesthetic,Reading/Writing",true
subjects,Which subjects interest you most?,multi-choice,"Mathematics,Science,Technology,Arts,History",false
goals,What are your main learning goals?,text,,false
feedback_pref,How do you prefer to receive feedback?,choice,"Encouraging,Direct,Detailed,Brief",false"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_file:
        tmp_file.write(survey_content)
        return tmp_file.name


def demo_dynamic_survey_system():
    """Demonstrate the dynamic survey system functionality."""
    print("🔬 Dynamic Survey System Demonstration")
    print("=" * 50)
    
    # Create mock database session
    db_session = Mock()
    db_session.begin.return_value.__enter__ = Mock()
    db_session.begin.return_value.__exit__ = Mock(return_value=None)
    
    # Initialize services
    survey_service = SurveyService(db_session)
    survey_logic = SurveyLogic(survey_service)
    
    # Create demo survey file
    survey_file_path = create_demo_survey_file()
    
    try:
        print(f"\n📄 Loading survey from: {os.path.basename(survey_file_path)}")
        
        # Step 1: Load survey definition
        survey_definition = survey_logic.load_survey_definition(survey_file_path)
        
        print(f"✅ Loaded survey: {survey_definition.title}")
        print(f"   Survey ID: {survey_definition.survey_id}")
        print(f"   Version: {survey_definition.version}")
        print(f"   Questions: {len(survey_definition.questions)}")
        
        # Display questions
        print("\n📋 Survey Questions:")
        for i, question in enumerate(survey_definition.questions, 1):
            print(f"   {i}. [{question.type.upper()}] {question.question_text}")
            if question.options:
                print(f"      Options: {', '.join(question.options)}")
            print(f"      Required: {'Yes' if question.required else 'No'}")
            print()
        
        # Step 2: Demonstrate valid responses
        print("✅ Testing Valid Responses:")
        valid_responses = {
            "name": "Alice Johnson",
            "age": "28",
            "learning_style": "Visual",
            "subjects": ["Mathematics", "Technology"],
            "goals": "Improve problem-solving skills and learn new technologies",
            "feedback_pref": "Encouraging"
        }
        
        print("   Responses:")
        for key, value in valid_responses.items():
            print(f"     {key}: {value}")
        
        # Validate responses
        validation_result = survey_logic.validate_survey_responses(valid_responses, survey_definition)
        print(f"\n   Validation Result: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}")
        if validation_result.errors:
            print(f"   Errors: {validation_result.errors}")
        if validation_result.warnings:
            print(f"   Warnings: {validation_result.warnings}")
        
        # Step 3: Process survey submission
        print("\n💾 Processing Survey Submission:")
        pseudonym_id = uuid4()
        
        # Mock successful storage
        survey_service.store_survey_responses = Mock(return_value=True)
        
        submission_result = survey_logic.process_survey_submission(
            pseudonym_id, valid_responses, survey_definition
        )
        
        print(f"   Submission Result: {'✅ SUCCESS' if submission_result.success else '❌ FAILED'}")
        if submission_result.errors:
            print(f"   Errors: {submission_result.errors}")
        
        # Step 4: Demonstrate invalid responses
        print("\n❌ Testing Invalid Responses:")
        invalid_responses = {
            # Missing required "name" field
            "age": "not_a_number",  # Invalid number
            "learning_style": "InvalidStyle",  # Invalid choice
            "subjects": ["InvalidSubject"],  # Invalid multi-choice
            "unexpected_field": "This shouldn't be here"  # Unexpected field
        }
        
        print("   Invalid Responses:")
        for key, value in invalid_responses.items():
            print(f"     {key}: {value}")
        
        validation_result = survey_logic.validate_survey_responses(invalid_responses, survey_definition)
        print(f"\n   Validation Result: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}")
        print(f"   Errors ({len(validation_result.errors)}):")
        for error in validation_result.errors:
            print(f"     - {error}")
        if validation_result.warnings:
            print(f"   Warnings ({len(validation_result.warnings)}):")
            for warning in validation_result.warnings:
                print(f"     - {warning}")
        
        # Step 5: Demonstrate minimal valid responses (only required fields)
        print("\n📝 Testing Minimal Valid Responses (Required Only):")
        minimal_responses = {
            "name": "Bob Smith",
            "age": "35",
            "learning_style": "Auditory"
            # Optional fields omitted
        }
        
        print("   Minimal Responses:")
        for key, value in minimal_responses.items():
            print(f"     {key}: {value}")
        
        validation_result = survey_logic.validate_survey_responses(minimal_responses, survey_definition)
        print(f"\n   Validation Result: {'✅ VALID' if validation_result.is_valid else '❌ INVALID'}")
        
        print("\n🎉 Dynamic Survey System Demonstration Complete!")
        print("\nKey Features Demonstrated:")
        print("✅ Dynamic survey loading from CSV files")
        print("✅ Support for multiple question types (text, number, choice, multi-choice)")
        print("✅ Comprehensive response validation")
        print("✅ Required vs optional field handling")
        print("✅ Error reporting and validation feedback")
        print("✅ Integration with pseudonym-based storage")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        
    finally:
        # Cleanup
        if os.path.exists(survey_file_path):
            os.unlink(survey_file_path)


if __name__ == "__main__":
    demo_dynamic_survey_system()