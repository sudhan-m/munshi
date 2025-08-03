"""
Shared observability utilities for microservices.

This module provides common logging, metrics, and tracing functionality
that can be used across all services.
"""

from .logging import setup_logging, get_logger, CorrelationIDFilter
from .metrics import MetricsCollector
from .tracing import setup_tracing, trace_request

__all__ = [
    "setup_logging", 
    "get_logger", 
    "CorrelationIDFilter",
    "MetricsCollector",
    "setup_tracing",
    "trace_request"
]