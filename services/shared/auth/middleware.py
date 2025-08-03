"""
Shared authentication middleware for FastAPI services.

Provides common authentication and authorization middleware that can be
used across all microservices.
"""

import logging
from typing import Optional, Callable, Any
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .jwt_handler import JWTHandler

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """
    Authentication middleware for FastAPI applications.
    """
    
    def __init__(self, jwt_handler: JWTHandler, cache_client=None):
        self.jwt_handler = jwt_handler
        self.cache_client = cache_client
        self.security = HTTPBearer(auto_error=False)
    
    async def verify_token_middleware(self, request: Request, call_next: Callable) -> Any:
        """
        Middleware to verify JWT tokens on protected routes.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from next handler or 401 if unauthorized
        """
        # Skip authentication for health checks and docs
        if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Extract authorization header
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            logger.warning(f"Missing authorization header for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header required"
            )
        
        # Extract and verify token
        token = self.jwt_handler.extract_token_from_header(authorization)
        if not token:
            logger.warning("Invalid authorization header format")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        # Check token blacklist if cache is available
        if self.cache_client:
            try:
                is_blacklisted = await self.cache_client.is_token_blacklisted(token)
                if is_blacklisted:
                    logger.warning("Attempted use of blacklisted token")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has been revoked"
                    )
            except Exception as e:
                logger.warning(f"Cache check failed, allowing request: {e}")
        
        # Verify token
        payload = self.jwt_handler.verify_token(token)
        if not payload:
            logger.warning("Invalid or expired token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Add user context to request
        request.state.user = payload
        request.state.token = token
        
        logger.info(f"Authenticated user: {payload.get('sub')} for {request.url.path}")
        
        return await call_next(request)
    
    async def verify_service_identity(self, request: Request, call_next: Callable) -> Any:
        """
        Middleware to verify service identity in Linkerd service mesh.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from next handler
        """
        # Check for Linkerd service identity headers
        linkerd_service = request.headers.get("X-Linkerd-Service-Name")
        gateway_id = request.headers.get("X-Gateway-ID")
        
        if linkerd_service and gateway_id:
            request.state.verified_client = True
            request.state.service_mesh = "linkerd"
            request.state.calling_service = linkerd_service
            logger.info(f"Verified Linkerd service identity: {linkerd_service}")
        else:
            request.state.verified_client = False
            request.state.service_mesh = None
        
        return await call_next(request)
    
    def get_current_user(self, request: Request) -> Optional[dict]:
        """
        Extract current user from request state.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User payload from JWT token or None
        """
        return getattr(request.state, "user", None)
    
    def require_auth(self, credentials: HTTPAuthorizationCredentials) -> dict:
        """
        Dependency function to require authentication on specific endpoints.
        
        Args:
            credentials: HTTP authorization credentials
            
        Returns:
            User payload from JWT token
            
        Raises:
            HTTPException: If authentication fails
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization required"
            )
        
        payload = self.jwt_handler.verify_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        return payload