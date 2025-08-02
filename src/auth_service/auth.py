"""
Authentication utilities and password management for the auth service.

This module provides secure authentication functions including server-side bcrypt
password hashing with strong validation, JWT token management, and user account
operations. Implements secure password handling and memory safety principles.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .models import User, TokenData
from .database import get_db
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_secret_key_here")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify plaintext password against stored bcrypt hash.
    
    Args:
        password: Plaintext password from client
        stored_hash: bcrypt hash stored in database
        
    Returns:
        bool: True if password is valid, False otherwise
    """
    return pwd_context.verify(password, stored_hash)


def get_password_hash(password: str) -> str:
    """
    Hash plaintext password with bcrypt for secure storage.
    
    Uses bcrypt with salt rounds=12 for strong password hashing.
    
    Args:
        password: Plaintext password from client
        
    Returns:
        str: bcrypt hash suitable for database storage
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token with specified data and expiration.
    
    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
        
    Example:
        token = create_access_token({"sub": "user@example.com"})
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception) -> TokenData:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string to verify
        credentials_exception: Exception to raise if verification fails
        
    Returns:
        TokenData: Decoded token data with user email
        
    Raises:
        credentials_exception: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
        return token_data
    except JWTError:
        raise credentials_exception


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """
    Retrieve a user by their email address.
    
    Args:
        db: Database session
        email: Email address to search for
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Retrieve a user by their username.
    
    Args:
        db: Database session
        username: Username to search for
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticate a user using email and plaintext password.
    
    Verifies the plaintext password against the stored bcrypt hash.
    
    Args:
        db: Database session
        email: User's email address
        password: Plaintext password from client
        
    Returns:
        Optional[User]: User object if authentication succeeds, None otherwise
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, email: str, username: str, password: str) -> User:
    """
    Create a new user account with plaintext password.
    
    Takes the plaintext password and hashes it with bcrypt for storage.
    
    Args:
        db: Database session
        email: User's email address
        username: User's chosen username
        password: Plaintext password from client
        
    Returns:
        User: Newly created user object
        
    Raises:
        SQLAlchemyError: If database constraints are violated
    """
    hashed_password = get_password_hash(password)
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


