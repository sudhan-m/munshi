"""
Shared database utilities for microservices.

This module provides common database models, connection management,
and utilities used across all services.
"""

from .base_model import BaseModel, TimestampMixin
from .connection import DatabaseManager

__all__ = ["BaseModel", "TimestampMixin", "DatabaseManager"]