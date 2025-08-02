# API Gateway Service - Beginner's Guide

A secure, production-ready API Gateway microservice built with Python FastAPI. This guide will walk you through every concept, pattern, and technology used in this service.

## 📚 Table of Contents

- [What is an API Gateway?](#what-is-an-api-gateway)
- [Architecture Overview](#architecture-overview)
- [Core Concepts Explained](#core-concepts-explained)
- [Libraries and Technologies](#libraries-and-technologies)
- [Database Design](#database-design)
- [API Endpoints Tutorial](#api-endpoints-tutorial)
- [Setting Up Development Environment](#setting-up-development-environment)
- [Gateway Patterns](#gateway-patterns)
- [Testing the Service](#testing-the-service)
- [Common Issues and Solutions](#common-issues-and-solutions)

## What is an API Gateway?

An **API Gateway** is a server that acts as a single entry point for all client requests in a microservices architecture. Think of it as a smart traffic controller that:

- **Routes requests** to the appropriate backend services
- **Authenticates users** before allowing access to protected resources
- **Rate limits** requests to prevent abuse and ensure fair usage
- **Logs all traffic** for monitoring and debugging
- **Handles cross-cutting concerns** like CORS, SSL termination, and request/response transformation

### Why Use an API Gateway?

Without a gateway, clients would need to:
- ❌ Know the addresses of all microservices
- ❌ Handle authentication separately for each service
- ❌ Deal with different protocols and formats
- ❌ Implement retry logic and circuit breakers

With a gateway, you get:
- ✅ Single entry point for all API calls
- ✅ Centralized authentication and authorization
- ✅ Unified logging and monitoring
- ✅ Load balancing and failover
- ✅ Request/response transformation
- ✅ Rate limiting and throttling

## Architecture Overview

```mermaid
graph TB
    subgraph "External Clients"
        WEB[Web Application]
        MOBILE[Mobile App]
        API_CLIENT[API Client]
    end
    
    subgraph "API Gateway - Port 8000"
        ROUTER[Request Router<br/>Service Discovery]
        AUTH_MW[Authentication<br/>Middleware]
        RATE_LIMITER[Rate Limiter<br/>Throttling]
        LOGGER[Request Logger<br/>Audit Trail]
        CIRCUIT[Circuit Breaker<br/>Fault Tolerance]
        
        ROUTER --> AUTH_MW
        AUTH_MW --> RATE_LIMITER
        RATE_LIMITER --> LOGGER
        LOGGER --> CIRCUIT
    end
    
    subgraph "Gateway Database"
        GW_DB[(PostgreSQL<br/>gateway_db:5434)]
        GW_REDIS[(Redis Cache<br/>Port 6381)]
        
        REGISTRY[Service Registry]
        RATE_DATA[Rate Limit Data]
        REQUEST_LOGS[Request Logs]
        
        GW_DB --> REGISTRY
        GW_DB --> RATE_DATA
        GW_DB --> REQUEST_LOGS
    end
    
    subgraph "Backend Services"
        AUTH_SVC[Auth Service<br/>Port 8001]
        USER_SVC[User Service<br/>Port 8002]
        ORDER_SVC[Order Service<br/>Port 8003]
        PAYMENT_SVC[Payment Service<br/>Port 8004]
    end
    
    WEB --> ROUTER
    MOBILE --> ROUTER
    API_CLIENT --> ROUTER
    
    ROUTER --> GW_DB
    RATE_LIMITER --> GW_REDIS
    LOGGER --> GW_DB
    
    CIRCUIT --> AUTH_SVC
    CIRCUIT --> USER_SVC
    CIRCUIT --> ORDER_SVC
    CIRCUIT --> PAYMENT_SVC
    
    style ROUTER fill:#e1f5fe
    style AUTH_MW fill:#e8f5e8
    style RATE_LIMITER fill:#fff3e0
    style LOGGER fill:#f3e5f5
    style CIRCUIT fill:#fce4ec
    style GW_DB fill:#f3e5f5
    style GW_REDIS fill:#fff3e0
```

### Key Components:

1. **Request Router**: Determines which backend service should handle each request
2. **Authentication Middleware**: Verifies JWT tokens with the auth service
3. **Rate Limiter**: Prevents abuse by limiting requests per client/endpoint
4. **Request Logger**: Records all traffic for monitoring and debugging
5. **Circuit Breaker**: Provides fault tolerance when backend services fail
6. **Service Registry**: Tracks available backend services and their health
7. **Database & Cache**: Stores operational data and improves performance

## Core Concepts Explained

### 🌐 Service Discovery

Service Discovery is how the gateway knows which services are available and where to find them.

```mermaid
sequenceDiagram
    participant SVC as Backend Service
    participant GW as API Gateway
    participant DB as Service Registry
    participant CLIENT as Client
    
    Note over SVC,DB: Service Registration
    SVC->>GW: POST /services/user-service<br/>{ "url": "http://user-service:8002" }
    GW->>DB: INSERT service registration
    DB-->>GW: Service registered
    GW-->>SVC: Registration confirmed
    
    Note over CLIENT,DB: Service Discovery
    CLIENT->>GW: GET /protected/user-service/profile
    GW->>DB: SELECT service_url WHERE name = 'user-service'
    DB-->>GW: http://user-service:8002
    GW->>SVC: GET http://user-service:8002/profile
    SVC-->>GW: User profile data
    GW-->>CLIENT: User profile data
    
    style SVC fill:#e8f5e8
    style GW fill:#e1f5fe
    style DB fill:#f3e5f5
    style CLIENT fill:#fff3e0
```

### 🛡️ Authentication Flow

The gateway acts as an authentication checkpoint for all requests.

```mermaid
sequenceDiagram
    participant CLIENT as Client
    participant GW as API Gateway
    participant AUTH as Auth Service
    participant BACKEND as Backend Service
    
    CLIENT->>GW: GET /protected/user-service/profile<br/>Authorization: Bearer <token>
    
    Note over GW: Extract JWT token from header
    GW->>AUTH: GET /auth/verify<br/>Authorization: Bearer <token>
    
    alt Token Valid
        AUTH-->>GW: { "email": "user@example.com", "valid": true }
        
        Note over GW: Add user context to request
        GW->>BACKEND: GET /profile<br/>X-User-Email: user@example.com<br/>X-User-ID: 123
        BACKEND-->>GW: Profile data
        GW-->>CLIENT: Profile data
        
    else Token Invalid
        AUTH-->>GW: 401 Unauthorized
        GW-->>CLIENT: 401 Unauthorized
    end
    
    style CLIENT fill:#fff3e0
    style GW fill:#e1f5fe
    style AUTH fill:#e8f5e8
    style BACKEND fill:#f3e5f5
```

### ⚡ Rate Limiting

Rate limiting prevents abuse by limiting how many requests a client can make.

```mermaid
flowchart TD
    REQUEST[Incoming Request] --> EXTRACT[Extract Client ID<br/>IP or User ID]
    EXTRACT --> CHECK[Check Rate Limit<br/>in Redis/Database]
    
    CHECK --> WITHIN{Within Limit?}
    
    WITHIN -->|Yes| INCREMENT[Increment Counter]
    INCREMENT --> FORWARD[Forward to Backend]
    FORWARD --> RESPONSE[Return Response]
    
    WITHIN -->|No| REJECT[429 Too Many Requests]
    
    CHECK --> EXPIRED{Window Expired?}
    EXPIRED -->|Yes| RESET[Reset Counter]
    RESET --> INCREMENT
    
    style REQUEST fill:#e1f5fe
    style WITHIN fill:#fff3e0
    style INCREMENT fill:#e8f5e8
    style REJECT fill:#ffebee
    style FORWARD fill:#e8f5e8
```

### 🔄 Circuit Breaker Pattern

Circuit breakers prevent cascading failures when backend services are down.

```mermaid
stateDiagram-v2
    [*] --> Closed
    
    Closed --> Open : Failure threshold reached
    Open --> HalfOpen : Timeout period elapsed
    HalfOpen --> Closed : Request succeeds
    HalfOpen --> Open : Request fails
    
    state Closed {
        [*] --> Normal : All requests pass through
        Normal --> CountingFailures : Failure detected
        CountingFailures --> Normal : Success resets counter
        CountingFailures --> [*] : Threshold reached
    }
    
    state Open {
        [*] --> FailFast : All requests rejected immediately
        FailFast --> [*] : Return cached response or error
    }
    
    state HalfOpen {
        [*] --> TestRequest : Allow limited requests
        TestRequest --> [*] : Evaluate success/failure
    }
```

**Circuit Breaker States:**
- **Closed**: Normal operation, requests pass through
- **Open**: Service is down, fail fast without calling backend
- **Half-Open**: Testing if service has recovered

## Libraries and Technologies

### 🐍 Core Python Libraries

#### FastAPI
```python
from fastapi import FastAPI, Depends, Request
```
**What it does**: Modern, fast web framework for building APIs
**Why we use it**:
- ✅ Excellent performance (comparable to NodeJS and Go)
- ✅ Automatic request/response validation
- ✅ Built-in OpenAPI documentation
- ✅ Dependency injection system
- ✅ WebSocket support for real-time features

#### HTTPx
```python
import httpx
```
**What it does**: Modern HTTP client for Python
**Why we use it**:
- ✅ Async/await support for high performance
- ✅ Connection pooling for efficiency
- ✅ Timeout handling and retry logic
- ✅ HTTP/2 support
- ✅ Excellent error handling

#### SQLAlchemy
```python
from sqlalchemy import Column, Integer, String, DateTime
```
**What it does**: Database ORM for managing gateway data
**Why we use it**:
- ✅ Service registry management
- ✅ Rate limiting data storage
- ✅ Request logging and analytics
- ✅ Database migrations

### 🗄️ Data Storage

#### PostgreSQL
**What it does**: Relational database for structured data
**Gateway Usage**:
- **Service Registry**: Track registered services and health status
- **Rate Limiting**: Store rate limit configurations and counters
- **Request Logs**: Audit trail of all API requests
- **Analytics**: Request patterns and performance metrics

#### Redis
**What it does**: In-memory data store for high-speed operations
**Gateway Usage**:
- **Caching**: Store frequently accessed data
- **Rate Limiting**: Fast request counters with TTL
- **Session Storage**: Temporary authentication data
- **Circuit Breaker State**: Track service health status

### 🔧 Configuration Management

#### Pydantic Settings
```python
from pydantic_settings import BaseSettings
```
**What it does**: Type-safe configuration management
**Why we use it**:
- ✅ Environment variable parsing
- ✅ Validation of configuration values
- ✅ Default value handling
- ✅ Documentation of settings

## Database Design

### Service Registry Table

```mermaid
erDiagram
    service_registry {
        SERIAL id PK "Auto-incrementing primary key"
        VARCHAR service_name UK "Unique service identifier"
        VARCHAR service_url "Base URL of the service"
        VARCHAR health_check_url "Health check endpoint"
        BOOLEAN is_active "Service availability status"
        TIMESTAMP last_health_check "Last successful health check"
        TIMESTAMP created_at "Service registration time"
        TIMESTAMP updated_at "Last modification time"
    }
```

### Rate Limiting Table

```mermaid
erDiagram
    rate_limits {
        SERIAL id PK "Auto-incrementing primary key"
        VARCHAR client_id "IP address or user ID"
        VARCHAR endpoint "API endpoint path"
        INTEGER requests_count "Number of requests in window"
        TIMESTAMP window_start "Start of rate limit window"
        TIMESTAMP created_at "Entry creation time"
    }
```

### Request Logs Table

```mermaid
erDiagram
    request_logs {
        SERIAL id PK "Auto-incrementing primary key"
        VARCHAR request_id UK "Unique request identifier"
        VARCHAR method "HTTP method (GET, POST, etc.)"
        VARCHAR path "Request path"
        VARCHAR user_id "Authenticated user ID"
        VARCHAR client_ip "Client IP address"
        VARCHAR user_agent "Client user agent"
        INTEGER status_code "HTTP response status"
        FLOAT response_time "Request processing time"
        TIMESTAMP created_at "Request timestamp"
    }
```

### Database Relationships

```mermaid
erDiagram
    service_registry ||--o{ request_logs : "service processes requests"
    rate_limits ||--o{ request_logs : "rate limiting affects requests"
    
    service_registry {
        SERIAL id PK
        VARCHAR service_name UK
        VARCHAR service_url
        BOOLEAN is_active
        TIMESTAMP last_health_check
    }
    
    rate_limits {
        SERIAL id PK
        VARCHAR client_id
        VARCHAR endpoint
        INTEGER requests_count
        TIMESTAMP window_start
    }
    
    request_logs {
        SERIAL id PK
        VARCHAR request_id UK
        VARCHAR method
        VARCHAR path
        VARCHAR user_id
        INTEGER status_code
        FLOAT response_time
        TIMESTAMP created_at
    }
```

## API Endpoints Tutorial

### 1. Health Check

**Endpoint**: `GET /health`

**Purpose**: Check if the gateway is running and healthy

```bash
curl -X GET "http://localhost:8000/health"
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": 1640995200.0,
  "service": "api-gateway"
}
```

### 2. Service Management

#### List Registered Services

**Endpoint**: `GET /services`
**Authentication**: Required

```bash
curl -X GET "http://localhost:8000/services" \
  -H "Authorization: Bearer <your_jwt_token>"
```

**Response**:
```json
{
  "services": ["auth-service", "user-service", "order-service"]
}
```

#### Register a New Service

**Endpoint**: `POST /services/{service_name}`
**Authentication**: Required

```bash
curl -X POST "http://localhost:8000/services/user-service" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://user-service:8002"}'
```

**Response**:
```json
{
  "message": "Service user-service registered successfully"
}
```

### 3. Request Proxying

#### Public Endpoints (Auth Service)

**Endpoint**: `/auth/*` (No authentication required)

```bash
# Login request proxied to auth service
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password_hash": "hashed_password"
  }'
```

**What happens**:
1. Gateway receives request at `/auth/login`
2. Gateway forwards to auth service at `http://auth-service:8001/auth/login`
3. Auth service processes login
4. Gateway returns auth service response to client

#### Protected Endpoints

**Endpoint**: `/protected/{service_name}/*` (Authentication required)

```bash
# User profile request
curl -X GET "http://localhost:8000/protected/user-service/profile" \
  -H "Authorization: Bearer <your_jwt_token>"
```

**Request Flow**:
```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant A as Auth Service
    participant U as User Service
    
    C->>G: GET /protected/user-service/profile<br/>Authorization: Bearer <token>
    
    Note over G: 1. Extract JWT token
    G->>A: GET /auth/verify<br/>Authorization: Bearer <token>
    A-->>G: { email: "user@example.com", valid: true }
    
    Note over G: 2. Get user details
    G->>A: GET /auth/me<br/>Authorization: Bearer <token>
    A-->>G: { id: 123, email: "user@example.com" }
    
    Note over G: 3. Add user context and forward
    G->>U: GET /profile<br/>X-User-Email: user@example.com<br/>X-User-ID: 123
    U-->>G: User profile data
    G-->>C: User profile data
    
    style C fill:#fff3e0
    style G fill:#e1f5fe
    style A fill:#e8f5e8
    style U fill:#f3e5f5
```

## Setting Up Development Environment

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Running Auth Service (for authentication)

### Step-by-Step Setup

#### 1. Install Dependencies
```bash
cd src/api-gateway
pip install -r requirements.txt
```

#### 2. Set Up Environment Variables
```bash
cp .env.example .env
# Edit .env file with your configuration
```

**Key Environment Variables**:
```bash
# Gateway Database
GATEWAY_DATABASE_URL=postgresql://gateway_user:gateway_password@localhost:5434/gateway_db

# Redis Cache
GATEWAY_REDIS_URL=redis://localhost:6381/0

# Auth Service
AUTH_SERVICE_URL=http://localhost:8001

# Rate Limiting
RATE_LIMIT_ENABLED=true
DEFAULT_RATE_LIMIT_REQUESTS=1000
DEFAULT_RATE_LIMIT_WINDOW=60
```

#### 3. Start Database Services
```bash
# Using Docker
docker-compose up -d gateway-postgres gateway-redis

# Or install locally
# PostgreSQL on port 5434
# Redis on port 6381
```

#### 4. Start Auth Service
```bash
# The gateway needs the auth service for token verification
cd ../auth_service
python -m uvicorn main:app --port 8001
```

#### 5. Run the Gateway
```bash
cd ../api-gateway
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 6. Test the Gateway
Visit: http://localhost:8000/docs

## Gateway Patterns

### 🔄 Request/Response Transformation

The gateway can modify requests and responses as they pass through:

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant S as Service
    
    C->>G: POST /api/v1/users<br/>{ "name": "John Doe" }
    
    Note over G: Transform request:<br/>- Add correlation ID<br/>- Add user context<br/>- Convert format
    
    G->>S: POST /users<br/>{ "name": "John Doe", "correlation_id": "abc123", "created_by": "user@example.com" }
    S-->>G: { "id": 123, "name": "John Doe", "status": "created" }
    
    Note over G: Transform response:<br/>- Add metadata<br/>- Format timestamps<br/>- Remove internal fields
    
    G-->>C: { "data": { "id": 123, "name": "John Doe" }, "meta": { "correlation_id": "abc123" } }
    
    style G fill:#e1f5fe
    style S fill:#e8f5e8
```

### 🚦 Load Balancing

When multiple instances of a service are available:

```mermaid
flowchart TD
    CLIENT[Client Request] --> GATEWAY[API Gateway]
    
    GATEWAY --> REGISTRY[Service Registry<br/>Check Available Instances]
    
    REGISTRY --> STRATEGY{Load Balancing<br/>Strategy}
    
    STRATEGY -->|Round Robin| RR[Next in Rotation]
    STRATEGY -->|Least Connections| LC[Fewest Active Requests]
    STRATEGY -->|Random| RAND[Random Selection]
    
    RR --> INSTANCE1[Service Instance 1]
    LC --> INSTANCE2[Service Instance 2]
    RAND --> INSTANCE3[Service Instance 3]
    
    INSTANCE1 --> RESPONSE[Return Response]
    INSTANCE2 --> RESPONSE
    INSTANCE3 --> RESPONSE
    
    style GATEWAY fill:#e1f5fe
    style STRATEGY fill:#fff3e0
    style RESPONSE fill:#e8f5e8
```

### 🔧 Health Monitoring

The gateway continuously monitors backend service health:

```mermaid
sequenceDiagram
    participant G as Gateway
    participant S1 as Service 1
    participant S2 as Service 2
    participant DB as Service Registry
    
    loop Every 30 seconds
        G->>S1: GET /health
        alt Service Healthy
            S1-->>G: 200 OK { "status": "healthy" }
            G->>DB: UPDATE service SET is_active=true, last_health_check=now()
        else Service Unhealthy
            S1-->>G: 500 Error / Timeout
            G->>DB: UPDATE service SET is_active=false
        end
        
        G->>S2: GET /health
        S2-->>G: 200 OK { "status": "healthy" }
        G->>DB: UPDATE service SET is_active=true, last_health_check=now()
    end
    
    style G fill:#e1f5fe
    style S1 fill:#ffebee
    style S2 fill:#e8f5e8
    style DB fill:#f3e5f5
```

## Testing the Service

### Manual Testing with curl

#### 1. Test Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

#### 2. Test Authentication Flow
```bash
# First, get token from auth service via gateway
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password_hash": "your_hashed_password"
  }'

# Extract token from response
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 3. Test Service Registration
```bash
# Register a new service
curl -X POST "http://localhost:8000/services/test-service" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "http://localhost:8080"}'
```

#### 4. Test Service Discovery
```bash
# List registered services
curl -X GET "http://localhost:8000/services" \
  -H "Authorization: Bearer $TOKEN"
```

### Load Testing

#### Using Apache Bench (ab)
```bash
# Test gateway performance
ab -n 1000 -c 10 http://localhost:8000/health

# Test authenticated endpoints
ab -n 100 -c 5 -H "Authorization: Bearer $TOKEN" \
   http://localhost:8000/services
```

#### Using hey
```bash
# Install hey: go install github.com/rakyll/hey@latest

# Test rate limiting
hey -n 1000 -c 50 -H "Authorization: Bearer $TOKEN" \
    http://localhost:8000/protected/user-service/profile
```

### Integration Testing with Python

```python
import asyncio
import httpx
import time

async def test_gateway_flow():
    """Test complete gateway flow"""
    
    async with httpx.AsyncClient() as client:
        # 1. Health check
        response = await client.get("http://localhost:8000/health")
        assert response.status_code == 200
        print("✅ Health check passed")
        
        # 2. Login through gateway
        login_data = {
            "email": "user@example.com",
            "password_hash": "your_hashed_password"
        }
        response = await client.post(
            "http://localhost:8000/auth/login",
            json=login_data
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        print("✅ Authentication successful")
        
        # 3. Test protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            "http://localhost:8000/auth/me",
            headers=headers
        )
        assert response.status_code == 200
        print("✅ Protected endpoint access successful")
        
        # 4. Test rate limiting
        start_time = time.time()
        tasks = []
        for i in range(10):
            task = client.get(
                "http://localhost:8000/services",
                headers=headers
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited = sum(1 for r in responses if r.status_code == 429)
        
        print(f"✅ Concurrent requests: {success_count} success, {rate_limited} rate limited")
        print(f"✅ Response time: {elapsed:.2f}s for 10 requests")

# Run the test
asyncio.run(test_gateway_flow())
```

## Common Issues and Solutions

### Issue: Gateway can't connect to auth service
**Problem**: Authentication middleware fails
**Solutions**:
1. Check if auth service is running: `curl http://localhost:8001/health`
2. Verify `AUTH_SERVICE_URL` in environment variables
3. Check network connectivity between services
4. Ensure auth service database is accessible

### Issue: Service registration fails
**Problem**: Can't register backend services
**Solutions**:
1. Check authentication token is valid
2. Verify service URL is accessible from gateway
3. Check database connectivity: `GATEWAY_DATABASE_URL`
4. Ensure service registry table exists

### Issue: Rate limiting not working
**Problem**: Requests not being rate limited
**Solutions**:
1. Check if Redis is running: `redis-cli ping`
2. Verify `GATEWAY_REDIS_URL` configuration
3. Check rate limiting is enabled: `RATE_LIMIT_ENABLED=true`
4. Verify rate limit settings in environment variables

### Issue: Request logging missing
**Problem**: No request logs in database
**Solutions**:
1. Check database connection and permissions
2. Verify `request_logs` table exists
3. Check if logging middleware is enabled
4. Ensure sufficient disk space for logs

### Issue: Circuit breaker not functioning
**Problem**: Failed services still receiving requests
**Solutions**:
1. Check circuit breaker configuration
2. Verify failure threshold settings
3. Ensure health check endpoints are configured
4. Check service registry for service status

### Issue: High response times
**Problem**: Gateway introducing latency
**Solutions**:
1. **Connection Pooling**: Ensure HTTPx client reuses connections
2. **Redis Performance**: Check Redis memory usage and connection pool
3. **Database Queries**: Optimize service registry queries
4. **Async Operations**: Verify all operations are properly async
5. **Resource Limits**: Check CPU and memory usage

## Performance Optimization

### 🚀 Caching Strategies

```mermaid
flowchart TD
    REQUEST[Incoming Request] --> CACHE_CHECK{Check Redis Cache}
    
    CACHE_CHECK -->|Hit| RETURN_CACHED[Return Cached Response]
    CACHE_CHECK -->|Miss| FORWARD[Forward to Backend]
    
    FORWARD --> BACKEND[Backend Service]
    BACKEND --> RESPONSE[Service Response]
    RESPONSE --> CACHE_STORE[Store in Cache with TTL]
    CACHE_STORE --> RETURN_RESPONSE[Return Response]
    
    style CACHE_CHECK fill:#fff3e0
    style RETURN_CACHED fill:#e8f5e8
    style CACHE_STORE fill:#e1f5fe
```

### 📊 Monitoring and Metrics

Key metrics to monitor:

1. **Request Rate**: Requests per second
2. **Response Time**: Average, P95, P99 latencies
3. **Error Rate**: 4xx and 5xx response percentages
4. **Service Health**: Backend service availability
5. **Cache Hit Rate**: Percentage of requests served from cache
6. **Rate Limit Hits**: How often rate limits are triggered

```python
# Example metrics collection
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter('gateway_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('gateway_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('gateway_active_connections', 'Active connections')
```

## Security Considerations

### 🔒 Production Security Checklist

1. **HTTPS Only**: Set `REQUIRE_HTTPS=true` in production
2. **Strong JWT Secrets**: Use cryptographically secure secret keys
3. **Rate Limiting**: Configure appropriate limits for your use case
4. **CORS Policy**: Restrict allowed origins to known domains
5. **Request Size Limits**: Prevent large payload attacks
6. **SQL Injection**: Use parameterized queries (SQLAlchemy handles this)
7. **Input Validation**: Validate all incoming data
8. **Error Handling**: Don't expose internal errors to clients

### 🛡️ Security Headers

The gateway should add security headers:

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

This API Gateway provides a robust, scalable foundation for microservices architecture. It handles cross-cutting concerns, provides observability, and ensures security while maintaining high performance.

## Next Steps

1. **API Versioning**: Support multiple API versions
2. **GraphQL Gateway**: Add GraphQL endpoint aggregation
3. **WebSocket Support**: Real-time communication proxying
4. **Advanced Load Balancing**: Implement weighted round-robin
5. **Request Retries**: Automatic retry with exponential backoff
6. **API Documentation**: Auto-generate API docs from registered services
7. **Metrics Dashboard**: Real-time monitoring interface
8. **Alert System**: Automated alerts for service failures

Happy coding! 🚀