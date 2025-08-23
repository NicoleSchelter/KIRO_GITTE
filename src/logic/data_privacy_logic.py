"""
Data privacy logic for GITTE study participation system.
Handles participant data deletion, pseudonymization validation, and data export.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

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
)

logger = logging.getLogger(__name__)


class DataPrivacyError(Exception):
    """Base exception for data privacy operations."""
    pass


class DataDeletionError(DataPrivacyError):
    """Exception raised when data deletion fails."""
    pass


class DataExportError(DataPrivacyError):
    """Exception raised when data export fails."""
    pass


class PseudonymizationValidationError(DataPrivacyError):
    """Exception raised when pseudonymization validation fails."""
    pass


class DataPrivacyLogic:
    """
    Logic layer for data privacy operations.
    Handles participant data deletion, pseudonymization validation, and data export.
    """

    def __init__(
        self,
        pseudonym_repository: PseudonymRepository,
        pseudonym_mapping_repository: PseudonymMappingRepository,
        consent_repository: StudyConsentRepository,
        survey_repository: StudySurveyResponseRepository,
        chat_repository: ChatMessageRepository,
        pald_repository: StudyPALDDataRepository,
        image_repository: GeneratedImageRepository,
        feedback_repository: FeedbackRecordRepository,
        interaction_repository: InteractionLogRepository,
    ):
        self.pseudonym_repository = pseudonym_repository
        self.pseudonym_mapping_repository = pseudonym_mapping_repository
        self.consent_repository = consent_repository
        self.survey_repository = survey_repository
        self.chat_repository = chat_repository
        self.pald_repository = pald_repository
        self.image_repository = image_repository
        self.feedback_repository = feedback_repository
        self.interaction_repository = interaction_repository

    def delete_participant_data(self, request: DataDeletionRequest) -> DataDeletionResult:
        """
        Delete all data associated with a participant's pseudonym.
        
        Args:
            request: Data deletion request containing pseudonym_id or user_id
            
        Returns:
            DataDeletionResult: Result of the deletion operation
            
        Raises:
            DataDeletionError: If deletion fails
        """
        try:
            logger.info(f"Starting data deletion for request: {request}")
            
            # Get pseudonym_id from request
            pseudonym_id = self._resolve_pseudonym_id(request)
            if not pseudonym_id:
                raise DataDeletionError("Could not resolve pseudonym_id for deletion request")
            
            # Verify pseudonym exists
            pseudonym = self.pseudonym_repository.get_by_id(pseudonym_id)
            if not pseudonym:
                raise DataDeletionError(f"Pseudonym {pseudonym_id} not found")
            
            deletion_summary = {
                "pseudonym_id": str(pseudonym_id),
                "pseudonym_text": pseudonym.pseudonym_text,
                "deletion_timestamp": datetime.utcnow().isoformat(),
                "deleted_records": {}
            }
            
            # Delete data in reverse dependency order to avoid foreign key violations
            
            # 1. Delete interaction logs
            interaction_count = self.interaction_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["interaction_logs"] = interaction_count
            logger.info(f"Deleted {interaction_count} interaction logs")
            
            # 2. Delete feedback records
            feedback_count = self.feedback_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["feedback_records"] = feedback_count
            logger.info(f"Deleted {feedback_count} feedback records")
            
            # 3. Delete generated images
            image_count = self.image_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["generated_images"] = image_count
            logger.info(f"Deleted {image_count} generated images")
            
            # 4. Delete PALD data
            pald_count = self.pald_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["pald_data"] = pald_count
            logger.info(f"Deleted {pald_count} PALD records")
            
            # 5. Delete chat messages
            chat_count = self.chat_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["chat_messages"] = chat_count
            logger.info(f"Deleted {chat_count} chat messages")
            
            # 6. Delete survey responses
            survey_count = self.survey_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["survey_responses"] = survey_count
            logger.info(f"Deleted {survey_count} survey responses")
            
            # 7. Delete consent records
            consent_count = self.consent_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["consent_records"] = consent_count
            logger.info(f"Deleted {consent_count} consent records")
            
            # 8. Delete pseudonym mapping (if exists)
            mapping_deleted = self.pseudonym_mapping_repository.delete_by_pseudonym(pseudonym_id)
            deletion_summary["deleted_records"]["pseudonym_mapping"] = 1 if mapping_deleted else 0
            logger.info(f"Deleted pseudonym mapping: {mapping_deleted}")
            
            # 9. Finally, delete the pseudonym itself
            pseudonym_deleted = self.pseudonym_repository.delete(pseudonym_id)
            deletion_summary["deleted_records"]["pseudonym"] = 1 if pseudonym_deleted else 0
            logger.info(f"Deleted pseudonym: {pseudonym_deleted}")
            
            total_deleted = sum(deletion_summary["deleted_records"].values())
            
            return DataDeletionResult(
                success=True,
                pseudonym_id=pseudonym_id,
                deletion_summary=deletion_summary,
                total_records_deleted=total_deleted,
                deletion_timestamp=datetime.utcnow(),
                message=f"Successfully deleted {total_deleted} records for pseudonym {pseudonym.pseudonym_text}"
            )
            
        except Exception as e:
            logger.error(f"Data deletion failed: {e}")
            raise DataDeletionError(f"Data deletion failed: {str(e)}")

    def export_participant_data(self, request: DataExportRequest) -> DataExportResult:
        """
        Export all data associated with a participant's pseudonym.
        
        Args:
            request: Data export request containing pseudonym_id or user_id
            
        Returns:
            DataExportResult: Result containing pseudonymized data export
            
        Raises:
            DataExportError: If export fails
        """
        try:
            logger.info(f"Starting data export for request: {request}")
            
            # Get pseudonym_id from request
            pseudonym_id = self._resolve_pseudonym_id(request)
            if not pseudonym_id:
                raise DataExportError("Could not resolve pseudonym_id for export request")
            
            # Verify pseudonym exists
            pseudonym = self.pseudonym_repository.get_by_id(pseudonym_id)
            if not pseudonym:
                raise DataExportError(f"Pseudonym {pseudonym_id} not found")
            
            export_data = {
                "export_metadata": {
                    "pseudonym_id": str(pseudonym_id),
                    "pseudonym_text": pseudonym.pseudonym_text,
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "export_format": request.format,
                    "include_metadata": request.include_metadata
                },
                "participant_data": {}
            }
            
            # Export pseudonym information (without user_id mapping)
            export_data["participant_data"]["pseudonym"] = {
                "pseudonym_id": str(pseudonym.pseudonym_id),
                "pseudonym_text": pseudonym.pseudonym_text,
                "pseudonym_hash": pseudonym.pseudonym_hash,
                "created_at": pseudonym.created_at.isoformat(),
                "is_active": pseudonym.is_active
            }
            
            # Export consent records
            consents = self.consent_repository.get_by_pseudonym(pseudonym_id)
            export_data["participant_data"]["consents"] = [
                self._pseudonymize_consent_record(consent) for consent in consents
            ]
            
            # Export survey responses
            surveys = self.survey_repository.get_by_pseudonym(pseudonym_id)
            export_data["participant_data"]["survey_responses"] = [
                self._pseudonymize_survey_response(survey) for survey in surveys
            ]
            
            # Export chat messages
            chats = self.chat_repository.get_by_pseudonym(pseudonym_id)
            export_data["participant_data"]["chat_messages"] = [
                self._pseudonymize_chat_message(chat) for chat in chats
            ]
            
            # Export PALD data
            palds = self.pald_repository.get_by_pseudonym(pseudonym_id)
            export_data["participant_data"]["pald_data"] = [
                self._pseudonymize_pald_data(pald) for pald in palds
            ]
            
            # Export generated images
            images = self.image_repository.get_by_pseudonym(pseudonym_id)
            export_data["participant_data"]["generated_images"] = [
                self._pseudonymize_generated_image(image) for image in images
            ]
            
            # Export feedback records
            feedbacks = self.feedback_repository.get_by_pseudonym(pseudonym_id)
            export_data["participant_data"]["feedback_records"] = [
                self._pseudonymize_feedback_record(feedback) for feedback in feedbacks
            ]
            
            # Export interaction logs (if requested)
            if request.include_metadata:
                interactions = self.interaction_repository.get_by_pseudonym(pseudonym_id)
                export_data["participant_data"]["interaction_logs"] = [
                    self._pseudonymize_interaction_log(interaction) for interaction in interactions
                ]
            
            # Validate pseudonymization
            validation_result = self._validate_export_pseudonymization(export_data)
            if not validation_result.is_valid:
                raise DataExportError(f"Export failed pseudonymization validation: {validation_result.violations}")
            
            return DataExportResult(
                success=True,
                pseudonym_id=pseudonym_id,
                export_data=export_data,
                export_timestamp=datetime.utcnow(),
                record_counts={
                    "consents": len(export_data["participant_data"]["consents"]),
                    "survey_responses": len(export_data["participant_data"]["survey_responses"]),
                    "chat_messages": len(export_data["participant_data"]["chat_messages"]),
                    "pald_data": len(export_data["participant_data"]["pald_data"]),
                    "generated_images": len(export_data["participant_data"]["generated_images"]),
                    "feedback_records": len(export_data["participant_data"]["feedback_records"]),
                    "interaction_logs": len(export_data["participant_data"].get("interaction_logs", []))
                },
                message=f"Successfully exported data for pseudonym {pseudonym.pseudonym_text}"
            )
            
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            raise DataExportError(f"Data export failed: {str(e)}")

    def validate_pseudonymization(self, data: Dict[str, Any]) -> PseudonymizationValidationResult:
        """
        Validate that data contains only pseudonymized identifiers and no user_id exposure.
        
        Args:
            data: Data to validate for pseudonymization compliance
            
        Returns:
            PseudonymizationValidationResult: Validation result
        """
        try:
            violations = []
            
            # Check for user_id exposure in the data
            violations.extend(self._check_user_id_exposure(data, ""))
            
            # Check for other PII exposure
            violations.extend(self._check_pii_exposure(data, ""))
            
            # Check that all identifiers are pseudonym-based
            violations.extend(self._check_identifier_compliance(data, ""))
            
            is_valid = len(violations) == 0
            
            return PseudonymizationValidationResult(
                is_valid=is_valid,
                violations=violations,
                validation_timestamp=datetime.utcnow(),
                data_summary=self._generate_data_summary(data)
            )
            
        except Exception as e:
            logger.error(f"Pseudonymization validation failed: {e}")
            raise PseudonymizationValidationError(f"Validation failed: {str(e)}")

    def cleanup_expired_data(self, retention_days: int) -> Dict[str, int]:
        """
        Clean up data based on retention policies.
        
        Args:
            retention_days: Number of days to retain data
            
        Returns:
            Dict[str, int]: Count of records deleted by type
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            logger.info(f"Starting data cleanup for data older than {cutoff_date}")
            
            cleanup_summary = {}
            
            # Clean up interaction logs
            interaction_count = self.interaction_repository.delete_older_than(cutoff_date)
            cleanup_summary["interaction_logs"] = interaction_count
            
            # Clean up feedback records
            feedback_count = self.feedback_repository.delete_older_than(cutoff_date)
            cleanup_summary["feedback_records"] = feedback_count
            
            # Clean up generated images
            image_count = self.image_repository.delete_older_than(cutoff_date)
            cleanup_summary["generated_images"] = image_count
            
            # Note: We don't automatically delete core study data (consents, surveys, PALDs)
            # as these may be needed for research purposes beyond the retention period
            
            total_cleaned = sum(cleanup_summary.values())
            logger.info(f"Data cleanup completed. Deleted {total_cleaned} records")
            
            return cleanup_summary
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            raise DataPrivacyError(f"Data cleanup failed: {str(e)}")

    def _resolve_pseudonym_id(self, request) -> Optional[UUID]:
        """Resolve pseudonym_id from request (either direct or via user_id mapping)."""
        if hasattr(request, 'pseudonym_id') and request.pseudonym_id:
            return request.pseudonym_id
        
        if hasattr(request, 'user_id') and request.user_id:
            mapping = self.pseudonym_mapping_repository.get_by_user_id(request.user_id)
            return mapping.pseudonym_id if mapping else None
        
        return None

    def _pseudonymize_consent_record(self, consent) -> Dict[str, Any]:
        """Convert consent record to pseudonymized format."""
        return {
            "consent_id": str(consent.consent_id),
            "pseudonym_id": str(consent.pseudonym_id),
            "consent_type": consent.consent_type,
            "granted": consent.granted,
            "version": consent.version,
            "granted_at": consent.granted_at.isoformat(),
            "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None
        }

    def _pseudonymize_survey_response(self, survey) -> Dict[str, Any]:
        """Convert survey response to pseudonymized format."""
        return {
            "response_id": str(survey.response_id),
            "pseudonym_id": str(survey.pseudonym_id),
            "survey_version": survey.survey_version,
            "responses": survey.responses,
            "completed_at": survey.completed_at.isoformat()
        }

    def _pseudonymize_chat_message(self, chat) -> Dict[str, Any]:
        """Convert chat message to pseudonymized format."""
        return {
            "message_id": str(chat.message_id),
            "pseudonym_id": str(chat.pseudonym_id),
            "session_id": str(chat.session_id),
            "message_type": chat.message_type,
            "content": chat.content,
            "pald_data": chat.pald_data,
            "timestamp": chat.timestamp.isoformat()
        }

    def _pseudonymize_pald_data(self, pald) -> Dict[str, Any]:
        """Convert PALD data to pseudonymized format."""
        return {
            "pald_id": str(pald.pald_id),
            "pseudonym_id": str(pald.pseudonym_id),
            "session_id": str(pald.session_id),
            "pald_content": pald.pald_content,
            "pald_type": pald.pald_type,
            "consistency_score": pald.consistency_score,
            "created_at": pald.created_at.isoformat()
        }

    def _pseudonymize_generated_image(self, image) -> Dict[str, Any]:
        """Convert generated image to pseudonymized format."""
        return {
            "image_id": str(image.image_id),
            "pseudonym_id": str(image.pseudonym_id),
            "session_id": str(image.session_id),
            "image_path": image.image_path,
            "prompt": image.prompt,
            "pald_source_id": str(image.pald_source_id) if image.pald_source_id else None,
            "generation_parameters": image.generation_parameters,
            "created_at": image.created_at.isoformat()
        }

    def _pseudonymize_feedback_record(self, feedback) -> Dict[str, Any]:
        """Convert feedback record to pseudonymized format."""
        return {
            "feedback_id": str(feedback.feedback_id),
            "pseudonym_id": str(feedback.pseudonym_id),
            "session_id": str(feedback.session_id),
            "image_id": str(feedback.image_id) if feedback.image_id else None,
            "feedback_text": feedback.feedback_text,
            "feedback_pald": feedback.feedback_pald,
            "round_number": feedback.round_number,
            "created_at": feedback.created_at.isoformat()
        }

    def _pseudonymize_interaction_log(self, interaction) -> Dict[str, Any]:
        """Convert interaction log to pseudonymized format."""
        return {
            "log_id": str(interaction.log_id),
            "pseudonym_id": str(interaction.pseudonym_id),
            "session_id": str(interaction.session_id),
            "interaction_type": interaction.interaction_type,
            "prompt": interaction.prompt,
            "response": interaction.response,
            "model_used": interaction.model_used,
            "parameters": interaction.parameters,
            "token_usage": interaction.token_usage,
            "latency_ms": interaction.latency_ms,
            "timestamp": interaction.timestamp.isoformat()
        }

    def _validate_export_pseudonymization(self, export_data: Dict[str, Any]) -> PseudonymizationValidationResult:
        """Validate that export data is properly pseudonymized."""
        return self.validate_pseudonymization(export_data)

    def _check_user_id_exposure(self, data: Any, path: str) -> List[str]:
        """Check for user_id exposure in data."""
        violations = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check for user_id fields
                if key.lower() in ['user_id', 'userid', 'user_identifier']:
                    violations.append(f"User ID exposure at {current_path}")
                
                # Recursively check nested data
                violations.extend(self._check_user_id_exposure(value, current_path))
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                violations.extend(self._check_user_id_exposure(item, current_path))
        
        return violations

    def _check_pii_exposure(self, data: Any, path: str) -> List[str]:
        """Check for PII exposure in data."""
        violations = []
        pii_fields = ['email', 'phone', 'address', 'name', 'username', 'real_name']
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check for PII fields
                if key.lower() in pii_fields:
                    violations.append(f"PII exposure ({key}) at {current_path}")
                
                # Recursively check nested data
                violations.extend(self._check_pii_exposure(value, current_path))
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                violations.extend(self._check_pii_exposure(item, current_path))
        
        return violations

    def _check_identifier_compliance(self, data: Any, path: str) -> List[str]:
        """Check that all identifiers are pseudonym-based."""
        violations = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check that pseudonym_id is used instead of user_id
                if key.endswith('_id') and key != 'pseudonym_id' and 'user' in key.lower():
                    violations.append(f"Non-pseudonymized identifier {key} at {current_path}")
                
                # Recursively check nested data
                violations.extend(self._check_identifier_compliance(value, current_path))
                
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]"
                violations.extend(self._check_identifier_compliance(item, current_path))
        
        return violations

    def _generate_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of data for validation result."""
        summary = {
            "total_records": 0,
            "record_types": {},
            "identifier_types": set(),
            "validation_timestamp": datetime.utcnow().isoformat()
        }
        
        if "participant_data" in data:
            for record_type, records in data["participant_data"].items():
                if isinstance(records, list):
                    count = len(records)
                    summary["record_types"][record_type] = count
                    summary["total_records"] += count
                    
                    # Check identifier types in first record
                    if records and isinstance(records[0], dict):
                        for key in records[0].keys():
                            if key.endswith('_id'):
                                summary["identifier_types"].add(key)
        
        summary["identifier_types"] = list(summary["identifier_types"])
        return summary