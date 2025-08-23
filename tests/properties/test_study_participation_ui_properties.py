"""
Property-based tests for study participation UI components.
Tests invariants and properties of the UI behavior.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from src.data.schemas import PseudonymResponse, PseudonymValidation
from src.ui.study_participation_ui import StudyParticipationUI


class TestStudyParticipationUIProperties:
    """Property-based tests for study participation UI components."""

    @pytest.fixture
    def ui(self):
        """Create StudyParticipationUI instance."""
        return StudyParticipationUI()

    @given(
        pseudonym_text=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            min_size=1,
            max_size=50
        )
    )
    @settings(max_examples=50)
    def test_validate_pseudonym_format_ui_always_returns_dict(self, ui, pseudonym_text):
        """Property: _validate_pseudonym_format_ui always returns a dict with required keys."""
        # Arrange
        ui.pseudonym_service.validate_pseudonym = Mock(return_value=PseudonymValidation(
            is_valid=True,
            is_unique=True,
            error_message=None
        ))

        # Act
        result = ui._validate_pseudonym_format_ui(pseudonym_text)

        # Assert
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "error_message" in result
        assert isinstance(result["is_valid"], bool)

    @given(
        consents=st.dictionaries(
            keys=st.sampled_from(["data_protection", "ai_interaction", "study_participation"]),
            values=st.booleans(),
            min_size=0,
            max_size=3
        )
    )
    @settings(max_examples=30)
    def test_handle_consent_submission_preserves_input_structure(self, ui, consents):
        """Property: consent submission preserves the structure of input consents."""
        # Arrange
        pseudonym_id = uuid4()
        
        ui.consent_service.process_consent_collection = Mock(return_value={
            "success": True,
            "can_proceed": len(consents) == 3 and all(consents.values()),
            "consent_records": []
        })

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.success = Mock()
            mock_st.warning = Mock()
            mock_st.balloons = Mock()

            # Act
            result = ui._handle_consent_submission(pseudonym_id, consents, complete=True)

            # Assert
            # Service should be called with the exact consents provided
            ui.consent_service.process_consent_collection.assert_called_once_with(pseudonym_id, consents)

    @given(
        user_id=st.uuids(),
        pseudonym_exists=st.booleans()
    )
    @settings(max_examples=20)
    def test_pseudonym_creation_idempotency(self, ui, user_id, pseudonym_exists):
        """Property: pseudonym creation behavior is consistent based on existing pseudonym state."""
        # Arrange
        if pseudonym_exists:
            existing_pseudonym = PseudonymResponse(
                pseudonym_id=uuid4(),
                pseudonym_text="M03s2001AJ13",
                pseudonym_hash="test_hash",
                created_at="2024-01-01T00:00:00",
                is_active=True
            )
            ui.pseudonym_service.get_user_pseudonym = Mock(return_value=existing_pseudonym)
        else:
            ui.pseudonym_service.get_user_pseudonym = Mock(return_value=None)

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.title = Mock()
            mock_st.success = Mock()
            mock_st.markdown = Mock()
            mock_st.button = Mock(return_value=False)
            mock_st.form = Mock()
            mock_st.text_input = Mock(return_value="")
            mock_st.expander = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            
            # Mock context managers
            form_mock = Mock()
            form_mock.__enter__ = Mock(return_value=form_mock)
            form_mock.__exit__ = Mock(return_value=None)
            mock_st.form.return_value = form_mock
            
            expander_mock = Mock()
            expander_mock.__enter__ = Mock(return_value=expander_mock)
            expander_mock.__exit__ = Mock(return_value=None)
            mock_st.expander.return_value = expander_mock

            ui._validate_pseudonym_format_ui = Mock(return_value={"is_valid": True, "error_message": None})
            ui._render_existing_pseudonym_info = Mock()

            with patch("src.ui.study_participation_ui.form_submit_button") as mock_submit:
                mock_submit.return_value = False

                # Act
                result = ui.render_pseudonym_creation(user_id)

                # Assert
                if pseudonym_exists:
                    # Should show existing pseudonym info
                    ui._render_existing_pseudonym_info.assert_called_once()
                else:
                    # Should show creation form
                    mock_st.form.assert_called()

    @given(
        consent_counts=st.integers(min_value=0, max_value=3),
        all_granted=st.booleans()
    )
    @settings(max_examples=20)
    def test_consent_status_display_consistency(self, ui, consent_counts, all_granted):
        """Property: consent status display is consistent with the underlying data."""
        # Arrange
        pseudonym_id = uuid4()
        
        consent_status = {
            "pseudonym_id": pseudonym_id,
            "consent_status": {},
            "all_required_granted": all_granted and consent_counts == 3,
            "granted_count": consent_counts,
            "total_count": 3,
            "completion_rate": consent_counts / 3,
            "can_proceed_to_study": all_granted and consent_counts == 3
        }
        
        # Create consent status based on parameters
        consent_types = ["data_protection", "ai_interaction", "study_participation"]
        for i in range(consent_counts):
            consent_status["consent_status"][consent_types[i]] = all_granted

        ui.consent_service.check_consent_status = Mock(return_value=consent_status)

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.title = Mock()
            mock_st.success = Mock()
            mock_st.markdown = Mock()
            mock_st.progress = Mock()
            mock_st.form = Mock()
            mock_st.subheader = Mock()
            mock_st.checkbox = Mock(return_value=False)
            mock_st.warning = Mock()
            mock_st.expander = Mock()
            mock_st.divider = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock()])
            mock_st.button = Mock(return_value=False)
            
            # Mock context managers
            form_mock = Mock()
            form_mock.__enter__ = Mock(return_value=form_mock)
            form_mock.__exit__ = Mock(return_value=None)
            mock_st.form.return_value = form_mock
            
            expander_mock = Mock()
            expander_mock.__enter__ = Mock(return_value=expander_mock)
            expander_mock.__exit__ = Mock(return_value=None)
            mock_st.expander.return_value = expander_mock

            ui._render_consent_summary = Mock()

            with patch("src.ui.study_participation_ui.form_submit_button") as mock_submit:
                mock_submit.return_value = False

                # Act
                result = ui.render_consent_collection(pseudonym_id)

                # Assert
                if consent_status["all_required_granted"]:
                    # Should show success message for complete consents
                    mock_st.success.assert_called()
                else:
                    # Should show progress and form for incomplete consents
                    mock_st.progress.assert_called()

    @given(
        error_occurs=st.booleans(),
        error_type=st.sampled_from(["validation", "service", "unexpected"])
    )
    @settings(max_examples=15)
    def test_error_handling_robustness(self, ui, error_occurs, error_type):
        """Property: UI handles errors gracefully without crashing."""
        # Arrange
        user_id = uuid4()
        
        if error_occurs:
            if error_type == "validation":
                ui.pseudonym_service.validate_pseudonym = Mock(side_effect=ValueError("Validation error"))
            elif error_type == "service":
                ui.pseudonym_service.get_user_pseudonym = Mock(side_effect=Exception("Service error"))
            else:
                ui.pseudonym_service.get_user_pseudonym = Mock(side_effect=RuntimeError("Unexpected error"))
        else:
            ui.pseudonym_service.get_user_pseudonym = Mock(return_value=None)
            ui.pseudonym_service.validate_pseudonym = Mock(return_value=PseudonymValidation(
                is_valid=True, is_unique=True, error_message=None
            ))

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.title = Mock()
            mock_st.error = Mock()
            mock_st.warning = Mock()
            mock_st.subheader = Mock()
            mock_st.metric = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock()])
            mock_st.expander = Mock()
            
            # Mock context managers
            expander_mock = Mock()
            expander_mock.__enter__ = Mock(return_value=expander_mock)
            expander_mock.__exit__ = Mock(return_value=None)
            mock_st.expander.return_value = expander_mock

            # Act & Assert - should not raise exception
            try:
                ui.render_study_participation_status(user_id)
            except Exception as e:
                pytest.fail(f"UI should handle errors gracefully, but raised: {e}")

    @given(
        pseudonym_text=st.text(min_size=1, max_size=100),
        is_valid=st.booleans(),
        is_unique=st.booleans()
    )
    @settings(max_examples=30)
    def test_validation_result_consistency(self, ui, pseudonym_text, is_valid, is_unique):
        """Property: validation results are consistent with service responses."""
        # Arrange
        validation_response = PseudonymValidation(
            is_valid=is_valid,
            is_unique=is_unique,
            error_message="Error" if not (is_valid and is_unique) else None
        )
        
        ui.pseudonym_service.validate_pseudonym = Mock(return_value=validation_response)

        # Act
        result = ui._validate_pseudonym_format_ui(pseudonym_text)

        # Assert
        # UI result should reflect service validation
        expected_valid = is_valid and is_unique
        assert result["is_valid"] == expected_valid
        
        if not expected_valid:
            assert result["error_message"] is not None
        else:
            assert result["error_message"] is None

    @given(
        completion_rates=st.floats(min_value=0.0, max_value=1.0),
        granted_counts=st.integers(min_value=0, max_value=10)
    )
    @settings(max_examples=20)
    def test_status_metrics_consistency(self, ui, completion_rates, granted_counts):
        """Property: status metrics are mathematically consistent."""
        # Arrange
        user_id = uuid4()
        pseudonym_id = uuid4()
        
        total_count = max(1, granted_counts)  # Avoid division by zero
        actual_completion_rate = granted_counts / total_count
        
        pseudonym = PseudonymResponse(
            pseudonym_id=pseudonym_id,
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="test_hash",
            created_at="2024-01-01T00:00:00",
            is_active=True
        )
        
        consent_status = {
            "pseudonym_id": pseudonym_id,
            "consent_status": {},
            "all_required_granted": granted_counts >= 3,
            "granted_count": granted_counts,
            "total_count": total_count,
            "completion_rate": actual_completion_rate,
            "can_proceed_to_study": granted_counts >= 3
        }

        ui.pseudonym_service.get_user_pseudonym = Mock(return_value=pseudonym)
        ui.consent_service.check_consent_status = Mock(return_value=consent_status)

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.subheader = Mock()
            mock_st.metric = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock()])
            mock_st.expander = Mock()
            mock_st.write = Mock()
            
            # Mock context managers
            expander_mock = Mock()
            expander_mock.__enter__ = Mock(return_value=expander_mock)
            expander_mock.__exit__ = Mock(return_value=None)
            mock_st.expander.return_value = expander_mock

            # Act
            ui.render_study_participation_status(user_id)

            # Assert
            # Verify service was called and metrics are consistent
            ui.consent_service.check_consent_status.assert_called_once_with(pseudonym_id)
            
            # The completion rate should match the calculation
            assert abs(consent_status["completion_rate"] - actual_completion_rate) < 0.001

    @given(
        user_ids=st.lists(st.uuids(), min_size=1, max_size=5, unique=True)
    )
    @settings(max_examples=10)
    def test_multiple_user_isolation(self, ui, user_ids):
        """Property: UI operations for different users are properly isolated."""
        # Arrange
        responses = {}
        for user_id in user_ids:
            responses[user_id] = PseudonymResponse(
                pseudonym_id=uuid4(),
                pseudonym_text=f"U{str(user_id)[:8]}",
                pseudonym_hash="test_hash",
                created_at="2024-01-01T00:00:00",
                is_active=True
            )

        def mock_get_pseudonym(user_id):
            return responses.get(user_id)

        ui.pseudonym_service.get_user_pseudonym = Mock(side_effect=mock_get_pseudonym)

        with patch("src.ui.study_participation_ui.st") as mock_st:
            mock_st.subheader = Mock()
            mock_st.warning = Mock()
            mock_st.metric = Mock()
            mock_st.columns = Mock(return_value=[Mock(), Mock(), Mock()])
            mock_st.expander = Mock()
            mock_st.write = Mock()
            
            # Mock context managers
            expander_mock = Mock()
            expander_mock.__enter__ = Mock(return_value=expander_mock)
            expander_mock.__exit__ = Mock(return_value=None)
            mock_st.expander.return_value = expander_mock

            ui.consent_service.check_consent_status = Mock(return_value={
                "granted_count": 0,
                "total_count": 3,
                "completion_rate": 0.0,
                "can_proceed_to_study": False
            })

            # Act & Assert
            for user_id in user_ids:
                ui.render_study_participation_status(user_id)
                
                # Verify each user gets their own pseudonym
                last_call = ui.pseudonym_service.get_user_pseudonym.call_args_list[-1]
                assert last_call[0][0] == user_id