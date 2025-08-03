"""
Base settings classes for microservices.

Provides common configuration patterns using Pydantic settings
that can be extended by individual services.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseSettings, Field, validator
import logging

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """
    Database connection settings.
    """
    
    url: str = Field(..., env="DATABASE_URL", description="Database connection URL")
    echo: bool = Field(False, env="DATABASE_ECHO", description="Enable SQL query logging")
    pool_size: int = Field(10, env="DATABASE_POOL_SIZE", description="Connection pool size")
    max_overflow: int = Field(20, env="DATABASE_MAX_OVERFLOW", description="Max overflow connections")
    pool_timeout: int = Field(30, env="DATABASE_POOL_TIMEOUT", description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, env="DATABASE_POOL_RECYCLE", description="Connection recycle time")
    
    @validator("url")
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "mysql://", "sqlite:///")):
            raise ValueError("Database URL must start with postgresql://, mysql://, or sqlite:///")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class RedisSettings(BaseSettings):
    """
    Redis connection settings.
    """
    
    url: str = Field(..., env="REDIS_URL", description="Redis connection URL")
    db: int = Field(0, env="REDIS_DB", description="Redis database number")
    max_connections: int = Field(20, env="REDIS_MAX_CONNECTIONS", description="Max connections in pool")
    socket_timeout: int = Field(5, env="REDIS_SOCKET_TIMEOUT", description="Socket timeout in seconds")
    socket_connect_timeout: int = Field(5, env="REDIS_SOCKET_CONNECT_TIMEOUT", description="Connect timeout")
    health_check_interval: int = Field(30, env="REDIS_HEALTH_CHECK_INTERVAL", description="Health check interval")
    
    @validator("url")
    def validate_redis_url(cls, v):
        """Validate Redis URL format."""
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with redis://")
        return v
    
    @validator("db")
    def validate_redis_db(cls, v):
        """Validate Redis database number."""
        if not 0 <= v <= 15:
            raise ValueError("Redis database number must be between 0 and 15")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class SecuritySettings(BaseSettings):
    """
    Security-related settings.
    """
    
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY", description="JWT signing secret")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES", description="Token expiry time")
    password_hash_rounds: int = Field(12, env="PASSWORD_HASH_ROUNDS", description="Bcrypt hash rounds")
    
    # Rate limiting
    rate_limit_requests_per_minute: int = Field(1000, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_burst_size: int = Field(100, env="RATE_LIMIT_BURST_SIZE")
    
    # Account security
    max_failed_login_attempts: int = Field(5, env="MAX_FAILED_LOGIN_ATTEMPTS")
    account_lockout_duration_minutes: int = Field(15, env="ACCOUNT_LOCKOUT_DURATION_MINUTES")
    failed_attempt_window_minutes: int = Field(15, env="FAILED_ATTEMPT_WINDOW_MINUTES")
    
    @validator("jwt_secret_key")
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key strength."""
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v
    
    @validator("password_hash_rounds")
    def validate_hash_rounds(cls, v):
        """Validate bcrypt hash rounds."""
        if not 10 <= v <= 15:
            raise ValueError("Password hash rounds should be between 10 and 15")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ObservabilitySettings(BaseSettings):
    """
    Observability and monitoring settings.
    """
    
    log_level: str = Field("INFO", env="LOG_LEVEL", description="Logging level")
    log_format: str = Field("json", env="LOG_FORMAT", description="Log format (json or text)")
    enable_metrics: bool = Field(True, env="ENABLE_METRICS", description="Enable Prometheus metrics")
    enable_tracing: bool = Field(True, env="ENABLE_TRACING", description="Enable distributed tracing")
    
    # Tracing settings
    jaeger_endpoint: Optional[str] = Field(None, env="JAEGER_ENDPOINT", description="Jaeger collector endpoint")
    trace_sample_rate: float = Field(1.0, env="TRACE_SAMPLE_RATE", description="Tracing sample rate (0.0-1.0)")
    
    # Metrics settings
    metrics_path: str = Field("/metrics", env="METRICS_PATH", description="Prometheus metrics endpoint path")
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("log_format")
    def validate_log_format(cls, v):
        """Validate log format."""
        if v.lower() not in ["json", "text"]:
            raise ValueError("Log format must be 'json' or 'text'")
        return v.lower()
    
    @validator("trace_sample_rate")
    def validate_sample_rate(cls, v):
        """Validate trace sample rate."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Trace sample rate must be between 0.0 and 1.0")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ServiceMeshSettings(BaseSettings):
    """
    Service mesh (Linkerd) settings.
    """
    
    enable_service_mesh: bool = Field(False, env="ENABLE_SERVICE_MESH", description="Enable service mesh features")
    service_mesh_type: str = Field("linkerd", env="SERVICE_MESH_TYPE", description="Service mesh type")
    trust_service_mesh_headers: bool = Field(True, env="TRUST_SERVICE_MESH_HEADERS", description="Trust mesh headers")
    
    # Service identity
    service_name: str = Field(..., env="SERVICE_NAME", description="Service name for mesh identity")
    service_namespace: str = Field("default", env="SERVICE_NAMESPACE", description="Service namespace")
    
    # Mesh-specific headers
    mesh_service_header: str = Field("X-Linkerd-Service-Name", env="MESH_SERVICE_HEADER")
    mesh_namespace_header: str = Field("X-Linkerd-Namespace", env="MESH_NAMESPACE_HEADER")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class BaseServiceSettings(BaseSettings):
    """
    Base settings class for microservices.
    
    Combines all common configuration settings that services typically need.
    Services can extend this class and add their own specific settings.
    """
    
    # Service identification
    service_name: str = Field(..., env="SERVICE_NAME", description="Name of the service")
    service_version: str = Field("1.0.0", env="SERVICE_VERSION", description="Service version")
    environment: str = Field("development", env="ENVIRONMENT", description="Deployment environment")
    debug: bool = Field(False, env="DEBUG", description="Enable debug mode")
    
    # HTTP server settings
    host: str = Field("0.0.0.0", env="HOST", description="Server host")
    port: int = Field(8000, env="PORT", description="Server port")
    reload: bool = Field(False, env="RELOAD", description="Enable auto-reload")
    
    # CORS settings
    cors_origins: List[str] = Field(["*"], env="CORS_ORIGINS", description="CORS allowed origins")
    cors_methods: List[str] = Field(["*"], env="CORS_METHODS", description="CORS allowed methods")
    cors_headers: List[str] = Field(["*"], env="CORS_HEADERS", description="CORS allowed headers")
    
    # Database settings
    database: DatabaseSettings = DatabaseSettings()
    
    # Redis settings
    redis: RedisSettings = RedisSettings()
    
    # Security settings
    security: SecuritySettings = SecuritySettings()
    
    # Observability settings
    observability: ObservabilitySettings = ObservabilitySettings()
    
    # Service mesh settings
    service_mesh: ServiceMeshSettings = ServiceMeshSettings()
    
    @validator("environment")
    def validate_environment(cls, v):
        """Validate deployment environment."""
        valid_envs = ["development", "staging", "production", "testing"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()
    
    @validator("port")
    def validate_port(cls, v):
        """Validate port number."""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    def get_database_url(self) -> str:
        """Get database URL."""
        return self.database.url
    
    def get_redis_url(self) -> str:
        """Get Redis URL."""
        return self.redis.url
    
    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            "level": self.observability.log_level,
            "format": self.observability.log_format,
            "service_name": self.service_name
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "allow_origins": self.cors_origins,
            "allow_methods": self.cors_methods,
            "allow_headers": self.cors_headers,
            "allow_credentials": True
        }
    
    def mask_sensitive_values(self) -> Dict[str, Any]:
        """Get configuration dict with sensitive values masked."""
        config = self.dict()
        
        # Mask sensitive values
        if "database" in config and "url" in config["database"]:
            config["database"]["url"] = self._mask_url(config["database"]["url"])
        
        if "redis" in config and "url" in config["redis"]:
            config["redis"]["url"] = self._mask_url(config["redis"]["url"])
        
        if "security" in config and "jwt_secret_key" in config["security"]:
            config["security"]["jwt_secret_key"] = "***"
        
        return config
    
    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in URLs."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.password:
                return url.replace(parsed.password, "***")
            return url
        except Exception:
            return "***"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        # Allow extra fields for service-specific settings
        extra = "allow"


class HealthCheckSettings(BaseSettings):
    """
    Health check configuration.
    """
    
    enabled: bool = Field(True, env="HEALTH_CHECK_ENABLED", description="Enable health checks")
    path: str = Field("/health", env="HEALTH_CHECK_PATH", description="Health check endpoint path")
    include_details: bool = Field(False, env="HEALTH_CHECK_INCLUDE_DETAILS", description="Include detailed info")
    check_database: bool = Field(True, env="HEALTH_CHECK_DATABASE", description="Check database connectivity")
    check_redis: bool = Field(True, env="HEALTH_CHECK_REDIS", description="Check Redis connectivity")
    timeout_seconds: int = Field(5, env="HEALTH_CHECK_TIMEOUT", description="Health check timeout")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"