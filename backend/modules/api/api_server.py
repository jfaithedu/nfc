"""
NFC-Based Toddler-Friendly Music Player - API Server

This module implements the REST API server for the NFC music player application.
"""

import logging
import threading
import time
from pathlib import Path
import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from waitress import serve

from ..database import db_manager
from ..nfc import nfc_controller
from ..media import media_manager
from ..audio import audio_controller
from backend.config import CONFIG
from backend.utils.logger import get_logger

# Import routes
from .routes import tags, media, system, nfc_writer
from .routes import auth as auth_routes

# Import middleware
from .middleware import auth as auth_middleware
from .middleware import error_handler

logger = get_logger(__name__)

# Flask application instance
app = Flask(__name__, static_folder='static')
api_thread = None
server_running = False
start_time = None
request_count = 0


def initialize():
    """
    Initialize the API server.

    Returns:
        bool: True if initialization successful
    """
    global app

    logger.info("Initializing API server")

    # Set Flask configuration
    app.config.update(
        SECRET_KEY=os.urandom(24),
        JSON_SORT_KEYS=False,
        MAX_CONTENT_LENGTH=100 * 1024 * 1024,  # 100MB max upload size
    )

    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize authentication middleware
    auth_middleware.init_auth(app, CONFIG)

    # Initialize error handlers
    error_handler.init_error_handlers(app)

    # Register route blueprints
    auth_routes.register_routes(app)  # Register auth routes first
    tags.register_routes(app)
    media.register_routes(app)
    system.register_routes(app)
    nfc_writer.register_routes(app)

    # Default route for frontend
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        """Serve the React frontend."""
        if path and Path(app.static_folder, path).exists():
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')

    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'uptime': get_uptime(),
            'version': '0.1.0'
        })

    logger.info("API server initialized")
    return True


def start():
    """
    Start the API server in a separate thread.

    Returns:
        bool: True if server started successfully
    """
    global api_thread, server_running, start_time, app

    if server_running:
        logger.warning("API server already running")
        return True

    logger.info("Starting API server")

    # Create a thread to run the server
    api_thread = threading.Thread(target=_run_server, daemon=True)
    api_thread.start()

    # Set server state
    server_running = True
    start_time = time.time()
    logger.info(f"API server started at {get_server_url()}")
    
    return True


def _run_server():
    """Run the waitress WSGI server."""
    host = CONFIG['api']['host']
    port = CONFIG['api']['port']
    ssl_enabled = CONFIG['api']['ssl_enabled']

    # Log server startup
    logger.info(f"Starting API server on {host}:{port} (SSL: {ssl_enabled})")

    try:
        # Use waitress for production-ready server
        serve(app, host=host, port=port, threads=4)
    except Exception as e:
        logger.error(f"Error running API server: {e}")
        global server_running
        server_running = False


def stop():
    """
    Stop the API server.

    Returns:
        bool: True if server stopped successfully
    """
    global api_thread, server_running

    if not server_running:
        logger.warning("API server not running")
        return True

    logger.info("Stopping API server")

    # Set server state
    server_running = False

    # The thread will end when the process exits as it's a daemon thread
    api_thread = None
    logger.info("API server stopped")
    
    return True


def is_running():
    """
    Check if the API server is running.

    Returns:
        bool: True if server is running
    """
    global server_running
    return server_running


def get_server_url():
    """
    Get the URL where the server is running.

    Returns:
        str: Server URL (e.g., http://localhost:5000)
    """
    if not server_running:
        return None

    host = CONFIG['api']['host']
    port = CONFIG['api']['port']
    ssl_enabled = CONFIG['api']['ssl_enabled']
    
    # Use 'localhost' for user display if server bound to all interfaces
    display_host = 'localhost' if host == '0.0.0.0' else host
    
    protocol = 'https' if ssl_enabled else 'http'
    return f"{protocol}://{display_host}:{port}"


def get_uptime():
    """
    Get the uptime of the API server in seconds.

    Returns:
        float: Uptime in seconds or None if server not running
    """
    if not server_running or start_time is None:
        return None
    return time.time() - start_time


def get_api_status():
    """
    Get the status of the API server.

    Returns:
        dict: Status information including uptime, request count, etc.
    """
    if not server_running:
        return {
            'running': False
        }

    return {
        'running': True,
        'uptime': get_uptime(),
        'uptime_formatted': _format_uptime(get_uptime()),
        'url': get_server_url(),
        'request_count': request_count,
    }


def _format_uptime(seconds):
    """Format uptime in human-readable format."""
    if seconds is None:
        return "Not running"
    
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    
    return " ".join(parts)
