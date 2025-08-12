"""
Integration tests for onboarding system.
Tests the complete onboarding flow integration between UI and logic layers.
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.data.models import ConsentType
from src.logic.onboarding import OnboardingLogic, OnboardingStatus, OnboardingStep
from src.ui.onboarding_ui import OnboardingUI


class TestOnboardingIntegration:
    """Integration tests for onboarding system."""

    @pytest.fixture
    def mock_onboarding_logic(self):
        """Mock onboarding logic."""
        mock = Mock(spec=OnboardingLogic)
        mock.flow_steps = [
            OnboardingStep.CONSENT,
            OnboardingStep.SURVEY,
            OnboardingStep.DESIGN,
            OnboardingStep.CHAT,
            OnboardingStep.IMAGE_GENERATION,
            OnboardingStep.FEEDBACK,
            OnboardingStep.COMPLETE,
        ]
        return mock

    @pytest.fixture
    def mock_consent_service(self):
        """Mock consent service."""
        return Mock()

    @pytest.fixture
    def onboarding_ui(self, mock_onboarding_logic, mock_consent_service):
        """Create OnboardingUI with mocked dependencies."""
        ui = OnboardingUI()
        ui.onboarding_logic = mock_onboarding_logic
        ui.consent_service = mock_consent_service
        return ui

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return uuid4()

    def test_onboarding_flow_new_user(self, onboarding_ui, mock_onboarding_logic, sample_user_id):
        """Test onboarding flow for new user."""
        # Setup mock for new user
        mock_onboarding_logic.get_user_onboarding_state.return_value = {
            "user_id": sample_user_id,
            "status": OnboardingStatus.IN_PROGRESS,
            "current_step": OnboardingStep.CONSENT,
            "completed_steps": [],
            "progress": 0.0,
            "personalization_data": {},
            "onboarding_complete": False,
        }

        mock_onboarding_logic.can_access_step.return_value = (True, None)

        # Test that UI can handle new user state
        with (
            patch("streamlit.title"),
            patch("streamlit.write"),
            patch("streamlit.progress"),
            patch("streamlit.columns"),
            patch("src.ui.onboarding_ui.render_onboarding_consent") as mock_consent,
        ):

            mock_consent.return_value = False  # Consent not yet given

            result = onboarding_ui.render_guided_onboarding_flow(sample_user_id)

            # Assertions
            assert result is False  # Onboarding not complete
            mock_onboarding_logic.get_user_onboarding_state.assert_called_once_with(sample_user_id)
            mock_onboarding_logic.can_access_step.assert_called_once_with(
                sample_user_id, OnboardingStep.CONSENT
            )

    def test_onboarding_flow_completed_user(
        self, onboarding_ui, mock_onboarding_logic, sample_user_id
    ):
        """Test onboarding flow for completed user."""
        # Setup mock for completed user
        mock_onboarding_logic.get_user_onboarding_state.return_value = {
            "user_id": sample_user_id,
            "status": OnboardingStatus.COMPLETED,
            "current_step": OnboardingStep.COMPLETE,
            "completed_steps": [
                OnboardingStep.CONSENT,
                OnboardingStep.SURVEY,
                OnboardingStep.DESIGN,
                OnboardingStep.CHAT,
                OnboardingStep.IMAGE_GENERATION,
                OnboardingStep.FEEDBACK,
            ],
            "progress": 1.0,
            "personalization_data": {},
            "onboarding_complete": True,
        }

        # Test that UI returns True for completed user
        result = onboarding_ui.render_guided_onboarding_flow(sample_user_id)

        # Assertions
        assert result is True  # Onboarding complete
        mock_onboarding_logic.get_user_onboarding_state.assert_called_once_with(sample_user_id)

    def test_step_completion_advancement(
        self, onboarding_ui, mock_onboarding_logic, sample_user_id
    ):
        """Test step completion and advancement."""
        # Setup mock for step completion
        mock_onboarding_logic.advance_to_next_step.return_value = OnboardingStep.SURVEY
        mock_onboarding_logic.collect_personalization_data = Mock()

        step_data = {"step": "consent", "completed": True, "data": {"consent_given": True}}

        # Test step completion handling
        with patch("streamlit.session_state", {}), patch("streamlit.rerun") as mock_rerun:

            result = onboarding_ui._handle_step_completion(
                sample_user_id, OnboardingStep.CONSENT, step_data
            )

            # Assertions
            assert result is False  # Not complete yet
            mock_onboarding_logic.collect_personalization_data.assert_called_once()
            mock_onboarding_logic.advance_to_next_step.assert_called_once()
            mock_rerun.assert_called_once()

    def test_step_completion_final_step(self, onboarding_ui, mock_onboarding_logic, sample_user_id):
        """Test completion of final step."""
        # Setup mock for final step completion
        mock_onboarding_logic.advance_to_next_step.return_value = OnboardingStep.COMPLETE

        step_data = {"step": "feedback", "completed": True, "data": {"feedback_given": True}}

        # Test final step completion
        with patch("streamlit.session_state", {}) as mock_session:

            result = onboarding_ui._handle_step_completion(
                sample_user_id, OnboardingStep.FEEDBACK, step_data
            )

            # Assertions
            assert result is True  # Onboarding complete
            assert mock_session.get("onboarding_complete") is True

    def test_consent_blocking(self, onboarding_ui, mock_onboarding_logic, sample_user_id):
        """Test consent blocking functionality."""
        # Setup mock for consent blocking
        mock_onboarding_logic.can_access_step.return_value = (
            False,
            "Missing required consent: data_processing",
        )

        # Test that blocked step shows error
        with patch("streamlit.error") as mock_error:

            result = onboarding_ui._render_current_step(
                sample_user_id, OnboardingStep.SURVEY, {"current_step": OnboardingStep.SURVEY.value}
            )

            # Assertions
            assert result is None  # Cannot proceed
            mock_error.assert_called_once()
            mock_onboarding_logic.can_access_step.assert_called_once_with(
                sample_user_id, OnboardingStep.SURVEY
            )

    def test_personalization_data_collection(
        self, onboarding_ui, mock_onboarding_logic, sample_user_id
    ):
        """Test personalization data collection."""
        # Setup test data
        survey_data = {
            "learning_preferences": {
                "learning_style": "visual",
                "difficulty_preference": "intermediate",
            }
        }

        # Test data collection
        with patch("src.ui.onboarding_ui.render_personalization_survey") as mock_survey:
            mock_survey.return_value = survey_data

            result = onboarding_ui._render_survey_step(sample_user_id)

            # Assertions
            assert result is not None
            assert result["completed"] is True
            assert result["data"] == survey_data
            mock_survey.assert_called_once_with(sample_user_id)

    def test_onboarding_summary_display(self, onboarding_ui, mock_onboarding_logic, sample_user_id):
        """Test onboarding summary display."""
        # Setup mock summary data
        mock_summary = {
            "user_id": sample_user_id,
            "onboarding_status": OnboardingStatus.IN_PROGRESS,
            "completion_progress": 0.6,
            "completed_steps": 4,
            "total_steps": 7,
            "current_step": OnboardingStep.CHAT,
            "consents_given": 3,
            "total_consent_types": 5,
            "learning_preferences": {"learning_style": "visual"},
            "embodiment_design": {"appearance_style": "friendly"},
            "survey_completed": True,
            "onboarding_completed": False,
        }

        mock_onboarding_logic.get_onboarding_summary.return_value = mock_summary

        # Test summary rendering
        with (
            patch("streamlit.subheader"),
            patch("streamlit.columns"),
            patch("streamlit.metric"),
            patch("streamlit.expander"),
        ):

            onboarding_ui.render_onboarding_summary(sample_user_id)

            # Assertions
            mock_onboarding_logic.get_onboarding_summary.assert_called_once_with(sample_user_id)

    def test_error_handling_in_ui(self, onboarding_ui, mock_onboarding_logic, sample_user_id):
        """Test error handling in UI components."""
        # Setup mock to raise exception
        mock_onboarding_logic.get_user_onboarding_state.side_effect = Exception("Database error")

        # Test error handling
        with patch("streamlit.error") as mock_error:

            result = onboarding_ui.render_guided_onboarding_flow(sample_user_id)

            # Assertions
            assert result is False
            mock_error.assert_called_once()

    def test_flow_step_navigation(self, onboarding_ui, mock_onboarding_logic, sample_user_id):
        """Test navigation through onboarding steps."""
        # Test each step can be rendered
        steps_to_test = [
            OnboardingStep.CONSENT,
            OnboardingStep.SURVEY,
            OnboardingStep.DESIGN,
            OnboardingStep.CHAT,
            OnboardingStep.IMAGE_GENERATION,
            OnboardingStep.FEEDBACK,
            OnboardingStep.COMPLETE,
        ]

        mock_onboarding_logic.can_access_step.return_value = (True, None)

        for step in steps_to_test:
            with (
                patch("streamlit.subheader"),
                patch("streamlit.write"),
                patch("streamlit.button"),
                patch("src.ui.onboarding_ui.render_onboarding_consent"),
                patch("src.ui.onboarding_ui.render_personalization_survey"),
                patch("src.ui.onboarding_ui.render_embodiment_design_chat"),
                patch("src.ui.onboarding_ui.render_chat_interface"),
                patch("src.ui.onboarding_ui.render_image_generation_interface"),
            ):

                # Test that each step can be rendered without error
                onboarding_ui._render_current_step(
                    sample_user_id, step, {"personalization_data": {}}
                )

                # Should not raise exception
                # Result can be None if step is not completed

    def test_automated_flow_progression(self, onboarding_ui, mock_onboarding_logic, sample_user_id):
        """Test automated flow progression without manual intervention."""
        # Setup sequence of states for automated progression
        states = [
            {
                "current_step": OnboardingStep.CONSENT,
                "completed_steps": [],
                "onboarding_complete": False,
            },
            {
                "current_step": OnboardingStep.SURVEY,
                "completed_steps": [OnboardingStep.CONSENT],
                "onboarding_complete": False,
            },
            {
                "current_step": OnboardingStep.COMPLETE,
                "completed_steps": [OnboardingStep.CONSENT, OnboardingStep.SURVEY],
                "onboarding_complete": True,
            },
        ]

        # Mock progression through states
        mock_onboarding_logic.get_user_onboarding_state.side_effect = states
        mock_onboarding_logic.can_access_step.return_value = (True, None)
        mock_onboarding_logic.advance_to_next_step.side_effect = [
            OnboardingStep.SURVEY,
            OnboardingStep.COMPLETE,
        ]

        # Test automated progression
        with (
            patch("src.ui.onboarding_ui.render_onboarding_consent") as mock_consent,
            patch("streamlit.session_state", {}),
            patch("streamlit.rerun"),
        ):

            # First call - consent step
            mock_consent.return_value = {"step": "consent", "completed": True}
            result1 = onboarding_ui.render_guided_onboarding_flow(sample_user_id)

            # Should progress automatically
            assert result1 is False  # Not complete yet

            # Final call - complete step
            result2 = onboarding_ui.render_guided_onboarding_flow(sample_user_id)
            assert result2 is True  # Complete


class TestOnboardingLogicIntegration:
    """Integration tests for onboarding logic with real dependencies."""

    def test_onboarding_state_persistence(self):
        """Test that onboarding state is properly managed."""
        # This would test with real database in full integration test
        # For now, just test the logic structure

        from src.logic.onboarding import OnboardingLogic

        # Mock dependencies
        mock_user_repo = Mock()
        mock_consent_service = Mock()
        mock_pald_manager = Mock()

        logic = OnboardingLogic(mock_user_repo, mock_consent_service, mock_pald_manager)

        # Test flow steps are properly defined
        assert len(logic.flow_steps) == 7
        assert OnboardingStep.CONSENT in logic.flow_steps
        assert OnboardingStep.COMPLETE in logic.flow_steps

        # Test consent requirements are defined
        assert OnboardingStep.SURVEY in logic.step_consent_requirements
        assert ConsentType.DATA_PROCESSING in logic.step_consent_requirements[OnboardingStep.SURVEY]

    def test_step_advancement_logic(self):
        """Test step advancement logic."""
        from src.logic.onboarding import OnboardingLogic

        # Mock dependencies
        mock_user_repo = Mock()
        mock_consent_service = Mock()
        mock_pald_manager = Mock()

        logic = OnboardingLogic(mock_user_repo, mock_consent_service, mock_pald_manager)

        # Test step sequence
        steps = logic.flow_steps
        for i in range(len(steps) - 1):
            current_step = steps[i]
            expected_next = steps[i + 1]

            # Mock the advance method behavior
            with (
                patch.object(logic, "_store_step_data"),
                patch.object(logic, "_mark_step_completed"),
                patch.object(logic, "_complete_onboarding"),
            ):

                next_step = logic.advance_to_next_step(uuid4(), current_step)
                assert next_step == expected_next
