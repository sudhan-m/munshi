"""
Configuration settings for the API Gateway service.

This module defines all configuration parameters for the API gateway using
Pydantic settings. The gateway acts as the entry point for all client requests
and handles routing, authentication, rate limiting, and service discovery.
"""

from pydantic_settings import BaseSettings
from typing import Dict, List


class GatewaySettings(BaseSettings):
    """
    Configuration settings for the API Gateway microservice.
    
    The gateway maintains its own database for service registry, request logs,
    and rate limiting data. All settings can be overridden via environment
    variables for different deployment environments.
    
    Attributes:
        service_name: Service identifier for logging and monitoring
        service_version: Current version of the gateway service
        gateway_database_url: PostgreSQL connection for gateway database
        gateway_redis_url: Redis connection for caching and rate limiting
        gateway_host: Host address to bind the gateway service
        gateway_port: Port number for the gateway service
        auth_service_url: URL of the authentication service
        service_discovery_enabled: Enable automatic service discovery
        health_check_interval: Health check frequency in seconds
        environment: Deployment environment (development/staging/production)
        debug: Enable debug mode (should be False in production)
        allowed_origins: CORS allowed origins list
        allowed_methods: CORS allowed HTTP methods
        allowed_headers: CORS allowed headers
        allow_credentials: Allow credentials in CORS requests
        rate_limit_enabled: Enable rate limiting functionality
        default_rate_limit_requests: Default requests per time window
        default_rate_limit_window: Default rate limiting window in seconds
        authenticated_rate_limit_requests: Higher limit for authenticated users
        authenticated_rate_limit_window: Rate limiting window for authenticated users
        max_request_size: Maximum request body size in bytes
        request_timeout: Request timeout in seconds
        circuit_breaker_enabled: Enable circuit breaker pattern
        circuit_breaker_failure_threshold: Failures before opening circuit
        circuit_breaker_timeout: Circuit breaker reset timeout
        load_balancing_strategy: Strategy for distributing requests
        jwt_verification_enabled: Enable JWT token verification
        require_https: Require HTTPS connections (production setting)
        trusted_proxies: List of trusted proxy IP addresses
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR)
        log_format: Log message format string
        access_log_enabled: Enable HTTP access logging
        metrics_enabled: Enable metrics collection
        health_check_enabled: Enable health check endpoints
    """
    
    # Service info
    service_name: str = "api-gateway"
    service_version: str = "1.0.0"
    
    # Gateway database (for service registry, rate limiting, etc.)
    gateway_database_url: str = "postgresql://gateway_user:gateway_password@localhost:5432/gateway_db"
    
    # Redis for caching and rate limiting
    gateway_redis_url: str = "redis://localhost:6379/0"
    
    # Gateway settings
    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8000
    
    # Service discovery
    auth_service_url: str = "http://localhost:8001"
    service_discovery_enabled: bool = True
    health_check_interval: int = 30
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # CORS settings
    allowed_origins: list = ["http://localhost:3000", "http://localhost:3001"]
    allowed_methods: list = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    allowed_headers: list = ["*"]
    allow_credentials: bool = True
    
    # Rate limiting
    rate_limit_enabled: bool = True
    default_rate_limit_requests: int = 1000
    default_rate_limit_window: int = 60
    authenticated_rate_limit_requests: int = 5000
    authenticated_rate_limit_window: int = 60
    
    # Request/Response settings
    max_request_size: int = 10 * 1024 * 1024  # 10MB
    request_timeout: int = 30
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    
    # Load balancing
    load_balancing_strategy: str = "round_robin"  # round_robin, least_connections, random
    
    # Security
    jwt_verification_enabled: bool = True
    require_https: bool = False  # Set to True in production
    trusted_proxies: list = ["127.0.0.1", "::1"]
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    access_log_enabled: bool = True
    
    # Monitoring
    metrics_enabled: bool = True
    health_check_enabled: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_gateway_settings() -> GatewaySettings:
    """
    Get the current API Gateway service settings.
    
    Creates and returns a settings instance with values from environment
    variables or defaults. This function should be used to access settings
    throughout the gateway application.
    
    Returns:
        GatewaySettings: Configured settings instance
        
    Example:
        settings = get_gateway_settings()
        auth_url = settings.auth_service_url
    """
    return GatewaySettings()