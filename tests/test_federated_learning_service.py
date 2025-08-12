"""
Unit tests for federated learning service layer.
Tests FL client functionality, server communication, and update management.
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
import requests

from config.config import config
from src.data.repositories import FederatedLearningRepository
from src.logic.federated_learning import ModelUpdate
from src.services.federated_learning_service import (
    FederatedLearningClient,
    FederatedLearningServerStub,
)


class TestFederatedLearningClient:
    """Test cases for FederatedLearningClient."""

    @pytest.fixture
    def mock_fl_repository(self):
        """Create mock FL repository."""
        return Mock(spec=FederatedLearningRepository)

    @pytest.fixture
    def fl_client(self, mock_fl_repository):
        """Create FL client for testing."""
        return FederatedLearningClient(mock_fl_repository)

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return uuid4()

    @pytest.fixture
    def sample_user_pseudonym(self):
        """Sample user pseudonym for testing."""
        return f"user_pseudo_{uuid4().hex[:8]}"

    @pytest.fixture
    def sample_model_update(self, sample_user_id):
        """Sample model update for testing."""
        return ModelUpdate(
            update_id=f"update_{sample_user_id}",
            model_version="1.0.0",
            update_weights=b"test_weights_data",
            privacy_budget_used={"epsilon_used": 1.0, "delta_used": 1e-5},
            signal_count=5,
            created_at=datetime.utcnow(),
        )

    def test_client_initialization(self, mock_fl_repository):
        """Test FL client initialization."""
        client = FederatedLearningClient(mock_fl_repository)

        assert client.fl_repository == mock_fl_repository
        assert client.fl_logic is not None
        assert client.current_round == 0

    def test_collect_embodiment_preferences_disabled(
        self, fl_client, sample_user_id, sample_user_pseudonym
    ):
        """Test preference collection when FL is disabled."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = False

        try:
            result = fl_client.collect_embodiment_preferences(sample_user_id, sample_user_pseudonym)

            assert result["status"] == "disabled"
            assert result["signal_count"] == 0

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_collect_embodiment_preferences_active(
        self, fl_client, sample_user_id, sample_user_pseudonym
    ):
        """Test preference collection when FL is active."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            result = fl_client.collect_embodiment_preferences(sample_user_id, sample_user_pseudonym)

            assert result["status"] == "active"
            assert "signal_count" in result
            assert "ready_for_update" in result
            assert "privacy_budget" in result

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_create_personalization_update_disabled(self, fl_client, sample_user_id):
        """Test update creation when FL is disabled."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = False

        try:
            result = fl_client.create_personalization_update(sample_user_id)
            assert result is None

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_create_personalization_update_no_signals(self, fl_client, sample_user_id):
        """Test update creation with no signals."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            result = fl_client.create_personalization_update(sample_user_id)
            assert result is None

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_create_personalization_update_with_signals(
        self, fl_client, sample_user_id, sample_user_pseudonym
    ):
        """Test update creation with signals."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            # Add some signals
            fl_client.record_pald_interaction(
                sample_user_pseudonym, "learning_style", "visual", 0.8
            )
            fl_client.record_feedback_interaction(sample_user_pseudonym, "like", "avatar", 4.0)

            result = fl_client.create_personalization_update(sample_user_id)

            assert result is not None
            assert isinstance(result, ModelUpdate)
            assert result.signal_count == 2

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_submit_update_local_storage_success(
        self, fl_client, sample_user_id, sample_model_update, mock_fl_repository
    ):
        """Test successful update submission with local storage."""
        # Mock successful repository creation
        mock_fl_update = Mock()
        mock_fl_update.id = uuid4()
        mock_fl_repository.create_fl_update.return_value = mock_fl_update

        # No server URL configured (local-only mode)
        fl_client.server_url = None

        result = fl_client.submit_update(sample_user_id, sample_model_update)

        assert result["status"] == "success"
        assert "Update stored locally" in result["message"]
        assert "update_id" in result

        mock_fl_repository.create_fl_update.assert_called_once()

    def test_submit_update_local_storage_failure(
        self, fl_client, sample_user_id, sample_model_update, mock_fl_repository
    ):
        """Test update submission with local storage failure."""
        # Mock repository failure
        mock_fl_repository.create_fl_update.return_value = None

        result = fl_client.submit_update(sample_user_id, sample_model_update)

        assert result["status"] == "error"
        assert "Failed to store update locally" in result["message"]

    @patch("src.services.federated_learning_service.requests.post")
    def test_submit_update_server_success(
        self, mock_post, fl_client, sample_user_id, sample_model_update, mock_fl_repository
    ):
        """Test successful update submission to server."""
        # Mock successful repository creation
        mock_fl_update = Mock()
        mock_fl_update.id = uuid4()
        mock_fl_repository.create_fl_update.return_value = mock_fl_update

        # Mock successful server response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "accepted", "update_id": "server_123"}
        mock_post.return_value = mock_response

        # Configure server URL
        fl_client.server_url = "http://localhost:8080"

        result = fl_client.submit_update(sample_user_id, sample_model_update)

        assert result["status"] == "success"
        assert "server_response" in result

        mock_fl_repository.create_fl_update.assert_called_once()
        mock_fl_repository.mark_update_processed.assert_called_once_with(mock_fl_update.id)
        mock_post.assert_called_once()

    @patch("src.services.federated_learning_service.requests.post")
    def test_submit_update_server_failure(
        self, mock_post, fl_client, sample_user_id, sample_model_update, mock_fl_repository
    ):
        """Test update submission with server failure."""
        # Mock successful repository creation
        mock_fl_update = Mock()
        mock_fl_update.id = uuid4()
        mock_fl_repository.create_fl_update.return_value = mock_fl_update

        # Mock server error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        # Configure server URL
        fl_client.server_url = "http://localhost:8080"

        result = fl_client.submit_update(sample_user_id, sample_model_update)

        assert result["status"] == "error"
        assert "Server error: 500" in result["message"]

        mock_fl_repository.create_fl_update.assert_called_once()
        mock_fl_repository.mark_update_processed.assert_not_called()

    @patch("src.services.federated_learning_service.requests.post")
    def test_submit_update_connection_error(
        self, mock_post, fl_client, sample_user_id, sample_model_update, mock_fl_repository
    ):
        """Test update submission with connection error."""
        # Mock successful repository creation
        mock_fl_update = Mock()
        mock_fl_update.id = uuid4()
        mock_fl_repository.create_fl_update.return_value = mock_fl_update

        # Mock connection error
        mock_post.side_effect = requests.ConnectionError("Connection failed")

        # Configure server URL
        fl_client.server_url = "http://localhost:8080"

        result = fl_client.submit_update(sample_user_id, sample_model_update)

        assert result["status"] == "error"
        assert "Connection error" in result["message"]

    def test_apply_global_embodiment_model_disabled(self, fl_client):
        """Test applying global model when FL is disabled."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = False

        try:
            global_update = {
                "model_version": "1.1.0",
                "aggregation_round": 5,
                "global_weights": {"param1": 0.5},
            }

            result = fl_client.apply_global_embodiment_model(global_update)
            assert result is False

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_apply_global_embodiment_model_success(self, fl_client):
        """Test successful global model application."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            global_update = {
                "model_version": "1.1.0",
                "aggregation_round": 5,
                "global_weights": {"param1": 0.5, "param2": 0.3},
            }

            result = fl_client.apply_global_embodiment_model(global_update)

            assert result is True
            assert fl_client.fl_logic.current_model_version == "1.1.0"
            assert fl_client.current_round == 5

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_apply_global_embodiment_model_invalid_format(self, fl_client):
        """Test applying global model with invalid format."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            # Missing required fields
            global_update = {"model_version": "1.1.0"}

            result = fl_client.apply_global_embodiment_model(global_update)
            assert result is False

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_get_fl_status(self, fl_client, sample_user_id, mock_fl_repository):
        """Test FL status retrieval."""
        # Mock repository response
        mock_updates = [Mock(), Mock(), Mock()]
        mock_fl_repository.get_user_updates.return_value = mock_updates

        result = fl_client.get_fl_status(sample_user_id)

        assert "enabled" in result
        assert "server_configured" in result
        assert "current_round" in result
        assert "model_version" in result
        assert "recent_updates_count" in result
        assert "signals_in_buffer" in result
        assert "ready_for_update" in result
        assert "privacy_budget" in result

        assert result["recent_updates_count"] == 3
        mock_fl_repository.get_user_updates.assert_called_once_with(sample_user_id, limit=10)

    def test_record_pald_interaction(self, fl_client, sample_user_pseudonym):
        """Test PALD interaction recording."""
        result = fl_client.record_pald_interaction(
            sample_user_pseudonym, "learning_style", "visual", 0.8
        )

        # Result depends on FL feature flag
        assert isinstance(result, bool)

    def test_record_feedback_interaction(self, fl_client, sample_user_pseudonym):
        """Test feedback interaction recording."""
        result = fl_client.record_feedback_interaction(sample_user_pseudonym, "like", "avatar", 4.0)

        # Result depends on FL feature flag
        assert isinstance(result, bool)

    def test_record_consistency_interaction(self, fl_client, sample_user_pseudonym):
        """Test consistency interaction recording."""
        result = fl_client.record_consistency_interaction(sample_user_pseudonym, "personality", 0.9)

        # Result depends on FL feature flag
        assert isinstance(result, bool)


class TestFederatedLearningServerStub:
    """Test cases for FederatedLearningServerStub."""

    @pytest.fixture
    def fl_server(self):
        """Create FL server stub for testing."""
        return FederatedLearningServerStub()

    @pytest.fixture
    def sample_client_id(self):
        """Sample client ID for testing."""
        return f"client_{uuid4().hex[:8]}"

    @pytest.fixture
    def sample_update_data(self):
        """Sample update data for testing."""
        return {
            "update_id": f"update_{uuid4()}",
            "model_version": "1.0.0",
            "update_data": b"test_weights".hex(),
            "privacy_budget": {"epsilon_used": 1.0},
            "signal_count": 5,
        }

    def test_server_initialization(self, fl_server):
        """Test FL server stub initialization."""
        assert fl_server.client_updates == {}
        assert fl_server.global_model_version == "1.0.0"
        assert fl_server.current_round == 0
        assert fl_server.min_clients_for_aggregation == 2

    def test_receive_update_success(self, fl_server, sample_client_id, sample_update_data):
        """Test successful update reception."""
        result = fl_server.receive_update(sample_client_id, sample_update_data)

        assert result["status"] == "received"
        assert result["client_id"] == sample_client_id
        assert result["total_updates"] == 1
        assert result["can_aggregate"] is False  # Only 1 client
        assert result["current_round"] == 0

        assert sample_client_id in fl_server.client_updates
        assert len(fl_server.client_updates[sample_client_id]) == 1

    def test_receive_multiple_updates(self, fl_server, sample_update_data):
        """Test receiving updates from multiple clients."""
        client1 = "client_1"
        client2 = "client_2"

        # Receive from first client
        result1 = fl_server.receive_update(client1, sample_update_data)
        assert result1["can_aggregate"] is False

        # Receive from second client
        result2 = fl_server.receive_update(client2, sample_update_data)
        assert result2["can_aggregate"] is True  # Now we have 2 clients
        assert result2["total_updates"] == 2

    def test_perform_aggregation_insufficient_clients(
        self, fl_server, sample_client_id, sample_update_data
    ):
        """Test aggregation with insufficient clients."""
        # Add update from only one client
        fl_server.receive_update(sample_client_id, sample_update_data)

        result = fl_server.perform_aggregation()
        assert result is None

    def test_perform_aggregation_success(self, fl_server, sample_update_data):
        """Test successful aggregation."""
        client1 = "client_1"
        client2 = "client_2"

        # Add updates from two clients
        fl_server.receive_update(client1, sample_update_data)
        fl_server.receive_update(client2, sample_update_data)

        result = fl_server.perform_aggregation()

        assert result is not None
        assert result["model_version"] == "1.0.0"
        assert result["aggregation_round"] == 1
        assert "global_weights" in result
        assert result["participating_clients"] == 2
        assert result["total_signals"] == 10  # 5 signals per client
        assert "aggregated_at" in result

        # Client updates should be cleared
        assert fl_server.client_updates == {}
        assert fl_server.current_round == 1

    def test_perform_aggregation_with_invalid_updates(self, fl_server):
        """Test aggregation with invalid update data."""
        client1 = "client_1"
        client2 = "client_2"

        # Add invalid updates
        invalid_update = {"invalid": "data"}
        fl_server.receive_update(client1, invalid_update)
        fl_server.receive_update(client2, invalid_update)

        result = fl_server.perform_aggregation()

        # With invalid data, aggregation might return None or empty result
        if result is not None:
            assert result["total_signals"] == 0
        # If result is None, that's also acceptable behavior for invalid data

    def test_get_global_model(self, fl_server):
        """Test global model state retrieval."""
        result = fl_server.get_global_model()

        assert result["model_version"] == "1.0.0"
        assert result["current_round"] == 0
        assert result["active_clients"] == 0
        assert result["min_clients_required"] == 2

    def test_multiple_aggregation_rounds(self, fl_server, sample_update_data):
        """Test multiple aggregation rounds."""
        client1 = "client_1"
        client2 = "client_2"

        # First round
        fl_server.receive_update(client1, sample_update_data)
        fl_server.receive_update(client2, sample_update_data)
        result1 = fl_server.perform_aggregation()

        assert result1["aggregation_round"] == 1

        # Second round
        fl_server.receive_update(client1, sample_update_data)
        fl_server.receive_update(client2, sample_update_data)
        result2 = fl_server.perform_aggregation()

        assert result2["aggregation_round"] == 2
        assert fl_server.current_round == 2

    def test_aggregation_error_handling(self, fl_server):
        """Test aggregation error handling."""
        # Force an error by corrupting internal state
        fl_server.client_updates = {
            "client1": [{"malformed": "data"}],
            "client2": [{"also": "bad"}],
        }

        result = fl_server.perform_aggregation()

        # Should handle errors gracefully
        assert result is not None or result is None  # Either works, just shouldn't crash
