"""
Global pytest configuration and fixtures.

Provides common test fixtures and configuration for all test types
across the microservices project.
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
from typing import Generator, AsyncGenerator, Dict, Any
from unittest.mock import Mock

# Test environment setup
os.environ["ENVIRONMENT"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"

# Import shared components for testing
from services.shared.auth import JWTHandler
from services.shared.cache import RedisClient
from services.shared.database import DatabaseManager
from services.shared.observability import setup_logging, MetricsCollector
from services.shared.config import get_config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_settings():
    """
    Test settings configuration using new config system.
    
    Returns:
        Test configuration object with safe defaults
    """
    # Create temporary database for testing
    temp_dir = tempfile.mkdtemp()
    test_db_path = os.path.join(temp_dir, "test.db")
    
    # Override environment variables for testing
    test_env = {
        "ENVIRONMENT": "testing",
        "DEBUG": "true",
        "AUTH_DATABASE_URL": f"sqlite:///{test_db_path}",
        "GATEWAY_DATABASE_URL": f"sqlite:///{test_db_path}",
        "AUTH_REDIS_URL": "redis://localhost:6379/15",  # Use test database
        "GATEWAY_REDIS_URL": "redis://localhost:6379/14",
        "JWT_SECRET_KEY": "test-secret-key-for-testing-only-32chars",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "5",  # Short expiry for tests
        "LOG_LEVEL": "DEBUG",
        "ENABLE_METRICS": "false",
        "ENABLE_TRACING": "false",
        "AUTH_SERVICE_HOST": "127.0.0.1",
        "AUTH_SERVICE_PORT": "8001",
        "GATEWAY_HOST": "127.0.0.1",
        "GATEWAY_PORT": "8000"
    }
    
    # Temporarily set environment variables
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        # Create a simple test settings object
        class TestSettings:
            def __init__(self):
                self.host = "127.0.0.1"
                self.port = 8000
                self.database_url = test_env["AUTH_DATABASE_URL"]
                self.redis_url = test_env["AUTH_REDIS_URL"]
                self.jwt_secret_key = test_env["JWT_SECRET_KEY"]
                self.jwt_algorithm = "HS256"
                self.access_token_expire_minutes = 5
        
        settings = TestSettings()
        yield settings
    finally:
        # Restore original environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


@pytest.fixture
def jwt_handler(test_settings) -> JWTHandler:
    """
    JWT handler for testing.
    
    Returns:
        Configured JWT handler instance
    """
    return JWTHandler(
        secret_key=test_settings.jwt_secret_key,
        algorithm=test_settings.jwt_algorithm,
        expire_minutes=test_settings.access_token_expire_minutes
    )


@pytest.fixture
def mock_redis_client() -> Mock:
    """
    Mock Redis client for testing.
    
    Returns:
        Mock Redis client with common methods
    """
    mock_client = Mock(spec=RedisClient)
    
    # Mock common Redis operations
    mock_client.is_available.return_value = True
    mock_client.set.return_value = True
    mock_client.get.return_value = None
    mock_client.delete.return_value = 1
    mock_client.exists.return_value = False
    mock_client.expire.return_value = True
    
    # Mock authentication-specific operations
    mock_client.blacklist_token.return_value = True
    mock_client.is_token_blacklisted.return_value = False
    mock_client.cache_user_session.return_value = True
    mock_client.get_user_session.return_value = None
    mock_client.clear_user_session.return_value = True
    
    # Mock rate limiting
    mock_client.check_rate_limit.return_value = {
        "allowed": True,
        "remaining": 999,
        "reset_time": 3600,
        "current_count": 1
    }
    
    # Mock failed login tracking
    mock_client.track_failed_login.return_value = 1
    mock_client.clear_failed_logins.return_value = True
    mock_client.get_failed_login_count.return_value = 0
    mock_client.lock_account.return_value = True
    mock_client.is_account_locked.return_value = False
    mock_client.unlock_account.return_value = True
    
    return mock_client


@pytest.fixture
def database_manager(test_settings) -> Generator[DatabaseManager, None, None]:
    """
    Test database manager.
    
    Yields:
        Database manager with test database
    """
    manager = DatabaseManager(
        database_url=test_settings.database.url,
        echo=test_settings.database.echo
    )
    
    # Create tables for testing
    manager.create_tables()
    
    yield manager
    
    # Cleanup
    manager.close()


@pytest.fixture
def metrics_collector() -> MetricsCollector:
    """
    Metrics collector for testing.
    
    Returns:
        Metrics collector instance
    """
    return MetricsCollector("test-service")


@pytest.fixture
def sample_user_data() -> Dict[str, Any]:
    """
    Sample user data for testing.
    
    Returns:
        Dictionary with sample user information
    """
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123",
        "is_active": True,
        "is_verified": False
    }


@pytest.fixture
def sample_jwt_payload() -> Dict[str, Any]:
    """
    Sample JWT payload for testing.
    
    Returns:
        Dictionary with sample JWT claims
    """
    return {
        "sub": "test@example.com",
        "username": "testuser",
        "user_id": 1,
        "type": "access_token"
    }


@pytest.fixture
async def test_client():
    """
    Test HTTP client for API testing.
    
    Returns:
        HTTP client for making test requests
    """
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            yield client
    except ImportError:
        pytest.skip("httpx not available for HTTP client testing")


@pytest.fixture
def mock_request():
    """
    Mock FastAPI request object.
    
    Returns:
        Mock request with common attributes
    """
    mock_req = Mock()
    mock_req.method = "GET"
    mock_req.url.path = "/test"
    mock_req.url.query = ""
    mock_req.headers = {}
    mock_req.client.host = "127.0.0.1"
    mock_req.state = Mock()
    mock_req.state.user = None
    mock_req.state.verified_client = False
    
    return mock_req


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """
    Temporary file for testing.
    
    Yields:
        Path to temporary file
    """
    import tempfile
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError:
        pass


@pytest.fixture
def temp_directory() -> Generator[str, None, None]:
    """
    Temporary directory for testing.
    
    Yields:
        Path to temporary directory
    """
    import tempfile
    import shutil
    
    temp_dir = tempfile.mkdtemp()
    
    yield temp_dir
    
    # Cleanup
    try:
        shutil.rmtree(temp_dir)
    except OSError:
        pass


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.e2e = pytest.mark.e2e
pytest.mark.performance = pytest.mark.performance
pytest.mark.security = pytest.mark.security


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")
    config.addinivalue_line("markers", "database: Tests requiring database")


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location."""
    for item in items:
        # Get the test file path relative to the tests directory
        test_path = Path(item.fspath).relative_to(Path(__file__).parent)
        
        # Auto-mark tests based on directory
        if "integration" in test_path.parts:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in test_path.parts:
            item.add_marker(pytest.mark.e2e)
        elif "performance" in test_path.parts:
            item.add_marker(pytest.mark.performance)
        elif "security" in test_path.parts:
            item.add_marker(pytest.mark.security)
        else:
            item.add_marker(pytest.mark.unit)
        
        # Mark tests that require external services
        if "redis" in item.name.lower() or "cache" in item.name.lower():
            item.add_marker(pytest.mark.redis)
        
        if "database" in item.name.lower() or "db" in item.name.lower():
            item.add_marker(pytest.mark.database)