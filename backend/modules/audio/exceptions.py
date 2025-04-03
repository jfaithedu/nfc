"""
Audio module exception classes.

This module defines all exceptions related to audio playback, Bluetooth connections,
and system sound functionality.
"""

class AudioError(Exception):
    """Base exception for all audio related errors."""
    pass

class AudioInitializationError(AudioError):
    """Exception raised when audio subsystem initialization fails."""
    pass

class BluetoothError(AudioError):
    """Base exception for Bluetooth related errors."""
    pass

class BluetoothDiscoveryError(BluetoothError):
    """Exception raised when Bluetooth discovery fails."""
    pass

class BluetoothConnectionError(BluetoothError):
    """Exception raised when Bluetooth connection fails."""
    pass

class AudioPlaybackError(AudioError):
    """Exception raised when audio playback fails."""
    pass

class MediaLoadError(AudioError):
    """Exception raised when media cannot be loaded."""
    pass

class SystemSoundError(AudioError):
    """Exception raised when system sound cannot be played."""
    pass

class BlueALSAError(AudioError):
    """Exception raised when BlueALSA operation fails."""
    pass