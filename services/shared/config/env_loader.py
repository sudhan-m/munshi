"""
Environment variable loading and validation utilities.

Provides utilities for loading environment variables with type conversion,
validation, and default values.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type, TypeVar
from functools import lru_cache

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

logger = logging.getLogger(__name__)

T = TypeVar('T')


def load_environment(
    env_file: Optional[str] = None,
    search_paths: List[str] = None,
    override: bool = False
) -> bool:
    """
    Load environment variables from .env files.
    
    Args:
        env_file: Specific .env file to load
        search_paths: List of directories to search for .env files
        override: Override existing environment variables
        
    Returns:
        True if .env file was loaded, False otherwise
    """
    if not DOTENV_AVAILABLE:
        logger.warning("python-dotenv not available - environment loading skipped")
        return False
    
    search_paths = search_paths or [
        ".",
        "..",
        "../..",
        "/app",
        "/app/config",
        str(Path.home())
    ]
    
    env_files_to_try = []
    
    if env_file:
        # Use specific file
        env_files_to_try.append(env_file)
    else:
        # Search for common .env file names
        env_filenames = [
            ".env",
            ".env.local",
            f".env.{os.getenv('ENVIRONMENT', 'development')}",
            f".env.{os.getenv('ENV', 'development')}"
        ]
        
        for path in search_paths:
            for filename in env_filenames:
                env_path = Path(path) / filename
                if env_path.exists():
                    env_files_to_try.append(str(env_path))
    
    # Load environment files
    loaded = False
    for env_path in env_files_to_try:
        try:
            if Path(env_path).exists():
                load_dotenv(env_path, override=override)
                logger.info(f"Loaded environment from: {env_path}")
                loaded = True
                break
        except Exception as e:
            logger.warning(f"Failed to load {env_path}: {e}")
    
    if not loaded:
        logger.info("No .env file found - using system environment variables only")
    
    return loaded


def get_env_var(
    name: str,
    default: Any = None,
    var_type: Type[T] = str,
    required: bool = False,
    choices: List[Any] = None,
    description: str = None
) -> T:
    """
    Get environment variable with type conversion and validation.
    
    Args:
        name: Environment variable name
        default: Default value if not found
        var_type: Type to convert to (str, int, float, bool, list)
        required: Raise error if not found and no default
        choices: List of valid choices
        description: Description for error messages
        
    Returns:
        Environment variable value converted to specified type
        
    Raises:
        ValueError: If required variable not found or validation fails
    """
    value = os.getenv(name)
    
    if value is None:
        if required and default is None:
            raise ValueError(f"Required environment variable '{name}' not found")
        return default
    
    # Convert to specified type
    try:
        if var_type == bool:
            converted_value = value.lower() in ('true', '1', 'yes', 'on', 'enabled')
        elif var_type == list:
            # Split comma-separated values
            converted_value = [item.strip() for item in value.split(',') if item.strip()]
        elif var_type in (int, float):
            converted_value = var_type(value)
        else:
            converted_value = var_type(value)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert environment variable '{name}' to {var_type.__name__}: {e}")
    
    # Validate choices
    if choices and converted_value not in choices:
        raise ValueError(f"Environment variable '{name}' must be one of {choices}, got: {converted_value}")
    
    return converted_value


def get_database_url(
    service_name: str = "service",
    default_host: str = "localhost",
    default_port: int = 5432,
    default_database: str = None,
    required: bool = True
) -> str:
    """
    Get database URL from environment variables.
    
    Tries to get complete URL first, then builds from components.
    
    Args:
        service_name: Service name for default database name
        default_host: Default database host
        default_port: Default database port
        default_database: Default database name
        required: Whether database URL is required
        
    Returns:
        Database URL string
    """
    # Try complete URL first
    database_url = get_env_var("DATABASE_URL", required=False)
    if database_url:
        return database_url
    
    # Build URL from components
    host = get_env_var("DB_HOST", default_host)
    port = get_env_var("DB_PORT", default_port, int)
    username = get_env_var("DB_USERNAME", get_env_var("DB_USER", "postgres"))
    password = get_env_var("DB_PASSWORD", get_env_var("DB_PASS", ""))
    database = get_env_var("DB_DATABASE", get_env_var("DB_NAME", default_database or f"{service_name}_db"))
    
    if required and not all([host, username, database]):
        raise ValueError("Database connection requires host, username, and database name")
    
    # Build PostgreSQL URL
    if password:
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    else:
        return f"postgresql://{username}@{host}:{port}/{database}"


def get_redis_url(
    default_host: str = "localhost",
    default_port: int = 6379,
    default_db: int = 0,
    required: bool = True
) -> str:
    """
    Get Redis URL from environment variables.
    
    Tries to get complete URL first, then builds from components.
    
    Args:
        default_host: Default Redis host
        default_port: Default Redis port
        default_db: Default Redis database number
        required: Whether Redis URL is required
        
    Returns:
        Redis URL string
    """
    # Try complete URL first
    redis_url = get_env_var("REDIS_URL", required=False)
    if redis_url:
        return redis_url
    
    # Build URL from components
    host = get_env_var("REDIS_HOST", default_host)
    port = get_env_var("REDIS_PORT", default_port, int)
    password = get_env_var("REDIS_PASSWORD", get_env_var("REDIS_PASS", ""))
    db = get_env_var("REDIS_DB", default_db, int)
    
    if required and not host:
        raise ValueError("Redis connection requires host")
    
    # Build Redis URL
    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    else:
        return f"redis://{host}:{port}/{db}"


@lru_cache(maxsize=128)
def get_service_endpoints() -> Dict[str, str]:
    """
    Get service endpoint URLs from environment variables.
    
    Looks for environment variables in the format SERVICE_NAME_URL.
    
    Returns:
        Dictionary mapping service names to URLs
    """
    endpoints = {}
    
    # Common service patterns
    service_patterns = [
        "AUTH_SERVICE_URL",
        "API_GATEWAY_URL", 
        "USER_SERVICE_URL",
        "ORDER_SERVICE_URL",
        "PAYMENT_SERVICE_URL",
        "NOTIFICATION_SERVICE_URL"
    ]
    
    # Check environment for service URLs
    for key, value in os.environ.items():
        if key.endswith("_SERVICE_URL") or key.endswith("_URL"):
            # Extract service name
            if key.endswith("_SERVICE_URL"):
                service_name = key[:-12].lower().replace("_", "-")
            elif key.endswith("_URL"):
                service_name = key[:-4].lower().replace("_", "-")
            else:
                continue
            
            endpoints[service_name] = value
    
    return endpoints


def validate_environment() -> Dict[str, Any]:
    """
    Validate environment configuration and return summary.
    
    Returns:
        Dictionary with validation results
    """
    validation_results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": {}
    }
    
    # Check for required environment variables
    required_vars = [
        ("SERVICE_NAME", "Service name must be set"),
        ("ENVIRONMENT", "Deployment environment must be set")
    ]
    
    for var_name, error_msg in required_vars:
        if not os.getenv(var_name):
            validation_results["errors"].append(f"{var_name}: {error_msg}")
            validation_results["valid"] = False
    
    # Check environment value
    environment = os.getenv("ENVIRONMENT", "").lower()
    if environment and environment not in ["development", "staging", "production", "testing"]:
        validation_results["warnings"].append(f"Unknown environment: {environment}")
    
    # Check for common misconfigurations
    if environment == "production":
        # Production-specific checks
        if os.getenv("DEBUG", "").lower() in ["true", "1", "yes"]:
            validation_results["warnings"].append("DEBUG mode enabled in production")
        
        if not os.getenv("JWT_SECRET_KEY"):
            validation_results["errors"].append("JWT_SECRET_KEY must be set in production")
            validation_results["valid"] = False
    
    # Add environment info
    validation_results["info"] = {
        "environment": environment,
        "service_name": os.getenv("SERVICE_NAME"),
        "debug_mode": os.getenv("DEBUG", "false").lower() in ["true", "1", "yes"],
        "dotenv_available": DOTENV_AVAILABLE
    }
    
    return validation_results


def print_environment_summary():
    """Print a summary of current environment configuration."""
    validation = validate_environment()
    
    print("=" * 50)
    print("ENVIRONMENT CONFIGURATION SUMMARY")
    print("=" * 50)
    
    # Basic info
    info = validation["info"]
    print(f"Service Name: {info.get('service_name', 'NOT SET')}")
    print(f"Environment: {info.get('environment', 'NOT SET')}")
    print(f"Debug Mode: {info.get('debug_mode', False)}")
    print(f"Dotenv Available: {info.get('dotenv_available', False)}")
    
    # Validation results
    if validation["valid"]:
        print("\n✅ Environment validation: PASSED")
    else:
        print("\n❌ Environment validation: FAILED")
    
    # Errors
    if validation["errors"]:
        print("\nERRORS:")
        for error in validation["errors"]:
            print(f"  ❌ {error}")
    
    # Warnings
    if validation["warnings"]:
        print("\nWARNINGS:")
        for warning in validation["warnings"]:
            print(f"  ⚠️  {warning}")
    
    # Service endpoints
    endpoints = get_service_endpoints()
    if endpoints:
        print("\nSERVICE ENDPOINTS:")
        for service, url in endpoints.items():
            print(f"  {service}: {url}")
    
    print("=" * 50)