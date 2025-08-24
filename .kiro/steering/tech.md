# Tech Stack for GITTE

- Python 3.11+
- UI: Streamlit
- Services: FastAPI + Uvicorn
- Models: Ollama (LLM), SDXL (image) via adapters
- Package manager: uv or poetry
- Tooling: ruff, black, mypy, bandit, pytest, Playwright
- Observability: JSON logs, request IDs, `/health`, `/metrics`
- Environments: cpu (default), gpu (optional)
- DB Access: `get_session()` context manager only; never at import-time. 
- Config-driven UI: `CONSENT_TYPES_UI` in `config/config.py` controls visible consent toggles.