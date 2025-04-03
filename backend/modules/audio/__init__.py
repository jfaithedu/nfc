"""
Audio module for the NFC music player.

This module provides functionality for Bluetooth audio connections and playback.
"""

from .audio_controller import (
    # Core functionality
    initialize,
    shutdown,
    
    # Playback control
    play,
    pause,
    resume,
    stop,
    seek,
    
    # Volume control
    set_volume,
    get_volume,
    mute,
    unmute,
    
    # Status
    get_playback_status,
    
    # System sounds
    play_system_sound,
    play_error_sound,
    play_success_sound,
    
    # Bluetooth management
    start_bluetooth_discovery,
    stop_bluetooth_discovery,
    get_discovered_bluetooth_devices,
    connect_bluetooth_device,
    disconnect_bluetooth_device,
    get_connected_bluetooth_device,
    get_saved_bluetooth_devices
)

from .exceptions import (
    AudioError,
    AudioInitializationError,
    BluetoothError,
    BluetoothDiscoveryError,
    BluetoothConnectionError,
    AudioPlaybackError,
    MediaLoadError,
    SystemSoundError
)

__all__ = [
    # Core functionality
    'initialize',
    'shutdown',
    
    # Playback control
    'play',
    'pause',
    'resume',
    'stop',
    'seek',
    
    # Volume control
    'set_volume',
    'get_volume',
    'mute',
    'unmute',
    
    # Status
    'get_playback_status',
    
    # System sounds
    'play_system_sound',
    'play_error_sound',
    'play_success_sound',
    
    # Bluetooth management
    'start_bluetooth_discovery',
    'stop_bluetooth_discovery',
    'get_discovered_bluetooth_devices',
    'connect_bluetooth_device',
    'disconnect_bluetooth_device',
    'get_connected_bluetooth_device',
    'get_saved_bluetooth_devices',
    
    # Exceptions
    'AudioError',
    'AudioInitializationError',
    'BluetoothError',
    'BluetoothDiscoveryError',
    'BluetoothConnectionError',
    'AudioPlaybackError',
    'MediaLoadError',
    'SystemSoundError'
]
