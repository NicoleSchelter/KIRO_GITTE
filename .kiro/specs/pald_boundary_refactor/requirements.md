# PALD Boundary Enforcement and Schema Evolution - Software Requirements Specification

## 1. Scope and Objectives

### 1.1 Purpose
This specification defines requirements for enforcing PALD (Pedagogical Agent Level of Design) boundaries, removing PALD misuse from non-embodiment flows, and implementing runtime schema evolution capabilities while preserving the existing 4-layer architecture.

### 1.2 Scope
- **In Scope**: PALD boundary enforcement, schema evolution pipeline, deferred bias analysis, survey/onboarding data separation, runtime schema loading
- **Out of Scope**: Changes to current PALD schema content, UI/UX modifications beyond data routing, performance optimizations beyond basic caching

### 1.3 Non-Goals
- Widening the current embodiment-only PALD schema
- Changing Streamlit UI appearance or user workflows
- Modifying existing PALD data structure or validation logic
- Adding new bias analysis algorithms (only infrastructure)

## 2. Functional Requirements

### FR-1: PALD Boundary Enforcement
**Priority**: Critical
- **FR-1.1**: System SHALL only accept embodiment-related attributes in PALD data structures
- **FR-1.2**: System SHALL reject survey responses, onboarding metadata, and user preferences from PALD storage
- **FR-1.3**: System SHALL provide deny-lists for non-embodiment keys with validation errors
- **FR-1.4**: System SHALL log boundary violations with detailed error messages

### FR-2: Runtime Schema Management
**Priority**: High
- **FR-2.1**: System SHALL load PALD schema from `config/pald_schema.json` at runtime
- **FR-2.2**: System SHALL cache loaded schema with file modification detection
- **FR-2.3**: System SHALL log schema checksum and version information on load
- **FR-2.4**: System SHALL fallback to embedded default schema if file loading fails

### FR-3: Data Separation and Proper Storage
**Priority**: Critical
- **FR-3.1**: Survey responses SHALL be stored in dedicated `survey_responses` table
- **FR-3.2**: Onboarding workflow metadata SHALL be stored in `onboarding_progress` table
- **FR-3.3**: User preferences SHALL be stored in `user_preferences` table
- **FR-3.4**: Only embodiment descriptions and images SHALL trigger PALD data creation

### FR-4: Schema Evolution Pipeline
**Priority**: Medium
- **FR-4.1**: System SHALL detect out-of-schema fields during processing
- **FR-4.2**: System SHALL harvest field candidates with occurrence counts
- **FR-4.3**: System SHALL store candidates in `schema_field_candidates` table
- **FR-4.4**: System SHALL NOT write out-of-schema fields to PALD data
- **FR-4.5**: System SHALL provide governance interface for candidate approval/rejection

### FR-5: Deferred Bias Analysis
**Priority**: Medium
- **FR-5.1**: System SHALL extract mandatory PALD Light for immediate use
- **FR-5.2**: System SHALL queue bias analysis jobs when `defer_bias_scan=true`
- **FR-5.3**: System SHALL return immediate response with `pald_light`, optional `pald_diff_summary`, and `defer_notice`
- **FR-5.4**: System SHALL process bias jobs asynchronously with retry logic

### FR-6: Migration and Data Integrity
**Priority**: High
- **FR-6.1**: System SHALL provide forward migration to separate existing mixed data
- **FR-6.2**: System SHALL provide rollback capability for migration failures
- **FR-6.3**: System SHALL preserve all existing data during migration (no data loss)
- **FR-6.4**: System SHALL log all migration operations with detailed audit trails

## 3. Non-Functional Requirements

### NFR-1: Performance
- **NFR-1.1**: Schema loading SHALL complete within 100ms for cached schemas
- **NFR-1.2**: Boundary validation SHALL add <50ms overhead to PALD operations
- **NFR-1.3**: Migration SHALL process 1000 records per minute minimum

### NFR-2: Reliability
- **NFR-2.1**: System SHALL maintain 99.9% uptime during boundary enforcement
- **NFR-2.2**: Schema loading failures SHALL NOT break existing functionality
- **NFR-2.3**: Migration SHALL be atomic per record with rollback capability

### NFR-3: Maintainability
- **NFR-3.1**: All boundary logic SHALL be centralized in `logic/pald_boundary.py`
- **NFR-3.2**: Schema evolution SHALL be configurable via feature flags
- **NFR-3.3**: Migration scripts SHALL be idempotent and rerunnable

### NFR-4: Security and Privacy
- **NFR-4.1**: All data separation SHALL preserve user pseudonymization
- **NFR-4.2**: Migration SHALL maintain existing encryption and access controls
- **NFR-4.3**: Schema candidates SHALL NOT expose raw user input

## 4. Data Requirements

### 4.1 New Data Models
- `survey_responses`: User survey data with structured preferences
- `onboarding_progress`: Workflow state and completion tracking
- `user_preferences`: General user settings and non-embodiment preferences
- `schema_field_candidates`: Detected out-of-schema fields for governance
- `schema_versions`: Runtime schema version tracking
- `schema_changes`: Audit trail for schema evolution decisions

### 4.2 Enhanced Existing Models
- `pald_data`: Add append-only artifacts store reference
- `bias_analysis_jobs`: Enhanced job queue with retry and DLQ support
- `bias_analysis_results`: Structured bias findings storage

### 4.3 Data Migration Requirements
- Extract non-embodiment fields from existing `pald_data.pald_content`
- Migrate survey data to `survey_responses` table
- Migrate onboarding metadata to `onboarding_progress` table
- Migrate user preferences to `user_preferences` table
- Preserve embodiment-only fields in cleaned `pald_data`

## 5. Interface Requirements

### 5.1 Logic Layer Interfaces
```python
# src/logic/pald_boundary.py
def filter_to_pald_attributes(data: dict) -> dict
def validate_pald_boundary(data: dict) -> ValidationResult
def get_embodiment_deny_list() -> list[str]

# src/logic/pald_evolution.py  
def extract_candidate_fields(data: dict, schema: dict) -> list[FieldCandidate]
def harvest_schema_candidates(candidates: list) -> None
def propose_schema_changes(candidates: list) -> list[SchemaChange]
```

### 5.2 Service Layer Interfaces
```python
# src/services/pald_schema_registry_service.py
def get_active_schema() -> tuple[str, dict]
def load_schema_from_file(path: str) -> dict
def cache_schema(version: str, schema: dict) -> None

# src/services/survey_response_service.py
def save_survey_response(user_id: UUID, data: dict) -> SurveyResponse
def get_user_survey_data(user_id: UUID) -> SurveyResponse | None

# src/services/onboarding_progress_service.py
def update_progress(user_id: UUID, step: str, data: dict) -> OnboardingProgress
def get_user_progress(user_id: UUID) -> OnboardingProgress | None
```

### 5.3 UI Response Contract
```python
@dataclass
class PALDProcessingResponse:
    pald_light: dict[str, Any]                    # Immediate PALD data
    pald_diff_summary: str | None = None          # Optional diff summary
    defer_notice: str | None = None               # Deferred processing notice
    validation_errors: list[str] = field(default_factory=list)
    processing_metadata: dict[str, Any] = field(default_factory=dict)
```

## 6. Configuration Requirements

### 6.1 Feature Flags (Centralized in config.py)
```python
MANDATORY_PALD_EXTRACTION: bool = True           # Always True
PALD_ANALYSIS_DEFERRED: bool = True              # Default deferred processing
ENABLE_BIAS_ANALYSIS: bool = True                # Enable bias analysis
ENABLE_PALD_AUTO_EXTENSION: bool = False         # Disable auto schema extension
PALD_CANDIDATE_MIN_SUPPORT: int = 5              # Min occurrences for candidates
```

### 6.2 Schema Configuration
```python
PALD_SCHEMA_FILE_PATH: str = "config/pald_schema.json"  # Portable path
PALD_SCHEMA_CACHE_TTL: int = 300                        # 5 minutes cache
PALD_SCHEMA_CHECKSUM_LOG: bool = True                   # Log checksums
```

## 7. Migration Requirements

### 7.1 Forward Migration
1. **Data Analysis Phase**: Scan existing `pald_data` for non-embodiment fields
2. **Schema Validation Phase**: Validate fields against current embodiment schema
3. **Data Separation Phase**: Extract and categorize non-embodiment data
4. **Storage Migration Phase**: Move data to appropriate new tables
5. **Cleanup Phase**: Remove non-embodiment fields from `pald_data`
6. **Verification Phase**: Validate migration completeness and integrity

### 7.2 Rollback Strategy
1. **Backup Creation**: Full backup before migration start
2. **Incremental Rollback**: Per-record rollback capability
3. **State Restoration**: Restore original `pald_data` content
4. **Cleanup Rollback**: Remove newly created table entries
5. **Verification Rollback**: Validate rollback completeness

## 8. Acceptance Criteria

### 8.1 Boundary Enforcement
- [ ] Writing non-embodiment keys to PALD fails with clear error message
- [ ] Survey UI stores responses without creating PALD entries
- [ ] Onboarding logic stores metadata without PALD writes
- [ ] Schema validation rejects non-embodiment attributes
- [ ] Boundary violations are logged with detailed context

### 8.2 Schema Evolution
- [ ] Out-of-schema fields become candidates, not PALD data
- [ ] Candidate harvesting works without exposing raw user data
- [ ] Schema registry maintains version history and checksums
- [ ] Runtime schema loading works with file modification detection
- [ ] Governance interface allows candidate approval/rejection

### 8.3 Data Migration
- [ ] Migration separates mixed data correctly without loss
- [ ] Forward migration preserves all user data integrity
- [ ] Rollback migration restores original state completely
- [ ] Migration audit logs provide complete operation history
- [ ] Post-migration validation confirms data separation success

### 8.4 System Integration
- [ ] All tests pass after boundary enforcement implementation
- [ ] UI workflows remain unchanged from user perspective
- [ ] Performance impact stays within defined NFR limits
- [ ] Configuration flags control all new behavior appropriately
- [ ] Documentation accurately reflects new architecture

## 9. Risk Assessment

### 9.1 High Risk
- **Data Loss During Migration**: Mitigation via comprehensive backup and rollback
- **Performance Degradation**: Mitigation via caching and optimized queries
- **Breaking Existing Functionality**: Mitigation via extensive testing and gradual rollout

### 9.2 Medium Risk
- **Schema Loading Failures**: Mitigation via fallback to embedded schema
- **Migration Complexity**: Mitigation via phased approach and validation
- **Configuration Errors**: Mitigation via validation and clear documentation

### 9.3 Low Risk
- **User Experience Changes**: Minimal risk due to data-only routing changes
- **Security Vulnerabilities**: Low risk due to preservation of existing patterns
- **Compatibility Issues**: Low risk due to backward-compatible approach

## 10. Success Metrics

### 10.1 Technical Metrics
- Zero data loss during migration (100% data preservation)
- <50ms performance overhead for boundary validation
- >99.9% schema loading success rate
- <1% false positive rate for boundary violations

### 10.2 Quality Metrics
- 100% test coverage for new boundary enforcement logic
- Zero critical bugs in production after 30 days
- <5 configuration-related support tickets per month
- 100% successful rollback capability in testing

### 10.3 Operational Metrics
- Migration completion within 4-hour maintenance window
- <2 hours mean time to recovery for schema loading issues
- 100% audit trail completeness for all data operations
- Zero unauthorized access to separated data stores