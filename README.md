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

- **Docker Desktop** with Kubernetes enabled
- **Helm 3.x** for Kubernetes deployments
- **Python 3.11+**
- **Poetry** for dependency management
- **kubectl** (included with Docker Desktop)
- **Git** for version control

### 1. Initialize Project

```bash
# Clone repository
git clone <repository-url>
cd munshi

# Initialize development environment
make init

# This will:
# - Install Python dependencies with Poetry
# - Setup pre-commit hooks
# - Prepare development environment
```

### 2. Install Helm (if not already installed)

```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installation
helm version
```

### 3. Start Development Environment

```bash
# Complete local development setup (recommended)
make dev-setup

# This will:
# 1. Start local Docker registry (localhost:5001)
# 2. Build and push images to local registry
# 3. Deploy to Docker Desktop Kubernetes using Helm
# 4. Setup development namespace (munshi-dev)
```

### 4. Access Services

```bash
# Port forward to access services
kubectl port-forward svc/api-gateway 8000:8000 -n munshi-dev
kubectl port-forward svc/auth-service 8001:8001 -n munshi-dev
```

- **API Gateway**: http://localhost:8000/docs
- **Auth Service**: http://localhost:8001/docs
- **Local Registry**: http://localhost:5001/v2/_catalog
- **Helm Release Status**: `helm status munshi-dev`

## 🔧 Development Workflow

### Local Development (Docker Desktop + Kubernetes + Helm)

```bash
# Setup and Development
make init                   # Initialize project
make dev-setup              # Complete local setup with Helm
make dev-status             # Check development environment
make dev-logs               # Follow application logs
make dev-rebuild            # Rebuild and redeploy with Helm
make dev-clean              # Clean local environment and Helm release

# Local Registry Management
make registry-start         # Start local Docker registry
make registry-stop          # Stop local Docker registry
make registry-status        # Check registry status

# Helm Management
helm status munshi-dev      # Check Helm release status
helm list                   # List all Helm releases
helm get values munshi-dev  # View current configuration

# Testing
make test                   # Run all tests
make test-unit              # Unit tests only
make test-integration       # Integration tests
make test-e2e              # End-to-end tests
make test-performance      # Performance tests
make test-security         # Security tests

# Code Quality
make lint                   # Run linting checks
make format                 # Format code
make security-scan          # Run security scans
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

### Local Development (Docker Desktop + Helm)

```bash
# Complete local setup with Helm
make dev-setup

# Rebuild after code changes
make dev-rebuild

# Monitor development environment
make dev-status
make dev-logs

# Manual Helm commands
helm upgrade munshi-dev infrastructure/helm/munshi -f infrastructure/helm/munshi/values-local.yaml
```

### Cloud Production Deployment with Helm

```bash
# Build and push to GitHub Container Registry
make push-cloud GITHUB_USERNAME=your-username TAG=v1.0.0

# Deploy to production cluster using Helm
make deploy-cloud-prod GITHUB_USERNAME=your-username CLUSTER_CONTEXT=prod-cluster TAG=v1.0.0

# Deploy to staging cluster using Helm
make deploy-cloud-staging GITHUB_USERNAME=your-username CLUSTER_CONTEXT=staging-cluster TAG=v1.0.0

# Manual Helm deployment
helm upgrade --install munshi-prod infrastructure/helm/munshi \
  -f infrastructure/helm/munshi/values-prod.yaml \
  --set global.imageRegistry=ghcr.io/your-username \
  --set images.apiGateway.tag=v1.0.0 \
  --set images.authService.tag=v1.0.0 \
  --create-namespace
```

### Helm Chart Structure

```
infrastructure/helm/munshi/
├── Chart.yaml              # Helm chart metadata
├── values.yaml             # Default production values
├── values-local.yaml       # Local development values
├── values-prod.yaml        # Production values
└── templates/
    ├── _helpers.tpl        # Template helpers
    ├── namespace.yaml      # Namespace definition
    ├── secrets.yaml        # Secrets management
    ├── api-gateway.yaml    # API Gateway deployment
    ├── auth-service.yaml   # Auth Service deployment
    └── databases.yaml      # PostgreSQL and Redis
```

### GitHub Actions CI/CD

The project includes automated CI/CD with GitHub Actions:
- **Builds** images on push to main/develop
- **Pushes** to GitHub Container Registry
- **Creates** signed attestations for security
- **Ready for Helm-based deployments**

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

The project uses Helm for consistent deployments across environments:

```bash
# Local development workflow
make lint                   # Code quality checks
make test                   # Run all tests
make security-scan          # Security scanning
make dev-rebuild            # Local testing with Helm

# Production deployment with Helm
make deploy-cloud-prod GITHUB_USERNAME=username CLUSTER_CONTEXT=prod-cluster
```

### Environment Configuration

- **Local Development**: `values-local.yaml` with reduced resources and debug settings
- **Production**: `values-prod.yaml` with production-grade resources and security
- **Staging**: Uses production values with staging-specific overrides

### GitHub Container Registry Setup

1. **Enable** GitHub Container Registry in your repository
2. **Update** `values-prod.yaml` with your GitHub username
3. **Configure** your cloud cluster credentials
4. **Deploy** using Helm commands or Makefile shortcuts

### Helm Best Practices Implemented

- **Values-based configuration** for different environments
- **Template helpers** for consistent labeling
- **Resource management** with proper limits and requests
- **Security contexts** and non-root containers
- **Health checks** for all services
- **Service mesh ready** with Linkerd annotations

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

### Helm Values Configuration

Configuration is managed through Helm values files:

```yaml
# values-local.yaml (Development)
global:
  imageRegistry: host.docker.internal:5001
environment: development
replicaCount:
  apiGateway: 1
  authService: 1
resources:
  apiGateway:
    requests:
      memory: "128Mi"
      cpu: "50m"
```

```yaml
# values-prod.yaml (Production)
global:
  imageRegistry: ghcr.io/your-username
environment: production
replicaCount:
  apiGateway: 3
  authService: 2
serviceMesh:
  enabled: true
monitoring:
  enabled: true
```

### Environment Variables

Services use environment-based configuration:

```bash
# Core settings (configured via Helm values)
ENVIRONMENT=production
DEBUG=false

# Database URLs (auto-generated by Helm)
GATEWAY_DATABASE_URL=postgresql://gateway_user:password@postgres-gateway:5432/gateway_db
AUTH_DATABASE_URL=postgresql://auth_user:password@postgres-auth:5432/auth_db

# Redis URLs (auto-generated by Helm)
GATEWAY_REDIS_URL=redis://redis-gateway:6379/0
AUTH_REDIS_URL=redis://redis-auth:6379/1

# Security (managed via Kubernetes secrets)
JWT_SECRET_KEY=<from-secret>
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

- [**Helm Chart**](infrastructure/helm/munshi/) - Kubernetes deployment with Helm
- [**Auth Service README**](services/auth-service/README.md) - Authentication service details
- [**API Gateway README**](services/api-gateway/README.md) - Gateway service details
- [**Configuration Guide**](docs/CONFIGURATION.md) - Environment and Helm configuration

## 🏆 Enterprise Features

- ✅ **Microservices Architecture** with proper service isolation
- ✅ **Helm-based Deployments** for consistent, reproducible deployments
- ✅ **Multi-Environment Support** (local, staging, production)
- ✅ **Local Development** with Docker Desktop Kubernetes and local registry
- ✅ **Cloud-Ready** with GitHub Container Registry integration
- ✅ **Shared Component Libraries** for code reuse and consistency
- ✅ **Comprehensive Testing Strategy** (unit, integration, E2E, performance, security)
- ✅ **Service Mesh Ready** with Linkerd annotations and configuration
- ✅ **Enterprise Security** with authentication, authorization, and encryption
- ✅ **Production Monitoring** ready with observability configuration
- ✅ **Development Experience** with automated tooling and documentation

---

Built with ❤️ using modern microservices best practices and enterprise-grade tooling.