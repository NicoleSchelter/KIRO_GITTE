# Architecture (arc42-style)

**Version:** generated 2025-08-21 12:13

## 1. Goals & Purpose

- Provide a modular learning assistant with strict layering
- Support PALD extraction (light) and deferred heavy stereotype analysis
- Ensure accessibility, observability, and reliability

## 2. Constraints

- Layering: ui → logic → services → data (no cross-violations)
- Streamlit restricted to UI layer
- Local-first operation possible (Postgres, Ollama, SD)

## 3. Context

External systems:
- PostgreSQL (persistence)
- Ollama (LLM inference)
- Optional: Stable Diffusion/WebUI (image generation/correction)

## 4. Solution Strategy

- Central config in `config/config.py` (re-export via `src/config.py`)
- Services encapsulate integrations and are invoked by logic layer
- UI remains thin, rendering-only

## 5. Building Block View

- **UI**: `src/ui/main.py`, `chat_ui.py`, `auth_ui.py`, `image_ui.py`, tooltips
- **Logic**: `pald.py`, `authentication.py`, `onboarding.py`, `consent.py`
- **Services**: `pald_service.py`, `llm_service.py`, `prerequisite_checker.py`, `storage_service.py`, `monitoring_service.py`, `image_*`
- **Data**: `database.py`, `models.py`, `repositories.py`, `schemas.py`
- **Cross-cutting**: `utils/` (logging, errors, circuit breaker)

## 6. Runtime

1. User opens Streamlit → `ui/main.py`
2. `auth_ui` authenticates; `onboarding_ui` collects consent
3. `prerequisite_checker` validates environment (DB/LLM/SD)
4. Chat interactions call `logic/llm.py` → `services/llm_service.py`
5. PALD light extraction via `logic/pald.py` → `services/pald_service.py`
6. Heavy stereotype analysis optionally enqueued by `services/bias_worker.py`

## 7. Deployment

- Local dev (venv)
- Optional Docker compose for DB + Ollama + App

## 8. Cross-cutting Concepts

- Config flags for PALD behavior, retries, timeouts
- Structured error objects and UX-first error messages

## 9. Architecture Decisions (ADR snapshots)

- Keep Streamlit strictly in UI
- Re-export config through `src/config.py`
- Introduce `prerequisite_checker` before enabling features

## 10. Quality Scenarios

- If DB down → UI shows actionable recovery, circuit breaker prevents storms
- If LLM slow → timeouts + retries, progress banners in UI

## 11. Risks & Technical Debt

- Missing `config/config.py` may break boot
- Ensure test coverage for PALD flow + prerequisite checks

## 12. Glossary

- **PALD**: Persona & Activity Level Description
- **Light/Deferred**: fast extraction now; heavy analysis queued
