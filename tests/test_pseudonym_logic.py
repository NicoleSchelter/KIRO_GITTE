"""
Unit tests for pseudonym logic.
Tests pseudonym creation, validation, and hash generation functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4, UUID

from src.logic.pseudonym_logic import (
    PseudonymLogic,
    PseudonymError,
    InvalidPseudonymFormatError,
    PseudonymNotUniqueError,
)
from src.data.models import Pseudonym
from src.data.schemas import PseudonymValidation, PseudonymResponse


class TestPseudonymLogic:
    """Test cases for PseudonymLogic class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_repository = Mock()
        self.logic = PseudonymLogic(self.mock_repository)
        self.test_user_id = uuid4()

    def test_validate_pseudonym_format_valid(self):
        """Test validation of valid pseudonym format."""
        # Arrange
        valid_pseudonym = "M03s2001AJ13"
        self.mock_repository.is_pseudonym_unique.return_value = True

        # Act
        result = self.logic.validate_pseudonym_format(valid_pseudonym)

        # Assert
        assert result.is_valid is True
        assert result.is_unique is True
        assert result.error_message is None

    def test_validate_pseudonym_format_too_short(self):
        """Test validation of too short pseudonym."""
        # Arrange
        short_pseudonym = "M03s20"

        # Act
        result = self.logic.validate_pseudonym_format(short_pseudonym)

        # Assert
        assert result.is_valid is False
        assert result.is_unique is False
        assert "at least 8 characters" in result.error_message

    def test_validate_pseudonym_format_invalid_pattern(self):
        """Test validation of invalid pseudonym pattern."""
        # Arrange
        invalid_pseudonym = "m03S2001aj13"  # Wrong case pattern

        # Act
        result = self.logic.validate_pseudonym_format(invalid_pseudonym)

        # Assert
        assert result.is_valid is False
        assert result.is_unique is False
        assert "format invalid" in result.error_message

    def test_validate_pseudonym_format_not_unique(self):
        """Test validation when pseudonym is not unique."""
        # Arrange
        valid_pseudonym = "M03s2001AJ13"
        self.mock_repository.is_pseudonym_unique.return_value = False

        # Act
        result = self.logic.validate_pseudonym_format(valid_pseudonym)

        # Assert
        assert result.is_valid is True
        assert result.is_unique is False
        assert "already exists" in result.error_message

    def test_generate_pseudonym_hash(self):
        """Test pseudonym hash generation."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"

        # Act
        hash1 = self.logic.generate_pseudonym_hash(pseudonym_text, self.test_user_id)
        hash2 = self.logic.generate_pseudonym_hash(pseudonym_text, self.test_user_id)

        # Assert
        assert hash1 == hash2  # Same input should produce same hash
        assert len(hash1) == 64  # SHA-256 produces 64 character hex string
        assert isinstance(hash1, str)

    def test_generate_pseudonym_hash_different_users(self):
        """Test that different users produce different hashes for same pseudonym."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        user_id_2 = uuid4()

        # Act
        hash1 = self.logic.generate_pseudonym_hash(pseudonym_text, self.test_user_id)
        hash2 = self.logic.generate_pseudonym_hash(pseudonym_text, user_id_2)

        # Assert
        assert hash1 != hash2  # Different users should produce different hashes

    def test_create_pseudonym_success(self):
        """Test successful pseudonym creation."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_pseudonym.pseudonym_id = uuid4()
        mock_pseudonym.pseudonym_text = pseudonym_text
        mock_pseudonym.pseudonym_hash = "test_hash"
        mock_pseudonym.created_at = "2023-01-01T00:00:00"
        mock_pseudonym.is_active = True

        mock_mapping = Mock()
        mock_mapping.mapping_id = uuid4()

        self.mock_repository.get_by_user_id.return_value = None  # No existing pseudonym
        self.mock_repository.is_pseudonym_unique.return_value = True
        self.mock_repository.create_pseudonym_with_mapping.return_value = (mock_pseudonym, mock_mapping)

        # Act
        result = self.logic.create_pseudonym(self.test_user_id, pseudonym_text)

        # Assert
        assert isinstance(result, PseudonymResponse)
        assert result.pseudonym_text == pseudonym_text
        assert result.is_active is True

    def test_create_pseudonym_user_already_has_pseudonym(self):
        """Test pseudonym creation when user already has one."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        existing_pseudonym = Mock(spec=Pseudonym)
        self.mock_repository.get_by_user_id.return_value = existing_pseudonym

        # Act & Assert
        with pytest.raises(PseudonymError, match="already has an active pseudonym"):
            self.logic.create_pseudonym(self.test_user_id, pseudonym_text)

    def test_create_pseudonym_invalid_format(self):
        """Test pseudonym creation with invalid format."""
        # Arrange
        invalid_pseudonym = "invalid"
        self.mock_repository.get_by_user_id.return_value = None

        # Act & Assert
        with pytest.raises(InvalidPseudonymFormatError):
            self.logic.create_pseudonym(self.test_user_id, invalid_pseudonym)

    def test_create_pseudonym_not_unique(self):
        """Test pseudonym creation when not unique."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        self.mock_repository.get_by_user_id.return_value = None
        self.mock_repository.is_pseudonym_unique.return_value = False

        # Act & Assert
        with pytest.raises(PseudonymNotUniqueError):
            self.logic.create_pseudonym(self.test_user_id, pseudonym_text)

    def test_create_pseudonym_database_failure(self):
        """Test pseudonym creation when database creation fails."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        self.mock_repository.get_by_user_id.return_value = None
        self.mock_repository.is_pseudonym_unique.return_value = True
        self.mock_repository.create_pseudonym_with_mapping.return_value = (None, None)  # Database failure

        # Act & Assert
        with pytest.raises(PseudonymError, match="Failed to create pseudonym in database"):
            self.logic.create_pseudonym(self.test_user_id, pseudonym_text)

    def test_get_user_pseudonym_exists(self):
        """Test getting existing user pseudonym."""
        # Arrange
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_pseudonym.pseudonym_id = uuid4()
        mock_pseudonym.pseudonym_text = "M03s2001AJ13"
        mock_pseudonym.pseudonym_hash = "test_hash"
        mock_pseudonym.created_at = "2023-01-01T00:00:00"
        mock_pseudonym.is_active = True

        self.mock_repository.get_by_user_id.return_value = mock_pseudonym

        # Act
        result = self.logic.get_user_pseudonym(self.test_user_id)

        # Assert
        assert result is not None
        assert isinstance(result, PseudonymResponse)
        assert result.pseudonym_text == "M03s2001AJ13"

    def test_get_user_pseudonym_not_exists(self):
        """Test getting non-existing user pseudonym."""
        # Arrange
        self.mock_repository.get_by_user_id.return_value = None

        # Act
        result = self.logic.get_user_pseudonym(self.test_user_id)

        # Assert
        assert result is None

    def test_deactivate_pseudonym_success(self):
        """Test successful pseudonym deactivation."""
        # Arrange
        self.mock_repository.deactivate_user_pseudonym.return_value = True

        # Act
        result = self.logic.deactivate_pseudonym(self.test_user_id)

        # Assert
        assert result is True
        self.mock_repository.deactivate_user_pseudonym.assert_called_once_with(self.test_user_id)

    def test_deactivate_pseudonym_not_found(self):
        """Test pseudonym deactivation when pseudonym not found."""
        # Arrange
        self.mock_repository.deactivate_user_pseudonym.return_value = False

        # Act
        result = self.logic.deactivate_pseudonym(self.test_user_id)

        # Assert
        assert result is False

    def test_verify_pseudonym_ownership_valid(self):
        """Test valid pseudonym ownership verification."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_pseudonym.pseudonym_text = pseudonym_text
        self.mock_repository.get_by_user_id.return_value = mock_pseudonym

        # Act
        result = self.logic.verify_pseudonym_ownership(self.test_user_id, pseudonym_text)

        # Assert
        assert result is True

    def test_verify_pseudonym_ownership_invalid(self):
        """Test invalid pseudonym ownership verification."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        wrong_pseudonym = "A01b1999XY99"
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_pseudonym.pseudonym_text = wrong_pseudonym
        self.mock_repository.get_by_user_id.return_value = mock_pseudonym

        # Act
        result = self.logic.verify_pseudonym_ownership(self.test_user_id, pseudonym_text)

        # Assert
        assert result is False

    def test_verify_pseudonym_ownership_no_pseudonym(self):
        """Test pseudonym ownership verification when user has no pseudonym."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        self.mock_repository.get_by_user_id.return_value = None

        # Act
        result = self.logic.verify_pseudonym_ownership(self.test_user_id, pseudonym_text)

        # Assert
        assert result is False