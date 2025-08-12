"""
Onboarding logic for GITTE system.
Handles guided onboarding flow orchestration, state management, and personalization data collection.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from src.data.models import ConsentType
from src.data.repositories import UserRepository
from src.data.schemas import PALDDataCreate
from src.logic.pald import PALDManager
from src.services.consent_service import ConsentService

logger = logging.getLogger(__name__)


class OnboardingStep(str, Enum):
    """Onboarding step enumeration."""

    CONSENT = "consent"
    SURVEY = "survey"
    DESIGN = "design"
    CHAT = "chat"
    IMAGE_GENERATION = "image_generation"
    FEEDBACK = "feedback"
    COMPLETE = "complete"


class OnboardingStatus(str, Enum):
    """Onboarding status enumeration."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class OnboardingError(Exception):
    """Base exception for onboarding errors."""

    pass


class OnboardingFlowError(OnboardingError):
    """Exception raised for onboarding flow errors."""

    pass


class OnboardingStateError(OnboardingError):
    """Exception raised for onboarding state errors."""

    pass


class OnboardingLogic:
    """Logic for managing guided onboarding flow."""

    def __init__(
        self,
        user_repository: UserRepository,
        consent_service: ConsentService,
        pald_manager: PALDManager,
    ):
        self.user_repository = user_repository
        self.consent_service = consent_service
        self.pald_manager = pald_manager

        # Define onboarding flow steps
        self.flow_steps = [
            OnboardingStep.CONSENT,
            OnboardingStep.SURVEY,
            OnboardingStep.DESIGN,
            OnboardingStep.CHAT,
            OnboardingStep.IMAGE_GENERATION,
            OnboardingStep.FEEDBACK,
            OnboardingStep.COMPLETE,
        ]

        # Define required consents for each step
        self.step_consent_requirements = {
            OnboardingStep.CONSENT: [],  # No prior consent needed
            OnboardingStep.SURVEY: [ConsentType.DATA_PROCESSING],
            OnboardingStep.DESIGN: [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            OnboardingStep.CHAT: [ConsentType.DATA_PROCESSING, ConsentType.AI_INTERACTION],
            OnboardingStep.IMAGE_GENERATION: [
                ConsentType.DATA_PROCESSING,
                ConsentType.IMAGE_GENERATION,
            ],
            OnboardingStep.FEEDBACK: [ConsentType.DATA_PROCESSING],
            OnboardingStep.COMPLETE: [],
        }

    def get_user_onboarding_state(self, user_id: UUID) -> dict[str, Any]:
        """
        Get current onboarding state for user.

        Args:
            user_id: User identifier

        Returns:
            Dict containing onboarding state information
        """
        try:
            # Get user's PALD data to check onboarding progress
            pald_data_list = self.pald_manager.get_user_pald_data(user_id)

            # Check if user has completed onboarding
            onboarding_complete = False
            current_step = OnboardingStep.CONSENT
            completed_steps = []
            personalization_data = {}

            if pald_data_list:
                # Find onboarding-related PALD data
                for pald_data in pald_data_list:
                    content = pald_data.pald_content

                    # Check for survey completion
                    if content.get("survey_completed_at"):
                        completed_steps.append(OnboardingStep.SURVEY)
                        personalization_data.update(content)

                    # Check for embodiment design completion
                    if content.get("embodiment_characteristics"):
                        completed_steps.append(OnboardingStep.DESIGN)
                        personalization_data["embodiment_characteristics"] = content.get(
                            "embodiment_characteristics"
                        )

                    # Check for onboarding completion marker
                    if content.get("onboarding_completed_at"):
                        onboarding_complete = True
                        completed_steps = self.flow_steps[:-1]  # All except COMPLETE

            # Check consent completion
            consent_status = self.consent_service.get_consent_status(user_id)
            if any(consent_status.values()):
                completed_steps.append(OnboardingStep.CONSENT)

            # Determine current step
            if not onboarding_complete:
                for step in self.flow_steps:
                    if step not in completed_steps:
                        current_step = step
                        break
                else:
                    current_step = OnboardingStep.COMPLETE
            else:
                current_step = OnboardingStep.COMPLETE

            # Calculate progress
            progress = len(completed_steps) / len(self.flow_steps)

            return {
                "user_id": user_id,
                "status": (
                    OnboardingStatus.COMPLETED
                    if onboarding_complete
                    else OnboardingStatus.IN_PROGRESS
                ),
                "current_step": current_step,
                "completed_steps": completed_steps,
                "progress": progress,
                "personalization_data": personalization_data,
                "onboarding_complete": onboarding_complete,
            }

        except Exception as e:
            logger.error(f"Error getting onboarding state for user {user_id}: {e}")
            raise OnboardingStateError(f"Failed to get onboarding state: {e}")

    def can_access_step(self, user_id: UUID, step: OnboardingStep) -> tuple[bool, str | None]:
        """
        Check if user can access a specific onboarding step.

        Args:
            user_id: User identifier
            step: Onboarding step to check

        Returns:
            Tuple of (can_access, reason_if_not)
        """
        try:
            # Check if step requires consent
            required_consents = self.step_consent_requirements.get(step, [])

            for consent_type in required_consents:
                if not self.consent_service.check_consent(user_id, consent_type):
                    return False, f"Missing required consent: {consent_type.value}"

            # Check if user has completed prerequisite steps
            state = self.get_user_onboarding_state(user_id)
            current_step_index = self.flow_steps.index(state["current_step"])
            target_step_index = self.flow_steps.index(step)

            if target_step_index > current_step_index:
                return False, f"Must complete step {state['current_step'].value} first"

            return True, None

        except Exception as e:
            logger.error(f"Error checking step access for user {user_id}, step {step}: {e}")
            return False, f"Error checking access: {e}"

    def advance_to_next_step(
        self, user_id: UUID, current_step: OnboardingStep, step_data: dict[str, Any] | None = None
    ) -> OnboardingStep:
        """
        Advance user to next onboarding step.

        Args:
            user_id: User identifier
            current_step: Current step being completed
            step_data: Data collected in current step

        Returns:
            Next onboarding step
        """
        try:
            # Store step completion data if provided
            if step_data:
                self._store_step_data(user_id, current_step, step_data)

            # Mark step as completed
            self._mark_step_completed(user_id, current_step)

            # Determine next step
            current_index = self.flow_steps.index(current_step)

            if current_index < len(self.flow_steps) - 1:
                next_step = self.flow_steps[current_index + 1]
            else:
                next_step = OnboardingStep.COMPLETE

            # If reaching complete step, mark onboarding as finished
            if next_step == OnboardingStep.COMPLETE:
                self._complete_onboarding(user_id)

            logger.info(f"User {user_id} advanced from {current_step} to {next_step}")
            return next_step

        except Exception as e:
            logger.error(f"Error advancing user {user_id} from step {current_step}: {e}")
            raise OnboardingFlowError(f"Failed to advance to next step: {e}")

    def collect_personalization_data(
        self, user_id: UUID, data_type: str, data: dict[str, Any]
    ) -> None:
        """
        Collect and store personalization data during onboarding.

        Args:
            user_id: User identifier
            data_type: Type of personalization data
            data: Personalization data to store
        """
        try:
            # Create PALD data entry for personalization
            pald_content = {
                "data_type": data_type,
                "collected_at": datetime.now().isoformat(),
                "onboarding_data": True,
                **data,
            }

            pald_create = PALDDataCreate(pald_content=pald_content, schema_version="1.0")

            self.pald_manager.create_pald_data(user_id, pald_create)

            logger.info(f"Collected personalization data for user {user_id}: {data_type}")

        except Exception as e:
            logger.error(f"Error collecting personalization data for user {user_id}: {e}")
            raise OnboardingError(f"Failed to collect personalization data: {e}")

    def get_onboarding_summary(self, user_id: UUID) -> dict[str, Any]:
        """
        Get comprehensive onboarding summary for user.

        Args:
            user_id: User identifier

        Returns:
            Dict containing onboarding summary
        """
        try:
            state = self.get_user_onboarding_state(user_id)

            # Get consent summary
            consent_status = self.consent_service.get_consent_status(user_id)

            # Extract key personalization data
            personalization = state.get("personalization_data", {})

            summary = {
                "user_id": user_id,
                "onboarding_status": state["status"],
                "completion_progress": state["progress"],
                "completed_steps": len(state["completed_steps"]),
                "total_steps": len(self.flow_steps),
                "current_step": state["current_step"],
                "consents_given": sum(1 for granted in consent_status.values() if granted),
                "total_consent_types": len(consent_status),
                "learning_preferences": personalization.get("learning_preferences", {}),
                "embodiment_design": personalization.get("embodiment_characteristics", {}),
                "survey_completed": bool(personalization.get("survey_completed_at")),
                "onboarding_completed": state["onboarding_complete"],
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting onboarding summary for user {user_id}: {e}")
            raise OnboardingError(f"Failed to get onboarding summary: {e}")

    def reset_onboarding(self, user_id: UUID) -> None:
        """
        Reset user's onboarding progress (admin function).

        Args:
            user_id: User identifier
        """
        try:
            # This would typically involve:
            # 1. Removing onboarding completion markers from PALD data
            # 2. Optionally resetting consent (with user confirmation)
            # 3. Clearing cached onboarding state

            # For now, we'll just log the action
            logger.warning(f"Onboarding reset requested for user {user_id}")

            # In a full implementation, you would:
            # - Update PALD data to remove completion markers
            # - Reset session state
            # - Optionally withdraw consents

        except Exception as e:
            logger.error(f"Error resetting onboarding for user {user_id}: {e}")
            raise OnboardingError(f"Failed to reset onboarding: {e}")

    def _store_step_data(self, user_id: UUID, step: OnboardingStep, data: dict[str, Any]) -> None:
        """Store data collected during a specific step."""
        try:
            step_data = {
                "step": step.value,
                "completed_at": datetime.now().isoformat(),
                "step_data": data,
            }

            self.collect_personalization_data(user_id, f"onboarding_step_{step.value}", step_data)

        except Exception as e:
            logger.error(f"Error storing step data for user {user_id}, step {step}: {e}")
            raise

    def _mark_step_completed(self, user_id: UUID, step: OnboardingStep) -> None:
        """Mark a specific step as completed."""
        try:
            completion_data = {
                "step_completed": step.value,
                "completed_at": datetime.now().isoformat(),
            }

            self.collect_personalization_data(
                user_id, f"step_completion_{step.value}", completion_data
            )

        except Exception as e:
            logger.error(f"Error marking step completed for user {user_id}, step {step}: {e}")
            raise

    def _complete_onboarding(self, user_id: UUID) -> None:
        """Mark onboarding as fully completed."""
        try:
            completion_data = {
                "onboarding_completed_at": datetime.now().isoformat(),
                "completion_version": "1.0",
                "all_steps_completed": True,
            }

            self.collect_personalization_data(user_id, "onboarding_completion", completion_data)

            logger.info(f"Onboarding completed for user {user_id}")

        except Exception as e:
            logger.error(f"Error completing onboarding for user {user_id}: {e}")
            raise


def get_onboarding_logic() -> OnboardingLogic:
    """Get onboarding logic instance with dependencies."""
    from src.data.database import get_session
    from src.data.repositories import get_user_repository
    from src.services.consent_service import get_consent_service

    # Note: In a real application, you'd want to manage the database session lifecycle properly
    # For now, we'll create a new session each time
    db_session_context = get_session()
    db_session = db_session_context.__enter__()

    return OnboardingLogic(
        user_repository=get_user_repository(),
        consent_service=get_consent_service(),
        pald_manager=PALDManager(db_session),
    )
