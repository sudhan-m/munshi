"""
Shared distributed tracing for microservices.

Provides OpenTelemetry tracing setup and utilities for request
tracing across service boundaries.
"""

import logging
from functools import wraps
from typing import Dict, Any, Optional, Callable
from contextvars import ContextVar
import time

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.b3 import B3MultiFormat
    
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    trace = None

logger = logging.getLogger(__name__)

# Context variable for current span
current_span_context: ContextVar[Optional[object]] = ContextVar('current_span', default=None)


def setup_tracing(
    service_name: str,
    jaeger_endpoint: Optional[str] = None,
    sample_rate: float = 1.0,
    enable_auto_instrumentation: bool = True
) -> Optional[object]:
    """
    Setup OpenTelemetry tracing for a microservice.
    
    Args:
        service_name: Name of the service
        jaeger_endpoint: Jaeger collector endpoint
        sample_rate: Sampling rate (0.0 to 1.0)
        enable_auto_instrumentation: Enable automatic instrumentation
        
    Returns:
        Tracer instance or None if tracing not available
    """
    if not TRACING_AVAILABLE:
        logger.warning("OpenTelemetry not available - tracing disabled")
        return None
    
    try:
        # Set up tracer provider
        tracer_provider = TracerProvider(
            resource={
                "service.name": service_name,
                "service.version": "1.0.0"
            }
        )
        trace.set_tracer_provider(tracer_provider)
        
        # Set up Jaeger exporter if endpoint provided
        if jaeger_endpoint:
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=14268,
                collector_endpoint=jaeger_endpoint,
            )
            
            span_processor = BatchSpanProcessor(jaeger_exporter)
            tracer_provider.add_span_processor(span_processor)
            
            logger.info(f"Jaeger tracing configured for {service_name}")
        
        # Set up B3 propagation for Linkerd compatibility
        set_global_textmap(B3MultiFormat())
        
        # Enable auto-instrumentation
        if enable_auto_instrumentation:
            # These instrumentations are automatically configured
            # when the libraries are used
            pass
        
        # Get tracer
        tracer = trace.get_tracer(__name__)
        
        logger.info(f"Tracing configured for service: {service_name}")
        return tracer
        
    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}")
        return None


def trace_request(operation_name: str, tags: Dict[str, Any] = None):
    """
    Decorator to trace function calls as spans.
    
    Args:
        operation_name: Name of the operation being traced
        tags: Additional tags to add to the span
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not TRACING_AVAILABLE:
                return await func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Add tags to span
                if tags:
                    for key, value in tags.items():
                        span.set_attribute(key, str(value))
                
                # Add function info
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    # Store span in context
                    current_span_context.set(span)
                    
                    # Execute function
                    start_time = time.time()
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Add success metrics
                    span.set_attribute("operation.success", True)
                    span.set_attribute("operation.duration_ms", duration * 1000)
                    
                    return result
                    
                except Exception as e:
                    # Add error info to span
                    span.set_attribute("operation.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    
                    raise
                finally:
                    # Clear span from context
                    current_span_context.set(None)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not TRACING_AVAILABLE:
                return func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(operation_name) as span:
                # Add tags to span
                if tags:
                    for key, value in tags.items():
                        span.set_attribute(key, str(value))
                
                # Add function info
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    # Store span in context
                    current_span_context.set(span)
                    
                    # Execute function
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Add success metrics
                    span.set_attribute("operation.success", True)
                    span.set_attribute("operation.duration_ms", duration * 1000)
                    
                    return result
                    
                except Exception as e:
                    # Add error info to span
                    span.set_attribute("operation.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    
                    raise
                finally:
                    # Clear span from context
                    current_span_context.set(None)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class TracingMixin:
    """
    Mixin class to add tracing capabilities to any class.
    """
    
    def add_span_attributes(self, **attributes):
        """
        Add attributes to current span.
        
        Args:
            **attributes: Key-value pairs to add as span attributes
        """
        if not TRACING_AVAILABLE:
            return
        
        span = current_span_context.get()
        if span:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
    
    def add_span_event(self, name: str, attributes: Dict[str, Any] = None):
        """
        Add an event to current span.
        
        Args:
            name: Event name
            attributes: Event attributes
        """
        if not TRACING_AVAILABLE:
            return
        
        span = current_span_context.get()
        if span:
            span.add_event(name, attributes or {})
    
    def set_span_status(self, success: bool, description: str = None):
        """
        Set status of current span.
        
        Args:
            success: Whether operation was successful
            description: Optional status description
        """
        if not TRACING_AVAILABLE:
            return
        
        span = current_span_context.get()
        if span:
            if success:
                span.set_status(trace.Status(trace.StatusCode.OK, description))
            else:
                span.set_status(trace.Status(trace.StatusCode.ERROR, description))


def trace_database_operation(operation: str, table: str = None):
    """
    Decorator specifically for database operations.
    
    Args:
        operation: Database operation (select, insert, update, delete)
        table: Table name
        
    Returns:
        Decorator function
    """
    tags = {"db.operation": operation}
    if table:
        tags["db.table"] = table
    
    return trace_request(f"db.{operation}", tags)


def trace_cache_operation(operation: str, cache_type: str = "redis"):
    """
    Decorator specifically for cache operations.
    
    Args:
        operation: Cache operation (get, set, delete)
        cache_type: Type of cache
        
    Returns:
        Decorator function
    """
    tags = {
        "cache.operation": operation,
        "cache.type": cache_type
    }
    
    return trace_request(f"cache.{operation}", tags)


def trace_http_client_request(method: str, url: str = None):
    """
    Decorator for HTTP client requests.
    
    Args:
        method: HTTP method
        url: Request URL (optional)
        
    Returns:
        Decorator function
    """
    tags = {"http.method": method}
    if url:
        tags["http.url"] = url
    
    return trace_request(f"http.client.{method.lower()}", tags)


def instrument_fastapi_app(app, service_name: str):
    """
    Instrument FastAPI app for automatic tracing.
    
    Args:
        app: FastAPI application instance
        service_name: Name of the service
    """
    if not TRACING_AVAILABLE:
        logger.warning("OpenTelemetry not available - FastAPI instrumentation skipped")
        return
    
    try:
        FastAPIInstrumentor.instrument_app(
            app,
            server_request_hook=None,
            client_request_hook=None,
            excluded_urls="health,metrics,docs,redoc,openapi.json"
        )
        
        logger.info(f"FastAPI instrumentation enabled for {service_name}")
        
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI app: {e}")


def instrument_sqlalchemy(engine):
    """
    Instrument SQLAlchemy engine for automatic tracing.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    if not TRACING_AVAILABLE:
        logger.warning("OpenTelemetry not available - SQLAlchemy instrumentation skipped")
        return
    
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumentation enabled")
        
    except Exception as e:
        logger.error(f"Failed to instrument SQLAlchemy: {e}")


def instrument_redis(redis_client):
    """
    Instrument Redis client for automatic tracing.
    
    Args:
        redis_client: Redis client instance
    """
    if not TRACING_AVAILABLE:
        logger.warning("OpenTelemetry not available - Redis instrumentation skipped")
        return
    
    try:
        RedisInstrumentor().instrument()
        logger.info("Redis instrumentation enabled")
        
    except Exception as e:
        logger.error(f"Failed to instrument Redis: {e}")


def get_trace_context() -> Dict[str, str]:
    """
    Get current trace context for propagation.
    
    Returns:
        Dictionary with trace context headers
    """
    if not TRACING_AVAILABLE:
        return {}
    
    try:
        from opentelemetry.propagate import inject
        
        headers = {}
        inject(headers)
        return headers
        
    except Exception as e:
        logger.error(f"Failed to get trace context: {e}")
        return {}


def set_trace_context(headers: Dict[str, str]):
    """
    Set trace context from headers.
    
    Args:
        headers: Dictionary with trace context headers
    """
    if not TRACING_AVAILABLE:
        return
    
    try:
        from opentelemetry.propagate import extract
        from opentelemetry.context import attach
        
        context = extract(headers)
        attach(context)
        
    except Exception as e:
        logger.error(f"Failed to set trace context: {e}")