"""
Chat Service Layer for Study Participation
Handles data persistence for chat messages, PALD data, and interaction logging.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from src.data.models import (
    ChatMessage,
    ChatMessageType,
    FeedbackRecord,
    GeneratedImage,
    InteractionLog,
    StudyPALDData,
    StudyPALDType,
)
from src.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


class ChatService:
    """Service layer for chat data persistence and retrieval."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def store_chat_message(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        message_type: ChatMessageType,
        content: str,
        pald_data: dict[str, Any] | None = None,
    ) -> ChatMessage:
        """
        Store a chat message in the database.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            message_type: Type of message (user, assistant, system)
            content: Message content
            pald_data: Optional PALD data extracted from message
            
        Returns:
            ChatMessage: Stored message object
            
        Raises:
            DatabaseError: If storage fails
            ValidationError: If input validation fails
        """
        try:
            if not content.strip():
                raise ValidationError("Message content cannot be empty")
            
            message = ChatMessage(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                message_type=message_type.value,
                content=content,
                pald_data=pald_data,
            )
            
            self.db_session.add(message)
            self.db_session.commit()
            
            logger.info(f"Stored chat message {message.message_id} for pseudonym {pseudonym_id}")
            return message
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to store chat message: {e}")
            raise DatabaseError(f"Failed to store chat message: {e}")

    def get_chat_history(
        self,
        pseudonym_id: UUID,
        session_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ChatMessage]:
        """
        Retrieve chat history for a participant.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Optional session ID to filter by
            limit: Maximum number of messages to retrieve
            
        Returns:
            list[ChatMessage]: List of chat messages ordered by timestamp
        """
        try:
            query = self.db_session.query(ChatMessage).filter(
                ChatMessage.pseudonym_id == pseudonym_id
            )
            
            if session_id:
                query = query.filter(ChatMessage.session_id == session_id)
            
            messages = (
                query.order_by(ChatMessage.timestamp.desc())
                .limit(limit)
                .all()
            )
            
            # Return in chronological order (oldest first)
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            raise DatabaseError(f"Failed to retrieve chat history: {e}")

    def store_pald_data(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        pald_content: dict[str, Any],
        pald_type: StudyPALDType,
        consistency_score: float | None = None,
    ) -> StudyPALDData:
        """
        Store PALD data in the database.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            pald_content: PALD data content
            pald_type: Type of PALD (input, description, feedback)
            consistency_score: Optional consistency score
            
        Returns:
            StudyPALDData: Stored PALD data object
            
        Raises:
            DatabaseError: If storage fails
            ValidationError: If input validation fails
        """
        try:
            if not pald_content:
                raise ValidationError("PALD content cannot be empty")
            
            pald_data = StudyPALDData(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                pald_content=pald_content,
                pald_type=pald_type.value,
                consistency_score=consistency_score,
            )
            
            self.db_session.add(pald_data)
            self.db_session.commit()
            
            logger.info(f"Stored PALD data {pald_data.pald_id} for pseudonym {pseudonym_id}")
            return pald_data
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to store PALD data: {e}")
            raise DatabaseError(f"Failed to store PALD data: {e}")

    def get_pald_data(
        self,
        pseudonym_id: UUID,
        session_id: UUID | None = None,
        pald_type: StudyPALDType | None = None,
        limit: int = 50,
    ) -> list[StudyPALDData]:
        """
        Retrieve PALD data for a participant.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Optional session ID to filter by
            pald_type: Optional PALD type to filter by
            limit: Maximum number of records to retrieve
            
        Returns:
            list[StudyPALDData]: List of PALD data records
        """
        try:
            query = self.db_session.query(StudyPALDData).filter(
                StudyPALDData.pseudonym_id == pseudonym_id
            )
            
            if session_id:
                query = query.filter(StudyPALDData.session_id == session_id)
            
            if pald_type:
                query = query.filter(StudyPALDData.pald_type == pald_type.value)
            
            return (
                query.order_by(StudyPALDData.created_at.desc())
                .limit(limit)
                .all()
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve PALD data: {e}")
            raise DatabaseError(f"Failed to retrieve PALD data: {e}")

    def store_feedback_record(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        feedback_text: str,
        round_number: int,
        image_id: UUID | None = None,
        feedback_pald: dict[str, Any] | None = None,
    ) -> FeedbackRecord:
        """
        Store a feedback record in the database.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            feedback_text: User feedback text
            round_number: Feedback round number
            image_id: Optional associated image ID
            feedback_pald: Optional PALD data extracted from feedback
            
        Returns:
            FeedbackRecord: Stored feedback record
            
        Raises:
            DatabaseError: If storage fails
            ValidationError: If input validation fails
        """
        try:
            if not feedback_text.strip():
                raise ValidationError("Feedback text cannot be empty")
            
            if round_number < 1:
                raise ValidationError("Round number must be positive")
            
            feedback = FeedbackRecord(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                image_id=image_id,
                feedback_text=feedback_text,
                feedback_pald=feedback_pald,
                round_number=round_number,
            )
            
            self.db_session.add(feedback)
            self.db_session.commit()
            
            logger.info(f"Stored feedback record {feedback.feedback_id} for pseudonym {pseudonym_id}")
            return feedback
            
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to store feedback record: {e}")
            raise DatabaseError(f"Failed to store feedback record: {e}")

    def get_feedback_records(
        self,
        pseudonym_id: UUID,
        session_id: UUID | None = None,
        limit: int = 50,
    ) -> list[FeedbackRecord]:
        """
        Retrieve feedback records for a participant.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Optional session ID to filter by
            limit: Maximum number of records to retrieve
            
        Returns:
            list[FeedbackRecord]: List of feedback records
        """
        try:
            query = self.db_session.query(FeedbackRecord).filter(
                FeedbackRecord.pseudonym_id == pseudonym_id
            )
            
            if session_id:
                query = query.filter(FeedbackRecord.session_id == session_id)
            
            return (
                query.order_by(FeedbackRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve feedback records: {e}")
            raise DatabaseError(f"Failed to retrieve feedback records: {e}")

    def log_interaction_metadata(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
        interaction_type: str,
        model_used: str,
        parameters: dict[str, Any],
        latency_ms: int,
        prompt: str | None = None,
        response: str | None = None,
        token_usage: dict[str, int] | None = None,
    ) -> InteractionLog:
        """
        Log interaction metadata for audit and analysis.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            interaction_type: Type of interaction (e.g., "pald_extraction", "consistency_check")
            model_used: Name of the model used
            parameters: Model parameters used
            latency_ms: Processing latency in milliseconds
            prompt: Optional prompt text
            response: Optional response text
            token_usage: Optional token usage statistics
            
        Returns:
            InteractionLog: Stored interaction log
            
        Raises:
            DatabaseError: If storage fails
        """
        try:
            log_entry = InteractionLog(
                pseudonym_id=pseudonym_id,
                session_id=session_id,
                interaction_type=interaction_type,
                prompt=prompt,
                response=response,
                model_used=model_used,
                parameters=parameters,
                token_usage=token_usage,
                latency_ms=latency_ms,
            )
            
            self.db_session.add(log_entry)
            self.db_session.commit()
            
            logger.debug(f"Logged interaction {log_entry.log_id} for pseudonym {pseudonym_id}")
            return log_entry
            
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to log interaction metadata: {e}")
            raise DatabaseError(f"Failed to log interaction metadata: {e}")

    def get_session_statistics(
        self,
        pseudonym_id: UUID,
        session_id: UUID,
    ) -> dict[str, Any]:
        """
        Get statistics for a chat session.
        
        Args:
            pseudonym_id: Participant's pseudonym ID
            session_id: Chat session ID
            
        Returns:
            dict: Session statistics including message counts, PALD extractions, etc.
        """
        try:
            # Count messages by type
            message_counts = {}
            for msg_type in ChatMessageType:
                count = (
                    self.db_session.query(ChatMessage)
                    .filter(
                        ChatMessage.pseudonym_id == pseudonym_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.message_type == msg_type.value,
                    )
                    .count()
                )
                message_counts[msg_type.value] = count
            
            # Count PALD extractions by type
            pald_counts = {}
            for pald_type in StudyPALDType:
                count = (
                    self.db_session.query(StudyPALDData)
                    .filter(
                        StudyPALDData.pseudonym_id == pseudonym_id,
                        StudyPALDData.session_id == session_id,
                        StudyPALDData.pald_type == pald_type.value,
                    )
                    .count()
                )
                pald_counts[pald_type.value] = count
            
            # Count feedback rounds
            feedback_count = (
                self.db_session.query(FeedbackRecord)
                .filter(
                    FeedbackRecord.pseudonym_id == pseudonym_id,
                    FeedbackRecord.session_id == session_id,
                )
                .count()
            )
            
            # Count interactions
            interaction_count = (
                self.db_session.query(InteractionLog)
                .filter(
                    InteractionLog.pseudonym_id == pseudonym_id,
                    InteractionLog.session_id == session_id,
                )
                .count()
            )
            
            return {
                "message_counts": message_counts,
                "pald_counts": pald_counts,
                "feedback_count": feedback_count,
                "interaction_count": interaction_count,
                "total_messages": sum(message_counts.values()),
                "total_pald_extractions": sum(pald_counts.values()),
            }
            
        except Exception as e:
            logger.error(f"Failed to get session statistics: {e}")
            raise DatabaseError(f"Failed to get session statistics: {e}")