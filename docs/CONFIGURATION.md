# Configuration Architecture

This document explains the new configuration architecture for Munshi microservices, which separates application behavior from infrastructure settings.

## 🎯 Design Principles

### Clear Separation of Concerns
- **JSON Config Files**: Application behavior, business logic, static settings
- **Environment Variables**: Infrastructure, secrets, deployment-specific values

### Configuration Hierarchy
1. **Environment Variables** (highest priority)
2. **JSON Configuration Files** 
3. **Default Values** (lowest priority)

## 📁 Configuration Structure

```
services/
├── auth-service/
│   ├── config.json          # Application behavior & business logic
│   └── config.py            # Configuration loader wrapper
├── api-gateway/
│   ├── config.json          # Application behavior & business logic  
│   └── config.py            # Configuration loader wrapper
└── shared/
    └── config/
        └── config_loader.py  # Unified configuration loader
```

## 📋 JSON Configuration Files

### What Goes in JSON Config
- **Business Logic Settings**: Password rules, rate limits, timeouts
- **Feature Flags**: Enable/disable features
- **Application Behavior**: CORS methods, logging formats
- **Static Configuration**: Service names, versions, algorithms

### Auth Service Config (`services/auth-service/config.json`)
```json
{
  "service": {
    "name": "auth-service",
    "version": "1.0.0"
  },
  "security": {
    "jwt": {
      "algorithm": "HS256",
      "access_token_expire_minutes": 30
    },
    "password": {
      "min_length": 8,
      "require_uppercase": true,
      "require_lowercase": true,
      "require_numbers": true
    }
  },
  "features": {
    "enable_refresh_tokens": true,
    "enable_two_factor_auth": false
  }
}
```

### API Gateway Config (`services/api-gateway/config.json`)
```json
{
  "routing": {
    "service_discovery": {
      "enabled": true,
      "health_check_interval_seconds": 30
    },
    "load_balancing": {
      "strategy": "round_robin",
      "max_retries": 3
    }
  },
  "rate_limiting": {
    "enabled": true,
    "default_requests_per_minute": 1000
  }
}
```

## 🔐 Environment Variables

### What Goes in Environment Variables
- **Secrets**: JWT keys, database passwords
- **Infrastructure URLs**: Database connections, Redis URLs
- **Deployment Settings**: Debug mode, environment type
- **Host/Port Bindings**: Service endpoints

### Environment File Structure
```bash
# .env.example - Template with all possible variables
# .env.development - Development-specific overrides  
# .env.production - Production-specific overrides
```

### Key Environment Variables
```bash
# Deployment
ENVIRONMENT=development
DEBUG=true

# Infrastructure & Secrets
AUTH_DATABASE_URL=postgresql://user:pass@host:port/db
JWT_SECRET_KEY=your-secret-key

# Service URLs
AUTH_SERVICE_URL=http://localhost:8001
API_GATEWAY_URL=http://localhost:8000

# Deployment-specific Overrides
CORS_ORIGINS=["http://localhost:3000"]
LOG_LEVEL=DEBUG
```

## 🔄 Configuration Loading

### ConfigLoader Class
The `ConfigLoader` class in `services/shared/config/config_loader.py` provides:

- **Unified Loading**: Combines JSON + environment variables
- **Type Conversion**: Automatic parsing of env vars to proper types
- **Environment Overrides**: Env vars always take precedence
- **Caching**: Performance optimization for repeated access

### Usage Example
```python
from shared.config.config_loader import get_config

# Get configuration loader
config = get_config("auth-service", "/path/to/service")

# Load values with environment override
jwt_secret = config.get("security.jwt.secret_key", "default", "JWT_SECRET_KEY")
password_length = config.get("security.password.min_length", 8, "PASSWORD_MIN_LENGTH")

# Helper methods for common patterns
database_url = config.get_database_url("auth")
cors_config = config.get_cors_config()
```

### Service Configuration Classes
Each service has a wrapper class that provides property-based access:

```python
from .config import get_auth_settings

settings = get_auth_settings()
print(settings.jwt_secret_key)      # From JWT_SECRET_KEY env var
print(settings.password_min_length)  # From JSON config or PASSWORD_MIN_LENGTH env var
print(settings.service_name)        # From JSON config
```

## 🌍 Environment-Specific Configuration

### Development (`.env.development`)
```bash
ENVIRONMENT=development
DEBUG=true
JWT_SECRET_KEY=dev-secret-not-for-production
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
LOG_LEVEL=DEBUG
```

### Production (`.env.production`)  
```bash
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=${JWT_SECRET_KEY}
CORS_ORIGINS=["https://yourdomain.com"]
REQUIRE_HTTPS=true
LOG_LEVEL=INFO
```

## 🔧 Migration Guide

### From Old Config
**Before** (everything in Python config):
```python
class Settings(BaseSettings):
    jwt_secret_key: str = "hardcoded-secret"
    password_min_length: int = 8
    cors_origins: list = ["http://localhost:3000"]
```

**After** (separated):

**JSON Config** (`config.json`):
```json
{
  "security": {
    "password": {
      "min_length": 8
    }
  }
}
```

**Environment Variables** (`.env`):
```bash
JWT_SECRET_KEY=actual-secret-key
CORS_ORIGINS=["http://localhost:3000"]
```

**Python Config** (`config.py`):
```python
class Settings:
    def __init__(self):
        self.config = get_config("service-name")
    
    @property
    def jwt_secret_key(self) -> str:
        return os.getenv("JWT_SECRET_KEY", "default")
    
    @property  
    def password_min_length(self) -> int:
        return self.config.get("security.password.min_length", 8, "PASSWORD_MIN_LENGTH")
```

## 📚 Best Practices

### 1. Configuration Placement
- **Secrets** → Environment variables only
- **URLs/Hostnames** → Environment variables  
- **Business rules** → JSON config files
- **Feature flags** → JSON config (with env override option)

### 2. Environment Variable Naming
- Use service prefix: `AUTH_DATABASE_URL`, `GATEWAY_REDIS_URL`
- Follow naming convention: `UPPER_SNAKE_CASE`
- Group related vars: `JWT_SECRET_KEY`, `JWT_ALGORITHM`

### 3. JSON Config Organization
- Use nested structure for logical grouping
- Keep related settings together
- Use descriptive names
- Include comments where helpful

### 4. Deployment Strategy
- Use different env files per environment
- Keep secrets in secure secret management systems
- Use environment variable substitution in production
- Validate configuration on startup

### 5. Security Considerations
- Never commit real secrets to version control
- Use `.env.example` as template only
- Rotate secrets regularly
- Use minimal permissions for service accounts

## 🧪 Testing Configuration

### Unit Testing
```python
def test_config_loading():
    # Test with mock environment
    with mock.patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret"}):
        settings = get_auth_settings()
        assert settings.jwt_secret_key == "test-secret"

def test_json_config():
    # Test JSON config loading
    config = get_config("auth-service", "test/fixtures")
    assert config.get("security.password.min_length") == 8
```

### Integration Testing
```bash
# Test different environments
ENV=development python -m pytest tests/
ENV=production python -m pytest tests/
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Configuration Not Found
**Problem**: `KeyError` or `None` values for configuration
**Solution**: 
- Check JSON config file exists and is valid
- Verify environment variable names
- Use default values appropriately

#### 2. Environment Variable Override Not Working
**Problem**: Environment variable ignored
**Solution**:
- Check variable name spelling
- Ensure proper type conversion
- Verify environment variable is set

#### 3. JSON Parsing Errors
**Problem**: `JSONDecodeError` when loading config
**Solution**:
- Validate JSON syntax
- Check for trailing commas
- Use proper JSON formatting tools

### Debug Configuration
```python
# Debug what configuration is loaded
config = get_config("auth-service")
print("Service config:", config.get_service_config())
print("JWT config:", config.get_jwt_config())
print("Environment:", config.get_environment())
```

## 📈 Benefits

### 1. **Separation of Concerns**
- Clear distinction between app logic and infrastructure
- Easier to understand and maintain
- Better security practices

### 2. **Environment Flexibility**
- Same codebase works across all environments
- Easy deployment with different configurations
- No code changes needed for environment differences

### 3. **Security**
- Secrets stay in environment variables
- No hardcoded credentials in code
- Easy secret rotation

### 4. **Maintainability**
- JSON configs are easy to read and modify
- Type safety with Python property decorators
- Centralized configuration loading logic

### 5. **Testing**
- Easy to mock configuration for testing
- Environment-specific test configurations
- Isolated configuration testing