"""
Database models for GITTE system.
Defines all SQLAlchemy models for users, consent, PALD, audit logs, and federated learning.
"""

from enum import Enum
from uuid import uuid4
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Float,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import declarative_base, relationship, validates
from sqlalchemy.types import TypeDecorator

Base = declarative_base()


# Database-agnostic JSON column type
class JSONColumn(TypeDecorator):
    """JSON column that uses JSONB for PostgreSQL and JSON for other databases."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            return dialect.type_descriptor(JSON())


class UserRole(str, Enum):
    """User role enumeration."""

    ADMIN = "admin"
    PARTICIPANT = "participant"


class ConsentType(str, Enum):
    """Legacy consent type enumeration - DEPRECATED: Use StudyConsentType for new code."""

    DATA_PROCESSING = "data_processing"
    AI_INTERACTION = "ai_interaction"
    IMAGE_GENERATION = "image_generation"
    FEDERATED_LEARNING = "federated_learning"
    ANALYTICS = "analytics"
    INVESTIGATION_PARTICIPATION = "investigation_participation"


class AuditLogStatus(str, Enum):
    """Audit log status enumeration."""

    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    FINALIZED = "finalized"


class User(Base):
    """User model for authentication and role management."""

    __tablename__ = "users"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.PARTICIPANT.value)
    pseudonym = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    consent_records = relationship(
        "ConsentRecord", back_populates="user", cascade="all, delete-orphan"
    )
    pald_data = relationship("PALDData", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    fl_updates = relationship(
        "FederatedLearningUpdate", back_populates="user", cascade="all, delete-orphan"
    )
    # UX Enhancement relationships
    image_processing_results = relationship(
        "ImageProcessingResult", cascade="all, delete-orphan"
    )
    image_corrections = relationship("ImageCorrection", cascade="all, delete-orphan")
    prerequisite_check_results = relationship(
        "PrerequisiteCheckResult", cascade="all, delete-orphan"
    )
    tooltip_interactions = relationship("TooltipInteraction", cascade="all, delete-orphan")
    ux_audit_logs = relationship("UXAuditLog", cascade="all, delete-orphan")

    @validates("role")
    def validate_role(self, key, role):
        """Validate user role."""
        if role not in [r.value for r in UserRole]:
            raise ValueError(f"Invalid role: {role}")
        return role

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class ConsentRecord(Base):
    """Consent record model for GDPR compliance."""

    __tablename__ = "consent_records"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    consent_type = Column(String(100), nullable=False)
    consent_given = Column(Boolean, nullable=False)
    consent_version = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())
    consent_metadata = Column(JSONColumn, nullable=True)
    withdrawn_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="consent_records")

    # Indexes
    __table_args__ = (
        Index("idx_consent_user_type", "user_id", "consent_type"),
        Index("idx_consent_timestamp", "timestamp"),
    )

    @validates("consent_type")
    def validate_consent_type(self, key, consent_type):
        """Validate consent type."""
        if consent_type not in [c.value for c in ConsentType]:
            raise ValueError(f"Invalid consent type: {consent_type}")
        return consent_type

    def __repr__(self):
        return f"<ConsentRecord(id={self.id}, user_id={self.user_id}, type={self.consent_type}, given={self.consent_given})>"


class PALDSchemaVersion(Base):
    """PALD schema version model for schema evolution tracking."""

    __tablename__ = "pald_schema_versions"

    version = Column(String(50), primary_key=True)
    schema_content = Column(JSONColumn, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    is_active = Column(Boolean, nullable=False, default=False)
    migration_notes = Column(Text, nullable=True)

    # Relationships
    pald_data = relationship("PALDData", back_populates="schema_version_obj")

    def __repr__(self):
        return f"<PALDSchemaVersion(version={self.version}, is_active={self.is_active})>"


class PALDAttributeCandidate(Base):
    """PALD attribute candidate model for dynamic schema evolution."""

    __tablename__ = "pald_attribute_candidates"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    attribute_name = Column(String(255), nullable=False, index=True)
    attribute_category = Column(String(100), nullable=True)
    mention_count = Column(Integer, nullable=False, default=1)
    first_detected = Column(DateTime, nullable=False, default=func.now())
    last_mentioned = Column(DateTime, nullable=False, default=func.now())
    threshold_reached = Column(Boolean, nullable=False, default=False)
    added_to_schema = Column(Boolean, nullable=False, default=False)
    schema_version_added = Column(String(50), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_attribute_name", "attribute_name"),
        Index("idx_attribute_threshold", "threshold_reached"),
        Index("idx_attribute_added", "added_to_schema"),
    )

    def __repr__(self):
        return f"<PALDAttributeCandidate(id={self.id}, name={self.attribute_name}, count={self.mention_count})>"


class PALDData(Base):
    """PALD data model for pedagogical agent level of design information."""

    __tablename__ = "pald_data"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    pald_content = Column(JSONColumn, nullable=False)
    schema_version = Column(String(50), ForeignKey("pald_schema_versions.version"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    is_validated = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSONColumn, nullable=True)
    bias_detected = Column(Boolean, default=False)
    analysis_type = Column(String(50), nullable=True)
    issues = Column(JSON, nullable=True)


    # Relationships
    user = relationship("User", back_populates="pald_data")
    schema_version_obj = relationship("PALDSchemaVersion", back_populates="pald_data")

    # Indexes
    __table_args__ = (
        Index("idx_pald_user", "user_id"),
        Index("idx_pald_schema_version", "schema_version"),
        Index("idx_pald_validated", "is_validated"),
    )

    def __repr__(self):
        return f"<PALDData(id={self.id}, user_id={self.user_id}, schema_version={self.schema_version})>"


class AuditLog(Base):
    """Audit log model for comprehensive AI interaction logging."""

    __tablename__ = "audit_logs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id = Column(String(255), nullable=False, index=True)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    operation = Column(String(100), nullable=False)
    model_used = Column(String(100), nullable=True)
    input_data = Column(JSONColumn, nullable=True)
    output_data = Column(JSONColumn, nullable=True)
    parameters = Column(JSONColumn, nullable=True)
    token_usage = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    parent_log_id = Column(PostgresUUID(as_uuid=True), ForeignKey("audit_logs.id"), nullable=True)
    status = Column(String(50), nullable=False, default=AuditLogStatus.INITIALIZED.value)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    finalized_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    parent_log = relationship("AuditLog", remote_side=[id], backref="child_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_request_id", "request_id"),
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_operation", "operation"),
        Index("idx_audit_status", "status"),
        Index("idx_audit_created_at", "created_at"),
        Index("idx_audit_parent", "parent_log_id"),
    )

    @validates("status")
    def validate_status(self, key, status):
        """Validate audit log status."""
        if status not in [s.value for s in AuditLogStatus]:
            raise ValueError(f"Invalid status: {status}")
        return status

    def __repr__(self):
        return f"<AuditLog(id={self.id}, request_id={self.request_id}, operation={self.operation}, status={self.status})>"


class FederatedLearningUpdate(Base):
    """Federated learning update model for FL client submissions."""

    __tablename__ = "fl_updates"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    update_data = Column(LargeBinary, nullable=False)
    model_version = Column(String(50), nullable=False)
    aggregation_round = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, nullable=False, default=func.now())
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime, nullable=True)
    update_size_bytes = Column(Integer, nullable=True)
    privacy_budget_used = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="fl_updates")

    # Indexes
    __table_args__ = (
        Index("idx_fl_user", "user_id"),
        Index("idx_fl_model_version", "model_version"),
        Index("idx_fl_round", "aggregation_round"),
        Index("idx_fl_processed", "processed"),
        Index("idx_fl_submitted_at", "submitted_at"),
    )

    def __repr__(self):
        return f"<FederatedLearningUpdate(id={self.id}, user_id={self.user_id}, model_version={self.model_version}, processed={self.processed})>"


# Additional utility tables for system management


class SystemMetadata(Base):
    """System metadata for tracking database version and configuration."""

    __tablename__ = "system_metadata"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SystemMetadata(key={self.key}, value={self.value})>"


# UX Enhancement Models


class ImageProcessingResultStatus(str, Enum):
    """Image processing result status enumeration."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CORRECTED = "corrected"


class ImageQualityIssue(str, Enum):
    """Image quality issue enumeration."""

    NO_PERSON_DETECTED = "no_person_detected"
    MULTIPLE_PEOPLE_DETECTED = "multiple_people_detected"
    WRONG_SUBJECT_TYPE = "wrong_subject_type"
    POOR_QUALITY = "poor_quality"
    BLUR_DETECTED = "blur_detected"
    NOISE_DETECTED = "noise_detected"
    CORRUPTION_DETECTED = "corruption_detected"


class UserCorrectionAction(str, Enum):
    """User correction action enumeration."""

    ACCEPT_PROCESSED = "accept_processed"
    ADJUST_CROP = "adjust_crop"
    USE_ORIGINAL = "use_original"
    MARK_GARBAGE = "mark_garbage"
    REGENERATE = "regenerate"


class ImageProcessingResult(Base):
    """Image processing result model for isolation and quality analysis."""

    __tablename__ = "image_processing_results"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_image_path = Column(String(500), nullable=False)
    processed_image_path = Column(String(500), nullable=True)
    processing_method = Column(String(100), nullable=False)  # rembg, opencv, manual
    status = Column(String(50), nullable=False, default=ImageProcessingResultStatus.PENDING.value)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    processing_time_ms = Column(Integer, nullable=True)
    quality_issues = Column(JSONColumn, nullable=True)  # List of detected issues
    person_count = Column(Integer, nullable=True)
    quality_score = Column(Integer, nullable=True)  # 0-100
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", overlaps="image_processing_results")
    corrections = relationship(
        "ImageCorrection", back_populates="processing_result", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_image_processing_user", "user_id"),
        Index("idx_image_processing_status", "status"),
        Index("idx_image_processing_created", "created_at"),
        Index("idx_image_processing_method", "processing_method"),
    )

    @validates("status")
    def validate_status(self, key, status):
        """Validate processing status."""
        if status not in [s.value for s in ImageProcessingResultStatus]:
            raise ValueError(f"Invalid status: {status}")
        return status

    def __repr__(self):
        return f"<ImageProcessingResult(id={self.id}, user_id={self.user_id}, status={self.status})>"


class ImageCorrection(Base):
    """Image correction model for user manual corrections."""

    __tablename__ = "image_corrections"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    processing_result_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("image_processing_results.id"), nullable=False
    )
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    correction_action = Column(String(50), nullable=False)
    crop_coordinates = Column(JSONColumn, nullable=True)  # {left, top, right, bottom}
    rejection_reason = Column(String(200), nullable=True)
    suggested_modifications = Column(Text, nullable=True)
    final_image_path = Column(String(500), nullable=True)
    correction_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    processing_result = relationship("ImageProcessingResult", back_populates="corrections")
    user = relationship("User", overlaps="image_corrections")

    # Indexes
    __table_args__ = (
        Index("idx_image_correction_result", "processing_result_id"),
        Index("idx_image_correction_user", "user_id"),
        Index("idx_image_correction_action", "correction_action"),
        Index("idx_image_correction_created", "created_at"),
    )

    @validates("correction_action")
    def validate_correction_action(self, key, action):
        """Validate correction action."""
        if action not in [a.value for a in UserCorrectionAction]:
            raise ValueError(f"Invalid correction action: {action}")
        return action

    def __repr__(self):
        return f"<ImageCorrection(id={self.id}, action={self.correction_action})>"


class PrerequisiteCheckResultStatus(str, Enum):
    """Prerequisite check result status enumeration."""

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    UNKNOWN = "unknown"


class PrerequisiteCheckType(str, Enum):
    """Prerequisite check type enumeration."""

    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class PrerequisiteCheckResult(Base):
    """Prerequisite check result model for system validation tracking."""

    __tablename__ = "prerequisite_check_results"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    operation_name = Column(String(100), nullable=False)
    checker_name = Column(String(100), nullable=False)
    check_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    resolution_steps = Column(JSONColumn, nullable=True)  # List of resolution steps
    check_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Integer, nullable=True)  # 0-100
    cached = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    user = relationship("User", overlaps="prerequisite_check_results")

    # Indexes
    __table_args__ = (
        Index("idx_prerequisite_user", "user_id"),
        Index("idx_prerequisite_operation", "operation_name"),
        Index("idx_prerequisite_checker", "checker_name"),
        Index("idx_prerequisite_status", "status"),
        Index("idx_prerequisite_type", "check_type"),
        Index("idx_prerequisite_created", "created_at"),
        Index("idx_prerequisite_operation_user", "operation_name", "user_id"),
    )

    @validates("status")
    def validate_status(self, key, status):
        """Validate check status."""
        if status not in [s.value for s in PrerequisiteCheckResultStatus]:
            raise ValueError(f"Invalid status: {status}")
        return status

    @validates("check_type")
    def validate_check_type(self, key, check_type):
        """Validate check type."""
        if check_type not in [t.value for t in PrerequisiteCheckType]:
            raise ValueError(f"Invalid check type: {check_type}")
        return check_type

    def __repr__(self):
        return f"<PrerequisiteCheckResult(id={self.id}, checker={self.checker_name}, status={self.status})>"


class TooltipInteractionType(str, Enum):
    """Tooltip interaction type enumeration."""

    HOVER = "hover"
    CLICK = "click"
    FOCUS = "focus"
    DISMISS = "dismiss"
    ACTION_TAKEN = "action_taken"


class TooltipInteraction(Base):
    """Tooltip interaction model for tracking user help system usage."""

    __tablename__ = "tooltip_interactions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True)
    element_id = Column(String(200), nullable=False)
    tooltip_content_id = Column(String(200), nullable=True)
    interaction_type = Column(String(50), nullable=False)
    page_context = Column(String(200), nullable=True)
    tooltip_title = Column(String(500), nullable=True)
    tooltip_description = Column(Text, nullable=True)
    display_time_ms = Column(Integer, nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    user = relationship("User", overlaps="tooltip_interactions")

    # Indexes
    __table_args__ = (
        Index("idx_tooltip_user", "user_id"),
        Index("idx_tooltip_element", "element_id"),
        Index("idx_tooltip_interaction", "interaction_type"),
        Index("idx_tooltip_session", "session_id"),
        Index("idx_tooltip_created", "created_at"),
        Index("idx_tooltip_context", "page_context"),
    )

    @validates("interaction_type")
    def validate_interaction_type(self, key, interaction_type):
        """Validate interaction type."""
        if interaction_type not in [t.value for t in TooltipInteractionType]:
            raise ValueError(f"Invalid interaction type: {interaction_type}")
        return interaction_type

    def __repr__(self):
        return f"<TooltipInteraction(id={self.id}, element={self.element_id}, type={self.interaction_type})>"


class UXEventType(str, Enum):
    """UX event type enumeration."""

    IMAGE_CORRECTION_STARTED = "image_correction_started"
    IMAGE_CORRECTION_COMPLETED = "image_correction_completed"
    PREREQUISITE_CHECK_TRIGGERED = "prerequisite_check_triggered"
    PREREQUISITE_RESOLUTION_ATTEMPTED = "prerequisite_resolution_attempted"
    TOOLTIP_HELP_ACCESSED = "tooltip_help_accessed"
    USER_WORKFLOW_BLOCKED = "user_workflow_blocked"
    USER_WORKFLOW_RESUMED = "user_workflow_resumed"
    ACCESSIBILITY_FEATURE_USED = "accessibility_feature_used"


class UXAuditLog(Base):
    """UX audit log model for tracking user experience events."""

    __tablename__ = "ux_audit_logs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(String(255), nullable=True)
    event_type = Column(String(100), nullable=False)
    event_context = Column(String(200), nullable=True)
    event_data = Column(JSONColumn, nullable=True)
    workflow_step = Column(String(100), nullable=True)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    user = relationship("User", overlaps="ux_audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_ux_audit_user", "user_id"),
        Index("idx_ux_audit_event", "event_type"),
        Index("idx_ux_audit_session", "session_id"),
        Index("idx_ux_audit_context", "event_context"),
        Index("idx_ux_audit_created", "created_at"),
        Index("idx_ux_audit_success", "success"),
        Index("idx_ux_audit_workflow", "workflow_step"),
    )

    @validates("event_type")
    def validate_event_type(self, key, event_type):
        """Validate event type."""
        if event_type not in [t.value for t in UXEventType]:
            raise ValueError(f"Invalid event type: {event_type}")
        return event_type

    def __repr__(self):
        return f"<UXAuditLog(id={self.id}, event={self.event_type}, success={self.success})>"

# === STUDY PARTICIPATION MODELS ===

class Pseudonym(Base):
    """Pseudonym model for study participation identity management.
    
    Note: This model does NOT have a direct foreign key to users table
    to ensure privacy separation. The mapping is handled separately
    with appropriate access controls.
    """

    __tablename__ = "pseudonyms"

    pseudonym_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_text = Column(String(255), unique=True, nullable=False, index=True)
    pseudonym_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships - NO direct relationship to User model for privacy
    study_consent_records = relationship(
        "StudyConsentRecord", back_populates="pseudonym", cascade="all, delete-orphan"
    )
    study_survey_responses = relationship(
        "StudySurveyResponse", back_populates="pseudonym", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="pseudonym", cascade="all, delete-orphan"
    )
    study_pald_data = relationship(
        "StudyPALDData", back_populates="pseudonym", cascade="all, delete-orphan"
    )
    generated_images = relationship(
        "GeneratedImage", back_populates="pseudonym", cascade="all, delete-orphan"
    )
    feedback_records = relationship(
        "FeedbackRecord", back_populates="pseudonym", cascade="all, delete-orphan"
    )
    interaction_logs = relationship(
        "InteractionLog", back_populates="pseudonym", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_pseudonym_text", "pseudonym_text"),
        Index("idx_pseudonym_active", "is_active"),
        Index("idx_pseudonym_hash", "pseudonym_hash"),
    )

    def __repr__(self):
        return f"<Pseudonym(pseudonym_id={self.pseudonym_id}, pseudonym_text={self.pseudonym_text}, is_active={self.is_active})>"


class PseudonymMapping(Base):
    """Pseudonym mapping model for secure user-pseudonym association.
    
    This table provides the mapping between user authentication and pseudonyms
    with appropriate access controls. It should be accessed only by authorized
    admin functions and never exposed in research data exports.
    """

    __tablename__ = "pseudonym_mappings"

    mapping_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    pseudonym_id = Column(PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    created_by = Column(String(100), nullable=False)  # Admin user who created the mapping
    access_level = Column(String(50), nullable=False, default="admin_only")  # Access control level

    # Relationships
    user = relationship("User")
    pseudonym = relationship("Pseudonym")

    # Indexes
    __table_args__ = (
        Index("idx_pseudonym_mapping_user", "user_id"),
        Index("idx_pseudonym_mapping_pseudonym", "pseudonym_id"),
        Index("idx_pseudonym_mapping_created", "created_at"),
        # Ensure one-to-one mapping between user and pseudonym
        Index("idx_pseudonym_mapping_unique_user", "user_id", unique=True),
        Index("idx_pseudonym_mapping_unique_pseudonym", "pseudonym_id", unique=True),
    )

    def __repr__(self):
        return f"<PseudonymMapping(mapping_id={self.mapping_id}, access_level={self.access_level})>"


class StudyConsentType(str, Enum):
    """Study consent type enumeration."""

    DATA_PROTECTION = "data_protection"
    AI_INTERACTION = "ai_interaction"
    STUDY_PARTICIPATION = "study_participation"
    IMAGE_GENERATION = "image_generation"


class StudyConsentRecord(Base):
    """Study consent record model for research participation consent."""

    __tablename__ = "study_consent_records"

    consent_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False
    )
    consent_type = Column(String(100), nullable=False)
    granted = Column(Boolean, nullable=False)
    version = Column(String(20), nullable=False)
    granted_at = Column(DateTime, nullable=False, default=func.now())
    revoked_at = Column(DateTime, nullable=True)

    # Relationships
    pseudonym = relationship("Pseudonym", back_populates="study_consent_records")

    # Indexes
    __table_args__ = (
        Index("idx_study_consent_pseudonym_type", "pseudonym_id", "consent_type"),
        Index("idx_study_consent_granted_at", "granted_at"),
    )

    @validates("consent_type")
    def validate_consent_type(self, key, consent_type):
        """Validate study consent type."""
        if consent_type not in [c.value for c in StudyConsentType]:
            raise ValueError(f"Invalid study consent type: {consent_type}")
        return consent_type

    def __repr__(self):
        return f"<StudyConsentRecord(consent_id={self.consent_id}, pseudonym_id={self.pseudonym_id}, type={self.consent_type}, granted={self.granted})>"


class StudySurveyResponse(Base):
    """Study survey response model for dynamic survey data collection."""

    __tablename__ = "study_survey_responses"

    response_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False
    )
    survey_version = Column(String(20), nullable=False)
    responses = Column(JSONColumn, nullable=False)
    completed_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    pseudonym = relationship("Pseudonym", back_populates="study_survey_responses")

    # Indexes
    __table_args__ = (
        Index("idx_study_survey_pseudonym", "pseudonym_id"),
        Index("idx_study_survey_version", "survey_version"),
        Index("idx_study_survey_completed", "completed_at"),
    )

    def __repr__(self):
        return f"<StudySurveyResponse(response_id={self.response_id}, pseudonym_id={self.pseudonym_id}, survey_version={self.survey_version})>"


class ChatMessageType(str, Enum):
    """Chat message type enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(Base):
    """Chat message model for study participation chat interactions."""

    __tablename__ = "chat_messages"

    message_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False
    )
    session_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    message_type = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    pald_data = Column(JSONColumn, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    pseudonym = relationship("Pseudonym", back_populates="chat_messages")

    # Indexes
    __table_args__ = (
        Index("idx_chat_pseudonym", "pseudonym_id"),
        Index("idx_chat_session", "session_id"),
        Index("idx_chat_timestamp", "timestamp"),
        Index("idx_chat_type", "message_type"),
    )

    @validates("message_type")
    def validate_message_type(self, key, message_type):
        """Validate chat message type."""
        if message_type not in [t.value for t in ChatMessageType]:
            raise ValueError(f"Invalid message type: {message_type}")
        return message_type

    def __repr__(self):
        return f"<ChatMessage(message_id={self.message_id}, pseudonym_id={self.pseudonym_id}, session_id={self.session_id}, type={self.message_type})>"


class StudyPALDType(str, Enum):
    """Study PALD type enumeration."""

    INPUT = "input"
    DESCRIPTION = "description"
    FEEDBACK = "feedback"


class StudyPALDData(Base):
    """Study PALD data model for research-specific PALD processing."""

    __tablename__ = "study_pald_data"

    pald_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False
    )
    session_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    pald_content = Column(JSONColumn, nullable=False)
    pald_type = Column(String(20), nullable=False)
    consistency_score = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    pseudonym = relationship("Pseudonym", back_populates="study_pald_data")

    # Indexes
    __table_args__ = (
        Index("idx_study_pald_pseudonym", "pseudonym_id"),
        Index("idx_study_pald_session", "session_id"),
        Index("idx_study_pald_type", "pald_type"),
        Index("idx_study_pald_created", "created_at"),
    )

    @validates("pald_type")
    def validate_pald_type(self, key, pald_type):
        """Validate study PALD type."""
        if pald_type not in [t.value for t in StudyPALDType]:
            raise ValueError(f"Invalid study PALD type: {pald_type}")
        return pald_type

    def __repr__(self):
        return f"<StudyPALDData(pald_id={self.pald_id}, pseudonym_id={self.pseudonym_id}, session_id={self.session_id}, type={self.pald_type})>"


class GeneratedImage(Base):
    """Generated image model for study participation image generation."""

    __tablename__ = "generated_images"

    image_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False
    )
    session_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    prompt = Column(Text, nullable=False)
    pald_source_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("study_pald_data.pald_id"), nullable=True
    )
    generation_parameters = Column(JSONColumn, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    pseudonym = relationship("Pseudonym", back_populates="generated_images")
    pald_source = relationship("StudyPALDData")

    # Indexes
    __table_args__ = (
        Index("idx_generated_image_pseudonym", "pseudonym_id"),
        Index("idx_generated_image_session", "session_id"),
        Index("idx_generated_image_created", "created_at"),
        Index("idx_generated_image_pald_source", "pald_source_id"),
    )

    def __repr__(self):
        return f"<GeneratedImage(image_id={self.image_id}, pseudonym_id={self.pseudonym_id}, session_id={self.session_id})>"


class FeedbackRecord(Base):
    """Feedback record model for study participation feedback collection."""

    __tablename__ = "feedback_records"

    feedback_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False
    )
    session_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    image_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("generated_images.image_id"), nullable=True
    )
    feedback_text = Column(Text, nullable=False)
    feedback_pald = Column(JSONColumn, nullable=True)
    round_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    pseudonym = relationship("Pseudonym", back_populates="feedback_records")
    image = relationship("GeneratedImage")

    # Indexes
    __table_args__ = (
        Index("idx_feedback_pseudonym", "pseudonym_id"),
        Index("idx_feedback_session", "session_id"),
        Index("idx_feedback_image", "image_id"),
        Index("idx_feedback_round", "round_number"),
        Index("idx_feedback_created", "created_at"),
    )

    def __repr__(self):
        return f"<FeedbackRecord(feedback_id={self.feedback_id}, pseudonym_id={self.pseudonym_id}, session_id={self.session_id}, round={self.round_number})>"


class InteractionLog(Base):
    """Interaction log model for comprehensive study participation logging."""

    __tablename__ = "interaction_logs"

    log_id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    pseudonym_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("pseudonyms.pseudonym_id"), nullable=False
    )
    session_id = Column(PostgresUUID(as_uuid=True), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    model_used = Column(String(100), nullable=False)
    parameters = Column(JSONColumn, nullable=False)
    token_usage = Column(JSONColumn, nullable=True)
    latency_ms = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    pseudonym = relationship("Pseudonym", back_populates="interaction_logs")

    # Indexes
    __table_args__ = (
        Index("idx_interaction_pseudonym", "pseudonym_id"),
        Index("idx_interaction_session", "session_id"),
        Index("idx_interaction_type", "interaction_type"),
        Index("idx_interaction_model", "model_used"),
        Index("idx_interaction_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<InteractionLog(log_id={self.log_id}, pseudonym_id={self.pseudonym_id}, session_id={self.session_id}, type={self.interaction_type})>"


# === BEGIN PALD ENHANCEMENT (from split_02_src_data_models.py.patch) ===
class BiasAnalysisJobStatus(str, Enum):
    """Bias analysis job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"
    DLQ = "dlq"  # Dead Letter Queue
    TIMEOUT = "timeout"
    PARTIAL = "partial"


class PALDSchemaFieldCandidate(Base):
    """PALD schema field candidate model for schema evolution tracking."""
    __tablename__ = "schema_field_candidates"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    field_name = Column(String(255), nullable=False, index=True)
    field_category = Column(String(100), nullable=True)
    mention_count = Column(Integer, nullable=False, default=1)
    first_detected = Column(DateTime, nullable=False, default=func.now())
    last_mentioned = Column(DateTime, nullable=False, default=func.now())
    threshold_reached = Column(Boolean, nullable=False, default=False)
    added_to_schema = Column(Boolean, nullable=False, default=False)
    schema_version_added = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_schema_field_name", "field_name"),
        Index("idx_schema_field_threshold", "threshold_reached"),
        Index("idx_schema_field_added", "added_to_schema"),
        Index("idx_schema_field_category", "field_category"),
    )

    def __repr__(self):
        return f"<PALDSchemaFieldCandidate(id={self.id}, name={self.field_name}, count={self.mention_count})>"


class PALDProcessingLog(Base):
    """PALD processing log model for tracking processing stages and operations."""
    __tablename__ = "pald_processing_logs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    processing_stage = Column(String(100), nullable=False)  # extraction, validation, bias_analysis, etc.
    operation = Column(String(100), nullable=False)        # field_detection, schema_validation, etc.
    status = Column(String(50), nullable=False)            # started, completed, failed
    start_time = Column(DateTime, nullable=False, default=func.now())
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    details = Column(JSONColumn, nullable=True)            # Stage-specific details
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())

    __table_args__ = (
        Index("idx_pald_log_session", "session_id"),
        Index("idx_pald_log_stage", "processing_stage"),
        Index("idx_pald_log_status", "status"),
        Index("idx_pald_log_created", "created_at"),
    )

    def __repr__(self):
        return f"<PALDProcessingLog(id={self.id}, session={self.session_id}, stage={self.processing_stage})>"


class BiasAnalysisJob(Base):
    """Bias analysis job model for deferred bias analysis processing."""
    __tablename__ = "bias_analysis_jobs"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String(255), nullable=False, index=True)
    pald_data = Column(JSONColumn, nullable=False)           # PALD data to analyze
    analysis_types = Column(JSONColumn, nullable=False)      # List of analysis types to perform
    priority = Column(Integer, nullable=False, default=5)    # 1=highest, 10=lowest
    status = Column(String(50), nullable=False, default=BiasAnalysisJobStatus.PENDING.value)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    scheduled_at = Column(DateTime, nullable=False, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    # Relationships
    results = relationship("BiasAnalysisResult", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_bias_job_session", "session_id"),
        Index("idx_bias_job_status", "status"),
        Index("idx_bias_job_scheduled", "scheduled_at"),
        Index("idx_bias_job_priority", "priority"),
    )

    @validates("status")
    def validate_status(self, key, status):
        """Validate job status."""
        if status not in [s.value for s in BiasAnalysisJobStatus]:
            raise ValueError(f"Invalid status: {status}")
        return status

    def __repr__(self):
        return f"<BiasAnalysisJob(id={self.id}, session={self.session_id}, status={self.status})>"


class BiasAnalysisResult(Base):
    """Bias analysis result model for storing analysis outcomes."""
    __tablename__ = "bias_analysis_results"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("bias_analysis_jobs.id", ondelete="CASCADE"),
        nullable=False
    )
    session_id = Column(String(255), nullable=False, index=True)
    analysis_type = Column(String(100), nullable=False)    # age_shift, gender_conformity, etc.
    bias_detected = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=False)       # 0.0 to 1.0
    bias_indicators = Column(JSONColumn, nullable=True)    # Specific bias indicators found
    analysis_details = Column(JSONColumn, nullable=True)    # Detailed analysis results
    created_at = Column(DateTime, nullable=False, default=func.now())

    # Relationships
    job = relationship("BiasAnalysisJob", back_populates="results")

    __table_args__ = (
        Index("idx_bias_result_job", "job_id"),
        Index("idx_bias_result_session", "session_id"),
        Index("idx_bias_result_type", "analysis_type"),
        Index("idx_bias_result_bias", "bias_detected"),
        Index("idx_bias_result_created", "created_at"),
    )

    def __repr__(self):
        return f"<BiasAnalysisResult(id={self.id}, job_id={self.job_id}, type={self.analysis_type})>"


# === PALD BOUNDARY ENFORCEMENT MODELS ===

class SurveyResponse(Base):
    """Survey response data model for storing user survey data separately from PALD."""
    __tablename__ = "survey_responses"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    survey_data = Column(JSONColumn, nullable=False)
    survey_version = Column(String(50), nullable=False, default="1.0")
    completed_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="survey_responses")
    
    __table_args__ = (
        Index("idx_survey_user", "user_id"),
        Index("idx_survey_completed", "completed_at"),
        Index("idx_survey_version", "survey_version"),
    )
    
    def __repr__(self):
        return f"<SurveyResponse(id={self.id}, user_id={self.user_id}, version={self.survey_version})>"


class OnboardingProgress(Base):
    """Onboarding progress tracking model for workflow state management."""
    __tablename__ = "onboarding_progress"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    current_step = Column(String(100), nullable=False)
    completed_steps = Column(JSONColumn, nullable=False, default=list)
    step_data = Column(JSONColumn, nullable=True)
    progress_percentage = Column(Float, nullable=False, default=0.0)
    started_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="onboarding_progress")
    
    __table_args__ = (
        Index("idx_onboarding_user", "user_id"),
        Index("idx_onboarding_step", "current_step"),
        Index("idx_onboarding_progress", "progress_percentage"),
    )
    
    def __repr__(self):
        return f"<OnboardingProgress(id={self.id}, user_id={self.user_id}, step={self.current_step})>"


class UserPreferences(Base):
    """User preferences model for non-embodiment user settings."""
    __tablename__ = "user_preferences"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    preferences = Column(JSONColumn, nullable=False)
    category = Column(String(100), nullable=False, default="general")
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="user_preferences")
    
    __table_args__ = (
        Index("idx_preferences_user", "user_id"),
        Index("idx_preferences_category", "category"),
        Index("idx_preferences_user_category", "user_id", "category"),
    )
    
    def __repr__(self):
        return f"<UserPreferences(id={self.id}, user_id={self.user_id}, category={self.category})>"


class SchemaVersion(Base):
    """Schema version tracking model for runtime schema management."""
    __tablename__ = "schema_versions"
    
    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    version = Column(String(50), unique=True, nullable=False)
    schema_content = Column(JSONColumn, nullable=False)
    checksum = Column(String(64), nullable=False)
    file_path = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=func.now())
    
    __table_args__ = (
        Index("idx_schema_version", "version"),
        Index("idx_schema_active", "is_active"),
        Index("idx_schema_checksum", "checksum"),
    )
    
    def __repr__(self):
        return f"<SchemaVersion(version={self.version}, active={self.is_active})>"
