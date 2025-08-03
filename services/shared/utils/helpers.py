"""
Helper utilities for microservices.

Provides common helper functions for ID generation, data masking,
date/time formatting, and other utilities.
"""

import re
import uuid
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID for request tracing.
    
    Returns:
        UUID4 string for correlation tracking
    """
    return str(uuid.uuid4())


def generate_short_id(length: int = 8) -> str:
    """
    Generate a short alphanumeric ID.
    
    Args:
        length: Length of the ID to generate
        
    Returns:
        Short alphanumeric ID
    """
    import random
    import string
    
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def mask_sensitive_data(
    data: Union[str, Dict, List],
    sensitive_keys: List[str] = None,
    mask_char: str = "*",
    show_last: int = 4
) -> Union[str, Dict, List]:
    """
    Mask sensitive data in strings, dictionaries, or lists.
    
    Args:
        data: Data to mask
        sensitive_keys: List of keys to mask in dictionaries
        mask_char: Character to use for masking
        show_last: Number of characters to show at the end
        
    Returns:
        Data with sensitive information masked
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'token', 'secret', 'key', 'credential',
            'authorization', 'auth', 'jwt', 'api_key', 'access_token',
            'refresh_token', 'private_key', 'cert', 'certificate'
        ]
    
    def mask_string(text: str) -> str:
        """Mask a string value."""
        if not text or len(text) <= show_last:
            return mask_char * len(text)
        
        visible_part = text[-show_last:]
        masked_part = mask_char * (len(text) - show_last)
        return masked_part + visible_part
    
    def should_mask_key(key: str) -> bool:
        """Check if a key should be masked."""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in sensitive_keys)
    
    if isinstance(data, str):
        return mask_string(data)
    
    elif isinstance(data, dict):
        masked_dict = {}
        for key, value in data.items():
            if should_mask_key(key):
                if isinstance(value, str):
                    masked_dict[key] = mask_string(value)
                else:
                    masked_dict[key] = mask_char * 8
            else:
                masked_dict[key] = mask_sensitive_data(value, sensitive_keys, mask_char, show_last)
        return masked_dict
    
    elif isinstance(data, list):
        return [mask_sensitive_data(item, sensitive_keys, mask_char, show_last) for item in data]
    
    else:
        return data


def format_datetime(
    dt: datetime,
    format_type: str = "iso",
    timezone_aware: bool = True
) -> str:
    """
    Format datetime object to string.
    
    Args:
        dt: Datetime object to format
        format_type: Format type (iso, human, compact, timestamp)
        timezone_aware: Ensure timezone awareness
        
    Returns:
        Formatted datetime string
    """
    if timezone_aware and dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    if format_type == "iso":
        return dt.isoformat()
    elif format_type == "human":
        return dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    elif format_type == "compact":
        return dt.strftime("%Y%m%d_%H%M%S")
    elif format_type == "timestamp":
        return str(int(dt.timestamp()))
    elif format_type == "date_only":
        return dt.strftime("%Y-%m-%d")
    elif format_type == "time_only":
        return dt.strftime("%H:%M:%S")
    else:
        return dt.isoformat()


def parse_datetime(
    dt_string: str,
    formats: List[str] = None
) -> Optional[datetime]:
    """
    Parse datetime string to datetime object.
    
    Args:
        dt_string: Datetime string to parse
        formats: List of formats to try
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not dt_string:
        return None
    
    if formats is None:
        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",      # ISO with microseconds
            "%Y-%m-%dT%H:%M:%SZ",         # ISO without microseconds
            "%Y-%m-%dT%H:%M:%S.%f%z",     # ISO with timezone
            "%Y-%m-%dT%H:%M:%S%z",        # ISO with timezone, no microseconds
            "%Y-%m-%d %H:%M:%S",          # Common format
            "%Y-%m-%d",                   # Date only
            "%H:%M:%S",                   # Time only (today's date)
        ]
    
    for fmt in formats:
        try:
            if fmt == "%H:%M:%S":
                # For time-only format, use today's date
                time_obj = datetime.strptime(dt_string, fmt).time()
                return datetime.combine(datetime.today().date(), time_obj)
            else:
                return datetime.strptime(dt_string, fmt)
        except ValueError:
            continue
    
    # Try parsing as timestamp
    try:
        timestamp = float(dt_string)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (ValueError, OSError):
        pass
    
    logger.warning(f"Failed to parse datetime string: {dt_string}")
    return None


def parse_duration(duration_string: str) -> Optional[timedelta]:
    """
    Parse duration string to timedelta object.
    
    Supports formats like: "1h", "30m", "45s", "1h30m", "2d", "1w"
    
    Args:
        duration_string: Duration string to parse
        
    Returns:
        Timedelta object or None if parsing fails
    """
    if not duration_string or not isinstance(duration_string, str):
        return None
    
    # Pattern to match duration components
    pattern = r'(\d+)([dhmsw])'
    matches = re.findall(pattern, duration_string.lower())
    
    if not matches:
        return None
    
    total_seconds = 0
    
    for value, unit in matches:
        try:
            value = int(value)
            if unit == 's':
                total_seconds += value
            elif unit == 'm':
                total_seconds += value * 60
            elif unit == 'h':
                total_seconds += value * 3600
            elif unit == 'd':
                total_seconds += value * 86400
            elif unit == 'w':
                total_seconds += value * 604800
        except ValueError:
            return None
    
    return timedelta(seconds=total_seconds)


def format_file_size(size_bytes: int, decimal_places: int = 2) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: File size in bytes
        decimal_places: Number of decimal places
        
    Returns:
        Human-readable file size string
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.{decimal_places}f} {units[unit_index]}"


def generate_hash(
    data: Union[str, bytes, Dict],
    algorithm: str = "sha256",
    encoding: str = "utf-8"
) -> str:
    """
    Generate hash of data.
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
        encoding: String encoding for conversion
        
    Returns:
        Hex digest of hash
    """
    # Convert data to bytes
    if isinstance(data, str):
        data_bytes = data.encode(encoding)
    elif isinstance(data, dict):
        data_bytes = json.dumps(data, sort_keys=True).encode(encoding)
    elif isinstance(data, bytes):
        data_bytes = data
    else:
        data_bytes = str(data).encode(encoding)
    
    # Create hash object
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(data_bytes)
    
    return hash_obj.hexdigest()


def extract_domain_from_url(url: str) -> Optional[str]:
    """
    Extract domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name or None if invalid URL
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return None


def extract_domain_from_email(email: str) -> Optional[str]:
    """
    Extract domain from email address.
    
    Args:
        email: Email address
        
    Returns:
        Domain name or None if invalid email
    """
    try:
        return email.split('@')[1].lower()
    except (IndexError, AttributeError):
        return None


def truncate_string(
    text: str,
    max_length: int,
    suffix: str = "...",
    word_boundary: bool = True
) -> str:
    """
    Truncate string to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncating
        word_boundary: Try to break at word boundaries
        
    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text
    
    if len(suffix) >= max_length:
        return text[:max_length]
    
    truncated_length = max_length - len(suffix)
    
    if word_boundary:
        # Try to break at word boundary
        words = text[:truncated_length].split()
        if words:
            truncated = ' '.join(words[:-1])  # Remove last potentially partial word
            if len(truncated) >= max_length * 0.7:  # Only if we keep most of the text
                return truncated + suffix
    
    return text[:truncated_length] + suffix


def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(
    data: Dict,
    separator: str = ".",
    prefix: str = ""
) -> Dict:
    """
    Flatten nested dictionary.
    
    Args:
        data: Dictionary to flatten
        separator: Separator for nested keys
        prefix: Prefix for keys
        
    Returns:
        Flattened dictionary
    """
    result = {}
    
    for key, value in data.items():
        new_key = f"{prefix}{separator}{key}" if prefix else key
        
        if isinstance(value, dict):
            result.update(flatten_dict(value, separator, new_key))
        else:
            result[new_key] = value
    
    return result


def retry_on_exception(
    func,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator for functions that might fail.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Initial delay between attempts
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exceptions to catch and retry
        
    Returns:
        Decorated function
    """
    def wrapper(*args, **kwargs):
        import time
        
        last_exception = None
        current_delay = delay
        
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                
                if attempt < max_attempts - 1:
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {current_delay}s: {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff_factor
                else:
                    logger.error(f"All {max_attempts} attempts failed")
        
        raise last_exception
    
    return wrapper


def safe_json_loads(json_string: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with fallback.
    
    Args:
        json_string: JSON string to parse
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    if not json_string:
        return default
    
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(data: Any, default: str = "{}") -> str:
    """
    Safely serialize data to JSON with fallback.
    
    Args:
        data: Data to serialize
        default: Default JSON string if serialization fails
        
    Returns:
        JSON string or default value
    """
    try:
        return json.dumps(data, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return default