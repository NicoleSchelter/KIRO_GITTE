# Requirements Document

## Introduction

This specification defines a comprehensive study participation and onboarding flow for the GITTE system that ensures proper data collection, consent management, and user progression through a structured research study. The feature establishes pseudonym-based data storage as the foundation for all subsequent interactions, implements dynamic survey capabilities, and provides a complete chat and image generation pipeline with configurable feedback loops. This enhancement integrates with existing GITTE components while ensuring GDPR compliance and research data integrity.

## Requirements

### Requirement 1: Pseudonym-Based Identity Management

**User Story:** As a research participant, I want to create a unique pseudonym that protects my identity while allowing the system to track my study data, so that my privacy is protected throughout the research process.

#### Acceptance Criteria

1. WHEN a user completes initial login/registration THEN they SHALL be required to create a unique pseudonym before any data collection
2. WHEN creating a pseudonym THEN the user SHALL generate a unique key based on birthdays, nitails of parents or own ones, for Example: 
✏️ How to create your pseudonym step by step
Your pseudonym consists of a combination of letters and numbers that you can easily remember but others cannot easily trace back to you.

Please use the following components:
First letter of your first name (uppercase)

Birth month (two digits, e.g. "03" for March)

First letter of your last name (lowercase)

Year of birth (four digits, e.g. "2001")

First letter of the parents' first names in alphabetical order (uppercase)

Any number or word you like (e.g. your lucky number)

✅ Example
Your name is Maxima Schneider, born in March 2001,
your father's name is Jürgen, your mother's name is Angela, your lucky number is 13

Then your pseudonym would be: M03s2001AJ13'''

3. WHEN a pseudonym is created THEN it SHALL become the primary identifier for all subsequent data storage (consents, surveys, PALDs, chat)
4. WHEN pseudonym creation fails THEN the user SHALL NOT be able to proceed to consent or survey steps
5. WHEN a pseudonym is successfully created THEN it SHALL be validated for uniqueness and stored securely
6. WHEN data is stored THEN it SHALL use pseudonym_id as the foreign key, NOT the original user_id
7. WHEN a user returns to the system THEN they should use there login-credentials but, the must have the possibility to delete der data based on their pseudonyms

### Requirement 2: Multi-Step Consent Collection Flow

**User Story:** As a research participant, I want to provide informed consent for different aspects of the study, so that I understand and control how my data will be used.

#### Acceptance Criteria

1. WHEN a user has created a pseudonym THEN they SHALL be presented with the consent collection flow
2. WHEN consent is collected THEN it SHALL include data protection, AI interaction, and study participation consents
3. WHEN any required consent is not provided THEN the system SHALL abort the onboarding process and prevent further progression
4. WHEN all required consents are provided THEN they SHALL be stored with timestamps and version information under the pseudonym_id
5. WHEN consent is withdrawn at any time THEN all associated data processing SHALL cease immediately
6. WHEN consent status changes THEN the system SHALL log the change with appropriate audit trails
7. WHEN consent collection completes successfully THEN the user SHALL automatically proceed to the survey step

### Requirement 3: Dynamic Survey System with Excel/CSV Loading

**User Story:** As a researcher, I want to load survey questions dynamically from Excel/CSV files with flexible question types, so that I can modify surveys without code changes and collect structured participant data.

#### Acceptance Criteria

1. WHEN the survey step begins THEN the system SHALL load questions from a configurable Excel/CSV file
2. WHEN loading survey data THEN it SHALL support the schema: question_id, question_text, type, options, required
3. WHEN question type is "text" THEN the system SHALL present a text input field
4. WHEN question type is "number" THEN the system SHALL present a numeric input with validation
5. WHEN question type is "choice" THEN the system SHALL present single-select options from the options field
6. WHEN question type is "multi-choice" THEN the system SHALL present multiple-select options from the options field
7. WHEN required questions are not answered THEN the system SHALL prevent survey submission with clear error messages
8. WHEN survey is completed THEN responses SHALL be stored under pseudonym_id in a dedicated survey_responses table
9. WHEN survey submission succeeds THEN the user SHALL automatically proceed to the chat interface

### Requirement 4: Chat and PALD Pipeline with Consistency Loop

**User Story:** As a research participant, I want to interact with the AI system through chat that generates consistent embodiment images, so that I can create personalized learning assistant representations.

#### Acceptance Criteria

1. WHEN the chat interface loads THEN it SHALL process student input through the complete PALD pipeline
2. WHEN student input is received THEN the system SHALL extract PALD data from the description
3. WHEN PALD is extracted THEN it SHALL generate a compressed 77-token image prompt for Stable Diffusion
4. WHEN an image is generated THEN the system SHALL describe the image and extract PALD from the description
5. WHEN both input and description PALDs exist THEN the system SHALL compare them for consistency
6. WHEN PALDs are inconsistent THEN the system SHALL loop until consistent or maximum iterations reached
7. WHEN consistency is achieved OR max iterations reached THEN the system SHALL store all PALDs and messages under pseudonym_id
8. WHEN the consistency loop completes THEN the system SHALL present the final image and description to the user
9. WHEN prompts are use THEN the system SHALL extract PALD data from the prompt 
10. WHEN ansers are given from the llm THEN the system SHALL extract PALD data from the answer
11. When PALD data is not needed during the process THEN the system SHALL give the possibility to postpoone the PALD-Analysis

### Requirement 5: Configurable Feedback Loop System

**User Story:** As a research participant, I want to provide feedback on generated images with a limited number of rounds, so that I can help improve the AI while maintaining study structure.

#### Acceptance Criteria

1. WHEN an image is presented THEN the user SHALL be able to provide feedback on the result
2. WHEN feedback is provided THEN it SHALL be stored as both PALD data and text under pseudonym_id
3. WHEN feedback triggers regeneration THEN a new image SHALL be generated with corrected parameters
4. WHEN feedback rounds are counted THEN they SHALL NOT exceed the MAX_FEEDBACK_ROUNDS configuration setting
5. WHEN maximum feedback rounds are reached THEN the system SHALL finalize the current result
6. WHEN feedback is processed THEN all feedback data SHALL be logged with timestamps and round numbers
7. WHEN the feedback loop completes THEN the user SHALL be able to continue with additional interactions or end the session
8. When the user would like to stop the feedback-Loop, she will have a possibility to stop.

### Requirement 6: Comprehensive Data Logging and Storage

**User Story:** As a researcher, I want complete logging of all interactions, prompts, responses, and processing metadata, so that I can analyze the AI system's behavior and participant interactions.

#### Acceptance Criteria

1. WHEN any AI interaction occurs THEN the system SHALL log prompts, responses, PALDs, latencies, LLM-Modeltemperature and token usage
2. WHEN data is logged THEN it SHALL include session metadata, timestamps, and processing parameters
3. WHEN storing interaction data THEN it SHALL use pseudonym_id as the primary identifier
4. WHEN logging chat interactions THEN it SHALL maintain conversation threading and context
5. WHEN storing PALD data THEN it SHALL include version information and validation status
6. WHEN logging image generation THEN it SHALL include model parameters, generation time, and quality metrics
7. WHEN audit data is created THEN it SHALL be stored in append-only format for research integrity

### Requirement 7: Database Initialization and Admin Reset Functionality

**User Story:** As a system administrator, I want to initialize all database tables and reset them for clean experiments, so that I can manage research studies effectively.

#### Acceptance Criteria

1. WHEN the system initializes THEN init_all_db SHALL create all required tables exactly once (students, consents, palds, prompts, chat, survey_responses)
2. WHEN tables already exist THEN initialization SHALL NOT duplicate or corrupt existing data
3. WHEN admin reset is requested THEN the system SHALL provide a routine to drop and re-create all tables
4. WHEN reset is performed THEN it SHALL completely clear all study data for fresh experiments
5. WHEN reset completes THEN all tables SHALL be recreated with proper schema and constraints
6. WHEN foreign key relationships exist THEN reset SHALL maintain proper referential integrity
7. WHEN reset is executed THEN it SHALL log the operation with timestamp and administrator identification

### Requirement 8: Configurable System Parameters

**User Story:** As a system administrator, I want configurable parameters for feedback rounds, PALD analysis, and consistency checking, so that I can adapt the system for different research scenarios.

#### Acceptance Criteria

1. WHEN MAX_FEEDBACK_ROUNDS is configured THEN the system SHALL enforce this limit strictly
2. WHEN PALD_ANALYSIS_DEFERRED is set THEN deep analysis SHALL be processed according to the configuration
3. WHEN ENABLE_CONSISTENCY_CHECK is configured THEN the PALD consistency loop SHALL be enabled or disabled accordingly
4. WHEN model parameters are configured THEN they SHALL control temperature, top_p for JSON/chat/image LLMs
5. WHEN configuration changes THEN they SHALL take effect without requiring code changes (restart allowed)
6. WHEN invalid configuration is detected THEN the system SHALL use safe defaults and log warnings
7. WHEN configuration is loaded THEN it SHALL validate all parameters and report any issues

### Requirement 9: Data Privacy and Participant Rights

**User Story:** As a research participant, I want my data to be deletable by request and properly pseudonymized, so that my privacy rights are protected throughout the study.

#### Acceptance Criteria

1. WHEN a participant requests data deletion THEN all data associated with their pseudonym_id SHALL be removable
2. WHEN data deletion is performed THEN it SHALL cascade through all related tables (consents, surveys, PALDs, chat)
3. WHEN data is stored THEN it SHALL use only pseudonymized identifiers, never original user_id
4. WHEN pseudonym mapping is needed THEN it SHALL be stored separately with appropriate access controls
5. WHEN data export is requested THEN it SHALL include only pseudonymized data
6. WHEN audit trails are maintained THEN they SHALL not compromise participant anonymity
7. WHEN data retention policies apply THEN the system SHALL support automated cleanup based on configured retention periods

### Requirement 10: Integration with Existing GITTE Architecture

**User Story:** As a system architect, I want the study participation flow to integrate seamlessly with existing GITTE components, so that system consistency and maintainability are preserved.

#### Acceptance Criteria

1. WHEN implementing the onboarding flow THEN it SHALL maintain the existing 4-layer architecture (UI → Logic → Service → Data)
2. WHEN Streamlit components are used THEN they SHALL remain in the UI layer with no business logic
3. WHEN integrating with existing PALD systems THEN it SHALL use established interfaces and patterns
4. WHEN database changes are made THEN they SHALL follow existing migration patterns and schema conventions
5. WHEN new services are created THEN they SHALL implement proper port/adapter patterns
6. WHEN configuration is extended THEN it SHALL integrate with the existing centralized configuration system
7. WHEN audit logging is implemented THEN it SHALL use the existing audit system and write-ahead logging patterns

### Requirement 11: Error Handling and Recovery

**User Story:** As a research participant, I want the system to handle errors gracefully and allow me to recover from issues, so that technical problems don't prevent me from completing the study.

#### Acceptance Criteria

1. WHEN pseudonym creation fails THEN the system SHALL provide clear error messages and retry options
2. WHEN consent collection encounters errors THEN the user SHALL be able to restart the consent process
3. WHEN survey loading fails THEN the system SHALL fall back to a default survey or provide admin notification
4. WHEN PALD processing fails THEN the system SHALL log errors and continue with available data
5. WHEN image generation fails THEN the system SHALL provide fallback options and clear user feedback
6. WHEN database operations fail THEN the system SHALL maintain data consistency and provide recovery options
7. WHEN any critical error occurs THEN the system SHALL preserve user progress and allow session resumption

### Requirement 12: Testing and Validation

**User Story:** As a developer, I want comprehensive tests covering the study participation flow, so that the system reliability and data integrity are ensured.

#### Acceptance Criteria

1. WHEN tests are written THEN they SHALL cover pseudonym creation, validation, and uniqueness
2. WHEN consent flow is tested THEN it SHALL verify proper storage and retrieval under pseudonym_id
3. WHEN survey functionality is tested THEN it SHALL validate dynamic loading, question types, and data storage
4. WHEN PALD pipeline is tested THEN it SHALL verify consistency loops, feedback rounds, and data logging
5. WHEN database operations are tested THEN they SHALL verify proper foreign key relationships and data integrity
6. WHEN admin functions are tested THEN they SHALL verify reset functionality and table recreation
7. WHEN integration tests are run THEN they SHALL verify end-to-end flow from registration through chat completion