"""
Unit tests for pseudonym service.
Tests service layer operations for pseudonym management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from src.services.pseudonym_service import PseudonymService
from src.logic.pseudonym_logic import PseudonymError, InvalidPseudonymFormatError, PseudonymNotUniqueError
from src.data.schemas import PseudonymResponse, PseudonymValidation


class TestPseudonymService:
    """Test cases for PseudonymService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = PseudonymService()
        self.test_user_id = uuid4()

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_create_pseudonym_success(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test successful pseudonym creation."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        
        expected_response = PseudonymResponse(
            pseudonym_id=uuid4(),
            user_id=self.test_user_id,
            pseudonym_text=pseudonym_text,
            pseudonym_hash="test_hash",
            created_at="2023-01-01T00:00:00",
            is_active=True
        )
        mock_logic.create_pseudonym.return_value = expected_response

        # Act
        result = self.service.create_pseudonym(self.test_user_id, pseudonym_text)

        # Assert
        assert result == expected_response
        mock_logic.create_pseudonym.assert_called_once_with(self.test_user_id, pseudonym_text, "system")
        mock_session.commit.assert_called_once()

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_create_pseudonym_invalid_format(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test pseudonym creation with invalid format."""
        # Arrange
        pseudonym_text = "invalid"
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.create_pseudonym.side_effect = InvalidPseudonymFormatError("Invalid format")

        # Act & Assert
        with pytest.raises(InvalidPseudonymFormatError):
            self.service.create_pseudonym(self.test_user_id, pseudonym_text)
        
        mock_session.rollback.assert_called_once()

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_create_pseudonym_not_unique(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test pseudonym creation when not unique."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.create_pseudonym.side_effect = PseudonymNotUniqueError("Not unique")

        # Act & Assert
        with pytest.raises(PseudonymNotUniqueError):
            self.service.create_pseudonym(self.test_user_id, pseudonym_text)
        
        mock_session.rollback.assert_called_once()

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_validate_pseudonym_valid(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test pseudonym validation for valid pseudonym."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        
        expected_validation = PseudonymValidation(
            is_valid=True,
            is_unique=True,
            error_message=None
        )
        mock_logic.validate_pseudonym_format.return_value = expected_validation

        # Act
        result = self.service.validate_pseudonym(pseudonym_text)

        # Assert
        assert result == expected_validation
        mock_logic.validate_pseudonym_format.assert_called_once_with(pseudonym_text)

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_validate_pseudonym_invalid(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test pseudonym validation for invalid pseudonym."""
        # Arrange
        pseudonym_text = "invalid"
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        
        expected_validation = PseudonymValidation(
            is_valid=False,
            is_unique=False,
            error_message="Invalid format"
        )
        mock_logic.validate_pseudonym_format.return_value = expected_validation

        # Act
        result = self.service.validate_pseudonym(pseudonym_text)

        # Assert
        assert result == expected_validation
        mock_logic.validate_pseudonym_format.assert_called_once_with(pseudonym_text)

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_get_user_pseudonym_exists(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test getting existing user pseudonym."""
        # Arrange
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        
        expected_response = PseudonymResponse(
            pseudonym_id=uuid4(),
            user_id=self.test_user_id,
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="test_hash",
            created_at="2023-01-01T00:00:00",
            is_active=True
        )
        mock_logic.get_user_pseudonym.return_value = expected_response

        # Act
        result = self.service.get_user_pseudonym(self.test_user_id)

        # Assert
        assert result == expected_response
        mock_logic.get_user_pseudonym.assert_called_once_with(self.test_user_id)

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_get_user_pseudonym_not_exists(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test getting non-existing user pseudonym."""
        # Arrange
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.get_user_pseudonym.return_value = None

        # Act
        result = self.service.get_user_pseudonym(self.test_user_id)

        # Assert
        assert result is None
        mock_logic.get_user_pseudonym.assert_called_once_with(self.test_user_id)

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_deactivate_user_pseudonym_success(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test successful pseudonym deactivation."""
        # Arrange
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.deactivate_pseudonym.return_value = True

        # Act
        result = self.service.deactivate_user_pseudonym(self.test_user_id)

        # Assert
        assert result is True
        mock_logic.deactivate_pseudonym.assert_called_once_with(self.test_user_id)
        mock_session.commit.assert_called_once()

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_deactivate_user_pseudonym_failure(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test pseudonym deactivation failure."""
        # Arrange
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.deactivate_pseudonym.return_value = False

        # Act
        result = self.service.deactivate_user_pseudonym(self.test_user_id)

        # Assert
        assert result is False
        mock_logic.deactivate_pseudonym.assert_called_once_with(self.test_user_id)
        mock_session.commit.assert_not_called()

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_verify_pseudonym_ownership_valid(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test valid pseudonym ownership verification."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.verify_pseudonym_ownership.return_value = True

        # Act
        result = self.service.verify_pseudonym_ownership(self.test_user_id, pseudonym_text)

        # Assert
        assert result is True
        mock_logic.verify_pseudonym_ownership.assert_called_once_with(self.test_user_id, pseudonym_text)

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_verify_pseudonym_ownership_invalid(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test invalid pseudonym ownership verification."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.verify_pseudonym_ownership.return_value = False

        # Act
        result = self.service.verify_pseudonym_ownership(self.test_user_id, pseudonym_text)

        # Assert
        assert result is False
        mock_logic.verify_pseudonym_ownership.assert_called_once_with(self.test_user_id, pseudonym_text)

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_has_user_pseudonym_true(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test checking if user has pseudonym when they do."""
        # Arrange
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        
        expected_response = PseudonymResponse(
            pseudonym_id=uuid4(),
            user_id=self.test_user_id,
            pseudonym_text="M03s2001AJ13",
            pseudonym_hash="test_hash",
            created_at="2023-01-01T00:00:00",
            is_active=True
        )
        mock_logic.get_user_pseudonym.return_value = expected_response

        # Act
        result = self.service.has_user_pseudonym(self.test_user_id)

        # Assert
        assert result is True

    @patch('src.services.pseudonym_service.get_session')
    @patch('src.services.pseudonym_service.PseudonymRepository')
    @patch('src.services.pseudonym_service.PseudonymLogic')
    def test_has_user_pseudonym_false(self, mock_logic_class, mock_repo_class, mock_get_session):
        """Test checking if user has pseudonym when they don't."""
        # Arrange
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo
        
        mock_logic = Mock()
        mock_logic_class.return_value = mock_logic
        mock_logic.get_user_pseudonym.return_value = None

        # Act
        result = self.service.has_user_pseudonym(self.test_user_id)

        # Assert
        assert result is False