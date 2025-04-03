"""
Audio controller for the NFC music player.

This is the main interface for other modules to interact with the audio subsystem.
Controls Bluetooth connections, audio playback, and system sounds.
"""

import os
import logging
import threading
import time
from pathlib import Path

from .bluetooth_manager import BluetoothManager
from .playback_handler import AudioPlayer
from .system_sounds import (
    initialize_system_sounds, 
    play_sound, 
    get_available_sounds,
    add_custom_sound
)
from .exceptions import (
    AudioError, 
    AudioInitializationError, 
    BluetoothConnectionError,
    AudioPlaybackError
)

# Set up logger
logger = logging.getLogger(__name__)

# Global variables
_bluetooth_manager = None
_audio_player = None
_initialized = False
_last_media_path = None

# Constants
SYSTEM_SOUNDS_DIR = "sounds"  # Relative to app directory

def initialize():
    """
    Initialize the audio subsystem.
    Connect to the last used Bluetooth device if available.

    Returns:
        bool: True if initialization successful
    """
    global _bluetooth_manager, _audio_player, _initialized
    
    try:
        logger.info("Initializing audio subsystem")
        
        # Initialize Bluetooth manager
        _bluetooth_manager = BluetoothManager()
        
        # Initialize audio player
        _audio_player = AudioPlayer()
        
        # Initialize system sounds
        app_dir = Path(__file__).parent.parent.parent.parent  # 4 levels up from this file
        sounds_dir = app_dir / SYSTEM_SOUNDS_DIR
        
        if not initialize_system_sounds(sounds_dir):
            logger.warning("System sounds not initialized (directory not found)")
        
        # Try to connect to last paired device
        saved_devices = _bluetooth_manager.get_saved_devices()
        if saved_devices:
            # Sort by last connected time (most recent first)
            sorted_devices = sorted(
                saved_devices, 
                key=lambda d: d.get('last_connected', 0), 
                reverse=True
            )
            
            last_device = sorted_devices[0]
            try:
                logger.info(f"Attempting to connect to last paired device: {last_device['name']}")
                # Start discovery to find the device
                _bluetooth_manager.start_discovery(timeout=10)
                time.sleep(2)  # Give it a moment to discover devices
                
                # Try to connect
                _bluetooth_manager.connect_device(last_device['address'])
                logger.info(f"Successfully connected to {last_device['name']}")
                
            except BluetoothConnectionError as e:
                logger.warning(f"Failed to connect to last device: {str(e)}")
        
        _initialized = True
        logger.info("Audio subsystem initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize audio subsystem: {str(e)}")
        raise AudioInitializationError(f"Failed to initialize audio subsystem: {str(e)}")

def shutdown():
    """
    Perform clean shutdown of audio subsystem.
    """
    global _bluetooth_manager, _audio_player, _initialized
    
    if not _initialized:
        logger.debug("Audio not initialized, nothing to shut down")
        return
    
    logger.info("Shutting down audio subsystem")
    
    # Stop any playback
    if _audio_player:
        try:
            _audio_player.stop()
        except Exception as e:
            logger.error(f"Error stopping playback during shutdown: {str(e)}")
    
    # Disconnect Bluetooth
    if _bluetooth_manager:
        try:
            _bluetooth_manager.disconnect_device()
        except Exception as e:
            logger.error(f"Error disconnecting Bluetooth during shutdown: {str(e)}")
    
    _initialized = False
    logger.info("Audio subsystem shut down")

def play(media_path):
    """
    Play audio from the specified path.

    Args:
        media_path (str): Path to the media file

    Returns:
        bool: True if playback started successfully

    Raises:
        AudioPlaybackError: If playback cannot be started
    """
    global _audio_player, _last_media_path
    
    _check_initialized()
    
    if not media_path:
        raise AudioPlaybackError("No media path provided")
    
    logger.info(f"Playing media: {media_path}")
    
    try:
        # Load and play the media
        _audio_player.load_media(media_path)
        success = _audio_player.play()
        
        if success:
            _last_media_path = media_path
        
        return success
        
    except Exception as e:
        logger.error(f"Failed to play media: {str(e)}")
        raise AudioPlaybackError(f"Failed to play media: {str(e)}")

def pause():
    """
    Pause current playback.

    Returns:
        bool: True if paused successfully
    """
    _check_initialized()
    
    logger.debug("Pausing playback")
    return _audio_player.pause()

def resume():
    """
    Resume paused playback.

    Returns:
        bool: True if resumed successfully
    """
    _check_initialized()
    
    logger.debug("Resuming playback")
    return _audio_player.resume()

def stop():
    """
    Stop current playback.

    Returns:
        bool: True if stopped successfully
    """
    _check_initialized()
    
    logger.debug("Stopping playback")
    return _audio_player.stop()

def seek(position_seconds):
    """
    Seek to a specific position in the current track.

    Args:
        position_seconds (int): Position in seconds

    Returns:
        bool: True if seek successful
    """
    _check_initialized()
    
    logger.debug(f"Seeking to position: {position_seconds}s")
    return _audio_player.seek(position_seconds)

def set_volume(level):
    """
    Set volume level.

    Args:
        level (int): Volume level (0-100)

    Returns:
        int: New volume level
    """
    _check_initialized()
    
    logger.debug(f"Setting volume to {level}%")
    return _audio_player.set_volume(level)

def get_volume():
    """
    Get current volume level.

    Returns:
        int: Current volume level (0-100)
    """
    _check_initialized()
    
    return _audio_player.get_volume()

def mute():
    """
    Mute audio output.

    Returns:
        bool: True if muted
    """
    _check_initialized()
    
    logger.debug("Muting audio")
    return _audio_player.mute()

def unmute():
    """
    Unmute audio output.

    Returns:
        bool: True if unmuted
    """
    _check_initialized()
    
    logger.debug("Unmuting audio")
    return _audio_player.unmute()

def get_playback_status():
    """
    Get current playback status.

    Returns:
        dict: Playback status including:
            - state: 'playing', 'paused', 'stopped'
            - position: Current position in seconds
            - duration: Total duration in seconds
            - media_path: Path to current media
    """
    _check_initialized()
    
    return {
        'state': _audio_player.get_state(),
        'position': _audio_player.get_position(),
        'duration': _audio_player.get_duration(),
        'media_path': _last_media_path
    }

def play_system_sound(sound_type):
    """
    Play a system notification sound.

    Args:
        sound_type (str): Type of sound ('error', 'success', etc.)

    Returns:
        bool: True if sound played successfully
    """
    _check_initialized()
    
    logger.debug(f"Playing system sound: {sound_type}")
    return play_sound(sound_type)

def play_error_sound():
    """
    Play the error notification sound.

    Returns:
        bool: True if sound played successfully
    """
    return play_system_sound('error')

def play_success_sound():
    """
    Play the success notification sound.

    Returns:
        bool: True if sound played successfully
    """
    return play_system_sound('success')

def start_bluetooth_discovery(timeout=30):
    """
    Start Bluetooth device discovery.

    Args:
        timeout (int, optional): Discovery timeout in seconds

    Returns:
        bool: True if discovery started
    """
    _check_initialized()
    
    logger.info(f"Starting Bluetooth discovery (timeout: {timeout}s)")
    return _bluetooth_manager.start_discovery(timeout)

def stop_bluetooth_discovery():
    """
    Stop Bluetooth device discovery.

    Returns:
        bool: True if discovery stopped
    """
    _check_initialized()
    
    logger.info("Stopping Bluetooth discovery")
    return _bluetooth_manager.stop_discovery()

def get_discovered_bluetooth_devices():
    """
    Get list of discovered Bluetooth devices.

    Returns:
        list: List of device dictionaries
    """
    _check_initialized()
    
    return _bluetooth_manager.get_discovered_devices()

def connect_bluetooth_device(device_address):
    """
    Connect to a Bluetooth device.

    Args:
        device_address (str): Bluetooth device address

    Returns:
        bool: True if connected successfully
    """
    _check_initialized()
    
    logger.info(f"Connecting to Bluetooth device: {device_address}")
    return _bluetooth_manager.connect_device(device_address)

def disconnect_bluetooth_device():
    """
    Disconnect the current Bluetooth device.

    Returns:
        bool: True if disconnected successfully
    """
    _check_initialized()
    
    logger.info("Disconnecting Bluetooth device")
    return _bluetooth_manager.disconnect_device()

def get_connected_bluetooth_device():
    """
    Get information about the currently connected Bluetooth device.

    Returns:
        dict or None: Device information or None if not connected
    """
    _check_initialized()
    
    return _bluetooth_manager.get_connected_device()

def get_saved_bluetooth_devices():
    """
    Get all saved Bluetooth devices.

    Returns:
        list: List of saved device dictionaries
    """
    _check_initialized()
    
    return _bluetooth_manager.get_saved_devices()

def _check_initialized():
    """Check if the audio subsystem is initialized."""
    global _initialized
    if not _initialized:
        logger.error("Audio subsystem not initialized")
        raise AudioError("Audio subsystem not initialized. Call initialize() first.")
