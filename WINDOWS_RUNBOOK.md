# Windows Development Runbook for GITTE

## Quick Start (5 Minutes)

```powershell
# 1. Clone and enter directory
git clone <repository-url> gitte
cd gitte

# 2. Run automated setup
.\tools\smoke_run.ps1

# 3. Start application (if setup succeeded)
streamlit run src/ui/main.py
```

**Access**: http://localhost:8501

## Manual Setup (If Automated Fails)

### Prerequisites Check

```powershell
# Check Python
python --version  # Should be 3.11+

# Check Git
git --version

# Check Docker (optional)
docker --version
docker-compose --version

# Check PowerShell execution policy
Get-ExecutionPolicy
# If Restricted, run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step-by-Step Setup

#### 1. Python Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (CMD)
venv\Scripts\activate.bat

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Environment Configuration

```powershell
# Copy environment template
copy .env.example .env

# Edit .env file (use notepad, VS Code, or any editor)
notepad .env
```

**Key settings for .env:**
```bash
ENVIRONMENT=development
POSTGRES_DSN=postgresql://gitte:sicheres_passwort@localhost:5432/kiro_test
OLLAMA_URL=http://localhost:11434
FEATURE_ENABLE_MINIO_STORAGE=false
LOG_LEVEL=INFO
```

#### 3. Database Setup

**Option A: Docker (Recommended)**
```powershell
# Start PostgreSQL only
docker-compose -f docker-compose.dev.yml up -d postgres

# Wait for startup (30 seconds)
Start-Sleep -Seconds 30

# Run migrations
python -m alembic upgrade head
```

**Option B: Local PostgreSQL**
```powershell
# Install PostgreSQL (if not installed)
# Download from: https://www.postgresql.org/download/windows/

# Create database
psql -U postgres -c "CREATE DATABASE kiro_test;"
psql -U postgres -c "CREATE USER gitte WITH PASSWORD 'sicheres_passwort';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE kiro_test TO gitte;"

# Run migrations
python -m alembic upgrade head
```

#### 4. Optional Services

**Ollama (LLM Service)**
```powershell
# Download and install Ollama
# From: https://ollama.ai/download

# Start Ollama
ollama serve

# Pull a model (in new terminal)
ollama pull llama2
```

**MinIO (Object Storage) - Optional**
```powershell
# Using Docker
docker-compose -f docker-compose.dev.yml up -d minio

# Access console: http://localhost:9001 (minioadmin/minioadmin)
```

#### 5. Verification

```powershell
# Check system health
python tools/check_system_health.py

# Run smoke tests
python tools/smoke_e2e.py

# Start application
streamlit run src/ui/main.py
```

## Development Workflow

### Daily Startup

```powershell
# 1. Activate Python environment
.\venv\Scripts\Activate.ps1

# 2. Start services (if using Docker)
docker-compose -f docker-compose.dev.yml up -d

# 3. Check system health
python tools/check_system_health.py

# 4. Start development server
streamlit run src/ui/main.py
```

### Testing

```powershell
# Run all tests
pytest

# Run specific test categories
pytest tests/contracts/
pytest tests/properties/
pytest -m integration

# Run with coverage
pytest --cov=src tests/

# Quick smoke test
python tools/smoke_e2e.py
```

### Database Operations

```powershell
# Check migration status
python -m alembic current

# Create new migration
python -m alembic revision --autogenerate -m "description"

# Apply migrations
python -m alembic upgrade head

# Rollback migration
python -m alembic downgrade -1

# Reset database (DANGER!)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d postgres
python -m alembic upgrade head
```

### Code Quality

```powershell
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

## Troubleshooting

### Common Issues

#### "Python not found"
```powershell
# Check if Python is in PATH
where python

# If not found, add to PATH or use full path
C:\Python311\python.exe -m venv venv
```

#### "Execution policy error"
```powershell
# Allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Or run with bypass
powershell -ExecutionPolicy Bypass -File .\tools\smoke_run.ps1
```

#### "Database connection failed"
```powershell
# Check if PostgreSQL is running
docker-compose -f docker-compose.dev.yml ps postgres

# Check connection manually
python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://gitte:sicheres_passwort@localhost:5432/kiro_test')
    print('✅ Database connection OK')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"

# Reset database
docker-compose -f docker-compose.dev.yml down postgres
docker-compose -f docker-compose.dev.yml up -d postgres
```

#### "Port already in use"
```powershell
# Check what's using port 8501
netstat -ano | findstr :8501

# Kill process (replace PID)
taskkill /PID <PID> /F

# Or use different port
streamlit run src/ui/main.py --server.port 8502
```

#### "Module not found"
```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

#### "Ollama not responding"
```powershell
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama manually
ollama serve

# Check if model is installed
ollama list

# Pull a model if none exist
ollama pull llama2
```

#### "Streamlit won't start"
```powershell
# Clear Streamlit cache
streamlit cache clear

# Remove Streamlit config
Remove-Item -Recurse -Force $env:USERPROFILE\.streamlit

# Start with verbose logging
streamlit run src/ui/main.py --logger.level debug
```

### Performance Issues

#### Slow startup
```powershell
# Disable heavy features
$env:FEATURE_ENABLE_IMAGE_GENERATION="false"
$env:PREREQUISITE_CHECKS_ENABLED="false"

# Use SQLite for development
$env:POSTGRES_DSN="sqlite:///./dev.db"

# Start with minimal features
streamlit run src/ui/main.py
```

#### Memory issues
```powershell
# Check memory usage
Get-Process python | Select-Object ProcessName,WorkingSet

# Reduce cache sizes in .env
$env:MAX_CACHE_SIZE_MB="128"
$env:CACHE_TTL_SECONDS="1800"
```

### Network Issues

#### Docker networking
```powershell
# Reset Docker networks
docker network prune -f

# Recreate services
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

#### Firewall issues
```powershell
# Check Windows Firewall
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Python*"}

# Allow Python through firewall (run as Administrator)
New-NetFirewallRule -DisplayName "Python" -Direction Inbound -Program "C:\Python311\python.exe" -Action Allow
```

## Production Deployment

### Environment Preparation

```powershell
# Set production environment
$env:ENVIRONMENT="production"

# Use strong secrets
$env:SECRET_KEY="<generate-strong-key>"
$env:ENCRYPTION_KEY="<generate-strong-key>"

# Production database
$env:POSTGRES_DSN="postgresql://user:pass@prod-server:5432/gitte"
```

### Docker Production

```powershell
# Build production image
docker build -f Dockerfile.prod -t gitte:latest .

# Run production stack
docker-compose -f docker-compose.prod.yml up -d

# Check health
docker-compose -f docker-compose.prod.yml ps
```

### Windows Service (Optional)

```powershell
# Install NSSM (Non-Sucking Service Manager)
# Download from: https://nssm.cc/download

# Create service
nssm install GITTE "C:\path\to\venv\Scripts\python.exe"
nssm set GITTE Arguments "C:\path\to\gitte\src\ui\main.py"
nssm set GITTE AppDirectory "C:\path\to\gitte"

# Start service
nssm start GITTE
```

## Monitoring and Maintenance

### Health Checks

```powershell
# Quick health check
python tools/check_system_health.py

# Full system test
python tools/smoke_e2e.py

# Check logs
docker-compose -f docker-compose.dev.yml logs gitte-app
```

### Backup and Recovery

```powershell
# Backup database
docker exec -t postgres_container pg_dump -U gitte kiro_test > backup.sql

# Restore database
docker exec -i postgres_container psql -U gitte kiro_test < backup.sql

# Backup generated images
Compress-Archive -Path generated_images -DestinationPath images_backup.zip
```

### Updates and Maintenance

```powershell
# Update dependencies
pip install -r requirements.txt --upgrade

# Update Docker images
docker-compose -f docker-compose.dev.yml pull
docker-compose -f docker-compose.dev.yml up -d

# Clean up Docker
docker system prune -f
```

## Emergency Procedures

### Complete Reset

```powershell
# Stop all services
docker-compose -f docker-compose.dev.yml down -v

# Remove virtual environment
Remove-Item -Recurse -Force venv

# Clean Python cache
Get-ChildItem -Path . -Recurse -Name "__pycache__" | Remove-Item -Recurse -Force

# Start fresh
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\tools\smoke_run.ps1
```

### Rollback Changes

```powershell
# See IMPACT_MATRIX_AND_ROLLBACK.md for detailed procedures

# Quick rollback to working state
git stash
git checkout main
.\tools\smoke_run.ps1
```

### Get Help

1. **Check logs**: `docker-compose logs <service>`
2. **Run diagnostics**: `python tools/check_system_health.py`
3. **Test connectivity**: `python tools/smoke_e2e.py`
4. **Review configuration**: Check `.env` file
5. **Restart services**: `docker-compose restart`

---

**Windows Version Tested**: Windows 10/11, PowerShell 5.1+
**Last Updated**: Generated during build-and-test implementation
**Support**: Run health checks first, then consult troubleshooting section