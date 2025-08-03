"""
Shared JWT token handling utilities.

Provides common JWT creation, validation, and management across services.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


class JWTHandler:
    """
    Centralized JWT token management for microservices.
    """
    
    def __init__(self, secret_key: str, algorithm: str = "HS256", 
                 expire_minutes: int = 30):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expire_minutes = expire_minutes
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def create_access_token(self, data: Dict[str, Any], 
                          expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token with user data.
        
        Args:
            data: User data to encode in token
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.expire_minutes)
        
        to_encode.update({"exp": expire})
        
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.info(f"JWT token created for user: {data.get('sub', 'unknown')}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create JWT token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            email: str = payload.get("sub")
            
            if email is None:
                logger.warning("Token missing subject (sub) claim")
                return None
                
            return payload
            
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Bcrypt hashed password
        """
        try:
            hashed = self.pwd_context.hash(password)
            logger.info("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Bcrypt hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            result = self.pwd_context.verify(plain_password, hashed_password)
            logger.info(f"Password verification: {'success' if result else 'failed'}")
            return result
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def extract_token_from_header(self, authorization: str) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        
        Args:
            authorization: Authorization header value
            
        Returns:
            JWT token or None if invalid format
        """
        if not authorization:
            return None
            
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                logger.warning(f"Invalid authorization scheme: {scheme}")
                return None
            return token
        except ValueError:
            logger.warning("Invalid authorization header format")
            return None
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Get the expiry time of a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token expiry datetime or None if invalid
        """
        payload = self.verify_token(token)
        if not payload:
            return None
            
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            return None
            
        return datetime.fromtimestamp(exp_timestamp)