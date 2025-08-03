"""
Shared configuration utilities for microservices.

This module provides common configuration patterns, environment
variable handling, and settings management.
"""

from .base_settings import BaseServiceSettings, DatabaseSettings, RedisSettings
from .env_loader import load_environment, get_env_var

__all__ = [
    "BaseServiceSettings", 
    "DatabaseSettings", 
    "RedisSettings",
    "load_environment",
    "get_env_var"
]