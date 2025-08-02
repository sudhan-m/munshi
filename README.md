# Munshi Microservices Architecture

A secure, production-ready microservices architecture with independent API Gateway and Authentication services built with Python FastAPI.

## Architecture Overview

This project implements a true microservices architecture where each service:
- Has its own dedicated database
- Can be deployed independently
- Has separate configuration and dependencies
- Communicates via HTTP APIs

```
┌─────────────────┐    ┌─────────────────────────────────┐
│   API Gateway   │    │       Auth Service              │
│   (Port 8000)   │◄───┤   HTTPS (Port 443/8443)        │
│                 │    │  ┌─────────────────────────────┐ │
│ ┌─────────────┐ │    │  │    Nginx Reverse Proxy     │ │
│ │ Gateway DB  │ │    │  │  (SSL Termination, Rate     │ │
│ │(Port 5434)  │ │    │  │   Limiting, Security)       │ │
│ └─────────────┘ │    │  └─────────────┬───────────────┘ │
│ ┌─────────────┐ │    │                │                 │
│ │Gateway Redis│ │    │  ┌─────────────▼───────────────┐ │
│ │(Port 6381)  │ │    │  │   FastAPI Auth Service      │ │
│ └─────────────┘ │    │  │      (Port 8001)            │ │
└─────────────────┘    │  └─────────────────────────────┘ │
                       │ ┌─────────────┐ ┌─────────────┐ │
                       │ │   Auth DB   │ │ Auth Redis  │ │
                       │ │ (Port 5433) │ │ (Port 6380) │ │
                       │ └─────────────┘ └─────────────┘ │
                       └─────────────────────────────────┘
```

## Services

### Authentication Service (HTTPS Port 443/8443)
**Independent microservice for user authentication with SSL termination**
- **Nginx Reverse Proxy**: HTTPS termination with mkcert (dev) / Let's Encrypt (prod)
- **FastAPI Backend**: Internal HTTP service on port 8001
- **Dedicated Database**: PostgreSQL on port 5433
- **Dedicated Cache**: Redis on port 6380
- **Secure Password Handling**: Server-side bcrypt with strong validation
- **JWT Authentication**: Stateless token-based authentication
- **Security Features**: Rate limiting, security headers, request filtering
- **SSL/TLS**: Strong cipher suites, HSTS, perfect forward secrecy

### API Gateway (Port 8000)
**Independent microservice for request routing and management**
- **Dedicated Database**: PostgreSQL on port 5434 (service registry, logs)
- **Dedicated Cache**: Redis on port 6381 (rate limiting, caching)
- **Service Discovery**: Dynamic service registration and health checks
- **Authentication Middleware**: Token validation via auth service
- **Request Proxying**: Intelligent routing to backend services
- **Rate Limiting**: IP and user-based rate limiting
- **Circuit Breaker**: Fault tolerance for downstream services
- **Request Logging**: Comprehensive request/response logging

## Security Features

- **HTTPS Everywhere**: SSL termination with strong TLS configuration
- **Server-Side Password Hashing**: Bcrypt with salt rounds=12 and strong validation
- **Password Strength Requirements**: Minimum 8 characters with uppercase, lowercase, and numbers
- **Rate Limiting**: Protection against brute force attacks (5-10 req/min)
- **Security Headers**: HSTS, CSP, X-Frame-Options, and more
- **JWT Tokens**: Secure, stateless authentication
- **Service Isolation**: Each service has separate credentials and databases
- **Request Tracing**: Full request ID tracking across services
- **Error Sanitization**: No sensitive data in error responses

## Deployment Options

### Option 1: Full Microservices (Recommended)
Deploy all services together with separate databases and HTTPS:
```bash
docker-compose -f docker-compose.microservices.yml up -d

# Services available at:
# - Auth Service: https://localhost:8443
# - API Gateway: http://localhost:8000
```

### Option 2: Independent Service Deployment

**Deploy Auth Service independently with HTTPS:**
```bash
cd src/auth_service
docker-compose up -d

# Auth service available at: https://localhost
```

**Deploy API Gateway independently:**
```bash
cd src/api-gateway
docker-compose up -d
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

### Authentication Service (`https://localhost` or `https://your-domain.com:8443`)
- `POST /auth/register` - Register new user with plaintext password (over HTTPS)
- `POST /auth/login` - User login with plaintext password (over HTTPS)
- `GET /auth/verify` - Verify JWT token
- `GET /auth/me` - Get current user info
- `GET /health` - Health check endpoint

### API Gateway (`http://localhost:8000`)
- `GET /health` - Health check
- `GET /services` - List registered services
- `POST /auth/*` - Proxy to auth service
- `* /protected/{service}/*` - Authenticated proxy to services

## Authentication Flow

The service uses server-side bcrypt password hashing:

### Registration (HTTPS)
```bash
curl -X POST "https://localhost/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "johndoe",
    "password": "MySecurePass123"
  }'
```

### Login (HTTPS)
```bash
curl -X POST "https://localhost/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "MySecurePass123"
  }'
```

**Security Features:**
- **HTTPS Encryption**: All password transmission encrypted with TLS
- **Password validation**: 8+ chars, uppercase, lowercase, numbers
- **Bcrypt hashing**: Salt rounds=12 for strong password protection
- **Memory safety**: Passwords cleared from memory after processing
- **Rate limiting**: Protection against brute force attacks
- **Security headers**: HSTS, CSP, XSS protection
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