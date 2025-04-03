"""
NFC-Based Toddler-Friendly Music Player - Authentication Routes

This module implements the API routes for authentication.
"""

from flask import request, jsonify

from ..middleware.auth import verify_pin, generate_token
from ..exceptions import AuthenticationError, InvalidRequestError
from ...utils.logger import get_logger

logger = get_logger(__name__)


def register_routes(app):
    """
    Register authentication-related routes with the Flask application.

    Args:
        app: Flask application instance
    """
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """Authenticate with PIN and generate a JWT token."""
        # Get request data
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'pin' not in data:
            raise InvalidRequestError("PIN is required")
        
        pin = data['pin']
        
        # Verify PIN
        if not verify_pin(pin):
            # Use a generic error message for security
            raise AuthenticationError("Invalid PIN")
        
        # Generate token (default 1 hour expiration)
        token_duration = data.get('duration', 3600)  # seconds
        try:
            token = generate_token(token_duration)
        except Exception as e:
            logger.error(f"Error generating token: {e}")
            raise AuthenticationError("Authentication failed")
        
        # Return token
        return jsonify({
            'success': True,
            'data': {
                'token': token,
                'expires_in': token_duration,
                'token_type': 'Bearer'
            }
        })
    
    logger.info("Authentication routes registered")
