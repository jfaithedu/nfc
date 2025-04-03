# Utils Module - Implementation Guide

## Overview

The Utils Module contains common utility functions and helper classes that are used across the different modules of the NFC music player application. It provides reusable code for tasks such as logging, error handling, file operations, and other general-purpose functionality. The utilities in this module help maintain consistency and reduce code duplication throughout the application.

## Core Responsibilities

1. Provide logging functionality with consistent formatting
2. Handle file system operations safely
3. Implement reusable error handling patterns
4. Provide helper functions for common tasks
5. Implement cross-module communication utilities
6. Provide system-level utilities for interacting with the Raspberry Pi

## Implementation Details

### File Structure

```
utils/
├── __init__.py             # Package initialization
├── logger.py               # Logging utilities
├── file_utils.py           # File system operations
├── validators.py           # Input validation functions
├── event_bus.py            # Cross-module event handling
├── system_utils.py         # System-level utilities
└── exceptions.py           # Common exception definitions
```

### Key Components

#### 1. Logger (`logger.py`)

Provides consistent logging across all modules:

```python
def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with consistent formatting.

    Args:
        name (str): Logger name, typically the module name
        log_file (str, optional): Path to log file, if None logs to console only
        level (int, optional): Logging level

    Returns:
        Logger: Configured logger instance
    """

def get_logger(name):
    """
    Get a logger instance by name.

    Args:
        name (str): Logger name

    Returns:
        Logger: Logger instance
    """

def set_global_log_level(level):
    """
    Set the log level for all loggers.

    Args:
        level (int): Logging level (e.g., logging.INFO)
    """

class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.

    Usage:
        class MyClass(LoggerMixin):
            def __init__(self):
                self.setup_logger()

            def some_method(self):
                self.logger.info("Some message")
    """

    def setup_logger(self, name=None):
        """
        Set up logger for this instance.

        Args:
            name (str, optional): Logger name, defaults to class name
        """
```

#### 2. File Utilities (`file_utils.py`)

Safe file system operations:

```python
def ensure_dir(directory):
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory (str): Directory path

    Returns:
        str: Directory path
    """

def safe_filename(filename):
    """
    Convert a string to a safe filename.

    Args:
        filename (str): Original filename

    Returns:
        str: Safe filename with invalid characters removed
    """

def get_file_extension(filename):
    """
    Get the extension of a file.

    Args:
        filename (str): Filename

    Returns:
        str: File extension without the dot, or empty string if none
    """

def file_size(file_path):
    """
    Get the size of a file in bytes.

    Args:
        file_path (str): Path to file

    Returns:
        int: File size in bytes
    """

def is_media_file(file_path, allowed_extensions=None):
    """
    Check if a file is a supported media file.

    Args:
        file_path (str): Path to file
        allowed_extensions (list, optional): List of allowed extensions

    Returns:
        bool: True if file is a supported media file
    """

def copy_file_safe(source, destination, overwrite=False):
    """
    Safely copy a file with error handling.

    Args:
        source (str): Source file path
        destination (str): Destination file path
        overwrite (bool, optional): Overwrite destination if it exists

    Returns:
        bool: True if copy successful
    """

def delete_file_safe(file_path):
    """
    Safely delete a file with error handling.

    Args:
        file_path (str): Path to file

    Returns:
        bool: True if deletion successful
    """

def list_files_by_extension(directory, extensions):
    """
    List all files in a directory with specified extensions.

    Args:
        directory (str): Directory path
        extensions (list): List of file extensions to include

    Returns:
        list: List of file paths
    """
```

#### 3. Validators (`validators.py`)

Input validation functions:

```python
def is_valid_url(url):
    """
    Check if a string is a valid URL.

    Args:
        url (str): URL to validate

    Returns:
        bool: True if valid URL
    """

def is_valid_youtube_url(url):
    """
    Check if a string is a valid YouTube URL.

    Args:
        url (str): URL to validate

    Returns:
        bool: True if valid YouTube URL
    """

def is_valid_nfc_uid(uid):
    """
    Check if a string is a valid NFC tag UID.

    Args:
        uid (str): UID to validate

    Returns:
        bool: True if valid UID
    """

def is_valid_media_id(media_id):
    """
    Check if a string is a valid media ID.

    Args:
        media_id (str): Media ID to validate

    Returns:
        bool: True if valid media ID
    """

def sanitize_input(input_str, allowed_chars=None):
    """
    Sanitize a string by removing potentially harmful characters.

    Args:
        input_str (str): Input string
        allowed_chars (str, optional): String of allowed characters

    Returns:
        str: Sanitized string
    """
```

#### 4. Event Bus (`event_bus.py`)

Cross-module event handling:

```python
class EventBus:
    """
    Simple event bus for cross-module communication.

    Usage:
        # In a module that triggers events:
        from utils.event_bus import event_bus
        event_bus.emit('tag_detected', tag_uid='ABC123')

        # In a module that listens for events:
        from utils.event_bus import event_bus

        def on_tag_detected(tag_uid):
            print(f"Tag detected: {tag_uid}")

        event_bus.on('tag_detected', on_tag_detected)
    """

    def __init__(self):
        """Initialize the event bus."""
        self._events = {}

    def on(self, event_name, callback):
        """
        Register an event handler.

        Args:
            event_name (str): Event name
            callback (callable): Function to call when event is emitted
        """

    def off(self, event_name, callback=None):
        """
        Remove an event handler.

        Args:
            event_name (str): Event name
            callback (callable, optional): Function to remove,
                                           or None to remove all handlers
        """

    def emit(self, event_name, **kwargs):
        """
        Emit an event.

        Args:
            event_name (str): Event name
            **kwargs: Event data
        """

    def once(self, event_name, callback):
        """
        Register an event handler that will be called only once.

        Args:
            event_name (str): Event name
            callback (callable): Function to call when event is emitted
        """

# Global event bus instance
event_bus = EventBus()
```

#### 5. System Utilities (`system_utils.py`)

Raspberry Pi specific utilities:

```python
def get_system_info():
    """
    Get system information.

    Returns:
        dict: System information including:
            - os_name: Operating system name
            - os_version: Operating system version
            - hostname: System hostname
            - uptime: System uptime in seconds
            - cpu_usage: CPU usage as a percentage
            - memory_usage: Memory usage as a percentage
            - disk_usage: Disk usage as a percentage
    """

def restart_service(service_name):
    """
    Restart a system service.

    Args:
        service_name (str): Name of the service

    Returns:
        bool: True if restart successful
    """

def check_network_status():
    """
    Check network connectivity.

    Returns:
        dict: Network status information including:
            - connected: True if connected to a network
            - interface: Active network interface
            - ip_address: IP address
            - wifi_strength: WiFi signal strength if applicable
    """

def check_process_running(process_name):
    """
    Check if a process is running.

    Args:
        process_name (str): Process name

    Returns:
        bool: True if process is running
    """

def reboot_system():
    """
    Reboot the system (requires appropriate permissions).

    Returns:
        bool: True if reboot command was issued
    """

def shutdown_system():
    """
    Shutdown the system (requires appropriate permissions).

    Returns:
        bool: True if shutdown command was issued
    """

def get_bluetooth_devices():
    """
    Get list of bluetooth devices.

    Returns:
        list: List of bluetooth device dictionaries
    """

def get_gpio_pin(pin_number):
    """
    Get a GPIO pin object.

    Args:
        pin_number (int): BCM pin number

    Returns:
        Pin: GPIO pin object
    """
```

#### 6. Exceptions (`exceptions.py`)

Common exception definitions:

```python
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
```

### Cross-Module Communication

#### 1. Event Bus Pattern

The event bus pattern allows for loose coupling between modules:

- **Advantages**:

  - Modules can communicate without direct dependencies
  - Easy to add new event listeners without modifying existing code
  - Events can have multiple listeners

- **Usage Guidelines**:
  - Use for non-critical cross-module notifications
  - Document all events and their expected parameters
  - Avoid circular event chains that could cause infinite loops

#### 2. Common Events

Define standard events that can be used across modules:

1. `tag_detected`: Emitted when a new NFC tag is detected

   - Parameters: `tag_uid` (str)

2. `playback_started`: Emitted when media playback starts

   - Parameters: `media_id` (str), `tag_uid` (str, optional)

3. `playback_stopped`: Emitted when media playback stops

   - Parameters: `media_id` (str), `position` (int)

4. `bluetooth_connected`: Emitted when a Bluetooth device connects

   - Parameters: `device_address` (str), `device_name` (str)

5. `bluetooth_disconnected`: Emitted when a Bluetooth device disconnects

   - Parameters: `device_address` (str)

6. `system_error`: Emitted when a system error occurs
   - Parameters: `error_type` (str), `message` (str), `details` (dict)

### Logging Strategy

#### 1. Log Levels

Use appropriate log levels for different types of information:

- **DEBUG**: Detailed information for debugging
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened, but the application still works
- **ERROR**: Due to a more serious problem, the application couldn't perform some function
- **CRITICAL**: A serious error indicating that the program itself may be unable to continue running

#### 2. Log Format

Use a consistent log format across all modules:

```
[TIMESTAMP] [LEVEL] [MODULE_NAME] - Message
```

For example:

```
[2023-06-15 14:23:45] [INFO] [nfc_controller] - Tag detected: ABC123
```

#### 3. Log Storage

- Store logs in a rotating file system to prevent excessive disk usage
- Keep daily log files with a retention period (e.g., 30 days)
- Consider forwarding critical logs to system log for persistent storage

### File Management

#### 1. Safe File Operations

- Always check for file existence before attempting to read
- Use proper error handling for all file operations
- Implement atomic write operations when possible (write to temp file, then rename)
- Handle concurrent access properly

#### 2. Path Handling

- Use absolute paths whenever possible
- Validate paths before file operations
- Sanitize all filenames to prevent directory traversal attacks

### Error Handling

#### 1. Exception Hierarchy

Use the custom exception hierarchy to provide clear error information:

- `AppError`: Base class for all application-specific exceptions
  - `NetworkError`: Network-related failures
  - `FileOperationError`: File system operation failures
  - `ValidationError`: Input validation failures
  - `ConfigurationError`: Configuration-related failures
  - `SystemError`: System-level operation failures

#### 2. Error Recovery

- Design utilities to be resilient to temporary failures
- Implement retry logic where appropriate
- Provide clear error messages to aid in troubleshooting

## Common Issues and Solutions

#### 1. File Permission Issues

- Issue: File operations fail due to permission errors
- Solution: Check and validate permissions before operations
- Solution: Handle permission errors gracefully with informative messages

#### 2. Event Handling Issues

- Issue: Event listeners not being called
- Solution: Verify that the event name matches exactly
- Solution: Check if the event bus has been properly initialized

#### 3. Path Resolution Problems

- Issue: File paths not resolving correctly
- Solution: Use absolute paths or resolve relative paths properly
- Solution: Test file operations on the target platform

## Resources and References

#### 1. Python Utilities

- [Python Logging Documentation](https://docs.python.org/3/library/logging.html)
- [Python File I/O](https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files)
- [Python Error and Exceptions](https://docs.python.org/3/tutorial/errors.html)

#### 2. Raspberry Pi

- [Raspberry Pi GPIO Library](https://gpiozero.readthedocs.io/)
- [Raspberry Pi System Information](https://www.raspberrypi.org/documentation/computers/system.html)

#### 3. Design Patterns

- [Event Bus Pattern](https://medium.com/@sevcsik/the-event-bus-pattern-paradigm-in-javascript-64d82e71756)
- [Error Handling Best Practices](https://www.toptal.com/python/python-design-patterns)
