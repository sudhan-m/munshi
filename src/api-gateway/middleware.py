"""
Authentication middleware for the API Gateway.

This module provides authentication middleware that integrates with the
auth service to verify JWT tokens and extract user information. It acts
as a bridge between the gateway and the authentication microservice.
"""

from fastapi import HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")

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