# Authentication Service - Beginner's Guide

A secure, production-ready authentication microservice built with Python FastAPI. This guide will walk you through every concept, library, and security principle used in this service.

## 📚 Table of Contents

- [What is an Authentication Service?](#what-is-an-authentication-service)
- [Architecture Overview](#architecture-overview)
- [Security Concepts Explained](#security-concepts-explained)
- [Libraries and Technologies](#libraries-and-technologies)
- [Database Design](#database-design)
- [API Endpoints Tutorial](#api-endpoints-tutorial)
- [Setting Up Development Environment](#setting-up-development-environment)
- [Security Best Practices](#security-best-practices)
- [Testing the Service](#testing-the-service)
- [Common Issues and Solutions](#common-issues-and-solutions)

## What is an Authentication Service?

An **authentication service** is a specialized microservice that handles user identity verification. Think of it as a digital bouncer that:

- **Registers new users** and stores their credentials securely
- **Verifies user identity** when they log in
- **Issues digital tokens** (like digital ID cards) that prove a user is authenticated
- **Validates tokens** for other services that need to know "who is this user?"

### Why Separate Authentication?

Instead of having every application handle user logins, we create one specialized service that:
- ✅ Centralizes security logic in one place
- ✅ Makes it easier to maintain and update security features
- ✅ Allows multiple applications to share the same user base
- ✅ Reduces code duplication across services

## Architecture Overview

```mermaid
graph TB
    subgraph "Authentication Service"
        API[FastAPI Web Server<br/>Port 8001]
        DB[(PostgreSQL Database<br/>auth_db:5433)]
        REDIS[(Redis Cache<br/>Port 6380)]
        AUTH[Password Security<br/>Double Hashing]
        JWT[JWT Token System<br/>Authentication]
        
        API --> DB
        API --> REDIS
        API --> AUTH
        API --> JWT
        AUTH --> DB
        JWT --> REDIS
    end
    
    CLIENT[Client Applications<br/>Web, Mobile, Desktop]
    GATEWAY[API Gateway<br/>Port 8000]
    
    CLIENT --> API
    GATEWAY --> API
    
    style API fill:#e1f5fe
    style DB fill:#f3e5f5
    style REDIS fill:#fff3e0
    style AUTH fill:#e8f5e8
    style JWT fill:#fce4ec
```

### Key Components:

1. **FastAPI Web Server**: Handles HTTP requests and responses
2. **PostgreSQL Database**: Stores user accounts and authentication data
3. **Redis Cache**: Stores temporary data for faster access
4. **JWT Token System**: Creates and validates digital authentication tokens
5. **Password Security**: Double-layer password protection

## Security Concepts Explained

### 🔐 Password Security: Double Hashing

**The Problem**: Passwords should never be stored in plain text or transmitted over the internet as plain text.

**Our Solution**: We use a "double hashing" approach:

```mermaid
sequenceDiagram
    participant User as User
    participant Client as Client App
    participant Server as Auth Server
    participant DB as Database
    
    User->>Client: Enter password: "mypassword123"
    Client->>Server: GET /auth/salt
    Server-->>Client: { "salt": "random64chars..." }
    
    Note over Client: Client-side PBKDF2 hashing
    Client->>Client: hash = pbkdf2("mypassword123", salt, 100000)
    
    Client->>Server: POST /auth/register<br/>{ password_hash: hash }
    
    Note over Server: Server-side bcrypt hashing
    Server->>Server: stored_hash = bcrypt(hash)
    Server->>DB: Store user with stored_hash
    
    DB-->>Server: User created
    Server-->>Client: User info (no password)
    
```

#### Step 1: Client-Side Hashing (PBKDF2)
```python
# Client does this BEFORE sending to server
import hashlib
password = "user_password"
salt = "random_salt_from_server"
client_hash = hashlib.pbkdf2_hex(password.encode(), salt.encode(), 100000, 64)
# Result: "a1b2c3d4e5f6..." (64 character hash)
```

**Why PBKDF2?**
- **Slow by design**: Takes significant time to compute, making brute force attacks impractical
- **Salt-based**: Each password gets a unique random salt, preventing rainbow table attacks
- **Configurable iterations**: 100,000 iterations make it very expensive to crack

#### Step 2: Server-Side Hashing (bcrypt)
```python
# Server does this when storing the password
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"])
stored_hash = pwd_context.hash(client_hash)
# Result: "$2b$12$xyz..." (bcrypt hash of the client hash)
```

**Why bcrypt?**
- **Adaptive**: Can increase difficulty over time as computers get faster
- **Salt included**: Automatically generates and includes salt in the hash
- **Proven secure**: Battle-tested algorithm used by major companies

#### Why Double Hashing?
1. **Defense in depth**: Two layers of protection
2. **Network security**: No plain text passwords on the network
3. **Database security**: Even if database is compromised, passwords are double-protected
4. **Future-proof**: Can upgrade either layer independently

### 🎫 JWT Tokens Explained

**JWT (JSON Web Token)** is like a digital passport that contains user information.

#### Structure of a JWT:

```mermaid
graph LR
    JWT["JWT Token"] --> HEADER["Header<br/>Algorithm & Type"]
    JWT --> PAYLOAD["Payload<br/>User Data & Claims"]
    JWT --> SIGNATURE["Signature<br/>Verification Hash"]
    
    HEADER --> H_DATA["{ alg: 'HS256', typ: 'JWT' }"]
    PAYLOAD --> P_DATA["{ sub: 'user@example.com', exp: 1634567890 }"]
    SIGNATURE --> S_DATA["HMACSHA256(base64(header) + '.' + base64(payload), secret)"]
    
    style HEADER fill:#e3f2fd
    style PAYLOAD fill:#f3e5f5
    style SIGNATURE fill:#e8f5e8
```

- **Header**: Specifies the algorithm used (HS256)
- **Payload**: Contains user information (email, expiration time)
- **Signature**: Proves the token hasn't been tampered with

#### Why JWT?
- **Stateless**: Server doesn't need to store session information
- **Self-contained**: All needed information is in the token
- **Secure**: Cryptographically signed to prevent tampering
- **Standard**: Widely supported across different technologies

## Libraries and Technologies

### 🐍 Core Python Libraries

#### FastAPI
```python
from fastapi import FastAPI, Depends, HTTPException
```
**What it does**: Modern, fast web framework for building APIs
**Why we use it**:
- ✅ Automatic API documentation (Swagger UI)
- ✅ Built-in request validation
- ✅ Excellent performance
- ✅ Type hints support
- ✅ Dependency injection system

#### SQLAlchemy
```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
```
**What it does**: Object-Relational Mapping (ORM) library
**Why we use it**:
- ✅ Write database queries using Python objects instead of SQL
- ✅ Database-agnostic (works with PostgreSQL, MySQL, SQLite, etc.)
- ✅ Automatic relationship handling
- ✅ Migration support

#### Pydantic
```python
from pydantic import BaseModel, EmailStr
```
**What it does**: Data validation and parsing
**Why we use it**:
- ✅ Automatic request/response validation
- ✅ Type conversion and error handling
- ✅ Clear error messages for invalid data
- ✅ JSON serialization/deserialization

### 🔒 Security Libraries

#### Passlib
```python
from passlib.context import CryptContext
```
**What it does**: Password hashing library
**Why we use it**:
- ✅ Supports multiple hashing algorithms (bcrypt, scrypt, argon2)
- ✅ Handles salt generation automatically
- ✅ Easy to upgrade algorithms over time

#### Python-JOSE
```python
from jose import jwt, JWTError
```
**What it does**: JSON Web Token implementation
**Why we use it**:
- ✅ Create and verify JWT tokens
- ✅ Support for different algorithms
- ✅ Token expiration handling

### 🗄️ Database Libraries

#### psycopg2-binary
```python
# Used internally by SQLAlchemy
```
**What it does**: PostgreSQL adapter for Python
**Why we use it**:
- ✅ Fast C implementation
- ✅ Production-ready
- ✅ Full PostgreSQL feature support

#### Redis
```python
import redis
```
**What it does**: In-memory data structure store
**Why we use it**:
- ✅ Ultra-fast caching
- ✅ Session storage
- ✅ Rate limiting support

## Database Design

### User Table Schema

```mermaid
erDiagram
    users {
        SERIAL id PK "Auto-incrementing primary key"
        VARCHAR email UK "User's email (unique)"
        VARCHAR username UK "Display name (unique)"
        VARCHAR hashed_password "bcrypt hash of PBKDF2 hash"
        BOOLEAN is_active "Account status flag"
        BOOLEAN is_verified "Email verification status"
        TIMESTAMP created_at "Account creation time"
        TIMESTAMP updated_at "Last modification time"
    }
```

**SQL Definition:**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,              -- Unique user identifier
    email VARCHAR UNIQUE NOT NULL,      -- User's email (must be unique)
    username VARCHAR UNIQUE NOT NULL,   -- User's display name (must be unique)
    hashed_password VARCHAR NOT NULL,   -- bcrypt hash of client's PBKDF2 hash
    is_active BOOLEAN DEFAULT TRUE,     -- Account status flag
    is_verified BOOLEAN DEFAULT FALSE,  -- Email verification status
    created_at TIMESTAMP DEFAULT NOW(), -- Account creation time
    updated_at TIMESTAMP                -- Last modification time
);
```

### Why This Design?

1. **id**: Auto-incrementing primary key for efficient database operations
2. **email**: Unique identifier for login (with email validation)
3. **username**: Human-readable display name
4. **hashed_password**: Securely stored password hash (never plain text)
5. **is_active**: Allows disabling accounts without deletion
6. **is_verified**: Email verification workflow support
7. **timestamps**: Audit trail for account management

## API Endpoints Tutorial

### 1. Get Salt for Password Hashing

**Endpoint**: `GET /auth/salt`

**Purpose**: Get a cryptographic salt for client-side password hashing

```bash
curl -X GET "http://localhost:8001/auth/salt"
```

**Response**:
```json
{
  "salt": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456"
}
```

**What happens**:
1. Server generates a random 64-character salt
2. Client uses this salt to hash their password with PBKDF2
3. Client sends the hashed password (not plain text) to server

### 2. Register New User

**Endpoint**: `POST /auth/register`

**Purpose**: Create a new user account

```bash
# First, hash the password client-side:
# password_hash = pbkdf2_hex("my_password", salt, 100000, 64)

curl -X POST "http://localhost:8001/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "john_doe",
    "password_hash": "client_hashed_password_here"
  }'
```

**Response**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "john_doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2023-01-01T12:00:00"
}
```

**What happens**:
1. Server validates email format and uniqueness
2. Server checks username uniqueness
3. Server applies bcrypt to the client's password hash
4. User account is created in database
5. User information (without password) is returned

### 3. User Login

**Endpoint**: `POST /auth/login`

**Purpose**: Authenticate user and get access token

```bash
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password_hash": "client_hashed_password_here"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**What happens**:
1. Server finds user by email
2. Server verifies client password hash against stored bcrypt hash
3. If valid, server creates JWT token with user's email and expiration
4. Token is returned to client

### 4. Verify Token

**Endpoint**: `GET /auth/verify`

**Purpose**: Validate a JWT token (used by other services)

```bash
curl -X GET "http://localhost:8001/auth/verify" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**:
```json
{
  "email": "user@example.com",
  "valid": true
}
```

### 5. Get Current User

**Endpoint**: `GET /auth/me`

**Purpose**: Get detailed information about authenticated user

```bash
curl -X GET "http://localhost:8001/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "john_doe",
  "is_active": true,
  "is_verified": false,
  "created_at": "2023-01-01T12:00:00"
}
```

## Setting Up Development Environment

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Step-by-Step Setup

#### 1. Install Dependencies
```bash
cd src/auth_service
pip install -r requirements.txt
```

#### 2. Set Up Environment Variables
```bash
cp .env.example .env
# Edit .env file with your database credentials
```

#### 3. Start Database Services
```bash
# Using Docker
docker-compose up -d auth-postgres auth-redis

# Or install locally
# PostgreSQL on port 5433
# Redis on port 6380
```

#### 4. Run the Service
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

#### 5. Test the API
Visit: http://localhost:8001/docs

This opens the **Swagger UI** where you can:
- See all available endpoints
- Test API calls directly in the browser
- View request/response schemas
- Understand parameter requirements

## Security Best Practices

### ✅ What We Do Right

1. **No Plain Text Passwords**: Ever. Anywhere.
2. **Double Hashing**: Client-side + server-side protection
3. **Unique Salts**: Each password gets its own random salt
4. **JWT Expiration**: Tokens expire after 30 minutes by default
5. **Input Validation**: All requests are validated before processing
6. **Database Isolation**: Auth service has its own dedicated database
7. **Environment Variables**: Sensitive config stored in environment variables

### ⚠️ Production Considerations

1. **Change JWT Secret**: Update `JWT_SECRET_KEY` to a strong random value
2. **Use HTTPS**: Always encrypt traffic in production
3. **Rate Limiting**: Implement request rate limiting
4. **Password Policies**: Add minimum password requirements
5. **Account Lockout**: Lock accounts after failed login attempts
6. **Email Verification**: Verify user email addresses
7. **Audit Logging**: Log all authentication events

## Testing the Service

### Manual Testing with curl

#### 1. Get a salt
```bash
curl -X GET "http://localhost:8001/auth/salt"
```

#### 2. Hash password client-side (Python example)
```python
import hashlib
password = "test123"
salt = "salt_from_step_1"
password_hash = hashlib.pbkdf2_hex(password.encode(), salt.encode(), 100000, 64)
print(password_hash)
```

#### 3. Register user
```bash
curl -X POST "http://localhost:8001/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password_hash": "YOUR_HASHED_PASSWORD"
  }'
```

#### 4. Login
```bash
curl -X POST "http://localhost:8001/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password_hash": "YOUR_HASHED_PASSWORD"
  }'
```

### Testing with Python

```python
import hashlib
import requests

# 1. Get salt
response = requests.get("http://localhost:8001/auth/salt")
salt = response.json()["salt"]

# 2. Hash password
password = "test123"
password_hash = hashlib.pbkdf2_hex(password.encode(), salt.encode(), 100000, 64)

# 3. Register
register_data = {
    "email": "test@example.com",
    "username": "testuser",
    "password_hash": password_hash
}
response = requests.post("http://localhost:8001/auth/register", json=register_data)
print("Register:", response.json())

# 4. Login
login_data = {
    "email": "test@example.com",
    "password_hash": password_hash
}
response = requests.post("http://localhost:8001/auth/login", json=login_data)
token = response.json()["access_token"]
print("Token:", token)

# 5. Use token
headers = {"Authorization": f"Bearer {token}"}
response = requests.get("http://localhost:8001/auth/me", headers=headers)
print("User info:", response.json())
```

## Common Issues and Solutions

### Issue: "Import could not be resolved"
**Problem**: IDE shows import warnings
**Solution**: Install dependencies in your Python environment:
```bash
pip install -r requirements.txt
```

### Issue: Database connection error
**Problem**: Can't connect to PostgreSQL
**Solutions**:
1. Check if PostgreSQL is running: `docker-compose ps`
2. Verify database URL in `.env` file
3. Ensure database exists: `auth_db`
4. Check port conflicts (default: 5433)

### Issue: Redis connection error
**Problem**: Can't connect to Redis
**Solutions**:
1. Check if Redis is running: `docker-compose ps`
2. Verify Redis URL in `.env` file
3. Check port conflicts (default: 6380)

### Issue: JWT token errors
**Problem**: Token validation fails
**Solutions**:
1. Check if `JWT_SECRET_KEY` is set in environment
2. Verify token hasn't expired (default: 30 minutes)
3. Ensure token format is correct: `Bearer <token>`

### Issue: Password validation fails
**Problem**: Login fails with correct password
**Solutions**:
1. Verify password is hashed client-side with correct salt
2. Check PBKDF2 parameters: 100,000 iterations, 64-byte output
3. Ensure same salt is used for registration and login

## Understanding the Code Flow

### Registration Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth Service
    participant D as Database
    
    C->>A: GET /auth/salt
    A-->>C: { salt: "random64chars" }
    
    Note over C: hash = pbkdf2(password, salt, 100000)
    
    C->>A: POST /auth/register<br/>{ email, username, password_hash }
    
    A->>A: Validate email/username uniqueness
    A->>A: bcrypt_hash = bcrypt(password_hash)
    A->>D: INSERT user with bcrypt_hash
    D-->>A: User created successfully
    A-->>C: { id, email, username, is_active, created_at }
    
```

### Login Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth Service
    participant D as Database
    
    Note over C: hash = pbkdf2(password, salt, 100000)
    
    C->>A: POST /auth/login<br/>{ email, password_hash }
    
    A->>D: SELECT user WHERE email = ?
    D-->>A: User record with bcrypt_hash
    
    A->>A: verify(password_hash, bcrypt_hash)
    
    alt Authentication Success
        A->>A: jwt_token = create_jwt(email, expiration)
        A-->>C: { access_token, token_type: "bearer" }
    else Authentication Failed
        A-->>C: 401 Unauthorized
    end
    
```

### Token Verification Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth Service
    participant G as API Gateway
    
    C->>G: Request with Authorization: Bearer <token>
    G->>A: GET /auth/verify<br/>Authorization: Bearer <token>
    
    A->>A: Decode JWT token
    A->>A: Verify signature & expiration
    
    alt Token Valid
        A-->>G: { email: "user@example.com", valid: true }
        G-->>C: Proceed with request
    else Token Invalid
        A-->>G: 401 Unauthorized
        G-->>C: 401 Unauthorized
    end
    
```

This authentication service provides a solid foundation for secure user management in a microservices architecture. The double hashing approach ensures maximum password security, while JWT tokens provide stateless authentication suitable for distributed systems.

## Next Steps

1. **Add Rate Limiting**: Prevent brute force attacks
2. **Email Verification**: Implement email confirmation workflow
3. **Password Reset**: Add forgot password functionality
4. **OAuth Integration**: Support Google/GitHub login
5. **Audit Logging**: Track all authentication events
6. **Multi-Factor Authentication**: Add 2FA support

Happy coding! 🚀