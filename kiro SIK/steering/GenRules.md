# Development Rules for KIRO

These rules define how KIRO should work when implementing tasks for the PM Analysis Tool project.

## General Principles
1. **Do not modify tests (with narrow exceptions)**
   - Never edit, delete, or comment out existing unit tests to “make them pass”.
   - Allowed test changes are strictly limited to:
     a) Syntax/format fixes (unterminated strings, broken imports, line endings).
     b) Refactor-induced path/API adjustments when the public contract was intentionally changed and updated in the spec.
     c) Stabilization of flaky tests (freeze time, seed RNG, use temp dirs) without weakening assertions.
   - Process guardrails:
     - Any commit that modifies files under `tests/` must include `[ALLOW-TEST-CHANGE]` in the commit message subject.
     - The commit body must explain Reason, Spec reference, Scope, and Before→After behavior.
   - If a test fails, prefer fixing the implementation code. Only touch tests under the allowed cases above.

2. **Preserve Layered Architecture**  
   - Keep the strict separation between layers:
     - **UI Level**: Only display/input logic (Streamlit).
     - **Logic Level**: Application logic, decision-making, orchestration.
     - **Service Level**: Access to external data sources, file I/O, API calls.
     - **Data Level**: Data storage and schema definitions.
   - Do not move code between layers unless explicitly requested.

3. **Task Execution**
   - Complete all subtasks for a task before marking it as done.
   - If a task was previously aborted, resume it without overwriting already working code.
   - Only implement what is missing to make the task pass its requirements.
   - Do not abort a task after a single failure. On command failure, immediately:
      1) surface the full command and exit code,
      2) show the minimal failing test name and traceback,
      3) propose exactly one fix in implementation code (not tests),
      4) re-run only the targeted test (`pytest -q --maxfail=1 <test-or-module>`).


4. **Coding Style**
   - Follow existing naming conventions and patterns in the repository.
   - Maintain full type hinting for all functions and classes.
   - Keep functions small and focused on a single responsibility.

5. **Testing**
   - Always create or update implementation to ensure all tests pass.
   - New features must include corresponding unit tests (without altering existing ones).
   - Test coverage for new code must be as complete as existing patterns.
   - During development, prefer targeted tests to save time and resources:
      - run only the most relevant test module or `--last-failed` with `--maxfail=1`,
      - reserve the full test suite for pre-commit or continuous integration.
   - Do not ask for confirmation to run local test commands; execute them directly (via hooks or integrated terminal) and summarize results afterwards.


6. **Logging & Debugging**
   - Use the existing `logger` instead of print statements.
   - Preserve existing debug outputs if present in the original code.

7. **File Management**
   - Place new files in the appropriate directory based on their layer.
   - Maintain file structure and naming according to project conventions.

## 8. Automation & Hooks
   - Use runCommand-based hooks for routine actions (format, lint, typecheck, tests). Do not open chat sessions for these actions.
   - Avoid `askAgent` for local commands to prevent confirmation prompts and interaction budget usage.
   - Keep hooks silent unless failures occur; print concise error summaries with next-step suggestions.
   - Ensure commands run within the project’s virtual environment (correct Python interpreter selected).

---

**Purpose:**  
These rules ensure consistent, predictable, and maintainable code contributions from KIRO, aligned with the architectural and testing standards of the PM Analysis Tool project.
