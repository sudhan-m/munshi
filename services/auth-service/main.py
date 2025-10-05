"""
Authentication Service - Main FastAPI Application

A secure authentication microservice that provides user registration, login,
and JWT token management. Implements server-side bcrypt password hashing
with strong validation and secure memory handling.

This service maintains its own dedicated database and operates independently
from other microservices in the system.
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
from models import UserCreate, UserLogin, UserResponse, Token, User
from database import get_db, create_tables
from auth import (
    authenticate_user, 
    create_user, 
    create_access_token, 
    verify_token,
    get_user_by_email,
    get_user_by_username,
    blacklist_token,
    logout_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from cache import get_cache, close_cache
from config import get_auth_settings
import os
import re
import logging
from dotenv import load_dotenv
import httpx
import asyncio

load_dotenv()
settings = get_auth_settings()

app = FastAPI(
    title="Authentication Service",
    description="Secure authentication microservice with server-side bcrypt password hashing and mTLS support",
    version=settings.service_version,
    debug=settings.debug
)
security = HTTPBearer()

# Note: TrustedHostMiddleware is optional when using Linkerd ServerAuthorization
# Linkerd handles service-to-service authorization at the mesh level
# Only add for additional host-based restrictions if needed
if settings.trusted_hosts_enabled:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.trusted_hosts
    )

@app.middleware("http")
async def linkerd_identity_middleware(request: Request, call_next):
    """Extract Linkerd service identity for observability and logging"""
    # Linkerd automatically handles authorization via ServerAuthorization policies
    # This middleware just extracts identity information for logging/observability
    
    # Extract Linkerd identity headers (set by Linkerd proxy)
    client_identity = request.headers.get("l5d-client-id", "unknown")
    dst_service = request.headers.get("l5d-dst-service", "unknown")
    
    # Set request state for logging and observability
    request.state.client_identity = client_identity
    request.state.destination_service = dst_service
    request.state.service_mesh = "linkerd"
    
    # Log service-to-service communication for audit
    if client_identity != "unknown":
        logging.info(f"Service-to-service call: {client_identity} -> auth-service")
    
    response = await call_next(request)
    
    # Add observability headers
    response.headers["X-Service-Identity"] = client_identity
    response.headers["X-Destination-Service"] = dst_service
    response.headers["X-Auth-Service-Version"] = settings.service_version
    
    return response

# Initialize database tables and Redis cache on startup
create_tables()

@app.on_event("startup")
async def startup_event():
    """Initialize Redis cache connection on startup."""
    cache = get_cache()
    if cache.is_connected():
        logging.info("Auth service connected to Redis cache")
    else:
        logging.warning("Auth service failed to connect to Redis cache")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up Redis cache connection on shutdown."""
    close_cache()
    logging.info("Auth service Redis cache connection closed")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)



@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account with plaintext password.
    
    Validates input, checks for existing users, hashes password with bcrypt,
    and stores securely in database.
    
    Args:
        user: User registration data with plaintext password
        db: Database session dependency
        
    Returns:
        UserResponse: Created user information (without password)
        
    Raises:
        HTTPException: 400 if validation fails or user already exists
    """
    if len(user.password) < settings.password_min_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must be at least {settings.password_min_length} characters long"
        )
    
    if settings.require_password_uppercase and not re.search(r"[A-Z]", user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    
    if settings.require_password_lowercase and not re.search(r"[a-z]", user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    
    if settings.require_password_numbers and not re.search(r"\d", user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number"
        )
    
    if len(user.username) < settings.min_username_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username must be at least {settings.min_username_length} characters long"
        )
    
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_username = get_user_by_username(db, user.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    db_user = create_user(db, user.email, user.username, user.password)
    user.password = None
    return UserResponse.from_orm(db_user)


async def _prewarm_gpu():
    """
    Pre-warm GPU node by triggering ASR pod scheduling.
    This ensures GPU is ready when user needs pronunciation practice.
    Fire-and-forget - don't wait for response.
    """
    try:
        asr_url = os.getenv("ASR_SERVICE_URL", "http://asr-service:8004")
        async with httpx.AsyncClient(timeout=1.0) as client:
            await client.get(f"{asr_url}/health")
    except:
        pass  # Ignore errors - this is just a trigger


@app.post("/auth/login")
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token with user data.

    Accepts plaintext password, verifies against stored bcrypt hash,
    and returns JWT token along with user information for accessing protected endpoints.

    Args:
        user_credentials: Login credentials with plaintext password
        db: Database session dependency

    Returns:
        dict: JWT access token, token type, and user data

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    user_credentials.password = None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Pre-warm GPU node in background (fire-and-forget)
    asyncio.create_task(_prewarm_gpu())

    # Return user data along with token
    user_data = UserResponse.from_orm(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data.dict()
    }


@app.get("/auth/verify")
async def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify a JWT token and return basic validation info.
    
    Used by other services (like the API Gateway) to validate tokens
    without needing to know JWT secrets or validation logic.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        
    Returns:
        dict: Token validation result with user email
        
    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    token_data = verify_token(credentials.credentials, credentials_exception)
    return {"email": token_data.email, "valid": True}


@app.get("/auth/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """
    Get detailed information about the currently authenticated user.
    
    Returns full user profile information for the user associated with
    the provided JWT token.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session dependency
        
    Returns:
        UserResponse: Complete user profile information
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token_data = verify_token(credentials.credentials, credentials_exception)
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise credentials_exception
    return UserResponse.from_orm(user)


@app.post("/auth/logout")
async def logout(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """
    Logout user by blacklisting their JWT token.
    
    Adds the provided JWT token to the blacklist and clears user session cache.
    This prevents the token from being used for future authentication.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session dependency
        
    Returns:
        dict: Logout confirmation message
        
    Raises:
        HTTPException: 401 if token is invalid
    """
    # Verify token is valid before blacklisting
    token_data = verify_token(credentials.credentials, credentials_exception)
    user = get_user_by_email(db, token_data.email)
    if user is None:
        raise credentials_exception
    
    # Logout user (blacklist token and clear session)
    success = logout_user(user.id, credentials.credentials)
    
    if success:
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Service health status
    """
    return {"status": "healthy", "service": settings.service_name, "version": settings.service_version}


if __name__ == "__main__":
    """
    Run the authentication service directly.
    
    For development only. In production, use a proper WSGI server
    like uvicorn with appropriate configuration.
    """
    import uvicorn
    uvicorn.run(app, host=settings.auth_service_host, port=settings.auth_service_port)