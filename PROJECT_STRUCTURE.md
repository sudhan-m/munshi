# Project Structure

This document outlines the complete structure of the Munshi microservices project.

## Root Directory

```
munshi/
├── README.md                           # Main project documentation
├── PROJECT_STRUCTURE.md               # This file - project structure guide
├── docker-compose.microservices.yml   # Complete microservices deployment
└── src/                               # Source code directory
    ├── auth_service/                  # Authentication microservice
    └── api-gateway/                   # API Gateway microservice
```

## Authentication Service (`src/auth_service/`)

```
src/auth_service/
├── __init__.py                  # Package initialization
├── main.py                      # FastAPI application and endpoints
├── models.py                    # SQLAlchemy and Pydantic models
├── database.py                  # Database configuration and session management
├── auth.py                      # Authentication utilities and password hashing
├── config.py                    # Service configuration and settings
├── requirements.txt             # Python dependencies for auth service
├── .env.example                 # Environment variables template
├── Dockerfile                   # Docker image configuration
└── docker-compose.yml           # Standalone deployment configuration
```

### Authentication Service Features

- **Secure Authentication**: Client-side PBKDF2 + server-side bcrypt double hashing
- **JWT Token Management**: Stateless token-based authentication
- **User Management**: Registration, login, profile endpoints
- **Dedicated Database**: PostgreSQL on port 5433 (auth_db)
- **Dedicated Cache**: Redis on port 6380 for sessions and caching
- **Independent Deployment**: Can be deployed separately from other services

## API Gateway Service (`src/api-gateway/`)

```
src/api-gateway/
├── __init__.py                  # Package initialization
├── main.py                      # FastAPI application and main routes
├── router.py                    # Request routing and service discovery
├── middleware.py                # Authentication middleware
├── database.py                  # Database models and connection management
├── config.py                    # Gateway configuration and settings
├── requirements.txt             # Python dependencies for gateway
├── .env.example                 # Environment variables template
├── Dockerfile                   # Docker image configuration
└── docker-compose.yml           # Standalone deployment configuration
```

### API Gateway Features

- **Service Discovery**: Dynamic service registration and health monitoring
- **Authentication Middleware**: JWT token validation via auth service
- **Request Proxying**: Intelligent routing to backend microservices
- **Rate Limiting**: IP and user-based request throttling
- **Request Logging**: Comprehensive HTTP request/response logging
- **Dedicated Database**: PostgreSQL on port 5434 (gateway_db)
- **Dedicated Cache**: Redis on port 6381 for caching and rate limiting

## Database Architecture

### Authentication Service Database (auth_db)
- **Port**: 5433
- **Tables**:
  - `users`: User accounts and authentication data
- **Redis**: Port 6380 (database 1) for auth-specific caching

### API Gateway Database (gateway_db)
- **Port**: 5434
- **Tables**:
  - `service_registry`: Registered microservices and health status
  - `rate_limits`: Rate limiting entries per client/endpoint
  - `request_logs`: HTTP request/response logging
- **Redis**: Port 6381 (database 0) for gateway caching and rate limiting

## Service Communication

```
Client Request → API Gateway (Port 8000) → Auth Service (Port 8001)
                      ↓
               Other Microservices
```

### Authentication Flow
1. Client gets salt from auth service: `GET /auth/salt`
2. Client hashes password with PBKDF2 using salt
3. Client sends hashed password to auth service: `POST /auth/login`
4. Auth service verifies hash and returns JWT token
5. Client includes JWT token in subsequent requests to gateway
6. Gateway validates token with auth service: `GET /auth/verify`
7. Gateway forwards authenticated requests to backend services

## Security Features

### Password Security
- **No Plaintext Transmission**: Passwords are hashed client-side before sending
- **Double Hashing**: Client PBKDF2 + server bcrypt for storage
- **Unique Salts**: Each password hash uses a unique cryptographic salt

### Service Isolation
- **Separate Databases**: Each service has its own PostgreSQL database
- **Separate Configuration**: Independent environment variables and settings
- **Separate Deployment**: Services can be deployed and scaled independently

### Authentication
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Token Validation**: Centralized token verification via auth service
- **User Context**: User information injected into proxied requests

## Deployment Options

### 1. Complete Microservices Deployment
```bash
docker-compose -f docker-compose.microservices.yml up -d
```
- Deploys all services with separate databases
- Services communicate via Docker network
- Recommended for production

### 2. Independent Service Deployment

**Auth Service Only**:
```bash
cd src/auth_service
docker-compose up -d
```

**Gateway Only**:
```bash
cd src/api-gateway
docker-compose up -d
```

### 3. Development Setup
```bash
# Auth Service
cd src/auth_service
pip install -r requirements.txt
python -m uvicorn main:app --port 8001

# API Gateway
cd src/api-gateway
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

## Environment Configuration

Each service uses environment variables for configuration:

### Auth Service Environment Variables
- `AUTH_DATABASE_URL`: PostgreSQL connection for auth database
- `AUTH_REDIS_URL`: Redis connection for auth service
- `JWT_SECRET_KEY`: Secret key for JWT token signing
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

### Gateway Environment Variables
- `GATEWAY_DATABASE_URL`: PostgreSQL connection for gateway database
- `GATEWAY_REDIS_URL`: Redis connection for gateway service
- `AUTH_SERVICE_URL`: URL of the authentication service
- `RATE_LIMIT_REQUESTS`: Rate limiting configuration

## API Endpoints

### Authentication Service (Port 8001)
- `GET /auth/salt` - Get cryptographic salt for password hashing
- `POST /auth/register` - Register new user with pre-hashed password
- `POST /auth/login` - Login with pre-hashed password
- `GET /auth/verify` - Verify JWT token (used by gateway)
- `GET /auth/me` - Get current user information
- `GET /health` - Service health check

### API Gateway (Port 8000)
- `GET /health` - Gateway health check
- `GET /services` - List registered services (authenticated)
- `POST /services/{name}` - Register new service (authenticated)
- `DELETE /services/{name}` - Unregister service (authenticated)
- `* /auth/*` - Proxy to authentication service (no auth required)
- `* /protected/{service}/*` - Proxy to services (authentication required)

## Monitoring and Observability

### Health Checks
- Each service provides `/health` endpoint
- Docker health checks configured for all containers
- Gateway monitors backend service health

### Logging
- Structured logging with request IDs
- Separate log files for each service
- HTTP access logs in gateway
- Error logs with stack traces

### Request Tracing
- Unique request IDs for each HTTP request
- Request/response timing
- User context in logs
- Cross-service request correlation

## Development Guidelines

### Adding New Services
1. Create new directory in `src/`
2. Follow the same structure as existing services
3. Add service configuration to gateway
4. Update docker-compose files
5. Document endpoints and configuration

### Security Considerations
- Never transmit plaintext passwords
- Always validate inputs
- Use prepared statements for database queries
- Implement proper CORS policies
- Use HTTPS in production
- Rotate JWT secrets regularly

### Testing
- Unit tests for business logic
-Integration tests for API endpoints
- End-to-end tests for authentication flow
- Load testing for performance validation
- Security testing for vulnerability assessment