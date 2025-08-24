# Development Rules for GITTE in KIRO

## 1. Test Modification Policy
- Never edit, delete, or comment out existing unit tests just to “make them pass”.
- Allowed test changes:
  1. Syntax/format fixes (unterminated strings, broken imports, line endings).
  2. Refactor-induced path/API adjustments when the public contract changed per updated spec.
  3. Stabilizing flaky tests (freeze time via Clock, seed RNG via Rng, use temp dirs) without weakening assertions.
  4. Adding or modifying `# allowed-monkeypatch` comments for permitted framework bug workarounds.
- Any commit modifying `tests/` outside `tests/contracts/`, `tests/properties/`, `tests/types/` must:
  - Include `[ALLOW-TEST-CHANGE]` in the commit subject.
  - Explain **Reason**, **Spec Reference**, **Scope**, and **Before→After** in the commit body.
- Prefer fixing implementation code over tests.
- **No mocks**: Do not introduce mocking/patching libs except where explicitly allowed (see Testing Standards).

## 2. Layered Architecture
- Maintain strict separation:
  - **UI Level**: Streamlit UI only (no business logic)
  - **Logic Level**: Orchestration & decision-making
  - **Service Level**: Access to external data, APIs, files (via defined ports/adapters)
  - **Data Level**: Data schemas, storage
- Ports (interfaces) live in Logic/Service level, adapters in Service level
- Contract tests verify adapters through their ports
- No cross-layer calls except via defined interfaces
- **Performance**: Heavy modules (e.g., StableDiffusion, large models) must be lazy-loaded in Streamlit so they initialize only when needed.

## 3. Task Execution
- Complete all subtasks before marking a task as done
- Resume aborted tasks without overwriting working code
- Implement only what is missing to meet requirements
- On command failure:
  1. Show the full command + exit code
  2. Show minimal failing test name + traceback
  3. Propose exactly one implementation fix
  4. Re-run only the targeted test (`pytest -q --maxfail=1 <file>`)

## 4. Coding Style
- Follow existing naming patterns
- Full type hints for all functions/classes
- Functions should be small & single-purpose
- Use `ruff` + `black` + `mypy` in strict mode for `services/`

## 5. Testing
- New features require matching unit tests
- Coverage for new code must meet or exceed repo baseline
- New features that touch external dependencies must have contract tests
- Core business rules must have property-based tests
- Public API changes must have type-oriented tests
- During dev: run targeted tests (`pytest --last-failed` or by module)
- Full suite runs in pre-commit/CI

## 6. Logging & Debugging
- Use the shared `logger`; avoid `print()`
- Preserve existing debug logs

## 7. File Management
- Place new files according to their layer
- Keep directory naming consistent

## 8. Automation & Hooks
- Prefer `runCommand` hooks over `askAgent` to save interaction budget
- Hooks should be silent unless failures occur
- Always use the project’s Python virtual environment

## 9. Consent & Enum Discipline (Must-Fail)
- Canonical consent types live only in `src/data/models.py` (`StudyConsentType`).
- UI renders keys from `config/config.py::CONSENT_TYPES_UI` (no hardcoded literals).
- Logic normalizes input strings to `StudyConsentType`; unknowns → typed error (list valid values).
- Repositories accept only `StudyConsentType` (or `.value`), never free-form strings.

## 10. Factory & Forward-Ref Hygiene
- Exactly one factory per service (`get_*_service|get_*_manager`).
- If a return annotation references a later class, the file must include:
  `from __future__ import annotations` at the top.
- Prefer defining factories **after** classes.

## 11. DB Import-Time Safety
- No `create_engine()` or `Session()` at import-time anywhere in `src`.
- Open sessions only via `get_session()`/factory **inside** functions/methods.

## 12. Consent Write Preconditions
- Any write to `study_consent_records` must prove:
  1) `pseudonym_id` exists and 2) belongs to the current user/context.
- Missing guard is a must-fail in pre-commit (`11-consent-fk-preconditions-audit.kiro.hook`).
