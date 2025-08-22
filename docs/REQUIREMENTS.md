# Functional & Non-Functional Requirements (Traceability)

Generated: 2025-08-21 12:13

## Functional
- User authentication & consent capture
- Chat interaction with LLM backends
- PALD light extraction, deferred heavy analysis job
- Image isolation/correction workflow
- Monitoring & error surfacing in UI

## Non-Functional
- Accessibility (screen reader hints, keyboard nav)
- Observability (logs, metrics, error IDs)
- Configurability via `config/config.py` + env vars
- Performance: responsive UI + bounded retries

## Traceability (example mapping)
- `logic/pald.py` ↔ PALD extraction
- `services/pald_service.py` ↔ persistence + schema
- `services/llm_service.py` ↔ LLM calls
- `services/prerequisite_checker.py` ↔ environment gate
- `ui/*` ↔ interaction & rendering
