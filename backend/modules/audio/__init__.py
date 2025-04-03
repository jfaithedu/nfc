"""
Audio module for the NFC-based music player.

This module provides audio playback functionality, Bluetooth device management,
and system sound capabilities.
"""

from . import audio_controller
from . import bluetooth_manager
from . import playback_handler
from . import system_sounds
from . import exceptions

# Export the public API
from .audio_controller import (
    initialize,
    shutdown,
    play,
    pause,
    resume,
    stop,
    seek,
    set_volume,
    get_volume,
    mute,
    unmute,
    get_playback_status,
    is_playing,
    play_system_sound,
    play_error_sound,
    play_success_sound,
    
    # Bluetooth functions
    start_discovery,
    stop_discovery,
    get_discovered_devices,
    connect_device,
    disconnect_device,
    forget_device,
    get_connected_device,
    is_device_connected,
    get_paired_devices,
    reconnect_last_device,
    set_auto_reconnect,
    get_bluetooth_status,
    
    # Testing
    test_audio_output
)