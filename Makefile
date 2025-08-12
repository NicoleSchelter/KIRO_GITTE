.PHONY: help dev test migrate seed run clean build up down logs shell

# Default target
help:
	@echo "Available targets:"
	@echo "  dev      - Start development environment"
	@echo "  test     - Run test suite"
	@echo "  migrate  - Run database migrations"
	@echo "  seed     - Seed database with initial data"
	@echo "  run      - Run the application locally"
	@echo "  build    - Build Docker images"
	@echo "  up       - Start all services with Docker Compose"
	@echo "  down     - Stop all services"
	@echo "  logs     - Show logs from all services"
	@echo "  shell    - Open shell in app container"
	@echo "  clean    - Clean up containers and volumes"

# Development environment
dev: up
	@echo "Development environment started"
	@echo "Access the application at http://localhost:8501"
	@echo "Access MinIO console at http://localhost:9001"
	@echo "PostgreSQL is available at localhost:5432"

# Run tests
test:
	@echo "Running test suite..."
	python -m pytest tests/ -v --tb=short

# Database migrations
migrate:
	@echo "Running database migrations..."
	python -m alembic upgrade head

# Seed database
seed:
	@echo "Seeding database with initial data..."
	python scripts/seed_database.py

# Run application locally (without Docker)
run:
	@echo "Starting GITTE application..."
	streamlit run src/ui/main.py --server.port=8501

# Docker operations
build:
	@echo "Building Docker images..."
	docker-compose build

up:
	@echo "Starting services with Docker Compose..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10

down:
	@echo "Stopping all services..."
	docker-compose down

logs:
	@echo "Showing logs from all services..."
	docker-compose logs -f

shell:
	@echo "Opening shell in app container..."
	docker-compose exec gitte-app /bin/bash

# Cleanup
clean:
	@echo "Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f

# Development helpers
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/

lint:
	@echo "Running linters..."
	mypy src/
	black --check src/ tests/
	isort --check-only src/ tests/

# Database helpers
db-reset: down
	@echo "Resetting database..."
	docker volume rm gitte-federated-learning-system_postgres_data || true
	$(MAKE) up
	$(MAKE) migrate
	$(MAKE) seed

# Testing helpers
test-unit:
	@echo "Running unit tests..."
	python -m pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	python -m pytest tests/integration/ -v

test-e2e:
	@echo "Running end-to-end tests..."
	python -m pytest tests/e2e/ -v

# Production helpers
prod-build:
	@echo "Building production images..."
	docker-compose -f docker-compose.prod.yml build

prod-up:
	@echo "Starting production environment..."
	docker-compose -f docker-compose.prod.yml up -d