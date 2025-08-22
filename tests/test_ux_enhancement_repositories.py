"""
Tests for UX enhancement repositories.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.repositories import (
    ImageProcessingResultRepository,
    ImageCorrectionRepository,
    PrerequisiteCheckResultRepository,
    TooltipInteractionRepository,
    UXAuditLogRepository,
)
from src.data.schemas import (
    ImageProcessingResultCreate,
    ImageCorrectionCreate,
    PrerequisiteCheckResultCreate,
    TooltipInteractionCreate,
    UXAuditLogCreate,
    ImageProcessingResultStatus,
    UserCorrectionAction,
    PrerequisiteCheckResultStatus,
    PrerequisiteCheckType,
    TooltipInteractionType,
    UXEventType,
)
from src.data.models import Base, User


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


class TestImageProcessingResultRepository:
    """Test ImageProcessingResultRepository."""

    def test_create_image_processing_result(self, db_session, test_user):
        """Test creating an image processing result."""
        repo = ImageProcessingResultRepository(db_session)
        
        result_data = ImageProcessingResultCreate(
            original_image_path="/path/to/original.jpg",
            processed_image_path="/path/to/processed.png",
            processing_method="rembg",
            status=ImageProcessingResultStatus.SUCCESS,
            confidence_score=85,
            processing_time_ms=2500,
            quality_issues=["blur_detected"],
            person_count=1,
            quality_score=78,
        )
        
        result = repo.create(test_user.id, result_data)
        
        assert result is not None
        assert result.user_id == test_user.id
        assert result.original_image_path == "/path/to/original.jpg"
        assert result.status == ImageProcessingResultStatus.SUCCESS.value

    def test_get_by_user(self, db_session, test_user):
        """Test getting results by user."""
        repo = ImageProcessingResultRepository(db_session)
        
        # Create multiple results
        for i in range(3):
            result_data = ImageProcessingResultCreate(
                original_image_path=f"/path/to/original_{i}.jpg",
                processing_method="rembg",
            )
            repo.create(test_user.id, result_data)
        
        results = repo.get_by_user(test_user.id)
        assert len(results) == 3

    def test_update_status(self, db_session, test_user):
        """Test updating result status."""
        repo = ImageProcessingResultRepository(db_session)
        
        result_data = ImageProcessingResultCreate(
            original_image_path="/path/to/original.jpg",
            processing_method="rembg",
        )
        result = repo.create(test_user.id, result_data)
        
        success = repo.update_status(result.id, ImageProcessingResultStatus.CORRECTED)
        assert success is True
        
        updated_result = repo.get_by_id(result.id)
        assert updated_result.status == ImageProcessingResultStatus.CORRECTED.value

    def test_get_by_status(self, db_session, test_user):
        """Test getting results by status."""
        repo = ImageProcessingResultRepository(db_session)
        
        # Create results with different statuses
        for status in [ImageProcessingResultStatus.SUCCESS, ImageProcessingResultStatus.FAILED]:
            result_data = ImageProcessingResultCreate(
                original_image_path=f"/path/to/{status.value}.jpg",
                processing_method="rembg",
                status=status,
            )
            repo.create(test_user.id, result_data)
        
        success_results = repo.get_by_status(ImageProcessingResultStatus.SUCCESS)
        assert len(success_results) == 1
        assert success_results[0].status == ImageProcessingResultStatus.SUCCESS.value


class TestImageCorrectionRepository:
    """Test ImageCorrectionRepository."""

    def test_create_image_correction(self, db_session, test_user):
        """Test creating an image correction."""
        # First create a processing result
        result_repo = ImageProcessingResultRepository(db_session)
        result_data = ImageProcessingResultCreate(
            original_image_path="/path/to/original.jpg",
            processing_method="rembg",
        )
        processing_result = result_repo.create(test_user.id, result_data)
        
        # Now create a correction
        correction_repo = ImageCorrectionRepository(db_session)
        correction_data = ImageCorrectionCreate(
            processing_result_id=processing_result.id,
            correction_action=UserCorrectionAction.ADJUST_CROP,
            crop_coordinates={"left": 10, "top": 20, "right": 100, "bottom": 150},
            rejection_reason="Poor crop quality",
            correction_time_ms=1500,
        )
        
        correction = correction_repo.create(test_user.id, correction_data)
        
        assert correction is not None
        assert correction.processing_result_id == processing_result.id
        assert correction.correction_action == UserCorrectionAction.ADJUST_CROP.value

    def test_get_by_processing_result(self, db_session, test_user):
        """Test getting corrections by processing result."""
        # Create processing result and corrections
        result_repo = ImageProcessingResultRepository(db_session)
        result_data = ImageProcessingResultCreate(
            original_image_path="/path/to/original.jpg",
            processing_method="rembg",
        )
        processing_result = result_repo.create(test_user.id, result_data)
        
        correction_repo = ImageCorrectionRepository(db_session)
        
        # Create multiple corrections
        for action in [UserCorrectionAction.ACCEPT_PROCESSED, UserCorrectionAction.ADJUST_CROP]:
            correction_data = ImageCorrectionCreate(
                processing_result_id=processing_result.id,
                correction_action=action,
            )
            correction_repo.create(test_user.id, correction_data)
        
        corrections = correction_repo.get_by_processing_result(processing_result.id)
        assert len(corrections) == 2

    def test_get_by_action(self, db_session, test_user):
        """Test getting corrections by action type."""
        # Create processing result
        result_repo = ImageProcessingResultRepository(db_session)
        result_data = ImageProcessingResultCreate(
            original_image_path="/path/to/original.jpg",
            processing_method="rembg",
        )
        processing_result = result_repo.create(test_user.id, result_data)
        
        correction_repo = ImageCorrectionRepository(db_session)
        correction_data = ImageCorrectionCreate(
            processing_result_id=processing_result.id,
            correction_action=UserCorrectionAction.MARK_GARBAGE,
        )
        correction_repo.create(test_user.id, correction_data)
        
        corrections = correction_repo.get_by_action(UserCorrectionAction.MARK_GARBAGE)
        assert len(corrections) == 1
        assert corrections[0].correction_action == UserCorrectionAction.MARK_GARBAGE.value


class TestPrerequisiteCheckResultRepository:
    """Test PrerequisiteCheckResultRepository."""

    def test_create_prerequisite_check_result(self, db_session, test_user):
        """Test creating a prerequisite check result."""
        repo = PrerequisiteCheckResultRepository(db_session)
        
        result_data = PrerequisiteCheckResultCreate(
            user_id=test_user.id,
            operation_name="image_generation",
            checker_name="OllamaConnectivityChecker",
            check_type=PrerequisiteCheckType.REQUIRED,
            status=PrerequisiteCheckResultStatus.PASSED,
            message="Ollama service is accessible",
            details="Connected successfully",
            resolution_steps=["Check installation"],
            check_time_ms=250,
            confidence_score=95,
        )
        
        result = repo.create(result_data)
        
        assert result is not None
        assert result.operation_name == "image_generation"
        assert result.checker_name == "OllamaConnectivityChecker"
        assert result.status == PrerequisiteCheckResultStatus.PASSED.value

    def test_get_by_operation(self, db_session, test_user):
        """Test getting results by operation."""
        repo = PrerequisiteCheckResultRepository(db_session)
        
        # Create results for different operations
        for operation in ["image_generation", "chat"]:
            result_data = PrerequisiteCheckResultCreate(
                user_id=test_user.id,
                operation_name=operation,
                checker_name="TestChecker",
                check_type=PrerequisiteCheckType.REQUIRED,
                status=PrerequisiteCheckResultStatus.PASSED,
                message="Test message",
            )
            repo.create(result_data)
        
        results = repo.get_by_operation("image_generation", test_user.id)
        assert len(results) == 1
        assert results[0].operation_name == "image_generation"

    def test_get_latest_by_checker(self, db_session, test_user):
        """Test getting latest result by checker."""
        repo = PrerequisiteCheckResultRepository(db_session)
        
        # Create multiple results for same checker
        for i in range(3):
            result_data = PrerequisiteCheckResultCreate(
                user_id=test_user.id,
                operation_name="test_operation",
                checker_name="TestChecker",
                check_type=PrerequisiteCheckType.REQUIRED,
                status=PrerequisiteCheckResultStatus.PASSED,
                message=f"Test message {i}",
            )
            repo.create(result_data)
        
        latest = repo.get_latest_by_checker("TestChecker", "test_operation", test_user.id)
        assert latest is not None
        # Latest should be one of the created messages
        assert latest.message in ["Test message 0", "Test message 1", "Test message 2"]

    def test_cleanup_old_results(self, db_session, test_user):
        """Test cleaning up old results."""
        repo = PrerequisiteCheckResultRepository(db_session)
        
        # Create an old result
        result_data = PrerequisiteCheckResultCreate(
            user_id=test_user.id,
            operation_name="test_operation",
            checker_name="TestChecker",
            check_type=PrerequisiteCheckType.REQUIRED,
            status=PrerequisiteCheckResultStatus.PASSED,
            message="Old result",
        )
        result = repo.create(result_data)
        
        # Manually set created_at to be old
        result.created_at = datetime.utcnow() - timedelta(days=35)
        db_session.commit()
        
        deleted_count = repo.cleanup_old_results(days_to_keep=30)
        assert deleted_count == 1


class TestTooltipInteractionRepository:
    """Test TooltipInteractionRepository."""

    def test_create_tooltip_interaction(self, db_session, test_user):
        """Test creating a tooltip interaction."""
        repo = TooltipInteractionRepository(db_session)
        
        interaction_data = TooltipInteractionCreate(
            user_id=test_user.id,
            session_id="session_123",
            element_id="register_button",
            tooltip_content_id="registration_help",
            interaction_type=TooltipInteractionType.HOVER,
            page_context="registration_page",
            tooltip_title="Registration Help",
            tooltip_description="Click to create your account",
            display_time_ms=2500,
        )
        
        interaction = repo.create(interaction_data)
        
        assert interaction is not None
        assert interaction.element_id == "register_button"
        assert interaction.interaction_type == TooltipInteractionType.HOVER.value

    def test_get_by_element(self, db_session, test_user):
        """Test getting interactions by element."""
        repo = TooltipInteractionRepository(db_session)
        
        # Create interactions for different elements
        for element in ["button1", "button2"]:
            interaction_data = TooltipInteractionCreate(
                user_id=test_user.id,
                element_id=element,
                interaction_type=TooltipInteractionType.HOVER,
            )
            repo.create(interaction_data)
        
        interactions = repo.get_by_element("button1")
        assert len(interactions) == 1
        assert interactions[0].element_id == "button1"

    def test_get_interaction_stats(self, db_session, test_user):
        """Test getting interaction statistics."""
        repo = TooltipInteractionRepository(db_session)
        
        # Create multiple interactions
        for i in range(3):
            interaction_data = TooltipInteractionCreate(
                user_id=test_user.id,
                element_id="test_element",
                interaction_type=TooltipInteractionType.HOVER,
                display_time_ms=1000 + i * 500,
            )
            repo.create(interaction_data)
        
        stats = repo.get_interaction_stats("test_element")
        
        assert stats["total_interactions"] == 3
        assert stats["unique_users"] == 1
        assert TooltipInteractionType.HOVER.value in stats["interaction_types"]
        assert stats["avg_display_time_ms"] == 1500  # Average of 1000, 1500, 2000


class TestUXAuditLogRepository:
    """Test UXAuditLogRepository."""

    def test_create_ux_audit_log(self, db_session, test_user):
        """Test creating a UX audit log entry."""
        repo = UXAuditLogRepository(db_session)
        
        log_data = UXAuditLogCreate(
            user_id=test_user.id,
            session_id="session_456",
            event_type=UXEventType.IMAGE_CORRECTION_STARTED,
            event_context="image_generation_flow",
            event_data={"image_id": "img_123"},
            workflow_step="image_correction",
            success=True,
            duration_ms=3500,
        )
        
        log_entry = repo.create(log_data)
        
        assert log_entry is not None
        assert log_entry.event_type == UXEventType.IMAGE_CORRECTION_STARTED.value
        assert log_entry.success is True

    def test_get_by_event_type(self, db_session, test_user):
        """Test getting logs by event type."""
        repo = UXAuditLogRepository(db_session)
        
        # Create logs with different event types
        for event_type in [UXEventType.IMAGE_CORRECTION_STARTED, UXEventType.TOOLTIP_HELP_ACCESSED]:
            log_data = UXAuditLogCreate(
                user_id=test_user.id,
                event_type=event_type,
            )
            repo.create(log_data)
        
        logs = repo.get_by_event_type(UXEventType.IMAGE_CORRECTION_STARTED.value)
        assert len(logs) == 1
        assert logs[0].event_type == UXEventType.IMAGE_CORRECTION_STARTED.value

    def test_get_workflow_analytics(self, db_session, test_user):
        """Test getting workflow analytics."""
        repo = UXAuditLogRepository(db_session)
        
        # Create logs with different success states
        for success in [True, False, True]:
            log_data = UXAuditLogCreate(
                user_id=test_user.id,
                event_type=UXEventType.IMAGE_CORRECTION_STARTED,
                workflow_step="image_correction",
                success=success,
                duration_ms=2000,
                error_message="Test error" if not success else None,
            )
            repo.create(log_data)
        
        analytics = repo.get_workflow_analytics("image_correction")
        
        assert analytics["total_events"] == 3
        assert abs(analytics["success_rate"] - 66.67) < 0.01  # 2 out of 3 successful
        assert analytics["avg_duration_ms"] == 2000
        assert UXEventType.IMAGE_CORRECTION_STARTED.value in analytics["event_types"]

    def test_cleanup_old_logs(self, db_session, test_user):
        """Test cleaning up old logs."""
        repo = UXAuditLogRepository(db_session)
        
        # Create an old log
        log_data = UXAuditLogCreate(
            user_id=test_user.id,
            event_type=UXEventType.IMAGE_CORRECTION_STARTED,
        )
        log_entry = repo.create(log_data)
        
        # Manually set created_at to be old
        log_entry.created_at = datetime.utcnow() - timedelta(days=95)
        db_session.commit()
        
        deleted_count = repo.cleanup_old_logs(days_to_keep=90)
        assert deleted_count == 1


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