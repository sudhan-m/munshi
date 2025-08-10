"""
Configuration settings for the API Gateway service.

This module provides configuration loading for the API gateway using
JSON configuration files for application settings and environment variables
for infrastructure and secrets.
"""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add the services directory to the Python path
services_dir = Path(__file__).parent.parent
if str(services_dir) not in sys.path:
    sys.path.insert(0, str(services_dir))

from shared.config.config_loader import get_config


class GatewaySettings:
    """
    Configuration settings for the API Gateway microservice.
    
    Loads configuration from:
    - config.json: Application behavior, business logic, static settings
    - Environment variables: Secrets, infrastructure, deployment settings
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize gateway service settings."""
        service_dir = config_dir or os.path.dirname(os.path.abspath(__file__))
        self.config = get_config("api-gateway", service_dir)
        
        # Cache commonly used values
        self._service_config = self.config.get_service_config()
        self._logging_config = self.config.get_logging_config()
        self._cors_config = self.config.get_cors_config()
        self._rate_limit_config = self.config.get_rate_limit_config()
        self._host, self._port = self.config.get_host_port()
    
    # Service info
    @property
    def service_name(self) -> str:
        return self._service_config["name"]
    
    @property
    def service_version(self) -> str:
        return self._service_config["version"]
    
    @property
    def environment(self) -> str:
        return self.config.get_environment()
    
    @property
    def debug(self) -> bool:
        return self.config.is_debug()
    
    # Infrastructure settings (from environment)
    @property
    def gateway_database_url(self) -> str:
        return self.config.get_database_url("gateway")
    
    @property
    def gateway_redis_url(self) -> str:
        return self.config.get_redis_url("gateway")
    
    @property
    def gateway_host(self) -> str:
        return self._host
    
    @property
    def gateway_port(self) -> int:
        return self._port
    
    @property
    def auth_service_url(self) -> str:
        return os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
    
    # Service Discovery
    @property
    def service_discovery_enabled(self) -> bool:
        return self.config.get("routing.service_discovery.enabled", True, "SERVICE_DISCOVERY_ENABLED")
    
    @property
    def health_check_interval(self) -> int:
        return self.config.get("routing.service_discovery.health_check_interval_seconds", 30, "HEALTH_CHECK_INTERVAL")
    
    # CORS settings
    @property
    def allowed_origins(self) -> list:
        return self._cors_config["origins"]
    
    @property
    def allowed_methods(self) -> list:
        return self._cors_config["methods"]
    
    @property
    def allowed_headers(self) -> list:
        return self._cors_config["headers"]
    
    @property
    def allow_credentials(self) -> bool:
        return self._cors_config["allow_credentials"]
    
    # Rate limiting
    @property
    def rate_limit_enabled(self) -> bool:
        return self._rate_limit_config["enabled"]
    
    @property
    def default_rate_limit_requests(self) -> int:
        return self._rate_limit_config["requests_per_minute"]
    
    @property
    def default_rate_limit_window(self) -> int:
        return self._rate_limit_config["window_seconds"]
    
    @property
    def authenticated_rate_limit_requests(self) -> int:
        return self.config.get("rate_limiting.authenticated_requests_per_minute", 5000, "GATEWAY_RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    @property
    def authenticated_rate_limit_window(self) -> int:
        return self.config.get("rate_limiting.authenticated_window_seconds", 60, "AUTH_RATE_LIMIT_WINDOW_SECONDS")
    
    # Request/Response settings
    @property
    def max_request_size(self) -> int:
        mb_size = self.config.get("security.request_limits.max_request_size_mb", 10, "MAX_REQUEST_SIZE_MB")
        return mb_size * 1024 * 1024
    
    @property
    def request_timeout(self) -> int:
        return self.config.get("security.request_limits.request_timeout_seconds", 30, "REQUEST_TIMEOUT_SECONDS")
    
    # Circuit breaker
    @property
    def circuit_breaker_enabled(self) -> bool:
        return self.config.get("circuit_breaker.enabled", True, "CIRCUIT_BREAKER_ENABLED")
    
    @property
    def circuit_breaker_failure_threshold(self) -> int:
        return self.config.get("circuit_breaker.failure_threshold", 5, "CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    
    @property
    def circuit_breaker_timeout(self) -> int:
        return self.config.get("circuit_breaker.timeout_seconds", 60, "CIRCUIT_BREAKER_TIMEOUT_SECONDS")
    
    # Load balancing
    @property
    def load_balancing_strategy(self) -> str:
        return self.config.get("routing.load_balancing.strategy", "round_robin", "LOAD_BALANCING_STRATEGY")
    
    # Security
    @property
    def jwt_verification_enabled(self) -> bool:
        return self.config.get("security.jwt_verification.enabled", True, "JWT_VERIFICATION_ENABLED")
    
    @property
    def require_https(self) -> bool:
        return self.config.get("security.require_https", False, "REQUIRE_HTTPS")
    
    @property
    def trusted_proxies(self) -> list:
        return self.config.get("security.trusted_proxies", ["127.0.0.1", "::1"], "TRUSTED_PROXIES")
    
    # Logging
    @property
    def log_level(self) -> str:
        return self._logging_config["level"]
    
    @property
    def log_format(self) -> str:
        return self._logging_config["format"]
    
    @property
    def access_log_enabled(self) -> bool:
        return self._logging_config["enable_access_logs"]
    
    # Monitoring
    @property
    def metrics_enabled(self) -> bool:
        return self.config.get("monitoring.metrics_enabled", True, "ENABLE_METRICS")
    
    @property
    def health_check_enabled(self) -> bool:
        return self.config.get("monitoring.health_check_enabled", True, "HEALTH_CHECK_ENABLED")
    
    # Caching
    @property
    def caching_enabled(self) -> bool:
        return self.config.get("caching.enabled", True)
    
    @property
    def default_cache_ttl(self) -> int:
        return self.config.get("caching.default_ttl_seconds", 300)
    
    # Features
    @property
    def enable_request_tracing(self) -> bool:
        return self.config.get("features.enable_request_tracing", True)
    
    @property
    def enable_response_compression(self) -> bool:
        return self.config.get("features.enable_response_compression", True)


def get_gateway_settings() -> GatewaySettings:
    """
    Get the current API Gateway service settings.
    
    Creates and returns a settings instance that loads configuration from
    both JSON files and environment variables.
    
    Returns:
        GatewaySettings: Configured settings instance
        
    Example:
        settings = get_gateway_settings()
        auth_url = settings.auth_service_url
    """
    return GatewaySettings()