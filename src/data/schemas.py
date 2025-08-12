"""
Pydantic schemas for data validation and serialization.
Provides validation models for all database entities and API requests/responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import conint, constr


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


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


# User schemas
class UserBase(BaseSchema):
    """Base user schema."""

    username: constr(min_length=3, max_length=255)
    role: UserRole = UserRole.PARTICIPANT


class UserCreate(UserBase):
    """User creation schema."""

    password: constr(min_length=8, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # For development/testing, we'll have more lenient requirements
        # In production, these could be made stricter via configuration
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one digit")
        return v


class UserUpdate(BaseSchema):
    """User update schema."""

    username: constr(min_length=3, max_length=255) | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """User response schema."""

    id: UUID
    pseudonym: str
    created_at: datetime
    updated_at: datetime
    is_active: bool


class UserLogin(BaseSchema):
    """User login schema."""

    username: constr(min_length=3, max_length=255)
    password: constr(min_length=1, max_length=255)


# Consent schemas
class ConsentRecordBase(BaseSchema):
    """Base consent record schema."""

    consent_type: ConsentType
    consent_given: bool
    consent_version: constr(min_length=1, max_length=50)
    consent_metadata: dict[str, Any] | None = None


class ConsentRecordCreate(ConsentRecordBase):
    """Consent record creation schema."""

    pass


class ConsentRecordResponse(ConsentRecordBase):
    """Consent record response schema."""

    id: UUID
    user_id: UUID
    timestamp: datetime
    withdrawn_at: datetime | None = None


class ConsentWithdrawal(BaseSchema):
    """Consent withdrawal schema."""

    consent_type: ConsentType
    reason: str | None = None


# PALD schemas
class PALDSchemaVersionBase(BaseSchema):
    """Base PALD schema version schema."""

    version: constr(min_length=1, max_length=50)
    schema_content: dict[str, Any]
    migration_notes: str | None = None


class PALDSchemaVersionCreate(PALDSchemaVersionBase):
    """PALD schema version creation schema."""

    pass


class PALDSchemaVersionResponse(PALDSchemaVersionBase):
    """PALD schema version response schema."""

    created_at: datetime
    is_active: bool


class PALDAttributeCandidateBase(BaseSchema):
    """Base PALD attribute candidate schema."""

    attribute_name: constr(min_length=1, max_length=255)
    attribute_category: constr(max_length=100) | None = None


class PALDAttributeCandidateCreate(PALDAttributeCandidateBase):
    """PALD attribute candidate creation schema."""

    pass


class PALDAttributeCandidateResponse(PALDAttributeCandidateBase):
    """PALD attribute candidate response schema."""

    id: UUID
    mention_count: int
    first_detected: datetime
    last_mentioned: datetime
    threshold_reached: bool
    added_to_schema: bool
    schema_version_added: str | None = None


class PALDDataBase(BaseSchema):
    """Base PALD data schema."""

    pald_content: dict[str, Any]
    schema_version: constr(min_length=1, max_length=50)


class PALDDataCreate(PALDDataBase):
    """PALD data creation schema."""

    @field_validator("pald_content")
    @classmethod
    def validate_pald_content(cls, v):
        """Validate PALD content structure."""
        if not isinstance(v, dict):
            raise ValueError("PALD content must be a dictionary")
        if not v:
            raise ValueError("PALD content cannot be empty")
        return v


class PALDDataUpdate(BaseSchema):
    """PALD data update schema."""

    pald_content: dict[str, Any] | None = None
    schema_version: constr(min_length=1, max_length=50) | None = None


class PALDDataResponse(PALDDataBase):
    """PALD data response schema."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    is_validated: bool
    validation_errors: dict[str, Any] | None = None


class PALDValidationResult(BaseSchema):
    """PALD validation result schema."""

    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    coverage_percentage: float = Field(ge=0, le=100)


class PALDDiff(BaseSchema):
    """PALD comparison result schema."""

    added_fields: list[str] = []
    removed_fields: list[str] = []
    modified_fields: list[str] = []
    unchanged_fields: list[str] = []
    similarity_score: float = Field(ge=0, le=1)


class PALDCoverageMetrics(BaseSchema):
    """PALD coverage metrics schema."""

    total_fields: int = Field(ge=0)
    filled_fields: int = Field(ge=0)
    coverage_percentage: float = Field(ge=0, le=100)
    missing_fields: list[str] = []
    field_completeness: dict[str, bool] = {}


# Audit log schemas
class AuditLogBase(BaseSchema):
    """Base audit log schema."""

    request_id: constr(min_length=1, max_length=255)
    operation: constr(min_length=1, max_length=100)
    model_used: constr(max_length=100) | None = None
    parameters: dict[str, Any] | None = None


class AuditLogCreate(AuditLogBase):
    """Audit log creation schema."""

    user_id: UUID | None = None
    parent_log_id: UUID | None = None


class AuditLogUpdate(BaseSchema):
    """Audit log update schema."""

    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    token_usage: conint(ge=0) | None = None
    latency_ms: conint(ge=0) | None = None
    status: AuditLogStatus | None = None
    error_message: str | None = None
    parameters: dict[str, Any] | None = None


class AuditLogResponse(AuditLogBase):
    """Audit log response schema."""

    id: UUID
    user_id: UUID | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    token_usage: int | None = None
    latency_ms: int | None = None
    parent_log_id: UUID | None = None
    status: AuditLogStatus
    error_message: str | None = None
    created_at: datetime
    finalized_at: datetime | None = None


class AuditLogFilters(BaseSchema):
    """Audit log filtering schema."""

    user_id: UUID | None = None
    operation: str | None = None
    model_used: str | None = None
    status: AuditLogStatus | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    request_id: str | None = None
    parent_log_id: UUID | None = None


# Federated Learning schemas
class FederatedLearningUpdateBase(BaseSchema):
    """Base federated learning update schema."""

    model_version: constr(min_length=1, max_length=50)
    aggregation_round: conint(ge=0) | None = None


class FederatedLearningUpdateCreate(FederatedLearningUpdateBase):
    """Federated learning update creation schema."""

    update_data: bytes
    privacy_budget_used: dict[str, Any] | None = None

    @field_validator("update_data")
    @classmethod
    def validate_update_data(cls, v):
        """Validate update data."""
        if not v:
            raise ValueError("Update data cannot be empty")
        if len(v) > 100 * 1024 * 1024:  # 100MB limit
            raise ValueError("Update data too large (max 100MB)")
        return v


class FederatedLearningUpdateResponse(FederatedLearningUpdateBase):
    """Federated learning update response schema."""

    id: UUID
    user_id: UUID
    submitted_at: datetime
    processed: bool
    processed_at: datetime | None = None
    update_size_bytes: int | None = None
    privacy_budget_used: dict[str, Any] | None = None


# System schemas
class SystemMetadataBase(BaseSchema):
    """Base system metadata schema."""

    key: constr(min_length=1, max_length=100)
    value: str


class SystemMetadataCreate(SystemMetadataBase):
    """System metadata creation schema."""

    pass


class SystemMetadataResponse(SystemMetadataBase):
    """System metadata response schema."""

    created_at: datetime
    updated_at: datetime


# Export schemas
class ExportFilters(BaseSchema):
    """Export filtering schema."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    user_id: UUID | None = None
    format: str = Field(default="json", pattern="^(json|csv)$")


class ExportResult(BaseSchema):
    """Export result schema."""

    filename: str
    format: str
    record_count: int
    file_size_bytes: int
    created_at: datetime
    download_url: str | None = None


# Health check schema
class HealthCheckResponse(BaseSchema):
    """Health check response schema."""

    status: str
    database: bool
    timestamp: datetime
    version: str
    uptime_seconds: float
