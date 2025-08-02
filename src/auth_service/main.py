"""
Authentication Service - Main FastAPI Application

A secure authentication microservice that provides user registration, login,
and JWT token management. Implements server-side bcrypt password hashing
with strong validation and secure memory handling.

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
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import os
import re
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Authentication Service",
    description="Secure authentication microservice with server-side bcrypt password hashing",
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
    if len(user.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    if not re.search(r"[A-Z]", user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter"
        )
    
    if not re.search(r"[a-z]", user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter"
        )
    
    if not re.search(r"\d", user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one number"
        )
    
    if len(user.username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be at least 3 characters long"
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


@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token.
    
    Accepts plaintext password, verifies against stored bcrypt hash,
    and returns JWT token for accessing protected endpoints.
    
    Args:
        user_credentials: Login credentials with plaintext password
        db: Database session dependency
        
    Returns:
        Token: JWT access token and token type
        
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