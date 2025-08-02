# Munshi Microservices Architecture

A secure, production-ready microservices architecture with independent API Gateway and Authentication services built with Python FastAPI.

## Architecture Overview

This project implements a true microservices architecture where each service:
- Has its own dedicated database
- Can be deployed independently
- Has separate configuration and dependencies
- Communicates via HTTP APIs

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                            │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS (TLS)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Caddy Ingress                               │
│           (Port 443 - TLS Termination)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Rate Limiting, Security Headers, Load Balancing   │   │
│  └─────────────────────┬───────────────────────────────┘   │
└────────────────────────┼───────────────────────────────────┘
                         │ HTTP (Internal)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway                               │
│                  (Port 8000)                               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │ Gateway DB  │ │Gateway Redis│ │   Service Registry   │   │
│  │(Port 5434)  │ │(Port 6381)  │ │   Auth Middleware    │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │ mTLS (Mutual TLS)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 Auth Service                                │
│                (Port 8001)                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │   Auth DB   │ │ Auth Redis  │ │   mTLS Validation    │   │
│  │ (Port 5433) │ │ (Port 6380) │ │   JWT Management     │   │
│  └─────────────┘ └─────────────┘ └─────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Services

### Caddy Ingress (HTTPS Port 443)
**TLS termination and reverse proxy layer**
- **Automatic HTTPS**: Self-signed certificates (dev) / Let's Encrypt (prod)
- **Rate Limiting**: 10 req/min for auth endpoints, 100 req/min general
- **Security Headers**: HSTS, CSP, XSS protection, and more
- **Load Balancing**: Round-robin with health checks
- **Admin API**: Management interface on port 2019

### API Gateway (Internal Port 8000)
**Service mesh orchestration and authentication**
- **Dedicated Database**: PostgreSQL on port 5434 (service registry, logs)
- **Dedicated Cache**: Redis on port 6381 (rate limiting, caching)
- **mTLS Client**: Secure communication with auth service
- **Service Discovery**: Dynamic service registration and health checks
- **Authentication Middleware**: JWT token validation
- **Request Proxying**: Intelligent routing to backend services
- **Circuit Breaker**: Fault tolerance for downstream services

### Authentication Service (Internal Port 8001)
**Secure authentication with mTLS support**
- **mTLS Server**: Validates gateway client certificates
- **Dedicated Database**: PostgreSQL on port 5433
- **Dedicated Cache**: Redis on port 6380
- **Secure Password Handling**: Server-side bcrypt with strong validation
- **JWT Authentication**: Stateless token-based authentication
- **Client Verification**: Trusted host middleware for internal communication

## Security Features

- **mTLS Communication**: Mutual TLS between Gateway and Auth Service
- **TLS Termination**: HTTPS with automatic certificate management via Caddy
- **Certificate Authority**: Internal CA for service-to-service communication
- **Server-Side Password Hashing**: Bcrypt with salt rounds=12 and strong validation
- **Password Strength Requirements**: Minimum 8 characters with uppercase, lowercase, and numbers
- **Rate Limiting**: Multi-tier protection (10 req/min auth, 100 req/min general)
- **Security Headers**: HSTS, CSP, X-Frame-Options, and more via Caddy
- **JWT Tokens**: Secure, stateless authentication
- **Service Isolation**: Each service has separate credentials and databases
- **Client Verification**: Trusted host middleware for internal requests
- **Request Tracing**: Full request ID tracking across services
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
- `POST /auth/register` - Register new user with plaintext password (over HTTPS)
- `POST /auth/login` - User login with plaintext password (over HTTPS)
- `GET /auth/verify` - Verify JWT token
- `GET /auth/me` - Get current user info
- `GET /health` - Health check endpoint
- `GET /services` - List registered services (authenticated)

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

**Security Features:**
- **mTLS**: Mutual TLS between Gateway and Auth Service
- **TLS Termination**: HTTPS encryption via Caddy with automatic certificates
- **Rate limiting**: 10 req/min for auth endpoints (brute force protection)
- **Password validation**: 8+ chars, uppercase, lowercase, numbers
- **Bcrypt hashing**: Salt rounds=12 for strong password protection
- **Memory safety**: Passwords cleared from memory after processing
- **Security headers**: HSTS, CSP, XSS protection via Caddy
- **Certificate Authority**: Internal CA for service communication
- **No plaintext storage**: Passwords never stored in plaintext

## Environment Variables

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/munshi_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
API_GATEWAY_PORT=8000
AUTH_SERVICE_PORT=8001
AUTH_SERVICE_URL=http://localhost:8001
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