"""
Unit tests for study participation UI components.
Tests pseudonym creation and consent collection workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID

import streamlit as st

from src.data.models import StudyConsentType
from src.data.schemas import PseudonymResponse, PseudonymValidation
from src.logic.pseudonym_logic import InvalidPseudonymFormatError, PseudonymNotUniqueError, PseudonymError
from src.ui.study_participation_ui import StudyParticipationUI


class TestStudyParticipationUI:
    """Test study participation UI components."""

    @pytest.fixture
    def ui(self):
        """Create StudyParticipationUI instance."""
        return StudyParticipationUI()

    @pytest.fixture
    def user_id(self):
        """Create test user ID."""
        return uuid4()

    @pytest.fixture
    def pseudonym_id(self):
        """Create test pseudonym ID."""
        return uuid4()

    @pytest.fixture
    def mock_pseudonym_response(self, pseudonym_id):
        """Create mock pseudonym response."""
        return PseudonymResponse(
            pseudonym_id=pseudonym_id,
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="test_hash",
            created_at="2024-01-01T00:00:00",
            is_active=True
        )

    @pytest.fixture
    def mock_consent_status(self, pseudonym_id):
        """Create mock consent status."""
        return {
            "pseudonym_id": pseudonym_id,
            "consent_status": {
                "data_protection": True,
                "ai_interaction": True,
                "study_participation": True
            },
            "all_required_granted": True,
            "granted_count": 3,
            "total_count": 3,
            "completion_rate": 1.0,
            "can_proceed_to_study": True
        }

    @patch("src.ui.study_participation_ui.st")
    def test_render_pseudonym_creation_new_user(self, mock_st, ui, user_id):
        """Test pseudonym creation for new user."""
        # Arrange
        mock_st.title = Mock()
        mock_st.markdown = Mock()
        mock_st.expander = Mock()
        mock_st.form = Mock()
        mock_st.text_input = Mock(return_value="M03s2001AJ13")
        mock_st.success = Mock()
        mock_st.error = Mock()
        mock_st.info = Mock()
        mock_st.subheader = Mock()
        
        # Mock columns with context manager support
        col1_mock = Mock()
        col1_mock.__enter__ = Mock(return_value=col1_mock)
        col1_mock.__exit__ = Mock(return_value=None)
        col2_mock = Mock()
        col2_mock.__enter__ = Mock(return_value=col2_mock)
        col2_mock.__exit__ = Mock(return_value=None)
        mock_st.columns = Mock(return_value=[col1_mock, col2_mock])
        
        # Mock form context manager
        form_mock = Mock()
        form_mock.__enter__ = Mock(return_value=form_mock)
        form_mock.__exit__ = Mock(return_value=None)
        mock_st.form.return_value = form_mock
        
        # Mock expander context manager
        expander_mock = Mock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_st.expander.return_value = expander_mock

        ui.pseudonym_service.get_user_pseudonym = Mock(return_value=None)
        ui._validate_pseudonym_format_ui = Mock(return_value={"is_valid": True, "error_message": None})

        with patch("src.ui.study_participation_ui.form_submit_button") as mock_submit:
            mock_submit.return_value = False

            # Act
            result = ui.render_pseudonym_creation(user_id)

            # Assert
            assert result is None
            mock_st.title.assert_called_once_with("🔐 Create Your Study Pseudonym")
            ui.pseudonym_service.get_user_pseudonym.assert_called_once_with(user_id)

    @patch("src.ui.study_participation_ui.st")
    def test_render_pseudonym_creation_existing_user(self, mock_st, ui, user_id, mock_pseudonym_response):
        """Test pseudonym creation for user with existing pseudonym."""
        # Arrange
        mock_st.title = Mock()
        mock_st.success = Mock()
        mock_st.button = Mock(return_value=True)
        
        ui.pseudonym_service.get_user_pseudonym = Mock(return_value=mock_pseudonym_response)
        ui._render_existing_pseudonym_info = Mock()

        # Act
        result = ui.render_pseudonym_creation(user_id)

        # Assert
        assert result is not None
        assert result["pseudonym_created"] is True
        assert result["existing"] is True
        assert result["pseudonym_id"] == mock_pseudonym_response.pseudonym_id
        mock_st.success.assert_called_once_with("✅ You already have a study pseudonym!")

    @patch("src.ui.study_participation_ui.st")
    def test_handle_pseudonym_creation_success(self, mock_st, ui, user_id, mock_pseudonym_response):
        """Test successful pseudonym creation."""
        # Arrange
        mock_st.success = Mock()
        mock_st.balloons = Mock()
        
        ui.pseudonym_service.create_pseudonym = Mock(return_value=mock_pseudonym_response)

        # Act
        result = ui._handle_pseudonym_creation(user_id, "M03s2001AJ13")

        # Assert
        assert result is not None
        assert result["pseudonym_created"] is True
        assert result["existing"] is False
        assert result["pseudonym_id"] == mock_pseudonym_response.pseudonym_id
        mock_st.success.assert_called_once()
        mock_st.balloons.assert_called_once()

    @patch("src.ui.study_participation_ui.st")
    def test_handle_pseudonym_creation_invalid_format(self, mock_st, ui, user_id):
        """Test pseudonym creation with invalid format."""
        # Arrange
        mock_st.error = Mock()
        
        ui.pseudonym_service.create_pseudonym = Mock(
            side_effect=InvalidPseudonymFormatError("Invalid format")
        )

        # Act
        result = ui._handle_pseudonym_creation(user_id, "invalid")

        # Assert
        assert result is None
        mock_st.error.assert_called_once()

    @patch("src.ui.study_participation_ui.st")
    def test_handle_pseudonym_creation_not_unique(self, mock_st, ui, user_id):
        """Test pseudonym creation with non-unique pseudonym."""
        # Arrange
        mock_st.error = Mock()
        mock_st.info = Mock()
        
        ui.pseudonym_service.create_pseudonym = Mock(
            side_effect=PseudonymNotUniqueError("Not unique")
        )

        # Act
        result = ui._handle_pseudonym_creation(user_id, "M03s2001AJ13")

        # Assert
        assert result is None
        mock_st.error.assert_called_once()
        mock_st.info.assert_called_once()

    @patch("src.ui.study_participation_ui.st")
    def test_render_consent_collection_new_user(self, mock_st, ui, pseudonym_id):
        """Test consent collection for new user."""
        # Arrange
        mock_st.title = Mock()
        mock_st.markdown = Mock()
        mock_st.progress = Mock()
        mock_st.form = Mock()
        mock_st.subheader = Mock()
        mock_st.checkbox = Mock(return_value=False)
        mock_st.warning = Mock()
        mock_st.expander = Mock()
        mock_st.divider = Mock()
        
        # Mock columns with context manager support
        col1_mock = Mock()
        col1_mock.__enter__ = Mock(return_value=col1_mock)
        col1_mock.__exit__ = Mock(return_value=None)
        col2_mock = Mock()
        col2_mock.__enter__ = Mock(return_value=col2_mock)
        col2_mock.__exit__ = Mock(return_value=None)
        mock_st.columns = Mock(return_value=[col1_mock, col2_mock])
        
        # Mock form context manager
        form_mock = Mock()
        form_mock.__enter__ = Mock(return_value=form_mock)
        form_mock.__exit__ = Mock(return_value=None)
        mock_st.form.return_value = form_mock
        
        # Mock expander context manager
        expander_mock = Mock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_st.expander.return_value = expander_mock

        ui.consent_service.check_consent_status = Mock(return_value={
            "all_required_granted": False,
            "consent_status": {},
            "granted_count": 0,
            "total_count": 3
        })

        with patch("src.ui.study_participation_ui.form_submit_button") as mock_submit:
            mock_submit.return_value = False

            # Act
            result = ui.render_consent_collection(pseudonym_id)

            # Assert
            assert result is None
            mock_st.title.assert_called_once_with("📋 Study Participation Consent")
            ui.consent_service.check_consent_status.assert_called_once_with(pseudonym_id)

    @patch("src.ui.study_participation_ui.st")
    def test_render_consent_collection_existing_consents(self, mock_st, ui, pseudonym_id, mock_consent_status):
        """Test consent collection for user with existing consents."""
        # Arrange
        mock_st.title = Mock()
        mock_st.success = Mock()
        mock_st.button = Mock(return_value=True)
        
        ui.consent_service.check_consent_status = Mock(return_value=mock_consent_status)
        ui._render_consent_summary = Mock()

        # Act
        result = ui.render_consent_collection(pseudonym_id)

        # Assert
        assert result is not None
        assert result["consents_completed"] is True
        assert result["existing"] is True
        mock_st.success.assert_called_once_with("✅ All required consents have been provided!")

    @patch("src.ui.study_participation_ui.st")
    def test_handle_consent_submission_success(self, mock_st, ui, pseudonym_id):
        """Test successful consent submission."""
        # Arrange
        mock_st.success = Mock()
        mock_st.balloons = Mock()
        
        consents = {
            "data_protection": True,
            "ai_interaction": True,
            "study_participation": True
        }
        
        ui.consent_service.process_consent_collection = Mock(return_value={
            "success": True,
            "can_proceed": True,
            "consent_records": []
        })

        # Act
        result = ui._handle_consent_submission(pseudonym_id, consents, complete=True)

        # Assert
        assert result is not None
        assert result["consents_completed"] is True
        assert result["existing"] is False
        mock_st.success.assert_called_once()
        mock_st.balloons.assert_called_once()

    @patch("src.ui.study_participation_ui.st")
    def test_handle_consent_submission_incomplete(self, mock_st, ui, pseudonym_id):
        """Test consent submission with incomplete consents."""
        # Arrange
        mock_st.warning = Mock()
        
        consents = {
            "data_protection": True,
            "ai_interaction": False,
            "study_participation": True
        }
        
        ui.consent_service.process_consent_collection = Mock(return_value={
            "success": True,
            "can_proceed": False,
            "consent_records": []
        })

        # Act
        result = ui._handle_consent_submission(pseudonym_id, consents, complete=True)

        # Assert
        assert result is None
        mock_st.warning.assert_called_once()

    @patch("src.ui.study_participation_ui.st")
    def test_handle_consent_submission_save_progress(self, mock_st, ui, pseudonym_id):
        """Test saving consent progress."""
        # Arrange
        mock_st.info = Mock()
        
        consents = {
            "data_protection": True,
            "ai_interaction": False,
            "study_participation": False
        }
        
        ui.consent_service.process_consent_collection = Mock(return_value={
            "success": True,
            "can_proceed": False,
            "consent_records": []
        })

        # Act
        result = ui._handle_consent_submission(pseudonym_id, consents, complete=False)

        # Assert
        assert result is None
        mock_st.info.assert_called_once_with("💾 Progress saved successfully!")

    def test_validate_pseudonym_format_ui_valid(self, ui):
        """Test UI pseudonym format validation for valid pseudonym."""
        # Arrange
        ui.pseudonym_service.validate_pseudonym = Mock(return_value=PseudonymValidation(
            is_valid=True,
            is_unique=True,
            error_message=None
        ))

        # Act
        result = ui._validate_pseudonym_format_ui("M03s2001AJ13")

        # Assert
        assert result["is_valid"] is True
        assert result["error_message"] is None

    def test_validate_pseudonym_format_ui_invalid(self, ui):
        """Test UI pseudonym format validation for invalid pseudonym."""
        # Arrange
        ui.pseudonym_service.validate_pseudonym = Mock(return_value=PseudonymValidation(
            is_valid=False,
            is_unique=False,
            error_message="Invalid format"
        ))

        # Act
        result = ui._validate_pseudonym_format_ui("invalid")

        # Assert
        assert result["is_valid"] is False
        assert result["error_message"] == "Invalid format"

    @patch("src.ui.study_participation_ui.st")
    def test_render_study_participation_status(self, mock_st, ui, user_id, mock_pseudonym_response, mock_consent_status):
        """Test rendering study participation status."""
        # Arrange
        mock_st.subheader = Mock()
        mock_st.warning = Mock()
        mock_st.metric = Mock()
        mock_st.write = Mock()
        mock_st.expander = Mock()
        
        # Mock columns with context manager support
        col1_mock = Mock()
        col1_mock.__enter__ = Mock(return_value=col1_mock)
        col1_mock.__exit__ = Mock(return_value=None)
        col2_mock = Mock()
        col2_mock.__enter__ = Mock(return_value=col2_mock)
        col2_mock.__exit__ = Mock(return_value=None)
        col3_mock = Mock()
        col3_mock.__enter__ = Mock(return_value=col3_mock)
        col3_mock.__exit__ = Mock(return_value=None)
        mock_st.columns = Mock(return_value=[col1_mock, col2_mock, col3_mock])
        
        # Mock expander context manager
        expander_mock = Mock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_st.expander.return_value = expander_mock

        ui.pseudonym_service.get_user_pseudonym = Mock(return_value=mock_pseudonym_response)
        ui.consent_service.check_consent_status = Mock(return_value=mock_consent_status)

        # Act
        ui.render_study_participation_status(user_id)

        # Assert
        mock_st.subheader.assert_called_once_with("📊 Your Study Participation Status")
        ui.pseudonym_service.get_user_pseudonym.assert_called_once_with(user_id)
        ui.consent_service.check_consent_status.assert_called_once_with(mock_pseudonym_response.pseudonym_id)

    @patch("src.ui.study_participation_ui.st")
    def test_render_study_participation_status_no_pseudonym(self, mock_st, ui, user_id):
        """Test rendering study participation status with no pseudonym."""
        # Arrange
        mock_st.subheader = Mock()
        mock_st.warning = Mock()

        ui.pseudonym_service.get_user_pseudonym = Mock(return_value=None)

        # Act
        ui.render_study_participation_status(user_id)

        # Assert
        mock_st.warning.assert_called_once_with("⚠️ No study pseudonym found. Please create one to participate.")

    @patch("src.ui.study_participation_ui.st")
    def test_render_existing_pseudonym_info(self, mock_st, ui, mock_pseudonym_response):
        """Test rendering existing pseudonym information."""
        # Arrange
        mock_st.expander = Mock()
        mock_st.write = Mock()
        mock_st.info = Mock()
        
        # Mock expander context manager
        expander_mock = Mock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_st.expander.return_value = expander_mock

        # Act
        ui._render_existing_pseudonym_info(mock_pseudonym_response)

        # Assert
        mock_st.expander.assert_called_once_with("Your Pseudonym Information", expanded=False)

    @patch("src.ui.study_participation_ui.st")
    def test_render_consent_summary(self, mock_st, ui, mock_consent_status):
        """Test rendering consent summary."""
        # Arrange
        mock_st.expander = Mock()
        mock_st.write = Mock()
        
        # Mock expander context manager
        expander_mock = Mock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_st.expander.return_value = expander_mock

        # Act
        ui._render_consent_summary(mock_consent_status)

        # Assert
        mock_st.expander.assert_called_once_with("Your Consent Summary", expanded=False)

    @patch("src.ui.study_participation_ui.st")
    def test_render_pseudonym_help(self, mock_st, ui):
        """Test rendering pseudonym help."""
        # Arrange
        mock_st.info = Mock()
        mock_st.expander = Mock()
        mock_st.markdown = Mock()
        
        # Mock expander context manager
        expander_mock = Mock()
        expander_mock.__enter__ = Mock(return_value=expander_mock)
        expander_mock.__exit__ = Mock(return_value=None)
        mock_st.expander.return_value = expander_mock

        # Act
        ui._render_pseudonym_help()

        # Assert
        mock_st.info.assert_called_once_with("📞 **Need Help Creating Your Pseudonym?**")
        mock_st.expander.assert_called_once_with("Detailed Examples", expanded=True)


class TestStudyParticipationUIConvenienceFunctions:
    """Test convenience functions for study participation UI."""

    @patch("src.ui.study_participation_ui.study_participation_ui")
    def test_render_pseudonym_creation_function(self, mock_ui):
        """Test render_pseudonym_creation convenience function."""
        # Arrange
        from src.ui.study_participation_ui import render_pseudonym_creation
        user_id = uuid4()
        expected_result = {"pseudonym_created": True}
        mock_ui.render_pseudonym_creation.return_value = expected_result

        # Act
        result = render_pseudonym_creation(user_id)

        # Assert
        assert result == expected_result
        mock_ui.render_pseudonym_creation.assert_called_once_with(user_id)

    @patch("src.ui.study_participation_ui.study_participation_ui")
    def test_render_consent_collection_function(self, mock_ui):
        """Test render_consent_collection convenience function."""
        # Arrange
        from src.ui.study_participation_ui import render_consent_collection
        pseudonym_id = uuid4()
        expected_result = {"consents_completed": True}
        mock_ui.render_consent_collection.return_value = expected_result

        # Act
        result = render_consent_collection(pseudonym_id)

        # Assert
        assert result == expected_result
        mock_ui.render_consent_collection.assert_called_once_with(pseudonym_id)

    @patch("src.ui.study_participation_ui.study_participation_ui")
    def test_render_study_participation_status_function(self, mock_ui):
        """Test render_study_participation_status convenience function."""
        # Arrange
        from src.ui.study_participation_ui import render_study_participation_status
        user_id = uuid4()

        # Act
        render_study_participation_status(user_id)

        # Assert
        mock_ui.render_study_participation_status.assert_called_once_with(user_id)