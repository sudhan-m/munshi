"""
Shared authentication utilities for microservices.

This module provides common JWT handling, password hashing, and middleware
for authentication across all services.
"""

from .jwt_handler import JWTHandler
from .middleware import AuthMiddleware

__all__ = ["JWTHandler", "AuthMiddleware"]