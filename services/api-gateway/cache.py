"""
Redis cache utilities for the API Gateway service.

This module provides Redis connection management and caching utilities
for rate limiting, response caching, service discovery, and other
gateway-related operations. Implements connection pooling and error handling.
"""

import json
import logging
import hashlib
from typing import Optional, Any, Dict, List
from datetime import datetime, timedelta
import redis
from redis.connection import ConnectionPool
from .config import get_gateway_settings

logger = logging.getLogger(__name__)


class GatewayRedisCache:
    """
    Redis cache manager for API Gateway service.
    
    Provides methods for rate limiting, response caching, service registry
    caching, and general caching operations with automatic connection handling
    and error recovery.
    """
    
    def __init__(self):
        """Initialize Redis connection with connection pooling."""
        self.settings = get_gateway_settings()
        self.pool = None
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection with connection pooling."""
        try:
            self.pool = ConnectionPool.from_url(
                self.settings.gateway_redis_url,
                max_connections=50,  # Higher for gateway
                retry_on_timeout=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self.redis_client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            self.redis_client.ping()
            logger.info("Gateway connected to Redis cache successfully")
            
        except Exception as e:
            logger.error(f"Gateway failed to connect to Redis: {e}")
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
            logger.info("Gateway attempting to reconnect to Redis...")
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
    
    def increment(self, key: str, amount: int = 1, ttl: Optional[int] = None) -> int:
        """
        Increment a counter in Redis atomically.
        
        Args:
            key: Counter key
            amount: Amount to increment by
            ttl: Time to live in seconds
            
        Returns:
            int: New counter value
        """
        if not self.is_connected():
            return 0
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.incrby(key, amount)
            if ttl:
                pipe.expire(key, ttl)
            results = pipe.execute()
            return results[0] if results else 0
        except Exception as e:
            logger.error(f"Failed to increment counter {key}: {e}")
            return 0
    
    def get_counter(self, key: str) -> int:
        """
        Get counter value from Redis.
        
        Args:
            key: Counter key
            
        Returns:
            int: Counter value or 0 if not found
        """
        try:
            value = self.get(key)
            return int(value) if value else 0
        except (ValueError, TypeError):
            return 0
    
    # Rate Limiting Methods
    
    def check_rate_limit(self, client_id: str, limit: int, window: int) -> Dict[str, Any]:
        """
        Check and update rate limit for a client using sliding window.
        
        Args:
            client_id: Unique client identifier (IP, user ID, etc.)
            limit: Number of requests allowed per window
            window: Time window in seconds
            
        Returns:
            Dict with rate limit information
        """
        if not self.is_connected():
            # Fail open - allow request if Redis is down
            return {
                "allowed": True,
                "current_count": 0,
                "remaining": limit,
                "reset_time": datetime.utcnow() + timedelta(seconds=window)
            }
        
        try:
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window)
            
            # Use sorted set to implement sliding window
            key = f"rate_limit:{client_id}"
            score = now.timestamp()
            
            # Redis pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start.timestamp())
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(score): score})
            
            # Set expiration
            pipe.expire(key, window + 10)  # Keep a bit longer for cleanup
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the current request
            
            allowed = current_count <= limit
            remaining = max(0, limit - current_count)
            reset_time = now + timedelta(seconds=window)
            
            return {
                "allowed": allowed,
                "current_count": current_count,
                "remaining": remaining,
                "reset_time": reset_time,
                "limit": limit,
                "window": window
            }
            
        except Exception as e:
            logger.error(f"Rate limit check failed for {client_id}: {e}")
            # Fail open - allow request on error
            return {
                "allowed": True,
                "current_count": 0,
                "remaining": limit,
                "reset_time": datetime.utcnow() + timedelta(seconds=window)
            }
    
    def reset_rate_limit(self, client_id: str) -> bool:
        """
        Reset rate limit for a client.
        
        Args:
            client_id: Unique client identifier
            
        Returns:
            bool: True if reset successfully
        """
        key = f"rate_limit:{client_id}"
        return self.delete(key)
    
    # Response Caching Methods
    
    def _generate_cache_key(self, method: str, url: str, headers: Dict[str, str] = None) -> str:
        """
        Generate a cache key for a request.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers to include in cache key
            
        Returns:
            str: Cache key
        """
        # Include relevant headers in cache key
        cache_headers = {}
        if headers:
            for header in ['Authorization', 'Accept', 'Content-Type']:
                if header in headers:
                    cache_headers[header] = headers[header]
        
        cache_data = {
            "method": method,
            "url": url,
            "headers": cache_headers
        }
        
        cache_string = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()
        return f"response_cache:{cache_hash}"
    
    def cache_response(self, method: str, url: str, response_data: Dict[str, Any], 
                      ttl: int = 300, headers: Dict[str, str] = None) -> bool:
        """
        Cache an HTTP response.
        
        Args:
            method: HTTP method
            url: Request URL
            response_data: Response data to cache
            ttl: Time to live in seconds (default 5 minutes)
            headers: Request headers
            
        Returns:
            bool: True if cached successfully
        """
        key = self._generate_cache_key(method, url, headers)
        
        cache_entry = {
            "data": response_data,
            "cached_at": datetime.utcnow().isoformat(),
            "ttl": ttl
        }
        
        return self.set(key, cache_entry, ttl)
    
    def get_cached_response(self, method: str, url: str, 
                           headers: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached response for a request.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            
        Returns:
            Cached response data or None if not found
        """
        key = self._generate_cache_key(method, url, headers)
        return self.get(key)
    
    def invalidate_cache_pattern(self, pattern: str) -> int:
        """
        Invalidate cache entries matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "response_cache:*")
            
        Returns:
            int: Number of keys deleted
        """
        if not self.is_connected():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")
            return 0
    
    # Service Discovery Caching
    
    def cache_service_info(self, service_name: str, service_data: Dict[str, Any], ttl: int = 60) -> bool:
        """
        Cache service discovery information.
        
        Args:
            service_name: Name of the service
            service_data: Service information to cache
            ttl: Time to live in seconds (default 1 minute)
            
        Returns:
            bool: True if cached successfully
        """
        key = f"service:{service_name}"
        return self.set(key, service_data, ttl)
    
    def get_service_info(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        Get cached service information.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service information or None if not found
        """
        key = f"service:{service_name}"
        return self.get(key)
    
    def invalidate_service_cache(self, service_name: str) -> bool:
        """
        Invalidate cached service information.
        
        Args:
            service_name: Name of the service
            
        Returns:
            bool: True if invalidated successfully
        """
        key = f"service:{service_name}"
        return self.delete(key)
    
    # Circuit Breaker State Caching
    
    def set_circuit_breaker_state(self, service_name: str, state: str, ttl: int = 60) -> bool:
        """
        Set circuit breaker state for a service.
        
        Args:
            service_name: Name of the service
            state: Circuit breaker state (CLOSED, OPEN, HALF_OPEN)
            ttl: Time to live in seconds
            
        Returns:
            bool: True if set successfully
        """
        key = f"circuit_breaker:{service_name}"
        return self.set(key, {"state": state, "timestamp": datetime.utcnow().isoformat()}, ttl)
    
    def get_circuit_breaker_state(self, service_name: str) -> Optional[str]:
        """
        Get circuit breaker state for a service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Circuit breaker state or None if not found
        """
        key = f"circuit_breaker:{service_name}"
        data = self.get(key)
        return data.get("state") if data else None
    
    def increment_failure_count(self, service_name: str, ttl: int = 60) -> int:
        """
        Increment failure count for circuit breaker.
        
        Args:
            service_name: Name of the service
            ttl: Time to live in seconds
            
        Returns:
            int: New failure count
        """
        key = f"circuit_breaker_failures:{service_name}"
        return self.increment(key, 1, ttl)
    
    def reset_failure_count(self, service_name: str) -> bool:
        """
        Reset failure count for circuit breaker.
        
        Args:
            service_name: Name of the service
            
        Returns:
            bool: True if reset successfully
        """
        key = f"circuit_breaker_failures:{service_name}"
        return self.delete(key)
    
    def close(self):
        """Close Redis connection."""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Gateway Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Gateway Redis connection: {e}")


# Global cache instance
_gateway_cache_instance: Optional[GatewayRedisCache] = None


def get_gateway_cache() -> GatewayRedisCache:
    """
    Get the global Gateway Redis cache instance.
    
    Returns:
        GatewayRedisCache: Global cache instance
    """
    global _gateway_cache_instance
    if _gateway_cache_instance is None:
        _gateway_cache_instance = GatewayRedisCache()
    return _gateway_cache_instance


def close_gateway_cache():
    """Close the global Gateway Redis cache connection."""
    global _gateway_cache_instance
    if _gateway_cache_instance:
        _gateway_cache_instance.close()
        _gateway_cache_instance = None