"""
Tests for study participation models.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from src.data.models import (
    Pseudonym,
    StudyConsentRecord,
    StudySurveyResponse,
    ChatMessage,
    StudyPALDData,
    GeneratedImage,
    FeedbackRecord,
    InteractionLog,
    StudyConsentType,
    ChatMessageType,
    StudyPALDType,
)


class TestPseudonym:
    """Test Pseudonym model."""

    def test_pseudonym_creation(self):
        """Test creating a pseudonym."""
        user_id = uuid4()
        created_at = datetime.now()
        pseudonym = Pseudonym(
            user_id=user_id,
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="hashed_value_123",
            created_at=created_at,
            is_active=True,
        )
        
        assert pseudonym.user_id == user_id
        assert pseudonym.pseudonym_text == "M03s2001AJ13"
        assert pseudonym.pseudonym_hash == "hashed_value_123"
        assert pseudonym.is_active is True
        assert pseudonym.created_at == created_at

    def test_pseudonym_repr(self):
        """Test pseudonym string representation."""
        user_id = uuid4()
        pseudonym = Pseudonym(
            user_id=user_id,
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="hashed_value_123",
        )
        
        repr_str = repr(pseudonym)
        assert "Pseudonym" in repr_str
        assert str(pseudonym.pseudonym_id) in repr_str
        assert str(user_id) in repr_str


class TestStudyConsentRecord:
    """Test StudyConsentRecord model."""

    def test_consent_record_creation(self):
        """Test creating a consent record."""
        pseudonym_id = uuid4()
        granted_at = datetime.now()
        consent = StudyConsentRecord(
            pseudonym_id=pseudonym_id,
            consent_type=StudyConsentType.DATA_PROTECTION.value,
            granted=True,
            version="1.0",
            granted_at=granted_at,
        )
        
        assert consent.pseudonym_id == pseudonym_id
        assert consent.consent_type == StudyConsentType.DATA_PROTECTION.value
        assert consent.granted is True
        assert consent.version == "1.0"
        assert consent.granted_at == granted_at

    def test_consent_type_validation(self):
        """Test consent type validation."""
        pseudonym_id = uuid4()
        consent = StudyConsentRecord(
            pseudonym_id=pseudonym_id,
            consent_type=StudyConsentType.AI_INTERACTION.value,
            granted=True,
            version="1.0",
        )
        
        # Valid consent type should work
        assert consent.consent_type == StudyConsentType.AI_INTERACTION.value
        
        # Invalid consent type should raise ValueError
        with pytest.raises(ValueError, match="Invalid study consent type"):
            consent.validate_consent_type("consent_type", "invalid_type")


class TestStudySurveyResponse:
    """Test StudySurveyResponse model."""

    def test_survey_response_creation(self):
        """Test creating a survey response."""
        pseudonym_id = uuid4()
        responses = {"question_1": "answer_1", "question_2": 42}
        completed_at = datetime.now()
        
        survey_response = StudySurveyResponse(
            pseudonym_id=pseudonym_id,
            survey_version="1.0",
            responses=responses,
            completed_at=completed_at,
        )
        
        assert survey_response.pseudonym_id == pseudonym_id
        assert survey_response.survey_version == "1.0"
        assert survey_response.responses == responses
        assert survey_response.completed_at == completed_at


class TestChatMessage:
    """Test ChatMessage model."""

    def test_chat_message_creation(self):
        """Test creating a chat message."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        timestamp = datetime.now()
        
        message = ChatMessage(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.USER.value,
            content="Hello, AI!",
            pald_data={"age": 25, "gender": "female"},
            timestamp=timestamp,
        )
        
        assert message.pseudonym_id == pseudonym_id
        assert message.session_id == session_id
        assert message.message_type == ChatMessageType.USER.value
        assert message.content == "Hello, AI!"
        assert message.pald_data == {"age": 25, "gender": "female"}
        assert message.timestamp == timestamp

    def test_message_type_validation(self):
        """Test message type validation."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        message = ChatMessage(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            message_type=ChatMessageType.ASSISTANT.value,
            content="Hello, human!",
        )
        
        # Valid message type should work
        assert message.message_type == ChatMessageType.ASSISTANT.value
        
        # Invalid message type should raise ValueError
        with pytest.raises(ValueError, match="Invalid message type"):
            message.validate_message_type("message_type", "invalid_type")


class TestStudyPALDData:
    """Test StudyPALDData model."""

    def test_pald_data_creation(self):
        """Test creating PALD data."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        pald_content = {
            "age": 25,
            "gender": "female",
            "learning_style": "visual",
        }
        created_at = datetime.now()
        
        pald_data = StudyPALDData(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            pald_content=pald_content,
            pald_type=StudyPALDType.INPUT.value,
            consistency_score=0.85,
            created_at=created_at,
        )
        
        assert pald_data.pseudonym_id == pseudonym_id
        assert pald_data.session_id == session_id
        assert pald_data.pald_content == pald_content
        assert pald_data.pald_type == StudyPALDType.INPUT.value
        assert pald_data.consistency_score == 0.85
        assert pald_data.created_at == created_at

    def test_pald_type_validation(self):
        """Test PALD type validation."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        
        pald_data = StudyPALDData(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            pald_content={"age": 25},
            pald_type=StudyPALDType.FEEDBACK.value,
        )
        
        # Valid PALD type should work
        assert pald_data.pald_type == StudyPALDType.FEEDBACK.value
        
        # Invalid PALD type should raise ValueError
        with pytest.raises(ValueError, match="Invalid study PALD type"):
            pald_data.validate_pald_type("pald_type", "invalid_type")


class TestGeneratedImage:
    """Test GeneratedImage model."""

    def test_generated_image_creation(self):
        """Test creating a generated image."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        pald_source_id = uuid4()
        created_at = datetime.now()
        
        image = GeneratedImage(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            image_path="/path/to/image.png",
            prompt="A young female student with visual learning style",
            pald_source_id=pald_source_id,
            generation_parameters={"model": "sdxl", "steps": 20, "cfg": 7.5},
            created_at=created_at,
        )
        
        assert image.pseudonym_id == pseudonym_id
        assert image.session_id == session_id
        assert image.image_path == "/path/to/image.png"
        assert image.prompt == "A young female student with visual learning style"
        assert image.pald_source_id == pald_source_id
        assert image.generation_parameters == {"model": "sdxl", "steps": 20, "cfg": 7.5}
        assert image.created_at == created_at


class TestFeedbackRecord:
    """Test FeedbackRecord model."""

    def test_feedback_record_creation(self):
        """Test creating a feedback record."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        image_id = uuid4()
        created_at = datetime.now()
        
        feedback = FeedbackRecord(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            image_id=image_id,
            feedback_text="The image looks great, but could be more colorful",
            feedback_pald={"color_preference": "bright", "satisfaction": 8},
            round_number=1,
            created_at=created_at,
        )
        
        assert feedback.pseudonym_id == pseudonym_id
        assert feedback.session_id == session_id
        assert feedback.image_id == image_id
        assert feedback.feedback_text == "The image looks great, but could be more colorful"
        assert feedback.feedback_pald == {"color_preference": "bright", "satisfaction": 8}
        assert feedback.round_number == 1
        assert feedback.created_at == created_at


class TestInteractionLog:
    """Test InteractionLog model."""

    def test_interaction_log_creation(self):
        """Test creating an interaction log."""
        pseudonym_id = uuid4()
        session_id = uuid4()
        timestamp = datetime.now()
        
        log = InteractionLog(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type="pald_extraction",
            prompt="Extract PALD from: I am a 25-year-old visual learner",
            response='{"age": 25, "learning_style": "visual"}',
            model_used="gpt-4",
            parameters={"temperature": 0.1, "max_tokens": 500},
            token_usage={"prompt_tokens": 50, "completion_tokens": 25},
            latency_ms=1500,
            timestamp=timestamp,
        )
        
        assert log.pseudonym_id == pseudonym_id
        assert log.session_id == session_id
        assert log.interaction_type == "pald_extraction"
        assert log.prompt == "Extract PALD from: I am a 25-year-old visual learner"
        assert log.response == '{"age": 25, "learning_style": "visual"}'
        assert log.model_used == "gpt-4"
        assert log.parameters == {"temperature": 0.1, "max_tokens": 500}
        assert log.token_usage == {"prompt_tokens": 50, "completion_tokens": 25}
        assert log.latency_ms == 1500
        assert log.timestamp == timestamp