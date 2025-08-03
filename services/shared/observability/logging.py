"""
Shared logging configuration for microservices.

Provides structured logging with correlation IDs, request tracing,
and consistent formatting across services.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Dict, Any, Optional
from datetime import datetime

# Context variable for correlation ID
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter to add correlation ID to log records.
    """
    
    def filter(self, record):
        record.correlation_id = correlation_id.get('')
        return True


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    """
    
    def __init__(self, service_name: str = "unknown"):
        self.service_name = service_name
        super().__init__()
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, 'correlation_id', ''),
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add function and line info for debug level
        if record.levelno <= logging.DEBUG:
            log_entry.update({
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno
            })
        
        return json.dumps(log_entry)


class StructuredLogger:
    """
    Wrapper for standard logger to add structured logging capabilities.
    """
    
    def __init__(self, name: str, service_name: str = "unknown"):
        self.logger = logging.getLogger(name)
        self.service_name = service_name
    
    def _log_with_extra(self, level: int, message: str, extra_fields: Dict[str, Any] = None, **kwargs):
        """Log message with extra structured fields."""
        extra = {"extra_fields": extra_fields or {}}
        self.logger.log(level, message, extra=extra, **kwargs)
    
    def debug(self, message: str, **extra_fields):
        """Log debug message with extra fields."""
        self._log_with_extra(logging.DEBUG, message, extra_fields)
    
    def info(self, message: str, **extra_fields):
        """Log info message with extra fields."""
        self._log_with_extra(logging.INFO, message, extra_fields)
    
    def warning(self, message: str, **extra_fields):
        """Log warning message with extra fields."""
        self._log_with_extra(logging.WARNING, message, extra_fields)
    
    def error(self, message: str, **extra_fields):
        """Log error message with extra fields."""
        self._log_with_extra(logging.ERROR, message, extra_fields)
    
    def critical(self, message: str, **extra_fields):
        """Log critical message with extra fields."""
        self._log_with_extra(logging.CRITICAL, message, extra_fields)
    
    def request_start(self, method: str, path: str, client_ip: str = None, user_id: str = None):
        """Log request start."""
        self.info(
            f"Request started: {method} {path}",
            request_method=method,
            request_path=path,
            client_ip=client_ip,
            user_id=user_id,
            event_type="request_start"
        )
    
    def request_end(self, method: str, path: str, status_code: int, response_time_ms: float):
        """Log request completion."""
        self.info(
            f"Request completed: {method} {path} - {status_code} ({response_time_ms:.2f}ms)",
            request_method=method,
            request_path=path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            event_type="request_end"
        )
    
    def auth_event(self, event_type: str, user_email: str = None, success: bool = True, reason: str = None):
        """Log authentication events."""
        level = logging.INFO if success else logging.WARNING
        message = f"Auth {event_type}: {'success' if success else 'failed'}"
        if reason:
            message += f" - {reason}"
        
        self._log_with_extra(
            level,
            message,
            {
                "event_type": f"auth_{event_type}",
                "user_email": user_email,
                "success": success,
                "reason": reason
            }
        )
    
    def database_event(self, operation: str, table: str, record_id: Any = None, duration_ms: float = None):
        """Log database operations."""
        message = f"Database {operation}: {table}"
        if record_id:
            message += f" (id={record_id})"
        if duration_ms:
            message += f" ({duration_ms:.2f}ms)"
        
        self.debug(
            message,
            event_type="database_operation",
            db_operation=operation,
            db_table=table,
            record_id=record_id,
            duration_ms=duration_ms
        )
    
    def cache_event(self, operation: str, key: str, hit: bool = None, ttl: int = None):
        """Log cache operations."""
        message = f"Cache {operation}: {key}"
        if hit is not None:
            message += f" ({'hit' if hit else 'miss'})"
        
        self.debug(
            message,
            event_type="cache_operation",
            cache_operation=operation,
            cache_key=key,
            cache_hit=hit,
            cache_ttl=ttl
        )
    
    def security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security events."""
        self.warning(
            f"Security event: {event_type}",
            event_type=f"security_{event_type}",
            **details
        )


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    json_format: bool = True,
    enable_correlation: bool = True
) -> None:
    """
    Setup logging configuration for a microservice.
    
    Args:
        service_name: Name of the service for logging context
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON formatter for structured logging
        enable_correlation: Enable correlation ID tracking
    """
    # Convert string log level to logging constant
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Set formatter
    if json_format:
        formatter = JSONFormatter(service_name)
    else:
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(name)s: %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    
    # Add correlation ID filter if enabled
    if enable_correlation:
        correlation_filter = CorrelationIDFilter()
        console_handler.addFilter(correlation_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Set specific log levels for third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    
    # Log setup completion
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for service: {service_name} (level={log_level})")


def get_logger(name: str, service_name: str = "unknown") -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        service_name: Name of the service
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, service_name)


def set_correlation_id(correlation_id_value: str = None) -> str:
    """
    Set correlation ID for current context.
    
    Args:
        correlation_id_value: Custom correlation ID, generates UUID if None
        
    Returns:
        The correlation ID that was set
    """
    if correlation_id_value is None:
        correlation_id_value = str(uuid.uuid4())
    
    correlation_id.set(correlation_id_value)
    return correlation_id_value


def get_correlation_id() -> str:
    """
    Get current correlation ID.
    
    Returns:
        Current correlation ID or empty string if not set
    """
    return correlation_id.get('')


def clear_correlation_id():
    """Clear correlation ID from current context."""
    correlation_id.set('')


class RequestLoggingMiddleware:
    """
    Middleware to add request logging and correlation IDs to FastAPI apps.
    """
    
    def __init__(self, service_name: str):
        self.logger = get_logger(__name__, service_name)
    
    async def __call__(self, request, call_next):
        """Process request with logging and correlation ID."""
        import time
        
        # Generate correlation ID
        request_correlation_id = request.headers.get(
            "X-Correlation-ID", 
            str(uuid.uuid4())
        )
        set_correlation_id(request_correlation_id)
        
        # Log request start
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, 'user', {}).get('sub') if hasattr(request.state, 'user') else None
        
        self.logger.request_start(
            method=request.method,
            path=str(request.url.path),
            client_ip=client_ip,
            user_id=user_id
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = request_correlation_id
            
            # Log request completion
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.request_end(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                response_time_ms=response_time_ms
            )
            
            return response
            
        except Exception as e:
            # Log request error
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"Request failed: {request.method} {request.url.path}",
                error=str(e),
                response_time_ms=response_time_ms,
                event_type="request_error"
            )
            raise
        finally:
            # Clear correlation ID
            clear_correlation_id()