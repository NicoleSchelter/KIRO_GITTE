"""
Federated Learning Service Layer for GITTE.
Handles FL client communication, update submission, and server interaction.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import requests

from config.config import config
from src.data.repositories import FederatedLearningRepository
from src.logic.federated_learning import FederatedLearningLogic, ModelUpdate

logger = logging.getLogger(__name__)


class FederatedLearningClient:
    """
    Federated Learning Client for embodiment personalization.
    Handles communication with FL server and local update management.
    """

    def __init__(self, fl_repository: FederatedLearningRepository):
        self.fl_repository = fl_repository
        self.fl_logic = FederatedLearningLogic()
        self.server_url = config.federated_learning.server_url
        self.client_id = config.federated_learning.client_id
        self.current_round = 0

    def collect_embodiment_preferences(self, user_id: UUID, user_pseudonym: str) -> dict[str, Any]:
        """
        Collect structured embodiment preference signals from user interactions.

        Args:
            user_id: User ID
            user_pseudonym: User's pseudonym for privacy

        Returns:
            Dict with collection status and signal count
        """
        try:
            if not config.feature_flags.use_federated_learning:
                return {"status": "disabled", "signal_count": 0}

            # This would typically be called from UI interactions
            # For now, return current buffer status
            signal_count = self.fl_logic.get_signal_count()

            return {
                "status": "active",
                "signal_count": signal_count,
                "ready_for_update": self.fl_logic.is_ready_for_update(),
                "privacy_budget": self.fl_logic.get_privacy_budget_status(),
            }

        except Exception as e:
            logger.error(f"Failed to collect embodiment preferences: {e}")
            return {"status": "error", "error": str(e)}

    def create_personalization_update(self, user_id: UUID) -> ModelUpdate | None:
        """
        Create local model update for embodiment personalization.

        Args:
            user_id: User ID for the update

        Returns:
            ModelUpdate or None if creation failed
        """
        try:
            if not config.feature_flags.use_federated_learning:
                logger.debug("Federated learning disabled")
                return None

            # Create local update from collected signals
            update = self.fl_logic.create_local_update(user_id)

            if update:
                logger.info(f"Created personalization update for user {user_id}")
            else:
                logger.debug(f"No update created for user {user_id} - insufficient signals")

            return update

        except Exception as e:
            logger.error(f"Failed to create personalization update: {e}")
            return None

    def submit_update(self, user_id: UUID, update: ModelUpdate) -> dict[str, Any]:
        """
        Submit model update to FL server and store locally.

        Args:
            user_id: User ID
            update: Model update to submit

        Returns:
            Dict with submission result
        """
        try:
            # Store update locally first
            fl_update_record = self.fl_repository.create_fl_update(
                user_id=user_id,
                update_data=update.update_weights,
                model_version=update.model_version,
                aggregation_round=self.current_round,
                privacy_budget_used=update.privacy_budget_used,
            )

            if not fl_update_record:
                return {"status": "error", "message": "Failed to store update locally"}

            # Submit to FL server if configured
            if self.server_url:
                server_result = self._submit_to_server(update)
                if server_result["status"] == "success":
                    # Mark as processed
                    self.fl_repository.mark_update_processed(fl_update_record.id)

                return server_result
            else:
                # Local-only mode
                logger.info("FL server not configured, storing update locally only")
                return {
                    "status": "success",
                    "message": "Update stored locally (server not configured)",
                    "update_id": str(fl_update_record.id),
                }

        except Exception as e:
            logger.error(f"Failed to submit update: {e}")
            return {"status": "error", "message": str(e)}

    def _submit_to_server(self, update: ModelUpdate) -> dict[str, Any]:
        """
        Submit update to FL server via HTTP API.

        Args:
            update: Model update to submit

        Returns:
            Dict with server response
        """
        try:
            if not self.server_url:
                return {"status": "error", "message": "FL server URL not configured"}

            payload = {
                "client_id": self.client_id,
                "update_id": update.update_id,
                "model_version": update.model_version,
                "update_data": update.update_weights.hex(),  # Convert bytes to hex
                "privacy_budget": update.privacy_budget_used,
                "signal_count": update.signal_count,
                "timestamp": update.created_at.isoformat(),
            }

            response = requests.post(
                f"{self.server_url}/api/v1/updates",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully submitted update {update.update_id} to server")
                return {"status": "success", "server_response": result}
            else:
                logger.error(f"Server rejected update: {response.status_code} - {response.text}")
                return {
                    "status": "error",
                    "message": f"Server error: {response.status_code}",
                    "details": response.text,
                }

        except requests.RequestException as e:
            logger.error(f"Failed to connect to FL server: {e}")
            return {"status": "error", "message": f"Connection error: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error submitting to server: {e}")
            return {"status": "error", "message": str(e)}

    def apply_global_embodiment_model(self, global_update: dict[str, Any]) -> bool:
        """
        Apply global model update received from FL server.

        Args:
            global_update: Global model update from server

        Returns:
            bool: True if applied successfully
        """
        try:
            if not config.feature_flags.use_federated_learning:
                return False

            # Extract global model parameters
            model_version = global_update.get("model_version")
            aggregation_round = global_update.get("aggregation_round")
            global_weights = global_update.get("global_weights")

            if not all([model_version, aggregation_round is not None, global_weights]):
                logger.error("Invalid global update format")
                return False

            # Update local model version
            self.fl_logic.current_model_version = model_version
            self.current_round = aggregation_round

            # In a real implementation, this would update the actual model weights
            # For now, we just log the update
            logger.info(
                f"Applied global model update: version {model_version}, round {aggregation_round}"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to apply global model update: {e}")
            return False

    def get_fl_status(self, user_id: UUID) -> dict[str, Any]:
        """
        Get federated learning status for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with FL status information
        """
        try:
            # Get recent updates from database
            recent_updates = self.fl_repository.get_user_updates(user_id, limit=10)

            # Get current signal status
            signal_status = self.fl_logic.get_privacy_budget_status()

            return {
                "enabled": config.feature_flags.use_federated_learning,
                "server_configured": self.server_url is not None,
                "current_round": self.current_round,
                "model_version": self.fl_logic.current_model_version,
                "recent_updates_count": len(recent_updates),
                "signals_in_buffer": self.fl_logic.get_signal_count(),
                "ready_for_update": self.fl_logic.is_ready_for_update(),
                "privacy_budget": signal_status,
            }

        except Exception as e:
            logger.error(f"Failed to get FL status: {e}")
            return {"enabled": False, "error": str(e)}

    def record_pald_interaction(
        self, user_pseudonym: str, pald_slot: str, value: Any, confidence: float = 1.0
    ) -> bool:
        """
        Record PALD interaction signal for FL.

        Args:
            user_pseudonym: User's pseudonym
            pald_slot: PALD attribute name
            value: Structured value
            confidence: Confidence score

        Returns:
            bool: True if recorded successfully
        """
        return self.fl_logic.collect_pald_signal(user_pseudonym, pald_slot, value, confidence)

    def record_feedback_interaction(
        self, user_pseudonym: str, feedback_type: str, target_element: str, rating: float
    ) -> bool:
        """
        Record user feedback signal for FL.

        Args:
            user_pseudonym: User's pseudonym
            feedback_type: Type of feedback
            target_element: Element being rated
            rating: Rating value

        Returns:
            bool: True if recorded successfully
        """
        return self.fl_logic.collect_feedback_signal(
            user_pseudonym, feedback_type, target_element, rating
        )

    def record_consistency_interaction(
        self, user_pseudonym: str, embodiment_attribute: str, consistency_score: float
    ) -> bool:
        """
        Record consistency signal for FL.

        Args:
            user_pseudonym: User's pseudonym
            embodiment_attribute: Attribute being evaluated
            consistency_score: Consistency score

        Returns:
            bool: True if recorded successfully
        """
        return self.fl_logic.collect_consistency_signal(
            user_pseudonym, embodiment_attribute, consistency_score
        )


class FederatedLearningServerStub:
    """
    Stub implementation of FL server for testing and development.
    Provides basic aggregation functionality using FedAvg algorithm.
    """

    def __init__(self):
        self.client_updates: dict[str, list[dict[str, Any]]] = {}
        self.global_model_version = "1.0.0"
        self.current_round = 0
        self.min_clients_for_aggregation = 2

    def receive_update(self, client_id: str, update_data: dict[str, Any]) -> dict[str, Any]:
        """
        Receive client update for aggregation.

        Args:
            client_id: Client identifier
            update_data: Client's model update

        Returns:
            Dict with reception confirmation
        """
        try:
            if client_id not in self.client_updates:
                self.client_updates[client_id] = []

            self.client_updates[client_id].append(
                {**update_data, "received_at": datetime.utcnow().isoformat()}
            )

            logger.info(f"Received update from client {client_id}")

            # Check if we can perform aggregation
            total_updates = sum(len(updates) for updates in self.client_updates.values())
            can_aggregate = len(self.client_updates) >= self.min_clients_for_aggregation

            return {
                "status": "received",
                "client_id": client_id,
                "total_updates": total_updates,
                "can_aggregate": can_aggregate,
                "current_round": self.current_round,
            }

        except Exception as e:
            logger.error(f"Failed to receive update from {client_id}: {e}")
            return {"status": "error", "message": str(e)}

    def perform_aggregation(self) -> dict[str, Any] | None:
        """
        Perform FedAvg aggregation of client updates.

        Returns:
            Dict with global model update or None if insufficient updates
        """
        try:
            if len(self.client_updates) < self.min_clients_for_aggregation:
                logger.debug("Insufficient clients for aggregation")
                return None

            # Simple FedAvg implementation for demonstration
            aggregated_weights = {}
            total_signal_count = 0

            for client_id, updates in self.client_updates.items():
                for update in updates:
                    # Deserialize update weights (simplified)
                    try:
                        update_weights_hex = update.get("update_data", "")
                        if update_weights_hex:
                            # In real implementation, this would deserialize actual model weights
                            signal_count = update.get("signal_count", 1)
                            total_signal_count += signal_count

                            # Aggregate privacy budgets
                            privacy_budget = update.get("privacy_budget", {})
                            for key, value in privacy_budget.items():
                                if key not in aggregated_weights:
                                    aggregated_weights[key] = 0
                                aggregated_weights[key] += value * signal_count
                    except Exception as e:
                        logger.warning(f"Failed to process update from {client_id}: {e}")

            if total_signal_count == 0:
                return None

            # Average the weights
            for key in aggregated_weights:
                aggregated_weights[key] /= total_signal_count

            # Create global update
            self.current_round += 1
            global_update = {
                "model_version": self.global_model_version,
                "aggregation_round": self.current_round,
                "global_weights": aggregated_weights,
                "participating_clients": len(self.client_updates),
                "total_signals": total_signal_count,
                "aggregated_at": datetime.utcnow().isoformat(),
            }

            # Clear client updates for next round
            self.client_updates.clear()

            logger.info(f"Performed aggregation for round {self.current_round}")
            return global_update

        except Exception as e:
            logger.error(f"Failed to perform aggregation: {e}")
            return None

    def get_global_model(self) -> dict[str, Any]:
        """
        Get current global model state.

        Returns:
            Dict with global model information
        """
        return {
            "model_version": self.global_model_version,
            "current_round": self.current_round,
            "active_clients": len(self.client_updates),
            "min_clients_required": self.min_clients_for_aggregation,
        }


# Global FL client instance
_fl_client: FederatedLearningClient | None = None


def get_fl_client() -> FederatedLearningClient:
    """Get the global FL client instance."""
    global _fl_client

    if _fl_client is None:
        from src.data.repositories import get_fl_repository

        _fl_client = FederatedLearningClient(get_fl_repository())

    return _fl_client


def set_fl_client(client: FederatedLearningClient) -> None:
    """Set the global FL client instance."""
    global _fl_client
    _fl_client = client


# Convenience functions
def collect_embodiment_preferences(user_id: UUID, user_pseudonym: str) -> dict[str, Any]:
    """Collect embodiment preferences using the global FL client."""
    return get_fl_client().collect_embodiment_preferences(user_id, user_pseudonym)


def create_personalization_update(user_id: UUID) -> ModelUpdate | None:
    """Create personalization update using the global FL client."""
    return get_fl_client().create_personalization_update(user_id)


def submit_update(user_id: UUID, update: ModelUpdate) -> dict[str, Any]:
    """Submit update using the global FL client."""
    return get_fl_client().submit_update(user_id, update)


def record_pald_interaction(
    user_pseudonym: str, pald_slot: str, value: Any, confidence: float = 1.0
) -> bool:
    """Record PALD interaction using the global FL client."""
    return get_fl_client().record_pald_interaction(user_pseudonym, pald_slot, value, confidence)


def record_feedback_interaction(
    user_pseudonym: str, feedback_type: str, target_element: str, rating: float
) -> bool:
    """Record feedback interaction using the global FL client."""
    return get_fl_client().record_feedback_interaction(
        user_pseudonym, feedback_type, target_element, rating
    )


def record_consistency_interaction(
    user_pseudonym: str, embodiment_attribute: str, consistency_score: float
) -> bool:
    """Record consistency interaction using the global FL client."""
    return get_fl_client().record_consistency_interaction(
        user_pseudonym, embodiment_attribute, consistency_score
    )


def get_fl_status(user_id: UUID) -> dict[str, Any]:
    """Get FL status using the global FL client."""
    return get_fl_client().get_fl_status(user_id)
