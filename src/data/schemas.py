"""
Pydantic schemas for data validation and serialization.
Provides validation models for all database entities and API requests/responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, conint, constr


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
    INVESTIGATION_PARTICIPATION = "investigation_participation"


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
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    coverage_percentage: float = Field(ge=0, le=100)


class PALDDiff(BaseSchema):
    """PALD comparison result schema."""

    added_fields: list[str] = Field(default_factory=list)
    removed_fields: list[str] = Field(default_factory=list)
    modified_fields: list[str] = Field(default_factory=list)
    unchanged_fields: list[str] = Field(default_factory=list)
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0)

class PALDCoverageMetrics(BaseSchema):
    """PALD coverage metrics schema."""

    total_fields: int = Field(ge=0)
    filled_fields: int = Field(ge=0)
    coverage_percentage: float = Field(ge=0, le=100)
    missing_fields: list[str] = Field(default_factory=list)
    field_completeness: dict[str, bool] = Field(default_factory=dict)

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


# UX Enhancement schemas

class ImageProcessingResultStatus(str, Enum):
    """Image processing result status enumeration."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CORRECTED = "corrected"


class UserCorrectionAction(str, Enum):
    """User correction action enumeration."""

    ACCEPT_PROCESSED = "accept_processed"
    ADJUST_CROP = "adjust_crop"
    USE_ORIGINAL = "use_original"
    MARK_GARBAGE = "mark_garbage"
    REGENERATE = "regenerate"


class ImageProcessingResultBase(BaseSchema):
    """Base image processing result schema."""

    original_image_path: constr(min_length=1, max_length=500)
    processed_image_path: constr(max_length=500) | None = None
    processing_method: constr(min_length=1, max_length=100)
    status: ImageProcessingResultStatus = ImageProcessingResultStatus.PENDING
    confidence_score: conint(ge=0, le=100) | None = None
    processing_time_ms: conint(ge=0) | None = None
    quality_issues: list[str] | None = None
    person_count: conint(ge=0) | None = None
    quality_score: conint(ge=0, le=100) | None = None


class ImageProcessingResultCreate(ImageProcessingResultBase):
    """Image processing result creation schema."""

    pass


class ImageProcessingResultResponse(ImageProcessingResultBase):
    """Image processing result response schema."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


class ImageCorrectionBase(BaseSchema):
    """Base image correction schema."""

    correction_action: UserCorrectionAction
    crop_coordinates: dict[str, int] | None = None  # {left, top, right, bottom}
    rejection_reason: constr(max_length=200) | None = None
    suggested_modifications: str | None = None
    final_image_path: constr(max_length=500) | None = None
    correction_time_ms: conint(ge=0) | None = None


class ImageCorrectionCreate(ImageCorrectionBase):
    """Image correction creation schema."""

    processing_result_id: UUID


class ImageCorrectionResponse(ImageCorrectionBase):
    """Image correction response schema."""

    id: UUID
    processing_result_id: UUID
    user_id: UUID
    created_at: datetime


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


class PrerequisiteCheckResultBase(BaseSchema):
    """Base prerequisite check result schema."""

    operation_name: constr(min_length=1, max_length=100)
    checker_name: constr(min_length=1, max_length=100)
    check_type: PrerequisiteCheckType
    status: PrerequisiteCheckResultStatus
    message: constr(min_length=1)
    details: str | None = None
    resolution_steps: list[str] | None = None
    check_time_ms: conint(ge=0) | None = None
    confidence_score: conint(ge=0, le=100) | None = None
    cached: bool = False


class PrerequisiteCheckResultCreate(PrerequisiteCheckResultBase):
    """Prerequisite check result creation schema."""

    user_id: UUID | None = None


class PrerequisiteCheckResultResponse(PrerequisiteCheckResultBase):
    """Prerequisite check result response schema."""

    id: UUID
    user_id: UUID | None = None
    created_at: datetime


class TooltipInteractionType(str, Enum):
    """Tooltip interaction type enumeration."""

    HOVER = "hover"
    CLICK = "click"
    FOCUS = "focus"
    DISMISS = "dismiss"
    ACTION_TAKEN = "action_taken"


class TooltipInteractionBase(BaseSchema):
    """Base tooltip interaction schema."""

    element_id: constr(min_length=1, max_length=200)
    tooltip_content_id: constr(max_length=200) | None = None
    interaction_type: TooltipInteractionType
    page_context: constr(max_length=200) | None = None
    tooltip_title: constr(max_length=500) | None = None
    tooltip_description: str | None = None
    display_time_ms: conint(ge=0) | None = None
    user_agent: constr(max_length=500) | None = None


class TooltipInteractionCreate(TooltipInteractionBase):
    """Tooltip interaction creation schema."""

    user_id: UUID | None = None
    session_id: constr(max_length=255) | None = None


class TooltipInteractionResponse(TooltipInteractionBase):
    """Tooltip interaction response schema."""

    id: UUID
    user_id: UUID | None = None
    session_id: str | None = None
    created_at: datetime


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


class UXAuditLogBase(BaseSchema):
    """Base UX audit log schema."""

    event_type: UXEventType
    event_context: constr(max_length=200) | None = None
    event_data: dict[str, Any] | None = None
    workflow_step: constr(max_length=100) | None = None
    success: bool | None = None
    error_message: str | None = None
    duration_ms: conint(ge=0) | None = None
    user_agent: constr(max_length=500) | None = None
    ip_address: constr(max_length=45) | None = None


class UXAuditLogCreate(UXAuditLogBase):
    """UX audit log creation schema."""

    user_id: UUID | None = None
    session_id: constr(max_length=255) | None = None


class UXAuditLogResponse(UXAuditLogBase):
    """UX audit log response schema."""

    id: UUID
    user_id: UUID | None = None
    session_id: str | None = None
    created_at: datetime
