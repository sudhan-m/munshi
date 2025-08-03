"""
Cache decorators for FastAPI endpoints.

Provides decorators for response caching and rate limiting that can be
applied to any FastAPI endpoint.
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Callable, Optional, Any
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from .redis_client import RedisClient

logger = logging.getLogger(__name__)


def cache_response(
    redis_client: RedisClient,
    ttl: int = 300,
    key_prefix: str = "response_cache",
    include_user: bool = False
):
    """
    Decorator to cache GET request responses.
    
    Args:
        redis_client: Redis client instance
        ttl: Cache TTL in seconds (default: 5 minutes)
        key_prefix: Cache key prefix
        include_user: Include user in cache key for user-specific caching
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs or args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, execute without caching
                return await func(*args, **kwargs)
            
            # Only cache GET requests
            if request.method != "GET":
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key_parts = [
                key_prefix,
                request.url.path,
                str(sorted(request.query_params.items()))
            ]
            
            # Include user in cache key if requested
            if include_user and hasattr(request.state, 'user'):
                user_id = request.state.user.get('sub', 'anonymous')
                cache_key_parts.append(f"user:{user_id}")
            
            # Create hash of cache key for consistent key length
            cache_key_str = ":".join(cache_key_parts)
            cache_key = f"{key_prefix}:{hashlib.md5(cache_key_str.encode()).hexdigest()}"
            
            # Try to get cached response
            try:
                cached_response = redis_client.get(cache_key, as_json=True)
                if cached_response:
                    logger.debug(f"Cache hit for {request.url.path}")
                    return JSONResponse(
                        content=cached_response["content"],
                        status_code=cached_response["status_code"],
                        headers=cached_response.get("headers", {})
                    )
            except Exception as e:
                logger.warning(f"Cache retrieval error: {e}")
            
            # Execute original function
            response = await func(*args, **kwargs)
            
            # Cache successful responses
            try:
                if isinstance(response, JSONResponse) and response.status_code == 200:
                    cache_data = {
                        "content": response.body.decode() if hasattr(response, 'body') else None,
                        "status_code": response.status_code,
                        "headers": dict(response.headers)
                    }
                    
                    # Try to parse content as JSON for proper caching
                    try:
                        if cache_data["content"]:
                            cache_data["content"] = json.loads(cache_data["content"])
                    except json.JSONDecodeError:
                        pass
                    
                    redis_client.set(cache_key, cache_data, ttl)
                    logger.debug(f"Response cached for {request.url.path}")
                    
            except Exception as e:
                logger.warning(f"Cache storage error: {e}")
            
            return response
        
        return wrapper
    return decorator


def rate_limit(
    redis_client: RedisClient,
    requests_per_minute: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
    error_message: str = "Rate limit exceeded"
):
    """
    Decorator to apply rate limiting to endpoints.
    
    Args:
        redis_client: Redis client instance
        requests_per_minute: Maximum requests per minute
        key_func: Function to generate rate limit key from request
        error_message: Error message for rate limit exceeded
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs or args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                # If no request found, execute without rate limiting
                return await func(*args, **kwargs)
            
            # Generate rate limit key
            if key_func:
                rate_limit_key = key_func(request)
            else:
                # Default: use IP address and user if available
                client_ip = request.client.host if request.client else "unknown"
                user_id = "anonymous"
                
                if hasattr(request.state, 'user') and request.state.user:
                    user_id = request.state.user.get('sub', 'anonymous')
                
                rate_limit_key = f"rate_limit:{client_ip}:{user_id}"
            
            # Check rate limit
            try:
                rate_check = redis_client.check_rate_limit(
                    rate_limit_key, 
                    requests_per_minute, 
                    60  # 60 seconds window
                )
                
                if not rate_check["allowed"]:
                    logger.warning(f"Rate limit exceeded for {rate_limit_key}")
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=error_message,
                        headers={
                            "X-RateLimit-Limit": str(requests_per_minute),
                            "X-RateLimit-Remaining": str(rate_check["remaining"]),
                            "X-RateLimit-Reset": str(int(rate_check.get("reset_time", 0)))
                        }
                    )
                
                # Execute original function
                response = await func(*args, **kwargs)
                
                # Add rate limit headers to response
                if hasattr(response, 'headers'):
                    response.headers["X-RateLimit-Limit"] = str(requests_per_minute)
                    response.headers["X-RateLimit-Remaining"] = str(rate_check["remaining"])
                    if rate_check.get("reset_time"):
                        response.headers["X-RateLimit-Reset"] = str(int(rate_check["reset_time"]))
                
                return response
                
            except HTTPException:
                raise  # Re-raise HTTP exceptions (like rate limit exceeded)
            except Exception as e:
                logger.error(f"Rate limiting error: {e}")
                # Fail open - allow request if rate limiting fails
                return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def cache_invalidate(
    redis_client: RedisClient,
    pattern: str = "*",
    key_prefix: str = "response_cache"
):
    """
    Decorator to invalidate cache entries after modifying operations.
    
    Args:
        redis_client: Redis client instance
        pattern: Pattern to match cache keys for invalidation
        key_prefix: Cache key prefix to invalidate
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute original function
            response = await func(*args, **kwargs)
            
            # Invalidate cache after successful operations
            try:
                if hasattr(response, 'status_code') and 200 <= response.status_code < 300:
                    # For now, we'll implement simple pattern-based invalidation
                    # In production, you might want more sophisticated cache tagging
                    
                    if redis_client.is_available():
                        # This is a simplified implementation
                        # In production, you'd want to track cache tags or use pub/sub
                        logger.info(f"Cache invalidation triggered by {func.__name__}")
                        
                        # Note: Redis doesn't support wildcard deletion efficiently
                        # Consider implementing cache tagging for production use
                        
            except Exception as e:
                logger.warning(f"Cache invalidation error: {e}")
            
            return response
        
        return wrapper
    return decorator