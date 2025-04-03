"""
validators.py - Input validation utilities for the NFC music player application.

This module provides validation functions for various types of input data.
"""

import re
import urllib.parse
from typing import Optional

from .exceptions import ValidationError


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.

    Args:
        url (str): URL to validate

    Returns:
        bool: True if valid URL
    """
    try:
        result = urllib.parse.urlparse(url)
        # Check for scheme and netloc
        return all([result.scheme, result.netloc])
    except:
        return False


def is_valid_youtube_url(url: str) -> bool:
    """
    Check if a string is a valid YouTube URL.

    Args:
        url (str): URL to validate

    Returns:
        bool: True if valid YouTube URL
    """
    # First check if it's a valid URL
    if not is_valid_url(url):
        return False
    
    # YouTube URL patterns
    youtube_patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',  # Standard watch URL
        r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+',     # Embed URL
        r'^https?://(?:www\.)?youtube\.com/v/[\w-]+',         # Old embed URL
        r'^https?://(?:www\.)?youtube\.com/shorts/[\w-]+',    # YouTube Shorts
        r'^https?://youtu\.be/[\w-]+'                         # Short URL
    ]
    
    # Check if the URL matches any of the YouTube patterns
    for pattern in youtube_patterns:
        if re.match(pattern, url):
            return True
            
    return False


def is_valid_nfc_uid(uid: str) -> bool:
    """
    Check if a string is a valid NFC tag UID.

    Args:
        uid (str): UID to validate

    Returns:
        bool: True if valid UID
    """
    # NFC UIDs are typically hex strings
    # The length depends on the tag type (4, 7, or 10 bytes)
    # We'll accept 8, 14, or 20 hex characters
    
    if not uid:
        return False
        
    # Remove colons, spaces, or dots if present (common separators)
    cleaned_uid = re.sub(r'[:\s\.]', '', uid).upper()
    
    # Check if it's a valid hex string of the appropriate length
    return bool(re.match(r'^[0-9A-F]{8}$|^[0-9A-F]{14}$|^[0-9A-F]{20}$', cleaned_uid))


def is_valid_media_id(media_id: str) -> bool:
    """
    Check if a string is a valid media ID.

    Args:
        media_id (str): Media ID to validate

    Returns:
        bool: True if valid media ID
    """
    # Assuming media IDs are alphanumeric strings with dashes, underscores
    # and have a minimum length of 3 and a maximum of 64 characters
    if not media_id:
        return False
        
    return bool(re.match(r'^[a-zA-Z0-9_-]{3,64}$', media_id))


def sanitize_input(input_str: str, allowed_chars: Optional[str] = None) -> str:
    """
    Sanitize a string by removing potentially harmful characters.

    Args:
        input_str (str): Input string
        allowed_chars (str, optional): String of allowed characters

    Returns:
        str: Sanitized string
    """
    if not input_str:
        return ""
    
    if allowed_chars:
        # Only keep allowed characters
        return ''.join(c for c in input_str if c in allowed_chars)
    else:
        # First remove HTML tags
        no_tags = re.sub(r'<[^>]*>', '', input_str)
        
        # Then remove control characters and common dangerous characters
        # Keep alphanumeric, spaces, and basic punctuation
        return re.sub(r'[^\w\s.,;:!?@#$%^&*()-_+=[\]{}|~`\'"]', '', no_tags)


def validate_required(value, field_name: str):
    """
    Validate that a required value is not None or empty.

    Args:
        value: Value to validate
        field_name (str): Name of the field for error message

    Raises:
        ValidationError: If value is None or empty
    """
    if value is None or (isinstance(value, (str, list, dict)) and not value):
        raise ValidationError(f"{field_name} is required")
        
    return value


def validate_length(value: str, field_name: str, min_length: int = 0, max_length: Optional[int] = None):
    """
    Validate string length.

    Args:
        value (str): String to validate
        field_name (str): Name of the field for error message
        min_length (int, optional): Minimum length required
        max_length (int, optional): Maximum length allowed

    Raises:
        ValidationError: If string length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
        
    if min_length > 0 and len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters")
        
    if max_length and len(value) > max_length:
        raise ValidationError(f"{field_name} cannot exceed {max_length} characters")
        
    return value
