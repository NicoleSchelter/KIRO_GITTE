# PowerShell script for Windows development setup and smoke testing
# Run with: .\tools\smoke_run.ps1

param(
    [switch]$SkipDocker,
    [switch]$SkipMigrations,
    [switch]$SkipTests,
    [string]$PythonPath = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 GITTE Development Environment Setup (Windows)" -ForegroundColor Green
Write-Host "=" * 60

# Function to check if command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to wait for service
function Wait-ForService {
    param($Name, $Url, $MaxAttempts = 30)
    
    Write-Host "⏳ Waiting for $Name to be ready..." -ForegroundColor Yellow
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Head -TimeoutSec 5 -ErrorAction Stop
            if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 405) {
                Write-Host "✅ $Name is ready!" -ForegroundColor Green
                return $true
            }
        } catch {
            # Service not ready yet
        }
        
        Write-Host "   Attempt $i/$MaxAttempts - waiting 2 seconds..." -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
    
    Write-Host "❌ $Name failed to start within timeout" -ForegroundColor Red
    return $false
}

try {
    # 1. Check Prerequisites
    Write-Host "`n📋 Checking Prerequisites..." -ForegroundColor Cyan
    
    $prerequisites = @(
        @{Name="Python"; Command=$PythonPath; Required=$true},
        @{Name="Docker"; Command="docker"; Required=$false},
        @{Name="Docker Compose"; Command="docker-compose"; Required=$false},
        @{Name="Git"; Command="git"; Required=$true}
    )
    
    $missingRequired = @()
    
    foreach ($prereq in $prerequisites) {
        if (Test-Command $prereq.Command) {
            Write-Host "✅ $($prereq.Name) found" -ForegroundColor Green
        } else {
            if ($prereq.Required) {
                $missingRequired += $prereq.Name
                Write-Host "❌ $($prereq.Name) not found (REQUIRED)" -ForegroundColor Red
            } else {
                Write-Host "⚠️ $($prereq.Name) not found (optional)" -ForegroundColor Yellow
            }
        }
    }
    
    if ($missingRequired.Count -gt 0) {
        Write-Host "`n❌ Missing required prerequisites: $($missingRequired -join ', ')" -ForegroundColor Red
        Write-Host "Please install missing tools and try again." -ForegroundColor Red
        exit 1
    }
    
    # 2. Setup Python Environment
    Write-Host "`n🐍 Setting up Python Environment..." -ForegroundColor Cyan
    
    if (-not (Test-Path "venv")) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        & $PythonPath -m venv venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create virtual environment"
        }
    }
    
    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
    
    # Install/upgrade dependencies
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & python -m pip install --upgrade pip
    & pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dependencies"
    }
    
    # 3. Setup Environment Variables
    Write-Host "`n⚙️ Setting up Environment..." -ForegroundColor Cyan
    
    if (-not (Test-Path ".env")) {
        Write-Host "Creating .env from template..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
    }
    
    # Load environment variables
    if (Test-Path ".env") {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^([^#][^=]+)=(.*)$") {
                [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
            }
        }
    }
    
    # 4. Start Services (Docker or Manual)
    if (-not $SkipDocker -and (Test-Command "docker-compose")) {
        Write-Host "`n🐳 Starting Docker Services..." -ForegroundColor Cyan
        
        # Check if docker-compose.dev.yml exists, otherwise use docker-compose.yml
        $composeFile = if (Test-Path "docker-compose.dev.yml") { "docker-compose.dev.yml" } else { "docker-compose.yml" }
        
        Write-Host "Using compose file: $composeFile" -ForegroundColor Yellow
        
        # Start only infrastructure services (not the app)
        & docker-compose -f $composeFile up -d postgres minio redis
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️ Docker services failed to start, continuing with manual setup..." -ForegroundColor Yellow
        } else {
            # Wait for services to be ready
            $services = @(
                @{Name="PostgreSQL"; Url="http://localhost:5432"},
                @{Name="MinIO"; Url="http://localhost:9000/minio/health/live"},
                @{Name="Redis"; Url="http://localhost:6379"}
            )
            
            foreach ($service in $services) {
                # For PostgreSQL, we'll check differently since it's not HTTP
                if ($service.Name -eq "PostgreSQL") {
                    Write-Host "⏳ Waiting for PostgreSQL..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 5  # Give it time to start
                } else {
                    Wait-ForService $service.Name $service.Url
                }
            }
        }
        
        # Try to start Ollama if available
        try {
            & docker-compose -f $composeFile up -d ollama
            if ($LASTEXITCODE -eq 0) {
                Wait-ForService "Ollama" "http://localhost:11434/api/tags"
            }
        } catch {
            Write-Host "⚠️ Ollama not available in Docker, will try local installation" -ForegroundColor Yellow
        }
    } else {
        Write-Host "`n📝 Manual Service Setup Required..." -ForegroundColor Cyan
        Write-Host "Please ensure the following services are running:" -ForegroundColor Yellow
        Write-Host "  - PostgreSQL on localhost:5432" -ForegroundColor Gray
        Write-Host "  - Ollama on localhost:11434 (optional)" -ForegroundColor Gray
        Write-Host "  - MinIO on localhost:9000 (optional)" -ForegroundColor Gray
        Write-Host "  - Redis on localhost:6379 (optional)" -ForegroundColor Gray
    }
    
    # 5. Database Setup
    if (-not $SkipMigrations) {
        Write-Host "`n🗄️ Setting up Database..." -ForegroundColor Cyan
        
        # Wait a bit for PostgreSQL to be fully ready
        Start-Sleep -Seconds 3
        
        # Run migrations
        Write-Host "Running database migrations..." -ForegroundColor Yellow
        & python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️ Migrations failed, attempting to create tables directly..." -ForegroundColor Yellow
            
            # Try direct table creation
            & python -c "
from src.data.database import setup_database
try:
    setup_database()
    print('✅ Database setup completed')
except Exception as e:
    print(f'❌ Database setup failed: {e}')
    exit(1)
"
            if ($LASTEXITCODE -ne 0) {
                throw "Database setup failed"
            }
        }
    }
    
    # 6. Run Smoke Tests
    if (-not $SkipTests) {
        Write-Host "`n🧪 Running Smoke Tests..." -ForegroundColor Cyan
        
        & python tools/smoke_e2e.py
        $smokeResult = $LASTEXITCODE
        
        if ($smokeResult -eq 0) {
            Write-Host "`n🎉 All smoke tests passed!" -ForegroundColor Green
        } else {
            Write-Host "`n⚠️ Some smoke tests failed (exit code: $smokeResult)" -ForegroundColor Yellow
            Write-Host "System may still be usable, check test output above." -ForegroundColor Yellow
        }
    }
    
    # 7. Final Status and Instructions
    Write-Host "`n✅ Setup Complete!" -ForegroundColor Green
    Write-Host "=" * 60
    Write-Host "`nTo start the application:" -ForegroundColor Cyan
    Write-Host "  streamlit run src/ui/main.py" -ForegroundColor White
    Write-Host "`nTo run tests:" -ForegroundColor Cyan
    Write-Host "  pytest tests/" -ForegroundColor White
    Write-Host "`nTo check system status:" -ForegroundColor Cyan
    Write-Host "  python tools/smoke_e2e.py" -ForegroundColor White
    
    Write-Host "`n🌐 Access URLs:" -ForegroundColor Cyan
    Write-Host "  Application: http://localhost:8501" -ForegroundColor White
    Write-Host "  MinIO Console: http://localhost:9001 (admin/admin)" -ForegroundColor White
    Write-Host "  PostgreSQL: localhost:5432 (gitte/sicheres_passwort)" -ForegroundColor White
    
} catch {
    Write-Host "`n❌ Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nFor troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check that all prerequisites are installed" -ForegroundColor Gray
    Write-Host "  2. Verify .env file configuration" -ForegroundColor Gray
    Write-Host "  3. Ensure PostgreSQL is accessible" -ForegroundColor Gray
    Write-Host "  4. Check Docker services if using Docker" -ForegroundColor Gray
    Write-Host "  5. Run with -Verbose for more details" -ForegroundColor Gray
    exit 1
}