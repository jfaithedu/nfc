"""
NFC Module - Provides interfaces for NFC tag detection and reading.

This module is responsible for interfacing with the NFC hardware
to detect and read NFC tags placed on the music player device.
"""

# Import public interface functions from controller
from .nfc_controller import (
    initialize,
    shutdown,
    poll_for_tag,
    read_tag_data,
    write_tag_data,
    get_hardware_info,
    authenticate_tag,
    read_ndef_data,
    write_ndef_data,
    continuous_poll
)

# Import exceptions for external use
from .exceptions import (
    NFCError,
    NFCHardwareError,
    NFCNoTagError,
    NFCReadError,
    NFCWriteError,
    NFCAuthenticationError
)

__all__ = [
    # Main controller functions
    'initialize',
    'shutdown',
    'poll_for_tag',
    'read_tag_data',
    'write_tag_data',
    'get_hardware_info',
    'authenticate_tag',
    'read_ndef_data',
    'write_ndef_data',
    'continuous_poll',
    
    # Exceptions
    'NFCError',
    'NFCHardwareError',
    'NFCNoTagError',
    'NFCReadError',
    'NFCWriteError',
    'NFCAuthenticationError'
]
