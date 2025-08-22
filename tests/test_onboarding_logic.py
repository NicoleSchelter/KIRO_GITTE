"""
Unit tests for onboarding logic.
Tests the guided onboarding flow orchestration, state management, and personalization data collection.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.data.models import ConsentType
from src.data.schemas import PALDDataCreate
from src.logic.onboarding import (
    OnboardingError,
    OnboardingFlowError,
    OnboardingLogic,
    OnboardingStateError,
    OnboardingStatus,
    OnboardingStep,
)


class TestOnboardingLogic:
    """Test cases for OnboardingLogic class."""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return Mock()

    @pytest.fixture
    def mock_consent_service(self):
        """Mock consent service."""
        return Mock()

    @pytest.fixture
    def mock_onboarding_service(self):
        """Mock onboarding progress service."""
        return Mock()

    @pytest.fixture
    def mock_preferences_service(self):
        """Mock user preferences service."""
        return Mock()

    @pytest.fixture
    def onboarding_logic(self, mock_user_repository, mock_consent_service, mock_onboarding_service, mock_preferences_service):
        """Create OnboardingLogic instance with mocked dependencies."""
        return OnboardingLogic(
            user_repository=mock_user_repository,
            consent_service=mock_consent_service,
            onboarding_service=mock_onboarding_service,
            preferences_service=mock_preferences_service,
        )

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_pald_data(self):
        """Sample PALD data for testing."""
        return [
            Mock(
                pald_content={
                    "survey_completed_at": "2024-01-15T10:30:00",
                    "learning_preferences": {
                        "learning_style": "visual",
                        "difficulty_preference": "intermediate",
                    },
                }
            ),
            Mock(
                pald_content={
                    "embodiment_characteristics": {
                        "appearance_style": "friendly",
                        "personality": "encouraging",
                    }
                }
            ),
        ]

    def test_init(self, onboarding_logic):
        """Test OnboardingLogic initialization."""
        assert onboarding_logic is not None
        assert len(onboarding_logic.flow_steps) == 7
        assert OnboardingStep.CONSENT in onboarding_logic.flow_steps
        assert OnboardingStep.COMPLETE in onboarding_logic.flow_steps

        # Check consent requirements are defined
        assert OnboardingStep.SURVEY in onboarding_logic.step_consent_requirements
        assert (
            ConsentType.DATA_PROCESSING
            in onboarding_logic.step_consent_requirements[OnboardingStep.SURVEY]
        )

    def test_get_user_onboarding_state_new_user(
        self, onboarding_logic, sample_user_id, mock_pald_manager, mock_consent_service
    ):
        """Test getting onboarding state for new user."""
        # Setup mocks
        mock_pald_manager.get_user_pald_data.return_value = []
        mock_consent_service.get_consent_status.return_value = {
            ConsentType.DATA_PROCESSING.value: False,
            ConsentType.AI_INTERACTION.value: False,
        }

        # Get state
        state = onboarding_logic.get_user_onboarding_state(sample_user_id)

        # Assertions
        assert state["user_id"] == sample_user_id
        assert state["status"] == OnboardingStatus.IN_PROGRESS
        assert state["current_step"] == OnboardingStep.CONSENT
        assert state["completed_steps"] == []
        assert state["progress"] == 0.0
        assert not state["onboarding_complete"]

    def test_get_user_onboarding_state_partial_completion(
        self, onboarding_logic, sample_user_id, mock_pald_manager, mock_consent_service
    ):
        """Test getting onboarding state for partially completed user."""
        # Setup mocks
        mock_pald_manager.get_user_pald_data.return_value = [
            Mock(
                pald_content={
                    "survey_completed_at": "2024-01-15T10:30:00",
                    "learning_preferences": {"learning_style": "visual"},
                }
            )
        ]
        mock_consent_service.get_consent_status.return_value = {
            ConsentType.DATA_PROCESSING.value: True,
            ConsentType.AI_INTERACTION.value: False,
        }

        # Get state
        state = onboarding_logic.get_user_onboarding_state(sample_user_id)

        # Assertions
        assert state["status"] == OnboardingStatus.IN_PROGRESS
        assert OnboardingStep.CONSENT in state["completed_steps"]
        assert OnboardingStep.SURVEY in state["completed_steps"]
        assert state["current_step"] == OnboardingStep.DESIGN
        assert state["progress"] > 0.0
        assert not state["onboarding_complete"]

    def test_get_user_onboarding_state_completed(
        self, onboarding_logic, sample_user_id, mock_pald_manager, mock_consent_service
    ):
        """Test getting onboarding state for completed user."""
        # Setup mocks
        mock_pald_manager.get_user_pald_data.return_value = [
            Mock(
                pald_content={
                    "onboarding_completed_at": "2024-01-15T12:00:00",
                    "survey_completed_at": "2024-01-15T10:30:00",
                    "embodiment_characteristics": {"appearance_style": "friendly"},
                }
            )
        ]
        mock_consent_service.get_consent_status.return_value = {
            ConsentType.DATA_PROCESSING.value: True,
            ConsentType.AI_INTERACTION.value: True,
        }

        # Get state
        state = onboarding_logic.get_user_onboarding_state(sample_user_id)

        # Assertions
        assert state["status"] == OnboardingStatus.COMPLETED
        assert state["current_step"] == OnboardingStep.COMPLETE
        assert state["onboarding_complete"]
        assert state["progress"] > 0.8  # Should be high completion

    def test_can_access_step_consent_required(
        self, onboarding_logic, sample_user_id, mock_consent_service
    ):
        """Test step access when consent is required."""
        # Setup mock - no consent given
        mock_consent_service.check_consent.return_value = False

        # Test access to survey step (requires data processing consent)
        can_access, reason = onboarding_logic.can_access_step(sample_user_id, OnboardingStep.SURVEY)

        # Assertions
        assert not can_access
        assert "consent" in reason.lower()
        assert ConsentType.DATA_PROCESSING.value in reason

    def test_can_access_step_prerequisite_required(
        self, onboarding_logic, sample_user_id, mock_consent_service, mock_pald_manager
    ):
        """Test step access when prerequisite steps are required."""
        # Setup mocks
        mock_consent_service.check_consent.return_value = True
        mock_pald_manager.get_user_pald_data.return_value = []
        mock_consent_service.get_consent_status.return_value = {
            ConsentType.DATA_PROCESSING.value: False
        }

        # Test access to design step when user is still on consent
        can_access, reason = onboarding_logic.can_access_step(sample_user_id, OnboardingStep.DESIGN)

        # Assertions
        assert not can_access
        assert "complete step" in reason.lower()

    def test_can_access_step_allowed(
        self, onboarding_logic, sample_user_id, mock_consent_service, mock_pald_manager
    ):
        """Test step access when allowed."""
        # Setup mocks
        mock_consent_service.check_consent.return_value = True
        mock_pald_manager.get_user_pald_data.return_value = []
        mock_consent_service.get_consent_status.return_value = {
            ConsentType.DATA_PROCESSING.value: False
        }

        # Test access to consent step (no prerequisites)
        can_access, reason = onboarding_logic.can_access_step(
            sample_user_id, OnboardingStep.CONSENT
        )

        # Assertions
        assert can_access
        assert reason is None

    def test_advance_to_next_step(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test advancing to next step."""
        # Setup mock
        mock_pald_manager.create_pald_data = Mock()

        # Test advancing from consent to survey
        next_step = onboarding_logic.advance_to_next_step(
            sample_user_id, OnboardingStep.CONSENT, {"consent_data": "test"}
        )

        # Assertions
        assert next_step == OnboardingStep.SURVEY
        assert (
            mock_pald_manager.create_pald_data.call_count >= 1
        )  # Called for step data and completion

    def test_advance_to_complete_step(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test advancing to complete step."""
        # Setup mock
        mock_pald_manager.create_pald_data = Mock()

        # Test advancing from feedback to complete
        next_step = onboarding_logic.advance_to_next_step(sample_user_id, OnboardingStep.FEEDBACK)

        # Assertions
        assert next_step == OnboardingStep.COMPLETE
        # Should call create_pald_data for completion marker
        assert mock_pald_manager.create_pald_data.call_count >= 1

    def test_collect_personalization_data(
        self, onboarding_logic, sample_user_id, mock_pald_manager
    ):
        """Test collecting personalization data."""
        # Setup mock
        mock_pald_manager.create_pald_data = Mock()

        # Test data collection
        test_data = {"learning_style": "visual", "difficulty": "intermediate"}
        onboarding_logic.collect_personalization_data(sample_user_id, "survey", test_data)

        # Assertions
        mock_pald_manager.create_pald_data.assert_called_once()
        call_args = mock_pald_manager.create_pald_data.call_args

        assert call_args[0][0] == sample_user_id  # user_id
        pald_create = call_args[0][1]
        assert isinstance(pald_create, PALDDataCreate)
        assert pald_create.pald_content["data_type"] == "survey"
        assert pald_create.pald_content["learning_style"] == "visual"

    def test_get_onboarding_summary(
        self, onboarding_logic, sample_user_id, mock_pald_manager, mock_consent_service
    ):
        """Test getting onboarding summary."""
        # Setup mocks
        mock_pald_manager.get_user_pald_data.return_value = [
            Mock(
                pald_content={
                    "survey_completed_at": "2024-01-15T10:30:00",
                    "learning_preferences": {"learning_style": "visual"},
                }
            )
        ]
        mock_consent_service.get_consent_status.return_value = {
            ConsentType.DATA_PROCESSING.value: True,
            ConsentType.AI_INTERACTION.value: False,
            ConsentType.IMAGE_GENERATION.value: False,
        }

        # Get summary
        summary = onboarding_logic.get_onboarding_summary(sample_user_id)

        # Assertions
        assert summary["user_id"] == sample_user_id
        assert summary["onboarding_status"] == OnboardingStatus.IN_PROGRESS
        assert summary["consents_given"] == 1
        assert summary["total_consent_types"] == 3
        assert summary["survey_completed"]
        assert not summary["onboarding_completed"]

    def test_reset_onboarding(self, onboarding_logic, sample_user_id):
        """Test resetting onboarding (should log without error)."""
        # This should not raise an exception
        onboarding_logic.reset_onboarding(sample_user_id)

    def test_store_step_data(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test storing step data."""
        # Setup mock
        mock_pald_manager.create_pald_data = Mock()

        # Test storing step data
        test_data = {"test": "data"}
        onboarding_logic._store_step_data(sample_user_id, OnboardingStep.SURVEY, test_data)

        # Assertions
        mock_pald_manager.create_pald_data.assert_called_once()
        call_args = mock_pald_manager.create_pald_data.call_args
        pald_create = call_args[0][1]
        assert pald_create.pald_content["step"] == OnboardingStep.SURVEY.value
        assert pald_create.pald_content["step_data"] == test_data

    def test_mark_step_completed(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test marking step as completed."""
        # Setup mock
        mock_pald_manager.create_pald_data = Mock()

        # Test marking step completed
        onboarding_logic._mark_step_completed(sample_user_id, OnboardingStep.CONSENT)

        # Assertions
        mock_pald_manager.create_pald_data.assert_called_once()
        call_args = mock_pald_manager.create_pald_data.call_args
        pald_create = call_args[0][1]
        assert pald_create.pald_content["step_completed"] == OnboardingStep.CONSENT.value

    def test_complete_onboarding(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test completing onboarding."""
        # Setup mock
        mock_pald_manager.create_pald_data = Mock()

        # Test completing onboarding
        onboarding_logic._complete_onboarding(sample_user_id)

        # Assertions
        mock_pald_manager.create_pald_data.assert_called_once()
        call_args = mock_pald_manager.create_pald_data.call_args
        pald_create = call_args[0][1]
        assert pald_create.pald_content["all_steps_completed"]
        assert "onboarding_completed_at" in pald_create.pald_content

    def test_error_handling_get_state(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test error handling in get_user_onboarding_state."""
        # Setup mock to raise exception
        mock_pald_manager.get_user_pald_data.side_effect = Exception("Database error")

        # Test that exception is properly wrapped
        with pytest.raises(OnboardingStateError):
            onboarding_logic.get_user_onboarding_state(sample_user_id)

    def test_error_handling_advance_step(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test error handling in advance_to_next_step."""
        # Setup mock to raise exception
        mock_pald_manager.create_pald_data.side_effect = Exception("Database error")

        # Test that exception is properly wrapped
        with pytest.raises(OnboardingFlowError):
            onboarding_logic.advance_to_next_step(sample_user_id, OnboardingStep.CONSENT)

    def test_error_handling_collect_data(self, onboarding_logic, sample_user_id, mock_pald_manager):
        """Test error handling in collect_personalization_data."""
        # Setup mock to raise exception
        mock_pald_manager.create_pald_data.side_effect = Exception("Database error")

        # Test that exception is properly wrapped
        with pytest.raises(OnboardingError):
            onboarding_logic.collect_personalization_data(sample_user_id, "test", {})


class TestOnboardingEnums:
    """Test cases for onboarding enums."""

    def test_onboarding_step_enum(self):
        """Test OnboardingStep enum values."""
        assert OnboardingStep.CONSENT.value == "consent"
        assert OnboardingStep.SURVEY.value == "survey"
        assert OnboardingStep.DESIGN.value == "design"
        assert OnboardingStep.CHAT.value == "chat"
        assert OnboardingStep.IMAGE_GENERATION.value == "image_generation"
        assert OnboardingStep.FEEDBACK.value == "feedback"
        assert OnboardingStep.COMPLETE.value == "complete"

    def test_onboarding_status_enum(self):
        """Test OnboardingStatus enum values."""
        assert OnboardingStatus.NOT_STARTED.value == "not_started"
        assert OnboardingStatus.IN_PROGRESS.value == "in_progress"
        assert OnboardingStatus.COMPLETED.value == "completed"
        assert OnboardingStatus.ABANDONED.value == "abandoned"


class TestOnboardingExceptions:
    """Test cases for onboarding exceptions."""

    def test_onboarding_error(self):
        """Test OnboardingError exception."""
        error = OnboardingError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_onboarding_flow_error(self):
        """Test OnboardingFlowError exception."""
        error = OnboardingFlowError("Flow error")
        assert str(error) == "Flow error"
        assert isinstance(error, OnboardingError)

    def test_onboarding_state_error(self):
        """Test OnboardingStateError exception."""
        error = OnboardingStateError("State error")
        assert str(error) == "State error"
        assert isinstance(error, OnboardingError)


def test_get_onboarding_logic():
    """Test get_onboarding_logic factory function."""
    with (
        patch("src.data.repositories.get_user_repository") as mock_user_repo,
        patch("src.services.consent_service.get_consent_service") as mock_consent_service,
        patch("src.data.database.get_session") as mock_db_session,
        patch("src.logic.onboarding.PALDManager"),
    ):

        # Setup mocks
        mock_db_session.return_value.__enter__.return_value = Mock()
        mock_db_session.return_value.__exit__.return_value = None

        from src.logic.onboarding import get_onboarding_logic

        # Call factory function
        logic = get_onboarding_logic()

        # Assertions
        assert isinstance(logic, OnboardingLogic)
        mock_user_repo.assert_called_once()
        mock_consent_service.assert_called_once()
        mock_db_session.assert_called()
