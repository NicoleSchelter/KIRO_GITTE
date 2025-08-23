"""
Unit tests for pseudonym repository.
Tests data access layer operations for pseudonym management.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from src.data.repositories import PseudonymRepository
from src.data.models import Pseudonym
from src.data.schemas import PseudonymCreate


class TestPseudonymRepository:
    """Test cases for PseudonymRepository class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.repository = PseudonymRepository(self.mock_session)
        self.test_user_id = uuid4()
        self.test_pseudonym_id = uuid4()

    def test_create_success(self):
        """Test successful pseudonym creation."""
        # Arrange
        pseudonym_data = PseudonymCreate(
            pseudonym_text="M03s2001AJ13"
        )
        pseudonym_hash = "test_hash"

        # Act
        result_pseudonym, result_mapping = self.repository.create_pseudonym_with_mapping(
            pseudonym_data, pseudonym_hash, self.test_user_id, "test_user"
        )

        # Assert
        assert result_pseudonym is not None
        assert result_mapping is not None
        assert isinstance(result_pseudonym, Pseudonym)
        assert result_pseudonym.pseudonym_text == "M03s2001AJ13"
        assert result_pseudonym.pseudonym_hash == pseudonym_hash
        # Should be called twice - once for pseudonym, once for mapping
        assert self.mock_session.add.call_count == 2
        assert self.mock_session.flush.call_count == 2

    def test_create_integrity_error(self):
        """Test pseudonym creation with integrity error."""
        # Arrange
        pseudonym_data = PseudonymCreate(
            pseudonym_text="M03s2001AJ13"
        )
        pseudonym_hash = "test_hash"
        self.mock_session.add.side_effect = IntegrityError("", "", "")

        # Act
        result_pseudonym, result_mapping = self.repository.create_pseudonym_with_mapping(
            pseudonym_data, pseudonym_hash, self.test_user_id, "test_user"
        )

        # Assert
        assert result_pseudonym is None
        assert result_mapping is None
        self.mock_session.rollback.assert_called_once()

    def test_create_general_exception(self):
        """Test pseudonym creation with general exception."""
        # Arrange
        pseudonym_data = PseudonymCreate(
            pseudonym_text="M03s2001AJ13"
        )
        pseudonym_hash = "test_hash"
        self.mock_session.add.side_effect = Exception("Database error")

        # Act
        result_pseudonym, result_mapping = self.repository.create_pseudonym_with_mapping(
            pseudonym_data, pseudonym_hash, self.test_user_id, "test_user"
        )

        # Assert
        assert result_pseudonym is None
        assert result_mapping is None
        self.mock_session.rollback.assert_called_once()

    def test_get_by_user_id_exists(self):
        """Test getting pseudonym by user ID when it exists."""
        # Arrange
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_pseudonym
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.get_by_user_id(self.test_user_id)

        # Assert
        assert result == mock_pseudonym
        self.mock_session.query.assert_called_once_with(Pseudonym)

    def test_get_by_user_id_not_exists(self):
        """Test getting pseudonym by user ID when it doesn't exist."""
        # Arrange
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_query.join.return_value = mock_join
        mock_join.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.get_by_user_id(self.test_user_id)

        # Assert
        assert result is None

    def test_get_by_user_id_exception(self):
        """Test getting pseudonym by user ID with exception."""
        # Arrange
        self.mock_session.query.side_effect = Exception("Database error")

        # Act
        result = self.repository.get_by_user_id(self.test_user_id)

        # Assert
        assert result is None

    def test_get_by_pseudonym_text_exists(self):
        """Test getting pseudonym by text when it exists."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_pseudonym
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.get_by_pseudonym_text(pseudonym_text)

        # Assert
        assert result == mock_pseudonym
        self.mock_session.query.assert_called_once_with(Pseudonym)

    def test_get_by_pseudonym_text_not_exists(self):
        """Test getting pseudonym by text when it doesn't exist."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.get_by_pseudonym_text(pseudonym_text)

        # Assert
        assert result is None

    def test_get_by_pseudonym_text_exception(self):
        """Test getting pseudonym by text with exception."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        self.mock_session.query.side_effect = Exception("Database error")

        # Act
        result = self.repository.get_by_pseudonym_text(pseudonym_text)

        # Assert
        assert result is None

    def test_is_pseudonym_unique_true(self):
        """Test pseudonym uniqueness check when unique."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.is_pseudonym_unique(pseudonym_text)

        # Assert
        assert result is True

    def test_is_pseudonym_unique_false(self):
        """Test pseudonym uniqueness check when not unique."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_pseudonym
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.is_pseudonym_unique(pseudonym_text)

        # Assert
        assert result is False

    def test_is_pseudonym_unique_exception(self):
        """Test pseudonym uniqueness check with exception."""
        # Arrange
        pseudonym_text = "M03s2001AJ13"
        # Mock get_by_pseudonym_text to raise an exception directly
        with patch.object(self.repository, 'get_by_pseudonym_text', side_effect=Exception("Database error")):
            # Act
            result = self.repository.is_pseudonym_unique(pseudonym_text)

            # Assert
            assert result is False

    def test_deactivate_pseudonym_success(self):
        """Test successful pseudonym deactivation."""
        # Arrange
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_pseudonym.is_active = True
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_pseudonym
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.deactivate_pseudonym(self.test_pseudonym_id)

        # Assert
        assert result is True
        assert mock_pseudonym.is_active is False
        self.mock_session.flush.assert_called_once()

    def test_deactivate_pseudonym_not_found(self):
        """Test pseudonym deactivation when pseudonym not found."""
        # Arrange
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.deactivate_pseudonym(self.test_pseudonym_id)

        # Assert
        assert result is False

    def test_deactivate_pseudonym_exception(self):
        """Test pseudonym deactivation with exception."""
        # Arrange
        self.mock_session.query.side_effect = Exception("Database error")

        # Act
        result = self.repository.deactivate_pseudonym(self.test_pseudonym_id)

        # Assert
        assert result is False

    def test_get_by_id_exists(self):
        """Test getting pseudonym by ID when it exists."""
        # Arrange
        mock_pseudonym = Mock(spec=Pseudonym)
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_pseudonym
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.get_by_id(self.test_pseudonym_id)

        # Assert
        assert result == mock_pseudonym
        self.mock_session.query.assert_called_once_with(Pseudonym)

    def test_get_by_id_not_exists(self):
        """Test getting pseudonym by ID when it doesn't exist."""
        # Arrange
        mock_query = Mock()
        mock_filter = Mock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None
        self.mock_session.query.return_value = mock_query

        # Act
        result = self.repository.get_by_id(self.test_pseudonym_id)

        # Assert
        assert result is None

    def test_get_by_id_exception(self):
        """Test getting pseudonym by ID with exception."""
        # Arrange
        self.mock_session.query.side_effect = Exception("Database error")

        # Act
        result = self.repository.get_by_id(self.test_pseudonym_id)

        # Assert
        assert result is None