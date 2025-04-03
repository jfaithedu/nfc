# API Module - Implementation Guide

## Overview

The API Module is responsible for providing a web-based interface to the NFC music player application. It creates a REST API server that allows the frontend application to manage media assignments, write NFC tags, and control the system. This module secures local-only access to administration features while providing an easy-to-use interface for parents or administrators.

## Core Responsibilities

1. Implement a secure REST API for administration
2. Provide endpoints for managing NFC tags and associations
3. Enable media library management through API
4. Allow control of NFC tag writing
5. Handle system settings and configuration
6. Serve the React frontend application

## Implementation Details

### File Structure

```
api/
├── __init__.py               # Package initialization
├── api_server.py             # Main server controller, exposed to other modules
├── routes/                   # API route handlers
│   ├── __init__.py           # Route initialization
│   ├── tags.py               # Tag management endpoints
│   ├── media.py              # Media management endpoints
│   ├── system.py             # System settings endpoints
│   └── nfc_writer.py         # NFC tag writing endpoints
├── middleware/               # API middleware
│   ├── __init__.py           # Middleware initialization
│   ├── auth.py               # Authentication middleware
│   └── error_handler.py      # Error handling middleware
├── static/                   # Static files for frontend
└── exceptions.py             # API-specific exception definitions
```

### Key Components

#### 1. API Server (`api_server.py`)

This is the main interface exposed to other modules:

```python
def initialize():
    """
    Initialize the API server.

    Returns:
        bool: True if initialization successful
    """

def start():
    """
    Start the API server in a separate thread.

    Returns:
        bool: True if server started successfully
    """

def stop():
    """
    Stop the API server.

    Returns:
        bool: True if server stopped successfully
    """

def is_running():
    """
    Check if the API server is running.

    Returns:
        bool: True if server is running
    """

def get_server_url():
    """
    Get the URL where the server is running.

    Returns:
        str: Server URL (e.g., http://localhost:5000)
    """

def get_api_status():
    """
    Get the status of the API server.

    Returns:
        dict: Status information including uptime, request count, etc.
    """
```

#### 2. Tag Routes (`routes/tags.py`)

API endpoints for NFC tag management:

```python
def register_routes(app):
    """
    Register tag-related routes with the Flask application.

    Args:
        app: Flask application instance
    """

    @app.route('/api/tags', methods=['GET'])
    def get_all_tags():
        """Get all registered NFC tags."""
        # Implementation

    @app.route('/api/tags/<tag_uid>', methods=['GET'])
    def get_tag(tag_uid):
        """Get a specific tag by UID."""
        # Implementation

    @app.route('/api/tags', methods=['POST'])
    def create_tag():
        """Register a new tag."""
        # Implementation

    @app.route('/api/tags/<tag_uid>', methods=['PUT'])
    def update_tag(tag_uid):
        """Update a tag's information."""
        # Implementation

    @app.route('/api/tags/<tag_uid>', methods=['DELETE'])
    def delete_tag(tag_uid):
        """Delete a tag registration."""
        # Implementation

    @app.route('/api/tags/<tag_uid>/associate', methods=['POST'])
    def associate_tag(tag_uid):
        """Associate a tag with media."""
        # Implementation

    @app.route('/api/tags/last-detected', methods=['GET'])
    def get_last_detected_tag():
        """Get information about the most recently detected tag."""
        # Implementation

    @app.route('/api/tags/history', methods=['GET'])
    def get_tag_history():
        """Get tag usage history."""
        # Implementation
```

#### 3. Media Routes (`routes/media.py`)

API endpoints for media management:

```python
def register_routes(app):
    """
    Register media-related routes with the Flask application.

    Args:
        app: Flask application instance
    """

    @app.route('/api/media', methods=['GET'])
    def get_all_media():
        """Get all media entries."""
        # Implementation

    @app.route('/api/media/<media_id>', methods=['GET'])
    def get_media(media_id):
        """Get a specific media entry."""
        # Implementation

    @app.route('/api/media/youtube', methods=['POST'])
    def add_youtube_media():
        """Add a new YouTube media source."""
        # Implementation

    @app.route('/api/media/upload', methods=['POST'])
    def upload_media():
        """Upload a local media file."""
        # Implementation

    @app.route('/api/media/<media_id>', methods=['DELETE'])
    def delete_media(media_id):
        """Delete a media entry."""
        # Implementation

    @app.route('/api/media/<media_id>/test', methods=['POST'])
    def test_playback(media_id):
        """Test playback of a media entry."""
        # Implementation

    @app.route('/api/media/cache/status', methods=['GET'])
    def get_cache_status():
        """Get media cache status."""
        # Implementation

    @app.route('/api/media/cache/clean', methods=['POST'])
    def clean_cache():
        """Clean the media cache."""
        # Implementation
```

#### 4. System Routes (`routes/system.py`)

API endpoints for system settings:

```python
def register_routes(app):
    """
    Register system-related routes with the Flask application.

    Args:
        app: Flask application instance
    """

    @app.route('/api/system/status', methods=['GET'])
    def get_system_status():
        """Get system status."""
        # Implementation

    @app.route('/api/system/bluetooth/devices', methods=['GET'])
    def get_bluetooth_devices():
        """Get available Bluetooth devices."""
        # Implementation

    @app.route('/api/system/bluetooth/connect', methods=['POST'])
    def connect_bluetooth():
        """Connect to a Bluetooth device."""
        # Implementation

    @app.route('/api/system/settings', methods=['GET'])
    def get_settings():
        """Get system settings."""
        # Implementation

    @app.route('/api/system/settings', methods=['PUT'])
    def update_settings():
        """Update system settings."""
        # Implementation

    @app.route('/api/system/backup', methods=['POST'])
    def create_backup():
        """Create a system backup."""
        # Implementation

    @app.route('/api/system/restore', methods=['POST'])
    def restore_backup():
        """Restore from a backup."""
        # Implementation

    @app.route('/api/system/restart', methods=['POST'])
    def restart_system():
        """Restart the NFC player service."""
        # Implementation
```

#### 5. NFC Writer Routes (`routes/nfc_writer.py`)

API endpoints for NFC tag writing:

```python
def register_routes(app):
    """
    Register NFC writer routes with the Flask application.

    Args:
        app: Flask application instance
    """

    @app.route('/api/nfc/write/start', methods=['POST'])
    def start_write_mode():
        """Start NFC tag writing mode."""
        # Implementation

    @app.route('/api/nfc/write/stop', methods=['POST'])
    def stop_write_mode():
        """Stop NFC tag writing mode."""
        # Implementation

    @app.route('/api/nfc/write/status', methods=['GET'])
    def get_write_status():
        """Get the status of write mode."""
        # Implementation

    @app.route('/api/nfc/write/<tag_uid>', methods=['POST'])
    def write_tag(tag_uid):
        """Write data to a specific tag."""
        # Implementation

    @app.route('/api/nfc/read', methods=['GET'])
    def read_tag_data():
        """Read raw data from a detected tag."""
        # Implementation

    @app.route('/api/nfc/ndef/read', methods=['GET'])
    def read_ndef_data():
        """Read and parse NDEF formatted data from a detected tag."""
        # Implementation

    @app.route('/api/nfc/ndef/write', methods=['POST'])
    def write_ndef_data():
        """Write NDEF formatted data to a detected tag.

        Request body should include either url or text or both:
        {
            "url": "https://example.com",
            "text": "Example text"
        }
        """
        # Implementation
```

#### 6. Authentication Middleware (`middleware/auth.py`)

Handles API authentication:

```python
def init_auth(app, config):
    """
    Initialize authentication middleware.

    Args:
        app: Flask application instance
        config: Configuration object
    """

def require_auth(f):
    """
    Decorator to require authentication for a route.

    Args:
        f: Function to decorate

    Returns:
        decorated function
    """

def verify_pin(pin):
    """
    Verify if a PIN is valid.

    Args:
        pin (str): PIN to verify

    Returns:
        bool: True if PIN is valid
    """

def check_token(token):
    """
    Verify if a token is valid.

    Args:
        token (str): JWT token to check

    Returns:
        dict: Token payload if valid, None otherwise
    """

def generate_token(duration=3600):
    """
    Generate a new JWT token.

    Args:
        duration (int, optional): Token validity in seconds

    Returns:
        str: JWT token
    """
```

#### 7. Error Handler Middleware (`middleware/error_handler.py`)

Handles API errors:

```python
def init_error_handlers(app):
    """
    Initialize error handlers for the Flask application.

    Args:
        app: Flask application instance
    """

def handle_not_found(error):
    """
    Handle 404 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """

def handle_bad_request(error):
    """
    Handle 400 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """

def handle_unauthorized(error):
    """
    Handle 401 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """

def handle_internal_error(error):
    """
    Handle 500 errors.

    Args:
        error: Error object

    Returns:
        Response: JSON error response
    """

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
```

#### 8. Exceptions (`exceptions.py`)

Define API-specific exceptions:

```python
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
```

### API Design

#### 1. RESTful Principles

- Use standard HTTP methods (GET, POST, PUT, DELETE)
- Use resource-oriented URLs
- Return appropriate HTTP status codes
- Include error details in response body
- Use JSON for request and response bodies

#### 2. Authentication

- Use a simple PIN-based authentication for initial access
- Generate JWT tokens for authenticated sessions
- Support token refresh for extended sessions
- Implement CSRF protection for form submissions

#### 3. Response Format

All API responses should follow a consistent format:

For successful responses:

```json
{
  "success": true,
  "data": {
    // Response data here
  }
}
```

For error responses:

```json
{
  "success": false,
  "error": {
    "message": "Error message",
    "status": 400,
    "details": {
      // Optional additional details
    }
  }
}
```

### Frontend Serving

The API server should also serve the React frontend application:

1. **Static File Serving**:

   - Serve the built React application from the `static` directory
   - Configure proper caching headers for static assets
   - Handle SPA routing by returning `index.html` for all non-API routes

2. **API Documentation**:
   - Provide a simple API documentation page
   - Include examples for common operations
   - Offer a testing interface for API endpoints

### Security Considerations

#### 1. Network Security

- Restrict API server to localhost or LAN only
- Implement optional HTTPS with self-signed certificates
- Rate limit authentication attempts to prevent brute force

#### 2. Input Validation

- Validate all input parameters
- Sanitize inputs to prevent injection attacks
- Use parameterized queries for database operations

#### 3. Authentication and Authorization

- Use secure methods for storing the admin PIN
- Implement proper token validation
- Set appropriate token expiration times
- Store tokens securely using HTTP-only cookies

### Performance Considerations

#### 1. Server Configuration

- Use a production-ready WSGI server (Waitress)
- Implement proper connection handling
- Configure appropriate timeouts

#### 2. Response Optimization

- Use compression for responses
- Implement ETag support for caching
- Paginate large responses

#### 3. Concurrency

- Ensure thread safety for all operations
- Handle concurrent requests properly
- Use asynchronous processing for long-running operations

### Error Handling and Resilience

#### 1. Error Responses

- Provide clear error messages
- Include enough details for troubleshooting
- Log errors for server-side diagnostics

#### 2. Graceful Degradation

- Handle service unavailability gracefully
- Provide fallback behavior when subsystems fail
- Give clear feedback on the UI when operations cannot be completed

### Testing

#### 1. Unit Testing

- Test each route independently
- Mock dependencies for isolated testing
- Test error handling and edge cases

#### 2. Integration Testing

- Test API interaction with the database
- Test authentication flow
- Test media operations end-to-end

#### 3. Security Testing

- Test authentication bypass attempts
- Test input validation
- Test rate limiting and brute force protection

## Common Issues and Solutions

#### 1. Authentication Problems

- Issue: Users cannot authenticate or tokens expire unexpectedly
- Solution: Check PIN configuration and token expiration settings
- Solution: Verify that cookies are being stored properly
- Solution: Check for clock synchronization issues

#### 2. Cross-Origin Problems

- Issue: Frontend cannot make API calls due to CORS
- Solution: Configure proper CORS headers for local development
- Solution: Ensure the API and frontend are served from the same origin in production

#### 3. Performance Issues

- Issue: Slow response times for media operations
- Solution: Implement caching for frequent operations
- Solution: Optimize database queries
- Solution: Use streaming responses for large data

## Resources and References

#### 1. Flask Documentation

- [Flask Official Documentation](https://flask.palletsprojects.com/)
- [Flask-CORS](https://flask-cors.readthedocs.io/)
- [Waitress WSGI Server](https://docs.pylonsproject.org/projects/waitress/en/latest/)

#### 2. Authentication

- [JWT Implementation in Python](https://pyjwt.readthedocs.io/)
- [Flask Authentication Best Practices](https://flask.palletsprojects.com/en/2.0.x/security/)

#### 3. API Design

- [RESTful API Design Best Practices](https://swagger.io/resources/articles/best-practices-in-api-design/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)
