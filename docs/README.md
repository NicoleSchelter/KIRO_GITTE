# KIRO_GITTE

A modular Streamlit-based learning assistant (“GITTE”) with strict layer architecture:

- **UI Level** (`src/ui`): Streamlit UI only (no business logic).
- **Logic Level** (`src/logic`): Consent & business logic, PALD handling.
- **Service Level** (`src/services`): IO and infrastructure (LLM, storage, queues, image ops, monitoring).
- **Data Level** (`src/data`): Database engine, ORM models, repositories, schemas.
- **Utils** (`src/utils`): Cross-cutting helpers (logging, error handling, circuit breaker).

> This documentation set was generated from the uploaded project snapshot (src.zip).

## Quickstart (Windows PowerShell)

```powershell
# 1) Create & activate venv
py -3.10 -m venv .venv
. .venv\Scripts\Activate.ps1

# 2) Install dependencies
pip install -U pip wheel
pip install -r requirements.txt  # if present; otherwise install your standard stack

# 3) Environment (example values)
$env:POSTGRES_DSN = "postgresql://gitte:sicheres_passwort@localhost:5432/kiro_test"
$env:OLLAMA_URL   = "http://localhost:11434"
$env:SD_URL       = "http://localhost:7860"      # if using a local SD/WebUI
$env:LOG_LEVEL    = "INFO"

# 4) Run Streamlit UI
streamlit run src/ui/main.py
```

**Note:** `src/config.py` is a shim that re-exports from `config/config.py`. Ensure `config/config.py` exists on your PYTHONPATH with your central settings.

## Key Features

- Authentication & onboarding, consent UI
- Chat UI (LLM-backed via services)
- PALD extraction (+ light vs. deferred heavy stereotype analysis)
- Image isolation & correction dialog
- Monitoring and error handling with UX-friendly messaging
- Federated learning scaffolding

## Project Structure

```
src/
  ui/         # Streamlit UI only
  logic/      # business logic (consent, pald, onboarding...)
  services/   # LLM, storage, prerequisite checks, monitoring, queues, images
  data/       # database, models, repositories, schemas
  utils/      # logging, error handler, circuit breaker, UX error helper
  cli/        # CLI entrypoints (e.g., bias_worker)
  config.py   # shim -> config/config.py
```

## Configuration

Central config is expected in `config/config.py` and imported by `src/config.py`.

Environment variables commonly used:

- `POSTGRES_DSN` – SQLAlchemy DSN (example above)
- `OLLAMA_URL` – base URL for local LLM via Ollama
- `SD_URL` – base URL for local Stable Diffusion (if relevant)
- `LOG_LEVEL` – INFO/DEBUG/WARN/ERROR

Add additional flags for PALD behavior in `config/config.py` (e.g. `DEFER_BIAS_SCAN=True`, `PALD_LIGHT_ONLY=True`).

## Layering Rules

- **UI**: no DB/LLM calls directly; call **logic** functions only.
- **Logic**: orchestrates services; pure business decisions.
- **Services**: IO and integrations (LLM, DB via repositories, queues).
- **Data**: schema + repositories; services must not use UI.

## Run Tests

```powershell
pytest -q
pytest -q --maxfail=1 --disable-warnings
pytest --cov=src --cov-report=term-missing
```
