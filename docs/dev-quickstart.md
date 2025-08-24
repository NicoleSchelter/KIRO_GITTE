# GITTE Development Quickstart (Windows)

This guide gets you up and running with GITTE on Windows in under 10 minutes.

## Prerequisites

- **Python 3.11+** (required)
- **Git** (required)
- **Docker Desktop** (optional, recommended)
- **PostgreSQL** (if not using Docker)

## Quick Start

### Option 1: Automated Setup (Recommended)

```powershell
# Clone and setup in one command
git clone <repository-url> gitte
cd gitte
.\tools\smoke_run.ps1
```

This script will:
- ✅ Create Python virtual environment
- ✅ Install dependencies
- ✅ Start Docker services (PostgreSQL, Ollama, MinIO)
- ✅ Run database migrations
- ✅ Execute smoke tests
- ✅ Provide next steps

### Option 2: Manual Setup

```powershell
# 1. Setup Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configure environment
copy .env.example .env
# Edit .env with your settings

# 3. Start services
docker-compose -f docker-compose.dev.yml up -d

# 4. Setup database
python -m alembic upgrade head

# 5. Run smoke test
python tools/smoke_e2e.py

# 6. Start application
streamlit run src/ui/main.py
```

## Configuration

### Environment Variables (.env)

```bash
# Database
POSTGRES_DSN=postgresql://gitte:sicheres_passwort@localhost:5432/kiro_test

# LLM Service
OLLAMA_URL=http://localhost:11434

# Storage (optional)
MINIO_ENDPOINT=localhost:9000
FEATURE_ENABLE_MINIO_STORAGE=false  # Use filesystem fallback

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
```

### Service URLs

- **Application**: http://localhost:8501
- **Database**: localhost:5432 (gitte/sicheres_passwort)
- **Ollama**: http://localhost:11434
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Adminer**: http://localhost:8080 (if using admin profile)

## Development Workflow

### Daily Development

```powershell
# Start services
docker-compose -f docker-compose.dev.yml up -d

# Activate environment
.\venv\Scripts\Activate.ps1

# Start development server
streamlit run src/ui/main.py

# Run tests
pytest tests/

# Check system health
python tools/check_system_health.py
```

### Database Operations

```powershell
# Create migration
python -m alembic revision --autogenerate -m "description"

# Apply migrations
python -m alembic upgrade head

# Check migration status
python -m alembic current

# Rollback migration
python -m alembic downgrade -1
```

### Testing

```powershell
# Run all tests
pytest

# Run specific test file
pytest tests/test_specific.py

# Run with coverage
pytest --cov=src tests/

# Run smoke test
python tools/smoke_e2e.py

# Run integration tests only
pytest -m integration
```

## Troubleshooting

### Common Issues

**Database Connection Failed**
```powershell
# Check if PostgreSQL is running
docker-compose -f docker-compose.dev.yml ps postgres

# Check connection manually
python -c "from src.data.database import health_check; print(health_check())"

# Reset database
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d postgres
```

**Ollama Not Available**
```powershell
# Check Ollama status
curl http://localhost:11434/api/tags

# Start Ollama manually
ollama serve

# Pull a model
ollama pull llama2
```

**Import Errors**
```powershell
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

**Streamlit Issues**
```powershell
# Clear Streamlit cache
streamlit cache clear

# Reset Streamlit config
rm -rf ~/.streamlit/

# Check port availability
netstat -an | findstr :8501
```

### Health Checks

```powershell
# Quick system check
python tools/check_system_health.py

# Full smoke test
python tools/smoke_e2e.py

# Check prerequisites
python -c "
from src.services.prerequisite_checker import PrerequisiteValidationService
service = PrerequisiteValidationService()
results = service.run_all_checks()
print(f'Status: {results.overall_status.value}')
"
```

### Performance Issues

**Slow Startup**
- Disable GPU features: `FEATURE_ENABLE_IMAGE_GENERATION=false`
- Use SQLite for development: `POSTGRES_DSN=sqlite:///./dev.db`
- Skip prerequisite checks: `PREREQUISITE_CHECKS_ENABLED=false`

**Memory Issues**
- Reduce cache sizes in .env
- Use CPU-only image generation
- Limit concurrent operations

## IDE Setup

### VS Code

Recommended extensions:
- Python
- Pylance
- Black Formatter
- GitLens
- Docker

Settings (`.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true
}
```

### PyCharm

1. Open project directory
2. Configure Python interpreter: `./venv/Scripts/python.exe`
3. Set source root: `src/`
4. Configure run configuration for `src/ui/main.py`

## Production Deployment

### Docker Production

```powershell
# Build production image
docker build -f Dockerfile.prod -t gitte:latest .

# Run with production compose
docker-compose -f docker-compose.prod.yml up -d
```

### Environment-Specific Configs

```bash
# Production
ENVIRONMENT=production
POSTGRES_DSN=postgresql://user:pass@prod-db:5432/gitte
SECRET_KEY=<strong-secret-key>
ENCRYPTION_KEY=<strong-encryption-key>

# Staging
ENVIRONMENT=staging
POSTGRES_DSN=postgresql://user:pass@staging-db:5432/gitte

# Testing
ENVIRONMENT=testing
POSTGRES_DSN=sqlite:///./test.db
```

## Getting Help

1. **Check logs**: `docker-compose logs <service>`
2. **Run health check**: `python tools/check_system_health.py`
3. **Check documentation**: `docs/` directory
4. **Review configuration**: `config/config.py`
5. **Test prerequisites**: `python tools/smoke_e2e.py`

## Next Steps

After successful setup:

1. **Explore the UI**: Visit http://localhost:8501
2. **Review architecture**: Check `docs/` for system design
3. **Run tests**: Execute `pytest` to ensure everything works
4. **Start developing**: Modify code and see changes live
5. **Check admin interface**: Login as admin to explore features

---

**Need help?** Run `python tools/check_system_health.py` for diagnostics.