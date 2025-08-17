"""
Configuration settings for the authentication service.

This module provides configuration loading for the auth service using
JSON configuration files for application settings and environment variables
for infrastructure and secrets.
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path


class SimpleConfigLoader:
    """Simple configuration loader for auth service."""
    
    def __init__(self, service_name: str, service_dir: str):
        self.service_name = service_name
        self.service_dir = service_dir
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json file."""
        config_file = Path(self.service_dir) / "config.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def get_service_config(self) -> Dict[str, Any]:
        return self.config_data.get("service", {})
    
    def get_jwt_config(self) -> Dict[str, Any]:
        jwt_config = self.config_data.get("jwt", {})
        # Override secret from environment
        jwt_config["secret_key"] = os.getenv("JWT_SECRET", jwt_config.get("secret_key", "dev-secret"))
        return jwt_config
    
    def get_logging_config(self) -> Dict[str, Any]:
        return self.config_data.get("logging", {})
    
    def get_cors_config(self) -> Dict[str, Any]:
        return self.config_data.get("cors", {})
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        return self.config_data.get("rate_limiting", {})
    
    def get_host_port(self) -> tuple:
        host = os.getenv("AUTH_SERVICE_HOST", "0.0.0.0")
        port_env = os.getenv("AUTH_SERVICE_PORT", "8001")
        # Handle Kubernetes service environment variable format (tcp://host:port)
        if port_env.startswith("tcp://"):
            port = int(port_env.split(":")[-1])
        else:
            port = int(port_env)
        return host, port
    
    def get_environment(self) -> str:
        return os.getenv("ENVIRONMENT", "development")
    
    def is_debug(self) -> bool:
        return os.getenv("DEBUG", "false").lower() == "true"
    
    def get_database_url(self, db_type: str) -> str:
        return os.getenv("DATABASE_URL", "")
    
    def get_redis_url(self, redis_type: str) -> str:
        return os.getenv("REDIS_URL", "")
    
    def get(self, key: str, default: Any = None, env_var: str = None) -> Any:
        """Get config value with fallback to environment variable."""
        if env_var and os.getenv(env_var):
            return os.getenv(env_var)
        
        keys = key.split('.')
        value = self.config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


def get_config(service_name: str, service_dir: str) -> SimpleConfigLoader:
    """Get configuration loader for service."""
    return SimpleConfigLoader(service_name, service_dir)


class AuthServiceSettings:
    """
    Configuration settings for the authentication microservice.
    
    Loads configuration from:
    - config.json: Application behavior, business logic, static settings
    - Environment variables: Secrets, infrastructure, deployment settings
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize auth service settings."""
        service_dir = config_dir or os.path.dirname(os.path.abspath(__file__))
        self.config = get_config("auth-service", service_dir)
        
        # Cache commonly used values
        self._service_config = self.config.get_service_config()
        self._jwt_config = self.config.get_jwt_config()
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
    def auth_database_url(self) -> str:
        return self.config.get_database_url("auth")
    
    @property
    def auth_redis_url(self) -> str:
        return self.config.get_redis_url("auth")
    
    @property
    def auth_service_host(self) -> str:
        return self._host
    
    @property
    def auth_service_port(self) -> int:
        return self._port
    
    # JWT settings (secret from env, config from JSON)
    @property
    def jwt_secret_key(self) -> str:
        return self._jwt_config["secret_key"]
    
    @property
    def jwt_algorithm(self) -> str:
        return self._jwt_config["algorithm"]
    
    @property
    def access_token_expire_minutes(self) -> int:
        return self._jwt_config["access_token_expire_minutes"]
    
    @property
    def refresh_token_expire_days(self) -> int:
        return self._jwt_config["refresh_token_expire_days"]
    
    # Security settings (from JSON config)
    @property
    def password_min_length(self) -> int:
        return self.config.get("security.password.min_length", 8, "PASSWORD_MIN_LENGTH")
    
    @property
    def password_hash_rounds(self) -> int:
        return self.config.get("security.password.hash_rounds", 12, "PASSWORD_HASH_ROUNDS")
    
    @property
    def max_login_attempts(self) -> int:
        return self.config.get("security.account_lockout.max_login_attempts", 5, "MAX_FAILED_LOGIN_ATTEMPTS")
    
    @property
    def account_lockout_minutes(self) -> int:
        return self.config.get("security.account_lockout.lockout_duration_minutes", 15, "ACCOUNT_LOCKOUT_DURATION_MINUTES")
    
    @property
    def trusted_hosts_enabled(self) -> bool:
        return self.config.get("security.trusted_hosts.enabled", False, "TRUSTED_HOSTS_ENABLED")
    
    @property
    def trusted_hosts(self) -> list:
        return self.config.get("security.trusted_hosts.hosts", ["localhost", "auth-service"], "TRUSTED_HOSTS")
    
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
    
    # Rate limiting
    @property
    def rate_limit_requests(self) -> int:
        return self._rate_limit_config["requests_per_minute"]
    
    @property
    def rate_limit_window(self) -> int:
        return self._rate_limit_config["window_seconds"]
    
    # Logging
    @property
    def log_level(self) -> str:
        return self._logging_config["level"]
    
    @property
    def log_format(self) -> str:
        return self._logging_config["format"]
    
    # Additional settings from JSON config
    @property
    def min_username_length(self) -> int:
        return self.config.get("validation.min_username_length", 3, "MIN_USERNAME_LENGTH")
    
    @property
    def require_password_uppercase(self) -> bool:
        return self.config.get("security.password.require_uppercase", True)
    
    @property
    def require_password_lowercase(self) -> bool:
        return self.config.get("security.password.require_lowercase", True)
    
    @property
    def require_password_numbers(self) -> bool:
        return self.config.get("security.password.require_numbers", True)
    
    @property
    def enable_refresh_tokens(self) -> bool:
        return self.config.get("features.enable_refresh_tokens", True)


def get_auth_settings() -> AuthServiceSettings:
    """
    Get the current authentication service settings.
    
    Creates and returns a settings instance that loads configuration from
    both JSON files and environment variables.
    
    Returns:
        AuthServiceSettings: Configured settings instance
        
    Example:
        settings = get_auth_settings()
        database_url = settings.auth_database_url
    """
    return AuthServiceSettings()