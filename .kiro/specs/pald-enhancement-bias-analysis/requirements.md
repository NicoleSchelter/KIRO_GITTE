# Requirements Document

## Introduction

This feature enhances the existing PALD (Pedagogical Agent Level of Design) system to provide more sophisticated bias analysis and schema management capabilities. The enhancement separates mandatory PALD extraction (needed for image generation) from optional bias analysis (for stereotype detection), implements runtime schema loading from external files, and removes standard button usage in Streamlit forms to improve user experience.

## Requirements

### Requirement 1: Streamlit Form Button Replacement

**User Story:** As a user interacting with GITTE forms, I want improved form interactions without standard buttons, so that I have a more seamless and accessible user experience.

#### Acceptance Criteria

1. WHEN a user interacts with any Streamlit form THEN the system SHALL NOT use standard `st.button()` components
2. WHEN a form requires submission THEN the system SHALL use alternative interaction methods (form_submit_button, automatic submission, or custom components)
3. WHEN a user completes form input THEN the system SHALL provide clear feedback without relying on standard button clicks
4. WHEN accessibility features are enabled THEN form interactions SHALL remain fully accessible

### Requirement 2: Runtime PALD Schema Loading

**User Story:** As a system administrator, I want PALD schemas to be loaded from external configuration files at runtime, so that I can update schemas without code changes and maintain schema versioning.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL load the PALD schema from `E:\Forschung\KIRO_GITTE\Basic files\pald_schema.json`
2. WHEN the schema file is not found THEN the system SHALL log an error and fall back to a default schema
3. WHEN the loaded schema is invalid JSON THEN the system SHALL log validation errors and use the default schema
4. WHEN new fields are detected in PALD parsing THEN they SHALL be queued for review and schema integration
5. WHEN schema evolution occurs THEN the system SHALL validate all changes against the loaded baseline schema

### Requirement 3: Mandatory PALD Light Extraction

**User Story:** As a user generating images, I want immediate PALD extraction from my descriptions, so that the system can compress prompts effectively for Stable Diffusion without delays.

#### Acceptance Criteria

1. WHEN a user provides description_text THEN the system SHALL immediately extract PALD Light JSON based on the loaded schema
2. WHEN embodiment_caption is present THEN it SHALL be included in the PALD extraction process
3. WHEN extracting PALD data THEN the system SHALL only include explicitly mentioned attributes from the text (no heuristics)
4. WHEN PALD extraction completes THEN it SHALL contain only filled fields at Global/Medium/Detail levels
5. WHEN PALD extraction fails THEN the system SHALL log the error and provide a minimal valid PALD structure
6. WHEN `MANDATORY_PALD_EXTRACTION` config flag is set THEN this extraction SHALL always occur regardless of other settings

### Requirement 4: Deferred Bias Analysis System

**User Story:** As a researcher studying AI bias, I want optional stereotype and bias analysis that doesn't slow down user interactions, so that I can gather bias data without impacting user experience.

#### Acceptance Criteria

1. WHEN `defer_bias_scan` is true THEN the system SHALL NOT add bias findings to the immediate UI response
2. WHEN bias analysis is deferred THEN the system SHALL create a bias_job entry in stereotype_queue for asynchronous processing
3. WHEN `ENABLE_BIAS_ANALYSIS` config flag is false THEN no bias analysis SHALL be performed
4. WHEN `PALD_ANALYSIS_DEFERRED` config flag is true THEN bias analysis SHALL be queued for post-session processing
5. WHEN bias analysis is enabled THEN it SHALL include age shift, gender conformity, ethnicity consistency, occupational stereotypes, ambivalent stereotypes, and multiple stereotyping detection
6. WHEN bias analysis completes THEN results SHALL be stored with pseudonymized identifiers only

### Requirement 5: PALD Diff Calculation and Persistence

**User Story:** As a researcher analyzing AI consistency, I want to compare description PALDs with embodiment PALDs, so that I can identify hallucinations and missing attributes.

#### Acceptance Criteria

1. WHEN both description and embodiment PALDs exist THEN the system SHALL compute pald_diff showing deltas between them
2. WHEN calculating diffs THEN each field SHALL be marked as {match | hallucination | missing}
3. WHEN PALD data is processed THEN all artifacts SHALL be written to pald_store in append-only format
4. WHEN storing PALD data THEN only pseudonymized identifiers (session_id/pseudonym) SHALL be used
5. WHEN storing artifacts THEN they SHALL include Input IDs, PALD Light, diffs, and metadata
6. WHEN data is persisted THEN no personally identifiable information SHALL be stored

### Requirement 6: Bias Job Payload Processing

**User Story:** As a bias researcher, I want comprehensive stereotype detection across multiple dimensions, so that I can identify various forms of bias in AI-generated content.

#### Acceptance Criteria

1. WHEN processing bias jobs THEN the system SHALL check for age shift (reported vs visually estimated age)
2. WHEN analyzing gender conformity THEN the system SHALL compare clothing/body proportions against description/context
3. WHEN checking ethnicity consistency THEN the system SHALL flag inconsistencies as technical markers only (no profiling)
4. WHEN analyzing occupational stereotypes THEN the system SHALL compare described roles with visual attributes
5. WHEN detecting ambivalent stereotypes THEN the system SHALL identify contradictory cues (e.g., "competent" with infantilized style)
6. WHEN checking multiple stereotyping THEN the system SHALL identify patterns of combined bias categories
7. WHEN bias analysis completes THEN results SHALL maintain indicator lists for systematic tracking

### Requirement 7: Configuration-Controlled Processing

**User Story:** As a system administrator, I want granular control over PALD and bias analysis features, so that I can configure the system for different deployment scenarios.

#### Acceptance Criteria

1. WHEN `PALD_ANALYSIS_DEFERRED` is true THEN deep analysis SHALL be processed in post-session batches
2. WHEN `ENABLE_BIAS_ANALYSIS` is false THEN no bias analysis SHALL be performed
3. WHEN `MANDATORY_PALD_EXTRACTION` is set THEN it SHALL always be true and cannot be disabled
4. WHEN configuration changes THEN the system SHALL apply new settings without restart where possible
5. WHEN invalid configuration is detected THEN the system SHALL log errors and use safe defaults

### Requirement 8: Schema Evolution and Governance

**User Story:** As a data scientist, I want automated schema evolution with governance controls, so that new attributes can be integrated systematically while maintaining data quality.

#### Acceptance Criteria

1. WHEN new attributes are detected THEN they SHALL be queued for review before schema integration
2. WHEN schema evolution is triggered THEN new attributes SHALL be appended only after governance approval
3. WHEN automated threshold approval is configured THEN attributes meeting criteria SHALL be auto-integrated
4. WHEN schema changes occur THEN all existing PALD data SHALL remain valid or be migrated appropriately
5. WHEN schema evolution completes THEN the new schema SHALL be validated against the baseline structure

### Requirement 9: UI Response Structure

**User Story:** As a user of the GITTE system, I want clear feedback about PALD processing status, so that I understand what analysis is happening and when results will be available.

#### Acceptance Criteria

1. WHEN PALD processing completes THEN the UI SHALL receive pald_light data immediately
2. WHEN diff calculation completes THEN the UI SHALL receive pald_diff_summary
3. WHEN bias analysis is deferred THEN the UI SHALL receive defer_notice indicating post-session processing
4. WHEN processing errors occur THEN the UI SHALL receive appropriate error messages with guidance
5. WHEN all processing completes THEN the UI SHALL provide clear status indicators for each component