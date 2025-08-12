"""
Database models for GITTE system.
Defines all SQLAlchemy models for users, consent, PALD, audit logs, and federated learning.
"""

from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
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
    """Consent type enumeration."""

    DATA_PROCESSING = "data_processing"
    AI_INTERACTION = "ai_interaction"
    IMAGE_GENERATION = "image_generation"
    FEDERATED_LEARNING = "federated_learning"
    ANALYTICS = "analytics"


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
