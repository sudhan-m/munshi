"""
Shared metrics collection for microservices.

Provides Prometheus metrics collection and common metrics patterns
used across services.
"""

import time
from typing import Dict, Any, Optional
from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    CollectorRegistry, generate_latest,
    CONTENT_TYPE_LATEST
)
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Centralized metrics collection for microservices.
    
    Provides common metrics patterns for HTTP requests, database operations,
    cache operations, and business metrics.
    """
    
    def __init__(self, service_name: str, registry: Optional[CollectorRegistry] = None):
        """
        Initialize metrics collector.
        
        Args:
            service_name: Name of the service
            registry: Optional custom registry, uses default if None
        """
        self.service_name = service_name
        self.registry = registry or CollectorRegistry()
        
        # Service info metric
        self.service_info = Info(
            'service_info',
            'Service information',
            registry=self.registry
        )
        self.service_info.info({
            'service_name': service_name,
            'version': '1.0.0'  # You might want to make this configurable
        })
        
        # HTTP request metrics
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_requests_in_flight = Gauge(
            'http_requests_in_flight',
            'Current number of HTTP requests being processed',
            registry=self.registry
        )
        
        # Authentication metrics
        self.auth_attempts_total = Counter(
            'auth_attempts_total',
            'Total authentication attempts',
            ['type', 'result'],
            registry=self.registry
        )
        
        self.auth_tokens_created = Counter(
            'auth_tokens_created_total',
            'Total JWT tokens created',
            registry=self.registry
        )
        
        self.auth_tokens_validated = Counter(
            'auth_tokens_validated_total',
            'Total JWT tokens validated',
            ['result'],
            registry=self.registry
        )
        
        # Database metrics
        self.db_operations_total = Counter(
            'db_operations_total',
            'Total database operations',
            ['operation', 'table', 'result'],
            registry=self.registry
        )
        
        self.db_operation_duration = Histogram(
            'db_operation_duration_seconds',
            'Database operation duration in seconds',
            ['operation', 'table'],
            registry=self.registry
        )
        
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Current active database connections',
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_operations_total = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'cache_hit_ratio',
            'Cache hit ratio (0-1)',
            registry=self.registry
        )
        
        # Rate limiting metrics
        self.rate_limit_exceeded = Counter(
            'rate_limit_exceeded_total',
            'Total rate limit violations',
            ['limit_type'],
            registry=self.registry
        )
        
        # Business metrics (can be extended per service)
        self.business_operations = Counter(
            'business_operations_total',
            'Total business operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        # Error metrics
        self.errors_total = Counter(
            'errors_total',
            'Total errors',
            ['error_type', 'component'],
            registry=self.registry
        )
        
        logger.info(f"Metrics collector initialized for service: {service_name}")
    
    # HTTP Request Metrics
    
    def track_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """
        Track HTTP request metrics.
        
        Args:
            method: HTTP method
            endpoint: Request endpoint
            status_code: Response status code
            duration: Request duration in seconds
        """
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def increment_requests_in_flight(self):
        """Increment in-flight requests counter."""
        self.http_requests_in_flight.inc()
    
    def decrement_requests_in_flight(self):
        """Decrement in-flight requests counter."""
        self.http_requests_in_flight.dec()
    
    # Authentication Metrics
    
    def track_auth_attempt(self, auth_type: str, success: bool):
        """
        Track authentication attempt.
        
        Args:
            auth_type: Type of authentication (login, token_validation, etc.)
            success: Whether authentication succeeded
        """
        result = "success" if success else "failure"
        self.auth_attempts_total.labels(
            type=auth_type,
            result=result
        ).inc()
    
    def track_token_creation(self):
        """Track JWT token creation."""
        self.auth_tokens_created.inc()
    
    def track_token_validation(self, success: bool):
        """
        Track JWT token validation.
        
        Args:
            success: Whether validation succeeded
        """
        result = "success" if success else "failure"
        self.auth_tokens_validated.labels(result=result).inc()
    
    # Database Metrics
    
    def track_db_operation(self, operation: str, table: str, success: bool, duration: float):
        """
        Track database operation.
        
        Args:
            operation: Database operation (select, insert, update, delete)
            table: Table name
            success: Whether operation succeeded
            duration: Operation duration in seconds
        """
        result = "success" if success else "failure"
        
        self.db_operations_total.labels(
            operation=operation,
            table=table,
            result=result
        ).inc()
        
        self.db_operation_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def set_db_connections_active(self, count: int):
        """
        Set current active database connections.
        
        Args:
            count: Number of active connections
        """
        self.db_connections_active.set(count)
    
    # Cache Metrics
    
    def track_cache_operation(self, operation: str, hit: bool = None):
        """
        Track cache operation.
        
        Args:
            operation: Cache operation (get, set, delete, etc.)
            hit: Whether operation was a cache hit (for get operations)
        """
        if operation == "get":
            result = "hit" if hit else "miss"
        else:
            result = "success"  # Assume set/delete operations succeed
        
        self.cache_operations_total.labels(
            operation=operation,
            result=result
        ).inc()
    
    def update_cache_hit_ratio(self, hit_ratio: float):
        """
        Update cache hit ratio.
        
        Args:
            hit_ratio: Cache hit ratio between 0 and 1
        """
        self.cache_hit_ratio.set(hit_ratio)
    
    # Rate Limiting Metrics
    
    def track_rate_limit_exceeded(self, limit_type: str):
        """
        Track rate limit violation.
        
        Args:
            limit_type: Type of rate limit (api, auth, etc.)
        """
        self.rate_limit_exceeded.labels(limit_type=limit_type).inc()
    
    # Business Metrics
    
    def track_business_operation(self, operation: str, success: bool):
        """
        Track business operation.
        
        Args:
            operation: Business operation name
            success: Whether operation succeeded
        """
        result = "success" if success else "failure"
        self.business_operations.labels(
            operation=operation,
            result=result
        ).inc()
    
    # Error Metrics
    
    def track_error(self, error_type: str, component: str):
        """
        Track error occurrence.
        
        Args:
            error_type: Type of error (validation, database, network, etc.)
            component: Component where error occurred
        """
        self.errors_total.labels(
            error_type=error_type,
            component=component
        ).inc()
    
    # Utility Methods
    
    def get_metrics(self) -> str:
        """
        Get Prometheus metrics in text format.
        
        Returns:
            Metrics in Prometheus text format
        """
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_content_type(self) -> str:
        """
        Get content type for metrics endpoint.
        
        Returns:
            Prometheus metrics content type
        """
        return CONTENT_TYPE_LATEST


class MetricsMiddleware:
    """
    FastAPI middleware for automatic HTTP metrics collection.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    async def __call__(self, request, call_next):
        """Process request with metrics collection."""
        import time
        
        # Start timing
        start_time = time.time()
        
        # Increment in-flight requests
        self.metrics.increment_requests_in_flight()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Track metrics
            self.metrics.track_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
            
        except Exception as e:
            # Track error
            duration = time.time() - start_time
            
            # Determine status code from exception
            status_code = getattr(e, 'status_code', 500)
            
            self.metrics.track_http_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=status_code,
                duration=duration
            )
            
            self.metrics.track_error(
                error_type=type(e).__name__,
                component="http_handler"
            )
            
            raise
        
        finally:
            # Decrement in-flight requests
            self.metrics.decrement_requests_in_flight()


def create_metrics_endpoint(metrics_collector: MetricsCollector):
    """
    Create FastAPI endpoint for Prometheus metrics.
    
    Args:
        metrics_collector: Metrics collector instance
        
    Returns:
        FastAPI endpoint function
    """
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        from fastapi import Response
        
        metrics_data = metrics_collector.get_metrics()
        return Response(
            content=metrics_data,
            media_type=metrics_collector.get_metrics_content_type()
        )
    
    return metrics_endpoint