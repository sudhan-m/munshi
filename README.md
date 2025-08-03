# Munshi Microservices Architecture

A secure, production-ready microservices architecture with independent API Gateway and Authentication services built with Python FastAPI. Features distributed Redis caching, intelligent rate limiting, and optimized reverse proxy integration.

## Architecture Overview

This project implements a true microservices architecture where each service:
- Has its own dedicated database and Redis cache
- Can be deployed independently with full isolation
- Has separate configuration and dependencies
- Communicates via HTTP APIs with mTLS security
- Features distributed caching and rate limiting
- Implements intelligent middleware for performance optimization

```mermaid
graph TB
    subgraph "External Access"
        CLIENT[Client Applications<br/>Web, Mobile, Desktop]
    end
    
    subgraph "Ingress Layer - Port 443"
        CADDY[Caddy Reverse Proxy<br/>HTTPS TLS Termination<br/>Emergency DDoS Protection<br/>Security Headers]
    end
    
    subgraph "API Gateway - Port 8000"
        GATEWAY[API Gateway Service<br/>FastAPI Application]
        GW_DB[(PostgreSQL Database<br/>gateway_db:5434)]
        GW_REDIS[(Redis Cache<br/>Database 0 - Port 6381)]
        
        subgraph "Gateway Features"
            RATE_LIMIT[Rate Limiting<br/>1000-5000 req/min]
            RESP_CACHE[Response Caching<br/>5-10 min TTL]
            SVC_REGISTRY[Service Registry<br/>60s TTL]
            CIRCUIT_BREAK[Circuit Breaker<br/>Fault Tolerance]
        end
    end
    
    subgraph "Auth Service - Port 8001"
        AUTH_SVC[Auth Service<br/>FastAPI Application]
        AUTH_DB[(PostgreSQL Database<br/>auth_db:5433)]
        AUTH_REDIS[(Redis Cache<br/>Database 1 - Port 6380)]
        
        subgraph "Security Features"
            TOKEN_BL[JWT Token Blacklisting<br/>Instant Logout]
            SESSION_CACHE[User Session Cache<br/>1-hour TTL]
            FAILED_LOGIN[Failed Login Tracking<br/>15-min Window]
            ACCOUNT_LOCK[Account Lockout<br/>15-min TTL]
        end
    end
    
    %% Client to Ingress
    CLIENT -->|HTTPS| CADDY
    
    %% Ingress to Gateway
    CADDY -->|HTTP| GATEWAY
    
    %% Gateway to Auth Service (mTLS)
    GATEWAY -->|mTLS| AUTH_SVC
    
    %% Gateway Internal Connections
    GATEWAY --> GW_DB
    GATEWAY --> GW_REDIS
    GATEWAY --> RATE_LIMIT
    GATEWAY --> RESP_CACHE
    GATEWAY --> SVC_REGISTRY
    GATEWAY --> CIRCUIT_BREAK
    
    %% Auth Service Internal Connections
    AUTH_SVC --> AUTH_DB
    AUTH_SVC --> AUTH_REDIS
    AUTH_SVC --> TOKEN_BL
    AUTH_SVC --> SESSION_CACHE
    AUTH_SVC --> FAILED_LOGIN
    AUTH_SVC --> ACCOUNT_LOCK
    
    %% Redis Feature Connections
    GW_REDIS --> RATE_LIMIT
    GW_REDIS --> RESP_CACHE
    GW_REDIS --> SVC_REGISTRY
    GW_REDIS --> CIRCUIT_BREAK
    
    AUTH_REDIS --> TOKEN_BL
    AUTH_REDIS --> SESSION_CACHE
    AUTH_REDIS --> FAILED_LOGIN
    AUTH_REDIS --> ACCOUNT_LOCK
    
    classDef ingress fill:#ff9800,stroke:#333,stroke-width:2px
    classDef gateway fill:#e1f5fe,stroke:#333,stroke-width:2px
    classDef auth fill:#e8f5e8,stroke:#333,stroke-width:2px
    classDef database fill:#f3e5f5,stroke:#333,stroke-width:2px
    classDef redis fill:#fff3e0,stroke:#333,stroke-width:2px
    classDef security fill:#fce4ec,stroke:#333,stroke-width:2px
    classDef performance fill:#e8f5e8,stroke:#333,stroke-width:2px
    
    class CADDY ingress
    class GATEWAY,GW_DB,RATE_LIMIT,RESP_CACHE,SVC_REGISTRY,CIRCUIT_BREAK gateway
    class AUTH_SVC,AUTH_DB,TOKEN_BL,SESSION_CACHE,FAILED_LOGIN,ACCOUNT_LOCK auth
    class GW_DB,AUTH_DB database
    class GW_REDIS,AUTH_REDIS redis
    class TOKEN_BL,SESSION_CACHE,FAILED_LOGIN,ACCOUNT_LOCK security
    class RATE_LIMIT,RESP_CACHE,SVC_REGISTRY,CIRCUIT_BREAK performance
```

## Services

### Caddy Reverse Proxy (HTTPS Port 443)
**Optimized TLS termination and request routing**
- **Automatic HTTPS**: Self-signed certificates (dev) / Let's Encrypt (prod)
- **Emergency DDoS Protection**: High threshold rate limiting (1000 req/min)
- **Response Compression**: gzip and zstd compression for better performance
- **Request Tracing**: Unique request IDs for correlation across services
- **Connection Pooling**: Optimized HTTP connections to API Gateway
- **Security Headers**: HSTS enforcement and server information hiding
- **Admin API**: Management interface on port 2019

### API Gateway (Internal Port 8000)
**Intelligent service mesh with Redis-powered features**
- **Dedicated Database**: PostgreSQL on port 5434 (service registry, logs)
- **Dedicated Redis Cache**: Redis on port 6381 with advanced features:
  - **Sliding Window Rate Limiting**: 1000 req/min (anonymous), 5000 req/min (authenticated)
  - **Response Caching**: Intelligent GET request caching with TTL management
  - **Service Discovery Cache**: Fast service resolution with 60s TTL
  - **Circuit Breaker State**: Distributed fault tolerance tracking
- **Authentication Middleware**: JWT token validation with blacklist checking
- **Request Proxying**: Intelligent routing with connection pooling
- **Enhanced Logging**: Request tracing with timing and correlation IDs

### Authentication Service (Internal Port 8001)
**Secure authentication with Redis-powered security features**
- **mTLS Server**: Validates gateway client certificates
- **Dedicated Database**: PostgreSQL on port 5433 (user accounts)
- **Dedicated Redis Cache**: Redis on port 6380 with security features:
  - **JWT Token Blacklisting**: Instant logout and token invalidation
  - **User Session Caching**: Fast session lookup with 1-hour TTL
  - **Failed Login Tracking**: Sliding window attempt counting (15-min TTL)
  - **Account Lockout Protection**: Automatic lockout after 5 failed attempts
- **Secure Password Handling**: Server-side bcrypt with strong validation
- **Enhanced Authentication**: Rate-limited login with intelligent caching

## Security Features

### **Multi-Layer Security Architecture**
- **mTLS Communication**: Mutual TLS between Gateway and Auth Service
- **TLS Termination**: HTTPS with automatic certificate management via Caddy
- **Certificate Authority**: Internal CA for service-to-service communication
- **Redis-Powered Security**: Distributed security features across all services

### **Authentication & Session Security**
- **JWT Token Blacklisting**: Instant logout with Redis-based token invalidation
- **User Session Caching**: Secure session management with automatic expiration
- **Server-Side Password Hashing**: Bcrypt with salt rounds=12 and strong validation
- **Password Strength Requirements**: Minimum 8 characters with uppercase, lowercase, and numbers
- **Account Lockout Protection**: Automatic protection against brute force attacks

### **Advanced Rate Limiting**
- **Sliding Window Algorithm**: Precise rate limiting using Redis sorted sets
- **Differentiated Limits**: Higher limits for authenticated users (5000 req/min vs 1000 req/min)
- **Failed Login Tracking**: Per-user attempt counting with 15-minute sliding windows
- **Emergency DDoS Protection**: Caddy-level protection for extreme attacks (1000 req/min)
- **Graceful Degradation**: Rate limiting fails open if Redis is unavailable

### **Request Security & Monitoring**
- **Request Tracing**: Full correlation ID tracking from Caddy through all services
- **Security Headers**: HSTS, CSP, X-Frame-Options, and more via Caddy
- **Service Isolation**: Each service has separate credentials, databases, and Redis instances
- **Client Verification**: Trusted host middleware for internal requests
- **Enhanced Logging**: Structured logging with timing and security context
- **Error Sanitization**: No sensitive data in error responses

## Deployment Options

### Option 1: Full Microservices with Caddy Ingress (Recommended)
Deploy all services with mTLS and HTTPS termination:
```bash
docker-compose -f docker-compose.microservices.yml up -d

# Services available at:
# - Caddy Ingress: https://localhost (all endpoints)
# - Caddy Admin: http://localhost:2019
```

### Option 2: Independent Service Deployment

**Deploy API Gateway with Caddy Ingress:**
```bash
cd src/api-gateway
docker-compose up -d

# Gateway with Caddy available at: https://localhost
```

**Deploy Auth Service independently:**
```bash
cd src/auth_service
docker-compose up -d

# Auth service available at: http://localhost:8001
```

### Option 3: Manual Setup

**Auth Service with Reverse Proxy:**
```bash
cd src/auth_service
cp .env.example .env
# Edit .env with your configurations

# Option 1: With HTTPS reverse proxy (recommended)
docker-compose up -d

# Option 2: Direct HTTP (development only)
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**API Gateway:**
```bash
cd src/api-gateway
cp .env.example .env
# Edit AUTH_SERVICE_URL to point to your auth service
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### API Endpoints (via Caddy Ingress at `https://localhost`)

#### **Authentication Endpoints**
- `POST /auth/register` - Register new user with plaintext password (over HTTPS)
- `POST /auth/login` - User login with plaintext password (over HTTPS) 
- `POST /auth/logout` - Logout user and blacklist JWT token (authenticated)
- `GET /auth/verify` - Verify JWT token (includes blacklist checking)
- `GET /auth/me` - Get current user info (with session caching)

#### **System Endpoints**
- `GET /health` - Health check endpoint (bypasses rate limiting)
- `GET /services` - List registered services (authenticated)

#### **Rate Limiting Headers**
All API responses include rate limiting information:
- `X-RateLimit-Limit` - Total requests allowed per window
- `X-RateLimit-Remaining` - Requests remaining in current window
- `X-RateLimit-Reset` - Unix timestamp when window resets
- `X-RateLimit-Window` - Rate limit window duration in seconds
- `X-RateLimit-Client` - Client type (ip/user)

#### **Caching Headers**
Cached responses include cache status:
- `X-Cache` - Cache status (HIT/MISS)
- `X-Cache-Date` - When response was cached (for HIT)
- `X-Cache-TTL` - Cache TTL in seconds (for MISS)

### Caddy Admin API (`http://localhost:2019`)
- `GET /config/` - View current configuration
- `GET /metrics` - Prometheus metrics
- `POST /load` - Reload configuration
- `GET /pki/ca/local` - View internal CA

## Authentication Flow

The service uses server-side bcrypt password hashing:

### Registration (HTTPS via Caddy)
```bash
curl -k -X POST "https://localhost/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "MySecurePass123"
  }'
```

### Login (HTTPS via Caddy)
```bash
curl -k -X POST "https://localhost/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MySecurePass123"
  }'
```

**Security & Performance Features:**
- **mTLS**: Mutual TLS between Gateway and Auth Service
- **TLS Termination**: HTTPS encryption via Caddy with automatic certificates
- **Advanced Rate Limiting**: Redis-based sliding window (1000-5000 req/min based on auth status)
- **JWT Token Blacklisting**: Instant logout with Redis-powered token invalidation
- **Password validation**: 8+ chars, uppercase, lowercase, numbers with failed attempt tracking
- **Bcrypt hashing**: Salt rounds=12 for strong password protection
- **Account Lockout**: Automatic protection after 5 failed login attempts
- **Response Caching**: Intelligent GET request caching for improved performance
- **Security headers**: HSTS, CSP, XSS protection via Caddy
- **Certificate Authority**: Internal CA for service communication
- **Memory safety**: Passwords cleared from memory after processing

## Redis Cache Features

### **Authentication Service Cache (Redis DB 1)**
- **Token Blacklist**: Instant JWT invalidation on logout
- **User Sessions**: 1-hour cached session data for authenticated users
- **Failed Login Tracking**: 15-minute sliding window for brute force protection
- **Account Lockout**: Automatic 15-minute lockout after 5 failed attempts
- **Cache TTL Management**: Automatic expiration based on token/session lifecycles

### **API Gateway Cache (Redis DB 0)**
- **Rate Limiting**: Sliding window algorithm with Redis sorted sets
- **Response Caching**: GET request caching with configurable TTL (5-10 minutes)
- **Service Discovery**: 60-second service information caching
- **Circuit Breaker**: Distributed failure state tracking
- **Connection Pooling**: Optimized Redis connections (50 max for gateway, 20 for auth)

### **Cache Performance Benefits**
- **Reduced Database Load**: Session and service data cached in Redis
- **Faster Authentication**: Blacklist and session checks in sub-millisecond time
- **Improved Rate Limiting**: Precise sliding window calculations
- **Better User Experience**: Cached responses for faster API performance
- **High Availability**: Graceful degradation when Redis is unavailable

## Environment Variables

### **Authentication Service**
```bash
# Database Configuration
AUTH_DATABASE_URL=postgresql://auth_user:auth_password@localhost:5433/auth_db

# Redis Cache Configuration
AUTH_REDIS_URL=redis://localhost:6380/1

# JWT Configuration
JWT_SECRET_KEY=your_secret_key_here_change_in_production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Service Configuration
AUTH_SERVICE_HOST=0.0.0.0
AUTH_SERVICE_PORT=8001
ENVIRONMENT=development

# Security Configuration
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_MINUTES=15
```

### **API Gateway**
```bash
# Database Configuration  
GATEWAY_DATABASE_URL=postgresql://gateway_user:gateway_password@localhost:5434/gateway_db

# Redis Cache Configuration
GATEWAY_REDIS_URL=redis://localhost:6381/0

# Service Discovery
AUTH_SERVICE_URL=https://localhost:8001

# Rate Limiting Configuration
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT_REQUESTS=1000
DEFAULT_RATE_LIMIT_WINDOW=60
AUTHENTICATED_RATE_LIMIT_REQUESTS=5000
AUTHENTICATED_RATE_LIMIT_WINDOW=60

# Gateway Configuration
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000
ENVIRONMENT=development

# Security & Features
JWT_VERIFICATION_ENABLED=true
CIRCUIT_BREAKER_ENABLED=true
METRICS_ENABLED=true
ACCESS_LOG_ENABLED=true
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
black src/
flake8 src/
mypy src/
```

## Production Deployment

1. **Update Security Settings**
   - Change `JWT_SECRET_KEY` to a strong random value
   - Set `DATABASE_URL` to production database
   - Configure proper CORS origins

2. **Deploy with Docker**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

3. **Health Monitoring**
   - Monitor `/health` endpoints
   - Check logs in `logs/` directory
   - Set up alerts for service failures

## Architecture

```
Client → API Gateway → Auth Service → Database
                   → Other Services
```

The API Gateway acts as a single entry point, handling authentication and routing requests to appropriate backend services.