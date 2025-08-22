"""
Simplified unit tests for onboarding logic.
Tests the guided onboarding flow orchestration, state management, and personalization data collection.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from src.data.models import ConsentType
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

    def test_init(self, onboarding_logic):
        """Test OnboardingLogic initialization."""
        assert onboarding_logic is not None
        assert hasattr(onboarding_logic, 'flow_steps')
        assert OnboardingStep.CONSENT in onboarding_logic.flow_steps

    def test_get_user_onboarding_state_new_user(
        self, onboarding_logic, sample_user_id, mock_consent_service, mock_onboarding_service
    ):
        """Test getting onboarding state for new user."""
        # Setup mocks
        mock_onboarding_service.get_user_progress.return_value = None
        mock_consent_service.get_consent_status.return_value = {
            ConsentType.DATA_PROCESSING.value: False,
            ConsentType.AI_INTERACTION.value: False,
        }

        # Test
        state = onboarding_logic.get_user_onboarding_state(sample_user_id)

        # Assertions
        assert state["status"] == OnboardingStatus.IN_PROGRESS  # Logic returns IN_PROGRESS for new users
        assert state["current_step"] == OnboardingStep.CONSENT
        assert state["progress"] == 0.0

    def test_can_access_step_consent_required(
        self, onboarding_logic, sample_user_id, mock_consent_service
    ):
        """Test step access when consent is required."""
        # Setup mocks
        mock_consent_service.check_consent.return_value = False

        # Test
        can_access, reason = onboarding_logic.can_access_step(
            sample_user_id, OnboardingStep.SURVEY
        )

        # Assertions
        assert not can_access
        assert "consent" in reason.lower()

    def test_advance_to_next_step(self, onboarding_logic, sample_user_id, mock_onboarding_service):
        """Test advancing to next step."""
        # Setup mock
        mock_onboarding_service.mark_step_completed = Mock()

        # Test advancing from consent to survey
        next_step = onboarding_logic.advance_to_next_step(
            sample_user_id, OnboardingStep.CONSENT
        )

        # Assertions
        assert next_step == OnboardingStep.SURVEY
        mock_onboarding_service.mark_step_completed.assert_called()

    def test_collect_personalization_data(
        self, onboarding_logic, sample_user_id, mock_preferences_service
    ):
        """Test collecting personalization data."""
        # Setup mock
        mock_preferences_service.save_preferences = Mock()

        # Test data collection
        test_data = {"learning_style": "visual", "difficulty": "intermediate"}
        onboarding_logic.collect_personalization_data(sample_user_id, "survey", test_data)

        # Assertions
        mock_preferences_service.save_preferences.assert_called_once()

    def test_complete_onboarding(self, onboarding_logic, sample_user_id, mock_onboarding_service):
        """Test completing onboarding."""
        # Setup mock
        mock_onboarding_service.mark_completed = Mock()

        # Test completing onboarding (using private method)
        onboarding_logic._complete_onboarding(sample_user_id)

        # Assertions
        mock_onboarding_service.complete_onboarding.assert_called_once_with(sample_user_id)


class TestOnboardingEnums:
    """Test cases for onboarding enums."""

    def test_onboarding_step_enum(self):
        """Test OnboardingStep enum values."""
        assert OnboardingStep.CONSENT == "consent"
        assert OnboardingStep.SURVEY == "survey"
        assert OnboardingStep.COMPLETE == "complete"

    def test_onboarding_status_enum(self):
        """Test OnboardingStatus enum values."""
        assert OnboardingStatus.NOT_STARTED == "not_started"
        assert OnboardingStatus.IN_PROGRESS == "in_progress"
        assert OnboardingStatus.COMPLETED == "completed"


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