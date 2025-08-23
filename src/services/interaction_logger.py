"""
Interaction Logger Service for Study Participation.
Provides comprehensive audit logging for research data collection with pseudonym-based identity management.
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.data.models import InteractionLog
from src.data.repositories import InteractionLogRepository
from src.data.schemas import InteractionLogCreate, InteractionLogResponse

logger = logging.getLogger(__name__)


class InteractionLogEntry:
    """
    Interaction log entry for study participation AI interactions.
    Provides context management for comprehensive research data logging.
    """

    def __init__(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        interaction_type: str,
        model_used: str,
        parameters: Dict[str, Any],
        interaction_logger: Optional["InteractionLogger"] = None,
    ):
        self.pseudonym_id = pseudonym_id
        self.session_id = session_id
        self.interaction_type = interaction_type
        self.model_used = model_used
        self.parameters = parameters
        self.interaction_logger = interaction_logger
        self.log_id: Optional[UUID] = None
        self.start_time = datetime.utcnow()
        self.prompt: Optional[str] = None
        self.response: Optional[str] = None
        self.token_usage: Optional[Dict[str, int]] = None
        self._finalized = False

    def __enter__(self):
        """Initialize interaction log entry."""
        if self.interaction_logger:
            self.log_id = self.interaction_logger.initialize_log(
                pseudonym_id=self.pseudonym_id,
                session_id=self.session_id,
                interaction_type=self.interaction_type,
                model_used=self.model_used,
                parameters=self.parameters,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finalize interaction log entry."""
        if not self._finalized and self.interaction_logger and self.log_id:
            # Calculate latency
            latency_ms = int((datetime.utcnow() - self.start_time).total_seconds() * 1000)
            
            self.interaction_logger.finalize_log(
                log_id=self.log_id,
                prompt=self.prompt,
                response=self.response,
                token_usage=self.token_usage,
                latency_ms=latency_ms,
            )
            self._finalized = True

    def set_prompt(self, prompt: str):
        """Set prompt data for the interaction log."""
        self.prompt = prompt

    def set_response(self, response: str):
        """Set response data for the interaction log."""
        self.response = response

    def set_token_usage(self, token_usage: Dict[str, int]):
        """Set token usage data for the interaction log."""
        self.token_usage = token_usage

    def add_parameter(self, key: str, value: Any):
        """Add parameter to the interaction log."""
        self.parameters[key] = value
        if self.interaction_logger and self.log_id:
            self.interaction_logger.update_parameters(self.log_id, self.parameters)


class InteractionLogger:
    """
    Service for comprehensive interaction logging in study participation.
    Handles pseudonym-based logging with session threading and metadata capture.
    """

    def __init__(self, db_session: Session):
        """
        Initialize interaction logger.

        Args:
            db_session: Database session for logging operations
        """
        self.db_session = db_session
        self.repository = InteractionLogRepository(db_session)

    @contextmanager
    def create_interaction_context(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        interaction_type: str,
        model_used: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        """
        Create interaction context for comprehensive logging.

        Args:
            pseudonym_id: Pseudonym ID for the participant
            session_id: Session ID for threading interactions
            interaction_type: Type of AI interaction (chat, pald_extraction, image_generation, etc.)
            model_used: AI model being used
            parameters: Interaction parameters including model settings

        Yields:
            InteractionLogEntry: Context manager for interaction logging
        """
        entry = InteractionLogEntry(
            pseudonym_id=pseudonym_id,
            session_id=session_id,
            interaction_type=interaction_type,
            model_used=model_used,
            parameters=parameters or {},
            interaction_logger=self,
        )

        try:
            with entry:
                yield entry
        except Exception as e:
            logger.error(f"Error in interaction context: {e}")
            raise

    def initialize_log(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        interaction_type: str,
        model_used: str,
        parameters: Dict[str, Any],
    ) -> Optional[UUID]:
        """
        Initialize interaction log entry.

        Args:
            pseudonym_id: Pseudonym ID for the participant
            session_id: Session ID for threading
            interaction_type: Type of interaction
            model_used: AI model being used
            parameters: Interaction parameters

        Returns:
            UUID: Log ID if successful, None otherwise
        """
        try:
            log_data = InteractionLogCreate(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_type=interaction_type,
                model_used=model_used,
                parameters=parameters,
                latency_ms=0,  # Will be updated when finalized
            )

            interaction_log = self.repository.create(log_data)
            if interaction_log:
                self.db_session.commit()
                logger.debug(
                    f"Initialized interaction log {interaction_log.log_id} for {interaction_type}"
                )
                return interaction_log.log_id
            else:
                logger.error(f"Failed to initialize interaction log for {interaction_type}")
                return None

        except Exception as e:
            logger.error(f"Error initializing interaction log: {e}")
            self.db_session.rollback()
            return None

    def finalize_log(
        self,
        log_id: UUID,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        token_usage: Optional[Dict[str, int]] = None,
        latency_ms: Optional[int] = None,
    ) -> bool:
        """
        Finalize interaction log entry with complete data.

        Args:
            log_id: Log ID to finalize
            prompt: AI prompt used
            response: AI response received
            token_usage: Token usage statistics
            latency_ms: Total interaction latency

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current log to update
            current_log = self.repository.get_by_id(log_id)
            if not current_log:
                logger.error(f"Interaction log {log_id} not found for finalization")
                return False

            # Update log with final data
            update_data = {}
            if prompt is not None:
                update_data["prompt"] = prompt
            if response is not None:
                update_data["response"] = response
            if token_usage is not None:
                update_data["token_usage"] = token_usage
            if latency_ms is not None:
                update_data["latency_ms"] = latency_ms

            updated_log = self.repository.update(log_id, update_data)
            if updated_log:
                self.db_session.commit()
                logger.debug(f"Finalized interaction log {log_id}")
                return True
            else:
                logger.error(f"Failed to finalize interaction log {log_id}")
                return False

        except Exception as e:
            logger.error(f"Error finalizing interaction log {log_id}: {e}")
            self.db_session.rollback()
            return False

    def update_parameters(self, log_id: UUID, parameters: Dict[str, Any]) -> bool:
        """
        Update parameters for an interaction log.

        Args:
            log_id: Log ID to update
            parameters: Updated parameters

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            updated_log = self.repository.update(log_id, {"parameters": parameters})
            if updated_log:
                self.db_session.commit()
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error updating parameters for log {log_id}: {e}")
            self.db_session.rollback()
            return False

    def log_ai_interaction(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        interaction_type: str,
        model_used: str,
        prompt: str,
        response: str,
        parameters: Dict[str, Any],
        token_usage: Optional[Dict[str, int]] = None,
        latency_ms: Optional[int] = None,
    ) -> Optional[UUID]:
        """
        Log a complete AI interaction in one call.

        Args:
            pseudonym_id: Pseudonym ID for the participant
            session_id: Session ID for threading
            interaction_type: Type of interaction
            model_used: AI model used
            prompt: AI prompt
            response: AI response
            parameters: Interaction parameters
            token_usage: Token usage statistics
            latency_ms: Interaction latency

        Returns:
            UUID: Log ID if successful, None otherwise
        """
        try:
            log_data = InteractionLogCreate(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_type=interaction_type,
                prompt=prompt,
                response=response,
                model_used=model_used,
                parameters=parameters,
                token_usage=token_usage,
                latency_ms=latency_ms or 0,
            )

            interaction_log = self.repository.create(log_data)
            if interaction_log:
                self.db_session.commit()
                logger.debug(f"Logged AI interaction {interaction_log.log_id}")
                return interaction_log.log_id
            else:
                logger.error("Failed to log AI interaction")
                return None

        except Exception as e:
            logger.error(f"Error logging AI interaction: {e}")
            self.db_session.rollback()
            return None

    def get_session_interactions(self, session_id: UUID) -> List[InteractionLogResponse]:
        """
        Get all interactions for a specific session.

        Args:
            session_id: Session ID to retrieve

        Returns:
            List[InteractionLogResponse]: List of interactions in chronological order
        """
        try:
            interactions = self.repository.get_by_session(session_id)
            return [
                InteractionLogResponse(
                    log_id=log.log_id,
                    pseudonym_id=log.pseudonym_id,
                    session_id=log.session_id,
                    interaction_type=log.interaction_type,
                    prompt=log.prompt,
                    response=log.response,
                    model_used=log.model_used,
                    parameters=log.parameters,
                    token_usage=log.token_usage,
                    latency_ms=log.latency_ms,
                    timestamp=log.timestamp,
                )
                for log in interactions
            ]

        except Exception as e:
            logger.error(f"Error getting session interactions for {session_id}: {e}")
            return []

    def get_pseudonym_interactions(
        self, pseudonym_id: UUID, limit: Optional[int] = None
    ) -> List[InteractionLogResponse]:
        """
        Get all interactions for a specific pseudonym.

        Args:
            pseudonym_id: Pseudonym ID to retrieve
            limit: Maximum number of interactions to return

        Returns:
            List[InteractionLogResponse]: List of interactions in chronological order
        """
        try:
            interactions = self.repository.get_by_pseudonym(pseudonym_id, limit=limit)
            return [
                InteractionLogResponse(
                    log_id=log.log_id,
                    pseudonym_id=log.pseudonym_id,
                    session_id=log.session_id,
                    interaction_type=log.interaction_type,
                    prompt=log.prompt,
                    response=log.response,
                    model_used=log.model_used,
                    parameters=log.parameters,
                    token_usage=log.token_usage,
                    latency_ms=log.latency_ms,
                    timestamp=log.timestamp,
                )
                for log in interactions
            ]

        except Exception as e:
            logger.error(f"Error getting pseudonym interactions for {pseudonym_id}: {e}")
            return []

    def export_interaction_data(
        self,
        pseudonym_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        interaction_types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Export interaction data for research analysis.

        Args:
            pseudonym_id: Filter by specific pseudonym
            session_id: Filter by specific session
            interaction_types: Filter by interaction types
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List[Dict]: Exported interaction data
        """
        try:
            interactions = self.repository.get_filtered(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_types=interaction_types,
                start_date=start_date,
                end_date=end_date,
            )

            return [
                {
                    "log_id": str(log.log_id),
                    "pseudonym_id": str(log.pseudonym_id),
                    "session_id": str(log.session_id),
                    "interaction_type": log.interaction_type,
                    "prompt": log.prompt,
                    "response": log.response,
                    "model_used": log.model_used,
                    "parameters": log.parameters,
                    "token_usage": log.token_usage,
                    "latency_ms": log.latency_ms,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                }
                for log in interactions
            ]

        except Exception as e:
            logger.error(f"Error exporting interaction data: {e}")
            return []

    def get_interaction_statistics(
        self,
        pseudonym_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get interaction statistics for analysis.

        Args:
            pseudonym_id: Filter by specific pseudonym
            start_date: Start date for statistics
            end_date: End date for statistics

        Returns:
            Dict: Interaction statistics
        """
        try:
            interactions = self.repository.get_filtered(
                pseudonym_id=pseudonym_id,
                start_date=start_date,
                end_date=end_date,
            )

            if not interactions:
                return {
                    "total_interactions": 0,
                    "interaction_type_breakdown": {},
                    "model_usage_breakdown": {},
                    "average_latency_ms": 0.0,
                    "total_tokens": 0,
                    "unique_sessions": 0,
                }

            # Calculate statistics
            interaction_type_counts = {}
            model_usage_counts = {}
            total_latency = 0
            total_tokens = 0
            unique_sessions = set()

            for log in interactions:
                # Interaction type breakdown
                interaction_type_counts[log.interaction_type] = (
                    interaction_type_counts.get(log.interaction_type, 0) + 1
                )

                # Model usage breakdown
                model_usage_counts[log.model_used] = (
                    model_usage_counts.get(log.model_used, 0) + 1
                )

                # Latency and tokens
                if log.latency_ms:
                    total_latency += log.latency_ms
                if log.token_usage:
                    if isinstance(log.token_usage, dict):
                        total_tokens += sum(log.token_usage.values())
                    else:
                        total_tokens += log.token_usage

                # Unique sessions
                unique_sessions.add(log.session_id)

            # Calculate averages
            total_interactions = len(interactions)
            average_latency = total_latency / total_interactions if total_interactions > 0 else 0

            return {
                "total_interactions": total_interactions,
                "interaction_type_breakdown": interaction_type_counts,
                "model_usage_breakdown": model_usage_counts,
                "average_latency_ms": average_latency,
                "total_tokens": total_tokens,
                "unique_sessions": len(unique_sessions),
                "period_start": start_date.isoformat() if start_date else None,
                "period_end": end_date.isoformat() if end_date else None,
            }

        except Exception as e:
            logger.error(f"Error getting interaction statistics: {e}")
            return {}

    def delete_pseudonym_data(self, pseudonym_id: UUID) -> bool:
        """
        Delete all interaction data for a specific pseudonym.
        Used for GDPR compliance and participant data deletion requests.

        Args:
            pseudonym_id: Pseudonym ID to delete data for

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            deleted_count = self.repository.delete_by_pseudonym(pseudonym_id)
            self.db_session.commit()
            logger.info(f"Deleted {deleted_count} interaction logs for pseudonym {pseudonym_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting interaction data for {pseudonym_id}: {e}")
            self.db_session.rollback()
            return False


# Convenience functions for common interaction logging operations
def create_interaction_context(
    db_session: Session,
    pseudonym_id: UUID,
    session_id: UUID,
    interaction_type: str,
    model_used: str,
    parameters: Optional[Dict[str, Any]] = None,
):
    """Create interaction context using a provided database session."""
    logger_instance = InteractionLogger(db_session)
    return logger_instance.create_interaction_context(
        pseudonym_id=pseudonym_id,
        session_id=session_id,
        interaction_type=interaction_type,
        model_used=model_used,
        parameters=parameters,
    )


def log_ai_interaction(
    db_session: Session,
    pseudonym_id: UUID,
    session_id: UUID,
    interaction_type: str,
    model_used: str,
    prompt: str,
    response: str,
    parameters: Dict[str, Any],
    token_usage: Optional[Dict[str, int]] = None,
    latency_ms: Optional[int] = None,
) -> Optional[UUID]:
    """Log a complete AI interaction using a provided database session."""
    logger_instance = InteractionLogger(db_session)
    return logger_instance.log_ai_interaction(
        pseudonym_id=pseudonym_id,
        session_id=session_id,
        interaction_type=interaction_type,
        model_used=model_used,
        prompt=prompt,
        response=response,
        parameters=parameters,
        token_usage=token_usage,
        latency_ms=latency_ms,
    )