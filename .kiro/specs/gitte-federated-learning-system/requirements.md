# Requirements Document

## Introduction

GITTE (Great Individual Tutor Embodiment) is a production-grade federated learning-capable system for creating personalized visual representations and embodiments of intelligent learning assistants. The system focuses on generating and managing personalized visual avatars, characters, and representations that will later be integrated into learning systems. It provides AI-powered chat for embodiment interaction and image generation for visual representation creation while maintaining GDPR compliance and supporting optional federated learning for embodiment personalization improvement. The system uses Python 3.10+, Streamlit for UI, Ollama for LLMs, and Stable Diffusion for image generation, all designed with swappable adapters and configuration flags.

## Requirements

### Requirement 1: System Architecture and Layer Separation

**User Story:** As a system architect, I want a strict 4-layer architecture enforced throughout the system, so that the codebase remains maintainable, testable, and scalable.

#### Acceptance Criteria

1. WHEN the system is designed THEN it SHALL implement exactly 4 layers: UI (Streamlit) → Logic → Service/Adapters → Data/Persistence
2. WHEN any component is developed THEN it SHALL NOT bypass layer boundaries or create cross-layer shortcuts
3. WHEN new features are added THEN they SHALL follow the established layer separation pattern
4. WHEN the system is deployed THEN each layer SHALL have clearly defined responsibilities and interfaces

### Requirement 2: User Authentication and Registration

**User Story:** As a user, I want to securely register and login to the system, so that I can access personalized tutoring features.

#### Acceptance Criteria

1. WHEN a new user accesses the system THEN they SHALL be presented with registration and login options
2. WHEN a user registers THEN their password SHALL be hashed using bcrypt
3. WHEN a user logs in THEN the system SHALL authenticate them against stored credentials
4. WHEN authentication is successful THEN the user SHALL be assigned appropriate roles (Admin or Participant)
5. WHEN authentication fails THEN the system SHALL provide appropriate error messages without revealing sensitive information

### Requirement 3: Consent Management and Privacy Gate

**User Story:** As a privacy-conscious user, I want explicit consent controls before any data processing, so that my privacy rights are protected according to GDPR standards.

#### Acceptance Criteria

1. WHEN a user first accesses the system THEN they SHALL encounter a consent gate before any chat or image functionality
2. WHEN consent is not provided THEN the system SHALL block access to chat and image generation features
3. WHEN consent is given THEN the system SHALL store the consent with timestamp and version information
4. WHEN consent is withdrawn THEN the system SHALL immediately restrict access to data processing features
5. WHEN consent status changes THEN the system SHALL log the change with appropriate audit trails

### Requirement 4: PALD Schema and Dynamic Evolution

**User Story:** As a system administrator, I want a versioned and validated PALD (Pedagogical Agent Level of Design) JSON schema with dynamic evolution capabilities, so that educational interactions are structured and can adapt to new attributes without central data collection.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL load a versioned PALD JSON schema with validation rules
2. WHEN educational interactions occur THEN they SHALL be validated against the current PALD schema
3. WHEN PALD data is processed THEN the system SHALL ensure 100% schema validation compliance
4. WHEN new attributes are discovered THEN they SHALL be proposed via aggregated client suggestions without raw data collection
5. WHEN users describe embodiment features not in current PALD schema THEN the system SHALL detect and track these new attributes
6. WHEN a new attribute reaches a specified threshold of mentions across users THEN it SHALL be automatically added to the PALD schema
7. WHEN schema versions change THEN the system SHALL maintain backward compatibility with previous versions
6. WHEN PALD data is exported THEN it SHALL include version information and validation status

### Requirement 4a: PALD Comparison and Coverage Metrics

**User Story:** As a system administrator, I want PALD comparison and coverage analysis tools, so that I can monitor data completeness and changes over time.

#### Acceptance Criteria

1. WHEN two PALDs are compared THEN the system SHALL provide a deterministic diff report showing differences
2. WHEN PALD coverage is calculated THEN the system SHALL report total fields vs. filled fields ratio
3. WHEN comparison results are generated THEN they SHALL be available in admin export functionality
4. WHEN coverage metrics are computed THEN they SHALL be consistent and reproducible across multiple calculations
5. WHEN PALD analysis is performed THEN results SHALL be available in both CSV and JSON formats

### Requirement 4b: Dynamic PALD Schema Evolution from User Interactions

**User Story:** As a system administrator, I want the PALD schema to automatically evolve based on user descriptions of embodiment features, so that the system can capture new attributes without manual schema updates.

#### Acceptance Criteria

1. WHEN users describe embodiment features during chat THEN the system SHALL extract and identify attributes not present in the current PALD schema
2. WHEN new attributes are detected THEN they SHALL be tracked with occurrence counts across all users without storing raw text
3. WHEN a new attribute reaches a configurable threshold of mentions THEN it SHALL be automatically proposed for schema inclusion
4. WHEN schema evolution occurs THEN it SHALL create a new schema version while maintaining backward compatibility
5. WHEN new attributes are added THEN existing PALD data SHALL remain valid and be upgradeable to new schema versions
6. WHEN attribute detection happens THEN it SHALL use privacy-preserving aggregation without exposing individual user data

### Requirement 5: LLM Integration with Ollama

**User Story:** As a user, I want to interact with embodiment prototypes through natural language chat, so that I can help define and refine the personality and characteristics of my personalized learning assistant avatar.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL connect to Ollama at the configured endpoint (default: http://localhost:11434)
2. WHEN a user sends a chat message THEN the system SHALL process it through the configured LLM model
3. WHEN LLM responses are generated THEN the median TTFT (Time To First Token) SHALL be ≤ 2 seconds
4. WHEN LLM responses take longer THEN the p95 latency SHALL be ≤ 5 seconds with streaming or progress fallback
5. WHEN LLM models are configured THEN they SHALL be swappable through configuration without code changes

### Requirement 6: Image Generation with Stable Diffusion

**User Story:** As a user, I want to generate visual representations of my learning assistant embodiment based on text prompts, so that I can create and customize the appearance of my personalized avatar.

#### Acceptance Criteria

1. WHEN a user requests image generation THEN the system SHALL use Stable Diffusion through the Diffusers library
2. WHEN images are generated THEN the default model SHALL be runwayml/stable-diffusion-v1-5 or configured alternative
3. WHEN generating 512×512 images THEN the p95 end-to-end latency SHALL be ≤ 30 seconds on GPU
4. WHEN GPU is unavailable THEN the system SHALL fallback to CPU or dummy mode as configured
5. WHEN images are created THEN they SHALL be stored with appropriate metadata and audit trails

### Requirement 7: Prompt Audit and Write-Ahead Logging

**User Story:** As a system administrator, I want comprehensive audit logging with write-ahead logging for all AI interactions, so that I can monitor system usage and ensure compliance with complete traceability.

#### Acceptance Criteria

1. WHEN any AI interaction begins THEN the system SHALL initialize a write-ahead log (WAL) entry before the model call
2. WHEN AI interactions complete THEN the system SHALL finalize the log entry with inputs, outputs, model used, parameters, token usage, latency, and timestamps
3. WHEN audit logs are created THEN they SHALL maintain parent-child linking for conversation threads
4. WHEN audit completeness is measured THEN it SHALL achieve ≥ 99% completeness per month
5. WHEN audit records are accessed THEN they SHALL be available for export in CSV and JSON formats with full conversation context
6. WHEN log entries are created THEN they SHALL include unique request IDs for traceability across system components

### Requirement 8: Federated Learning Implementation

**User Story:** As a system operator, I want optional federated learning capabilities, so that the system can improve while maintaining user privacy.

#### Acceptance Criteria

1. WHEN federated learning is enabled THEN it SHALL be controlled by feature flags without code changes
2. WHEN FL updates occur THEN they SHALL use only structured signals (PALD slots, feedback clicks, consistency labels)
3. WHEN FL processes data THEN no raw texts or images SHALL leave the client environment
4. WHEN FL aggregation happens THEN it SHALL use FedAvg algorithm on the server side
5. WHEN differential privacy is enabled THEN it SHALL provide configurable clip norm and noise parameters

### Requirement 9: Database and Storage Management

**User Story:** As a system administrator, I want reliable data persistence and optional object storage, so that user data and generated content are safely stored.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL connect to PostgreSQL (≥13) with UTF-8 encoding
2. WHEN the database is configured THEN it SHALL use the default database name "data_collector"
3. WHEN object storage is enabled THEN it SHALL use MinIO (S3-compatible) for images
4. WHEN object storage is unavailable THEN it SHALL fallback to local filesystem storage
5. WHEN images are stored THEN only paths/URIs SHALL be stored in the database, not binary data

### Requirement 10: Configuration Management

**User Story:** As a system administrator, I want centralized configuration management, so that system behavior can be controlled without code changes.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL load all configuration from a single source of truth (config.py)
2. WHEN feature flags are changed THEN they SHALL take effect without requiring code modifications
3. WHEN models are configured THEN they SHALL be mappable through configuration files
4. WHEN internationalization is needed THEN text strings SHALL be centrally managed in configuration
5. WHEN environment variables are used THEN they SHALL override default configuration values

### Requirement 11: Guided Onboarding Flow

**User Story:** As a new user, I want a fully automated guided onboarding process, so that I can seamlessly create personalized embodiment representations without manual navigation.

#### Acceptance Criteria

1. WHEN a user completes registration THEN they SHALL be automatically guided through the mandatory flow: Login/Registration → Consent UI → Survey → Design Features → GITTE Chat → Image Generation → Feedback Loop
2. WHEN the onboarding flow executes THEN it SHALL be fully automated without requiring manual navigation between steps
3. WHEN the survey is presented THEN it SHALL collect minimal data necessary for personalization while respecting privacy requirements
4. WHEN consent is missing at any step THEN the system SHALL block progression to further steps
5. WHEN the survey is completed THEN the data SHALL be stored with appropriate pseudonymization
6. WHEN the onboarding is finished THEN the user SHALL have access to all consented features with personalized embodiment settings applied

### Requirement 12: Roles and Administrative Interface

**User Story:** As a system administrator, I want role-based access controls and comprehensive administrative tools, so that I can manage the system effectively while maintaining security boundaries.

#### Acceptance Criteria

1. WHEN users are assigned roles THEN the system SHALL distinguish between "Admin" and "Participant" roles with appropriate permissions
2. WHEN admin users log in THEN they SHALL have exclusive access to administrative functions and monitoring tools
3. WHEN admin exports are requested THEN they SHALL be filterable by date range, user_id, model, and channel
4. WHEN administrative statistics are viewed THEN they SHALL include response time, error rate, and token usage metrics
5. WHEN data export is requested THEN the system SHALL provide CSV and JSON export options with role-based restrictions
6. WHEN PALD data is exported THEN it SHALL include diff utilities and coverage analysis tools
7. WHEN audit data is exported THEN it SHALL maintain referential integrity and parent-child relationships
8. WHEN exports are generated THEN they SHALL respect user privacy settings and consent status

### Requirement 13: Development and Deployment Infrastructure

**User Story:** As a developer, I want comprehensive development tools and deployment infrastructure with CI/CD pipeline, so that I can efficiently develop, test, and deploy the system.

#### Acceptance Criteria

1. WHEN the development environment is set up THEN it SHALL use Docker Compose including Streamlit app, PostgreSQL, optional MinIO, and Ollama containers
2. WHEN development commands are needed THEN they SHALL be available through Makefile targets: dev, test, migrate, seed, run
3. WHEN the system is tested THEN it SHALL include unit tests, integration tests, and smoke tests in a CI pipeline
4. WHEN smoke tests run THEN they SHALL verify chat roundtrip, image generation, and audit row creation
5. WHEN documentation is generated THEN it SHALL follow arc42-style architecture documentation with ADRs
6. WHEN the system is deployed THEN it SHALL support both containerized and local development modes
7. WHEN seed data is needed THEN it SHALL be available through automated seeding scripts

### Requirement 14: Security and GDPR Compliance

**User Story:** As a system operator, I want comprehensive security measures and GDPR compliance, so that user data is protected according to regulatory requirements.

#### Acceptance Criteria

1. WHEN the system handles user data THEN it SHALL implement GDPR-friendly defaults with pseudonymization
2. WHEN deletion requests are received THEN they SHALL be processed within 72 hours
3. WHEN data is backed up or exported THEN it SHALL be encrypted using AES-256 encryption
4. WHEN network communication occurs THEN it SHALL use TLS 1.2+ for all endpoints
5. WHEN user consent is withdrawn THEN all related data processing SHALL cease immediately
6. WHEN data breaches are detected THEN the system SHALL have appropriate incident response procedures

### Requirement 15: Accessibility and User Experience

**User Story:** As a user with accessibility needs, I want the system to be fully accessible and provide an optimal user experience, so that I can use all features regardless of my abilities.

#### Acceptance Criteria

1. WHEN the system is accessed THEN it SHALL comply with WCAG 2.1 AA accessibility standards
2. WHEN users navigate the interface THEN it SHALL support full keyboard navigation
3. WHEN screen readers are used THEN all elements SHALL have appropriate ARIA labels
4. WHEN visual elements are displayed THEN they SHALL meet sufficient contrast requirements
5. WHEN the chat interface is active THEN the screen SHALL clear after greeting and name entry, showing only the chat interface
6. WHEN user input is needed THEN the input field SHALL appear at the correct time in the flow

### Requirement 16: Performance and Quality Goals

**User Story:** As a system user, I want consistent performance and reliability, so that my learning experience is not interrupted by technical issues.

#### Acceptance Criteria

1. WHEN LLM responses are generated THEN the median TTFT (Time To First Token) SHALL be ≤ 2 seconds
2. WHEN LLM responses take longer THEN the p95 latency SHALL be ≤ 5 seconds with streaming or progress fallback
3. WHEN images are generated (512×512) THEN the p95 end-to-end latency SHALL be ≤ 30 seconds on GPU
4. WHEN system availability is measured THEN it SHALL achieve 99.5% uptime during business hours
5. WHEN error rates are monitored THEN they SHALL remain below 1% for all critical user flows
6. WHEN token budgets are managed THEN the system SHALL implement central guards and retry logic with exponential backoff

### Requirement 17: Configuration and Environment Management

**User Story:** As a system administrator, I want centralized configuration management with environment variable overrides, so that I can deploy and manage the system across different environments.

#### Acceptance Criteria

1. WHEN the system starts THEN environment variables SHALL override defaults defined in config.py
2. WHEN configuration changes are made THEN they SHALL take effect without requiring code modifications
3. WHEN internationalization is needed THEN text strings SHALL be centrally managed in configuration files
4. WHEN different environments are deployed THEN configuration SHALL be environment-specific while maintaining consistency
5. WHEN feature flags are toggled THEN they SHALL control system behavior without code changes (restart allowed)