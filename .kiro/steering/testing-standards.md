# Testing Standards

## 1. Test Pyramid
- Unit → Integration → E2E (pyramid shape)
- Coverage: **85% global**, **90% services/**
- Unit tests: pure functions and core business logic
- Integration tests: ports/adapters, external API integration (controlled env)
- E2E tests: minimal critical-path scenarios

## 2. Determinism
- **All tests must be deterministic**:
  - Fixed seeds for RNG (e.g., `HYPOTHESIS_PROFILE=ci`)
  - Time access via `Clock` interface (no `datetime.now()` or `time.time()` directly in src/)
  - Randomness via `Rng` interface (no `random.*` directly in src/)
- Property-based tests must set a fixed seed in CI to ensure reproducibility.

## 3. Fixture Policy
- **No large static fixtures**:
  - Size limit: ≤ 5 KB or ≤ 150 lines
  - Use small, in-test literals or data factories/builders in `tests/factories/`
- No committed live HTTP responses or recorded traffic.

## 4. Mock Policy
- **No use of mocking/patching libraries**:
  - Disallow: `unittest.mock`, `pytest-mock`, `monkeypatch`, `responses`, `requests_mock`
  - Exception: `monkeypatch` is allowed **only for reproducible 3rd-party/framework bugs** that cannot be fixed otherwise (e.g., StableDiffusion blocking Streamlit run loop).
    - Must be documented with comment `# allowed-monkeypatch: <short reason>` directly above usage.
- No fake implementations to bypass core logic.
- Replace with:
  - Pure functions for core logic (test directly)
  - Real adapters tested via ports (contract tests)
  - Controlled in-memory/local resources for integration

## 5. Required Test Types
Every new feature or refactor must include **at least**:
- **1 Contract test** per new or changed port/adapter
- **1 Property-based test** for key business invariants
- **1 Type-oriented test** (mypy/typeguard) for public API correctness

## 6. Test Structure
tests/
  - contracts/   # Contract tests for ports/adapters
  - properties/  # Hypothesis property tests
  - types/       # Type-oriented tests
  - factories/   # Data builders/factories for tests

## 7. Markers & CI
- Markers: `slow`, `gpu`, `e2e`
- CI:
  - Exclude `gpu` by default
  - Run `-m "not slow and not e2e"` on main pipeline
  - Nightly can include slow/e2e

## 8. Consent Contract Tests
- Positive: alias normalization (e.g., "data_processing" → `StudyConsentType.data_protection`).
- Negative: unknown key raises typed error with valid enum list in message.

## 9. Consent FK Contract
- When `study_consent_records` is written:
  - Test must assert existence/ownership pre-check for `pseudonym_id`.
  - Provide a red-path test where the pseudonym is missing → expect typed NotFound/Ownership error.
