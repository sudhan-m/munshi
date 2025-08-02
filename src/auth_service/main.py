"""
Authentication Service - Main FastAPI Application

A secure authentication microservice that provides user registration, login,
and JWT token management. Implements client-side password hashing to ensure
no plaintext passwords are ever transmitted over the network.

This service maintains its own dedicated database and operates independently
from other microservices in the system.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
from .models import UserCreate, UserLogin, UserResponse, Token, User
from .database import get_db, create_tables
from .auth import (
    authenticate_user, 
    create_user, 
    create_access_token, 
    verify_token,
    get_user_by_email,
    get_user_by_username,
    get_salt,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Authentication Service",
    description="Secure authentication microservice with client-side password hashing",
    version="1.0.0"
)
security = HTTPBearer()

# Initialize database tables on startup
create_tables()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


@app.get("/auth/salt")
async def get_password_salt():
    """
    Get a cryptographic salt for client-side password hashing.
    
    Clients must hash their passwords with PBKDF2 using this salt before
    sending registration or login requests. This ensures no plaintext
    passwords are ever transmitted.
    
    Returns:
        dict: Contains a 64-character hexadecimal salt string
        
    Example:
        GET /auth/salt
        Response: {"salt": "a1b2c3d4..."}
    """
    return {"salt": get_salt()}


@app.post("/auth/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user account with pre-hashed password.
    
    Expects a client-side PBKDF2 hashed password. The server will apply
    additional bcrypt hashing before storage for maximum security.
    
    Args:
        user: User registration data with pre-hashed password
        db: Database session dependency
        
    Returns:
        UserResponse: Created user information (without password)
        
    Raises:
        HTTPException: 400 if email or username already exists
    """
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
    
    db_user = create_user(db, user.email, user.username, user.password_hash)
    return UserResponse.from_orm(db_user)


@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token.
    
    Expects a client-side PBKDF2 hashed password for authentication.
    Returns a JWT token that can be used for accessing protected endpoints.
    
    Args:
        user_credentials: Login credentials with pre-hashed password
        db: Database session dependency
        
    Returns:
        Token: JWT access token and token type
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    user = authenticate_user(db, user_credentials.email, user_credentials.password_hash)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


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


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns:
        dict: Service health status
    """
    return {"status": "healthy", "service": "auth-service"}


if __name__ == "__main__":
    """
    Run the authentication service directly.
    
    For development only. In production, use a proper WSGI server
    like uvicorn with appropriate configuration.
    """
    import uvicorn
    port = int(os.getenv("AUTH_SERVICE_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)