# Design Document

## Overview

GITTE (Great Individual Tutor Embodiment) is a production-grade federated learning-capable system for creating personalized visual representations and embodiments of intelligent learning assistants. The system focuses on generating and managing personalized visual avatars, characters, and representations that will later be integrated into learning systems. It provides AI-powered chat for embodiment interaction and image generation for visual representation creation while maintaining GDPR compliance and supporting optional federated learning for embodiment personalization improvement.

### Key Design Principles

1. **Privacy by Design**: All data processing requires explicit consent, with pseudonymization and local processing
2. **Layered Architecture**: Strict 4-layer separation (UI → Logic → Service → Data) with no cross-layer shortcuts
3. **Swappable Components**: All external services (LLM, image generation, storage) are abstracted behind adapters
4. **Configuration-Driven**: All behavior controlled through centralized configuration with feature flags
5. **Audit-First**: Comprehensive logging with write-ahead logging for all AI interactions
6. **Embodiment-Focused**: System specializes in visual representation and personalization of learning assistant avatars

## Architecture

### High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "UI Layer (Streamlit)"
        A[Login UI] --> B[Consent UI]
        B --> C[Survey UI]
        C --> D[GITTE Chat UI]
        D --> E[Image Generation UI]
        E --> F[Admin UI]
    end
    
    subgraph "Logic Layer"
        G[Authentication Logic]
        H[Consent Logic]
        I[Embodiment Logic]
        J[Interaction Logic]
        K[Admin Logic]
        L[FL Client Logic]
    end
    
    subgraph "Service Layer"
        M[LLM Service]
        N[Image Service]
        O[PALD Service]
        P[Audit Service]
        Q[FL Service]
        R[Storage Service]
    end
    
    subgraph "Data Layer"
        S[(PostgreSQL)]
        T[MinIO/Local FS]
        U[Config Store]
    end
    
    subgraph "External Services"
        V[Ollama LLM]
        W[Stable Diffusion]
        X[FL Server]
    end
    
    A --> G
    B --> H
    D --> I
    I --> M
    M --> V
    N --> W
    S --> R
    T --> R
    L --> Q
    Q --> X
```

### 4-Layer Architecture Details

#### UI Layer (Streamlit)
- **Responsibility**: User interface, input validation, display logic
- **Components**: Login, Consent, Survey, Chat, Image Generation, Admin interfaces
- **Constraints**: No direct access to data layer, all business logic delegated to Logic layer

#### Logic Layer
- **Responsibility**: Business logic, workflow orchestration, decision making
- **Components**: Authentication, Consent management, Embodiment personalization logic, Interaction management
- **Constraints**: No direct external service calls, uses Service layer adapters

#### Service Layer
- **Responsibility**: External service integration, data transformation, caching
- **Components**: LLM adapters, Image generation adapters, Storage services, Audit services
- **Constraints**: Stateless operations, no business logic

#### Data Layer
- **Responsibility**: Data persistence, schema management, migrations
- **Components**: PostgreSQL database, File storage, Configuration storage
- **Constraints**: No business logic, pure data operations

## Components and Interfaces

### Core Components

#### 1. Authentication System
```python
class AuthenticationService:
    def register_user(self, username: str, password: str, role: UserRole) -> User
    def authenticate(self, username: str, password: str) -> Optional[User]
    def hash_password(self, password: str) -> str
    def verify_password(self, password: str, hashed: str) -> bool
```

#### 2. Consent Management
```python
class ConsentManager:
    def request_consent(self, user_id: str, consent_type: ConsentType) -> ConsentRequest
    def record_consent(self, user_id: str, consent_data: ConsentData) -> ConsentRecord
    def check_consent(self, user_id: str, operation: str) -> bool
    def withdraw_consent(self, user_id: str, consent_type: ConsentType) -> bool
```

#### 3. PALD System (Pedagogical Agent Level of Design)
```python
class PALDService:
    def validate_pald(self, pald_data: dict) -> ValidationResult
    def compare_pald(self, pald_a: dict, pald_b: dict) -> PALDDiff
    def calculate_coverage(self, pald_data: dict) -> CoverageMetrics
    def evolve_schema(self, suggestions: List[SchemaSuggestion]) -> SchemaVersion
    def generate_embodiment_attributes(self, pald_data: dict) -> EmbodimentAttributes
    def extract_new_attributes(self, chat_text: str) -> List[AttributeCandidate]
    def track_attribute_mentions(self, attributes: List[AttributeCandidate]) -> None
    def check_threshold_for_schema_evolution(self) -> List[NewAttribute]
    def propose_schema_update(self, new_attributes: List[NewAttribute]) -> SchemaUpdateProposal
```

#### 4. LLM Integration
```python
class LLMProvider(ABC):
    @abstractmethod
    def generate_response(self, prompt: str, model: str, params: dict) -> LLMResponse

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434")
    def generate_response(self, prompt: str, model: str, params: dict) -> LLMResponse
```

#### 5. Embodiment Image Generation
```python
class Text2ImageProvider(ABC):
    @abstractmethod
    def generate_embodiment_image(self, embodiment_prompt: str, params: dict) -> ImageResult

class StableDiffusionProvider(Text2ImageProvider):
    def __init__(self, model_name: str = "runwayml/stable-diffusion-v1-5")
    def generate_embodiment_image(self, embodiment_prompt: str, params: dict) -> ImageResult
    def generate_avatar_variations(self, base_prompt: str, variations: List[str]) -> List[ImageResult]
```

#### 6. Federated Learning Client for Embodiment Personalization
```python
class FederatedLearningClient:
    def collect_embodiment_preferences(self, user_id: str) -> EmbodimentSignals
    def create_personalization_update(self, signals: EmbodimentSignals) -> ModelUpdate
    def submit_update(self, update: ModelUpdate) -> SubmissionResult
    def apply_global_embodiment_model(self, global_update: GlobalModel) -> bool
```

#### 7. Audit System
```python
class AuditLogger:
    def initialize_log(self, request_id: str, operation: str) -> LogEntry
    def finalize_log(self, log_entry: LogEntry, result: dict) -> bool
    def create_parent_child_link(self, parent_id: str, child_id: str) -> bool
    def export_audit_data(self, filters: AuditFilters) -> ExportResult
```

### Interface Definitions

#### Configuration Interface
```python
@dataclass
class SystemConfig:
    # Feature flags
    feature_flags: Dict[str, bool]
    
    # LLM configuration
    llm_models: Dict[str, str]
    ollama_url: str
    
    # Image generation
    sd_model_name: str
    
    # Database
    postgres_dsn: str
    
    # Storage
    minio_config: Optional[MinIOConfig]
    
    # Federated Learning
    fl_config: Optional[FLConfig]
    
    # Security
    encryption_key: str
    tls_config: TLSConfig
```

#### PALD Schema Interface
```python
@dataclass
class PALDSchema:
    version: str
    schema: Dict[str, Any]
    validation_rules: List[ValidationRule]
    
class PALDData:
    def __init__(self, data: dict, schema_version: str)
    def validate(self) -> ValidationResult
    def to_dict(self) -> dict
    def get_coverage(self) -> float
```

## Data Models

### Core Data Models

#### User Model
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pseudonym VARCHAR(255) UNIQUE NOT NULL
);
```

#### Consent Model
```sql
CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    consent_type VARCHAR(100) NOT NULL,
    consent_given BOOLEAN NOT NULL,
    consent_version VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);
```

#### PALD Model
```sql
CREATE TABLE pald_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    pald_content JSONB NOT NULL,
    schema_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pald_attribute_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attribute_name VARCHAR(255) NOT NULL,
    attribute_category VARCHAR(100),
    mention_count INTEGER DEFAULT 1,
    first_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_mentioned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    threshold_reached BOOLEAN DEFAULT FALSE,
    added_to_schema BOOLEAN DEFAULT FALSE,
    schema_version_added VARCHAR(50)
);

CREATE TABLE pald_schema_versions (
    version VARCHAR(50) PRIMARY KEY,
    schema_content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,
    migration_notes TEXT
);
```

#### Audit Log Model
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES users(id),
    operation VARCHAR(100) NOT NULL,
    model_used VARCHAR(100),
    input_data JSONB,
    output_data JSONB,
    parameters JSONB,
    token_usage INTEGER,
    latency_ms INTEGER,
    parent_log_id UUID REFERENCES audit_logs(id),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalized_at TIMESTAMP
);
```

#### Federated Learning Model
```sql
CREATE TABLE fl_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    update_data BYTEA NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    aggregation_round INTEGER,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE
);
```

### Data Relationships

```mermaid
erDiagram
    USERS ||--o{ CONSENT_RECORDS : has
    USERS ||--o{ PALD_DATA : owns
    USERS ||--o{ AUDIT_LOGS : generates
    USERS ||--o{ FL_UPDATES : submits
    AUDIT_LOGS ||--o{ AUDIT_LOGS : parent_child
    PALD_DATA ||--o{ PALD_VERSIONS : versioned
```

## Error Handling

### Error Categories and Strategies

#### 1. Authentication Errors
- **Strategy**: Graceful degradation with clear user feedback
- **Implementation**: Custom exception hierarchy with user-friendly messages
- **Logging**: Security events logged with appropriate detail level

#### 2. Consent Violations
- **Strategy**: Immediate blocking with consent re-request
- **Implementation**: Consent middleware checking all operations
- **Logging**: Privacy compliance audit trail

#### 3. LLM Service Errors
- **Strategy**: Retry with exponential backoff, fallback to cached responses
- **Implementation**: Circuit breaker pattern with health checks
- **Logging**: Performance metrics and error rates

#### 4. Image Generation Errors
- **Strategy**: GPU fallback to CPU, then to placeholder images
- **Implementation**: Provider chain with automatic failover
- **Logging**: Resource utilization and failure patterns

#### 5. Federated Learning Errors
- **Strategy**: Graceful degradation, local-only mode
- **Implementation**: Optional FL with feature flag control
- **Logging**: FL participation metrics and error analysis

### Error Handling Implementation

```python
class GITTEException(Exception):
    """Base exception for GITTE system"""
    pass

class ConsentRequiredException(GITTEException):
    """Raised when operation requires consent"""
    pass

class LLMServiceException(GITTEException):
    """Raised when LLM service fails"""
    pass

class ImageGenerationException(GITTEException):
    """Raised when image generation fails"""
    pass

@dataclass
class ErrorResponse:
    error_code: str
    message: str
    user_message: str
    retry_after: Optional[int] = None
    support_contact: Optional[str] = None
```

## Testing Strategy

### Testing Pyramid

#### 1. Unit Tests (70%)
- **Scope**: Individual components, business logic, data models
- **Tools**: pytest, pytest-mock, factory-boy
- **Coverage**: >90% code coverage for logic and service layers
- **Focus**: Edge cases, error conditions, data validation

#### 2. Integration Tests (20%)
- **Scope**: Component interactions, database operations, external service mocks
- **Tools**: pytest, testcontainers, docker-compose
- **Coverage**: Critical user flows, data consistency
- **Focus**: Layer boundaries, configuration variations

#### 3. End-to-End Tests (10%)
- **Scope**: Complete user journeys, smoke tests
- **Tools**: Selenium, pytest-playwright
- **Coverage**: Happy path scenarios, critical business flows
- **Focus**: User experience, performance benchmarks

### Test Implementation Strategy

#### Mock Strategy for External Services
```python
class MockOllamaProvider(LLMProvider):
    def generate_response(self, prompt: str, model: str, params: dict) -> LLMResponse:
        return LLMResponse(
            text="Mock response",
            tokens_used=10,
            latency_ms=100
        )

class MockStableDiffusionProvider(Text2ImageProvider):
    def generate_image(self, prompt: str, params: dict) -> ImageResult:
        return ImageResult(
            image_path="mock_image.png",
            generation_time=5.0
        )
```

#### Test Data Management
```python
class TestDataFactory:
    @staticmethod
    def create_user(role: UserRole = UserRole.PARTICIPANT) -> User:
        return User(
            id=uuid4(),
            username=f"test_user_{uuid4().hex[:8]}",
            role=role,
            pseudonym=f"pseudo_{uuid4().hex[:8]}"
        )
    
    @staticmethod
    def create_pald_data(user_id: UUID) -> PALDData:
        return PALDData(
            user_id=user_id,
            pald_content={"learning_style": "visual", "difficulty": "intermediate"},
            schema_version="1.0"
        )
```

### Performance Testing

#### Load Testing Scenarios
1. **Concurrent Chat Sessions**: 100 simultaneous users
2. **Image Generation Load**: 20 concurrent image requests
3. **Database Stress**: 1000 concurrent PALD updates
4. **Federated Learning**: 500 clients submitting updates

#### Performance Benchmarks
- Chat response time: median ≤ 2s, p95 ≤ 5s
- Image generation: p95 ≤ 30s (GPU)
- Database queries: p95 ≤ 100ms
- System availability: 99.5% uptime

### Security Testing

#### Security Test Categories
1. **Authentication**: Password strength, session management
2. **Authorization**: Role-based access control
3. **Data Protection**: Encryption, pseudonymization
4. **Privacy**: Consent enforcement, data deletion
5. **Input Validation**: SQL injection, XSS prevention

## Deployment Architecture

### Container Architecture

```mermaid
graph TB
    subgraph "Docker Compose Stack"
        A[Streamlit App Container]
        B[PostgreSQL Container]
        C[MinIO Container]
        D[Ollama Container]
        E[Redis Container]
    end
    
    subgraph "Host System"
        F[GPU Resources]
        G[Local Storage]
        H[Configuration Files]
    end
    
    A --> B
    A --> C
    A --> D
    A --> E
    D --> F
    C --> G
    A --> H
```

### Environment Configuration

#### Development Environment
```yaml
# docker-compose.dev.yml
version: '3.8'
services:
  gitte-app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - ENVIRONMENT=development
      - POSTGRES_DSN=postgresql://gitte:password@postgres:5432/data_collector
      - OLLAMA_URL=http://ollama:11434
    volumes:
      - ./config:/app/config
      - ./generated_images:/app/generated_images
    depends_on:
      - postgres
      - ollama
      - minio
  
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=data_collector
      - POSTGRES_USER=gitte
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  ollama_data:
  minio_data:
```

#### Production Environment Considerations
- **Secrets Management**: Use Docker secrets or external secret management
- **SSL/TLS**: Terminate SSL at load balancer or reverse proxy
- **Monitoring**: Prometheus metrics, Grafana dashboards
- **Backup Strategy**: Automated database backups, image storage replication
- **Scaling**: Horizontal scaling for Streamlit app, read replicas for database

### Configuration Management

#### Environment-Specific Configuration
```python
# config/config.py
import os
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class Config:
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Feature Flags
    feature_flags: Dict[str, bool] = None
    
    # Database
    postgres_dsn: str = os.getenv("POSTGRES_DSN", "postgresql://localhost/data_collector")
    
    # LLM Configuration
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    llm_models: Dict[str, str] = None
    
    # Image Generation
    sd_model_name: str = os.getenv("SD_MODEL_NAME", "runwayml/stable-diffusion-v1-5")
    
    # Storage
    minio_endpoint: Optional[str] = os.getenv("MINIO_ENDPOINT")
    minio_access_key: Optional[str] = os.getenv("MINIO_ACCESS_KEY")
    minio_secret_key: Optional[str] = os.getenv("MINIO_SECRET_KEY")
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key")
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "dev-encryption-key")
    
    def __post_init__(self):
        if self.feature_flags is None:
            self.feature_flags = {
                "SAVE_LLM_LOGS": True,
                "USE_FL": False,
                "ENABLE_CONSISTENCY_CHECK": False,
                "USE_LANGCHAIN": False
            }
        
        if self.llm_models is None:
            self.llm_models = {
                "default": "llama3",
                "creative": "mistral",
                "vision": "llava"
            }

# Load configuration
config = Config()
```

This comprehensive design document provides the foundation for implementing the GITTE federated learning system with all the required components, interfaces, and architectural decisions clearly defined.