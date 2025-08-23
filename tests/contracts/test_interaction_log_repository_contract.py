"""
Contract tests for InteractionLogRepository.
Tests the repository interface contract to ensure consistent behavior.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

from src.data.repositories import InteractionLogRepository
from src.data.schemas import InteractionLogCreate


class TestInteractionLogRepositoryContract:
    """Contract tests for InteractionLogRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def repository(self, mock_session):
        """Create InteractionLogRepository instance."""
        return InteractionLogRepository(mock_session)

    def test_repository_initialization_contract(self, mock_session):
        """Test that repository initializes with required interface."""
        repository = InteractionLogRepository(mock_session)
        
        # Verify required methods exist
        assert hasattr(repository, 'create')
        assert hasattr(repository, 'get_by_id')
        assert hasattr(repository, 'get_by_session')
        assert hasattr(repository, 'get_by_pseudonym')
        assert hasattr(repository, 'get_filtered')
        assert hasattr(repository, 'update')
        assert hasattr(repository, 'delete_by_pseudonym')
        assert hasattr(repository, 'delete_by_session')
        assert hasattr(repository, 'get_interaction_count_by_type')
        
        # Verify session is stored
        assert repository.session == mock_session

    def test_create_method_contract(self, repository):
        """Test that create method follows the expected contract."""
        log_data = InteractionLogCreate(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_type="chat",
            model_used="gpt-4",
            parameters={"temperature": 0.7},
            latency_ms=1500,
        )

        # Mock successful creation
        with patch('src.data.repositories.InteractionLog') as mock_log_class:
            mock_log = Mock()
            mock_log.log_id = uuid4()
            mock_log_class.return_value = mock_log
            
            result = repository.create(log_data)
            
            # Contract: create should return InteractionLog instance or None
            assert result is not None
            assert hasattr(result, 'log_id')

    def test_get_by_id_contract(self, repository, mock_session):
        """Test that get_by_id follows the expected contract."""
        log_id = uuid4()
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_first = Mock()
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_first
        
        result = repository.get_by_id(log_id)
        
        # Contract: should query database and return result
        mock_session.query.assert_called_once()
        assert result == mock_first

    def test_get_by_session_contract(self, repository, mock_session):
        """Test that get_by_session follows the expected contract."""
        session_id = uuid4()
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_all = []
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = mock_all
        
        result = repository.get_by_session(session_id)
        
        # Contract: should return list of InteractionLog instances
        assert isinstance(result, list)
        assert result == mock_all

    def test_get_by_pseudonym_contract(self, repository, mock_session):
        """Test that get_by_pseudonym follows the expected contract."""
        pseudonym_id = uuid4()
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_all = []
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.all.return_value = mock_all
        
        result = repository.get_by_pseudonym(pseudonym_id)
        
        # Contract: should return list of InteractionLog instances
        assert isinstance(result, list)
        assert result == mock_all

    def test_get_by_pseudonym_with_limit_contract(self, repository, mock_session):
        """Test that get_by_pseudonym with limit follows the expected contract."""
        pseudonym_id = uuid4()
        limit = 10
        
        # Mock query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_order = Mock()
        mock_limit = Mock()
        mock_all = []
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.order_by.return_value = mock_order
        mock_order.limit.return_value = mock_limit
        mock_limit.all.return_value = mock_all
        
        result = repository.get_by_pseudonym(pseudonym_id, limit=limit)
        
        # Contract: should apply limit and return list
        mock_order.limit.assert_called_once_with(limit)
        assert isinstance(result, list)

    def test_update_method_contract(self, repository, mock_session):
        """Test that update method follows the expected contract."""
        log_id = uuid4()
        update_data = {"prompt": "Updated prompt", "latency_ms": 2000}
        
        # Mock existing log
        mock_log = Mock()
        mock_log.prompt = "Original prompt"
        mock_log.latency_ms = 1000
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_log
        
        result = repository.update(log_id, update_data)
        
        # Contract: should return updated log or None
        assert result == mock_log
        # Verify attributes were updated
        assert mock_log.prompt == "Updated prompt"
        assert mock_log.latency_ms == 2000

    def test_delete_by_pseudonym_contract(self, repository, mock_session):
        """Test that delete_by_pseudonym follows the expected contract."""
        pseudonym_id = uuid4()
        
        # Mock query chain for deletion
        mock_query = Mock()
        mock_filter = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.delete.return_value = 5  # Number of deleted records
        
        result = repository.delete_by_pseudonym(pseudonym_id)
        
        # Contract: should return number of deleted records
        assert isinstance(result, int)
        assert result == 5
        mock_session.flush.assert_called_once()

    def test_delete_by_session_contract(self, repository, mock_session):
        """Test that delete_by_session follows the expected contract."""
        session_id = uuid4()
        
        # Mock query chain for deletion
        mock_query = Mock()
        mock_filter = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.delete.return_value = 3  # Number of deleted records
        
        result = repository.delete_by_session(session_id)
        
        # Contract: should return number of deleted records
        assert isinstance(result, int)
        assert result == 3
        mock_session.flush.assert_called_once()

    def test_get_filtered_contract(self, repository, mock_session):
        """Test that get_filtered follows the expected contract."""
        # Mock query chain
        mock_query = Mock()
        mock_order = Mock()
        mock_all = []
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query  # Chainable filters
        mock_query.order_by.return_value = mock_order
        mock_order.all.return_value = mock_all
        
        result = repository.get_filtered(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_types=["chat", "pald_extraction"],
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
        )
        
        # Contract: should return list of filtered results
        assert isinstance(result, list)
        assert result == mock_all

    def test_get_interaction_count_by_type_contract(self, repository, mock_session):
        """Test that get_interaction_count_by_type follows the expected contract."""
        # Mock query chain for aggregation
        mock_query = Mock()
        mock_group_by = Mock()
        mock_all = [("chat", 5), ("pald_extraction", 3)]
        
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query  # Chainable filters
        mock_query.group_by.return_value = mock_group_by
        mock_group_by.all.return_value = mock_all
        
        result = repository.get_interaction_count_by_type()
        
        # Contract: should return dictionary of type -> count
        assert isinstance(result, dict)
        assert result == {"chat": 5, "pald_extraction": 3}

    def test_error_handling_contract(self, repository, mock_session):
        """Test that repository handles errors gracefully."""
        # Test create with session exception
        mock_session.add.side_effect = Exception("Database error")
        
        log_data = InteractionLogCreate(
            pseudonym_id=uuid4(),
            session_id=uuid4(),
            interaction_type="chat",
            model_used="gpt-4",
            parameters={},
            latency_ms=1000,
        )
        
        result = repository.create(log_data)
        
        # Contract: should handle errors gracefully and return None
        assert result is None

        # Reset the side effect for next test
        mock_session.add.side_effect = None
        
        # Test get_by_id with exception
        mock_session.query.side_effect = Exception("Query error")
        
        result = repository.get_by_id(uuid4())
        
        # Contract: should handle errors gracefully and return None
        assert result is None

    def test_method_signatures_contract(self, repository):
        """Test that all methods have the expected signatures."""
        import inspect
        
        # Test create method signature
        create_sig = inspect.signature(repository.create)
        assert 'log_data' in create_sig.parameters
        
        # Test get_by_id method signature
        get_by_id_sig = inspect.signature(repository.get_by_id)
        assert 'log_id' in get_by_id_sig.parameters
        
        # Test get_by_session method signature
        get_by_session_sig = inspect.signature(repository.get_by_session)
        assert 'session_id' in get_by_session_sig.parameters
        
        # Test get_by_pseudonym method signature
        get_by_pseudonym_sig = inspect.signature(repository.get_by_pseudonym)
        assert 'pseudonym_id' in get_by_pseudonym_sig.parameters
        assert 'limit' in get_by_pseudonym_sig.parameters
        
        # Test update method signature
        update_sig = inspect.signature(repository.update)
        assert 'log_id' in update_sig.parameters
        assert 'update_data' in update_sig.parameters
        
        # Test delete methods signatures
        delete_pseudonym_sig = inspect.signature(repository.delete_by_pseudonym)
        assert 'pseudonym_id' in delete_pseudonym_sig.parameters
        
        delete_session_sig = inspect.signature(repository.delete_by_session)
        assert 'session_id' in delete_session_sig.parameters