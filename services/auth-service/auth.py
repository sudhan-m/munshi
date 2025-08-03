"""
Authentication utilities and password management for the auth service.

This module provides secure authentication functions including server-side bcrypt
password hashing with strong validation, JWT token management, and user account
operations. Implements secure password handling and memory safety principles.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .models import User, TokenData
from .database import get_db
from .cache import get_cache
import os
import logging
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your_secret_key_here")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


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
    Verify and decode a JWT token with blacklist checking.
    
    Args:
        token: JWT token string to verify
        credentials_exception: Exception to raise if verification fails
        
    Returns:
        TokenData: Decoded token data with user email
        
    Raises:
        credentials_exception: If token is invalid, expired, or blacklisted
    """
    cache = get_cache()
    
    # Check if token is blacklisted
    if cache.is_token_blacklisted(token):
        logger.warning(f"Attempted use of blacklisted token")
        raise credentials_exception
    
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
    Authenticate a user using email and plaintext password with rate limiting.
    
    Verifies the plaintext password against the stored bcrypt hash.
    Implements failed attempt tracking and account lockout protection.
    
    Args:
        db: Database session
        email: User's email address
        password: Plaintext password from client
        
    Returns:
        Optional[User]: User object if authentication succeeds, None otherwise
    """
    cache = get_cache()
    
    # Check if account is locked
    if cache.is_account_locked(email):
        logger.warning(f"Authentication attempt on locked account: {email}")
        return None
    
    user = get_user_by_email(db, email)
    if not user:
        # Increment failed attempts even for non-existent users to prevent enumeration
        cache.increment_failed_attempts(email, ttl=900)  # 15 minutes
        return None
    
    if not verify_password(password, user.hashed_password):
        # Increment failed attempts
        failed_count = cache.increment_failed_attempts(email, ttl=900)
        logger.warning(f"Failed authentication attempt for {email}. Count: {failed_count}")
        
        # Lock account if too many failures
        if failed_count >= 5:  # Max attempts from config
            cache.lock_account(email, ttl=900)  # 15 minutes lockout
            logger.warning(f"Account locked due to failed attempts: {email}")
        
        return None
    
    # Successful authentication - clear failed attempts
    cache.clear_failed_attempts(email)
    
    # Cache user session data
    session_data = {
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
        "last_login": datetime.utcnow().isoformat()
    }
    cache.cache_user_session(user.id, session_data, ttl=3600)  # 1 hour
    
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


def blacklist_token(token: str, expires_at: Optional[datetime] = None) -> bool:
    """
    Add a JWT token to the blacklist.
    
    Args:
        token: JWT token to blacklist
        expires_at: Token expiration time (for TTL calculation)
        
    Returns:
        bool: True if blacklisted successfully
    """
    cache = get_cache()
    
    # Calculate TTL based on token expiration
    ttl = None
    if expires_at:
        now = datetime.utcnow()
        if expires_at > now:
            ttl = int((expires_at - now).total_seconds())
    
    success = cache.blacklist_token(token, ttl)
    if success:
        logger.info("Token blacklisted successfully")
    else:
        logger.error("Failed to blacklist token")
    
    return success


def logout_user(user_id: int, token: str) -> bool:
    """
    Logout a user by blacklisting their token and clearing session.
    
    Args:
        user_id: User ID
        token: JWT token to blacklist
        
    Returns:
        bool: True if logout successful
    """
    cache = get_cache()
    
    # Extract token expiration for TTL
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        exp_timestamp = payload.get("exp")
        expires_at = datetime.fromtimestamp(exp_timestamp) if exp_timestamp else None
    except Exception:
        expires_at = None
    
    # Blacklist the token
    token_blacklisted = blacklist_token(token, expires_at)
    
    # Clear user session
    session_cleared = cache.invalidate_user_session(user_id)
    
    success = token_blacklisted and session_cleared
    if success:
        logger.info(f"User {user_id} logged out successfully")
    else:
        logger.warning(f"Partial logout for user {user_id}: token={token_blacklisted}, session={session_cleared}")
    
    return success


def get_cached_user_session(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get cached user session data.
    
    Args:
        user_id: User ID
        
    Returns:
        Dict containing session data or None if not found
    """
    cache = get_cache()
    return cache.get_user_session(user_id)


def refresh_user_session(user_id: int, user_data: Dict[str, Any]) -> bool:
    """
    Refresh/update cached user session data.
    
    Args:
        user_id: User ID
        user_data: Updated user data to cache
        
    Returns:
        bool: True if session refreshed successfully
    """
    cache = get_cache()
    session_data = {
        **user_data,
        "last_activity": datetime.utcnow().isoformat()
    }
    return cache.cache_user_session(user_id, session_data, ttl=3600)


def is_user_account_locked(email: str) -> bool:
    """
    Check if a user account is currently locked.
    
    Args:
        email: User email address
        
    Returns:
        bool: True if account is locked
    """
    cache = get_cache()
    return cache.is_account_locked(email)


def get_failed_login_attempts(email: str) -> int:
    """
    Get the number of failed login attempts for a user.
    
    Args:
        email: User email address
        
    Returns:
        int: Number of failed attempts
    """
    cache = get_cache()
    return cache.get_failed_attempts(email)


def unlock_user_account(email: str) -> bool:
    """
    Manually unlock a user account (admin function).
    
    Args:
        email: User email address
        
    Returns:
        bool: True if unlocked successfully
    """
    cache = get_cache()
    attempts_cleared = cache.clear_failed_attempts(email)
    account_unlocked = cache.unlock_account(email)
    
    success = attempts_cleared and account_unlocked
    if success:
        logger.info(f"Account manually unlocked: {email}")
    
    return success


