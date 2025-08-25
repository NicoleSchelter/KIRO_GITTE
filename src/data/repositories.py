"""
Repository classes for data access layer.
Implements the repository pattern for all database entities with CRUD operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (
    AuditLog,
    AuditLogStatus,
    ChatMessage,
    ConsentRecord,
    ConsentType,
    FederatedLearningUpdate,
    FeedbackRecord,
    GeneratedImage,
    ImageCorrection,
    ImageProcessingResult,
    ImageProcessingResultStatus,
    InteractionLog,
    PALDAttributeCandidate,
    PALDData,
    PALDSchemaVersion,
    PrerequisiteCheckResult,
    Pseudonym,
    PseudonymMapping,
    StudyConsentRecord,
    StudyConsentType,
    StudyPALDData,
    StudySurveyResponse,
    SystemMetadata,
    TooltipInteraction,
    UXAuditLog,
    User,
    UserCorrectionAction,
    UserRole,
)
from .schemas import (
    AuditLogCreate,
    AuditLogFilters,
    AuditLogUpdate,
    ConsentRecordCreate,
    FederatedLearningUpdateCreate,
    ImageCorrectionCreate,
    ImageProcessingResultCreate,
    PALDAttributeCandidateCreate,
    PALDSchemaVersionCreate,
    PrerequisiteCheckResultCreate,
    PseudonymCreate,
    PseudonymMappingCreate,
    SystemMetadataCreate,
    TooltipInteractionCreate,
    UXAuditLogCreate,
    UserCreate,
    UserUpdate,
)

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common CRUD operations."""

    def __init__(self, session: Session, model_class):
        self.session = session
        self.model_class = model_class

    def get_by_id(self, id: UUID) -> Any | None:
        """Get entity by ID."""
        try:
            return self.session.query(self.model_class).filter(self.model_class.id == id).first()
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID {id}: {e}")
            return None

    def get_all(self, limit: int | None = None, offset: int | None = None) -> list[Any]:
        """Get all entities with optional pagination."""
        try:
            query = self.session.query(self.model_class)
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting all {self.model_class.__name__}: {e}")
            return []

    def delete(self, id: UUID) -> bool:
        """Delete entity by ID."""
        try:
            entity = self.get_by_id(id)
            if entity:
                self.session.delete(entity)
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__} {id}: {e}")
            return False

    def count(self) -> int:
        """Count total entities."""
        try:
            return self.session.query(self.model_class).count()
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            return 0


class UserRepository(BaseRepository):
    """Repository for User entities."""

    def __init__(self, session: Session):
        super().__init__(session, User)

    def create(self, user_data: UserCreate, password_hash: str, pseudonym: str) -> User | None:
        """Create a new user."""
        try:
            user = User(
                username=user_data.username,
                password_hash=password_hash,
                role=user_data.role.value if hasattr(user_data.role, "value") else user_data.role,
                pseudonym=pseudonym,
            )
            self.session.add(user)
            self.session.flush()
            return user
        except IntegrityError as e:
            logger.error(f"User creation failed - integrity error: {e}")
            self.session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        try:
            return self.session.query(User).filter(User.username == username).first()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None

    def get_by_pseudonym(self, pseudonym: str) -> User | None:
        """Get user by pseudonym."""
        try:
            return self.session.query(User).filter(User.pseudonym == pseudonym).first()
        except Exception as e:
            logger.error(f"Error getting user by pseudonym {pseudonym}: {e}")
            return None

    def update(self, user_id: UUID, user_data: UserUpdate) -> User | None:
        """Update user."""
        try:
            user = self.get_by_id(user_id)
            if not user:
                return None

            if user_data.username is not None:
                user.username = user_data.username
            if user_data.role is not None:
                user.role = (
                    user_data.role.value if hasattr(user_data.role, "value") else user_data.role
                )
            if user_data.is_active is not None:
                user.is_active = user_data.is_active

            user.updated_at = datetime.utcnow()
            self.session.flush()
            return user
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            return None

    def get_by_role(self, role: UserRole) -> list[User]:
        """Get users by role."""
        try:
            return (
                self.session.query(User)
                .filter(User.role == (role.value if hasattr(role, "value") else role))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting users by role {role}: {e}")
            return []

    def get_active_users(self) -> list[User]:
        """Get all active users."""
        try:
            return self.session.query(User).filter(User.is_active is True).all()
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []


class ConsentRepository(BaseRepository):
    """Repository for ConsentRecord entities."""

    def __init__(self, session: Session):
        super().__init__(session, ConsentRecord)

    def create(self, user_id: UUID, consent_data: ConsentRecordCreate) -> ConsentRecord | None:
        """Create a new consent record."""
        try:
            consent = ConsentRecord(
                user_id=user_id,
                consent_type=(
                    consent_data.consent_type.value
                    if hasattr(consent_data.consent_type, "value")
                    else consent_data.consent_type
                ),
                consent_given=consent_data.consent_given,
                consent_version=consent_data.consent_version,
                consent_metadata=consent_data.consent_metadata,
            )
            self.session.add(consent)
            self.session.flush()
            return consent
        except Exception as e:
            logger.error(f"Error creating consent record: {e}")
            return None

    def get_by_user_and_type(
        self, user_id: UUID, consent_type: ConsentType
    ) -> ConsentRecord | None:
        """Get latest consent record by user and type."""
        try:
            return (
                self.session.query(ConsentRecord)
                .filter(
                    and_(
                        ConsentRecord.user_id == user_id,
                        ConsentRecord.consent_type
                        == (consent_type.value if hasattr(consent_type, "value") else consent_type),
                    )
                )
                .order_by(desc(ConsentRecord.timestamp))
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting consent by user {user_id} and type {consent_type}: {e}")
            return None

    def get_by_user(self, user_id: UUID) -> list[ConsentRecord]:
        """Get all consent records for a user."""
        try:
            return (
                self.session.query(ConsentRecord)
                .filter(ConsentRecord.user_id == user_id)
                .order_by(desc(ConsentRecord.timestamp))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting consent records for user {user_id}: {e}")
            return []

    def withdraw_consent(
        self, user_id: UUID, consent_type: ConsentType, reason: str | None = None
    ) -> bool:
        """Withdraw consent for a user and type."""
        try:
            import time

            # Small delay to ensure different timestamp
            time.sleep(0.001)

            # Create withdrawal record
            withdrawal_time = datetime.utcnow()
            withdrawal = ConsentRecord(
                user_id=user_id,
                consent_type=consent_type.value if hasattr(consent_type, "value") else consent_type,
                consent_given=False,
                consent_version="withdrawal",
                consent_metadata={"reason": reason, "withdrawn_at": withdrawal_time.isoformat()},
                withdrawn_at=withdrawal_time,
                timestamp=withdrawal_time,  # Explicitly set timestamp
            )
            self.session.add(withdrawal)
            self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Error withdrawing consent for user {user_id}, type {consent_type}: {e}")
            return False

    def check_consent(self, user_id: UUID, consent_type: ConsentType) -> bool:
        """Check if user has given consent for a specific type."""
        try:
            latest_consent = self.get_by_user_and_type(user_id, consent_type)
            # Consent is valid if the latest record shows consent_given=True and not withdrawn
            return (
                latest_consent is not None
                and latest_consent.consent_given
                and latest_consent.withdrawn_at is None
            )
        except Exception as e:
            logger.error(f"Error checking consent for user {user_id}, type {consent_type}: {e}")
            return False


class PALDSchemaRepository(BaseRepository):
    """Repository for PALDSchemaVersion entities."""

    def __init__(self, session: Session):
        super().__init__(session, PALDSchemaVersion)

    def create(self, schema_data: PALDSchemaVersionCreate) -> PALDSchemaVersion | None:
        """Create a new PALD schema version."""
        try:
            schema = PALDSchemaVersion(
                version=schema_data.version,
                schema_content=schema_data.schema_content,
                migration_notes=schema_data.migration_notes,
            )
            self.session.add(schema)
            self.session.flush()
            return schema
        except Exception as e:
            logger.error(f"Error creating PALD schema version: {e}")
            return None

    def get_by_version(self, version: str) -> PALDSchemaVersion | None:
        """Get schema by version."""
        try:
            return (
                self.session.query(PALDSchemaVersion)
                .filter(PALDSchemaVersion.version == version)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting PALD schema version {version}: {e}")
            return None

    def get_active_schema(self) -> PALDSchemaVersion | None:
        """Get the currently active schema."""
        try:
            return (
                self.session.query(PALDSchemaVersion)
                .filter(PALDSchemaVersion.is_active is True)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting active PALD schema: {e}")
            return None

    def set_active_schema(self, version: str) -> bool:
        """Set a schema version as active."""
        try:
            # Deactivate all schemas
            self.session.query(PALDSchemaVersion).update({PALDSchemaVersion.is_active: False})

            # Activate the specified version
            schema = self.get_by_version(version)
            if schema:
                schema.is_active = True
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting active PALD schema {version}: {e}")
            return False

    def get_all_versions(self) -> list[PALDSchemaVersion]:
        """Get all schema versions ordered by creation date."""
        try:
            return (
                self.session.query(PALDSchemaVersion)
                .order_by(desc(PALDSchemaVersion.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting all PALD schema versions: {e}")
            return []


class PALDAttributeCandidateRepository(BaseRepository):
    """Repository for PALDAttributeCandidate entities."""

    def __init__(self, session: Session):
        super().__init__(session, PALDAttributeCandidate)

    def create(self, candidate_data: PALDAttributeCandidateCreate) -> PALDAttributeCandidate | None:
        """Create a new attribute candidate."""
        try:
            candidate = PALDAttributeCandidate(
                attribute_name=candidate_data.attribute_name,
                attribute_category=candidate_data.attribute_category,
            )
            self.session.add(candidate)
            self.session.flush()
            return candidate
        except Exception as e:
            logger.error(f"Error creating PALD attribute candidate: {e}")
            return None

    def get_by_name(self, attribute_name: str) -> PALDAttributeCandidate | None:
        """Get attribute candidate by name."""
        try:
            return (
                self.session.query(PALDAttributeCandidate)
                .filter(PALDAttributeCandidate.attribute_name == attribute_name)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting attribute candidate {attribute_name}: {e}")
            return None

    def increment_mention_count(self, attribute_name: str) -> PALDAttributeCandidate | None:
        """Increment mention count for an attribute."""
        try:
            candidate = self.get_by_name(attribute_name)
            if candidate:
                candidate.mention_count += 1
                candidate.last_mentioned = datetime.utcnow()
                self.session.flush()
                return candidate
            return None
        except Exception as e:
            logger.error(f"Error incrementing mention count for {attribute_name}: {e}")
            return None

    def get_candidates_above_threshold(self, threshold: int) -> list[PALDAttributeCandidate]:
        """Get candidates that have reached the mention threshold."""
        try:
            return (
                self.session.query(PALDAttributeCandidate)
                .filter(
                    and_(
                        PALDAttributeCandidate.mention_count >= threshold,
                        PALDAttributeCandidate.threshold_reached is False,
                    )
                )
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting candidates above threshold {threshold}: {e}")
            return []

    def mark_threshold_reached(self, candidate_id: UUID) -> bool:
        """Mark a candidate as having reached the threshold."""
        try:
            candidate = self.get_by_id(candidate_id)
            if candidate:
                candidate.threshold_reached = True
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking threshold reached for candidate {candidate_id}: {e}")
            return False

    def mark_added_to_schema(self, candidate_id: UUID, schema_version: str) -> bool:
        """Mark a candidate as added to schema."""
        try:
            candidate = self.get_by_id(candidate_id)
            if candidate:
                candidate.added_to_schema = True
                candidate.schema_version_added = schema_version
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking candidate {candidate_id} as added to schema: {e}")
            return False


class PALDDataRepository(BaseRepository):
    """Repository for PALDData entities."""

    def __init__(self, session: Session):
        super().__init__(session, PALDData)

    def create(self, pald_data: PALDData) -> PALDData | None:
        """Create new PALD data."""
        try:
            self.session.add(pald_data)
            self.session.flush()
            return pald_data
        except Exception as e:
            logger.error(f"Error creating PALD data: {e}")
            return None

    def get_by_user_id(self, user_id: UUID) -> list[PALDData]:
        """Get all PALD data for a user."""
        try:
            return (
                self.session.query(PALDData)
                .filter(PALDData.user_id == user_id)
                .order_by(desc(PALDData.updated_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting PALD data for user {user_id}: {e}")
            return []

    def get_by_user(self, user_id: UUID) -> PALDData | None:
        """Get latest PALD data for a user."""
        try:
            return (
                self.session.query(PALDData)
                .filter(PALDData.user_id == user_id)
                .order_by(desc(PALDData.updated_at))
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting PALD data for user {user_id}: {e}")
            return None

    def update(self, pald_data: PALDData) -> PALDData | None:
        """Update PALD data."""
        try:
            self.session.flush()
            return pald_data
        except Exception as e:
            logger.error(f"Error updating PALD data {pald_data.id}: {e}")
            return None

    def set_validation_status(
        self, pald_id: UUID, is_valid: bool, errors: dict[str, Any] | None = None
    ) -> bool:
        """Set validation status for PALD data."""
        try:
            pald = self.get_by_id(pald_id)
            if pald:
                pald.is_validated = is_valid
                pald.validation_errors = errors
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error setting validation status for PALD {pald_id}: {e}")
            return False

    def get_by_schema_version(self, schema_version: str) -> list[PALDData]:
        """Get all PALD data for a specific schema version."""
        try:
            return (
                self.session.query(PALDData).filter(PALDData.schema_version == schema_version).all()
            )
        except Exception as e:
            logger.error(f"Error getting PALD data for schema version {schema_version}: {e}")
            return []


class AuditLogRepository(BaseRepository):
    """Repository for AuditLog entities."""

    def __init__(self, session: Session):
        super().__init__(session, AuditLog)

    def create(self, audit_data: AuditLogCreate) -> AuditLog | None:
        """Create new audit log entry."""
        try:
            audit = AuditLog(
                request_id=audit_data.request_id,
                user_id=audit_data.user_id,
                operation=audit_data.operation,
                model_used=audit_data.model_used,
                parameters=audit_data.parameters,
                parent_log_id=audit_data.parent_log_id,
            )
            self.session.add(audit)
            self.session.flush()
            return audit
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
            return None

    def update(self, audit_id: UUID, audit_data: AuditLogUpdate) -> AuditLog | None:
        """Update audit log entry."""
        try:
            audit = self.get_by_id(audit_id)
            if not audit:
                return None

            if audit_data.input_data is not None:
                audit.input_data = audit_data.input_data
            if audit_data.output_data is not None:
                audit.output_data = audit_data.output_data
            if audit_data.token_usage is not None:
                audit.token_usage = audit_data.token_usage
            if audit_data.latency_ms is not None:
                audit.latency_ms = audit_data.latency_ms
            if audit_data.status is not None:
                audit.status = (
                    audit_data.status.value
                    if hasattr(audit_data.status, "value")
                    else audit_data.status
                )
            if audit_data.error_message is not None:
                audit.error_message = audit_data.error_message

            self.session.flush()
            return audit
        except Exception as e:
            logger.error(f"Error updating audit log {audit_id}: {e}")
            return None

    def finalize(self, audit_id: UUID) -> bool:
        """Finalize audit log entry."""
        try:
            audit = self.get_by_id(audit_id)
            if audit:
                audit.status = AuditLogStatus.FINALIZED.value
                audit.finalized_at = datetime.utcnow()
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error finalizing audit log {audit_id}: {e}")
            return False

    def get_by_request_id(self, request_id: str) -> list[AuditLog]:
        """Get audit logs by request ID."""
        try:
            return (
                self.session.query(AuditLog)
                .filter(AuditLog.request_id == request_id)
                .order_by(asc(AuditLog.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting audit logs for request {request_id}: {e}")
            return []

    def get_by_user(self, user_id: UUID, limit: int | None = None) -> list[AuditLog]:
        """Get audit logs for a user."""
        try:
            query = (
                self.session.query(AuditLog)
                .filter(AuditLog.user_id == user_id)
                .order_by(desc(AuditLog.created_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting audit logs for user {user_id}: {e}")
            return []

    def get_filtered(
        self, filters: AuditLogFilters, limit: int | None = None, offset: int | None = None
    ) -> list[AuditLog]:
        """Get audit logs with filters."""
        try:
            query = self.session.query(AuditLog)

            if filters.user_id:
                query = query.filter(AuditLog.user_id == filters.user_id)
            if filters.operation:
                query = query.filter(AuditLog.operation == filters.operation)
            if filters.model_used:
                query = query.filter(AuditLog.model_used == filters.model_used)
            if filters.status:
                query = query.filter(
                    AuditLog.status
                    == (
                        filters.status.value if hasattr(filters.status, "value") else filters.status
                    )
                )
            if filters.start_date:
                query = query.filter(AuditLog.created_at >= filters.start_date)
            if filters.end_date:
                query = query.filter(AuditLog.created_at <= filters.end_date)
            if filters.request_id:
                query = query.filter(AuditLog.request_id == filters.request_id)
            if filters.parent_log_id:
                query = query.filter(AuditLog.parent_log_id == filters.parent_log_id)

            query = query.order_by(desc(AuditLog.created_at))

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            return query.all()
        except Exception as e:
            logger.error(f"Error getting filtered audit logs: {e}")
            return []


class FederatedLearningRepository(BaseRepository):
    """Repository for FederatedLearningUpdate entities."""

    def __init__(self, session: Session):
        super().__init__(session, FederatedLearningUpdate)

    def create(
        self, user_id: UUID, fl_data: FederatedLearningUpdateCreate
    ) -> FederatedLearningUpdate | None:
        """Create new FL update."""
        try:
            fl_update = FederatedLearningUpdate(
                user_id=user_id,
                update_data=fl_data.update_data,
                model_version=fl_data.model_version,
                aggregation_round=fl_data.aggregation_round,
                privacy_budget_used=fl_data.privacy_budget_used,
                update_size_bytes=len(fl_data.update_data),
            )
            self.session.add(fl_update)
            self.session.flush()
            return fl_update
        except Exception as e:
            logger.error(f"Error creating FL update: {e}")
            return None

    def mark_processed(self, update_id: UUID) -> bool:
        """Mark FL update as processed."""
        try:
            update = self.get_by_id(update_id)
            if update:
                update.processed = True
                update.processed_at = datetime.utcnow()
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error marking FL update {update_id} as processed: {e}")
            return False

    def get_unprocessed(self, model_version: str | None = None) -> list[FederatedLearningUpdate]:
        """Get unprocessed FL updates."""
        try:
            query = self.session.query(FederatedLearningUpdate).filter(
                FederatedLearningUpdate.processed is False
            )
            if model_version:
                query = query.filter(FederatedLearningUpdate.model_version == model_version)
            return query.order_by(asc(FederatedLearningUpdate.submitted_at)).all()
        except Exception as e:
            logger.error(f"Error getting unprocessed FL updates: {e}")
            return []

    def get_by_user(self, user_id: UUID) -> list[FederatedLearningUpdate]:
        """Get FL updates for a user."""
        try:
            return (
                self.session.query(FederatedLearningUpdate)
                .filter(FederatedLearningUpdate.user_id == user_id)
                .order_by(desc(FederatedLearningUpdate.submitted_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting FL updates for user {user_id}: {e}")
            return []

    def create_fl_update(
        self,
        user_id: UUID,
        update_data: bytes,
        model_version: str,
        aggregation_round: int | None = None,
        privacy_budget_used: dict[str, Any] | None = None,
    ) -> FederatedLearningUpdate | None:
        """Create new FL update with simplified interface."""
        try:
            fl_update = FederatedLearningUpdate(
                user_id=user_id,
                update_data=update_data,
                model_version=model_version,
                aggregation_round=aggregation_round,
                privacy_budget_used=privacy_budget_used,
                update_size_bytes=len(update_data),
            )
            self.session.add(fl_update)
            self.session.flush()
            return fl_update
        except Exception as e:
            logger.error(f"Error creating FL update: {e}")
            return None

    def mark_update_processed(self, update_id: UUID) -> bool:
        """Mark FL update as processed (alias for mark_processed)."""
        return self.mark_processed(update_id)

    def get_user_updates(
        self, user_id: UUID, limit: int | None = None
    ) -> list[FederatedLearningUpdate]:
        """Get FL updates for a user with optional limit."""
        try:
            query = (
                self.session.query(FederatedLearningUpdate)
                .filter(FederatedLearningUpdate.user_id == user_id)
                .order_by(desc(FederatedLearningUpdate.submitted_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting FL updates for user {user_id}: {e}")
            return []

    def get_by_model_version(self, model_version: str) -> list[FederatedLearningUpdate]:
        """Get FL updates by model version."""
        try:
            return (
                self.session.query(FederatedLearningUpdate)
                .filter(FederatedLearningUpdate.model_version == model_version)
                .order_by(desc(FederatedLearningUpdate.submitted_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting FL updates for model version {model_version}: {e}")
            return []


class SystemMetadataRepository(BaseRepository):
    """Repository for SystemMetadata entities."""

    def __init__(self, session: Session):
        super().__init__(session, SystemMetadata)

    def create(self, metadata: SystemMetadataCreate) -> SystemMetadata | None:
        """Create system metadata."""
        try:
            meta = SystemMetadata(key=metadata.key, value=metadata.value)
            self.session.add(meta)
            self.session.flush()
            return meta
        except Exception as e:
            logger.error(f"Error creating system metadata: {e}")
            return None

    def get_by_key(self, key: str) -> SystemMetadata | None:
        """Get metadata by key."""
        try:
            return self.session.query(SystemMetadata).filter(SystemMetadata.key == key).first()
        except Exception as e:
            logger.error(f"Error getting system metadata {key}: {e}")
            return None

    def set_value(self, key: str, value: str) -> bool:
        """Set metadata value."""
        try:
            meta = self.get_by_key(key)
            if meta:
                meta.value = value
                meta.updated_at = datetime.utcnow()
            else:
                meta = SystemMetadata(key=key, value=value)
                self.session.add(meta)
            self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Error setting system metadata {key}: {e}")
            return False


def get_fl_repository() -> FederatedLearningRepository:
    """Get FL repository with database session."""
    from src.data.database import get_session_sync

    return FederatedLearningRepository(get_session_sync())


def get_user_repository() -> UserRepository:
    """Get user repository with database session."""
    from src.data.database import get_session_sync

    return UserRepository(get_session_sync())


def get_consent_repository() -> ConsentRepository:
    """Get consent repository with database session."""
    from src.data.database import get_session_sync

    return ConsentRepository(get_session_sync())


def get_pald_data_repository() -> PALDDataRepository:
    """Get PALD data repository with database session."""
    from src.data.database import get_session_sync

    return PALDDataRepository(get_session_sync())


def get_audit_log_repository() -> AuditLogRepository:
    """Get audit log repository with database session."""
    from src.data.database import get_session_sync

    return AuditLogRepository(get_session_sync())


# UX Enhancement Repositories


class ImageProcessingResultRepository(BaseRepository):
    """Repository for ImageProcessingResult entities."""

    def __init__(self, session: Session):
        super().__init__(session, ImageProcessingResult)

    def create(self, user_id: UUID, result_data: ImageProcessingResultCreate) -> ImageProcessingResult | None:
        """Create a new image processing result."""
        try:
            result = ImageProcessingResult(
                user_id=user_id,
                original_image_path=result_data.original_image_path,
                processed_image_path=result_data.processed_image_path,
                processing_method=result_data.processing_method,
                status=result_data.status.value if hasattr(result_data.status, "value") else result_data.status,
                confidence_score=result_data.confidence_score,
                processing_time_ms=result_data.processing_time_ms,
                quality_issues=result_data.quality_issues,
                person_count=result_data.person_count,
                quality_score=result_data.quality_score,
            )
            self.session.add(result)
            self.session.flush()
            return result
        except Exception as e:
            logger.error(f"Error creating image processing result: {e}")
            return None

    def get_by_user(self, user_id: UUID, limit: int | None = None) -> list[ImageProcessingResult]:
        """Get image processing results for a user."""
        try:
            query = (
                self.session.query(ImageProcessingResult)
                .filter(ImageProcessingResult.user_id == user_id)
                .order_by(desc(ImageProcessingResult.created_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting image processing results for user {user_id}: {e}")
            return []

    def update_status(self, result_id: UUID, status: ImageProcessingResultStatus) -> bool:
        """Update processing result status."""
        try:
            result = self.get_by_id(result_id)
            if result:
                result.status = status.value if hasattr(status, "value") else status
                result.updated_at = datetime.utcnow()
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating image processing result status {result_id}: {e}")
            return False

    def get_by_status(self, status: ImageProcessingResultStatus) -> list[ImageProcessingResult]:
        """Get results by status."""
        try:
            return (
                self.session.query(ImageProcessingResult)
                .filter(ImageProcessingResult.status == (status.value if hasattr(status, "value") else status))
                .order_by(desc(ImageProcessingResult.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting image processing results by status {status}: {e}")
            return []


class ImageCorrectionRepository(BaseRepository):
    """Repository for ImageCorrection entities."""

    def __init__(self, session: Session):
        super().__init__(session, ImageCorrection)

    def create(self, user_id: UUID, correction_data: ImageCorrectionCreate) -> ImageCorrection | None:
        """Create a new image correction."""
        try:
            correction = ImageCorrection(
                processing_result_id=correction_data.processing_result_id,
                user_id=user_id,
                correction_action=correction_data.correction_action.value if hasattr(correction_data.correction_action, "value") else correction_data.correction_action,
                crop_coordinates=correction_data.crop_coordinates,
                rejection_reason=correction_data.rejection_reason,
                suggested_modifications=correction_data.suggested_modifications,
                final_image_path=correction_data.final_image_path,
                correction_time_ms=correction_data.correction_time_ms,
            )
            self.session.add(correction)
            self.session.flush()
            return correction
        except Exception as e:
            logger.error(f"Error creating image correction: {e}")
            return None

    def get_by_processing_result(self, processing_result_id: UUID) -> list[ImageCorrection]:
        """Get corrections for a processing result."""
        try:
            return (
                self.session.query(ImageCorrection)
                .filter(ImageCorrection.processing_result_id == processing_result_id)
                .order_by(desc(ImageCorrection.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting corrections for processing result {processing_result_id}: {e}")
            return []

    def get_by_user(self, user_id: UUID, limit: int | None = None) -> list[ImageCorrection]:
        """Get corrections by user."""
        try:
            query = (
                self.session.query(ImageCorrection)
                .filter(ImageCorrection.user_id == user_id)
                .order_by(desc(ImageCorrection.created_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting corrections for user {user_id}: {e}")
            return []

    def get_by_action(self, action: UserCorrectionAction) -> list[ImageCorrection]:
        """Get corrections by action type."""
        try:
            return (
                self.session.query(ImageCorrection)
                .filter(ImageCorrection.correction_action == (action.value if hasattr(action, "value") else action))
                .order_by(desc(ImageCorrection.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting corrections by action {action}: {e}")
            return []


class PrerequisiteCheckResultRepository(BaseRepository):
    """Repository for PrerequisiteCheckResult entities."""

    def __init__(self, session: Session):
        super().__init__(session, PrerequisiteCheckResult)

    def create(self, result_data: PrerequisiteCheckResultCreate) -> PrerequisiteCheckResult | None:
        """Create a new prerequisite check result."""
        try:
            result = PrerequisiteCheckResult(
                user_id=result_data.user_id,
                operation_name=result_data.operation_name,
                checker_name=result_data.checker_name,
                check_type=result_data.check_type.value if hasattr(result_data.check_type, "value") else result_data.check_type,
                status=result_data.status.value if hasattr(result_data.status, "value") else result_data.status,
                message=result_data.message,
                details=result_data.details,
                resolution_steps=result_data.resolution_steps,
                check_time_ms=result_data.check_time_ms,
                confidence_score=result_data.confidence_score,
                cached=result_data.cached,
            )
            self.session.add(result)
            self.session.flush()
            return result
        except Exception as e:
            logger.error(f"Error creating prerequisite check result: {e}")
            return None

    def get_by_operation(self, operation_name: str, user_id: UUID | None = None) -> list[PrerequisiteCheckResult]:
        """Get prerequisite results for an operation."""
        try:
            query = self.session.query(PrerequisiteCheckResult).filter(
                PrerequisiteCheckResult.operation_name == operation_name
            )
            if user_id:
                query = query.filter(PrerequisiteCheckResult.user_id == user_id)
            return query.order_by(desc(PrerequisiteCheckResult.created_at)).all()
        except Exception as e:
            logger.error(f"Error getting prerequisite results for operation {operation_name}: {e}")
            return []

    def get_latest_by_checker(self, checker_name: str, operation_name: str, user_id: UUID | None = None) -> PrerequisiteCheckResult | None:
        """Get latest result for a specific checker."""
        try:
            query = self.session.query(PrerequisiteCheckResult).filter(
                and_(
                    PrerequisiteCheckResult.checker_name == checker_name,
                    PrerequisiteCheckResult.operation_name == operation_name
                )
            )
            if user_id:
                query = query.filter(PrerequisiteCheckResult.user_id == user_id)
            return query.order_by(desc(PrerequisiteCheckResult.created_at)).first()
        except Exception as e:
            logger.error(f"Error getting latest result for checker {checker_name}: {e}")
            return None

    def cleanup_old_results(self, days_to_keep: int = 30) -> int:
        """Clean up old prerequisite check results."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            deleted_count = (
                self.session.query(PrerequisiteCheckResult)
                .filter(PrerequisiteCheckResult.created_at < cutoff_date)
                .delete()
            )
            self.session.flush()
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old prerequisite results: {e}")
            return 0


class TooltipInteractionRepository(BaseRepository):
    """Repository for TooltipInteraction entities."""

    def __init__(self, session: Session):
        super().__init__(session, TooltipInteraction)

    def create(self, interaction_data: TooltipInteractionCreate) -> TooltipInteraction | None:
        """Create a new tooltip interaction."""
        try:
            interaction = TooltipInteraction(
                user_id=interaction_data.user_id,
                session_id=interaction_data.session_id,
                element_id=interaction_data.element_id,
                tooltip_content_id=interaction_data.tooltip_content_id,
                interaction_type=interaction_data.interaction_type.value if hasattr(interaction_data.interaction_type, "value") else interaction_data.interaction_type,
                page_context=interaction_data.page_context,
                tooltip_title=interaction_data.tooltip_title,
                tooltip_description=interaction_data.tooltip_description,
                display_time_ms=interaction_data.display_time_ms,
                user_agent=interaction_data.user_agent,
            )
            self.session.add(interaction)
            self.session.flush()
            return interaction
        except Exception as e:
            logger.error(f"Error creating tooltip interaction: {e}")
            return None

    def get_by_user(self, user_id: UUID, limit: int | None = None) -> list[TooltipInteraction]:
        """Get tooltip interactions for a user."""
        try:
            query = (
                self.session.query(TooltipInteraction)
                .filter(TooltipInteraction.user_id == user_id)
                .order_by(desc(TooltipInteraction.created_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting tooltip interactions for user {user_id}: {e}")
            return []

    def get_by_element(self, element_id: str, limit: int | None = None) -> list[TooltipInteraction]:
        """Get interactions for a specific element."""
        try:
            query = (
                self.session.query(TooltipInteraction)
                .filter(TooltipInteraction.element_id == element_id)
                .order_by(desc(TooltipInteraction.created_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting tooltip interactions for element {element_id}: {e}")
            return []

    def get_interaction_stats(self, element_id: str | None = None) -> dict[str, Any]:
        """Get interaction statistics."""
        try:
            query = self.session.query(TooltipInteraction)
            if element_id:
                query = query.filter(TooltipInteraction.element_id == element_id)
            
            interactions = query.all()
            
            stats = {
                "total_interactions": len(interactions),
                "unique_users": len(set(i.user_id for i in interactions if i.user_id)),
                "interaction_types": {},
                "avg_display_time_ms": 0,
            }
            
            if interactions:
                # Count interaction types
                for interaction in interactions:
                    interaction_type = interaction.interaction_type
                    stats["interaction_types"][interaction_type] = stats["interaction_types"].get(interaction_type, 0) + 1
                
                # Calculate average display time
                display_times = [i.display_time_ms for i in interactions if i.display_time_ms]
                if display_times:
                    stats["avg_display_time_ms"] = sum(display_times) / len(display_times)
            
            return stats
        except Exception as e:
            logger.error(f"Error getting tooltip interaction stats: {e}")
            return {}


class UXAuditLogRepository(BaseRepository):
    """Repository for UXAuditLog entities."""

    def __init__(self, session: Session):
        super().__init__(session, UXAuditLog)

    def create(self, log_data: UXAuditLogCreate) -> UXAuditLog | None:
        """Create a new UX audit log entry."""
        try:
            log_entry = UXAuditLog(
                user_id=log_data.user_id,
                session_id=log_data.session_id,
                event_type=log_data.event_type.value if hasattr(log_data.event_type, "value") else log_data.event_type,
                event_context=log_data.event_context,
                event_data=log_data.event_data,
                workflow_step=log_data.workflow_step,
                success=log_data.success,
                error_message=log_data.error_message,
                duration_ms=log_data.duration_ms,
                user_agent=log_data.user_agent,
                ip_address=log_data.ip_address,
            )
            self.session.add(log_entry)
            self.session.flush()
            return log_entry
        except Exception as e:
            logger.error(f"Error creating UX audit log: {e}")
            return None

    def get_by_user(self, user_id: UUID, limit: int | None = None) -> list[UXAuditLog]:
        """Get UX audit logs for a user."""
        try:
            query = (
                self.session.query(UXAuditLog)
                .filter(UXAuditLog.user_id == user_id)
                .order_by(desc(UXAuditLog.created_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting UX audit logs for user {user_id}: {e}")
            return []

    def get_by_event_type(self, event_type: str, limit: int | None = None) -> list[UXAuditLog]:
        """Get logs by event type."""
        try:
            query = (
                self.session.query(UXAuditLog)
                .filter(UXAuditLog.event_type == event_type)
                .order_by(desc(UXAuditLog.created_at))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting UX audit logs by event type {event_type}: {e}")
            return []

    def get_workflow_analytics(self, workflow_step: str | None = None) -> dict[str, Any]:
        """Get workflow analytics."""
        try:
            query = self.session.query(UXAuditLog)
            if workflow_step:
                query = query.filter(UXAuditLog.workflow_step == workflow_step)
            
            logs = query.all()
            
            analytics = {
                "total_events": len(logs),
                "success_rate": 0,
                "avg_duration_ms": 0,
                "event_types": {},
                "error_types": {},
            }
            
            if logs:
                # Calculate success rate
                successful_events = [log for log in logs if log.success is True]
                analytics["success_rate"] = len(successful_events) / len(logs) * 100
                
                # Calculate average duration
                durations = [log.duration_ms for log in logs if log.duration_ms]
                if durations:
                    analytics["avg_duration_ms"] = sum(durations) / len(durations)
                
                # Count event types
                for log in logs:
                    event_type = log.event_type
                    analytics["event_types"][event_type] = analytics["event_types"].get(event_type, 0) + 1
                
                # Count error types
                failed_logs = [log for log in logs if log.success is False and log.error_message]
                for log in failed_logs:
                    error_type = log.error_message[:50] if log.error_message else "Unknown"
                    analytics["error_types"][error_type] = analytics["error_types"].get(error_type, 0) + 1
            
            return analytics
        except Exception as e:
            logger.error(f"Error getting workflow analytics: {e}")
            return {}

    def cleanup_old_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old UX audit logs."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            deleted_count = (
                self.session.query(UXAuditLog)
                .filter(UXAuditLog.created_at < cutoff_date)
                .delete()
            )
            self.session.flush()
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old UX audit logs: {e}")
            return 0


# Factory functions for UX enhancement repositories

def get_image_processing_result_repository() -> ImageProcessingResultRepository:
    """Get image processing result repository with database session."""
    from src.data.database import get_session_sync

    return ImageProcessingResultRepository(get_session_sync())


def get_image_correction_repository() -> ImageCorrectionRepository:
    """Get image correction repository with database session."""
    from src.data.database import get_session_sync

    return ImageCorrectionRepository(get_session_sync())


def get_prerequisite_check_result_repository() -> PrerequisiteCheckResultRepository:
    """Get prerequisite check result repository with database session."""
    from src.data.database import get_session_sync

    return PrerequisiteCheckResultRepository(get_session_sync())


def get_tooltip_interaction_repository() -> TooltipInteractionRepository:
    """Get tooltip interaction repository with database session."""
    from src.data.database import get_session_sync

    return TooltipInteractionRepository(get_session_sync())


def get_ux_audit_log_repository() -> UXAuditLogRepository:
    """Get UX audit log repository with database session."""
    from src.data.database import get_session_sync

    return UXAuditLogRepository(get_session_sync())


class PseudonymRepository(BaseRepository):
    """Repository for Pseudonym entities with privacy-preserving mapping."""

    def __init__(self, session: Session):
        super().__init__(session, Pseudonym)

    def create_pseudonym_with_mapping(
        self, 
        pseudonym_data: PseudonymCreate, 
        pseudonym_hash: str, 
        user_id: UUID, 
        created_by: str = "system"
    ) -> tuple[Pseudonym, PseudonymMapping] | tuple[None, None]:
        """Create a new pseudonym with user mapping."""
        try:
            # Create pseudonym
            pseudonym = Pseudonym(
                pseudonym_text=pseudonym_data.pseudonym_text,
                pseudonym_hash=pseudonym_hash,
            )
            self.session.add(pseudonym)
            self.session.flush()  # Get the pseudonym_id

            # Create mapping
            mapping = PseudonymMapping(
                user_id=user_id,
                pseudonym_id=pseudonym.pseudonym_id,
                created_by=created_by,
                access_level="admin_only"
            )
            self.session.add(mapping)
            self.session.flush()
            
            return pseudonym, mapping
        except IntegrityError as e:
            logger.error(f"Integrity error creating pseudonym: {e}")
            self.session.rollback()
            return None, None
        except Exception as e:
            logger.error(f"Error creating pseudonym: {e}")
            self.session.rollback()
            return None, None

    def create_pseudonym_standalone(
        self, 
        pseudonym_data: PseudonymCreate, 
        pseudonym_hash: str, 
        created_by: str = "system"
    ) -> Pseudonym | None:
        """Create a new pseudonym without user mapping (no user connection)."""
        try:
            # Create pseudonym without mapping
            pseudonym = Pseudonym(
                pseudonym_text=pseudonym_data.pseudonym_text,
                pseudonym_hash=pseudonym_hash,
            )
            self.session.add(pseudonym)
            self.session.flush()  # Get the pseudonym_id
            
            return pseudonym
        except IntegrityError as e:
            logger.error(f"Integrity error creating standalone pseudonym: {e}")
            self.session.rollback()
            return None
        except Exception as e:
            logger.error(f"Error creating standalone pseudonym: {e}")
            self.session.rollback()
            return None

    def get_by_user_id(self, user_id: UUID) -> Pseudonym | None:
        """Get active pseudonym by user ID through mapping."""
        try:
            result = (
                self.session.query(Pseudonym)
                .join(PseudonymMapping, Pseudonym.pseudonym_id == PseudonymMapping.pseudonym_id)
                .filter(
                    PseudonymMapping.user_id == user_id,
                    Pseudonym.is_active == True
                )
                .first()
            )
            return result
        except Exception as e:
            logger.error(f"Error getting pseudonym by user ID {user_id}: {e}")
            return None

    def get_mapping_by_user_id(self, user_id: UUID) -> PseudonymMapping | None:
        """Get pseudonym mapping by user ID."""
        try:
            return (
                self.session.query(PseudonymMapping)
                .filter(PseudonymMapping.user_id == user_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting mapping by user ID {user_id}: {e}")
            return None

    def get_by_pseudonym_text(self, pseudonym_text: str) -> Pseudonym | None:
        """Get pseudonym by pseudonym text."""
        try:
            return (
                self.session.query(Pseudonym)
                .filter(Pseudonym.pseudonym_text == pseudonym_text)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting pseudonym by text {pseudonym_text}: {e}")
            return None

    def get_by_text(self, pseudonym_text: str) -> Pseudonym | None:
        """Alias for get_by_pseudonym_text for consistency."""
        return self.get_by_pseudonym_text(pseudonym_text)

    def is_pseudonym_unique(self, pseudonym_text: str) -> bool:
        """Check if pseudonym text is unique."""
        try:
            existing = self.get_by_pseudonym_text(pseudonym_text)
            return existing is None
        except Exception as e:
            logger.error(f"Error checking pseudonym uniqueness: {e}")
            return False

    def deactivate_pseudonym(self, pseudonym_id: UUID) -> bool:
        """Deactivate a pseudonym."""
        try:
            pseudonym = self.get_by_id(pseudonym_id)
            if pseudonym:
                pseudonym.is_active = False
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deactivating pseudonym {pseudonym_id}: {e}")
            return False

    def deactivate_user_pseudonym(self, user_id: UUID) -> bool:
        """Deactivate a user's pseudonym through mapping."""
        try:
            pseudonym = self.get_by_user_id(user_id)
            if pseudonym:
                return self.deactivate_pseudonym(pseudonym.pseudonym_id)
            return False
        except Exception as e:
            logger.error(f"Error deactivating user pseudonym {user_id}: {e}")
            return False

    def get_by_id(self, pseudonym_id: UUID) -> Pseudonym | None:
        """Get pseudonym by ID."""
        try:
            return (
                self.session.query(Pseudonym)
                .filter(Pseudonym.pseudonym_id == pseudonym_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting pseudonym by ID {pseudonym_id}: {e}")
            return None


class StudyConsentRepository(BaseRepository):
    """Repository for StudyConsentRecord entities for study participation."""

    def __init__(self, session: Session):
        super().__init__(session, StudyConsentRecord)

    def create_consent(
        self,
        pseudonym_id: UUID,
        consent_type: StudyConsentType,
        granted: bool,
        version: str,
        metadata: dict[str, Any] | None = None,
    ) -> StudyConsentRecord | None:
        """Create a new study consent record with FK validation and idempotency."""
        try:
            from .models import StudyConsentRecord, StudyConsentType, Pseudonym
            from sqlalchemy.exc import IntegrityError
            
            # Validate consent type strictly
            if isinstance(consent_type, str):
                try:
                    consent_type = StudyConsentType(consent_type)
                except ValueError:
                    valid_types = [e.value for e in StudyConsentType]
                    logger.error(f"Invalid study consent type '{consent_type}'. Valid: {valid_types}")
                    raise ValueError(f"Invalid study consent type '{consent_type}'. Valid: {valid_types}")
            
            if not isinstance(consent_type, StudyConsentType):
                valid_types = [e.value for e in StudyConsentType]
                logger.error(f"Invalid study consent type '{consent_type}'. Valid: {valid_types}")
                raise ValueError(f"Invalid study consent type '{consent_type}'. Valid: {valid_types}")
            
            # CRITICAL: Check pseudonym exists before creating consent record
            pseudonym_exists = self.session.query(
                self.session.query(Pseudonym).filter(
                    Pseudonym.pseudonym_id == pseudonym_id
                ).exists()
            ).scalar()
            
            if not pseudonym_exists:
                from src.exceptions import MissingPseudonymError
                logger.error(f"Pseudonym {pseudonym_id} does not exist")
                raise MissingPseudonymError(f"Pseudonym {pseudonym_id} does not exist")
            
            # Check for existing consent with same pseudonym_id, consent_type, version (idempotency)
            existing_consent = self.session.query(StudyConsentRecord).filter(
                and_(
                    StudyConsentRecord.pseudonym_id == pseudonym_id,
                    StudyConsentRecord.consent_type == consent_type.value,
                    StudyConsentRecord.version == version
                )
            ).first()
            
            if existing_consent:
                # Update existing record if different granted status
                if existing_consent.granted != granted:
                    existing_consent.granted = granted
                    existing_consent.granted_at = datetime.utcnow()
                    if not granted:
                        existing_consent.revoked_at = datetime.utcnow()
                    else:
                        existing_consent.revoked_at = None
                    self.session.flush()
                
                logger.info(f"Updated existing consent record for pseudonym {pseudonym_id}, type {consent_type.value}")
                return existing_consent
            
            # Create new consent record
            consent = StudyConsentRecord(
                pseudonym_id=pseudonym_id,
                consent_type=consent_type.value,
                granted=granted,
                version=version,
            )
            self.session.add(consent)
            self.session.flush()
            
            logger.info(f"Created new consent record for pseudonym {pseudonym_id}, type {consent_type.value}")
            return consent
            
        except IntegrityError as e:
            logger.error(f"Integrity violation creating study consent record: {e}")
            self.session.rollback()
            
            # Check if it's a FK violation or uniqueness violation
            if "pseudonym" in str(e).lower() or "foreign key" in str(e).lower():
                from src.exceptions import MissingPseudonymError
                raise MissingPseudonymError(f"Pseudonym {pseudonym_id} does not exist")
            else:
                # Uniqueness violation - try to get existing record
                existing_consent = self.session.query(StudyConsentRecord).filter(
                    and_(
                        StudyConsentRecord.pseudonym_id == pseudonym_id,
                        StudyConsentRecord.consent_type == consent_type.value,
                        StudyConsentRecord.version == version
                    )
                ).first()
                
                if existing_consent:
                    logger.info(f"Consent already exists for pseudonym {pseudonym_id}, type {consent_type.value}")
                    return existing_consent
                else:
                    raise
                    
        except Exception as e:
            logger.error(f"Error creating study consent record: {e}")
            self.session.rollback()
            return None

    def get_by_pseudonym_and_type(
        self, pseudonym_id: UUID, consent_type: StudyConsentType
    ) -> StudyConsentRecord | None:
        """Get latest consent record by pseudonym and type."""
        try:
            from .models import StudyConsentRecord, StudyConsentType
            
            # Validate consent type strictly
            if isinstance(consent_type, str):
                try:
                    consent_type = StudyConsentType(consent_type)
                except ValueError:
                    valid_types = [e.value for e in StudyConsentType]
                    logger.error(f"Invalid study consent type '{consent_type}'. Valid: {valid_types}")
                    return None
            
            return (
                self.session.query(StudyConsentRecord)
                .filter(
                    and_(
                        StudyConsentRecord.pseudonym_id == pseudonym_id,
                        StudyConsentRecord.consent_type == consent_type.value,
                    )
                )
                .order_by(desc(StudyConsentRecord.granted_at))
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting consent by pseudonym {pseudonym_id} and type {consent_type}: {e}")
            return None

    def get_by_pseudonym(self, pseudonym_id: UUID) -> list[StudyConsentRecord]:
        """Get all consent records for a pseudonym."""
        try:
            from .models import StudyConsentRecord
            
            return (
                self.session.query(StudyConsentRecord)
                .filter(StudyConsentRecord.pseudonym_id == pseudonym_id)
                .order_by(desc(StudyConsentRecord.granted_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting consent records for pseudonym {pseudonym_id}: {e}")
            return []

    def withdraw_consent(
        self, pseudonym_id: UUID, consent_type: StudyConsentType, reason: str | None = None
    ) -> bool:
        """Withdraw consent for a pseudonym and type."""
        try:
            from .models import StudyConsentRecord, StudyConsentType
            import time

            # Validate consent type strictly
            if isinstance(consent_type, str):
                try:
                    consent_type = StudyConsentType(consent_type)
                except ValueError:
                    valid_types = [e.value for e in StudyConsentType]
                    logger.error(f"Invalid study consent type '{consent_type}'. Valid: {valid_types}")
                    return False

            # Small delay to ensure different timestamp
            time.sleep(0.001)

            # Create withdrawal record
            withdrawal_time = datetime.utcnow()
            withdrawal = StudyConsentRecord(
                pseudonym_id=pseudonym_id,
                consent_type=consent_type.value,
                granted=False,
                version="withdrawal",
                granted_at=withdrawal_time,
                revoked_at=withdrawal_time,
            )
            self.session.add(withdrawal)
            self.session.flush()
            return True
        except Exception as e:
            logger.error(f"Error withdrawing consent for pseudonym {pseudonym_id}, type {consent_type}: {e}")
            return False

    def check_consent(self, pseudonym_id: UUID, consent_type: StudyConsentType) -> bool:
        """Check if pseudonym has given consent for a specific type."""
        try:
            latest_consent = self.get_by_pseudonym_and_type(pseudonym_id, consent_type)
            # Consent is valid if the latest record shows granted=True and not revoked
            return (
                latest_consent is not None
                and latest_consent.granted
                and latest_consent.revoked_at is None
            )
        except Exception as e:
            logger.error(f"Error checking consent for pseudonym {pseudonym_id}, type {consent_type}: {e}")
            return False

    def get_by_id(self, consent_id: UUID) -> StudyConsentRecord | None:
        """Get study consent record by ID."""
        try:
            from .models import StudyConsentRecord
            
            return (
                self.session.query(StudyConsentRecord)
                .filter(StudyConsentRecord.consent_id == consent_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting study consent by ID {consent_id}: {e}")
            return None

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> int:
        """Delete all consent records for a pseudonym."""
        try:
            from .models import StudyConsentRecord
            
            count = (
                self.session.query(StudyConsentRecord)
                .filter(StudyConsentRecord.pseudonym_id == pseudonym_id)
                .count()
            )
            self.session.query(StudyConsentRecord).filter(
                StudyConsentRecord.pseudonym_id == pseudonym_id
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting consent records for pseudonym {pseudonym_id}: {e}")
            return 0


class InteractionLogRepository(BaseRepository):
    """Repository for InteractionLog entities for study participation logging."""

    def __init__(self, session: Session):
        from .models import InteractionLog
        super().__init__(session, InteractionLog)

    def create(self, log_data) -> InteractionLog | None:
        """Create new interaction log."""
        try:
            from .models import InteractionLog
            
            interaction_log = InteractionLog(
                pseudonym_id=log_data.pseudonym_id,
                session_id=log_data.session_id,
                interaction_type=log_data.interaction_type,
                prompt=getattr(log_data, 'prompt', None),
                response=getattr(log_data, 'response', None),
                model_used=log_data.model_used,
                parameters=log_data.parameters,
                token_usage=getattr(log_data, 'token_usage', None),
                latency_ms=log_data.latency_ms,
            )
            self.session.add(interaction_log)
            self.session.flush()
            return interaction_log
        except Exception as e:
            logger.error(f"Error creating interaction log: {e}")
            return None

    def update(self, log_id: UUID, update_data: dict) -> InteractionLog | None:
        """Update interaction log."""
        try:
            from .models import InteractionLog
            
            interaction_log = (
                self.session.query(InteractionLog)
                .filter(InteractionLog.log_id == log_id)
                .first()
            )
            if not interaction_log:
                return None

            for key, value in update_data.items():
                if hasattr(interaction_log, key):
                    setattr(interaction_log, key, value)

            self.session.flush()
            return interaction_log
        except Exception as e:
            logger.error(f"Error updating interaction log {log_id}: {e}")
            return None

    def get_by_id(self, log_id: UUID) -> InteractionLog | None:
        """Get interaction log by ID."""
        try:
            from .models import InteractionLog
            
            return (
                self.session.query(InteractionLog)
                .filter(InteractionLog.log_id == log_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting interaction log by ID {log_id}: {e}")
            return None

    def get_by_session(self, session_id: UUID) -> list[InteractionLog]:
        """Get all interaction logs for a session in chronological order."""
        try:
            from .models import InteractionLog
            
            return (
                self.session.query(InteractionLog)
                .filter(InteractionLog.session_id == session_id)
                .order_by(asc(InteractionLog.timestamp))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting interaction logs for session {session_id}: {e}")
            return []

    def get_by_pseudonym(self, pseudonym_id: UUID, limit: int | None = None) -> list[InteractionLog]:
        """Get all interaction logs for a pseudonym in chronological order."""
        try:
            from .models import InteractionLog
            
            query = (
                self.session.query(InteractionLog)
                .filter(InteractionLog.pseudonym_id == pseudonym_id)
                .order_by(desc(InteractionLog.timestamp))
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error getting interaction logs for pseudonym {pseudonym_id}: {e}")
            return []

    def get_filtered(
        self,
        pseudonym_id: UUID | None = None,
        session_id: UUID | None = None,
        interaction_types: list[str] | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[InteractionLog]:
        """Get filtered interaction logs."""
        try:
            from .models import InteractionLog
            
            query = self.session.query(InteractionLog)

            if pseudonym_id:
                query = query.filter(InteractionLog.pseudonym_id == pseudonym_id)
            if session_id:
                query = query.filter(InteractionLog.session_id == session_id)
            if interaction_types:
                query = query.filter(InteractionLog.interaction_type.in_(interaction_types))
            if start_date:
                query = query.filter(InteractionLog.timestamp >= start_date)
            if end_date:
                query = query.filter(InteractionLog.timestamp <= end_date)

            return query.order_by(asc(InteractionLog.timestamp)).all()
        except Exception as e:
            logger.error(f"Error getting filtered interaction logs: {e}")
            return []

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> int:
        """Delete all interaction logs for a pseudonym (GDPR compliance)."""
        try:
            from .models import InteractionLog
            
            deleted_count = (
                self.session.query(InteractionLog)
                .filter(InteractionLog.pseudonym_id == pseudonym_id)
                .delete()
            )
            self.session.flush()
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting interaction logs for pseudonym {pseudonym_id}: {e}")
            return 0

    def delete_by_session(self, session_id: UUID) -> int:
        """Delete all interaction logs for a session."""
        try:
            from .models import InteractionLog
            
            deleted_count = (
                self.session.query(InteractionLog)
                .filter(InteractionLog.session_id == session_id)
                .delete()
            )
            self.session.flush()
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting interaction logs for session {session_id}: {e}")
            return 0

    def delete_older_than(self, cutoff_date: datetime) -> int:
        """Delete interaction logs older than cutoff date."""
        try:
            from .models import InteractionLog
            
            count = (
                self.session.query(InteractionLog)
                .filter(InteractionLog.timestamp < cutoff_date)
                .count()
            )
            self.session.query(InteractionLog).filter(
                InteractionLog.timestamp < cutoff_date
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting old interaction logs: {e}")
            return 0

    def get_interaction_count_by_type(
        self, pseudonym_id: UUID | None = None, start_date: datetime | None = None
    ) -> dict[str, int]:
        """Get count of interactions by type."""
        try:
            from .models import InteractionLog
            from sqlalchemy import func
            
            query = self.session.query(
                InteractionLog.interaction_type, func.count(InteractionLog.log_id)
            )

            if pseudonym_id:
                query = query.filter(InteractionLog.pseudonym_id == pseudonym_id)
            if start_date:
                query = query.filter(InteractionLog.timestamp >= start_date)

            results = query.group_by(InteractionLog.interaction_type).all()
            return {interaction_type: count for interaction_type, count in results}
        except Exception as e:
            logger.error(f"Error getting interaction count by type: {e}")
            return {}

class PseudonymMappingRepository(BaseRepository):
    """Repository for PseudonymMapping entities with secure access controls."""

    def __init__(self, session: Session):
        super().__init__(session, PseudonymMapping)

    def create(self, mapping_data: PseudonymMappingCreate) -> PseudonymMapping | None:
        """Create a new pseudonym mapping."""
        try:
            mapping = PseudonymMapping(
                user_id=mapping_data.user_id,
                pseudonym_id=mapping_data.pseudonym_id,
                created_by=mapping_data.created_by,
                access_level=mapping_data.access_level,
            )
            self.session.add(mapping)
            self.session.flush()
            return mapping
        except Exception as e:
            logger.error(f"Error creating pseudonym mapping: {e}")
            return None

    def get_by_user_id(self, user_id: UUID) -> PseudonymMapping | None:
        """Get pseudonym mapping by user ID."""
        try:
            return (
                self.session.query(PseudonymMapping)
                .filter(PseudonymMapping.user_id == user_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting pseudonym mapping by user ID {user_id}: {e}")
            return None

    def get_by_pseudonym_id(self, pseudonym_id: UUID) -> PseudonymMapping | None:
        """Get pseudonym mapping by pseudonym ID."""
        try:
            return (
                self.session.query(PseudonymMapping)
                .filter(PseudonymMapping.pseudonym_id == pseudonym_id)
                .first()
            )
        except Exception as e:
            logger.error(f"Error getting pseudonym mapping by pseudonym ID {pseudonym_id}: {e}")
            return None

    def delete_by_user_id(self, user_id: UUID) -> bool:
        """Delete pseudonym mapping by user ID."""
        try:
            mapping = self.get_by_user_id(user_id)
            if mapping:
                self.session.delete(mapping)
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting pseudonym mapping by user ID {user_id}: {e}")
            return False

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> bool:
        """Delete pseudonym mapping by pseudonym ID."""
        try:
            mapping = self.get_by_pseudonym_id(pseudonym_id)
            if mapping:
                self.session.delete(mapping)
                self.session.flush()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting pseudonym mapping by pseudonym ID {pseudonym_id}: {e}")
            return False


class StudySurveyResponseRepository(BaseRepository):
    """Repository for StudySurveyResponse entities."""

    def __init__(self, session: Session):
        super().__init__(session, StudySurveyResponse)

    def get_by_pseudonym(self, pseudonym_id: UUID) -> list[StudySurveyResponse]:
        """Get all survey responses for a pseudonym."""
        try:
            return (
                self.session.query(StudySurveyResponse)
                .filter(StudySurveyResponse.pseudonym_id == pseudonym_id)
                .order_by(desc(StudySurveyResponse.completed_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting survey responses for pseudonym {pseudonym_id}: {e}")
            return []

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> int:
        """Delete all survey responses for a pseudonym."""
        try:
            count = (
                self.session.query(StudySurveyResponse)
                .filter(StudySurveyResponse.pseudonym_id == pseudonym_id)
                .count()
            )
            self.session.query(StudySurveyResponse).filter(
                StudySurveyResponse.pseudonym_id == pseudonym_id
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting survey responses for pseudonym {pseudonym_id}: {e}")
            return 0


class ChatMessageRepository(BaseRepository):
    """Repository for ChatMessage entities."""

    def __init__(self, session: Session):
        super().__init__(session, ChatMessage)

    def get_by_pseudonym(self, pseudonym_id: UUID) -> list[ChatMessage]:
        """Get all chat messages for a pseudonym."""
        try:
            return (
                self.session.query(ChatMessage)
                .filter(ChatMessage.pseudonym_id == pseudonym_id)
                .order_by(desc(ChatMessage.timestamp))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting chat messages for pseudonym {pseudonym_id}: {e}")
            return []

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> int:
        """Delete all chat messages for a pseudonym."""
        try:
            count = (
                self.session.query(ChatMessage)
                .filter(ChatMessage.pseudonym_id == pseudonym_id)
                .count()
            )
            self.session.query(ChatMessage).filter(
                ChatMessage.pseudonym_id == pseudonym_id
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting chat messages for pseudonym {pseudonym_id}: {e}")
            return 0


class StudyPALDDataRepository(BaseRepository):
    """Repository for StudyPALDData entities."""

    def __init__(self, session: Session):
        super().__init__(session, StudyPALDData)

    def get_by_pseudonym(self, pseudonym_id: UUID) -> list[StudyPALDData]:
        """Get all PALD data for a pseudonym."""
        try:
            return (
                self.session.query(StudyPALDData)
                .filter(StudyPALDData.pseudonym_id == pseudonym_id)
                .order_by(desc(StudyPALDData.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting PALD data for pseudonym {pseudonym_id}: {e}")
            return []

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> int:
        """Delete all PALD data for a pseudonym."""
        try:
            count = (
                self.session.query(StudyPALDData)
                .filter(StudyPALDData.pseudonym_id == pseudonym_id)
                .count()
            )
            self.session.query(StudyPALDData).filter(
                StudyPALDData.pseudonym_id == pseudonym_id
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting PALD data for pseudonym {pseudonym_id}: {e}")
            return 0


class GeneratedImageRepository(BaseRepository):
    """Repository for GeneratedImage entities."""

    def __init__(self, session: Session):
        super().__init__(session, GeneratedImage)

    def get_by_pseudonym(self, pseudonym_id: UUID) -> list[GeneratedImage]:
        """Get all generated images for a pseudonym."""
        try:
            return (
                self.session.query(GeneratedImage)
                .filter(GeneratedImage.pseudonym_id == pseudonym_id)
                .order_by(desc(GeneratedImage.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting generated images for pseudonym {pseudonym_id}: {e}")
            return []

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> int:
        """Delete all generated images for a pseudonym."""
        try:
            count = (
                self.session.query(GeneratedImage)
                .filter(GeneratedImage.pseudonym_id == pseudonym_id)
                .count()
            )
            self.session.query(GeneratedImage).filter(
                GeneratedImage.pseudonym_id == pseudonym_id
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting generated images for pseudonym {pseudonym_id}: {e}")
            return 0

    def delete_older_than(self, cutoff_date: datetime) -> int:
        """Delete generated images older than cutoff date."""
        try:
            count = (
                self.session.query(GeneratedImage)
                .filter(GeneratedImage.created_at < cutoff_date)
                .count()
            )
            self.session.query(GeneratedImage).filter(
                GeneratedImage.created_at < cutoff_date
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting old generated images: {e}")
            return 0


class FeedbackRecordRepository(BaseRepository):
    """Repository for FeedbackRecord entities."""

    def __init__(self, session: Session):
        super().__init__(session, FeedbackRecord)

    def get_by_pseudonym(self, pseudonym_id: UUID) -> list[FeedbackRecord]:
        """Get all feedback records for a pseudonym."""
        try:
            return (
                self.session.query(FeedbackRecord)
                .filter(FeedbackRecord.pseudonym_id == pseudonym_id)
                .order_by(desc(FeedbackRecord.created_at))
                .all()
            )
        except Exception as e:
            logger.error(f"Error getting feedback records for pseudonym {pseudonym_id}: {e}")
            return []

    def delete_by_pseudonym(self, pseudonym_id: UUID) -> int:
        """Delete all feedback records for a pseudonym."""
        try:
            count = (
                self.session.query(FeedbackRecord)
                .filter(FeedbackRecord.pseudonym_id == pseudonym_id)
                .count()
            )
            self.session.query(FeedbackRecord).filter(
                FeedbackRecord.pseudonym_id == pseudonym_id
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting feedback records for pseudonym {pseudonym_id}: {e}")
            return 0

    def delete_older_than(self, cutoff_date: datetime) -> int:
        """Delete feedback records older than cutoff date."""
        try:
            count = (
                self.session.query(FeedbackRecord)
                .filter(FeedbackRecord.created_at < cutoff_date)
                .count()
            )
            self.session.query(FeedbackRecord).filter(
                FeedbackRecord.created_at < cutoff_date
            ).delete()
            self.session.flush()
            return count
        except Exception as e:
            logger.error(f"Error deleting old feedback records: {e}")
            return 0