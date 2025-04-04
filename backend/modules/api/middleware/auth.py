"""
NFC-Based Toddler-Friendly Music Player - Authentication Middleware

This module provides authentication for the API server.
"""

import datetime
import functools
import logging
from flask import request, jsonify, current_app
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

from backend.utils.logger import get_logger
from ..exceptions import AuthenticationError

logger = get_logger(__name__)
SECRET_KEY = None
ADMIN_PIN_HASH = None


def init_auth(app, config):
    """
    Initialize authentication middleware.

    Args:
        app: Flask application instance
        config: Configuration object
    """
    global SECRET_KEY, ADMIN_PIN_HASH
    # Use app's secret key for JWT
    SECRET_KEY = app.config['SECRET_KEY']
    
    # Hash the admin PIN if not already hashed (first run)
    admin_pin = config['api']['admin_pin']
    ADMIN_PIN_HASH = generate_password_hash(admin_pin)
    
    logger.info("Authentication middleware initialized")


def require_auth(f):
    """
    Decorator to require authentication for a route.

    Args:
        f: Function to decorate

    Returns:
        decorated function
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': {
                    'message': 'Authentication required',
                    'status': 401
                }
            }), 401
        
        token = auth_header.split(' ')[1]
        payload = check_token(token)
        
        if not payload:
            return jsonify({
                'success': False,
                'error': {
                    'message': 'Invalid or expired token',
                    'status': 401
                }
            }), 401
        
        # Attach token payload to request for use in route handlers
        request.auth = payload
        return f(*args, **kwargs)
    
    return decorated


def verify_pin(pin):
    """
    Verify if a PIN is valid.

    Args:
        pin (str): PIN to verify

    Returns:
        bool: True if PIN is valid
    """
    if not pin or not ADMIN_PIN_HASH:
        return False
    
    return check_password_hash(ADMIN_PIN_HASH, pin)


def check_token(token):
    """
    Verify if a token is valid.

    Args:
        token (str): JWT token to check

    Returns:
        dict: Token payload if valid, None otherwise
    """
    if not token or not SECRET_KEY:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None


def generate_token(duration=3600):
    """
    Generate a new JWT token.

    Args:
        duration (int, optional): Token validity in seconds

    Returns:
        str: JWT token
    """
    if not SECRET_KEY:
        raise AuthenticationError("Authentication not initialized")
    
    now = datetime.datetime.utcnow()
    payload = {
        'iat': now,
        'exp': now + datetime.timedelta(seconds=duration),
        'role': 'admin'
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    # jwt.encode can return bytes or str depending on version
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token
