"""
Tests for UX enhancement database models.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.models import (
    Base,
    ImageProcessingResult,
    ImageProcessingResultStatus,
    ImageCorrection,
    UserCorrectionAction,
    PrerequisiteCheckResult,
    PrerequisiteCheckResultStatus,
    PrerequisiteCheckType,
    TooltipInteraction,
    TooltipInteractionType,
    UXAuditLog,
    UXEventType,
    User,
)


@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session


@pytest.fixture
def db_session(test_db):
    """Create database session for testing."""
    session = test_db()
    yield session
    session.close()


class TestImageProcessingResult:
    """Test ImageProcessingResult model."""

    def test_create_image_processing_result(self, db_session, test_user):
        """Test creating an image processing result."""
        result = ImageProcessingResult(
            user_id=test_user.id,
            original_image_path="/path/to/original.jpg",
            processed_image_path="/path/to/processed.png",
            processing_method="rembg",
            status=ImageProcessingResultStatus.SUCCESS.value,
            confidence_score=85,
            processing_time_ms=2500,
            quality_issues=["blur_detected"],
            person_count=1,
            quality_score=78,
        )
        
        db_session.add(result)
        db_session.commit()
        
        assert result.id is not None
        assert result.user_id == test_user.id
        assert result.original_image_path == "/path/to/original.jpg"
        assert result.status == ImageProcessingResultStatus.SUCCESS.value
        assert result.confidence_score == 85
        assert result.quality_issues == ["blur_detected"]

    def test_image_processing_result_validation(self, db_session, test_user):
        """Test image processing result status validation."""
        with pytest.raises(ValueError, match="Invalid status"):
            ImageProcessingResult(
                user_id=test_user.id,
                original_image_path="/path/to/original.jpg",
                processing_method="rembg",
                status="invalid_status",
            )

    def test_image_processing_result_relationships(self, db_session, test_user):
        """Test image processing result relationships."""
        result = ImageProcessingResult(
            user_id=test_user.id,
            original_image_path="/path/to/original.jpg",
            processing_method="rembg",
        )
        
        db_session.add(result)
        db_session.commit()
        
        # Test user relationship
        assert result.user == test_user
        
        # Test corrections relationship
        correction = ImageCorrection(
            processing_result_id=result.id,
            user_id=test_user.id,
            correction_action=UserCorrectionAction.ACCEPT_PROCESSED.value,
        )
        
        db_session.add(correction)
        db_session.commit()
        
        assert len(result.corrections) == 1
        assert result.corrections[0] == correction


class TestImageCorrection:
    """Test ImageCorrection model."""

    def test_create_image_correction(self, db_session, test_user):
        """Test creating an image correction."""
        # First create a processing result
        result = ImageProcessingResult(
            user_id=test_user.id,
            original_image_path="/path/to/original.jpg",
            processing_method="rembg",
        )
        db_session.add(result)
        db_session.commit()
        
        correction = ImageCorrection(
            processing_result_id=result.id,
            user_id=test_user.id,
            correction_action=UserCorrectionAction.ADJUST_CROP.value,
            crop_coordinates={"left": 10, "top": 20, "right": 100, "bottom": 150},
            rejection_reason="Poor crop quality",
            suggested_modifications="Adjust the crop area",
            final_image_path="/path/to/final.png",
            correction_time_ms=1500,
        )
        
        db_session.add(correction)
        db_session.commit()
        
        assert correction.id is not None
        assert correction.processing_result_id == result.id
        assert correction.correction_action == UserCorrectionAction.ADJUST_CROP.value
        assert correction.crop_coordinates == {"left": 10, "top": 20, "right": 100, "bottom": 150}

    def test_image_correction_validation(self):
        """Test image correction action validation."""
        with pytest.raises(ValueError, match="Invalid correction action"):
            ImageCorrection(
                processing_result_id=uuid4(),
                user_id=uuid4(),
                correction_action="invalid_action",
            )


class TestPrerequisiteCheckResult:
    """Test PrerequisiteCheckResult model."""

    def test_create_prerequisite_check_result(self, db_session, test_user):
        """Test creating a prerequisite check result."""
        result = PrerequisiteCheckResult(
            user_id=test_user.id,
            operation_name="image_generation",
            checker_name="OllamaConnectivityChecker",
            check_type=PrerequisiteCheckType.REQUIRED.value,
            status=PrerequisiteCheckResultStatus.PASSED.value,
            message="Ollama service is accessible",
            details="Connected successfully with 3 models available",
            resolution_steps=["Check Ollama installation", "Verify network connectivity"],
            check_time_ms=250,
            confidence_score=95,
            cached=False,
        )
        
        db_session.add(result)
        db_session.commit()
        
        assert result.id is not None
        assert result.operation_name == "image_generation"
        assert result.checker_name == "OllamaConnectivityChecker"
        assert result.status == PrerequisiteCheckResultStatus.PASSED.value
        assert result.resolution_steps == ["Check Ollama installation", "Verify network connectivity"]

    def test_prerequisite_check_result_validation(self):
        """Test prerequisite check result validation."""
        with pytest.raises(ValueError, match="Invalid check type"):
            PrerequisiteCheckResult(
                operation_name="test",
                checker_name="test",
                check_type="invalid_type",
                status=PrerequisiteCheckResultStatus.PASSED.value,
                message="test",
            )


class TestTooltipInteraction:
    """Test TooltipInteraction model."""

    def test_create_tooltip_interaction(self, db_session, test_user):
        """Test creating a tooltip interaction."""
        interaction = TooltipInteraction(
            user_id=test_user.id,
            session_id="session_123",
            element_id="register_button",
            tooltip_content_id="registration_help",
            interaction_type=TooltipInteractionType.HOVER.value,
            page_context="registration_page",
            tooltip_title="Registration Help",
            tooltip_description="Click to create your account",
            display_time_ms=2500,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        )
        
        db_session.add(interaction)
        db_session.commit()
        
        assert interaction.id is not None
        assert interaction.element_id == "register_button"
        assert interaction.interaction_type == TooltipInteractionType.HOVER.value
        assert interaction.display_time_ms == 2500

    def test_tooltip_interaction_validation(self):
        """Test tooltip interaction type validation."""
        with pytest.raises(ValueError, match="Invalid interaction type"):
            TooltipInteraction(
                element_id="test",
                interaction_type="invalid_type",
            )


class TestUXAuditLog:
    """Test UXAuditLog model."""

    def test_create_ux_audit_log(self, db_session, test_user):
        """Test creating a UX audit log entry."""
        log_entry = UXAuditLog(
            user_id=test_user.id,
            session_id="session_456",
            event_type=UXEventType.IMAGE_CORRECTION_STARTED.value,
            event_context="image_generation_flow",
            event_data={"image_id": "img_123", "processing_method": "rembg"},
            workflow_step="image_correction",
            success=True,
            duration_ms=3500,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            ip_address="192.168.1.100",
        )
        
        db_session.add(log_entry)
        db_session.commit()
        
        assert log_entry.id is not None
        assert log_entry.event_type == UXEventType.IMAGE_CORRECTION_STARTED.value
        assert log_entry.event_data == {"image_id": "img_123", "processing_method": "rembg"}
        assert log_entry.success is True

    def test_ux_audit_log_validation(self):
        """Test UX audit log event type validation."""
        with pytest.raises(ValueError, match="Invalid event type"):
            UXAuditLog(
                event_type="invalid_event_type",
            )


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        password_hash="hashed_password",
        pseudonym="test_pseudonym",
        role="participant",
    )
    db_session.add(user)
    db_session.commit()
    return user