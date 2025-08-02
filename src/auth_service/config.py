"""
Configuration settings for the authentication service.

This module defines all configuration parameters for the auth service using
Pydantic settings. Supports environment variable overrides and provides
sensible defaults for development.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class AuthServiceSettings(BaseSettings):
    """
    Configuration settings for the authentication microservice.
    
    All settings can be overridden via environment variables. The service
    uses its own dedicated database and Redis instance for security isolation.
    
    Attributes:
        service_name: Service identifier for logging and monitoring
        service_version: Current version of the auth service
        auth_database_url: PostgreSQL connection string for auth database
        auth_redis_url: Redis connection string for auth service cache
        jwt_secret_key: Secret key for JWT token signing (MUST be changed in production)
        jwt_algorithm: Algorithm for JWT token signing/verification
        access_token_expire_minutes: Token expiration time in minutes
        refresh_token_expire_days: Refresh token expiration in days
        auth_service_host: Host address to bind the service
        auth_service_port: Port number for the auth service
        environment: Deployment environment (development/staging/production)
        debug: Enable debug mode (should be False in production)
        allowed_origins: CORS allowed origins list
        allowed_methods: CORS allowed HTTP methods
        allowed_headers: CORS allowed headers
        rate_limit_requests: Maximum requests per time window
        rate_limit_window: Rate limiting time window in seconds
        password_hash_rounds: bcrypt rounds for password hashing
        salt_rounds: PBKDF2 iterations for client-side hashing
        log_level: Logging level (DEBUG/INFO/WARNING/ERROR)
        log_format: Log message format string
        password_min_length: Minimum password length requirement
        max_login_attempts: Maximum failed login attempts before lockout
        account_lockout_minutes: Account lockout duration after failed attempts
    """
    
    # Service info
    service_name: str = "auth-service"
    service_version: str = "1.0.0"
    
    # Database settings (dedicated auth database)
    auth_database_url: str = "postgresql://auth_user:auth_password@localhost:5432/auth_db"
    
    # Redis settings (for auth service caching/sessions)
    auth_redis_url: str = "redis://localhost:6379/1"
    
    # JWT settings
    jwt_secret_key: str = "auth_service_secret_key_change_this"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Service settings
    auth_service_host: str = "0.0.0.0"
    auth_service_port: int = 8001
    
    # Environment
    environment: str = "development"
    debug: bool = False
    
    # CORS settings
    allowed_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    allowed_methods: list = ["GET", "POST", "PUT", "DELETE"]
    allowed_headers: list = ["*"]
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Password hashing
    password_hash_rounds: int = 12
    salt_rounds: int = 100000
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security
    password_min_length: int = 8
    max_login_attempts: int = 5
    account_lockout_minutes: int = 15
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


def get_auth_settings() -> AuthServiceSettings:
    """
    Get the current authentication service settings.
    
    Creates and returns a settings instance with values from environment
    variables or defaults. This function should be used to access settings
    throughout the application.
    
    Returns:
        AuthServiceSettings: Configured settings instance
        
    Example:
        settings = get_auth_settings()
        database_url = settings.auth_database_url
    """
    return AuthServiceSettings()