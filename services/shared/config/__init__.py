"""
Shared configuration utilities for microservices.

This module provides unified configuration loading that combines
JSON configuration files with environment variables.
"""

from .config_loader import ConfigLoader, get_config

__all__ = [
    "ConfigLoader",
    "get_config"
]