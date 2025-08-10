"""
Middleware for the API Gateway service.

This module provides middleware for authentication, rate limiting, 
request/response caching, logging, and other cross-cutting concerns 
for the gateway. Integrates with Redis for distributed caching and rate limiting.
"""

import logging
import time
from typing import Callable, Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import httpx
import os
from dotenv import load_dotenv
from cache import get_gateway_cache
from config import get_gateway_settings

load_dotenv()

settings = get_gateway_settings()
AUTH_SERVICE_URL = settings.auth_service_url
logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthMiddleware:
    """
    Authentication middleware for verifying JWT tokens via the auth service.
    
    This middleware communicates with the authentication microservice to
    verify tokens and retrieve user information. It provides a layer of
    abstraction between the gateway and the auth service.
    
    Attributes:
        auth_service_url: Base URL of the authentication service
    """
    
    def __init__(self):
        """Initialize the auth middleware with the auth service URL."""
        self.auth_service_url = AUTH_SERVICE_URL
    
    async def verify_token(self, token: str) -> dict:
        """
        Verify a JWT token with the authentication service.
        
        Makes an HTTP request to the auth service to validate the token.
        This ensures that only the auth service needs to know about JWT
        secret keys and validation logic.
        
        Args:
            token: JWT token string to verify
            
        Returns:
            dict: Token verification response from auth service
            
        Raises:
            HTTPException: If token is invalid or auth service is unavailable
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.auth_service_url}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication credentials"
                    )
            except httpx.RequestError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Auth service unavailable"
                )
    
    async def get_current_user(self, token: str) -> dict:
        """
        Get current user information from the authentication service.
        
        Retrieves detailed user information for the provided token.
        This is used to inject user context into proxied requests.
        
        Args:
            token: JWT token string
            
        Returns:
            dict: User information from auth service
            
        Raises:
            HTTPException: If token is invalid or auth service is unavailable
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.auth_service_url}/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication credentials"
                    )
            except httpx.RequestError:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Auth service unavailable"
                )


# Global auth middleware instance
auth_middleware = AuthMiddleware()


async def require_auth(credentials: HTTPAuthorizationCredentials = security):
    """
    FastAPI dependency that requires valid authentication.
    
    This dependency can be used on any endpoint that requires authentication.
    It verifies the JWT token and returns the token string if valid.
    
    Args:
        credentials: HTTP Bearer credentials from the request
        
    Returns:
        str: Valid JWT token string
        
    Raises:
        HTTPException: If authentication fails
        
    Example:
        @app.get("/protected")
        async def protected_endpoint(token: str = Depends(require_auth)):
            return {"message": "This endpoint requires authentication"}
    """
    await auth_middleware.verify_token(credentials.credentials)
    return credentials.credentials


async def get_user_from_token(credentials: HTTPAuthorizationCredentials = security):
    """
    FastAPI dependency that returns current user information.
    
    This dependency verifies the token and returns the user information.
    Useful for endpoints that need to know who the authenticated user is.
    
    Args:
        credentials: HTTP Bearer credentials from the request
        
    Returns:
        dict: User information from auth service
        
    Raises:
        HTTPException: If authentication fails
        
    Example:
        @app.get("/profile")
        async def get_profile(user: dict = Depends(get_user_from_token)):
            return {"user_id": user["id"], "email": user["email"]}
    """
    user_info = await auth_middleware.get_current_user(credentials.credentials)
    return user_info


class RateLimitMiddleware:
    """
    Rate limiting middleware using Redis for distributed rate limiting.
    
    Implements sliding window rate limiting with different limits for
    authenticated vs anonymous users.
    """
    
    def __init__(self):
        """Initialize rate limiting middleware."""
        self.cache = get_gateway_cache()
        self.settings = get_gateway_settings()
    
    def get_client_id(self, request: Request) -> str:
        """
        Extract client identifier for rate limiting.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Client identifier (user ID or IP address)
        """
        # Check for authenticated user
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Get real client IP from Caddy headers (in order of preference)
        client_ip = (
            request.headers.get("X-Real-IP") or 
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.client.host
        )
        
        return f"ip:{client_ip}"
    
    def get_rate_limits(self, request: Request) -> Dict[str, int]:
        """
        Get rate limits based on client type.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dict with 'limit' and 'window' values
        """
        # Check if user is authenticated
        if hasattr(request.state, 'user_id') and request.state.user_id:
            return {
                "limit": self.settings.authenticated_rate_limit_requests,
                "window": self.settings.authenticated_rate_limit_window
            }
        else:
            return {
                "limit": self.settings.default_rate_limit_requests,
                "window": self.settings.default_rate_limit_window
            }
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting to the request.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response
        """
        # Skip rate limiting if disabled or for health checks
        if (not self.settings.rate_limit_enabled or 
            request.headers.get("X-Gateway-Health-Check") == "true" or
            request.url.path.startswith("/health")):
            return await call_next(request)
        
        # Get client identifier and rate limits
        client_id = self.get_client_id(request)
        rate_limits = self.get_rate_limits(request)
        
        # Check rate limit
        rate_limit_info = self.cache.check_rate_limit(
            client_id, 
            rate_limits["limit"], 
            rate_limits["window"]
        )
        
        # Add rate limit headers to response
        def add_rate_limit_headers(response: Response):
            response.headers["X-RateLimit-Limit"] = str(rate_limits["limit"])
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(int(rate_limit_info["reset_time"].timestamp()))
            response.headers["X-RateLimit-Window"] = str(rate_limits["window"])
            response.headers["X-RateLimit-Client"] = client_id.split(":")[0]  # ip or user
            return response
        
        # Check if rate limit exceeded
        if not rate_limit_info["allowed"]:
            logger.warning(f"Rate limit exceeded for client {client_id}")
            
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {rate_limits['limit']} per {rate_limits['window']} seconds",
                    "retry_after": rate_limits["window"],
                    "request_id": request.headers.get("X-Request-ID", "unknown")
                }
            )
            return add_rate_limit_headers(response)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to successful response
        return add_rate_limit_headers(response)


class ResponseCacheMiddleware:
    """
    Response caching middleware using Redis for distributed caching.
    
    Caches GET responses based on URL, query parameters, and relevant headers.
    """
    
    def __init__(self):
        """Initialize response caching middleware."""
        self.cache = get_gateway_cache()
        self.settings = get_gateway_settings()
        
        # Default cache TTL for different response types
        self.cache_ttl_map = {
            "application/json": 300,  # 5 minutes
            "text/html": 600,         # 10 minutes
            "text/plain": 180,        # 3 minutes
        }
    
    def should_cache_request(self, request: Request) -> bool:
        """
        Determine if a request should be cached.
        
        Args:
            request: FastAPI request object
            
        Returns:
            bool: True if request should be cached
        """
        # Only cache GET requests
        if request.method != "GET":
            return False
        
        # Don't cache requests with authorization headers (user-specific)
        if request.headers.get("Authorization"):
            return False
        
        # Don't cache requests with cache-control: no-cache
        cache_control = request.headers.get("Cache-Control", "")
        if "no-cache" in cache_control.lower():
            return False
        
        return True
    
    def get_cache_ttl(self, response: Response) -> int:
        """
        Get cache TTL based on response content type.
        
        Args:
            response: HTTP response
            
        Returns:
            int: Cache TTL in seconds
        """
        content_type = response.headers.get("content-type", "").split(";")[0]
        return self.cache_ttl_map.get(content_type, 300)  # Default 5 minutes
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Apply response caching to the request.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response (cached or fresh)
        """
        # Check if request should be cached
        if not self.should_cache_request(request):
            return await call_next(request)
        
        # Try to get cached response
        url = str(request.url)
        headers = dict(request.headers)
        
        cached_response = self.cache.get_cached_response("GET", url, headers)
        
        if cached_response:
            logger.debug(f"Cache hit for {url}")
            
            # Create response from cached data
            response_data = cached_response["data"]
            response = JSONResponse(
                content=response_data.get("content"),
                status_code=response_data.get("status_code", 200),
                headers=response_data.get("headers", {})
            )
            
            # Add cache headers
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Cache-Date"] = cached_response["cached_at"]
            
            return response
        
        # No cache hit - process request
        logger.debug(f"Cache miss for {url}")
        start_time = time.time()
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        # Cache successful responses
        if 200 <= response.status_code < 300:
            # Read response body if available
            response_content = None
            if hasattr(response, 'body'):
                response_content = response.body.decode()
            
            response_data = {
                "content": response_content,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "processing_time": processing_time
            }
            
            cache_ttl = self.get_cache_ttl(response)
            self.cache.cache_response("GET", url, response_data, cache_ttl, headers)
            
            # Add cache headers
            response.headers["X-Cache"] = "MISS"
            response.headers["X-Cache-TTL"] = str(cache_ttl)
        
        return response


class LoggingMiddleware:
    """
    Request/response logging middleware for monitoring and debugging.
    """
    
    def __init__(self):
        """Initialize logging middleware."""
        self.settings = get_gateway_settings()
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """
        Log request and response information.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint in chain
            
        Returns:
            Response: HTTP response
        """
        # Start timing
        start_time = time.time()
        
        # Extract request information (use Caddy headers for accurate client info)
        client_ip = (
            request.headers.get("X-Real-IP") or 
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or
            request.client.host
        )
        method = request.method
        url = str(request.url)
        user_agent = request.headers.get("User-Agent", "")
        request_id = request.headers.get("X-Request-ID", "unknown")
        request_type = request.headers.get("X-Request-Type", "unknown")
        
        # Log request with enhanced information
        if self.settings.access_log_enabled:
            logger.info(f"[{request_id}] {method} {url} from {client_ip} (type: {request_type})")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # milliseconds
            
            # Log response with enhanced information
            if self.settings.access_log_enabled:
                logger.info(
                    f"[{request_id}] {response.status_code} for {method} {url} "
                    f"({processing_time:.2f}ms) from {client_ip} (type: {request_type})"
                )
            
            # Add enhanced timing and tracing headers
            response.headers["X-Processing-Time"] = f"{processing_time:.2f}ms"
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Gateway-Version"] = "1.0.0"
            
            return response
            
        except Exception as e:
            # Log error with enhanced information
            processing_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] Error: {str(e)} for {method} {url} "
                f"({processing_time:.2f}ms) from {client_ip} (type: {request_type})"
            )
            raise


# Convenience functions for creating middleware instances

def create_rate_limit_middleware() -> RateLimitMiddleware:
    """Create rate limiting middleware instance."""
    return RateLimitMiddleware()


def create_response_cache_middleware() -> ResponseCacheMiddleware:
    """Create response caching middleware instance."""
    return ResponseCacheMiddleware()


def create_logging_middleware() -> LoggingMiddleware:
    """Create logging middleware instance."""
    return LoggingMiddleware()