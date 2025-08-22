# Test Recommendations (auto-derived from snapshot)

Generated: 2025-08-21 12:13

Below are suggested tests per module. Create tests under `tests/` mirroring the layer structure.

- `src/ui/accessibility.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/accessible_chat_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/admin_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/auth_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/chat_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/consent_integration_example.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/consent_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/contracts.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/error_monitoring_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/image_correction_dialog.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/image_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/main.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/onboarding_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/prerequisite_checklist_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/prerequisite_integration.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/survey_ui.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/tooltip_content_manager.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/tooltip_integration.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/ui/tooltip_system.py` → UI smoke test + snapshot of rendered components; integration test via Streamlit script runner.
- `src/logic/audit.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/authentication.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/consent.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/embodiment.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/federated_learning.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/image_correction.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/llm.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/onboarding.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/pald.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/logic/prerequisite_validation.py` → Pure unit tests on business rules; property-based tests for PALD transformations.
- `src/services/admin_statistics_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/audit_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/batch_error_handler.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/bias_worker.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/caching_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/consent_middleware.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/consent_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/database_optimization_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/error_monitoring_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/federated_learning_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/image_isolation_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/image_provider.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/image_quality_detector.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/image_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/job_queue.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/lazy_loading_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/llm_provider.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/llm_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/monitoring_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/pald_schema.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/pald_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/performance_monitoring_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/prerequisite_checker.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/session_manager.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/services/storage_service.py` → Integration tests with test doubles; timeout/retry behavior; error mapping; performance thresholds.
- `src/data/database.py` → Repository CRUD tests against a temporary DB; schema migration tests if any.
- `src/data/models.py` → Repository CRUD tests against a temporary DB; schema migration tests if any.
- `src/data/repositories.py` → Repository CRUD tests against a temporary DB; schema migration tests if any.
- `src/data/schemas.py` → Repository CRUD tests against a temporary DB; schema migration tests if any.
- `src/utils/circuit_breaker.py` → Unit tests for helpers; ensure deterministic behavior.
- `src/utils/error_handler.py` → Unit tests for helpers; ensure deterministic behavior.
- `src/utils/logging.py` → Unit tests for helpers; ensure deterministic behavior.
- `src/utils/ux_error_handler.py` → Unit tests for helpers; ensure deterministic behavior.

## Minimal Critical Path (if time-limited)
- services/prerequisite_checker.py
- services/pald_service.py
- services/llm_service.py
- logic/pald.py
- ui/main.py + ui/chat_ui.py
