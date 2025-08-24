**requirements_final.md**

**Introduction**

This specification consolidates all previous requirement sets for GITTE (Great Individual Tutor Embodiment). It defines a production‑grade, research‑ready system to create, validate and manage **personalized embodiments** (visual avatars) of intelligent learning assistants under strict privacy, architecture and quality constraints.

The system follows a **strict 4‑layer architecture** (UI → Logic → Service → Data), uses **pseudonym‑based identity**, enforces a **PALD boundary** (PALD contains *only embodiment‑related* information), supports **runtime PALD schema loading and evolution**, integrates **LLM chat** and **image generation** with a **consistency loop**, and applies **image isolation, quality checks and a user correction dialog** *after* feedback rounds and *before* final delivery. It includes **feature‑flagged prerequisites**, **contextual tooltips**, **centralized configuration**, **audit/WAL**, **optional federated learning**, **WCAG 2.1 AA**, **security & GDPR**, **CI/CD & testing**, and **admin reset**.

**Requirement 1: Architecture & Layering**

**User Story:** As an architect, I need a strict 4‑layer separation so we preserve maintainability and testability.

**Acceptance Criteria**

1.  All UI code (Streamlit) exists exclusively in the UI layer; no business logic in UI.

2.  Logic layer orchestrates workflows, validation, and decisions; no direct external calls.

3.  Service layer provides stateless adapters to external systems (LLM, SD, Storage, Prereqs, PALD schema registry, FL).

4.  Data layer holds models, repositories, and migrations; no business logic.

5.  No cross‑layer shortcuts; interfaces/ports define boundaries.

6.  New features must reuse existing interfaces/patterns.

**Requirement 2: Identity, Pseudonym & Consent**

**User Story:** As a participant, I want privacy‑preserving interaction so my research data is stored under a pseudonym.

**Acceptance Criteria**

1.  After login/registration, creation of a unique **pseudonym** is mandatory before any research data is collected.

2.  **pseudonym_id** is the primary foreign key for research data (consents, surveys, PALD, chat, images, feedback).

3.  Multi‑step consent (data protection, AI interaction, study participation) must be **granted** before AI operations.

4.  Consent withdrawal immediately blocks further processing and marks downstream operations as forbidden.

5.  Mapping between user_id and pseudonym_id is segregated and access controlled.

6.  A user‑initiated "delete my study data" deletes by pseudonym (cascading).

**Requirement 3: Study Onboarding & Dynamic Survey**

**User Story:** As a researcher, I need a robust onboarding flow that collects structured data via external survey files.

**Acceptance Criteria**

1.  Sequential flow: Registration → Pseudonym → Consent → **Dynamic Survey** → Chat.

2.  Surveys are loaded from Excel/CSV (schema: question_id, question_text, type\[text\|number\|choice\|multi-choice\], options, required).

3.  Optional randomization of question order; strict validation for required items.

4.  Survey results are stored under **survey_responses** (not in PALD).

5.  On submit, the system transitions to chat automatically if validation passes.

**Requirement 4: PALD Boundary (Embodiment‑Only) & Data Separation**

**User Story:** As a system owner, I want PALD to contain **only embodiment‑related** data to avoid schema pollution.

**Acceptance Criteria**

1.  PALD includes structured embodiment attributes from: (a) user descriptions, (b) actual images, (c) implicit cues in prompts and LLM answers.

2.  Non‑embodiment data (survey responses, onboarding metadata, preferences) is **rejected** by boundary validation and routed to proper tables.

3.  Deny‑lists for non‑embodiment keys are enforced; violations are logged (audit/WAL) with clear errors.

4.  Only flows in embodiment context may write PALD.

**Requirement 5: Runtime PALD Schema Loading & Versioning**

**User Story:** As an operator, I need to update PALD schemas at runtime without code changes.

**Acceptance Criteria**

1.  Active schema is loaded from config/pald_schema.json with caching and modification detection.

2.  Fallback to an embedded default on load/validation failure; checksum/logging is recorded.

3.  Schema versions are tracked; loading performance is monitored.

**Requirement 6: Mandatory PALD Extraction (PALD Light)**

**User Story:** As a product owner, I need reliable extraction of embodiment features for prompt compression.

**Acceptance Criteria**

1.  **Mandatory** PALD extraction from user text, prompts, LLM answers, and image descriptions is always enabled.

2.  The system produces PALD Light and a compressed prompt (≤77 tokens) for image generation.

3.  Validation against current schema; errors are logged with recovery to minimal viable PALD.

**Requirement 7: Consistency Loop (Description ↔ Image)**

**User Story:** As a user, I want the avatar to match the description.

**Acceptance Criteria**

1.  Compare PALD from user description with PALD from image description; classify fields {match\|hallucination\|missing}.

2.  Iterate until threshold or MAX_FEEDBACK_ROUNDS reached; store per‑round data (params, timestamps).

3.  Report a similarity score and a human‑readable summary.

**Requirement 8: PALD Schema Evolution & Governance**

**User Story:** As a data steward, I want controlled evolution when new embodiment attributes appear.

**Acceptance Criteria**

1.  Out‑of‑schema fields become **candidates** with occurrence counting (no raw text retention).

2.  Governance UI/process: approve/reject; optional **auto‑approve** when threshold met.

3.  Approved fields create a new schema version and optional data migrations; backward‑compatibility preserved.

**Requirement 9: Deferred & Optional Bias Analysis**

**User Story:** As a researcher, I want bias analysis but without blocking core flows.

**Acceptance Criteria**

1.  Bias analysis is separable from mandatory PALD extraction; can be **deferred** to a queue.

2.  Analyses may include age shift, gender conformity/sexualization indicators, ethnicity/skin tone consistency, occupational stereotypes, ambivalent patterns, multiple stereotyping patterns.

3.  Results are stored; failures do not block the main flow; metrics recorded.

**Requirement 10: LLM Chat & Image Generation**

**User Story:** As a user, I want responsive chat and robust image creation.

**Acceptance Criteria**

1.  LLM via **Ollama** with model mapping in config; TTFT median ≤ 2s, p95 ≤ 5s (streaming allowed).

2.  Stable Diffusion default runwayml/stable-diffusion-v1-5, 512×512 p95 ≤ 30s on GPU (fallback CPU/dummy).

3.  Model/provider selection is **config‑driven**, no code changes required.

4.  Full audit (inputs/outputs/params/tokens/latency/request‑id).

**Requirement 11: Feedback Rounds**

**User Story:** As a participant, I want to iteratively refine my avatar.

**Acceptance Criteria**

1.  Configurable MAX_FEEDBACK_ROUNDS; store round index, timestamps, input, output, parameters.

2.  Early stop is supported; state is consistent on exit.

**Requirement 12: Image Isolation, Quality Checks & User Correction**

**User Story:** As a user, I want a clean, high‑quality final avatar with a say in corrections.

**Acceptance Criteria**

1.  **Timing:** After the feedback loop and **before** final delivery.

2.  Automatic **person isolation**; background becomes transparent (PNG) or uniform color (config).

3.  Store **both** original and isolated versions; isolated shown by default if successful.

4.  **Quality detection:** reasons include no_person_detected, multiple_people_detected, wrong_subject_type, poor_quality (+ confidence).

5.  If all in batch fail, trigger regeneration with modified parameters.

6.  **Correction dialog:** side‑by‑side original/processed; interactive crop/selection; "Use original", "Adjust", "Garbage/Regenerate", "Accept".

7.  Real‑time feedback ≤100ms; accessibility compliant; learning from corrections (parameter tuning).

**Requirement 13: Prerequisite Checks & Contextual Tooltips**

**User Story:** As a newcomer, I want guidance and clear system prechecks.

**Acceptance Criteria**

1.  Prereq suite validates at startup and at key points (registration, chat start, image generation): Ollama, DB, consent status, storage, GPU.

2.  Feature‑flagged categories: **required, recommended, optional**; TTL caching for results.

3.  Checklist UI with re‑run and auto re‑enable; detailed resolution steps.

4.  Tooltips for critical UI elements, especially disabled controls; keyboard/screenreader accessible; contextual reasons included.

**Requirement 14: Federated Learning (Optional)**

**User Story:** As a researcher, I want privacy‑preserving global improvements.

**Acceptance Criteria**

1.  FL is feature‑flagged and **off by default**.

2.  Only **structured signals** are used (PALD slots, feedback clicks, consistency labels); **no raw texts or images** transferred.

3.  Aggregation with FedAvg; Differential Privacy parameters (clip/noise) are config‑driven.

4.  Full audit and monitoring of participation.

**Requirement 15: Centralized Configuration (config.py)**

**User Story:** As an operator, I want to change behavior without code edits.

**Acceptance Criteria**

1.  Single Source of Truth for feature flags, model mappings, timeouts, file paths (e.g., PALD_SCHEMA_FILE_PATH), internationalization texts, environment overrides.

2.  Validation of settings with safe defaults; restart may be required but no code change.

3.  Example flags:

    - MANDATORY_PALD_EXTRACTION=True (must remain true)

    - ENABLE_BIAS_ANALYSIS / PALD_ANALYSIS_DEFERRED

    - ENABLE_PALD_AUTO_EXTENSION, PALD_CANDIDATE_MIN_SUPPORT

    - MAX_FEEDBACK_ROUNDS, IMAGE_BACKGROUND_MODE

    - Prereq categories & TTL.

**Requirement 16: Data Model, Storage & Admin Reset**

**User Story:** As an admin, I want clean persistence and a safe reset for experiments.

**Acceptance Criteria**

1.  Postgres ≥13 (UTF‑8); images stored in S3/MinIO (FS fallback). DB stores only URIs/paths for images.

2.  Core tables include: pseudonyms, consents, survey_responses, chat_messages, pald_data, generated_images, feedback_records, onboarding_progress, schema_versions, schema_field_candidates, image_processing_results, image_corrections, prerequisite_checks, audit_logs.

3.  Admin reset tool: drop & recreate relevant tables with FK integrity; logs reset events.

**Requirement 17: Security, GDPR & Deletion**

**User Story:** As a participant, I want my data protected and deletable.

**Acceptance Criteria**

1.  Pseudonymization default; TLS ≥1.2; backups/exports encrypted (AES‑256).

2.  Deletion by pseudonym is cascaded within 72h; audited.

3.  DPIA readiness; breach response plan; role‑based access control to sensitive features (e.g., bias results, schema governance).

**Requirement 18: Performance & Accessibility**

**User Story:** As a user, I want speed and accessibility.

**Acceptance Criteria**

1.  LLM TTFT median ≤2s, p95 ≤5s; SD 512×512 p95 ≤30s (GPU).

2.  Prereq suite ≤5s; tooltips appear ≤200ms; correction dialog ≤1s to open.

3.  WCAG 2.1 AA: keyboard navigation, ARIA labels, contrast, text alternatives, error announcements.

4.  After greeting/name, screen clears to show only the chat; chat input appears at the right step.

**Requirement 19: Audit & Write‑Ahead Logging (WAL)**

**User Story:** As an auditor, I need full traceability of AI operations.

**Acceptance Criteria**

1.  WAL **before** each AI call; finalization with input, output, model, parameters, token counts, latency, timestamps.

2.  Parent‑child links for multi‑step flows; request IDs propagated.

3.  Export to CSV/JSON; monthly completeness ≥99%.

**Requirement 20: Deployment, CI/CD & Tests**

**User Story:** As a developer, I need reproducible environments and robust tests.

**Acceptance Criteria**

1.  Docker Compose stack (App, Postgres, optional MinIO, Ollama; + optional Redis/queue).

2.  Makefile targets for dev, test, migrate, seed, run.

3.  CI runs unit/integration/smoke tests (chat roundtrip, image generation, audit row write).

4.  Tests cover Pseudonym/Consent/Survey/PALD boundary & evolution/Consistency loop/Prereqs/Bild‑Pipeline/Admin‑Reset/FK integrity.

5.  Arc42/ADRs: architecture artifacts maintained.

**Requirement 21: Error Handling & Recovery**

**User Story:** As a user, I want graceful fallbacks instead of dead ends.

**Acceptance Criteria**

1.  Image isolation errors fall back to original (with notification); quality check errors warn and may accept image.

2.  Prereq check failures use cached results when safe; tooltip fallback text shown on load errors.

3.  Correction dialog failures allow default processed image; manual crop coordinates accepted when real‑time fails.

4.  Any critical feature failure degrades gracefully, disables the feature, and continues with notification.

**Requirement 22: Metrics & Success Criteria**

**User Story:** As a project owner, I need measurable outcomes.

**Acceptance Criteria**

1.  Zero data loss in migrations (verified by counts and integrity checks).

2.  Schema loading success ≥99.9%; boundary validation overhead \<50ms p95.

3.  False positives of boundary violations \<1%.

4.  Availability 99.5% (business hours); critical flow error rate \<1%.

**Requirement 23: Traceability & Governance**

**User Story:** As a reviewer, I want to map requirements to code and tests.

**Acceptance Criteria**

1.  Each requirement is traceable to modules, tests, and (where applicable) migrations.

2.  Changes in PALD schema versions and governance decisions are logged with rationale.

**Notes**

- The **final avatar delivery** always passes through isolation/quality/correction per Requirement 12.

- **PALD contains embodiment only**; evolution is governed (Req. 4 & 8).

- **FL is optional** and privacy‑preserving (Req. 14).

- **Config is authoritative** (Req. 15).
