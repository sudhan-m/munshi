"""
Redis cache utilities for the authentication service.

This module provides Redis connection management and caching utilities
for token blacklisting, user sessions, and other auth-related data.
Implements connection pooling and error handling for reliable cache operations.
"""

import json
import logging
from typing import Optional, Any, Dict, List
from datetime import timedelta
import redis
from redis.connection import ConnectionPool
from .config import get_auth_settings

logger = logging.getLogger(__name__)


class AuthRedisCache:
    """
    Redis cache manager for authentication service.
    
    Provides methods for token blacklisting, user session management,
    and general caching operations with automatic connection handling
    and error recovery.
    """
    
    def __init__(self):
        """Initialize Redis connection with connection pooling."""
        self.settings = get_auth_settings()
        self.pool = None
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection with connection pooling."""
        try:
            self.pool = ConnectionPool.from_url(
                self.settings.auth_redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self.redis_client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis cache successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    def reconnect(self):
        """Attempt to reconnect to Redis."""
        if not self.is_connected():
            logger.info("Attempting to reconnect to Redis...")
            self._connect()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a key-value pair in Redis with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_connected():
            self.reconnect()
            if not self.is_connected():
                logger.warning("Redis not available, skipping cache set")
                return False
        
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            if ttl:
                return self.redis_client.setex(key, ttl, serialized_value)
            else:
                return self.redis_client.set(key, serialized_value)
        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/error
        """
        if not self.is_connected():
            self.reconnect()
            if not self.is_connected():
                return None
        
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # Try to deserialize as JSON, fallback to string
            try:
                return json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return value.decode('utf-8')
                
        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: True if deleted, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Cache key to check
            
        Returns:
            bool: True if exists, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check existence of key {key}: {e}")
            return False
    
    def blacklist_token(self, token: str, ttl: Optional[int] = None) -> bool:
        """
        Add a JWT token to the blacklist.
        
        Args:
            token: JWT token to blacklist
            ttl: Time to live in seconds (should match token expiry)
            
        Returns:
            bool: True if blacklisted successfully
        """
        key = f"blacklist:token:{token}"
        return self.set(key, "blacklisted", ttl)
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a JWT token is blacklisted.
        
        Args:
            token: JWT token to check
            
        Returns:
            bool: True if blacklisted, False otherwise
        """
        key = f"blacklist:token:{token}"
        return self.exists(key)
    
    def cache_user_session(self, user_id: int, session_data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Cache user session data.
        
        Args:
            user_id: User ID
            session_data: Session data to cache
            ttl: Time to live in seconds (default 1 hour)
            
        Returns:
            bool: True if cached successfully
        """
        key = f"session:user:{user_id}"
        return self.set(key, session_data, ttl)
    
    def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached user session data.
        
        Args:
            user_id: User ID
            
        Returns:
            Session data or None if not found
        """
        key = f"session:user:{user_id}"
        return self.get(key)
    
    def invalidate_user_session(self, user_id: int) -> bool:
        """
        Invalidate user session cache.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if invalidated successfully
        """
        key = f"session:user:{user_id}"
        return self.delete(key)
    
    def increment_failed_attempts(self, username: str, ttl: int = 900) -> int:
        """
        Increment failed login attempts counter.
        
        Args:
            username: Username
            ttl: Time to live in seconds (default 15 minutes)
            
        Returns:
            int: Current attempt count
        """
        key = f"failed_attempts:{username}"
        
        if not self.is_connected():
            return 0
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, ttl)
            results = pipe.execute()
            return results[0] if results else 0
        except Exception as e:
            logger.error(f"Failed to increment failed attempts for {username}: {e}")
            return 0
    
    def get_failed_attempts(self, username: str) -> int:
        """
        Get failed login attempts count.
        
        Args:
            username: Username
            
        Returns:
            int: Failed attempts count
        """
        key = f"failed_attempts:{username}"
        try:
            count = self.get(key)
            return int(count) if count else 0
        except (ValueError, TypeError):
            return 0
    
    def clear_failed_attempts(self, username: str) -> bool:
        """
        Clear failed login attempts counter.
        
        Args:
            username: Username
            
        Returns:
            bool: True if cleared successfully
        """
        key = f"failed_attempts:{username}"
        return self.delete(key)
    
    def lock_account(self, username: str, ttl: int = 900) -> bool:
        """
        Lock user account after failed attempts.
        
        Args:
            username: Username
            ttl: Lock duration in seconds (default 15 minutes)
            
        Returns:
            bool: True if locked successfully
        """
        key = f"account_locked:{username}"
        return self.set(key, "locked", ttl)
    
    def is_account_locked(self, username: str) -> bool:
        """
        Check if user account is locked.
        
        Args:
            username: Username
            
        Returns:
            bool: True if locked, False otherwise
        """
        key = f"account_locked:{username}"
        return self.exists(key)
    
    def unlock_account(self, username: str) -> bool:
        """
        Unlock user account.
        
        Args:
            username: Username
            
        Returns:
            bool: True if unlocked successfully
        """
        key = f"account_locked:{username}"
        return self.delete(key)
    
    def close(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


# Global cache instance
_cache_instance: Optional[AuthRedisCache] = None


def get_cache() -> AuthRedisCache:
    """
    Get the global Redis cache instance.
    
    Returns:
        AuthRedisCache: Global cache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AuthRedisCache()
    return _cache_instance


def close_cache():
    """Close the global Redis cache connection."""
    global _cache_instance
    if _cache_instance:
        _cache_instance.close()
        _cache_instance = None