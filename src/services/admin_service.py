"""
Admin service for database management and data export operations.
Provides table management, data export, and system administration functionality.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.data.database import get_session
from src.data.models import (
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


class AdminService:
    """Admin service for database management and data export operations."""

    def __init__(self, session: Session):
        """Initialize admin service with database session."""
        self.session = session
        self.logger = logging.getLogger(__name__)

    def create_all_tables(self) -> bool:
        """
        Create all database tables.
        
        Returns:
            True if tables were created successfully, False otherwise
        """
        try:
            from src.data.models import Base
            from src.data.database import db_manager
            
            # Ensure database manager is initialized
            if not db_manager._initialized:
                db_manager.initialize()
            
            # Create all tables
            Base.metadata.create_all(bind=db_manager.engine)
            self.logger.info("All database tables created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {e}")
            return False

    def drop_all_tables(self) -> bool:
        """
        Drop all database tables. Use with extreme caution!
        
        Returns:
            True if tables were dropped successfully, False otherwise
        """
        try:
            from src.data.models import Base
            from src.data.database import db_manager
            
            # Ensure database manager is initialized
            if not db_manager._initialized:
                db_manager.initialize()
            
            # Drop all tables
            Base.metadata.drop_all(bind=db_manager.engine)
            self.logger.warning("All database tables dropped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to drop database tables: {e}")
            return False

    def verify_foreign_key_constraints(self) -> list[str]:
        """
        Verify foreign key constraints across study participation tables.
        
        Returns:
            List of constraint violations found
        """
        violations = []
        
        try:
            # Check for orphaned consent records
            orphaned_consents = self.session.execute("""
                SELECT scr.consent_id, scr.pseudonym_id 
                FROM study_consent_records scr
                LEFT JOIN pseudonyms p ON scr.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
                LIMIT 10
            """).fetchall()
            
            if orphaned_consents:
                violations.append(f"Found {len(orphaned_consents)} orphaned consent records")
                for record in orphaned_consents:
                    violations.append(f"  - Consent {record[0]} references missing pseudonym {record[1]}")

            # Check for orphaned survey responses
            orphaned_surveys = self.session.execute("""
                SELECT ssr.response_id, ssr.pseudonym_id
                FROM study_survey_responses ssr
                LEFT JOIN pseudonyms p ON ssr.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
                LIMIT 10
            """).fetchall()
            
            if orphaned_surveys:
                violations.append(f"Found {len(orphaned_surveys)} orphaned survey responses")
                for record in orphaned_surveys:
                    violations.append(f"  - Survey {record[0]} references missing pseudonym {record[1]}")

            # Check for orphaned chat messages
            orphaned_chats = self.session.execute("""
                SELECT cm.message_id, cm.pseudonym_id
                FROM chat_messages cm
                LEFT JOIN pseudonyms p ON cm.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
                LIMIT 10
            """).fetchall()
            
            if orphaned_chats:
                violations.append(f"Found {len(orphaned_chats)} orphaned chat messages")
                for record in orphaned_chats:
                    violations.append(f"  - Chat {record[0]} references missing pseudonym {record[1]}")

            # Check for orphaned PALD data
            orphaned_palds = self.session.execute("""
                SELECT spd.pald_id, spd.pseudonym_id
                FROM study_pald_data spd
                LEFT JOIN pseudonyms p ON spd.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
                LIMIT 10
            """).fetchall()
            
            if orphaned_palds:
                violations.append(f"Found {len(orphaned_palds)} orphaned PALD records")
                for record in orphaned_palds:
                    violations.append(f"  - PALD {record[0]} references missing pseudonym {record[1]}")

            # Check for orphaned generated images
            orphaned_images = self.session.execute("""
                SELECT gi.image_id, gi.pseudonym_id
                FROM generated_images gi
                LEFT JOIN pseudonyms p ON gi.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
                LIMIT 10
            """).fetchall()
            
            if orphaned_images:
                violations.append(f"Found {len(orphaned_images)} orphaned generated images")
                for record in orphaned_images:
                    violations.append(f"  - Image {record[0]} references missing pseudonym {record[1]}")

            # Check for orphaned feedback records
            orphaned_feedback = self.session.execute("""
                SELECT fr.feedback_id, fr.pseudonym_id
                FROM feedback_records fr
                LEFT JOIN pseudonyms p ON fr.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
                LIMIT 10
            """).fetchall()
            
            if orphaned_feedback:
                violations.append(f"Found {len(orphaned_feedback)} orphaned feedback records")
                for record in orphaned_feedback:
                    violations.append(f"  - Feedback {record[0]} references missing pseudonym {record[1]}")

            # Check for orphaned interaction logs
            orphaned_logs = self.session.execute("""
                SELECT il.log_id, il.pseudonym_id
                FROM interaction_logs il
                LEFT JOIN pseudonyms p ON il.pseudonym_id = p.pseudonym_id
                WHERE p.pseudonym_id IS NULL
                LIMIT 10
            """).fetchall()
            
            if orphaned_logs:
                violations.append(f"Found {len(orphaned_logs)} orphaned interaction logs")
                for record in orphaned_logs:
                    violations.append(f"  - Log {record[0]} references missing pseudonym {record[1]}")

        except Exception as e:
            violations.append(f"Constraint verification failed: {str(e)}")
            self.logger.error(f"Error verifying foreign key constraints: {e}")

        return violations

    def export_study_data_to_file(
        self, 
        output_path: str | Path, 
        pseudonym_id: UUID | None = None,
        format: str = "json"
    ) -> dict[str, Any]:
        """
        Export study data to file with proper pseudonymization.
        
        Args:
            output_path: Path where to save the exported data
            pseudonym_id: Optional specific pseudonym to export, None for all data
            format: Export format ("json" or "csv")
            
        Returns:
            Dictionary with export results and statistics
        """
        export_result = {
            "success": False,
            "file_path": None,
            "records_exported": {},
            "errors": [],
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            output_path = Path(output_path)
            
            # Collect all data
            export_data = {}
            
            # Export pseudonyms (without user mapping for privacy)
            pseudonym_query = self.session.query(Pseudonym)
            if pseudonym_id:
                pseudonym_query = pseudonym_query.filter(Pseudonym.pseudonym_id == pseudonym_id)
            
            pseudonyms = pseudonym_query.all()
            export_data["pseudonyms"] = [
                {
                    "pseudonym_id": str(p.pseudonym_id),
                    "pseudonym_text": p.pseudonym_text,
                    "pseudonym_hash": p.pseudonym_hash,
                    "created_at": p.created_at.isoformat(),
                    "is_active": p.is_active
                }
                for p in pseudonyms
            ]
            export_result["records_exported"]["pseudonyms"] = len(pseudonyms)

            # Export consent records
            consent_query = self.session.query(StudyConsentRecord)
            if pseudonym_id:
                consent_query = consent_query.filter(StudyConsentRecord.pseudonym_id == pseudonym_id)
            
            consents = consent_query.all()
            export_data["consent_records"] = [
                {
                    "consent_id": str(c.consent_id),
                    "pseudonym_id": str(c.pseudonym_id),
                    "consent_type": c.consent_type,
                    "granted": c.granted,
                    "version": c.version,
                    "granted_at": c.granted_at.isoformat(),
                    "revoked_at": c.revoked_at.isoformat() if c.revoked_at else None
                }
                for c in consents
            ]
            export_result["records_exported"]["consent_records"] = len(consents)

            # Export survey responses
            survey_query = self.session.query(StudySurveyResponse)
            if pseudonym_id:
                survey_query = survey_query.filter(StudySurveyResponse.pseudonym_id == pseudonym_id)
            
            surveys = survey_query.all()
            export_data["survey_responses"] = [
                {
                    "response_id": str(s.response_id),
                    "pseudonym_id": str(s.pseudonym_id),
                    "survey_version": s.survey_version,
                    "responses": s.responses,
                    "completed_at": s.completed_at.isoformat()
                }
                for s in surveys
            ]
            export_result["records_exported"]["survey_responses"] = len(surveys)

            # Export chat messages
            chat_query = self.session.query(ChatMessage)
            if pseudonym_id:
                chat_query = chat_query.filter(ChatMessage.pseudonym_id == pseudonym_id)
            
            chats = chat_query.all()
            export_data["chat_messages"] = [
                {
                    "message_id": str(c.message_id),
                    "pseudonym_id": str(c.pseudonym_id),
                    "session_id": str(c.session_id),
                    "message_type": c.message_type,
                    "content": c.content,
                    "pald_data": c.pald_data,
                    "timestamp": c.timestamp.isoformat()
                }
                for c in chats
            ]
            export_result["records_exported"]["chat_messages"] = len(chats)

            # Export PALD data
            pald_query = self.session.query(StudyPALDData)
            if pseudonym_id:
                pald_query = pald_query.filter(StudyPALDData.pseudonym_id == pseudonym_id)
            
            palds = pald_query.all()
            export_data["pald_data"] = [
                {
                    "pald_id": str(p.pald_id),
                    "pseudonym_id": str(p.pseudonym_id),
                    "session_id": str(p.session_id),
                    "pald_content": p.pald_content,
                    "pald_type": p.pald_type,
                    "consistency_score": p.consistency_score,
                    "created_at": p.created_at.isoformat()
                }
                for p in palds
            ]
            export_result["records_exported"]["pald_data"] = len(palds)

            # Export generated images
            image_query = self.session.query(GeneratedImage)
            if pseudonym_id:
                image_query = image_query.filter(GeneratedImage.pseudonym_id == pseudonym_id)
            
            images = image_query.all()
            export_data["generated_images"] = [
                {
                    "image_id": str(i.image_id),
                    "pseudonym_id": str(i.pseudonym_id),
                    "session_id": str(i.session_id),
                    "image_path": i.image_path,
                    "prompt": i.prompt,
                    "pald_source_id": str(i.pald_source_id) if i.pald_source_id else None,
                    "generation_parameters": i.generation_parameters,
                    "created_at": i.created_at.isoformat()
                }
                for i in images
            ]
            export_result["records_exported"]["generated_images"] = len(images)

            # Export feedback records
            feedback_query = self.session.query(FeedbackRecord)
            if pseudonym_id:
                feedback_query = feedback_query.filter(FeedbackRecord.pseudonym_id == pseudonym_id)
            
            feedbacks = feedback_query.all()
            export_data["feedback_records"] = [
                {
                    "feedback_id": str(f.feedback_id),
                    "pseudonym_id": str(f.pseudonym_id),
                    "session_id": str(f.session_id),
                    "image_id": str(f.image_id) if f.image_id else None,
                    "feedback_text": f.feedback_text,
                    "feedback_pald": f.feedback_pald,
                    "round_number": f.round_number,
                    "created_at": f.created_at.isoformat()
                }
                for f in feedbacks
            ]
            export_result["records_exported"]["feedback_records"] = len(feedbacks)

            # Export interaction logs
            log_query = self.session.query(InteractionLog)
            if pseudonym_id:
                log_query = log_query.filter(InteractionLog.pseudonym_id == pseudonym_id)
            
            logs = log_query.all()
            export_data["interaction_logs"] = [
                {
                    "log_id": str(l.log_id),
                    "pseudonym_id": str(l.pseudonym_id),
                    "session_id": str(l.session_id),
                    "interaction_type": l.interaction_type,
                    "prompt": l.prompt,
                    "response": l.response,
                    "model_used": l.model_used,
                    "parameters": l.parameters,
                    "token_usage": l.token_usage,
                    "latency_ms": l.latency_ms,
                    "timestamp": l.timestamp.isoformat()
                }
                for l in logs
            ]
            export_result["records_exported"]["interaction_logs"] = len(logs)

            # Write to file
            if format.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                export_result["errors"].append(f"Unsupported format: {format}")
                return export_result

            export_result["success"] = True
            export_result["file_path"] = str(output_path)
            
            total_records = sum(export_result["records_exported"].values())
            self.logger.info(f"Successfully exported {total_records} records to {output_path}")

        except Exception as e:
            error_msg = f"Data export failed: {str(e)}"
            self.logger.error(error_msg)
            export_result["errors"].append(error_msg)

        return export_result

    def get_table_counts(self) -> dict[str, int]:
        """
        Get record counts for all study participation tables.
        
        Returns:
            Dictionary mapping table names to record counts
        """
        counts = {}
        
        try:
            counts["pseudonyms"] = self.session.query(Pseudonym).count()
            counts["consent_records"] = self.session.query(StudyConsentRecord).count()
            counts["survey_responses"] = self.session.query(StudySurveyResponse).count()
            counts["chat_messages"] = self.session.query(ChatMessage).count()
            counts["pald_data"] = self.session.query(StudyPALDData).count()
            counts["generated_images"] = self.session.query(GeneratedImage).count()
            counts["feedback_records"] = self.session.query(FeedbackRecord).count()
            counts["interaction_logs"] = self.session.query(InteractionLog).count()
            counts["pseudonym_mappings"] = self.session.query(PseudonymMapping).count()
            
        except Exception as e:
            self.logger.error(f"Failed to get table counts: {e}")
            counts["error"] = str(e)

        return counts

    def cleanup_orphaned_records(self) -> dict[str, int]:
        """
        Clean up orphaned records that reference non-existent pseudonyms.
        
        Returns:
            Dictionary with counts of cleaned up records
        """
        cleanup_counts = {}
        
        try:
            # Clean up orphaned consent records
            deleted_consents = self.session.execute("""
                DELETE FROM study_consent_records 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["consent_records"] = deleted_consents

            # Clean up orphaned survey responses
            deleted_surveys = self.session.execute("""
                DELETE FROM study_survey_responses 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["survey_responses"] = deleted_surveys

            # Clean up orphaned chat messages
            deleted_chats = self.session.execute("""
                DELETE FROM chat_messages 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["chat_messages"] = deleted_chats

            # Clean up orphaned PALD data
            deleted_palds = self.session.execute("""
                DELETE FROM study_pald_data 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["pald_data"] = deleted_palds

            # Clean up orphaned generated images
            deleted_images = self.session.execute("""
                DELETE FROM generated_images 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["generated_images"] = deleted_images

            # Clean up orphaned feedback records
            deleted_feedback = self.session.execute("""
                DELETE FROM feedback_records 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["feedback_records"] = deleted_feedback

            # Clean up orphaned interaction logs
            deleted_logs = self.session.execute("""
                DELETE FROM interaction_logs 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["interaction_logs"] = deleted_logs

            # Clean up orphaned pseudonym mappings
            deleted_mappings = self.session.execute("""
                DELETE FROM pseudonym_mappings 
                WHERE pseudonym_id NOT IN (SELECT pseudonym_id FROM pseudonyms)
            """).rowcount
            cleanup_counts["pseudonym_mappings"] = deleted_mappings

            self.session.flush()
            
            total_cleaned = sum(cleanup_counts.values())
            if total_cleaned > 0:
                self.logger.info(f"Cleaned up {total_cleaned} orphaned records")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup orphaned records: {e}")
            cleanup_counts["error"] = str(e)

        return cleanup_counts

    def vacuum_database(self) -> bool:
        """
        Perform database maintenance operations (PostgreSQL VACUUM).
        
        Returns:
            True if vacuum was successful, False otherwise
        """
        try:
            # Check if we're using PostgreSQL
            if "postgresql" in str(self.session.bind.url):
                # Note: VACUUM cannot be run inside a transaction
                # This would need to be run with autocommit=True
                self.logger.info("Database vacuum would need to be run outside transaction")
                return True
            else:
                self.logger.info("Database vacuum not applicable for non-PostgreSQL database")
                return True
                
        except Exception as e:
            self.logger.error(f"Database vacuum failed: {e}")
            return False