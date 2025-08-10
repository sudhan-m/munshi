# Shared Configuration Module

This module provides a unified configuration loading system for all Munshi microservices.

## Overview

The `ConfigLoader` class combines JSON configuration files with environment variables to provide a flexible, secure, and maintainable configuration system.

## Usage

### Basic Usage
```python
from shared.config.config_loader import get_config

# Get configuration loader for a service
config = get_config("auth-service", "/path/to/service/directory")

# Load configuration values
jwt_algorithm = config.get("security.jwt.algorithm", "HS256", "JWT_ALGORITHM")
```

### Service Configuration Wrapper
```python
from shared.config.config_loader import get_config

class MyServiceSettings:
    def __init__(self):
        self.config = get_config("my-service", os.path.dirname(__file__))
    
    @property
    def database_url(self) -> str:
        return self.config.get_database_url("my")
    
    @property
    def jwt_secret(self) -> str:
        return self.config.get_jwt_config()["secret_key"]
```

## Configuration Priority

1. **Environment Variables** (highest priority)
2. **JSON Configuration Files**
3. **Default Values** (lowest priority)

## Helper Methods

### Infrastructure
- `get_database_url(service_type)` - Database connection URLs
- `get_redis_url(service_type)` - Redis connection URLs  
- `get_host_port()` - Host and port bindings
- `get_environment()` - Deployment environment
- `is_debug()` - Debug mode flag

### Common Configurations
- `get_service_config()` - Service metadata
- `get_jwt_config()` - JWT configuration
- `get_cors_config()` - CORS settings
- `get_rate_limit_config()` - Rate limiting config
- `get_logging_config()` - Logging configuration

### Type Parsing
- Automatically converts environment variables to appropriate Python types
- Supports: `bool`, `int`, `float`, `list` (JSON arrays), `str`

## JSON Configuration Format

```json
{
  "service": {
    "name": "service-name",
    "version": "1.0.0"
  },
  "security": {
    "jwt": {
      "algorithm": "HS256",
      "access_token_expire_minutes": 30
    }
  },
  "features": {
    "enable_feature_x": true
  }
}
```

## Environment Variables

### Required Infrastructure Variables
- `{SERVICE}_DATABASE_URL` - Database connection
- `{SERVICE}_REDIS_URL` - Redis connection
- `{SERVICE}_HOST` - Service host binding
- `{SERVICE}_PORT` - Service port binding

### Common Override Variables
- `ENVIRONMENT` - Deployment environment
- `DEBUG` - Debug mode flag
- `LOG_LEVEL` - Logging level
- `JWT_SECRET_KEY` - JWT signing secret
- `CORS_ORIGINS` - CORS allowed origins (JSON array)

## Examples

### Loading Service Configuration
```python
config = get_config("auth-service")

# Service metadata
service_info = config.get_service_config()
print(f"Running {service_info['name']} v{service_info['version']}")

# Database configuration  
db_url = config.get_database_url("auth")
redis_url = config.get_redis_url("auth")

# JWT configuration (secret from env, settings from JSON)
jwt_config = config.get_jwt_config()
secret = jwt_config["secret_key"]  # From JWT_SECRET_KEY env var
algorithm = jwt_config["algorithm"]  # From JSON config
```

### Environment-Specific Overrides
```python
# Development
export CORS_ORIGINS='["http://localhost:3000","http://localhost:8000"]'
export DEBUG=true

# Production  
export CORS_ORIGINS='["https://yourdomain.com"]'
export DEBUG=false
export REQUIRE_HTTPS=true
```

### Nested Configuration Access
```python
# Access nested JSON values with dot notation
password_rules = {
    "min_length": config.get("security.password.min_length", 8),
    "require_uppercase": config.get("security.password.require_uppercase", True),
    "require_numbers": config.get("security.password.require_numbers", True)
}
```

## Error Handling

The configuration loader handles errors gracefully:
- Missing JSON files log a warning and use defaults
- Invalid JSON logs an error and uses defaults  
- Missing environment variables use JSON config or defaults
- Type conversion errors fall back to string values

## Thread Safety

The `get_config()` function uses a singleton pattern with thread-safe lazy loading. Multiple calls with the same service name return the same instance.

## Testing

```python
import os
from unittest.mock import patch
from shared.config.config_loader import get_config

def test_environment_override():
    with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}):
        config = get_config("test-service")
        jwt_config = config.get_jwt_config()
        assert jwt_config["secret_key"] == "test-secret"
```