"""
NFC-Based Toddler-Friendly Music Player - API Exceptions

This module defines custom exceptions for the API module.
"""


class APIError(Exception):
    """Base exception for all API related errors."""
    status_code = 500

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """Convert exception to dictionary for JSON response."""
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = self.status_code
        return rv


class AuthenticationError(APIError):
    """Exception raised when authentication fails."""
    status_code = 401


class InvalidRequestError(APIError):
    """Exception raised when the request is invalid."""
    status_code = 400


class ResourceNotFoundError(APIError):
    """Exception raised when a requested resource is not found."""
    status_code = 404


class TagWriteError(APIError):
    """Exception raised when tag writing fails."""
    status_code = 500
