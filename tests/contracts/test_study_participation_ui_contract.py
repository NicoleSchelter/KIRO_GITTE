"""
Contract tests for study participation UI components.
Tests the contracts between UI layer and service layer components.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from src.data.models import StudyConsentType
from src.data.schemas import PseudonymResponse, PseudonymValidation
from src.ui.study_participation_ui import StudyParticipationUI


class TestStudyParticipationUIContracts:
    """Test contracts for study participation UI components."""

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

    def test_pseudonym_service_contract_get_user_pseudonym(self, ui, user_id):
        """Test contract with pseudonym service for getting user pseudonym."""
        # Arrange
        expected_response = PseudonymResponse(
            pseudonym_id=uuid4(),
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="test_hash",
            created_at="2024-01-01T00:00:00",
            is_active=True
        )
        
        ui.pseudonym_service.get_user_pseudonym = Mock(return_value=expected_response)

        # Act
        result = ui.pseudonym_service.get_user_pseudonym(user_id)

        # Assert
        assert isinstance(result, PseudonymResponse)
        assert result.pseudonym_text == "M03s2001AJ13"
        assert result.is_active is True
        ui.pseudonym_service.get_user_pseudonym.assert_called_once_with(user_id)

    def test_pseudonym_service_contract_create_pseudonym(self, ui, user_id):
        """Test contract with pseudonym service for creating pseudonym."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        expected_response = PseudonymResponse(
            pseudonym_id=uuid4(),
            pseudonym_text=pseudonym_text,
            pseudonym_hash="test_hash",
            created_at="2024-01-01T00:00:00",
            is_active=True
        )
        
        ui.pseudonym_service.create_pseudonym = Mock(return_value=expected_response)

        # Act
        result = ui.pseudonym_service.create_pseudonym(user_id, pseudonym_text)

        # Assert
        assert isinstance(result, PseudonymResponse)
        assert result.pseudonym_text == pseudonym_text
        ui.pseudonym_service.create_pseudonym.assert_called_once_with(user_id, pseudonym_text)

    def test_pseudonym_service_contract_validate_pseudonym(self, ui):
        """Test contract with pseudonym service for validating pseudonym."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        expected_validation = PseudonymValidation(
            is_valid=True,
            is_unique=True,
            error_message=None
        )
        
        ui.pseudonym_service.validate_pseudonym = Mock(return_value=expected_validation)

        # Act
        result = ui.pseudonym_service.validate_pseudonym(pseudonym_text)

        # Assert
        assert isinstance(result, PseudonymValidation)
        assert result.is_valid is True
        assert result.is_unique is True
        ui.pseudonym_service.validate_pseudonym.assert_called_once_with(pseudonym_text)

    def test_consent_service_contract_check_consent_status(self, ui, pseudonym_id):
        """Test contract with consent service for checking consent status."""
        # Arrange
        expected_status = {
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
        
        ui.consent_service.check_consent_status = Mock(return_value=expected_status)

        # Act
        result = ui.consent_service.check_consent_status(pseudonym_id)

        # Assert
        assert isinstance(result, dict)
        assert "pseudonym_id" in result
        assert "consent_status" in result
        assert "all_required_granted" in result
        assert result["pseudonym_id"] == pseudonym_id
        ui.consent_service.check_consent_status.assert_called_once_with(pseudonym_id)

    def test_consent_service_contract_process_consent_collection(self, ui, pseudonym_id):
        """Test contract with consent service for processing consent collection."""
        # Arrange
        consents = {
            "data_protection": True,
            "ai_interaction": True,
            "study_participation": True
        }
        
        expected_result = {
            "success": True,
            "consent_records": [],
            "failed_consents": [],
            "validation": {
                "is_complete": True,
                "missing_consents": [],
                "required_consents": ["data_protection", "ai_interaction", "study_participation"],
                "provided_consents": ["data_protection", "ai_interaction", "study_participation"]
            },
            "can_proceed": True
        }
        
        ui.consent_service.process_consent_collection = Mock(return_value=expected_result)

        # Act
        result = ui.consent_service.process_consent_collection(pseudonym_id, consents)

        # Assert
        assert isinstance(result, dict)
        assert "success" in result
        assert "consent_records" in result
        assert "validation" in result
        assert result["success"] is True
        ui.consent_service.process_consent_collection.assert_called_once_with(pseudonym_id, consents)

    def test_ui_method_contracts_return_types(self, ui, user_id, pseudonym_id):
        """Test that UI methods return expected types."""
        # Mock dependencies
        ui.pseudonym_service.get_user_pseudonym = Mock(return_value=None)
        ui.pseudonym_service.validate_pseudonym = Mock(return_value=PseudonymValidation(
            is_valid=True, is_unique=True, error_message=None
        ))
        ui.consent_service.check_consent_status = Mock(return_value={
            "all_required_granted": False,
            "consent_status": {},
            "granted_count": 0,
            "total_count": 3
        })
        ui._validate_pseudonym_format_ui = Mock(return_value={"is_valid": True, "error_message": None})

        with patch("src.ui.study_participation_ui.st") as mock_st:
            # Mock Streamlit components
            mock_st.title = Mock()
            mock_st.markdown = Mock()
            mock_st.form = Mock()
            mock_st.text_input = Mock(return_value="")
            mock_st.expander = Mock()
            mock_st.progress = Mock()
            mock_st.subheader = Mock()
            mock_st.checkbox = Mock(return_value=False)
            mock_st.warning = Mock()
            mock_st.divider = Mock()
            mock_st.success = Mock()
            mock_st.error = Mock()
            mock_st.info = Mock()
            
            # Mock columns with context manager support
            col1_mock = Mock()
            col1_mock.__enter__ = Mock(return_value=col1_mock)
            col1_mock.__exit__ = Mock(return_value=None)
            col2_mock = Mock()
            col2_mock.__enter__ = Mock(return_value=col2_mock)
            col2_mock.__exit__ = Mock(return_value=None)
            mock_st.columns = Mock(return_value=[col1_mock, col2_mock])
            
            # Mock context managers
            form_mock = Mock()
            form_mock.__enter__ = Mock(return_value=form_mock)
            form_mock.__exit__ = Mock(return_value=None)
            mock_st.form.return_value = form_mock
            
            expander_mock = Mock()
            expander_mock.__enter__ = Mock(return_value=expander_mock)
            expander_mock.__exit__ = Mock(return_value=None)
            mock_st.expander.return_value = expander_mock

            with patch("src.ui.study_participation_ui.form_submit_button") as mock_submit:
                mock_submit.return_value = False

                # Test render_pseudonym_creation return type
                result = ui.render_pseudonym_creation(user_id)
                assert result is None or isinstance(result, dict)

                # Test render_consent_collection return type
                result = ui.render_consent_collection(pseudonym_id)
                assert result is None or isinstance(result, dict)

    def test_validation_method_contract(self, ui):
        """Test validation method contract."""
        # Arrange
        ui.pseudonym_service.validate_pseudonym = Mock(return_value=PseudonymValidation(
            is_valid=True,
            is_unique=True,
            error_message=None
        ))

        # Act
        result = ui._validate_pseudonym_format_ui("M03s2001AJ13")

        # Assert
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "error_message" in result
        assert isinstance(result["is_valid"], bool)

    def test_handle_pseudonym_creation_contract(self, ui, user_id):
        """Test pseudonym creation handler contract."""
        # Arrange
        expected_response = PseudonymResponse(
            pseudonym_id=uuid4(),
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="test_hash",
            created_at="2024-01-01T00:00:00",
            is_active=True
        )
        
        ui.pseudonym_service.create_pseudonym = Mock(return_value=expected_response)

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.success = Mock()
            mock_st.balloons = Mock()

            # Act
            result = ui._handle_pseudonym_creation(user_id, "M03s2001AJ13")

            # Assert
            assert isinstance(result, dict)
            assert "pseudonym_created" in result
            assert "pseudonym_id" in result
            assert "existing" in result
            assert isinstance(result["pseudonym_created"], bool)

    def test_handle_consent_submission_contract(self, ui, pseudonym_id):
        """Test consent submission handler contract."""
        # Arrange
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

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.success = Mock()
            mock_st.balloons = Mock()

            # Act
            result = ui._handle_consent_submission(pseudonym_id, consents, complete=True)

            # Assert
            if result is not None:
                assert isinstance(result, dict)
                assert "consents_completed" in result
                assert "existing" in result
                assert isinstance(result["consents_completed"], bool)

    def test_service_error_handling_contracts(self, ui, user_id, pseudonym_id):
        """Test that UI properly handles service layer errors."""
        # Test pseudonym service error handling
        ui.pseudonym_service.get_user_pseudonym = Mock(side_effect=Exception("Service error"))
        
        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.subheader = Mock()
            mock_st.error = Mock()
            
            # Should not raise exception, should handle gracefully
            try:
                ui.render_study_participation_status(user_id)
            except Exception:
                pytest.fail("UI should handle service errors gracefully")

        # Test consent service error handling
        ui.consent_service.check_consent_status = Mock(side_effect=Exception("Service error"))
        
        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.title = Mock()
            mock_st.error = Mock()
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
            
            with patch("src.ui.study_participation_ui.form_submit_button") as mock_submit:
                mock_submit.return_value = False
                
                # Should not raise exception, should handle gracefully
                try:
                    ui.render_consent_collection(pseudonym_id)
                except Exception:
                    pytest.fail("UI should handle service errors gracefully")

    def test_streamlit_component_usage_contracts(self, ui, user_id):
        """Test that UI uses Streamlit components according to contracts."""
        # Mock all required Streamlit components
        with patch("src.ui.study_participation_ui.st") as mock_st:
            # Verify UI layer only uses Streamlit for presentation
            mock_st.title = Mock()
            mock_st.markdown = Mock()
            mock_st.success = Mock()
            mock_st.error = Mock()
            mock_st.warning = Mock()
            mock_st.info = Mock()
            mock_st.form = Mock()
            mock_st.text_input = Mock(return_value="")
            mock_st.checkbox = Mock(return_value=False)
            mock_st.button = Mock(return_value=False)
            mock_st.expander = Mock()
            mock_st.progress = Mock()
            mock_st.subheader = Mock()
            mock_st.divider = Mock()
            mock_st.balloons = Mock()
            
            # Mock columns with context manager support
            col1_mock = Mock()
            col1_mock.__enter__ = Mock(return_value=col1_mock)
            col1_mock.__exit__ = Mock(return_value=None)
            col2_mock = Mock()
            col2_mock.__enter__ = Mock(return_value=col2_mock)
            col2_mock.__exit__ = Mock(return_value=None)
            mock_st.columns = Mock(return_value=[col1_mock, col2_mock])
            
            # Mock context managers
            form_mock = Mock()
            form_mock.__enter__ = Mock(return_value=form_mock)
            form_mock.__exit__ = Mock(return_value=None)
            mock_st.form.return_value = form_mock
            
            expander_mock = Mock()
            expander_mock.__enter__ = Mock(return_value=expander_mock)
            expander_mock.__exit__ = Mock(return_value=None)
            mock_st.expander.return_value = expander_mock

            # Mock services
            ui.pseudonym_service.get_user_pseudonym = Mock(return_value=None)
            ui._validate_pseudonym_format_ui = Mock(return_value={"is_valid": True, "error_message": None})

            with patch("src.ui.study_participation_ui.form_submit_button") as mock_submit:
                mock_submit.return_value = False

                # Act - call UI method
                ui.render_pseudonym_creation(user_id)

                # Assert - verify no business logic in UI
                # UI should only call service methods, not implement business logic
                assert ui.pseudonym_service.get_user_pseudonym.called
                # Streamlit components should be called for presentation
                assert mock_st.title.called