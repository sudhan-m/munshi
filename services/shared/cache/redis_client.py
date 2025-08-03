"""
Shared Redis client for microservices.

Provides a common Redis interface with connection pooling, error handling,
and common operations used across services.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import redis
from redis.connection import ConnectionPool
from redis.exceptions import RedisError, ConnectionError

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Shared Redis client with common operations for microservices.
    """
    
    def __init__(self, redis_url: str, db: int = 0, max_connections: int = 20):
        """
        Initialize Redis client with connection pooling.
        
        Args:
            redis_url: Redis connection URL
            db: Redis database number
            max_connections: Maximum connections in pool
        """
        self.redis_url = redis_url
        self.db = db
        
        try:
            self.pool = ConnectionPool.from_url(
                redis_url,
                db=db,
                max_connections=max_connections,
                socket_timeout=5,
                socket_connect_timeout=5,
                health_check_interval=30
            )
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis client initialized successfully (db={db})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False
    
    # Basic Operations
    
    def set(self, key: str, value: Union[str, Dict, List], ttl: Optional[int] = None) -> bool:
        """
        Set a value in Redis with optional TTL.
        
        Args:
            key: Redis key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            logger.warning("Redis unavailable - set operation skipped")
            return False
        
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                result = self.client.setex(key, ttl, value)
            else:
                result = self.client.set(key, value)
            
            logger.debug(f"Redis SET: {key} (TTL: {ttl})")
            return bool(result)
            
        except RedisError as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def get(self, key: str, as_json: bool = False) -> Optional[Union[str, Dict, List]]:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            as_json: Parse value as JSON
            
        Returns:
            Value or None if not found
        """
        if not self.is_available():
            return None
        
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            value = value.decode('utf-8')
            
            if as_json:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON for key: {key}")
                    return None
            
            logger.debug(f"Redis GET: {key}")
            return value
            
        except RedisError as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def delete(self, *keys: str) -> int:
        """
        Delete one or more keys from Redis.
        
        Args:
            keys: Keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0
        
        try:
            result = self.client.delete(*keys)
            logger.debug(f"Redis DELETE: {keys}")
            return result
        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        
        Args:
            key: Redis key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self.client.exists(key)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL for an existing key.
        
        Args:
            key: Redis key
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            result = self.client.expire(key, ttl)
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False
    
    # Token Management
    
    def blacklist_token(self, token: str, ttl: int) -> bool:
        """
        Add a JWT token to blacklist.
        
        Args:
            token: JWT token to blacklist
            ttl: Time until token naturally expires
            
        Returns:
            True if successful, False otherwise
        """
        key = f"blacklist:token:{token}"
        return self.set(key, "blacklisted", ttl)
    
    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a JWT token is blacklisted.
        
        Args:
            token: JWT token to check
            
        Returns:
            True if blacklisted, False otherwise
        """
        key = f"blacklist:token:{token}"
        return self.exists(key)
    
    # Session Management
    
    def cache_user_session(self, user_id: Union[str, int], session_data: Dict, 
                          ttl: int = 3600) -> bool:
        """
        Cache user session data.
        
        Args:
            user_id: User identifier
            session_data: Session data to cache
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        key = f"session:user:{user_id}"
        return self.set(key, session_data, ttl)
    
    def get_user_session(self, user_id: Union[str, int]) -> Optional[Dict]:
        """
        Get cached user session data.
        
        Args:
            user_id: User identifier
            
        Returns:
            Session data or None if not found
        """
        key = f"session:user:{user_id}"
        return self.get(key, as_json=True)
    
    def clear_user_session(self, user_id: Union[str, int]) -> bool:
        """
        Clear user session from cache.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        key = f"session:user:{user_id}"
        return bool(self.delete(key))
    
    # Rate Limiting (Sliding Window)
    
    def check_rate_limit(self, key: str, limit: int, window: int) -> Dict[str, Any]:
        """
        Check rate limit using sliding window algorithm.
        
        Args:
            key: Rate limit key (e.g., user ID, IP address)
            limit: Maximum requests allowed
            window: Time window in seconds
            
        Returns:
            Dict with allowed status and remaining count
        """
        if not self.is_available():
            return {"allowed": True, "remaining": limit, "reset_time": None}
        
        try:
            now = datetime.utcnow().timestamp()
            window_start = now - window
            
            # Use Redis sorted set for sliding window
            pipe = self.client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry
            pipe.expire(key, window + 1)
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the request we just added
            
            allowed = current_count <= limit
            remaining = max(0, limit - current_count)
            reset_time = now + window
            
            logger.debug(f"Rate limit check: {key} - {current_count}/{limit}")
            
            return {
                "allowed": allowed,
                "remaining": remaining,
                "reset_time": reset_time,
                "current_count": current_count
            }
            
        except RedisError as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail open - allow request if Redis is down
            return {"allowed": True, "remaining": limit, "reset_time": None}
    
    # Failed Login Tracking
    
    def track_failed_login(self, identifier: str, ttl: int = 900) -> int:
        """
        Track failed login attempt.
        
        Args:
            identifier: User identifier (email, IP, etc.)
            ttl: Time window in seconds (default: 15 minutes)
            
        Returns:
            Current count of failed attempts
        """
        key = f"failed_attempts:{identifier}"
        
        if not self.is_available():
            return 0
        
        try:
            current = self.client.incr(key)
            if current == 1:  # First attempt
                self.client.expire(key, ttl)
            
            logger.debug(f"Failed login tracked: {identifier} - {current} attempts")
            return current
            
        except RedisError as e:
            logger.error(f"Failed login tracking error: {e}")
            return 0
    
    def clear_failed_logins(self, identifier: str) -> bool:
        """
        Clear failed login attempts for identifier.
        
        Args:
            identifier: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        key = f"failed_attempts:{identifier}"
        return bool(self.delete(key))
    
    def get_failed_login_count(self, identifier: str) -> int:
        """
        Get current failed login count.
        
        Args:
            identifier: User identifier
            
        Returns:
            Number of failed attempts
        """
        key = f"failed_attempts:{identifier}"
        
        if not self.is_available():
            return 0
        
        try:
            count = self.client.get(key)
            return int(count) if count else 0
        except (RedisError, ValueError):
            return 0
    
    # Account Lockout
    
    def lock_account(self, identifier: str, ttl: int = 900) -> bool:
        """
        Lock an account temporarily.
        
        Args:
            identifier: User identifier
            ttl: Lock duration in seconds (default: 15 minutes)
            
        Returns:
            True if successful, False otherwise
        """
        key = f"account_locked:{identifier}"
        return self.set(key, "locked", ttl)
    
    def is_account_locked(self, identifier: str) -> bool:
        """
        Check if an account is locked.
        
        Args:
            identifier: User identifier
            
        Returns:
            True if locked, False otherwise
        """
        key = f"account_locked:{identifier}"
        return self.exists(key)
    
    def unlock_account(self, identifier: str) -> bool:
        """
        Unlock an account.
        
        Args:
            identifier: User identifier
            
        Returns:
            True if successful, False otherwise
        """
        key = f"account_locked:{identifier}"
        return bool(self.delete(key))
    
    # Circuit Breaker
    
    def set_circuit_breaker(self, service: str, state: str, ttl: int = 300) -> bool:
        """
        Set circuit breaker state for a service.
        
        Args:
            service: Service name
            state: Circuit breaker state (open, closed, half-open)
            ttl: State duration in seconds
            
        Returns:
            True if successful, False otherwise
        """
        key = f"circuit_breaker:{service}"
        return self.set(key, state, ttl)
    
    def get_circuit_breaker_state(self, service: str) -> str:
        """
        Get circuit breaker state for a service.
        
        Args:
            service: Service name
            
        Returns:
            Circuit breaker state or "closed" if not set
        """
        key = f"circuit_breaker:{service}"
        state = self.get(key)
        return state if state else "closed"