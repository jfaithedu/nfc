"""
exceptions.py - Custom exception definitions for the NFC music player application.

This module defines a hierarchy of custom exceptions for use throughout the application.
"""

class AppError(Exception):
    """Base exception for all application errors."""
    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NetworkError(AppError):
    """Exception raised when network operations fail."""
    pass


class FileOperationError(AppError):
    """Exception raised when file operations fail."""
    pass


class ValidationError(AppError):
    """Exception raised when validation fails."""
    pass


class ConfigurationError(AppError):
    """Exception raised when configuration is invalid."""
    pass


class SystemError(AppError):
    """Exception raised when system operations fail."""
    pass
