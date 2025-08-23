"""
Data privacy service for GITTE study participation system.
Provides service layer abstraction for data privacy operations.
"""

import logging
from datetime import datetime
from uuid import UUID

from src.data.database import get_session
from src.data.repositories import (
    PseudonymRepository,
    PseudonymMappingRepository,
    StudyConsentRepository,
    StudySurveyResponseRepository,
    ChatMessageRepository,
    StudyPALDDataRepository,
    GeneratedImageRepository,
    FeedbackRecordRepository,
    InteractionLogRepository,
)
from src.data.schemas import (
    DataDeletionRequest,
    DataDeletionResult,
    DataExportRequest,
    DataExportResult,
    PseudonymizationValidationResult,
    DataCleanupResult,
)
from src.logic.data_privacy_logic import (
    DataPrivacyLogic,
    DataPrivacyError,
    DataDeletionError,
    DataExportError,
    PseudonymizationValidationError,
)

logger = logging.getLogger(__name__)


class DataPrivacyService:
    """
    Service layer for data privacy operations.
    Handles database sessions and provides high-level data privacy operations.
    """

    def __init__(self):
        self.data_privacy_logic = None  # Will be initialized per request

    def _get_data_privacy_logic(self) -> DataPrivacyLogic:
        """Get data privacy logic with database session."""
        if not hasattr(self, "_session") or not self._session:
            raise RuntimeError("Service not properly initialized with session")

        if not self.data_privacy_logic:
            # Initialize all repositories
            pseudonym_repository = PseudonymRepository(self._session)
            pseudonym_mapping_repository = PseudonymMappingRepository(self._session)
            consent_repository = StudyConsentRepository(self._session)
            survey_repository = StudySurveyResponseRepository(self._session)
            chat_repository = ChatMessageRepository(self._session)
            pald_repository = StudyPALDDataRepository(self._session)
            image_repository = GeneratedImageRepository(self._session)
            feedback_repository = FeedbackRecordRepository(self._session)
            interaction_repository = InteractionLogRepository(self._session)

            self.data_privacy_logic = DataPrivacyLogic(
                pseudonym_repository=pseudonym_repository,
                pseudonym_mapping_repository=pseudonym_mapping_repository,
                consent_repository=consent_repository,
                survey_repository=survey_repository,
                chat_repository=chat_repository,
                pald_repository=pald_repository,
                image_repository=image_repository,
                feedback_repository=feedback_repository,
                interaction_repository=interaction_repository,
            )

        return self.data_privacy_logic

    def delete_participant_data(self, request: DataDeletionRequest) -> DataDeletionResult:
        """
        Delete all data associated with a participant's pseudonym.
        
        Args:
            request: Data deletion request
            
        Returns:
            DataDeletionResult: Result of the deletion operation
            
        Raises:
            DataDeletionError: If deletion fails
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_data_privacy_logic()
                result = logic.delete_participant_data(request)
                session.commit()
                return result
            except Exception:
                session.rollback()
                raise
            finally:
                self._session = None
                self.data_privacy_logic = None

    def export_participant_data(self, request: DataExportRequest) -> DataExportResult:
        """
        Export all data associated with a participant's pseudonym.
        
        Args:
            request: Data export request
            
        Returns:
            DataExportResult: Result containing pseudonymized data export
            
        Raises:
            DataExportError: If export fails
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_data_privacy_logic()
                return logic.export_participant_data(request)
            finally:
                self._session = None
                self.data_privacy_logic = None

    def validate_pseudonymization(self, data: dict) -> PseudonymizationValidationResult:
        """
        Validate that data contains only pseudonymized identifiers.
        
        Args:
            data: Data to validate for pseudonymization compliance
            
        Returns:
            PseudonymizationValidationResult: Validation result
            
        Raises:
            PseudonymizationValidationError: If validation fails
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_data_privacy_logic()
                return logic.validate_pseudonymization(data)
            finally:
                self._session = None
                self.data_privacy_logic = None

    def cleanup_expired_data(self, retention_days: int) -> DataCleanupResult:
        """
        Clean up data based on retention policies.
        
        Args:
            retention_days: Number of days to retain data
            
        Returns:
            DataCleanupResult: Result of the cleanup operation
            
        Raises:
            DataPrivacyError: If cleanup fails
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_data_privacy_logic()
                cleanup_summary = logic.cleanup_expired_data(retention_days)
                session.commit()
                
                total_deleted = sum(cleanup_summary.values())
                
                return DataCleanupResult(
                    success=True,
                    cleanup_summary=cleanup_summary,
                    total_records_deleted=total_deleted,
                    cleanup_timestamp=datetime.utcnow(),
                    retention_policy=f"{retention_days}_days",
                    message=f"Successfully cleaned up {total_deleted} expired records"
                )
            except Exception as e:
                session.rollback()
                logger.error(f"Data cleanup failed: {e}")
                return DataCleanupResult(
                    success=False,
                    cleanup_summary={},
                    total_records_deleted=0,
                    cleanup_timestamp=datetime.utcnow(),
                    retention_policy=f"{retention_days}_days",
                    message="Data cleanup failed",
                    error_message=str(e)
                )
            finally:
                self._session = None
                self.data_privacy_logic = None

    def verify_data_privacy_compliance(self, pseudonym_id: UUID) -> dict:
        """
        Verify that all data for a pseudonym is properly pseudonymized.
        
        Args:
            pseudonym_id: The pseudonym ID to verify
            
        Returns:
            dict: Compliance verification result
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_data_privacy_logic()
                
                # Export data to validate pseudonymization
                export_request = DataExportRequest(
                    pseudonym_id=pseudonym_id,
                    format="json",
                    include_metadata=True,
                    requested_by="system_compliance_check"
                )
                
                export_result = logic.export_participant_data(export_request)
                if not export_result.success:
                    return {
                        "compliant": False,
                        "error": "Failed to export data for compliance check",
                        "details": export_result.error_message
                    }
                
                # Validate pseudonymization
                validation_result = logic.validate_pseudonymization(export_result.export_data)
                
                return {
                    "compliant": validation_result.is_valid,
                    "violations": validation_result.violations,
                    "data_summary": validation_result.data_summary,
                    "validation_timestamp": validation_result.validation_timestamp.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Privacy compliance verification failed: {e}")
                return {
                    "compliant": False,
                    "error": "Compliance verification failed",
                    "details": str(e)
                }
            finally:
                self._session = None
                self.data_privacy_logic = None

    def get_participant_data_summary(self, pseudonym_id: UUID) -> dict:
        """
        Get a summary of all data associated with a participant.
        
        Args:
            pseudonym_id: The pseudonym ID
            
        Returns:
            dict: Data summary
        """
        with get_session() as session:
            self._session = session
            try:
                logic = self._get_data_privacy_logic()
                
                # Get repositories
                pseudonym_repo = PseudonymRepository(session)
                consent_repo = StudyConsentRepository(session)
                survey_repo = StudySurveyResponseRepository(session)
                chat_repo = ChatMessageRepository(session)
                pald_repo = StudyPALDDataRepository(session)
                image_repo = GeneratedImageRepository(session)
                feedback_repo = FeedbackRecordRepository(session)
                interaction_repo = InteractionLogRepository(session)
                
                # Get pseudonym info
                pseudonym = pseudonym_repo.get_by_id(pseudonym_id)
                if not pseudonym:
                    return {"error": "Pseudonym not found"}
                
                # Count records by type
                summary = {
                    "pseudonym_id": str(pseudonym_id),
                    "pseudonym_text": pseudonym.pseudonym_text,
                    "created_at": pseudonym.created_at.isoformat(),
                    "is_active": pseudonym.is_active,
                    "record_counts": {
                        "consents": len(consent_repo.get_by_pseudonym(pseudonym_id)),
                        "survey_responses": len(survey_repo.get_by_pseudonym(pseudonym_id)),
                        "chat_messages": len(chat_repo.get_by_pseudonym(pseudonym_id)),
                        "pald_data": len(pald_repo.get_by_pseudonym(pseudonym_id)),
                        "generated_images": len(image_repo.get_by_pseudonym(pseudonym_id)),
                        "feedback_records": len(feedback_repo.get_by_pseudonym(pseudonym_id)),
                        "interaction_logs": len(interaction_repo.get_by_pseudonym(pseudonym_id)),
                    }
                }
                
                summary["total_records"] = sum(summary["record_counts"].values())
                
                return summary
                
            except Exception as e:
                logger.error(f"Failed to get participant data summary: {e}")
                return {"error": str(e)}
            finally:
                self._session = None
                self.data_privacy_logic = None