"""
Validation utilities for microservices.

Provides common validation functions for emails, passwords,
UUIDs, and input sanitization.
"""

import re
import uuid
import html
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid email format, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # Check length limits
    if len(email) > 254:  # RFC 5321 limit
        return False
    
    # Split local and domain parts
    try:
        local, domain = email.rsplit('@', 1)
    except ValueError:
        return False
    
    # Check local part length
    if len(local) > 64:  # RFC 5321 limit
        return False
    
    # Check domain part length
    if len(domain) > 253:  # RFC 1035 limit
        return False
    
    # Validate with regex
    return bool(re.match(pattern, email))


def validate_password(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digits: bool = True,
    require_special: bool = False,
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
) -> Dict[str, Any]:
    """
    Validate password strength with detailed feedback.
    
    Args:
        password: Password to validate
        min_length: Minimum password length
        require_uppercase: Require uppercase letters
        require_lowercase: Require lowercase letters
        require_digits: Require digits
        require_special: Require special characters
        special_chars: Valid special characters
        
    Returns:
        Dictionary with validation results and feedback
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "strength_score": 0,
        "suggestions": []
    }
    
    if not password or not isinstance(password, str):
        result["valid"] = False
        result["errors"].append("Password is required")
        return result
    
    # Check minimum length
    if len(password) < min_length:
        result["valid"] = False
        result["errors"].append(f"Password must be at least {min_length} characters long")
    else:
        result["strength_score"] += 1
    
    # Check uppercase requirement
    if require_uppercase:
        if not re.search(r'[A-Z]', password):
            result["valid"] = False
            result["errors"].append("Password must contain at least one uppercase letter")
        else:
            result["strength_score"] += 1
    
    # Check lowercase requirement
    if require_lowercase:
        if not re.search(r'[a-z]', password):
            result["valid"] = False
            result["errors"].append("Password must contain at least one lowercase letter")
        else:
            result["strength_score"] += 1
    
    # Check digits requirement
    if require_digits:
        if not re.search(r'\d', password):
            result["valid"] = False
            result["errors"].append("Password must contain at least one number")
        else:
            result["strength_score"] += 1
    
    # Check special characters requirement
    if require_special:
        if not re.search(f'[{re.escape(special_chars)}]', password):
            result["valid"] = False
            result["errors"].append(f"Password must contain at least one special character ({special_chars})")
        else:
            result["strength_score"] += 1
    
    # Additional strength checks
    if len(password) >= 12:
        result["strength_score"] += 1
    
    if len(set(password)) >= len(password) * 0.7:  # Character diversity
        result["strength_score"] += 1
    
    # Check for common weak patterns
    weak_patterns = [
        (r'(.)\1{2,}', "Avoid repeating characters"),
        (r'(012|123|234|345|456|567|678|789|890)', "Avoid sequential numbers"),
        (r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', "Avoid sequential letters"),
        (r'(qwerty|asdf|zxcv)', "Avoid keyboard patterns")
    ]
    
    for pattern, suggestion in weak_patterns:
        if re.search(pattern, password.lower()):
            result["warnings"].append(suggestion)
            result["strength_score"] -= 0.5
    
    # Common weak passwords (simplified list)
    common_passwords = {
        "password", "123456", "password123", "admin", "letmein",
        "welcome", "monkey", "dragon", "qwerty", "abc123"
    }
    
    if password.lower() in common_passwords:
        result["valid"] = False
        result["errors"].append("Password is too common")
        result["strength_score"] = 0
    
    # Generate suggestions
    if not result["valid"]:
        if len(password) < min_length:
            result["suggestions"].append(f"Use at least {min_length} characters")
        if require_uppercase and not re.search(r'[A-Z]', password):
            result["suggestions"].append("Add uppercase letters")
        if require_lowercase and not re.search(r'[a-z]', password):
            result["suggestions"].append("Add lowercase letters")
        if require_digits and not re.search(r'\d', password):
            result["suggestions"].append("Add numbers")
        if require_special and not re.search(f'[{re.escape(special_chars)}]', password):
            result["suggestions"].append("Add special characters")
    
    # Cap strength score
    result["strength_score"] = max(0, min(result["strength_score"], 5))
    
    return result


def validate_uuid(uuid_string: str, version: Optional[int] = None) -> bool:
    """
    Validate UUID format.
    
    Args:
        uuid_string: UUID string to validate
        version: Optional UUID version to check (1-5)
        
    Returns:
        True if valid UUID, False otherwise
    """
    if not uuid_string or not isinstance(uuid_string, str):
        return False
    
    try:
        uuid_obj = uuid.UUID(uuid_string)
        
        # Check version if specified
        if version is not None:
            if uuid_obj.version != version:
                return False
        
        return True
    except (ValueError, AttributeError):
        return False


def validate_url(url: str, allowed_schemes: List[str] = None) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: http, https)
        
    Returns:
        True if valid URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    allowed_schemes = allowed_schemes or ['http', 'https']
    
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme in allowed_schemes and
            parsed.netloc and
            len(url) <= 2048  # Reasonable URL length limit
        )
    except Exception:
        return False


def validate_phone_number(phone: str, country_code: str = None) -> bool:
    """
    Basic phone number validation.
    
    Args:
        phone: Phone number to validate
        country_code: Optional country code for more specific validation
        
    Returns:
        True if valid phone format, False otherwise
    """
    if not phone or not isinstance(phone, str):
        return False
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\+\.]', '', phone)
    
    # Check if all remaining characters are digits
    if not cleaned.isdigit():
        return False
    
    # Basic length check (international phone numbers are typically 7-15 digits)
    if not 7 <= len(cleaned) <= 15:
        return False
    
    # Country-specific validation could be added here
    # For now, just basic format validation
    
    return True


def sanitize_input(
    text: str,
    max_length: Optional[int] = None,
    allow_html: bool = False,
    strip_whitespace: bool = True
) -> str:
    """
    Sanitize user input to prevent XSS and other attacks.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML (default: escape HTML)
        strip_whitespace: Whether to strip leading/trailing whitespace
        
    Returns:
        Sanitized text
    """
    if not isinstance(text, str):
        return ""
    
    # Strip whitespace if requested
    if strip_whitespace:
        text = text.strip()
    
    # Truncate if max_length specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    # Handle HTML
    if not allow_html:
        text = html.escape(text)
    
    # Remove null bytes and other control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text


def validate_json_schema(data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Basic JSON schema validation.
    
    Args:
        data: Data to validate
        schema: Simple schema definition
        
    Returns:
        Dictionary with validation results
    """
    result = {
        "valid": True,
        "errors": [],
        "warnings": []
    }
    
    try:
        # This is a simplified schema validator
        # In production, you'd want to use jsonschema library
        
        if "type" in schema:
            expected_type = schema["type"]
            if expected_type == "string" and not isinstance(data, str):
                result["valid"] = False
                result["errors"].append(f"Expected string, got {type(data).__name__}")
            elif expected_type == "integer" and not isinstance(data, int):
                result["valid"] = False
                result["errors"].append(f"Expected integer, got {type(data).__name__}")
            elif expected_type == "number" and not isinstance(data, (int, float)):
                result["valid"] = False
                result["errors"].append(f"Expected number, got {type(data).__name__}")
            elif expected_type == "boolean" and not isinstance(data, bool):
                result["valid"] = False
                result["errors"].append(f"Expected boolean, got {type(data).__name__}")
            elif expected_type == "array" and not isinstance(data, list):
                result["valid"] = False
                result["errors"].append(f"Expected array, got {type(data).__name__}")
            elif expected_type == "object" and not isinstance(data, dict):
                result["valid"] = False
                result["errors"].append(f"Expected object, got {type(data).__name__}")
        
        # Check required fields for objects
        if isinstance(data, dict) and "required" in schema:
            for field in schema["required"]:
                if field not in data:
                    result["valid"] = False
                    result["errors"].append(f"Required field '{field}' is missing")
        
        # Check string length
        if isinstance(data, str) and "maxLength" in schema:
            if len(data) > schema["maxLength"]:
                result["valid"] = False
                result["errors"].append(f"String too long (max: {schema['maxLength']})")
        
        if isinstance(data, str) and "minLength" in schema:
            if len(data) < schema["minLength"]:
                result["valid"] = False
                result["errors"].append(f"String too short (min: {schema['minLength']})")
        
    except Exception as e:
        result["valid"] = False
        result["errors"].append(f"Validation error: {str(e)}")
    
    return result


def validate_ip_address(ip: str, version: Optional[int] = None) -> bool:
    """
    Validate IP address format.
    
    Args:
        ip: IP address to validate
        version: IP version (4 or 6), None for either
        
    Returns:
        True if valid IP address, False otherwise
    """
    if not ip or not isinstance(ip, str):
        return False
    
    import ipaddress
    
    try:
        if version == 4:
            ipaddress.IPv4Address(ip)
        elif version == 6:
            ipaddress.IPv6Address(ip)
        else:
            ipaddress.ip_address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


def validate_port_number(port: Any) -> bool:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid port number, False otherwise
    """
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False