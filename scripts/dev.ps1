# PowerShell development script for Windows users
# Equivalent to Makefile targets for Windows

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host "  help     - Show this help message"
    Write-Host "  dev      - Start development environment"
    Write-Host "  test     - Run test suite"
    Write-Host "  migrate  - Run database migrations"
    Write-Host "  seed     - Seed database with initial data"
    Write-Host "  run      - Run the application locally"
    Write-Host "  build    - Build Docker images"
    Write-Host "  up       - Start all services with Docker Compose"
    Write-Host "  down     - Stop all services"
    Write-Host "  logs     - Show logs from all services"
    Write-Host "  clean    - Clean up containers and volumes"
    Write-Host ""
    Write-Host "Usage: .\scripts\dev.ps1 <command>" -ForegroundColor Yellow
}

function Start-Dev {
    Write-Host "Starting development environment..." -ForegroundColor Green
    docker-compose up -d
    Write-Host "Development environment started" -ForegroundColor Green
    Write-Host "Access the application at http://localhost:8501" -ForegroundColor Cyan
    Write-Host "Access MinIO console at http://localhost:9001" -ForegroundColor Cyan
    Write-Host "PostgreSQL is available at localhost:5432" -ForegroundColor Cyan
}

function Run-Tests {
    Write-Host "Running test suite..." -ForegroundColor Green
    python -m pytest tests/ -v --tb=short
}

function Run-Migrations {
    Write-Host "Running database migrations..." -ForegroundColor Green
    python -m alembic upgrade head
}

function Seed-Database {
    Write-Host "Seeding database with initial data..." -ForegroundColor Green
    python scripts/seed_database.py
}

function Run-App {
    Write-Host "Starting GITTE application..." -ForegroundColor Green
    streamlit run src/ui/main.py --server.port=8501
}

function Build-Images {
    Write-Host "Building Docker images..." -ForegroundColor Green
    docker-compose build
}

function Start-Services {
    Write-Host "Starting services with Docker Compose..." -ForegroundColor Green
    docker-compose up -d
    Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    Write-Host "Services started" -ForegroundColor Green
}

function Stop-Services {
    Write-Host "Stopping all services..." -ForegroundColor Green
    docker-compose down
}

function Show-Logs {
    Write-Host "Showing logs from all services..." -ForegroundColor Green
    docker-compose logs -f
}

function Clean-Up {
    Write-Host "Cleaning up containers and volumes..." -ForegroundColor Green
    docker-compose down -v
    docker system prune -f
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "dev" { Start-Dev }
    "test" { Run-Tests }
    "migrate" { Run-Migrations }
    "seed" { Seed-Database }
    "run" { Run-App }
    "build" { Build-Images }
    "up" { Start-Services }
    "down" { Stop-Services }
    "logs" { Show-Logs }
    "clean" { Clean-Up }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
    }
}