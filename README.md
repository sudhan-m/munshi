# Munshi Microservices Architecture

A secure, production-ready microservices architecture with independent API Gateway and Authentication services built with Python FastAPI. Features Linkerd service mesh integration, shared component libraries, comprehensive testing, and enterprise-grade deployment infrastructure.

## 🏗️ Architecture Overview

This project implements a modern microservices architecture following enterprise best practices:

- **Service Mesh**: Linkerd integration for automatic mTLS, observability, and reliability
- **Shared Libraries**: Common components for auth, caching, database, and observability
- **Comprehensive Testing**: Unit, integration, E2E, performance, and security tests
- **Infrastructure as Code**: Docker, Kubernetes, and Terraform deployment options
- **Enterprise Standards**: Security scanning, code quality, and CI/CD pipeline ready

```mermaid
graph TB
    subgraph "External Access"
        CLIENT[Client Applications<br/>Web, Mobile, Desktop]
    end
    
    subgraph "Ingress Layer - Port 443"
        CADDY[Caddy Reverse Proxy<br/>HTTPS TLS Termination<br/>Request Tracing<br/>Compression]
    end
    
    subgraph "Service Mesh Layer"
        LINKERD[Linkerd Service Mesh<br/>Automatic mTLS<br/>Traffic Management<br/>Observability]
    end
    
    subgraph "API Gateway - Port 8000"
        GATEWAY[API Gateway Service<br/>FastAPI Application]
        GW_DB[(PostgreSQL Database<br/>gateway_db:5434)]
        GW_REDIS[(Redis Performance Cache<br/>Database 0 - Port 6381)]
        
        subgraph "Gateway Features"
            RATE_LIMIT[Advanced Rate Limiting<br/>Sliding Window Algorithm]
            RESP_CACHE[Intelligent Caching<br/>TTL-based Invalidation]
            SVC_REGISTRY[Service Discovery<br/>Health Monitoring]
            CIRCUIT_BREAK[Circuit Breaker<br/>Distributed Failure Tracking]
        end
    end
    
    subgraph "Auth Service - Port 8001"
        AUTH_SVC[Authentication Service<br/>FastAPI Application]
        AUTH_DB[(PostgreSQL Database<br/>auth_db:5433)]
        AUTH_REDIS[(Redis Security Cache<br/>Database 1 - Port 6380)]
        
        subgraph "Security Features"
            TOKEN_BL[JWT Token Blacklisting<br/>Instant Logout Security]
            SESSION_CACHE[User Session Cache<br/>1-hour Performance TTL]
            FAILED_LOGIN[Failed Login Tracking<br/>15-min Sliding Window]
            ACCOUNT_LOCK[Account Lockout<br/>Brute Force Protection]
        end
    end
    
    subgraph "Shared Libraries"
        SHARED_AUTH[Authentication Utils<br/>JWT, Middleware, Validators]
        SHARED_CACHE[Cache Components<br/>Redis Client, Decorators]
        SHARED_DB[Database Utils<br/>Models, Connections, Repos]
        SHARED_OBS[Observability<br/>Logging, Metrics, Tracing]
    end
    
    subgraph "Observability Stack"
        PROMETHEUS[Prometheus<br/>Metrics Collection]
        GRAFANA[Grafana<br/>Visualization]
        JAEGER[Jaeger<br/>Distributed Tracing]
    end
    
    CLIENT -->|HTTPS| CADDY
    CADDY -->|HTTP| LINKERD
    LINKERD -->|mTLS| GATEWAY
    LINKERD -->|mTLS| AUTH_SVC
    
    GATEWAY --> GW_DB
    GATEWAY --> GW_REDIS
    GATEWAY -->|Service Calls| AUTH_SVC
    
    AUTH_SVC --> AUTH_DB
    AUTH_SVC --> AUTH_REDIS
    
    GATEWAY --> RATE_LIMIT
    GATEWAY --> RESP_CACHE
    GATEWAY --> SVC_REGISTRY
    GATEWAY --> CIRCUIT_BREAK
    
    AUTH_SVC --> TOKEN_BL
    AUTH_SVC --> SESSION_CACHE
    AUTH_SVC --> FAILED_LOGIN
    AUTH_SVC --> ACCOUNT_LOCK
    
    GATEWAY -.-> SHARED_AUTH
    GATEWAY -.-> SHARED_CACHE
    GATEWAY -.-> SHARED_DB
    GATEWAY -.-> SHARED_OBS
    
    AUTH_SVC -.-> SHARED_AUTH
    AUTH_SVC -.-> SHARED_CACHE
    AUTH_SVC -.-> SHARED_DB
    AUTH_SVC -.-> SHARED_OBS
    
    LINKERD --> PROMETHEUS
    PROMETHEUS --> GRAFANA
    AUTH_SVC --> JAEGER
    GATEWAY --> JAEGER
    
    classDef ingress fill:#ff9800,stroke:#333,stroke-width:2px
    classDef mesh fill:#9c27b0,stroke:#333,stroke-width:2px
    classDef gateway fill:#e1f5fe,stroke:#333,stroke-width:2px
    classDef auth fill:#e8f5e8,stroke:#333,stroke-width:2px
    classDef database fill:#f3e5f5,stroke:#333,stroke-width:2px
    classDef redis fill:#fff3e0,stroke:#333,stroke-width:2px
    classDef features fill:#fce4ec,stroke:#333,stroke-width:2px
    classDef shared fill:#f9f9f9,stroke:#333,stroke-width:2px
    classDef observability fill:#e0f2f1,stroke:#333,stroke-width:2px
    
    class CADDY ingress
    class LINKERD mesh
    class GATEWAY gateway
    class AUTH_SVC auth
    class GW_DB,AUTH_DB database
    class GW_REDIS,AUTH_REDIS redis
    class RATE_LIMIT,RESP_CACHE,SVC_REGISTRY,CIRCUIT_BREAK,TOKEN_BL,SESSION_CACHE,FAILED_LOGIN,ACCOUNT_LOCK features
    class SHARED_AUTH,SHARED_CACHE,SHARED_DB,SHARED_OBS shared
    class PROMETHEUS,GRAFANA,JAEGER observability
```

## 📁 Project Structure

```
munshi/
├── README.md                                    # Main project documentation
├── IMPROVED_STRUCTURE.md                        # Structure improvement guide
├── LINKERD.md                                   # Service mesh integration guide
├── PROJECT_STRUCTURE.md                         # Legacy structure documentation
├── pyproject.toml                               # Python project configuration
├── Makefile                                     # Development task automation
│
├── services/                                    # 🔧 Microservices
│   ├── shared/                                  # Shared components and utilities
│   │   ├── auth/                                # Common authentication utilities
│   │   │   ├── jwt_handler.py                  # JWT token management
│   │   │   └── middleware.py                   # Authentication middleware
│   │   ├── cache/                               # Common cache utilities
│   │   │   ├── redis_client.py                 # Redis client with pooling
│   │   │   └── cache_decorators.py             # Caching decorators
│   │   ├── database/                            # Common database utilities
│   │   │   ├── base_model.py                   # Base models and mixins
│   │   │   └── connection.py                   # Connection management
│   │   ├── observability/                       # Common observability
│   │   │   ├── logging.py                      # Structured logging
│   │   │   ├── metrics.py                      # Prometheus metrics
│   │   │   └── tracing.py                      # OpenTelemetry tracing
│   │   ├── config/                              # Common configuration
│   │   │   ├── base_settings.py                # Base settings classes
│   │   │   └── env_loader.py                   # Environment management
│   │   └── utils/                               # Common utilities
│   │       ├── validators.py                   # Input validation
│   │       └── helpers.py                      # Helper functions
│   │
│   ├── auth-service/                            # Authentication microservice
│   └── api-gateway/                             # API Gateway microservice
│
├── tests/                                       # 🧪 Comprehensive testing
│   ├── conftest.py                              # Global test configuration
│   ├── integration/                             # Cross-service integration tests
│   │   └── test_auth_flow.py                   # Authentication flow tests
│   ├── e2e/                                     # End-to-end user journey tests
│   │   └── test_user_journey.py                # Complete user experience tests
│   ├── performance/                             # Load and performance tests
│   │   └── test_load_testing.py                # Throughput and latency tests
│   └── security/                                # Security vulnerability tests
│       └── test_security_vulnerabilities.py    # Security testing suite
│
├── infrastructure/                              # 🏗️ Infrastructure as Code
│   ├── docker/                                  # Docker configurations
│   │   ├── docker-compose.yml                  # Base compose configuration
│   │   ├── docker-compose.dev.yml              # Development overrides
│   │   ├── docker-compose.prod.yml             # Production optimizations
│   │   └── docker-compose.linkerd.yml          # Service mesh integration
│   ├── kubernetes/                              # Kubernetes manifests
│   │   ├── base/                                # Base Kubernetes resources
│   │   ├── overlays/                            # Kustomize environment overlays
│   │   │   ├── development/                    # Development configuration
│   │   │   ├── staging/                        # Staging configuration
│   │   │   └── production/                     # Production configuration
│   │   └── linkerd/                             # Service mesh configurations
│   ├── scripts/                                 # Deployment and utility scripts
│   │   └── deploy.sh                           # Universal deployment script
│   ├── terraform/                               # Infrastructure provisioning
│   └── monitoring/                              # Observability configurations
│       ├── prometheus/                         # Metrics collection
│       ├── grafana/                            # Visualization dashboards
│       └── alerting/                           # Alert management
│
└── docs/                                        # 📚 Documentation
    ├── api/                                     # API documentation
    ├── architecture/                            # Architecture documentation
    ├── guides/                                  # User and developer guides
    └── contributing/                            # Contribution guidelines
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Poetry (recommended) or pip
- kubectl (for Kubernetes deployment)
- Linkerd CLI (for service mesh)

### 1. Initialize Project

```bash
# Clone and setup
git clone <repository-url>
cd munshi

# Initialize development environment
make init

# Or manually:
poetry install --with dev,test
make build
```

### 2. Start Development Environment

```bash
# Start with Docker Compose
make dev

# Or with Linkerd integration
make dev-linkerd

# Or manually
./infrastructure/scripts/deploy.sh docker development
```

### 3. Access Services

- **Auth Service**: http://localhost:8001/docs
- **API Gateway**: http://localhost:8000/docs
- **Adminer** (DB): http://localhost:8080
- **Redis Commander**: http://localhost:8081
- **Prometheus**: http://localhost:9090 (with Linkerd)
- **Grafana**: http://localhost:3000 (with Linkerd)
- **Jaeger**: http://localhost:16686 (with Linkerd)

## 🔧 Development

### Common Tasks

```bash
# Development
make dev                    # Start development environment
make test                   # Run all tests
make lint                   # Run code quality checks
make format                 # Format code

# Testing
make test-unit              # Unit tests only
make test-integration       # Integration tests
make test-e2e              # End-to-end tests
make test-performance      # Performance tests
make test-security         # Security tests

# Deployment
make deploy-dev            # Deploy to development
make deploy-staging        # Deploy to staging
make deploy-prod           # Deploy to production (with confirmation)

# Monitoring
make status                # Show service status
make logs                  # Show service logs
make health                # Check service health
make metrics               # Open metrics dashboards
```

### Working with Shared Components

The project uses shared libraries to reduce code duplication:

```python
# Example: Using shared authentication
from services.shared.auth import JWTHandler, AuthMiddleware
from services.shared.cache import RedisClient
from services.shared.database import DatabaseManager
from services.shared.observability import setup_logging, MetricsCollector
```

### Running Tests

```bash
# All tests
pytest tests/

# Specific test types
pytest tests/ -m "unit"
pytest tests/ -m "integration"
pytest tests/ -m "e2e"
pytest tests/ -m "performance"
pytest tests/ -m "security"

# With coverage
pytest tests/ --cov=services --cov-report=html
```

## 🚢 Deployment Options

### 1. Docker Compose (Recommended for Development)

```bash
# Development
./infrastructure/scripts/deploy.sh docker development

# Production
./infrastructure/scripts/deploy.sh docker production
```

### 2. Kubernetes (Recommended for Production)

```bash
# Development
./infrastructure/scripts/deploy.sh k8s development

# Production with Linkerd
./infrastructure/scripts/deploy.sh k8s production --linkerd
```

### 3. Service Mesh with Linkerd

```bash
# Install Linkerd
curl -sL https://run.linkerd.io/install | sh
linkerd install --crds | kubectl apply -f -
linkerd install | kubectl apply -f -

# Deploy with mesh
./infrastructure/scripts/deploy.sh k8s production --linkerd
```

## 🔒 Security Features

### Authentication & Authorization
- **Server-side bcrypt hashing** with configurable rounds
- **JWT token management** with blacklisting
- **Failed login tracking** with account lockout
- **Session management** with Redis caching
- **Service mesh mTLS** for inter-service communication

### Rate Limiting & Protection
- **Sliding window rate limiting** with Redis
- **Circuit breaker pattern** for fault tolerance
- **Request validation** and input sanitization
- **Security headers** via Caddy reverse proxy

### Observability & Monitoring
- **Structured logging** with correlation IDs
- **Prometheus metrics** for performance monitoring
- **Distributed tracing** with OpenTelemetry/Jaeger
- **Health checks** and service status monitoring

## 📊 Performance Features

### Caching Strategy
- **Response caching** for GET requests with configurable TTL
- **User session caching** to reduce database load
- **Service discovery caching** for improved routing
- **Connection pooling** for databases and Redis

### Optimization
- **Database connection pooling** with SQLAlchemy
- **Redis pipelining** for batch operations
- **HTTP/2 support** via Caddy reverse proxy
- **Compression** and static asset optimization

## 🔄 CI/CD Integration

The project is designed for enterprise CI/CD pipelines:

```bash
# Code quality pipeline
make lint
make test
make security-scan

# Build and deploy pipeline
make build
make deploy-staging
make test-e2e
make deploy-prod
```

## 📈 Monitoring & Observability

### Metrics (Prometheus)
- HTTP request metrics (latency, throughput, errors)
- Authentication metrics (login success/failure rates)
- Database connection pool metrics
- Cache hit/miss ratios
- Rate limiting violations

### Logging (Structured JSON)
- Request/response logging with correlation IDs
- Authentication events (login, logout, failures)
- Database operations with timing
- Cache operations and performance
- Security events and violations

### Tracing (Jaeger)
- End-to-end request tracing across services
- Database query tracing
- Cache operation tracing
- External API call tracing

## 🛠️ Configuration

Services use environment-based configuration with validation:

```bash
# Core settings
SERVICE_NAME=auth-service
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@host:port/db

# Redis
REDIS_URL=redis://host:port/db

# Security
JWT_SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Observability
LOG_LEVEL=INFO
ENABLE_METRICS=true
ENABLE_TRACING=true
```

## 🤝 Contributing

1. **Code Quality**: All code must pass linting, formatting, and security scans
2. **Testing**: Maintain test coverage above 90%
3. **Documentation**: Update documentation for any architectural changes
4. **Security**: Follow security best practices and run security tests

```bash
# Setup development environment
make install-dev

# Before committing
make lint
make test
make security-scan
```

## 📚 Additional Documentation

- [**IMPROVED_STRUCTURE.md**](IMPROVED_STRUCTURE.md) - Detailed structure improvements
- [**LINKERD.md**](LINKERD.md) - Service mesh integration guide
- [**Auth Service README**](src/auth_service/README.md) - Authentication service details
- [**API Gateway README**](src/api-gateway/README.md) - Gateway service details

## 🏆 Enterprise Features

- ✅ **Microservices Architecture** with proper service isolation
- ✅ **Service Mesh Integration** with Linkerd for automatic mTLS
- ✅ **Shared Component Libraries** for code reuse and consistency
- ✅ **Comprehensive Testing Strategy** (unit, integration, E2E, performance, security)
- ✅ **Infrastructure as Code** with Docker, Kubernetes, and Terraform
- ✅ **CI/CD Ready** with automated testing and deployment
- ✅ **Enterprise Security** with authentication, authorization, and encryption
- ✅ **Production Monitoring** with metrics, logging, and tracing
- ✅ **High Availability** with auto-scaling and fault tolerance
- ✅ **Development Experience** with automated tooling and documentation

---

Built with ❤️ using modern microservices best practices and enterprise-grade tooling.