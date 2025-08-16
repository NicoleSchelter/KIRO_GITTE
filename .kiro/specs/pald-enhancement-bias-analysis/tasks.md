# Implementation Plan

- [ ] 1. Set up enhanced configuration and schema loading infrastructure
  - Create PALDEnhancementConfig class with all required feature flags and settings
  - Implement PALDSchemaLoader class for runtime schema loading from external file
  - Add configuration validation and error handling for missing schema files
  - Write unit tests for configuration validation and schema loading functionality
  - _Requirements: 2.1, 2.2, 2.3, 7.1, 7.2, 7.3_

- [ ] 2. Implement PALD Light extraction system
  - Create PALDLightExtractor class for mandatory immediate PALD extraction
  - Implement text parsing logic to extract explicit attributes from description_text and embodiment_caption
  - Add PALD validation against loaded schema with comprehensive error handling
  - Create PALDLightResult dataclass for structured extraction results
  - Implement prompt compression functionality for Stable Diffusion integration
  - Write unit tests for extraction logic, validation, and prompt compression
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 3. Create bias analysis engine and job management system
  - Implement BiasAnalysisEngine class with all required analysis types (age shift, gender conformity, ethnicity, occupational stereotypes, ambivalent stereotypes, multiple stereotyping)
  - Create BiasJobManager class for deferred bias analysis job creation and processing
  - Implement bias job queue data models and database schema
  - Add bias analysis result storage with pseudonymized identifiers
  - Create BiasAnalysisJob and BiasAnalysisResult dataclasses
  - Write unit tests for each bias analysis type and job management functionality
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [ ] 4. Implement PALD diff calculation and persistence system
  - Create PALDDiffCalculator class for comparing description and embodiment PALDs
  - Implement field classification logic (match/hallucination/missing)
  - Add PALDDiffResult dataclass with comprehensive diff information
  - Create append-only persistence layer for PALD artifacts with pseudonymization
  - Implement data storage models for pald_store with session_id/pseudonym identifiers
  - Write unit tests for diff calculation, field classification, and persistence
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

- [ ] 5. Replace standard Streamlit buttons with accessible form components
  - Create AccessibleFormComponents class with alternative interaction methods
  - Replace all st.button() usage in forms with form_submit_button or auto-submission
  - Implement progress indicators and validation feedback without standard buttons
  - Add accessibility enhancements for screen readers and keyboard navigation
  - Update existing UI components (chat_ui.py, image_ui.py, main.py) to use new form components
  - Write integration tests for form interactions and accessibility compliance
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ] 6. Integrate PALD enhancement into existing logic layer
  - Update PALDManager class to use new PALDLightExtractor and BiasAnalysisEngine
  - Modify existing PALD processing workflows to support mandatory/optional analysis separation
  - Add configuration-controlled processing based on feature flags
  - Implement error recovery and graceful degradation for processing failures
  - Update PALD service layer to handle deferred bias analysis
  - Write integration tests for enhanced PALD processing workflows
  - _Requirements: 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 7. Schema Governance & Config Baseline (bundles former 7, 10, 12)
  - Deliverables: `SchemaEvolutionManager` (detect/queue fields), DB migrations (`schema_field_candidates`, `pald_processing_logs`, `bias_analysis_jobs/_results`, indexes), model updates, `PALDEnhancementConfig` incl. ENV-overrides, runtime validation, minimal docs & migration tests.
  - _Requirements: 2.4, 2.5, 5.3, 5.4, 5.5, 5.6, 6.7, 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2_

- [ ] 8. Background Bias Worker (MVP) + Job Lifecycle (bundles former 11)
  - Deliverables: Worker with retry (exponential backoff), DLQ, status tracking, batch-sizes config, structured logs, CLI entrypoint; integration tests for recovery paths.
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 7.4, 7.5_

- [ ] 9. UI Response Contract & Wiring (bundles former 8 + 14)
  - Deliverables: `PALDProcessingRequest/Response` dataclasses; UI handles `pald_light`, `pald_diff_summary`, `defer_notice`; status/progress + user-guidance; notifications; E2E UI tests.
  - _Requirements: 3.1, 3.2, 3.3, 8.1, 8.2, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 10. Quality Gate, Monitoring & Final Validation (bundles former 9 + 13 + 15)
  - Deliverables: Error hierarchy + recovery manager; performance/processing metrics; privacy checks; extensive unit/integration/perf tests; API + user docs; security review; deployment & rollback docs; final production checks for config flags and external schema path.
  - _Requirements: cross-cutting (all)_