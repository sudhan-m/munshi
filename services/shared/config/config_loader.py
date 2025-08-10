"""
Configuration loader for Munshi microservices.

This module provides a unified way to load configuration from JSON files
and environment variables. It follows the principle of:
- JSON files for application behavior and business logic
- Environment variables for secrets, infrastructure, and deployment settings
"""

import json
import os
from typing import Any, Dict, Optional, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Unified configuration loader that combines JSON config files with environment variables.
    
    Priority order:
    1. Environment variables (highest priority)
    2. JSON configuration files
    3. Default values (lowest priority)
    """
    
    def __init__(self, service_name: str, config_dir: Optional[str] = None):
        """
        Initialize the configuration loader.
        
        Args:
            service_name: Name of the service (e.g., 'auth-service', 'api-gateway')
            config_dir: Directory containing config.json, defaults to service directory
        """
        self.service_name = service_name
        self.config_dir = config_dir or os.path.dirname(os.path.abspath(__file__))
        self.config_data = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from JSON file and environment variables."""
        # Load JSON configuration
        config_file = Path(self.config_dir) / "config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    self.config_data = json.load(f)
                logger.info(f"Loaded configuration from {config_file}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file {config_file}: {e}")
                self.config_data = {}
            except Exception as e:
                logger.error(f"Failed to load config file {config_file}: {e}")
                self.config_data = {}
        else:
            logger.warning(f"Config file {config_file} not found, using defaults")
            self.config_data = {}
    
    def get(self, key_path: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """
        Get a configuration value with environment variable override.
        
        Args:
            key_path: Dot-separated path to the config value (e.g., 'security.jwt.algorithm')
            default: Default value if not found in config or env
            env_var: Environment variable name to check (overrides JSON config)
        
        Returns:
            Configuration value with environment variable taking precedence
        """
        # Check environment variable first (highest priority)
        if env_var and env_var in os.environ:
            return self._parse_env_value(os.environ[env_var])
        
        # Check JSON configuration
        value = self._get_nested_value(self.config_data, key_path)
        if value is not None:
            return value
        
        # Return default value
        return default
    
    def get_database_url(self, service_type: str) -> str:
        """
        Get database URL from environment variables.
        
        Args:
            service_type: 'auth' or 'gateway'
            
        Returns:
            Database connection URL
        """
        env_var = f"{service_type.upper()}_DATABASE_URL"
        return os.getenv(env_var, f"postgresql://{service_type}_user:{service_type}_password@localhost:5432/{service_type}_db")
    
    def get_redis_url(self, service_type: str) -> str:
        """
        Get Redis URL from environment variables.
        
        Args:
            service_type: 'auth' or 'gateway'
            
        Returns:
            Redis connection URL
        """
        env_var = f"{service_type.upper()}_REDIS_URL"
        db_num = "1" if service_type == "auth" else "0"
        return os.getenv(env_var, f"redis://localhost:6379/{db_num}")
    
    def get_service_config(self) -> Dict[str, Any]:
        """Get service metadata configuration."""
        return self.get("service", {
            "name": self.service_name,
            "version": "1.0.0",
            "description": f"{self.service_name} microservice"
        })
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security-related configuration."""
        return self.get("security", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            "level": self.get("logging.level", "INFO", "LOG_LEVEL"),
            "format": self.get("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "LOG_FORMAT"),
            "enable_access_logs": self.get("logging.access_log_enabled", True, "ACCESS_LOG_ENABLED")
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "origins": self._parse_env_list(os.getenv("CORS_ORIGINS")) or self.get("cors.origins", ["*"]),
            "methods": self._parse_env_list(os.getenv("CORS_METHODS")) or self.get("cors.methods", ["GET", "POST"]),
            "headers": self._parse_env_list(os.getenv("CORS_HEADERS")) or self.get("cors.headers", ["*"]),
            "allow_credentials": self._parse_env_bool(os.getenv("CORS_ALLOW_CREDENTIALS")) or self.get("cors.allow_credentials", True)
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration."""
        return {
            "enabled": self._parse_env_bool(os.getenv("RATE_LIMIT_ENABLED")) or self.get("rate_limiting.enabled", True),
            "requests_per_minute": int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "0")) or self.get("rate_limiting.requests_per_minute", 1000),
            "window_seconds": int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "0")) or self.get("rate_limiting.window_seconds", 60)
        }
    
    def get_jwt_config(self) -> Dict[str, Any]:
        """Get JWT configuration (secret from env, config from JSON)."""
        return {
            "secret_key": os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
            "algorithm": self.get("security.jwt.algorithm", "HS256", "JWT_ALGORITHM"),
            "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "0")) or self.get("security.jwt.access_token_expire_minutes", 30),
            "refresh_token_expire_days": int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "0")) or self.get("security.jwt.refresh_token_expire_days", 7)
        }
    
    def get_host_port(self) -> tuple[str, int]:
        """Get host and port from environment variables."""
        service_prefix = self.service_name.upper().replace("-", "_")
        host = os.getenv(f"{service_prefix}_HOST", "0.0.0.0")
        
        # Handle Kubernetes service environment variables (e.g., tcp://10.1.1.1:8000)
        port_env = os.getenv(f"{service_prefix}_PORT", "8000")
        if port_env.startswith("tcp://"):
            port = int(port_env.split(":")[-1])
        else:
            port = int(port_env)
        return host, port
    
    def get_environment(self) -> str:
        """Get deployment environment."""
        return os.getenv("ENVIRONMENT", "development")
    
    def is_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return os.getenv("DEBUG", "false").lower() == "true"
    
    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """
        Get a nested value from dictionary using dot notation.
        
        Args:
            data: Dictionary to search in
            key_path: Dot-separated path (e.g., 'security.jwt.algorithm')
            
        Returns:
            Value if found, None otherwise
        """
        keys = key_path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _parse_env_value(self, value: str) -> Union[str, int, float, bool, list]:
        """
        Parse environment variable value to appropriate Python type.
        
        Args:
            value: String value from environment variable
            
        Returns:
            Parsed value with appropriate type
        """
        # Boolean values
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Numeric values
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # List values (JSON array format)
        if value.startswith('[') and value.endswith(']'):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # String value
        return value
    
    def _parse_env_list(self, value: Optional[str]) -> Optional[list]:
        """Parse environment variable as JSON list."""
        if not value:
            return None
        
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None
    
    def _parse_env_bool(self, value: Optional[str]) -> Optional[bool]:
        """Parse environment variable as boolean."""
        if not value:
            return None
        
        return value.lower() == 'true'


# Singleton instances for each service
_config_instances = {}


def get_config(service_name: str, config_dir: Optional[str] = None) -> ConfigLoader:
    """
    Get or create a configuration loader instance.
    
    Args:
        service_name: Name of the service
        config_dir: Directory containing config.json
        
    Returns:
        ConfigLoader instance
    """
    if service_name not in _config_instances:
        _config_instances[service_name] = ConfigLoader(service_name, config_dir)
    
    return _config_instances[service_name]