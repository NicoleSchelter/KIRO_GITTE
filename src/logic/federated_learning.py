"""
Federated Learning Logic Layer for GITTE.
Handles embodiment personalization through federated learning with privacy preservation.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import numpy as np

from config.config import config

logger = logging.getLogger(__name__)


@dataclass
class EmbodimentSignal:
    """Structured signal for embodiment personalization."""

    signal_type: str  # "pald_slot", "feedback_click", "consistency_label"
    signal_data: dict[str, Any]
    timestamp: datetime
    user_pseudonym: str


@dataclass
class ModelUpdate:
    """Local model update for federated learning."""

    update_id: str
    model_version: str
    update_weights: bytes  # Serialized model weights
    privacy_budget_used: dict[str, float]
    signal_count: int
    created_at: datetime


@dataclass
class DifferentialPrivacyParams:
    """Differential privacy parameters."""

    epsilon: float = 1.0
    delta: float = 1e-5
    clip_norm: float = 1.0
    noise_multiplier: float = 1.0


class FederatedLearningLogic:
    """
    Logic layer for federated learning operations.
    Handles embodiment personalization without exposing raw data.
    """

    def __init__(self):
        self.dp_params = DifferentialPrivacyParams(
            epsilon=config.federated_learning.differential_privacy_epsilon,
            delta=config.federated_learning.differential_privacy_delta,
        )
        self.signals_buffer: list[EmbodimentSignal] = []
        self.current_model_version = "1.0.0"

    def collect_pald_signal(
        self, user_pseudonym: str, pald_slot: str, value: Any, confidence: float = 1.0
    ) -> bool:
        """
        Collect PALD slot signal for embodiment personalization.

        Args:
            user_pseudonym: User's pseudonym (no raw user data)
            pald_slot: PALD attribute name
            value: Structured value (no raw text)
            confidence: Confidence score for the signal

        Returns:
            bool: True if signal collected successfully
        """
        try:
            if not config.feature_flags.use_federated_learning:
                logger.debug("Federated learning disabled, skipping PALD signal collection")
                return False

            signal = EmbodimentSignal(
                signal_type="pald_slot",
                signal_data={"slot": pald_slot, "value": value, "confidence": confidence},
                timestamp=datetime.utcnow(),
                user_pseudonym=user_pseudonym,
            )

            self.signals_buffer.append(signal)
            logger.debug(f"Collected PALD signal for slot {pald_slot}")
            return True

        except Exception as e:
            logger.error(f"Failed to collect PALD signal: {e}")
            return False

    def collect_feedback_signal(
        self, user_pseudonym: str, feedback_type: str, target_element: str, rating: float
    ) -> bool:
        """
        Collect user feedback signal for embodiment improvement.

        Args:
            user_pseudonym: User's pseudonym
            feedback_type: Type of feedback ("like", "dislike", "rating")
            target_element: Element being rated ("avatar", "response", "image")
            rating: Numerical rating or binary feedback

        Returns:
            bool: True if signal collected successfully
        """
        try:
            if not config.feature_flags.use_federated_learning:
                return False

            signal = EmbodimentSignal(
                signal_type="feedback_click",
                signal_data={
                    "feedback_type": feedback_type,
                    "target_element": target_element,
                    "rating": rating,
                },
                timestamp=datetime.utcnow(),
                user_pseudonym=user_pseudonym,
            )

            self.signals_buffer.append(signal)
            logger.debug(f"Collected feedback signal: {feedback_type} for {target_element}")
            return True

        except Exception as e:
            logger.error(f"Failed to collect feedback signal: {e}")
            return False

    def collect_consistency_signal(
        self, user_pseudonym: str, embodiment_attribute: str, consistency_score: float
    ) -> bool:
        """
        Collect consistency label for embodiment coherence.

        Args:
            user_pseudonym: User's pseudonym
            embodiment_attribute: Attribute being evaluated for consistency
            consistency_score: Score indicating consistency (0.0 to 1.0)

        Returns:
            bool: True if signal collected successfully
        """
        try:
            if not config.feature_flags.use_federated_learning:
                return False

            signal = EmbodimentSignal(
                signal_type="consistency_label",
                signal_data={
                    "attribute": embodiment_attribute,
                    "consistency_score": consistency_score,
                },
                timestamp=datetime.utcnow(),
                user_pseudonym=user_pseudonym,
            )

            self.signals_buffer.append(signal)
            logger.debug(f"Collected consistency signal for {embodiment_attribute}")
            return True

        except Exception as e:
            logger.error(f"Failed to collect consistency signal: {e}")
            return False

    def create_local_update(self, user_id: UUID) -> ModelUpdate | None:
        """
        Create local model update from collected signals with differential privacy.

        Args:
            user_id: User ID for the update

        Returns:
            ModelUpdate: Privacy-preserving model update or None if insufficient data
        """
        try:
            if not self.signals_buffer:
                logger.debug("No signals available for model update")
                return None

            # Aggregate signals into structured format
            aggregated_signals = self._aggregate_signals()

            # Apply differential privacy
            private_update = self._apply_differential_privacy(aggregated_signals)

            # Serialize update weights
            update_weights = self._serialize_update(private_update)

            # Calculate privacy budget used
            privacy_budget = {
                "epsilon_used": self.dp_params.epsilon,
                "delta_used": self.dp_params.delta,
                "signal_count": len(self.signals_buffer),
            }

            update = ModelUpdate(
                update_id=f"update_{user_id}_{datetime.utcnow().isoformat()}",
                model_version=self.current_model_version,
                update_weights=update_weights,
                privacy_budget_used=privacy_budget,
                signal_count=len(self.signals_buffer),
                created_at=datetime.utcnow(),
            )

            # Clear signals buffer after creating update
            self.signals_buffer.clear()

            logger.info(f"Created local model update with {update.signal_count} signals")
            return update

        except Exception as e:
            logger.error(f"Failed to create local update: {e}")
            return None

    def _aggregate_signals(self) -> dict[str, Any]:
        """
        Aggregate collected signals into structured format.

        Returns:
            Dict containing aggregated signal data
        """
        aggregated = {"pald_signals": {}, "feedback_signals": {}, "consistency_signals": {}}

        for signal in self.signals_buffer:
            if signal.signal_type == "pald_slot":
                slot = signal.signal_data["slot"]
                if slot not in aggregated["pald_signals"]:
                    aggregated["pald_signals"][slot] = []
                aggregated["pald_signals"][slot].append(
                    {
                        "value": signal.signal_data["value"],
                        "confidence": signal.signal_data["confidence"],
                    }
                )

            elif signal.signal_type == "feedback_click":
                target = signal.signal_data["target_element"]
                if target not in aggregated["feedback_signals"]:
                    aggregated["feedback_signals"][target] = []
                aggregated["feedback_signals"][target].append(
                    {
                        "type": signal.signal_data["feedback_type"],
                        "rating": signal.signal_data["rating"],
                    }
                )

            elif signal.signal_type == "consistency_label":
                attr = signal.signal_data["attribute"]
                if attr not in aggregated["consistency_signals"]:
                    aggregated["consistency_signals"][attr] = []
                aggregated["consistency_signals"][attr].append(
                    signal.signal_data["consistency_score"]
                )

        return aggregated

    def _apply_differential_privacy(self, signals: dict[str, Any]) -> dict[str, Any]:
        """
        Apply differential privacy to aggregated signals.

        Args:
            signals: Aggregated signal data

        Returns:
            Privacy-preserving signal data
        """
        private_signals = {}

        # Add noise to PALD signals
        for slot, values in signals["pald_signals"].items():
            if values:
                # Calculate mean confidence
                mean_confidence = np.mean([v["confidence"] for v in values])
                # Add Gaussian noise
                noise = np.random.normal(0, self.dp_params.noise_multiplier)
                private_confidence = max(0.0, min(1.0, mean_confidence + noise))

                private_signals[f"pald_{slot}"] = private_confidence

        # Add noise to feedback signals
        for target, feedbacks in signals["feedback_signals"].items():
            if feedbacks:
                # Calculate mean rating
                mean_rating = np.mean([f["rating"] for f in feedbacks])
                # Add Gaussian noise
                noise = np.random.normal(0, self.dp_params.noise_multiplier)
                private_rating = max(0.0, min(5.0, mean_rating + noise))

                private_signals[f"feedback_{target}"] = private_rating

        # Add noise to consistency signals
        for attr, scores in signals["consistency_signals"].items():
            if scores:
                # Calculate mean consistency
                mean_consistency = np.mean(scores)
                # Add Gaussian noise
                noise = np.random.normal(0, self.dp_params.noise_multiplier)
                private_consistency = max(0.0, min(1.0, mean_consistency + noise))

                private_signals[f"consistency_{attr}"] = private_consistency

        return private_signals

    def _serialize_update(self, update_data: dict[str, Any]) -> bytes:
        """
        Serialize model update data to bytes.

        Args:
            update_data: Privacy-preserving update data

        Returns:
            Serialized update as bytes
        """
        import gzip
        import json

        # Convert to JSON and compress
        json_data = json.dumps(update_data, default=str)
        compressed_data = gzip.compress(json_data.encode("utf-8"))

        return compressed_data

    def get_signal_count(self) -> int:
        """Get current number of signals in buffer."""
        return len(self.signals_buffer)

    def clear_signals(self) -> None:
        """Clear all signals from buffer."""
        self.signals_buffer.clear()
        logger.debug("Cleared signals buffer")

    def is_ready_for_update(self, min_signals: int = 10) -> bool:
        """
        Check if enough signals are collected for a meaningful update.

        Args:
            min_signals: Minimum number of signals required

        Returns:
            bool: True if ready for update
        """
        return len(self.signals_buffer) >= min_signals

    def get_privacy_budget_status(self) -> dict[str, float]:
        """
        Get current privacy budget status.

        Returns:
            Dict with privacy budget information
        """
        return {
            "epsilon_limit": self.dp_params.epsilon,
            "delta_limit": self.dp_params.delta,
            "epsilon_remaining": self.dp_params.epsilon,  # Simplified for demo
            "delta_remaining": self.dp_params.delta,
        }
