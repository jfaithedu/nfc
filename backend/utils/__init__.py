"""
Utils Module - Common utility functions and classes for the NFC music player application.

This package provides reusable utilities for tasks such as logging,
file operations, error handling, event communication, etc.
"""

# Import and expose key functions from other modules
from .exceptions import (
    AppError,
    NetworkError,
    FileOperationError,
    ValidationError,
    ConfigurationError,
    SystemError
)

from .logger import (
    setup_logger,
    get_logger,
    set_global_log_level,
    LoggerMixin
)

from .file_utils import (
    ensure_dir,
    safe_filename,
    get_file_extension,
    file_size,
    is_media_file,
    copy_file_safe,
    delete_file_safe,
    list_files_by_extension
)

from .validators import (
    is_valid_url,
    is_valid_youtube_url,
    is_valid_nfc_uid,
    is_valid_media_id,
    sanitize_input,
    validate_required,
    validate_length
)

from .event_bus import (
    event_bus,
    EventBus,
    EventNames
)

from .system_utils import (
    get_system_info,
    restart_service,
    check_network_status,
    check_process_running,
    reboot_system,
    shutdown_system,
    get_bluetooth_devices,
    get_gpio_pin,
    is_running_on_pi
)

# Define version
__version__ = '0.1.0'
