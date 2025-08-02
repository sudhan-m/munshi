"""
Data models for the authentication service.

This module defines the database models and Pydantic schemas used for user
authentication, including user entities, request/response models, and token
management structures.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

Base = declarative_base()


class User(Base):
    """
    SQLAlchemy model for user entities in the authentication database.
    
    Stores user authentication data including hashed passwords and account status.
    Uses separate database from other services for security isolation.
    
    Attributes:
        id: Primary key identifier
        email: Unique email address for authentication
        username: Unique username for display
        hashed_password: Double-hashed password (client PBKDF2 + server bcrypt)
        is_active: Account status flag
        is_verified: Email verification status
        created_at: Account creation timestamp
        updated_at: Last modification timestamp
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserCreate(BaseModel):
    """
    Pydantic model for user registration requests.
    
    Expects a pre-hashed password from the client to ensure no plaintext
    passwords are transmitted over the network.
    
    Attributes:
        email: Valid email address for the new account
        username: Unique username for the account
        password_hash: Client-side PBKDF2 hashed password
    """
    email: EmailStr
    username: str
    password_hash: str


class UserLogin(BaseModel):
    """
    Pydantic model for user login requests.
    
    Expects a pre-hashed password from the client for secure authentication.
    
    Attributes:
        email: Email address for authentication
        password_hash: Client-side PBKDF2 hashed password
    """
    email: EmailStr
    password_hash: str


class UserResponse(BaseModel):
    """
    Pydantic model for user data responses.
    
    Returns safe user information without sensitive data like passwords.
    
    Attributes:
        id: User's unique identifier
        email: User's email address
        username: User's display name
        is_active: Account status
        is_verified: Email verification status
        created_at: Account creation date
    """
    id: int
    email: str
    username: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """
    Pydantic model for JWT token responses.
    
    Returned after successful authentication.
    
    Attributes:
        access_token: JWT access token string
        token_type: Token type (always "bearer")
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Pydantic model for JWT token payload data.
    
    Used internally for token validation and user identification.
    
    Attributes:
        email: Email address extracted from token payload
    """
    email: Optional[str] = None