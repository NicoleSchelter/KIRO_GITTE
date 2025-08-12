"""
Unit tests for federated learning logic layer.
Tests embodiment personalization, signal collection, and privacy mechanisms.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from config.config import config
from src.logic.federated_learning import (
    DifferentialPrivacyParams,
    EmbodimentSignal,
    FederatedLearningLogic,
    ModelUpdate,
)


class TestFederatedLearningLogic:
    """Test cases for FederatedLearningLogic."""

    @pytest.fixture
    def fl_logic(self):
        """Create FL logic instance for testing."""
        return FederatedLearningLogic()

    @pytest.fixture
    def sample_user_pseudonym(self):
        """Sample user pseudonym for testing."""
        return f"user_pseudo_{uuid4().hex[:8]}"

    def test_initialization(self, fl_logic):
        """Test FL logic initialization."""
        assert fl_logic.dp_params.epsilon == config.federated_learning.differential_privacy_epsilon
        assert fl_logic.dp_params.delta == config.federated_learning.differential_privacy_delta
        assert fl_logic.signals_buffer == []
        assert fl_logic.current_model_version == "1.0.0"

    def test_collect_pald_signal_success(self, fl_logic, sample_user_pseudonym):
        """Test successful PALD signal collection."""
        # Enable FL for this test
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            result = fl_logic.collect_pald_signal(
                user_pseudonym=sample_user_pseudonym,
                pald_slot="learning_style",
                value="visual",
                confidence=0.8,
            )

            assert result is True
            assert len(fl_logic.signals_buffer) == 1

            signal = fl_logic.signals_buffer[0]
            assert signal.signal_type == "pald_slot"
            assert signal.signal_data["slot"] == "learning_style"
            assert signal.signal_data["value"] == "visual"
            assert signal.signal_data["confidence"] == 0.8
            assert signal.user_pseudonym == sample_user_pseudonym

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_collect_pald_signal_disabled(self, fl_logic, sample_user_pseudonym):
        """Test PALD signal collection when FL is disabled."""
        # Ensure FL is disabled
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = False

        try:
            result = fl_logic.collect_pald_signal(
                user_pseudonym=sample_user_pseudonym, pald_slot="learning_style", value="visual"
            )

            assert result is False
            assert len(fl_logic.signals_buffer) == 0

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_collect_feedback_signal_success(self, fl_logic, sample_user_pseudonym):
        """Test successful feedback signal collection."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            result = fl_logic.collect_feedback_signal(
                user_pseudonym=sample_user_pseudonym,
                feedback_type="like",
                target_element="avatar",
                rating=4.5,
            )

            assert result is True
            assert len(fl_logic.signals_buffer) == 1

            signal = fl_logic.signals_buffer[0]
            assert signal.signal_type == "feedback_click"
            assert signal.signal_data["feedback_type"] == "like"
            assert signal.signal_data["target_element"] == "avatar"
            assert signal.signal_data["rating"] == 4.5

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_collect_consistency_signal_success(self, fl_logic, sample_user_pseudonym):
        """Test successful consistency signal collection."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            result = fl_logic.collect_consistency_signal(
                user_pseudonym=sample_user_pseudonym,
                embodiment_attribute="personality",
                consistency_score=0.9,
            )

            assert result is True
            assert len(fl_logic.signals_buffer) == 1

            signal = fl_logic.signals_buffer[0]
            assert signal.signal_type == "consistency_label"
            assert signal.signal_data["attribute"] == "personality"
            assert signal.signal_data["consistency_score"] == 0.9

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_create_local_update_no_signals(self, fl_logic):
        """Test local update creation with no signals."""
        user_id = uuid4()
        update = fl_logic.create_local_update(user_id)

        assert update is None

    def test_create_local_update_with_signals(self, fl_logic, sample_user_pseudonym):
        """Test local update creation with signals."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            # Add some signals
            fl_logic.collect_pald_signal(sample_user_pseudonym, "learning_style", "visual", 0.8)
            fl_logic.collect_feedback_signal(sample_user_pseudonym, "like", "avatar", 4.0)
            fl_logic.collect_consistency_signal(sample_user_pseudonym, "personality", 0.9)

            user_id = uuid4()
            update = fl_logic.create_local_update(user_id)

            assert update is not None
            assert isinstance(update, ModelUpdate)
            assert update.model_version == "1.0.0"
            assert update.signal_count == 3
            assert isinstance(update.update_weights, bytes)
            assert "epsilon_used" in update.privacy_budget_used
            assert "delta_used" in update.privacy_budget_used
            assert "signal_count" in update.privacy_budget_used

            # Buffer should be cleared after update creation
            assert len(fl_logic.signals_buffer) == 0

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_aggregate_signals(self, fl_logic, sample_user_pseudonym):
        """Test signal aggregation."""
        # Add multiple signals of different types
        fl_logic.signals_buffer = [
            EmbodimentSignal(
                "pald_slot",
                {"slot": "style", "value": "visual", "confidence": 0.8},
                datetime.utcnow(),
                sample_user_pseudonym,
            ),
            EmbodimentSignal(
                "pald_slot",
                {"slot": "style", "value": "auditory", "confidence": 0.6},
                datetime.utcnow(),
                sample_user_pseudonym,
            ),
            EmbodimentSignal(
                "feedback_click",
                {"feedback_type": "like", "target_element": "avatar", "rating": 4.0},
                datetime.utcnow(),
                sample_user_pseudonym,
            ),
            EmbodimentSignal(
                "consistency_label",
                {"attribute": "personality", "consistency_score": 0.9},
                datetime.utcnow(),
                sample_user_pseudonym,
            ),
        ]

        aggregated = fl_logic._aggregate_signals()

        assert "pald_signals" in aggregated
        assert "feedback_signals" in aggregated
        assert "consistency_signals" in aggregated

        assert "style" in aggregated["pald_signals"]
        assert len(aggregated["pald_signals"]["style"]) == 2

        assert "avatar" in aggregated["feedback_signals"]
        assert len(aggregated["feedback_signals"]["avatar"]) == 1

        assert "personality" in aggregated["consistency_signals"]
        assert len(aggregated["consistency_signals"]["personality"]) == 1

    def test_apply_differential_privacy(self, fl_logic):
        """Test differential privacy application."""
        signals = {
            "pald_signals": {
                "style": [
                    {"value": "visual", "confidence": 0.8},
                    {"value": "auditory", "confidence": 0.6},
                ]
            },
            "feedback_signals": {
                "avatar": [{"type": "like", "rating": 4.0}, {"type": "like", "rating": 5.0}]
            },
            "consistency_signals": {"personality": [0.9, 0.8]},
        }

        private_signals = fl_logic._apply_differential_privacy(signals)

        assert "pald_style" in private_signals
        assert "feedback_avatar" in private_signals
        assert "consistency_personality" in private_signals

        # Check that values are within expected ranges
        assert 0.0 <= private_signals["pald_style"] <= 1.0
        assert 0.0 <= private_signals["feedback_avatar"] <= 5.0
        assert 0.0 <= private_signals["consistency_personality"] <= 1.0

    def test_serialize_update(self, fl_logic):
        """Test update serialization."""
        update_data = {"pald_style": 0.7, "feedback_avatar": 4.2, "consistency_personality": 0.85}

        serialized = fl_logic._serialize_update(update_data)

        assert isinstance(serialized, bytes)
        assert len(serialized) > 0

        # Test deserialization
        import gzip
        import json

        decompressed = gzip.decompress(serialized)
        deserialized = json.loads(decompressed.decode("utf-8"))

        assert deserialized["pald_style"] == 0.7
        assert deserialized["feedback_avatar"] == 4.2
        assert deserialized["consistency_personality"] == 0.85

    def test_signal_count_management(self, fl_logic, sample_user_pseudonym):
        """Test signal count and buffer management."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            assert fl_logic.get_signal_count() == 0

            fl_logic.collect_pald_signal(sample_user_pseudonym, "style", "visual")
            assert fl_logic.get_signal_count() == 1

            fl_logic.collect_feedback_signal(sample_user_pseudonym, "like", "avatar", 4.0)
            assert fl_logic.get_signal_count() == 2

            fl_logic.clear_signals()
            assert fl_logic.get_signal_count() == 0

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_ready_for_update(self, fl_logic, sample_user_pseudonym):
        """Test update readiness check."""
        original_flag = config.feature_flags.use_federated_learning
        config.feature_flags.use_federated_learning = True

        try:
            assert not fl_logic.is_ready_for_update(min_signals=5)

            # Add signals
            for i in range(6):
                fl_logic.collect_pald_signal(sample_user_pseudonym, f"attr_{i}", f"value_{i}")

            assert fl_logic.is_ready_for_update(min_signals=5)

        finally:
            config.feature_flags.use_federated_learning = original_flag

    def test_privacy_budget_status(self, fl_logic):
        """Test privacy budget status reporting."""
        status = fl_logic.get_privacy_budget_status()

        assert "epsilon_limit" in status
        assert "delta_limit" in status
        assert "epsilon_remaining" in status
        assert "delta_remaining" in status

        assert status["epsilon_limit"] == fl_logic.dp_params.epsilon
        assert status["delta_limit"] == fl_logic.dp_params.delta

    def test_differential_privacy_params(self):
        """Test differential privacy parameters initialization."""
        params = DifferentialPrivacyParams(
            epsilon=2.0, delta=1e-4, clip_norm=2.0, noise_multiplier=0.5
        )

        assert params.epsilon == 2.0
        assert params.delta == 1e-4
        assert params.clip_norm == 2.0
        assert params.noise_multiplier == 0.5

    def test_embodiment_signal_creation(self):
        """Test EmbodimentSignal dataclass."""
        signal = EmbodimentSignal(
            signal_type="test_signal",
            signal_data={"key": "value"},
            timestamp=datetime.utcnow(),
            user_pseudonym="test_pseudo",
        )

        assert signal.signal_type == "test_signal"
        assert signal.signal_data["key"] == "value"
        assert signal.user_pseudonym == "test_pseudo"
        assert isinstance(signal.timestamp, datetime)

    def test_model_update_creation(self):
        """Test ModelUpdate dataclass."""
        update = ModelUpdate(
            update_id="test_update",
            model_version="1.0.0",
            update_weights=b"test_weights",
            privacy_budget_used={"epsilon": 1.0},
            signal_count=5,
            created_at=datetime.utcnow(),
        )

        assert update.update_id == "test_update"
        assert update.model_version == "1.0.0"
        assert update.update_weights == b"test_weights"
        assert update.privacy_budget_used["epsilon"] == 1.0
        assert update.signal_count == 5
        assert isinstance(update.created_at, datetime)
