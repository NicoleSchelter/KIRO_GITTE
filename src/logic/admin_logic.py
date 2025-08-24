"""
Admin logic for database management and study operations.
Provides database initialization, reset, and data export functionality.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.data.database import get_session
from src.data.models import (
    Base,
    ChatMessage,
    FeedbackRecord,
    GeneratedImage,
    InteractionLog,
    Pseudonym,
    PseudonymMapping,
    StudyConsentRecord,
    StudyPALDData,
    StudySurveyResponse,
)

logger = logging.getLogger(__name__)


@dataclass
class InitializationResult:
    """Result of database initialization operation."""

    success: bool
    tables_created: list[str]
    errors: list[str]
    timestamp: datetime


@dataclass
class ResetResult:
    """Result of database reset operation."""

    success: bool
    tables_dropped: list[str]
    tables_recreated: list[str]
    errors: list[str]
    timestamp: datetime


@dataclass
class ValidationResult:
    """Result of database integrity validation."""

    success: bool
    constraint_violations: list[str]
    missing_tables: list[str]
    errors: list[str]
    timestamp: datetime


@dataclass
class ExportResult:
    """Result of study data export operation."""

    success: bool
    exported_records: dict[str, int]
    file_path: str | None
    errors: list[str]
    timestamp: datetime


class AdminLogic:
    """Admin logic for database management and study operations."""

    def __init__(self):
        """Initialize admin logic."""
        self.logger = logging.getLogger(__name__)

    def initialize_database_schema(self) -> InitializationResult:
        """
        Initialize all database tables exactly once.
        
        Returns:
            InitializationResult with operation details
        """
        timestamp = datetime.utcnow()
        tables_created = []
        errors = []

        try:
            from src.data.database_factory import _db_factory, create_all_tables
            
            # Ensure database factory is initialized
            _db_factory.initialize()

            # Get all table names from metadata
            all_tables = list(Base.metadata.tables.keys())
            
            # Check which tables already exist
            existing_tables = []
            with get_session() as session:
                for table_name in all_tables:
                    try:
                        # Try to query the table to see if it exists
                        session.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
                        existing_tables.append(table_name)
                    except Exception:
                        # Table doesn't exist, will be created
                        pass

            # Create all tables (this is idempotent - won't duplicate existing tables)
            create_all_tables()
            
            # Determine which tables were actually created
            tables_created = [table for table in all_tables if table not in existing_tables]
            
            if tables_created:
                self.logger.info(f"Created tables: {tables_created}")
            else:
                self.logger.info("All tables already exist, no new tables created")

            return InitializationResult(
                success=True,
                tables_created=tables_created,
                errors=errors,
                timestamp=timestamp,
            )

        except Exception as e:
            error_msg = f"Database initialization failed: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            return InitializationResult(
                success=False,
                tables_created=tables_created,
                errors=errors,
                timestamp=timestamp,
            )

    def reset_all_study_data(self) -> ResetResult:
        """
        Reset all study data by dropping and recreating all tables.
        This provides a clean slate for fresh experiments.
        
        Returns:
            ResetResult with operation details
        """
        timestamp = datetime.utcnow()
        tables_dropped = []
        tables_recreated = []
        errors = []

        try:
            from src.data.database_factory import _db_factory, create_all_tables
            
            # Ensure database factory is initialized
            _db_factory.initialize()
            
            # Get all table names before dropping
            all_tables = list(Base.metadata.tables.keys())
            
            # Drop all tables
            Base.metadata.drop_all(bind=_db_factory.engine)
            tables_dropped = all_tables.copy()
            self.logger.warning(f"Dropped all tables: {tables_dropped}")

            # Recreate all tables
            create_all_tables()
            tables_recreated = all_tables.copy()
            self.logger.info(f"Recreated all tables: {tables_recreated}")

            return ResetResult(
                success=True,
                tables_dropped=tables_dropped,
                tables_recreated=tables_recreated,
                errors=errors,
                timestamp=timestamp,
            )

        except Exception as e:
            error_msg = f"Database reset failed: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            return ResetResult(
                success=False,
                tables_dropped=tables_dropped,
                tables_recreated=tables_recreated,
                errors=errors,
                timestamp=timestamp,
            )

    def validate_database_integrity(self) -> ValidationResult:
        """
        Validate database integrity including foreign key constraints.
        
        Returns:
            ValidationResult with validation details
        """
        timestamp = datetime.utcnow()
        constraint_violations = []
        missing_tables = []
        errors = []

        try:
            # Check if all required tables exist
            expected_tables = list(Base.metadata.tables.keys())
            
            with get_session() as session:
                for table_name in expected_tables:
                    try:
                        session.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
                    except Exception as e:
                        missing_tables.append(table_name)
                        self.logger.warning(f"Table {table_name} is missing: {e}")

                # Check foreign key constraints for study participation tables
                if not missing_tables:
                    constraint_violations.extend(self._check_study_constraints(session))

            success = len(constraint_violations) == 0 and len(missing_tables) == 0

            return ValidationResult(
                success=success,
                constraint_violations=constraint_violations,
                missing_tables=missing_tables,
                errors=errors,
                timestamp=timestamp,
            )

        except Exception as e:
            error_msg = f"Database validation failed: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            return ValidationResult(
                success=False,
                constraint_violations=constraint_violations,
                missing_tables=missing_tables,
                errors=errors,
                timestamp=timestamp,
            )

    def _check_study_constraints(self, session) -> list[str]:
        """Check study participation foreign key constraints."""
        violations = []

        try:
            # Check for orphaned consent records
            orphaned_consents = session.execute("""
                SELECT COUNT(*) FROM study_consent_records scr
                LEFT JOIN pseudonyms p ON scr.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
            """).scalar()
            
            if orphaned_consents > 0:
                violations.append(f"Found {orphaned_consents} orphaned consent records")

            # Check for orphaned survey responses
            orphaned_surveys = session.execute("""
                SELECT COUNT(*) FROM study_survey_responses ssr
                LEFT JOIN pseudonyms p ON ssr.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
            """).scalar()
            
            if orphaned_surveys > 0:
                violations.append(f"Found {orphaned_surveys} orphaned survey responses")

            # Check for orphaned chat messages
            orphaned_chats = session.execute("""
                SELECT COUNT(*) FROM chat_messages cm
                LEFT JOIN pseudonyms p ON cm.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
            """).scalar()
            
            if orphaned_chats > 0:
                violations.append(f"Found {orphaned_chats} orphaned chat messages")

            # Check for orphaned PALD data
            orphaned_palds = session.execute("""
                SELECT COUNT(*) FROM study_pald_data spd
                LEFT JOIN pseudonyms p ON spd.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
            """).scalar()
            
            if orphaned_palds > 0:
                violations.append(f"Found {orphaned_palds} orphaned PALD records")

        except Exception as e:
            violations.append(f"Constraint check failed: {str(e)}")

        return violations

    def export_study_data(self, pseudonym_id: UUID | None = None) -> ExportResult:
        """
        Export study data with proper pseudonymization.
        
        Args:
            pseudonym_id: Optional specific pseudonym to export, None for all data
            
        Returns:
            ExportResult with export details
        """
        timestamp = datetime.utcnow()
        exported_records = {}
        errors = []
        file_path = None

        try:
            with get_session() as session:
                # Export pseudonyms (without mapping to user_id for privacy)
                pseudonym_query = session.query(Pseudonym)
                if pseudonym_id:
                    pseudonym_query = pseudonym_query.filter(Pseudonym.pseudonym_id == pseudonym_id)
                
                pseudonyms = pseudonym_query.all()
                exported_records["pseudonyms"] = len(pseudonyms)

                # Export consent records
                consent_query = session.query(StudyConsentRecord)
                if pseudonym_id:
                    consent_query = consent_query.filter(StudyConsentRecord.pseudonym_id == pseudonym_id)
                
                consents = consent_query.all()
                exported_records["consent_records"] = len(consents)

                # Export survey responses
                survey_query = session.query(StudySurveyResponse)
                if pseudonym_id:
                    survey_query = survey_query.filter(StudySurveyResponse.pseudonym_id == pseudonym_id)
                
                surveys = survey_query.all()
                exported_records["survey_responses"] = len(surveys)

                # Export chat messages
                chat_query = session.query(ChatMessage)
                if pseudonym_id:
                    chat_query = chat_query.filter(ChatMessage.pseudonym_id == pseudonym_id)
                
                chats = chat_query.all()
                exported_records["chat_messages"] = len(chats)

                # Export PALD data
                pald_query = session.query(StudyPALDData)
                if pseudonym_id:
                    pald_query = pald_query.filter(StudyPALDData.pseudonym_id == pseudonym_id)
                
                palds = pald_query.all()
                exported_records["pald_data"] = len(palds)

                # Export generated images
                image_query = session.query(GeneratedImage)
                if pseudonym_id:
                    image_query = image_query.filter(GeneratedImage.pseudonym_id == pseudonym_id)
                
                images = image_query.all()
                exported_records["generated_images"] = len(images)

                # Export feedback records
                feedback_query = session.query(FeedbackRecord)
                if pseudonym_id:
                    feedback_query = feedback_query.filter(FeedbackRecord.pseudonym_id == pseudonym_id)
                
                feedbacks = feedback_query.all()
                exported_records["feedback_records"] = len(feedbacks)

                # Export interaction logs
                log_query = session.query(InteractionLog)
                if pseudonym_id:
                    log_query = log_query.filter(InteractionLog.pseudonym_id == pseudonym_id)
                
                logs = log_query.all()
                exported_records["interaction_logs"] = len(logs)

                # Note: We do NOT export PseudonymMapping for privacy reasons
                # This table should only be accessible to authorized admin functions

                total_records = sum(exported_records.values())
                self.logger.info(f"Exported {total_records} total records")

            return ExportResult(
                success=True,
                exported_records=exported_records,
                file_path=file_path,  # Could be implemented to write to file
                errors=errors,
                timestamp=timestamp,
            )

        except Exception as e:
            error_msg = f"Data export failed: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            return ExportResult(
                success=False,
                exported_records=exported_records,
                file_path=file_path,
                errors=errors,
                timestamp=timestamp,
            )

    def delete_participant_data(self, pseudonym_id: UUID) -> bool:
        """
        Delete all data associated with a pseudonym (for participant rights).
        
        Args:
            pseudonym_id: The pseudonym ID to delete data for
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            with get_session() as session:
                # Delete in reverse dependency order to avoid foreign key violations
                
                # Delete interaction logs
                session.query(InteractionLog).filter(
                    InteractionLog.pseudonym_id == pseudonym_id
                ).delete()
                
                # Delete feedback records
                session.query(FeedbackRecord).filter(
                    FeedbackRecord.pseudonym_id == pseudonym_id
                ).delete()
                
                # Delete generated images
                session.query(GeneratedImage).filter(
                    GeneratedImage.pseudonym_id == pseudonym_id
                ).delete()
                
                # Delete PALD data
                session.query(StudyPALDData).filter(
                    StudyPALDData.pseudonym_id == pseudonym_id
                ).delete()
                
                # Delete chat messages
                session.query(ChatMessage).filter(
                    ChatMessage.pseudonym_id == pseudonym_id
                ).delete()
                
                # Delete survey responses
                session.query(StudySurveyResponse).filter(
                    StudySurveyResponse.pseudonym_id == pseudonym_id
                ).delete()
                
                # Delete consent records
                session.query(StudyConsentRecord).filter(
                    StudyConsentRecord.pseudonym_id == pseudonym_id
                ).delete()
                
                # Delete pseudonym mapping (if exists)
                session.query(PseudonymMapping).filter(
                    PseudonymMapping.pseudonym_id == pseudonym_id
                ).delete()
                
                # Finally delete the pseudonym itself
                session.query(Pseudonym).filter(
                    Pseudonym.pseudonym_id == pseudonym_id
                ).delete()
                
                # Commit is handled by the session context manager
                self.logger.info(f"Successfully deleted all data for pseudonym {pseudonym_id}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to delete participant data for {pseudonym_id}: {e}")
            return False

    def get_database_statistics(self) -> dict[str, Any]:
        """
        Get database statistics for monitoring and reporting.
        
        Returns:
            Dictionary with table counts and other statistics
        """
        stats = {}
        
        try:
            with get_session() as session:
                # Count records in each table
                stats["pseudonyms"] = session.query(Pseudonym).count()
                stats["consent_records"] = session.query(StudyConsentRecord).count()
                stats["survey_responses"] = session.query(StudySurveyResponse).count()
                stats["chat_messages"] = session.query(ChatMessage).count()
                stats["pald_data"] = session.query(StudyPALDData).count()
                stats["generated_images"] = session.query(GeneratedImage).count()
                stats["feedback_records"] = session.query(FeedbackRecord).count()
                stats["interaction_logs"] = session.query(InteractionLog).count()
                
                # Additional statistics
                stats["active_pseudonyms"] = session.query(Pseudonym).filter(
                    Pseudonym.is_active == True
                ).count()
                
                stats["total_study_records"] = sum([
                    stats["consent_records"],
                    stats["survey_responses"], 
                    stats["chat_messages"],
                    stats["pald_data"],
                    stats["generated_images"],
                    stats["feedback_records"],
                    stats["interaction_logs"]
                ])

        except Exception as e:
            self.logger.error(f"Failed to get database statistics: {e}")
            stats["error"] = str(e)

        return stats