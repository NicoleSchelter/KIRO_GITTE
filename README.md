# GITTE - Great Individual Tutor Embodiment

A production-grade federated learning-capable system for creating personalized visual representations and embodiments of intelligent learning assistants.

## 🏗️ Architecture

GITTE follows a strict 4-layer architecture:

- **UI Layer** (`src/ui/`): Streamlit interfaces and display logic
- **Logic Layer** (`src/logic/`): Business logic, workflow orchestration, decision making  
- **Service Layer** (`src/services/`): External service integration, data transformation, caching
- **Data Layer** (`src/data/`): Data persistence, schema management, migrations

## ✨ UX Enhancements

GITTE includes advanced user experience enhancements designed to make the system more intuitive, accessible, and efficient:

### 🖼️ Image Correction System
- **Automatic Quality Detection**: Identifies issues like blur, multiple people, poor lighting
- **Manual Correction Tools**: Interactive cropping with real-time preview
- **Smart Regeneration**: AI learns from your corrections to improve future generations
- **Background Removal**: Isolate subjects with transparent or custom backgrounds

### 💡 Intelligent Tooltips
- **Context-Sensitive Help**: Dynamic tooltips that adapt to your current task
- **Skill Level Adaptation**: Detailed help for beginners, concise tips for experts
- **Accessibility Support**: Enhanced tooltips for screen readers and keyboard navigation
- **Learning System**: Adapts to your usage patterns over time

### ✅ Prerequisite Validation
- **Real-Time Checking**: Validates system requirements before operations
- **User-Friendly Resolution**: Clear error messages with step-by-step fixes
- **Performance Monitoring**: Tracks system health and performance metrics
- **Automated Recovery**: Attempts to resolve simple issues automatically

### ♿ Accessibility Features
- **WCAG 2.1 AA Compliance**: Meets international accessibility standards
- **High Contrast Mode**: Enhanced visibility for users with visual impairments
- **Keyboard Navigation**: Full functionality without mouse interaction
- **Screen Reader Support**: Comprehensive ARIA labels and semantic markup

### ⚡ Performance Optimizations
- **Lazy Loading**: Resources load only when needed
- **Multi-Level Caching**: Memory, disk, and network caching for optimal performance
- **Resource Management**: Intelligent memory and CPU usage optimization
- **Monitoring**: Real-time performance metrics and alerting

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd gitte-federated-learning-system
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start development environment**
   ```bash
   make dev
   ```

4. **Access the application**
   - Main app: http://localhost:8501
   - MinIO console: http://localhost:9001
   - PostgreSQL: localhost:5432

### Available Commands

**Linux/macOS (using Makefile):**
```bash
make help          # Show all available commands
make dev           # Start development environment
make test          # Run test suite
make migrate       # Run database migrations
make seed          # Seed database with initial data
make run           # Run application locally (without Docker)
make build         # Build Docker images
make up            # Start all services
make down          # Stop all services
make logs          # Show service logs
make clean         # Clean up containers and volumes
```

**Windows (using PowerShell script):**
```powershell
.\scripts\dev.ps1 help     # Show all available commands
.\scripts\dev.ps1 dev      # Start development environment
.\scripts\dev.ps1 test     # Run test suite
.\scripts\dev.ps1 migrate  # Run database migrations
.\scripts\dev.ps1 seed     # Seed database with initial data
.\scripts\dev.ps1 run      # Run application locally (without Docker)
.\scripts\dev.ps1 build    # Build Docker images
.\scripts\dev.ps1 up       # Start all services
.\scripts\dev.ps1 down     # Stop all services
.\scripts\dev.ps1 logs     # Show service logs
.\scripts\dev.ps1 clean    # Clean up containers and volumes
```

## 📁 Project Structure

```
├── src/                    # Source code (4-layer architecture)
│   ├── ui/                # UI Layer - Streamlit interfaces
│   ├── logic/             # Logic Layer - Business logic
│   ├── services/          # Service Layer - External integrations
│   └── data/              # Data Layer - Persistence
├── config/                # Configuration management
├── tests/                 # Test suite
├── migrations/            # Database migrations
├── scripts/               # Utility scripts
├── docker-compose.yml     # Docker services
├── Dockerfile            # Application container
├── Makefile              # Development commands
└── requirements.txt      # Python dependencies
```

## ⚙️ Configuration

Configuration is managed through:

1. **Default values** in `config/config.py`
2. **Environment variables** (see `.env.example`)
3. **Feature flags** for runtime behavior control

### Key Configuration Sections

- **Database**: PostgreSQL connection and settings
- **LLM**: Ollama integration and model configuration
- **Image Generation**: Stable Diffusion settings
- **Storage**: MinIO/local filesystem configuration
- **Security**: Encryption and authentication settings
- **Federated Learning**: FL client configuration
- **Feature Flags**: Runtime behavior toggles

### Feature Flags

Control system behavior without code changes:

- `FEATURE_SAVE_LLM_LOGS`: Enable LLM interaction logging
- `FEATURE_USE_FEDERATED_LEARNING`: Enable FL capabilities
- `FEATURE_ENABLE_IMAGE_GENERATION`: Enable avatar generation
- `FEATURE_ENABLE_CONSENT_GATE`: Enforce privacy consent
- And more...

## 🐳 Docker Services

The system includes these containerized services:

- **gitte-app**: Main Streamlit application
- **postgres**: PostgreSQL database (v15)
- **ollama**: LLM service for chat functionality
- **minio**: S3-compatible object storage for images

## 🧪 Testing

```bash
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests only
make test-e2e          # Run end-to-end tests only
```

## 🔒 Security & Privacy

GITTE is designed with privacy-by-design principles:

- **GDPR Compliance**: Explicit consent management
- **Data Pseudonymization**: User data protection
- **Encryption**: AES-256 for sensitive data
- **TLS**: Secure communication
- **Audit Logging**: Comprehensive activity tracking

## 🤝 Federated Learning

Optional federated learning capabilities for embodiment personalization:

- **Privacy-Preserving**: No raw data leaves client
- **Structured Signals**: Only PALD slots and feedback
- **Differential Privacy**: Configurable privacy parameters
- **Feature Flag Controlled**: Easy enable/disable

## 📊 PALD System

Pedagogical Agent Level of Design (PALD) schema management:

- **Versioned Schema**: JSON schema with validation
- **Dynamic Evolution**: Schema adapts to new attributes
- **Coverage Analysis**: Data completeness metrics
- **Comparison Tools**: Diff utilities for analysis

## 🛠️ Development

### Code Style

- **Black**: Code formatting
- **isort**: Import sorting  
- **MyPy**: Type checking
- **Pytest**: Testing framework

### Layer Boundaries

Strict enforcement of 4-layer architecture:
- UI → Logic → Service → Data
- No cross-layer shortcuts allowed
- Clear interfaces between layers

## 📝 Status

🚧 **Under Development** - Core infrastructure complete, feature implementation in progress.

Current status:
- ✅ Project structure and architecture
- ✅ Configuration management system
- ✅ Docker containerization
- ✅ Development tooling
- 🚧 Feature implementation (in progress)

## 📚 Documentation

### User Documentation
- **[UX Enhancements User Guide](docs/UX_ENHANCEMENTS_USER_GUIDE.md)**: Complete guide to using the new UX features
- **[API Documentation](docs/api-spec.yaml)**: OpenAPI specification for all endpoints
- **[Architecture Guide](docs/ARCHITECTURE.md)**: System architecture and design decisions
- **[Deployment Guide](docs/DEPLOYMENT.md)**: Production deployment instructions
- **[Operations Guide](docs/OPERATIONS.md)**: System administration and monitoring

### Developer Documentation
- **[Troubleshooting Guide](docs/UX_ENHANCEMENTS_TROUBLESHOOTING.md)**: Solutions to common issues
- **[Testing Standards](docs/TESTING.md)**: Testing guidelines and best practices
- **[Development Workflow](docs/DEVELOPMENT.md)**: Development process and conventions

### Deployment and Operations
- **[Deployment Validation](scripts/deployment_validation.py)**: Automated deployment testing
- **[Rollback Procedures](scripts/rollback_procedures.py)**: Safe rollback mechanisms
- **[Monitoring Configuration](config/prometheus.yml)**: Prometheus monitoring setup
- **[Alert Rules](config/alert_rules.yml)**: Production alerting configuration

## 📄 License

[License information to be added]

## 🤝 Contributing

[Contributing guidelines to be added]