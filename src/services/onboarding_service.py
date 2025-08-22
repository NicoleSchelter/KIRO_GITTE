"""
Onboarding Service
Service for managing onboarding workflow with step transitions.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# Explicit onboarding step transition map
ONBOARDING_TRANSITIONS = {
    "survey": "intro_chat",
    "intro_chat": "design", 
    "design": "chat",
    "chat": "image_generation",
    "image_generation": "feedback",
    "feedback": "complete",
    "complete": "complete"  # Terminal state
}

# Progress percentage mapping
STEP_PROGRESS = {
    "survey": 15,
    "intro_chat": 30,
    "design": 45,
    "chat": 60,
    "image_generation": 75,
    "feedback": 90,
    "complete": 100
}


def advance_onboarding_step(user_id: UUID, completed_step: str) -> bool:
    """
    Advance onboarding step with concurrency safety and idempotency.
    
    Args:
        user_id: User identifier
        completed_step: Step that was just completed
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from src.data.database import get_session
        from src.data.models import OnboardingProgress, User
        
        with get_session() as db_session:
            # Begin transaction
            with db_session.begin():
                # Verify user exists
                user = db_session.query(User).filter(User.id == user_id).first()
                if not user:
                    logger.error(f"User {user_id} not found in database")
                    return False
                
                # Get or create progress record with SELECT FOR UPDATE for concurrency safety
                progress = db_session.query(OnboardingProgress).filter(
                    OnboardingProgress.user_id == user_id
                ).with_for_update().first()
                
                if not progress:
                    # Create new progress record
                    progress = OnboardingProgress(
                        user_id=user_id,
                        current_step=completed_step,
                        completed_steps=[],
                        step_data={},
                        progress_percentage=0.0
                    )
                    db_session.add(progress)
                    db_session.flush()  # Get the ID
                
                # Idempotent: add completed_step to completed_steps if not already present
                completed_steps = progress.completed_steps or []
                if completed_step not in completed_steps:
                    completed_steps.append(completed_step)
                    progress.completed_steps = completed_steps
                
                # Compute next step from transition map
                next_step = ONBOARDING_TRANSITIONS.get(completed_step, "complete")
                
                # Update progress
                progress.current_step = next_step
                progress.progress_percentage = STEP_PROGRESS.get(next_step, 100)
                progress.updated_at = datetime.utcnow()
                
                # Mark as completed if we've reached the end
                if next_step == "complete":
                    progress.completed_at = datetime.utcnow()
                
                # Flush to ensure changes are written
                db_session.flush()
                
                logger.info(
                    f"Advanced onboarding for user {user_id}: {completed_step} -> {next_step} "
                    f"({progress.progress_percentage}%)"
                )
                
                return True
                
    except Exception as e:
        logger.exception(f"Failed to advance onboarding step for user {user_id}, step {completed_step}: {e}")
        return False