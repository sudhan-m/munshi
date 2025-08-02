# Munshi Microservices Architecture

A secure, production-ready microservices architecture with independent API Gateway and Authentication services built with Python FastAPI.

## Architecture Overview

This project implements a true microservices architecture where each service:
- Has its own dedicated database
- Can be deployed independently
- Has separate configuration and dependencies
- Communicates via HTTP APIs

```
┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │  Auth Service   │
│   (Port 8000)   │◄───┤   (Port 8001)   │
│                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Gateway DB  │ │    │ │   Auth DB   │ │
│ │(Port 5434)  │ │    │ │ (Port 5433) │ │
│ └─────────────┘ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │Gateway Redis│ │    │ │ Auth Redis  │ │
│ │(Port 6381)  │ │    │ │ (Port 6380) │ │
│ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘
```

## Services

### Authentication Service (Port 8001)
**Independent microservice for user authentication**
- **Dedicated Database**: PostgreSQL on port 5433
- **Dedicated Cache**: Redis on port 6380
- **Secure Password Handling**: Client-side PBKDF2 + server-side bcrypt
- **JWT Authentication**: Stateless token-based authentication
- **User Management**: Registration, login, profile management
- **Rate Limiting**: Per-user request limiting
- **Account Security**: Login attempt tracking, account lockout

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

- **No Plaintext Passwords**: Client-side PBKDF2 hashing before transmission
- **Double Hashing**: Server-side bcrypt on client hashes
- **JWT Tokens**: Secure, stateless authentication
- **Service Isolation**: Each service has separate credentials and databases
- **Request Tracing**: Full request ID tracking across services
- **Error Sanitization**: No sensitive data in error responses

## Deployment Options

### Option 1: Full Microservices (Recommended)
Deploy all services together with separate databases:
```bash
docker-compose -f docker-compose.microservices.yml up -d
```

### Option 2: Independent Service Deployment

**Deploy Auth Service independently:**
```bash
cd src/auth_service
docker-compose up -d
```

**Deploy API Gateway independently:**
```bash
cd src/api-gateway
docker-compose up -d
```

### Option 3: Manual Setup

**Auth Service:**
```bash
cd src/auth_service
cp .env.example .env
# Edit .env with your configurations
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

### Authentication Service (`http://localhost:8001`)
- `GET /auth/salt` - Get salt for password hashing
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `GET /auth/verify` - Verify JWT token
- `GET /auth/me` - Get current user info

### API Gateway (`http://localhost:8000`)
- `GET /health` - Health check
- `GET /services` - List registered services
- `POST /auth/*` - Proxy to auth service
- `* /protected/{service}/*` - Authenticated proxy to services

## Client-Side Password Hashing

To maintain security, passwords must be hashed client-side before sending:

```python
import hashlib

def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hex(password.encode('utf-8'), salt.encode('utf-8'), 100000, 64)

# Usage:
# 1. GET /auth/salt to get a salt
# 2. Hash password with salt
# 3. Send hashed password in registration/login
```

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