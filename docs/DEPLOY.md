# Deployment & Operations

Generated: 2025-08-21 12:13

This guide targets **local development** first, with optional Docker notes.

## Prerequisites

- Python 3.10+
- PostgreSQL (local or remote)
- Optional: Ollama (for local LLM), Stable Diffusion/WebUI for image tasks
- Windows PowerShell (commands below)

## Database

Create DB and user (example):
```powershell
psql -U postgres -h localhost -c "CREATE DATABASE kiro_test;"
psql -U postgres -h localhost -c "CREATE USER gitte WITH PASSWORD 'sicheres_passwort';"
psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE kiro_test TO gitte;"
```
Set DSN:
```powershell
$env:POSTGRES_DSN = "postgresql://gitte:sicheres_passwort@localhost:5432/kiro_test"
```

## Environment Variables

- `POSTGRES_DSN`
- `OLLAMA_URL` (e.g., `http://localhost:11434`)
- `SD_URL` (e.g., `http://localhost:7860`)
- `LOG_LEVEL` (default: INFO)

## Launch

```powershell
. .venv\Scripts\Activate.ps1
streamlit run src/ui/main.py
```

### Optional: Docker Compose (example)

Save as `docker-compose.example.yml` and adapt as needed.
```yaml
version: "3.9"
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: gitte
      POSTGRES_PASSWORD: sicheres_passwort
      POSTGRES_DB: kiro_test
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes:
      - ollama:/root/.ollama
  app:
    build: .
    environment:
      POSTGRES_DSN: postgresql://gitte:sicheres_passwort@db:5432/kiro_test
      OLLAMA_URL: http://ollama:11434
      LOG_LEVEL: INFO
    ports: ["8501:8501"]
    depends_on: [db, ollama]
    command: ["streamlit", "run", "src/ui/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
volumes:
  pgdata: {}
  ollama: {}
```

## Logging & Monitoring

- Central logging via `src/utils/logging.py`
- Error aggregation via `src/utils/error_handler.py` and `src/services/error_monitoring_service.py`
- Performance counters in `src/services/performance_monitoring_service.py`

## Backup & Rollback

- DB backups via `pg_dump`.
- Keep `.env` out of VCS, rotate secrets.
- For rollbacks: tag releases, use `git revert`, ensure DB migrations are reversible (if any).
