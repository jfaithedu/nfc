"""
exceptions.py - Media-specific exception definitions for the NFC music player.

This module defines the exception hierarchy for the media module.
"""


class MediaError(Exception):
    """Base exception for all media related errors."""
    pass


class MediaPreparationError(MediaError):
    """Exception raised when media cannot be prepared for playback."""
    pass


class DownloadError(MediaError):
    """Exception raised when media cannot be downloaded."""
    pass


class InvalidURLError(MediaError):
    """Exception raised when URL is invalid."""
    pass


class UnsupportedFormatError(MediaError):
    """Exception raised when media format is not supported."""
    pass


class CacheError(MediaError):
    """Exception raised for cache-related issues."""
    pass


class YouTubeError(MediaError):
    """Base exception for YouTube-related errors."""
    pass


class YouTubeInfoError(YouTubeError):
    """Exception raised when YouTube info cannot be retrieved."""
    pass


class YouTubeDownloadError(YouTubeError):
    """Exception raised when YouTube download fails."""
    pass
