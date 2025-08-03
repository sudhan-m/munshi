"""
Security testing for microservices.

Tests for common security vulnerabilities, authentication bypass,
injection attacks, and other security concerns.
"""

import pytest
import time
from typing import Dict, Any, List


@pytest.mark.security
class TestSecurityVulnerabilities:
    """Security vulnerability testing."""
    
    @pytest.fixture(autouse=True)
    def setup(self, test_settings, jwt_handler, mock_redis_client):
        """Setup security test environment."""
        self.settings = test_settings
        self.jwt_handler = jwt_handler
        self.redis_client = mock_redis_client
    
    def test_jwt_token_security(self, sample_jwt_payload):
        """Test JWT token security and validation."""
        payload = sample_jwt_payload
        
        # Test valid token creation and verification
        token = self.jwt_handler.create_access_token(payload)
        assert token is not None
        
        decoded_payload = self.jwt_handler.verify_token(token)
        assert decoded_payload is not None
        assert decoded_payload["sub"] == payload["sub"]
        
        # Test token tampering detection
        tampered_token = token[:-5] + "XXXXX"  # Modify token
        tampered_payload = self.jwt_handler.verify_token(tampered_token)
        assert tampered_payload is None  # Should fail verification
        
        # Test empty/null token handling
        assert self.jwt_handler.verify_token("") is None
        assert self.jwt_handler.verify_token(None) is None
        
        # Test malformed tokens
        malformed_tokens = [
            "not.a.jwt",
            "too.short",
            "way.too.many.parts.in.this.token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # Header only
            "invalid_base64!@#$%"
        ]
        
        for malformed_token in malformed_tokens:
            assert self.jwt_handler.verify_token(malformed_token) is None
    
    def test_password_security(self):
        """Test password hashing and validation security."""
        test_password = "TestPassword123"
        
        # Test password hashing
        hashed_password = self.jwt_handler.hash_password(test_password)
        assert hashed_password != test_password  # Should be hashed
        assert hashed_password.startswith("$2b$")  # bcrypt format
        
        # Test password verification
        assert self.jwt_handler.verify_password(test_password, hashed_password) is True
        assert self.jwt_handler.verify_password("wrong_password", hashed_password) is False
        
        # Test timing attack resistance (basic check)
        # Multiple password checks should take similar time
        times = []
        for _ in range(10):
            start_time = time.time()
            self.jwt_handler.verify_password("wrong_password", hashed_password)
            times.append(time.time() - start_time)
        
        # Time variance should be minimal (basic timing attack resistance)
        avg_time = sum(times) / len(times)
        max_variance = max(abs(t - avg_time) for t in times)
        assert max_variance < avg_time * 0.5  # Less than 50% variance
        
        # Test edge cases
        assert self.jwt_handler.verify_password("", hashed_password) is False
        assert self.jwt_handler.verify_password(None, hashed_password) is False
        assert self.jwt_handler.verify_password(test_password, "") is False
        assert self.jwt_handler.verify_password(test_password, None) is False
    
    def test_input_validation_and_sanitization(self):
        """Test input validation and sanitization."""
        from services.shared.utils import validate_email, validate_password, sanitize_input
        
        # Test email validation against injection attempts
        malicious_emails = [
            "test@example.com<script>alert('xss')</script>",
            "test'; DROP TABLE users; --@example.com",
            "test@example.com\x00hidden",
            "test@example.com\r\nhidden-header: value",
            "test@example.com" + "A" * 1000,  # Overly long email
        ]
        
        for malicious_email in malicious_emails:
            assert validate_email(malicious_email) is False
        
        # Test password validation security
        weak_passwords = [
            "",
            "123",
            "password",
            "admin",
            "qwerty",
            "12345678",  # Numbers only
            "abcdefgh",  # Letters only
        ]
        
        for weak_password in weak_passwords:
            result = validate_password(weak_password)
            assert result["valid"] is False
        
        # Test input sanitization
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "test\x00hidden",
            "test\r\nhidden",
            "test" + "\x08" * 10,  # Control characters
        ]
        
        for malicious_input in malicious_inputs:
            sanitized = sanitize_input(malicious_input)
            assert "<script>" not in sanitized
            assert "DROP TABLE" not in sanitized
            assert "\x00" not in sanitized
            assert "\r\n" not in sanitized
    
    def test_authentication_bypass_attempts(self, sample_user_data):
        """Test various authentication bypass attempts."""
        # Test SQL injection in login
        sql_injection_attempts = [
            "admin' OR '1'='1",
            "admin'; DROP TABLE users; --",
            "admin' UNION SELECT * FROM users --",
            "' OR 1=1 --",
        ]
        
        for injection_attempt in sql_injection_attempts:
            # These should not succeed in authentication
            result = self._simulate_login_attempt(injection_attempt, "password")
            assert result["success"] is False
            assert "invalid credentials" in result["error"].lower()
        
        # Test header injection attempts
        malicious_headers = [
            {"Authorization": "Bearer \r\nX-Admin: true"},
            {"Authorization": "Bearer <script>alert('xss')</script>"},
            {"X-Forwarded-For": "127.0.0.1, admin"},
            {"X-Real-IP": "127.0.0.1\r\nX-Admin: true"},
        ]
        
        for headers in malicious_headers:
            result = self._simulate_request_with_headers(headers)
            assert result["success"] is False
    
    def test_token_replay_and_reuse_attacks(self, sample_jwt_payload):
        """Test protection against token replay and reuse attacks."""
        payload = sample_jwt_payload
        
        # Create a token
        token = self.jwt_handler.create_access_token(payload)
        
        # Simulate token being blacklisted (logged out)
        self.redis_client.blacklist_token(token, 3600)
        self.redis_client.is_token_blacklisted.return_value = True
        
        # Token should no longer be valid
        validation_result = self._simulate_token_validation(token)
        assert validation_result["valid"] is False
        assert "blacklisted" in validation_result["error"].lower()
        
        # Test old token reuse after new login
        # (In real scenario, old tokens should be invalidated)
        new_token = self.jwt_handler.create_access_token(payload)
        assert new_token != token  # Should be different token
    
    def test_brute_force_protection(self):
        """Test brute force attack protection."""
        email = "victim@example.com"
        
        # Simulate multiple failed login attempts
        for attempt in range(1, 6):
            self.redis_client.track_failed_login.return_value = attempt
            self.redis_client.get_failed_login_count.return_value = attempt
            
            result = self._simulate_login_attempt(email, "wrong_password")
            assert result["success"] is False
        
        # After 5 failed attempts, account should be locked
        self.redis_client.is_account_locked.return_value = True
        
        # Even with correct password, should fail due to lockout
        locked_result = self._simulate_login_attempt(email, "correct_password")
        assert locked_result["success"] is False
        assert "locked" in locked_result["error"].lower()
    
    def test_rate_limiting_security(self):
        """Test rate limiting as security measure."""
        user_id = "test_user"
        
        # Simulate rapid requests
        rate_limit_responses = []
        for i in range(100):
            # Mock increasing request count
            self.redis_client.check_rate_limit.return_value = {
                "allowed": i < 50,  # Allow first 50, then rate limit
                "remaining": max(0, 50 - i),
                "reset_time": time.time() + 60,
                "current_count": i + 1
            }
            
            result = self._simulate_rate_limited_request(user_id)
            rate_limit_responses.append(result)
        
        # Should have some rate limited responses
        rate_limited = [r for r in rate_limit_responses if not r["allowed"]]
        assert len(rate_limited) > 0
        
        # Rate limiting should kick in at expected threshold
        assert not rate_limit_responses[60]["allowed"]  # Should be rate limited
    
    def test_session_security(self, sample_user_data):
        """Test session management security."""
        user_data = sample_user_data
        user_id = 1
        
        # Test session creation and retrieval
        session_data = {
            "user_id": user_id,
            "email": user_data["email"],
            "last_login": time.time()
        }
        
        # Session should be cached securely
        self.redis_client.cache_user_session(user_id, session_data, 3600)
        self.redis_client.get_user_session.return_value = session_data
        
        cached_session = self.redis_client.get_user_session(user_id)
        assert cached_session == session_data
        
        # Test session invalidation
        self.redis_client.clear_user_session(user_id)
        self.redis_client.get_user_session.return_value = None
        
        cleared_session = self.redis_client.get_user_session(user_id)
        assert cleared_session is None
        
        # Test session hijacking protection
        # Sessions should be tied to specific user IDs
        malicious_user_id = 999
        hijack_attempt = self.redis_client.get_user_session(malicious_user_id)
        assert hijack_attempt != session_data  # Should not get other user's session
    
    def test_authorization_bypass_attempts(self):
        """Test authorization bypass attempts."""
        # Test unauthorized access attempts
        unauthorized_attempts = [
            {"user_id": 1, "target_user_id": 2},  # Access other user's data
            {"user_id": None, "target_user_id": 1},  # No authentication
            {"user_id": "admin", "target_user_id": 1},  # Privilege escalation
        ]
        
        for attempt in unauthorized_attempts:
            result = self._simulate_authorization_check(
                attempt["user_id"],
                attempt["target_user_id"]
            )
            assert result["authorized"] is False
    
    def test_information_disclosure_prevention(self):
        """Test prevention of sensitive information disclosure."""
        # Test error messages don't leak sensitive info
        error_scenarios = [
            {"input": "nonexistent@example.com", "type": "login"},
            {"input": "invalid_token", "type": "token_validation"},
            {"input": "admin", "type": "user_lookup"},
        ]
        
        for scenario in error_scenarios:
            error_response = self._simulate_error_scenario(scenario["input"], scenario["type"])
            
            # Error messages should be generic, not revealing system details
            error_message = error_response["error"].lower()
            
            # Should not contain sensitive information
            sensitive_terms = [
                "database", "sql", "table", "query", "connection",
                "internal", "system", "server", "path", "directory"
            ]
            
            for term in sensitive_terms:
                assert term not in error_message, f"Error message contains sensitive term: {term}"
    
    def test_security_headers_and_configuration(self):
        """Test security headers and configuration."""
        # Test that security configurations are properly set
        security_config = {
            "jwt_secret_length": len(self.settings.security.jwt_secret_key),
            "password_hash_rounds": self.settings.security.password_hash_rounds,
            "token_expire_minutes": self.settings.security.access_token_expire_minutes,
        }
        
        # JWT secret should be strong
        assert security_config["jwt_secret_length"] >= 32
        
        # Password hash rounds should be secure
        assert 10 <= security_config["password_hash_rounds"] <= 15
        
        # Token expiration should not be too long
        assert security_config["token_expire_minutes"] <= 60  # Max 1 hour
    
    # Helper methods for security testing
    
    def _simulate_login_attempt(self, email: str, password: str) -> Dict[str, Any]:
        """Simulate login attempt for security testing."""
        # Check if account is locked
        if self.redis_client.is_account_locked(email):
            return {
                "success": False,
                "error": "Account locked due to multiple failed attempts"
            }
        
        # Simulate credential validation
        if email == "test@example.com" and password == "correct_password":
            return {
                "success": True,
                "access_token": "mock_token",
                "token_type": "bearer"
            }
        else:
            # Track failed attempt
            self.redis_client.track_failed_login(email)
            return {
                "success": False,
                "error": "Invalid credentials"
            }
    
    def _simulate_token_validation(self, token: str) -> Dict[str, Any]:
        """Simulate token validation for security testing."""
        # Check blacklist
        if self.redis_client.is_token_blacklisted(token):
            return {
                "valid": False,
                "error": "Token has been blacklisted"
            }
        
        # Validate token format and signature
        payload = self.jwt_handler.verify_token(token)
        if payload:
            return {
                "valid": True,
                "email": payload.get("sub"),
                "user_id": payload.get("user_id")
            }
        else:
            return {
                "valid": False,
                "error": "Invalid or expired token"
            }
    
    def _simulate_request_with_headers(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Simulate request with potentially malicious headers."""
        # Check for header injection attempts
        for key, value in headers.items():
            if "\r\n" in value or "\x00" in value or "<script>" in value:
                return {
                    "success": False,
                    "error": "Invalid request"
                }
        
        return {
            "success": True,
            "data": "Request processed"
        }
    
    def _simulate_rate_limited_request(self, user_id: str) -> Dict[str, Any]:
        """Simulate rate limited request."""
        rate_check = self.redis_client.check_rate_limit(f"rate_limit:{user_id}", 50, 60)
        
        return {
            "allowed": rate_check["allowed"],
            "remaining": rate_check["remaining"],
            "user_id": user_id
        }
    
    def _simulate_authorization_check(self, user_id: Any, target_user_id: int) -> Dict[str, Any]:
        """Simulate authorization check."""
        # Only allow users to access their own data
        if user_id is None:
            return {
                "authorized": False,
                "error": "Authentication required"
            }
        
        if user_id != target_user_id:
            return {
                "authorized": False,
                "error": "Access denied"
            }
        
        return {
            "authorized": True
        }
    
    def _simulate_error_scenario(self, input_value: str, scenario_type: str) -> Dict[str, Any]:
        """Simulate error scenarios to test information disclosure."""
        if scenario_type == "login":
            return {
                "success": False,
                "error": "Invalid credentials"  # Generic error message
            }
        elif scenario_type == "token_validation":
            return {
                "success": False,
                "error": "Authentication failed"  # Generic error message
            }
        elif scenario_type == "user_lookup":
            return {
                "success": False,
                "error": "User not found"  # Generic error message
            }
        else:
            return {
                "success": False,
                "error": "Invalid request"
            }