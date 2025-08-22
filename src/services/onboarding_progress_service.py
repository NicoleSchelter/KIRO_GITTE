"""
Onboarding Progress Service
Service for managing onboarding workflow progress separate from PALD.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OnboardingProgressService:
    """Service for managing onboarding workflow progress."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def update_progress(
        self, 
        user_id: UUID, 
        step: str, 
        step_data: dict[str, Any] | None = None
    ) -> 'OnboardingProgress':
        """Update user's onboarding progress."""
        try:
            # Import here to avoid circular imports
            from src.data.models import OnboardingProgress
            
            # Get or create progress record
            progress = self.db_session.query(OnboardingProgress).filter(
                OnboardingProgress.user_id == user_id
            ).first()
            
            if not progress:
                progress = OnboardingProgress(
                    user_id=user_id,
                    current_step=step,
                    completed_steps=[],
                    step_data=step_data or {},
                    progress_percentage=0.0
                )
                self.db_session.add(progress)
            else:
                progress.current_step = step
                if step_data:
                    current_data = progress.step_data or {}
                    progress.step_data = {**current_data, **step_data}
                progress.updated_at = datetime.utcnow()
            
            self.db_session.commit()
            logger.info(f"Updated onboarding progress for user {user_id}: {step}")
            return progress
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error updating onboarding progress for user {user_id}: {e}")
            raise
    
    def get_user_progress(self, user_id: UUID) -> 'OnboardingProgress | None':
        """Get user's current onboarding progress."""
        try:
            from src.data.models import OnboardingProgress
            return self.db_session.query(OnboardingProgress).filter(
                OnboardingProgress.user_id == user_id
            ).first()
        except Exception as e:
            logger.error(f"Error retrieving onboarding progress for user {user_id}: {e}")
            return None
    
    def mark_step_completed(self, user_id: UUID, step: str) -> None:
        """Mark a specific onboarding step as completed."""
        progress = self.get_user_progress(user_id)
        if progress:
            completed = progress.completed_steps or []
            if step not in completed:
                completed.append(step)
                progress.completed_steps = completed
                
                # Update progress percentage (assuming 7 total steps)
                total_steps = 7
                progress.progress_percentage = len(completed) / total_steps * 100
                
                self.db_session.commit()
                logger.info(f"Marked step '{step}' completed for user {user_id}")
    
    def complete_onboarding(self, user_id: UUID) -> None:
        """Mark onboarding as fully completed."""
        progress = self.get_user_progress(user_id)
        if progress:
            progress.completed_at = datetime.utcnow()
            progress.progress_percentage = 100.0
            progress.current_step = "complete"
            self.db_session.commit()
            logger.info(f"Completed onboarding for user {user_id}")