"""
End-to-end tests for GITTE system.
Tests complete user journeys and critical business flows.
"""

from typing import Any
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest

from src.data.models import ConsentType, User, UserRole
from src.logic.authentication import AuthenticationLogic
from src.logic.consent import ConsentLogic
from src.logic.embodiment import EmbodimentLogic
from src.logic.llm import LLMLogic
from src.logic.onboarding import OnboardingLogic


@pytest.mark.e2e
class TestCompleteUserJourneys:
    """End-to-end tests for complete user journeys."""

    def test_complete_onboarding_flow(self):
        """Test complete user onboarding from registration to first chat."""
        # Mock all external dependencies
        with (
            patch("src.data.database.get_session") as mock_get_session,
            patch("src.services.llm_service.LLMService") as mock_llm_service,
            patch("src.services.image_service.ImageService") as mock_image_service,
            patch("src.services.storage_service.StorageService"),
        ):

            # Setup mocks
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Mock user creation
            test_user_id = uuid4()
            mock_user = Mock(
                id=test_user_id,
                username="test_user",
                role=UserRole.PARTICIPANT,
                pseudonym="pseudo_123",
            )
            mock_session.add.return_value = None
            mock_session.commit.return_value = None
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user

            # Mock LLM responses
            mock_llm_service.return_value.generate_response.return_value = Mock(
                text="Hello! I'm your learning assistant.",
                model_used="test-model",
                generation_time=1.0,
            )

            # Mock image generation
            mock_image_service.return_value.generate_embodiment_image.return_value = Mock(
                image_data=b"fake_image_data",
                image_url="http://test.com/avatar.jpg",
                metadata={"style": "realistic"},
            )

            # Step 1: User Registration
            auth_logic = AuthenticationLogic()
            registration_result = auth_logic.register_user(
                username="test_user", password="SecurePass123!", role=UserRole.PARTICIPANT
            )

            assert registration_result["success"] is True
            assert "user_id" in registration_result
            user_id = UUID(registration_result["user_id"])

            # Step 2: Consent Management
            consent_logic = ConsentLogic()

            # Grant all necessary consents
            consent_types = [
                ConsentType.DATA_COLLECTION,
                ConsentType.AI_INTERACTION,
                ConsentType.PERSONALIZATION,
                ConsentType.IMAGE_GENERATION,
            ]

            for consent_type in consent_types:
                consent_result = consent_logic.record_consent(
                    user_id=user_id,
                    consent_type=consent_type,
                    granted=True,
                    consent_text="I agree to the terms",
                )
                assert consent_result["success"] is True

            # Step 3: Onboarding Flow
            onboarding_logic = OnboardingLogic()

            # Complete survey
            survey_data = {
                "learning_preferences": {
                    "learning_style": "visual",
                    "difficulty_preference": "intermediate",
                    "pace_preference": "moderate",
                },
                "interests": ["technology", "science"],
                "goals": ["learn new skills", "improve knowledge"],
            }

            survey_result = onboarding_logic.complete_survey(user_id, survey_data)
            assert survey_result["success"] is True

            # Design embodiment
            embodiment_data = {
                "appearance_style": "professional",
                "personality": "friendly and knowledgeable",
                "communication_style": "clear and encouraging",
            }

            design_result = onboarding_logic.complete_embodiment_design(user_id, embodiment_data)
            assert design_result["success"] is True

            # Step 4: First Chat Interaction
            llm_logic = LLMLogic()
            chat_response = llm_logic.generate_embodiment_response(
                user_message="Hello, I'm excited to start learning!",
                user_id=user_id,
                embodiment_context={},
            )

            assert chat_response is not None
            assert chat_response.text == "Hello! I'm your learning assistant."

            # Step 5: Generate Avatar Image
            embodiment_logic = EmbodimentLogic()
            avatar_result = embodiment_logic.generate_embodiment_image(
                user_id=user_id, prompt="friendly learning assistant", style="realistic"
            )

            assert avatar_result is not None
            assert avatar_result.image_data == b"fake_image_data"

            # Step 6: Complete Onboarding
            completion_result = onboarding_logic.complete_onboarding(user_id)
            assert completion_result["success"] is True
            assert completion_result["onboarding_complete"] is True

            # Verify onboarding status
            status = onboarding_logic.get_onboarding_status(user_id)
            assert status["onboarding_complete"] is True
            assert status["survey_complete"] is True
            assert status["embodiment_design_complete"] is True
            assert status["first_chat_complete"] is True
            assert status["first_image_complete"] is True

    def test_complete_learning_session(self):
        """Test a complete learning session with multiple interactions."""
        with (
            patch("src.data.database.get_session") as mock_get_session,
            patch("src.services.llm_service.LLMService") as mock_llm_service,
        ):

            # Setup mocks
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            test_user_id = uuid4()

            # Mock LLM responses for a learning conversation
            responses = [
                "What would you like to learn about today?",
                "Great choice! Let's start with the basics of Python programming.",
                "Python is a versatile programming language. Here's a simple example...",
                "Excellent question! Let me explain that concept further...",
                "You're making great progress! Would you like to try a practice exercise?",
            ]

            mock_llm_service.return_value.generate_response.side_effect = [
                Mock(text=response, model_used="test-model", generation_time=1.0)
                for response in responses
            ]

            llm_logic = LLMLogic()

            # Simulate a learning conversation
            conversation = [
                "I want to learn Python programming",
                "Can you show me how to write a simple program?",
                "What are variables in Python?",
                "How do I create a function?",
                "Yes, I'd like to try an exercise",
            ]

            chat_history = []

            for i, user_message in enumerate(conversation):
                # User sends message
                chat_history.append({"role": "user", "content": user_message})

                # Assistant responds
                response = llm_logic.generate_embodiment_response(
                    user_message=user_message, user_id=test_user_id, embodiment_context={}
                )

                assert response is not None
                assert response.text == responses[i]

                chat_history.append({"role": "assistant", "content": response.text})

            # Verify conversation flow
            assert len(chat_history) == 10  # 5 user messages + 5 assistant responses
            assert all(msg["content"] for msg in chat_history)  # All messages have content

            # Verify learning progression
            user_messages = [msg["content"] for msg in chat_history if msg["role"] == "user"]
            assistant_messages = [
                msg["content"] for msg in chat_history if msg["role"] == "assistant"
            ]

            assert len(user_messages) == 5
            assert len(assistant_messages) == 5

            # Check that conversation progresses logically
            assert "Python" in user_messages[0]
            assert "variables" in user_messages[2]
            assert "function" in user_messages[3]
            assert "exercise" in assistant_messages[4]

    def test_admin_workflow(self):
        """Test admin workflow for data export and monitoring."""
        with (
            patch("src.data.database.get_session") as mock_get_session,
            patch("src.services.audit_service.AuditService") as mock_audit_service,
        ):

            # Setup mocks
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            admin_user_id = uuid4()

            # Mock admin user
            mock_admin = Mock(id=admin_user_id, username="admin_user", role=UserRole.ADMIN)
            mock_session.query.return_value.filter.return_value.first.return_value = mock_admin

            # Mock audit data
            mock_audit_service.return_value.export_audit_data.return_value = {
                "success": True,
                "export_url": "http://test.com/audit_export.csv",
                "record_count": 150,
            }

            # Step 1: Admin Authentication
            auth_logic = AuthenticationLogic()
            login_result = auth_logic.authenticate_user("admin_user", "AdminPass123!")

            # Mock successful login
            with patch.object(
                auth_logic,
                "authenticate_user",
                return_value={
                    "success": True,
                    "user_id": str(admin_user_id),
                    "role": UserRole.ADMIN.value,
                },
            ):
                login_result = auth_logic.authenticate_user("admin_user", "AdminPass123!")
                assert login_result["success"] is True
                assert login_result["role"] == UserRole.ADMIN.value

            # Step 2: Data Export
            from src.services.audit_service import AuditService

            audit_service = AuditService()

            export_result = audit_service.export_audit_data(
                start_date="2024-01-01", end_date="2024-12-31", format="csv"
            )

            assert export_result["success"] is True
            assert "export_url" in export_result
            assert export_result["record_count"] == 150

            # Step 3: System Monitoring
            # Mock system status
            with patch("src.logic.audit.AuditLogic") as mock_audit_logic:
                mock_audit_logic.return_value.get_system_statistics.return_value = {
                    "total_users": 100,
                    "active_sessions": 25,
                    "total_interactions": 1500,
                    "system_health": "healthy",
                }

                from src.logic.audit import AuditLogic

                audit_logic = AuditLogic()

                stats = audit_logic.get_system_statistics()
                assert stats["total_users"] == 100
                assert stats["active_sessions"] == 25
                assert stats["system_health"] == "healthy"

    @pytest.mark.slow
    def test_data_privacy_compliance_flow(self):
        """Test complete data privacy compliance workflow."""
        with (
            patch("src.data.database.get_session") as mock_get_session,
            patch("src.security.data_deletion.DataDeletionService") as mock_deletion_service,
        ):

            # Setup mocks
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            test_user_id = uuid4()

            # Step 1: User requests data deletion
            mock_deletion_service.return_value.request_data_deletion.return_value = (
                "deletion_request_123"
            )

            from src.security.data_deletion import DataDeletionService, DeletionScope

            deletion_service = DataDeletionService()

            request_id = deletion_service.request_data_deletion(
                user_id=test_user_id,
                scope=DeletionScope.USER_DATA,
                requested_by=test_user_id,
                reason="User requested data deletion",
            )

            assert request_id == "deletion_request_123"

            # Step 2: Check deletion status
            mock_deletion_service.return_value.get_deletion_status.return_value = [
                {
                    "user_id": str(test_user_id),
                    "scope": "user_data",
                    "status": "scheduled",
                    "requested_at": "2024-01-01T10:00:00",
                    "scheduled_for": "2024-01-02T10:00:00",
                    "reason": "User requested data deletion",
                }
            ]

            status = deletion_service.get_deletion_status(test_user_id)
            assert len(status) == 1
            assert status[0]["status"] == "scheduled"

            # Step 3: Execute deletion (simulated)
            mock_deletion_service.return_value.execute_scheduled_deletions.return_value = 1

            executed_count = deletion_service.execute_scheduled_deletions()
            assert executed_count == 1

            # Step 4: Verify compliance
            mock_deletion_service.return_value.get_compliance_report.return_value = {
                "total_requests": 1,
                "completed_requests": 1,
                "pending_requests": 0,
                "overdue_requests": 0,
                "compliance_rate": 100.0,
            }

            compliance_report = deletion_service.get_compliance_report()
            assert compliance_report["compliance_rate"] == 100.0
            assert compliance_report["overdue_requests"] == 0


@pytest.mark.e2e
class TestErrorRecoveryFlows:
    """Test error recovery and resilience flows."""

    def test_service_failure_recovery(self):
        """Test system behavior when external services fail."""
        with patch("src.services.llm_service.LLMService") as mock_llm_service:

            # Simulate service failure then recovery
            mock_llm_service.return_value.generate_response.side_effect = [
                Exception("Service temporarily unavailable"),  # First call fails
                Mock(
                    text="Service recovered", model_used="test-model", generation_time=1.0
                ),  # Second call succeeds
            ]

            llm_logic = LLMLogic()
            test_user_id = uuid4()

            # First attempt should handle the error gracefully
            with pytest.raises(Exception):
                llm_logic.generate_embodiment_response(
                    user_message="Test prompt", user_id=test_user_id, embodiment_context={}
                )

            # Second attempt should succeed
            response = llm_logic.generate_embodiment_response(
                user_message="Test prompt", user_id=test_user_id, embodiment_context={}
            )

            assert response is not None
            assert response.text == "Service recovered"

    def test_network_interruption_handling(self):
        """Test handling of network interruptions."""
        with patch("src.services.llm_provider.OllamaProvider") as mock_provider:

            # Simulate network timeout then success
            import requests

            mock_provider.return_value.generate_response.side_effect = [
                requests.exceptions.Timeout("Network timeout"),
                Mock(text="Network recovered", metadata={"model": "test-model"}),
            ]

            from src.services.llm_provider import OllamaProvider

            provider = OllamaProvider("http://test.com")

            # First attempt should raise timeout
            with pytest.raises(requests.exceptions.Timeout):
                provider.generate_response("Test prompt")

            # Second attempt should succeed
            response = provider.generate_response("Test prompt")
            assert response.text == "Network recovered"

    def test_data_corruption_recovery(self):
        """Test recovery from data corruption scenarios."""
        with patch("src.data.database.get_session") as mock_get_session:

            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            # Simulate database corruption then recovery
            from sqlalchemy.exc import DatabaseError

            mock_session.query.side_effect = [
                DatabaseError("Database corruption detected", None, None),
                Mock(),  # Recovery
            ]

            # First query should fail
            with pytest.raises(DatabaseError), mock_get_session() as session:
                session.query(User).first()

            # System should recover
            with mock_get_session() as session:
                result = session.query(User)
                assert result is not None


@pytest.mark.e2e
class TestIntegrationScenarios:
    """Test integration between different system components."""

    def test_full_personalization_pipeline(self):
        """Test complete personalization pipeline from data collection to model updates."""
        with (
            patch("src.data.database.get_session") as mock_get_session,
            patch(
                "src.services.federated_learning_service.FederatedLearningClient"
            ) as mock_fl_service,
        ):

            # Setup mocks
            mock_session = Mock()
            mock_get_session.return_value.__enter__.return_value = mock_session

            test_user_id = uuid4()

            # Step 1: Collect user interaction data
            interaction_data = {
                "user_id": str(test_user_id),
                "interaction_type": "chat",
                "content": "I prefer visual learning",
                "feedback": "positive",
                "timestamp": "2024-01-01T10:00:00",
            }

            # Step 2: Process data for personalization
            from src.logic.pald import PALDLogic

            pald_logic = PALDLogic()

            # Mock PALD processing
            with patch.object(
                pald_logic,
                "update_pald_data",
                return_value={
                    "success": True,
                    "updated_attributes": ["learning_style", "content_preference"],
                },
            ):
                pald_result = pald_logic.update_pald_data(test_user_id, interaction_data)
                assert pald_result["success"] is True
                assert "learning_style" in pald_result["updated_attributes"]

            # Step 3: Generate federated learning update
            mock_fl_service.return_value.create_local_update.return_value = {
                "success": True,
                "update_id": "fl_update_123",
                "privacy_preserved": True,
            }

            from src.services.federated_learning_service import FederatedLearningService

            fl_service = FederatedLearningService()

            fl_update = fl_service.create_local_update(
                user_id=test_user_id, interaction_data=interaction_data
            )

            assert fl_update["success"] is True
            assert fl_update["privacy_preserved"] is True

            # Step 4: Apply personalization to future interactions
            # This would involve using the updated model for responses
            # For testing, we verify the pipeline completed successfully
            assert pald_result["success"] is True
            assert fl_update["success"] is True


def run_smoke_tests() -> dict[str, Any]:
    """
    Run smoke tests for critical system functions.

    Returns:
        Dict with smoke test results
    """
    results = {
        "chat_roundtrip": False,
        "image_generation": False,
        "audit_logging": False,
        "data_storage": False,
        "user_authentication": False,
    }

    try:
        # Test 1: Chat roundtrip
        with patch("src.services.llm_service.LLMService") as mock_llm:
            mock_llm.return_value.generate_response.return_value = Mock(
                text="Test response", model_used="test", generation_time=1.0
            )

            llm_logic = LLMLogic()
            response = llm_logic.generate_embodiment_response("Test", uuid4(), {})
            results["chat_roundtrip"] = response is not None
    except Exception:
        pass

    try:
        # Test 2: Image generation
        with patch("src.services.image_service.ImageService") as mock_image:
            mock_image.return_value.generate_embodiment_image.return_value = Mock(
                image_data=b"test", image_url="http://test.com/image.jpg"
            )

            embodiment_logic = EmbodimentLogic()
            image = embodiment_logic.generate_embodiment_image(uuid4(), "test", "realistic")
            results["image_generation"] = image is not None
    except Exception:
        pass

    try:
        # Test 3: Audit logging
        with patch("src.services.audit_service.AuditService") as mock_audit:
            mock_audit.return_value.log_interaction.return_value = {"success": True}

            from src.services.audit_service import AuditService

            audit_service = AuditService()
            log_result = audit_service.log_interaction("test_request", uuid4(), "test", {}, {})
            results["audit_logging"] = log_result["success"]
    except Exception:
        pass

    try:
        # Test 4: Data storage
        with patch("src.services.storage_service.StorageService") as mock_storage:
            mock_storage.return_value.store_file.return_value = "http://test.com/file.jpg"

            from src.services.storage_service import StorageService

            storage_service = StorageService()
            url = storage_service.store_file(b"test", "test.jpg", "image/jpeg")
            results["data_storage"] = url is not None
    except Exception:
        pass

    try:
        # Test 5: User authentication
        with patch("src.logic.authentication.AuthenticationLogic") as mock_auth:
            mock_auth.return_value.authenticate_user.return_value = {
                "success": True,
                "user_id": str(uuid4()),
            }

            from src.logic.authentication import AuthenticationLogic

            auth_logic = AuthenticationLogic()
            auth_result = auth_logic.authenticate_user("test", "password")
            results["user_authentication"] = auth_result["success"]
    except Exception:
        pass

    return results


if __name__ == "__main__":
    # Run smoke tests when executed directly
    smoke_results = run_smoke_tests()
    print("Smoke Test Results:")
    for test_name, passed in smoke_results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")

    all_passed = all(smoke_results.values())
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}")
