# Development Rules for GITTE in KIRO

## 1. Test Modification Policy
- Never edit, delete, or comment out existing unit tests just to “make them pass”.
- Allowed test changes:
  1. Syntax/format fixes (unterminated strings, broken imports, line endings).
  2. Refactor-induced path/API adjustments when the public contract changed per updated spec.
  3. Stabilizing flaky tests (freeze time via Clock, seed RNG via Rng, use temp dirs) without weakening assertions.
- Any commit modifying `tests/` outside `tests/contracts/`, `tests/properties/`, `tests/types/` must:
  - Include `[ALLOW-TEST-CHANGE]` in the commit subject.
  - Explain **Reason**, **Spec Reference**, **Scope**, and **Before→After** in the commit body.
- Prefer fixing implementation code over tests.
- **No mocks**: Do not introduce or reintroduce mocking/patching libs (see Testing Standards).

## 2. Layered Architecture
- Maintain strict separation:
  - **UI Level**: Streamlit UI only (no business logic)
  - **Logic Level**: Orchestration & decision-making
  - **Service Level**: Access to external data, APIs, files (via defined ports/adapters)
  - **Data Level**: Data schemas, storage
- Ports (interfaces) live in Logic/Service level, adapters in Service level
- Contract tests verify adapters through their ports
- No cross-layer calls except via defined interfaces

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
