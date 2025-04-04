"""
NFC-Based Toddler-Friendly Music Player - Error Handler Middleware

This module provides error handling for the API server.
"""

import traceback
from flask import jsonify, request
from werkzeug.exceptions import NotFound, BadRequest, Unauthorized, InternalServerError

from ....utils.logger import get_logger
from ..exceptions import APIError

logger = get_logger(__name__)


def init_error_handlers(app):
    """
    Initialize error handlers for the Flask application.

    Args:
        app: Flask application instance
    """
    # Register error handlers for common HTTP errors
    app.register_error_handler(400, handle_bad_request)
    app.register_error_handler(401, handle_unauthorized)
    app.register_error_handler(404, handle_not_found)
    app.register_error_handler(500, handle_internal_error)
    
    # Register handler for custom API errors
    app.register_error_handler(APIError, handle_api_error)
    
    logger.info("Error handlers initialized")


def handle_not_found(error):
    """
    Handle 404 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """
    return api_error_response(
        f"Resource not found: {request.path}",
        404
    )


def handle_bad_request(error):
    """
    Handle 400 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """
    return api_error_response(
        str(error) or "Bad request",
        400
    )


def handle_unauthorized(error):
    """
    Handle 401 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """
    return api_error_response(
        str(error) or "Unauthorized",
        401
    )


def handle_internal_error(error):
    """
    Handle 500 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """
    # Log the full traceback for server-side debugging
    logger.error(f"Internal server error: {error}")
    logger.error(traceback.format_exc())
    
    # Return generic error to client
    return api_error_response(
        "An internal server error occurred",
        500
    )


def handle_api_error(error):
    """
    Handle custom API errors.

    Args:
        error: APIError instance

    Returns:
        Response: JSON error response
    """
    return api_error_response(
        error.message,
        error.status_code,
        error.payload
    )


def api_error_response(message, status_code, details=None):
    """
    Create a standardized error response.

    Args:
        message (str): Error message
        status_code (int): HTTP status code
        details (dict, optional): Additional error details

    Returns:
        tuple: (JSON response, status code)
    """
    response = {
        'success': False,
        'error': {
            'message': message,
            'status': status_code
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return jsonify(response), status_code
