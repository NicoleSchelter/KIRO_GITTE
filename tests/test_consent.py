"""
Unit tests for consent management system.
Tests consent logic, service layer, and middleware functionality.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.data.models import ConsentRecord, ConsentType
from src.data.repositories import ConsentRepository
from src.data.schemas import ConsentRecordResponse
from src.logic.consent import ConsentError, ConsentLogic, ConsentRequiredError
from src.services.consent_middleware import (
    ConsentMiddleware,
    require_consent,
    require_operation_consent,
)
from src.services.consent_service import ConsentService


class TestConsentLogic:
    """Test consent business logic."""

    @pytest.fixture
    def mock_consent_repository(self):
        """Mock consent repository."""
        return Mock(spec=ConsentRepository)

    @pytest.fixture
    def consent_logic(self, mock_consent_repository):
        """Consent logic instance with mocked repository."""
        return ConsentLogic(mock_consent_repository)

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    def test_record_consent_success(self, consent_logic, mock_consent_repository, user_id):
        """Test successful consent recording."""
        # Arrange
        consent_type = ConsentType.DATA_PROCESSING
        consent_given = True
        metadata = {"source": "test"}

        mock_record = ConsentRecord(
            id=uuid4(),
            user_id=user_id,
            consent_type=consent_type.value,
            consent_given=consent_given,
            consent_version="1.0",
            timestamp=datetime.utcnow(),
            consent_metadata=metadata,
        )
        mock_consent_repository.create.return_value = mock_record

        # Act
        result = consent_logic.record_consent(user_id, consent_type, consent_given, metadata)

        # Assert
        assert isinstance(result, ConsentRecordResponse)
        assert result.consent_type == consent_type
        assert result.consent_given == consent_given
        assert result.user_id == user_id
        mock_consent_repository.create.assert_called_once()

    def test_record_consent_failure(self, consent_logic, mock_consent_repository, user_id):
        """Test consent recording failure."""
        # Arrange
        mock_consent_repository.create.return_value = None

        # Act & Assert
        with pytest.raises(ConsentError, match="Failed to record consent"):
            consent_logic.record_consent(user_id, ConsentType.DATA_PROCESSING, True)

    def test_withdraw_consent_success(self, consent_logic, mock_consent_repository, user_id):
        """Test successful consent withdrawal."""
        # Arrange
        consent_type = ConsentType.DATA_PROCESSING

        mock_existing_consent = ConsentRecord(
            id=uuid4(),
            user_id=user_id,
            consent_type=consent_type.value,
            consent_given=True,
            consent_version="1.0",
            timestamp=datetime.utcnow(),
        )
        mock_consent_repository.get_by_user_and_type.return_value = mock_existing_consent
        mock_consent_repository.withdraw_consent.return_value = True

        # Act
        result = consent_logic.withdraw_consent(user_id, consent_type, "test reason")

        # Assert
        assert result is True
        mock_consent_repository.withdraw_consent.assert_called_once_with(
            user_id, consent_type, "test reason"
        )

    def test_withdraw_consent_no_existing_consent(
        self, consent_logic, mock_consent_repository, user_id
    ):
        """Test withdrawing consent when none exists."""
        # Arrange
        mock_consent_repository.get_by_user_and_type.return_value = None

        # Act
        result = consent_logic.withdraw_consent(user_id, ConsentType.DATA_PROCESSING)

        # Assert
        assert result is True  # Should succeed even if no consent exists
        mock_consent_repository.withdraw_consent.assert_not_called()

    def test_check_consent_valid(self, consent_logic, mock_consent_repository, user_id):
        """Test checking valid consent."""
        # Arrange
        mock_consent_repository.check_consent.return_value = True

        # Act
        result = consent_logic.check_consent(user_id, ConsentType.DATA_PROCESSING)

        # Assert
        assert result is True
        mock_consent_repository.check_consent.assert_called_once_with(
            user_id, ConsentType.DATA_PROCESSING
        )

    def test_check_consent_invalid(self, consent_logic, mock_consent_repository, user_id):
        """Test checking invalid consent."""
        # Arrange
        mock_consent_repository.check_consent.return_value = False

        # Act
        result = consent_logic.check_consent(user_id, ConsentType.DATA_PROCESSING)

        # Assert
        assert result is False

    def test_require_consent_valid(self, consent_logic, mock_consent_repository, user_id):
        """Test requiring consent when valid."""
        # Arrange
        mock_consent_repository.check_consent.return_value = True

        # Act & Assert (should not raise)
        consent_logic.require_consent(user_id, ConsentType.DATA_PROCESSING)

    def test_require_consent_invalid(self, consent_logic, mock_consent_repository, user_id):
        """Test requiring consent when invalid."""
        # Arrange
        mock_consent_repository.check_consent.return_value = False

        # Act & Assert
        with pytest.raises(ConsentRequiredError, match="Consent required for data_processing"):
            consent_logic.require_consent(user_id, ConsentType.DATA_PROCESSING)

    def test_get_consent_status(self, consent_logic, mock_consent_repository, user_id):
        """Test getting consent status for all types."""
        # Arrange
        mock_consent_repository.check_consent.side_effect = (
            lambda uid, ct: ct == ConsentType.DATA_PROCESSING
        )

        # Act
        result = consent_logic.get_consent_status(user_id)

        # Assert
        assert isinstance(result, dict)
        assert result[ConsentType.DATA_PROCESSING.value] is True
        assert result[ConsentType.AI_INTERACTION.value] is False
        assert len(result) == len(ConsentType)

    def test_check_operation_consent_chat(self, consent_logic, mock_consent_repository, user_id):
        """Test checking consent for chat operation."""
        # Arrange
        mock_consent_repository.check_consent.side_effect = lambda uid, ct: ct in [
            ConsentType.DATA_PROCESSING,
            ConsentType.AI_INTERACTION,
        ]

        # Act
        result = consent_logic.check_operation_consent(user_id, "chat")

        # Assert
        assert result is True

    def test_check_operation_consent_missing(self, consent_logic, mock_consent_repository, user_id):
        """Test checking consent for operation with missing consent."""
        # Arrange
        mock_consent_repository.check_consent.side_effect = (
            lambda uid, ct: ct == ConsentType.DATA_PROCESSING
        )

        # Act
        result = consent_logic.check_operation_consent(user_id, "chat")

        # Assert
        assert result is False  # Missing AI_INTERACTION consent

    def test_require_operation_consent_valid(self, consent_logic, mock_consent_repository, user_id):
        """Test requiring operation consent when valid."""
        # Arrange
        mock_consent_repository.check_consent.return_value = True

        # Act & Assert (should not raise)
        consent_logic.require_operation_consent(user_id, "chat")

    def test_require_operation_consent_invalid(
        self, consent_logic, mock_consent_repository, user_id
    ):
        """Test requiring operation consent when invalid."""
        # Arrange
        mock_consent_repository.check_consent.return_value = False

        # Act & Assert
        with pytest.raises(ConsentRequiredError):
            consent_logic.require_operation_consent(user_id, "chat")

    def test_record_bulk_consent(self, consent_logic, mock_consent_repository, user_id):
        """Test recording bulk consent."""
        # Arrange
        consents = {ConsentType.DATA_PROCESSING: True, ConsentType.AI_INTERACTION: False}

        mock_records = []
        for consent_type, consent_given in consents.items():
            mock_record = ConsentRecord(
                id=uuid4(),
                user_id=user_id,
                consent_type=consent_type.value,
                consent_given=consent_given,
                consent_version="1.0",
                timestamp=datetime.utcnow(),
            )
            mock_records.append(mock_record)

        mock_consent_repository.create.side_effect = mock_records

        # Act
        result = consent_logic.record_bulk_consent(user_id, consents)

        # Assert
        assert len(result) == 2
        assert mock_consent_repository.create.call_count == 2

    @patch("src.logic.consent.config")
    def test_is_consent_gate_enabled(self, mock_config, consent_logic):
        """Test checking if consent gate is enabled."""
        # Arrange
        mock_config.get_feature_flag.return_value = True

        # Act
        result = consent_logic.is_consent_gate_enabled()

        # Assert
        assert result is True
        mock_config.get_feature_flag.assert_called_once_with("enable_consent_gate")

    def test_get_required_consents_for_operation(self, consent_logic):
        """Test getting required consents for operations."""
        # Test chat operation
        chat_consents = consent_logic.get_required_consents_for_operation("chat")
        assert ConsentType.DATA_PROCESSING in chat_consents
        assert ConsentType.AI_INTERACTION in chat_consents

        # Test image generation operation
        image_consents = consent_logic.get_required_consents_for_operation("image_generation")
        assert ConsentType.DATA_PROCESSING in image_consents
        assert ConsentType.AI_INTERACTION in image_consents

        # Test unknown operation (should default to data processing)
        unknown_consents = consent_logic.get_required_consents_for_operation("unknown")
        assert unknown_consents == [ConsentType.DATA_PROCESSING]


class TestConsentService:
    """Test consent service layer."""

    @pytest.fixture
    def consent_service(self):
        """Consent service instance."""
        return ConsentService()

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @patch("src.services.consent_service.get_session")
    def test_record_consent(self, mock_get_session, consent_service, user_id):
        """Test service layer consent recording."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        with patch("src.services.consent_service.ConsentRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo

            mock_record = ConsentRecord(
                id=uuid4(),
                user_id=user_id,
                consent_type=ConsentType.DATA_PROCESSING.value,
                consent_given=True,
                consent_version="1.0",
                timestamp=datetime.utcnow(),
            )
            mock_repo.create.return_value = mock_record

            # Act
            result = consent_service.record_consent(user_id, ConsentType.DATA_PROCESSING, True)

            # Assert
            assert isinstance(result, ConsentRecordResponse)
            assert result.consent_type == ConsentType.DATA_PROCESSING
            assert result.consent_given is True

    @patch("src.services.consent_service.get_session")
    def test_check_consent(self, mock_get_session, consent_service, user_id):
        """Test service layer consent checking."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        with patch("src.services.consent_service.ConsentRepository") as mock_repo_class:
            mock_repo = Mock()
            mock_repo_class.return_value = mock_repo
            mock_repo.check_consent.return_value = True

            # Act
            result = consent_service.check_consent(user_id, ConsentType.DATA_PROCESSING)

            # Assert
            assert result is True


class TestConsentMiddleware:
    """Test consent middleware."""

    @pytest.fixture
    def middleware(self):
        """Consent middleware instance."""
        return ConsentMiddleware()

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    def test_extract_user_id_from_kwargs(self, middleware, user_id):
        """Test extracting user ID from keyword arguments."""
        # Act
        result = middleware._extract_user_id((), {"user_id": user_id})

        # Assert
        assert result == user_id

    def test_extract_user_id_from_args(self, middleware, user_id):
        """Test extracting user ID from positional arguments."""
        # Act
        result = middleware._extract_user_id((user_id,), {})

        # Assert
        assert result == user_id

    def test_extract_user_id_from_user_object(self, middleware, user_id):
        """Test extracting user ID from user object."""
        # Arrange
        mock_user = Mock()
        mock_user.user_id = user_id

        # Act
        result = middleware._extract_user_id((mock_user,), {})

        # Assert
        assert result == user_id

    def test_extract_user_id_none(self, middleware):
        """Test extracting user ID when none found."""
        # Act
        result = middleware._extract_user_id(("not_uuid",), {"other_param": "value"})

        # Assert
        assert result is None

    def test_check_consent_gate_enabled(self, middleware, user_id):
        """Test consent gate checking when enabled."""
        # Arrange
        with patch.object(middleware, "consent_service") as mock_service:
            mock_service.is_consent_gate_enabled.return_value = True
            mock_service.check_operation_consent.return_value = True

            # Act
            result = middleware.check_consent_gate(user_id, "chat")

            # Assert
            assert result is True
            mock_service.check_operation_consent.assert_called_once_with(user_id, "chat")

    def test_check_consent_gate_disabled(self, middleware, user_id):
        """Test consent gate checking when disabled."""
        # Arrange
        with patch.object(middleware, "consent_service") as mock_service:
            mock_service.is_consent_gate_enabled.return_value = False

            # Act
            result = middleware.check_consent_gate(user_id, "chat")

            # Assert
            assert result is True
            mock_service.check_operation_consent.assert_not_called()

    def test_get_missing_consents(self, middleware, user_id):
        """Test getting missing consents for operation."""
        # Arrange
        with patch.object(middleware, "consent_service") as mock_service:
            mock_service.get_required_consents_for_operation.return_value = [
                ConsentType.DATA_PROCESSING,
                ConsentType.AI_INTERACTION,
            ]
            mock_service.check_consent.side_effect = (
                lambda uid, ct: ct == ConsentType.DATA_PROCESSING
            )

            # Act
            result = middleware.get_missing_consents(user_id, "chat")

            # Assert
            assert result == [ConsentType.AI_INTERACTION]


class TestConsentDecorators:
    """Test consent decorators."""

    @pytest.fixture
    def user_id(self):
        """Test user ID."""
        return uuid4()

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.ConsentRepository")
    def test_require_consent_decorator_success(self, mock_repo_class, mock_get_session, user_id):
        """Test consent decorator when consent is valid."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.check_consent.return_value = True

        @require_consent(ConsentType.DATA_PROCESSING)
        def test_function(user_id):
            return "success"

        # Act
        result = test_function(user_id)

        # Assert
        assert result == "success"

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.ConsentRepository")
    def test_require_consent_decorator_failure(self, mock_repo_class, mock_get_session, user_id):
        """Test consent decorator when consent is missing."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.check_consent.return_value = False

        @require_consent(ConsentType.DATA_PROCESSING)
        def test_function(user_id):
            return "success"

        # Act & Assert
        with pytest.raises(ConsentRequiredError):
            test_function(user_id)

    @patch("src.services.consent_service.get_session")
    @patch("src.services.consent_service.ConsentRepository")
    def test_require_operation_consent_decorator(self, mock_repo_class, mock_get_session, user_id):
        """Test operation consent decorator."""
        # Arrange
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        mock_repo.check_consent.return_value = True  # All consents valid

        @require_operation_consent("chat")
        def test_function(user_id):
            return "success"

        # Act
        result = test_function(user_id)

        # Assert
        assert result == "success"


if __name__ == "__main__":
    pytest.main([__file__])
