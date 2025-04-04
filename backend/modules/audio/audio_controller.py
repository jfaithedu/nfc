"""
Audio Controller for the NFC music player.

This module provides the main interface for audio functionality, coordinating
Bluetooth connectivity and audio playback. It serves as the primary API that
other modules will interact with.
"""

import os
import time
import logging
import threading
import json
from typing import Dict, Optional, List, Any, Tuple

from .bluetooth_manager import BluetoothManager, get_bluetooth_status
from .playback_handler import AudioPlayer, test_audio_output
from .system_sounds import initialize_system_sounds, play_sound
from .exceptions import (
    AudioError, 
    AudioInitializationError,
    BluetoothError,
    AudioPlaybackError
)

# Configure logging
logger = logging.getLogger(__name__)


class AudioController:
    """Main controller for the audio subsystem."""
    
    def __init__(self, config_path: str = None, sounds_dir: str = None):
        """
        Initialize the audio controller.
        
        Args:
            config_path (str, optional): Path to config file
            sounds_dir (str, optional): Directory for system sounds
        """
        # Configuration
        self.config_path = config_path or os.path.expanduser("~/.audio_config.json")
        self.config = self._load_config()
        
        # Component references
        self.bt_manager = None
        self.player = None
        self.initialized = False
        
        # Current playback tracking
        self.current_media = None
        
        # Auto-reconnect settings
        self.auto_reconnect = self.config.get("auto_reconnect", True)
        self.reconnect_thread = None
        self.reconnect_running = False
        
        logger.info("Audio controller created")
    
    def _load_config(self) -> Dict:
        """
        Load configuration from file.
        
        Returns:
            dict: Configuration dictionary
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            
            # Default config
            return {
                "auto_reconnect": True,
                "volume": 50,
                "last_device": None
            }
        
        except Exception as e:
            logger.warning(f"Failed to load audio config: {e}")
            return {
                "auto_reconnect": True,
                "volume": 50,
                "last_device": None
            }
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save audio config: {e}")
    
    def initialize(self, sounds_dir: str = None) -> bool:
        """
        Initialize the audio subsystem.
        
        Args:
            sounds_dir (str, optional): Directory for system sounds
        
        Returns:
            bool: True if initialization successful
        
        Raises:
            AudioInitializationError: If initialization fails
        """
        if self.initialized:
            logger.warning("Audio controller already initialized")
            return True
        
        try:
            logger.info("Initializing audio controller...")
            
            # Initialize system sounds
            if not initialize_system_sounds(sounds_dir):
                logger.warning("Failed to initialize system sounds")
            
            # Initialize Bluetooth manager
            self.bt_manager = BluetoothManager()
            
            # Initialize audio player
            self.player = AudioPlayer()
            
            # Set initialized flag
            self.initialized = True
            
            # Start auto-reconnect if enabled
            if self.auto_reconnect:
                self._start_auto_reconnect()
            
            logger.info("Audio controller initialized successfully")
            return True
        
        except Exception as e:
            logger.error(f"Failed to initialize audio controller: {e}")
            self.shutdown()
            raise AudioInitializationError(f"Failed to initialize audio: {e}")
    
    def _start_auto_reconnect(self) -> None:
        """Start the auto-reconnect background thread."""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
        
        self.reconnect_running = True
        self.reconnect_thread = threading.Thread(target=self._auto_reconnect_worker)
        self.reconnect_thread.daemon = True
        self.reconnect_thread.start()
        
        logger.info("Auto-reconnect thread started")
    
    def _stop_auto_reconnect(self) -> None:
        """Stop the auto-reconnect background thread."""
        self.reconnect_running = False
        if self.reconnect_thread:
            # Wait for thread to terminate gracefully
            if self.reconnect_thread.is_alive():
                self.reconnect_thread.join(2.0)
            self.reconnect_thread = None
        
        logger.info("Auto-reconnect thread stopped")
    
    def _auto_reconnect_worker(self) -> None:
        """Background worker to automatically reconnect to Bluetooth device."""
        while self.reconnect_running:
            try:
                # Only try to reconnect if no device is connected
                if not self.bt_manager.get_connected_device():
                    # Try to reconnect to last device
                    last_device = self.config.get("last_device")
                    if last_device:
                        logger.info(f"Attempting to reconnect to {last_device}")
                        try:
                            self.bt_manager.connect_device(last_device)
                        except Exception as e:
                            logger.debug(f"Auto-reconnect failed: {e}")
                    else:
                        # Try any paired device
                        self.bt_manager.reconnect_last_device()
            
            except Exception as e:
                logger.warning(f"Error in auto-reconnect worker: {e}")
            
            # Sleep before next attempt
            for _ in range(30):  # Check every 30 seconds
                if not self.reconnect_running:
                    break
                time.sleep(1)
    
    def shutdown(self) -> None:
        """Perform clean shutdown of audio subsystem."""
        logger.info("Shutting down audio controller...")
        
        # Stop auto-reconnect thread
        self._stop_auto_reconnect()
        
        # Save config
        self._save_config()
        
        # Stop playback
        if self.player:
            try:
                self.player.stop()
                self.player.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down player: {e}")
            self.player = None
        
        # Clean up Bluetooth manager
        if self.bt_manager:
            try:
                self.bt_manager.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down Bluetooth manager: {e}")
            self.bt_manager = None
        
        # Reset state
        self.initialized = False
        self.current_media = None
        
        logger.info("Audio controller shutdown complete")
    
    def play(self, media_path: str) -> bool:
        """
        Play audio from the specified path.
        
        Args:
            media_path (str): Path to the media file
        
        Returns:
            bool: True if playback started successfully
        
        Raises:
            AudioPlaybackError: If playback cannot be started
        """
        self._ensure_initialized()
        
        try:
            # First, verify file exists
            if not os.path.exists(media_path):
                raise AudioPlaybackError(f"Media file not found: {media_path}")
            
            # Load and play the media
            self.player.load_media(media_path)
            result = self.player.play()
            
            if result:
                self.current_media = media_path
                
            return result
        
        except Exception as e:
            logger.error(f"Playback error: {e}")
            raise AudioPlaybackError(f"Playback error: {e}")
    
    def pause(self) -> bool:
        """
        Pause current playback.
        
        Returns:
            bool: True if paused successfully
        """
        self._ensure_initialized()
        
        try:
            return self.player.pause()
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
            return False
    
    def resume(self) -> bool:
        """
        Resume paused playback.
        
        Returns:
            bool: True if resumed successfully
        """
        self._ensure_initialized()
        
        try:
            return self.player.resume()
        except Exception as e:
            logger.error(f"Failed to resume: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop current playback.
        
        Returns:
            bool: True if stopped successfully
        """
        if not self.initialized or not self.player:
            return True
        
        try:
            self.current_media = None
            return self.player.stop()
        except Exception as e:
            logger.error(f"Failed to stop: {e}")
            return False
    
    def seek(self, position_seconds: int) -> bool:
        """
        Seek to a specific position in the current track.
        
        Args:
            position_seconds (int): Position in seconds
        
        Returns:
            bool: True if seek successful
        """
        self._ensure_initialized()
        
        try:
            return self.player.seek(position_seconds)
        except Exception as e:
            logger.error(f"Failed to seek: {e}")
            return False
    
    def set_volume(self, level: int) -> int:
        """
        Set volume level.
        
        Args:
            level (int): Volume level (0-100)
        
        Returns:
            int: New volume level
        """
        self._ensure_initialized()
        
        try:
            new_level = self.player.set_volume(level)
            # Update config
            self.config["volume"] = new_level
            self._save_config()
            return new_level
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return self.get_volume()
    
    def get_volume(self) -> int:
        """
        Get current volume level.
        
        Returns:
            int: Current volume level (0-100)
        """
        if not self.initialized or not self.player:
            return self.config.get("volume", 50)
        
        try:
            return self.player.get_volume()
        except Exception:
            return self.config.get("volume", 50)
    
    def mute(self) -> bool:
        """
        Mute audio output.
        
        Returns:
            bool: True if muted
        """
        self._ensure_initialized()
        
        try:
            return self.player.mute()
        except Exception as e:
            logger.error(f"Failed to mute: {e}")
            return False
    
    def unmute(self) -> bool:
        """
        Unmute audio output.
        
        Returns:
            bool: True if unmuted
        """
        self._ensure_initialized()
        
        try:
            return self.player.unmute()
        except Exception as e:
            logger.error(f"Failed to unmute: {e}")
            return False
    
    def get_playback_status(self) -> Dict:
        """
        Get current playback status.
        
        Returns:
            dict: Playback status including:
                - state: 'playing', 'paused', 'stopped'
                - position: Current position in seconds
                - duration: Total duration in seconds
                - media_path: Path to current media
                - volume: Current volume level
                - loop: Whether looping is enabled
        """
        if not self.initialized or not self.player:
            return {
                "state": "stopped",
                "position": 0,
                "duration": 0,
                "media_path": None,
                "volume": self.config.get("volume", 50),
                "loop": self.config.get("loop_playback", False)
            }
        
        try:
            status = self.player.get_status()
            status["media_path"] = self.current_media
            return status
        except Exception as e:
            logger.error(f"Failed to get playback status: {e}")
            return {
                "state": "unknown",
                "position": 0,
                "duration": 0,
                "media_path": self.current_media,
                "volume": self.config.get("volume", 50),
                "loop": self.config.get("loop_playback", False)
            }
    
    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.
        
        Returns:
            bool: True if audio is playing
        """
        if not self.initialized or not self.player:
            return False
        
        try:
            return self.player.get_state() == "playing"
        except Exception:
            return False
    
    def play_system_sound(self, sound_type: str) -> bool:
        """
        Play a system notification sound.
        
        Args:
            sound_type (str): Type of sound ('error', 'success', etc.)
        
        Returns:
            bool: True if sound played successfully
        """
        return play_sound(sound_type)
    
    def play_error_sound(self) -> bool:
        """
        Play the error notification sound.
        
        Returns:
            bool: True if sound played successfully
        """
        return play_sound("error")
    
    def play_success_sound(self) -> bool:
        """
        Play the success notification sound.
        
        Returns:
            bool: True if sound played successfully
        """
        return play_sound("success")
    
    def start_discovery(self, timeout: int = 30) -> bool:
        """
        Start discovery for Bluetooth devices.
        
        Args:
            timeout (int, optional): Discovery timeout in seconds
        
        Returns:
            bool: True if discovery started
        """
        self._ensure_initialized()
        
        try:
            return self.bt_manager.start_discovery(timeout)
        except Exception as e:
            logger.error(f"Failed to start discovery: {e}")
            return False
    
    def stop_discovery(self) -> bool:
        """
        Stop Bluetooth discovery.
        
        Returns:
            bool: True if discovery stopped
        """
        if not self.initialized or not self.bt_manager:
            return True
        
        try:
            return self.bt_manager.stop_discovery()
        except Exception as e:
            logger.error(f"Failed to stop discovery: {e}")
            return False
    
    def get_discovered_devices(self) -> List[Dict]:
        """
        Get list of discovered Bluetooth devices.
        
        Returns:
            list: List of device dictionaries
        """
        self._ensure_initialized()
        
        try:
            return self.bt_manager.get_discovered_devices()
        except Exception as e:
            logger.error(f"Failed to get discovered devices: {e}")
            return []
    
    def pair_device(self, device_address: str) -> bool:
        """
        Pair with a Bluetooth device.
        
        This establishes a trusted relationship but doesn't connect.
        To establish a connection after pairing, call connect_device().
        
        Args:
            device_address (str): Bluetooth device address

        Returns:
            bool: True if paired successfully
        """
        self._ensure_initialized()
        
        try:
            return self.bt_manager.pair_device(device_address)
        except Exception as e:
            logger.error(f"Failed to pair with {device_address}: {e}")
            return False
    
    def connect_device(self, device_address: str, auto_pair: bool = True) -> bool:
        """
        Connect to a Bluetooth device.
        
        Args:
            device_address (str): Bluetooth device address
            auto_pair (bool): Whether to automatically pair if not paired

        Returns:
            bool: True if connected successfully
        """
        self._ensure_initialized()
        
        try:
            result = self.bt_manager.connect_device(device_address, auto_pair)
            
            if result:
                # Save as last device
                self.config["last_device"] = device_address
                self._save_config()
            
            return result
        except Exception as e:
            logger.error(f"Failed to connect to {device_address}: {e}")
            return False
    
    def disconnect_device(self) -> bool:
        """
        Disconnect the current Bluetooth device.
        
        Returns:
            bool: True if disconnected successfully
        """
        if not self.initialized or not self.bt_manager:
            return True
        
        try:
            return self.bt_manager.disconnect_device()
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False
    
    def forget_device(self, device_address: str) -> bool:
        """
        Remove a paired Bluetooth device.
        
        Args:
            device_address (str): Bluetooth device address
        
        Returns:
            bool: True if device was forgotten
        """
        self._ensure_initialized()
        
        try:
            result = self.bt_manager.forget_device(device_address)
            
            # If this was the last device, clear it from config
            if result and self.config.get("last_device") == device_address:
                self.config["last_device"] = None
                self._save_config()
            
            return result
        except Exception as e:
            logger.error(f"Failed to forget device {device_address}: {e}")
            return False
    
    def get_connected_device(self) -> Optional[Dict]:
        """
        Get information about the currently connected Bluetooth device.
        
        Returns:
            dict or None: Device information or None if not connected
        """
        if not self.initialized or not self.bt_manager:
            return None
        
        try:
            return self.bt_manager.get_connected_device()
        except Exception as e:
            logger.error(f"Failed to get connected device: {e}")
            return None
    
    def is_device_connected(self) -> bool:
        """
        Check if a Bluetooth device is connected.
        
        Returns:
            bool: True if device is connected
        """
        if not self.initialized or not self.bt_manager:
            return False
        
        try:
            return self.bt_manager.is_device_connected()
        except Exception:
            return False
    
    def get_paired_devices(self) -> List[Dict]:
        """
        Get all paired Bluetooth devices.
        
        Returns:
            list: List of paired device dictionaries
        """
        self._ensure_initialized()
        
        try:
            return self.bt_manager.get_paired_devices()
        except Exception as e:
            logger.error(f"Failed to get paired devices: {e}")
            return []
    
    def reconnect_last_device(self) -> bool:
        """
        Attempt to reconnect to the last used Bluetooth device.
        
        Returns:
            bool: True if reconnection was successful
        """
        self._ensure_initialized()
        
        try:
            # Try the device from config first
            last_device = self.config.get("last_device")
            if last_device:
                try:
                    return self.bt_manager.connect_device(last_device)
                except Exception as e:
                    logger.warning(f"Failed to connect to last device {last_device}: {e}")
            
            # Fall back to any paired device
            return self.bt_manager.reconnect_last_device()
        except Exception as e:
            logger.error(f"Failed to reconnect: {e}")
            return False
    
    def set_auto_reconnect(self, enabled: bool) -> None:
        """
        Enable or disable automatic reconnection to Bluetooth devices.
        
        Args:
            enabled (bool): Whether to enable auto-reconnect
        """
        self.auto_reconnect = enabled
        self.config["auto_reconnect"] = enabled
        self._save_config()
        
        # Start or stop the thread as needed
        if enabled and self.initialized:
            self._start_auto_reconnect()
        else:
            self._stop_auto_reconnect()
    
    def get_bluetooth_status(self) -> Dict:
        """
        Get Bluetooth system status information.
        
        Returns:
            dict: Bluetooth status
        """
        # Import here to avoid circular import
        from .bluetooth_manager import get_bluetooth_status as get_basic_status
        status = get_basic_status()
        
        # Add controller-specific info
        if self.initialized and self.bt_manager:
            connected_device = self.bt_manager.get_connected_device()
            status["connected"] = connected_device is not None
            status["device"] = connected_device
            status["auto_reconnect"] = self.auto_reconnect
        else:
            status["connected"] = False
            status["device"] = None
            status["auto_reconnect"] = self.auto_reconnect
        
        return status
    
    def test_audio_output(self) -> bool:
        """
        Test audio output using a test sound.
        
        Returns:
            bool: True if test was successful
        """
        self._ensure_initialized()
        
        # Get connected device
        device = self.bt_manager.get_connected_device()
        if device:
            # Call the function from playback_handler with device address
            from .playback_handler import test_audio_output as test_audio_func
            return test_audio_func(device.get("address"))
        else:
            # Call the function without device address
            from .playback_handler import test_audio_output as test_audio_func
            return test_audio_func()
            
    def set_loop(self, enabled: bool) -> bool:
        """
        Enable or disable looping playback.
        
        Args:
            enabled (bool): Whether to enable looping
            
        Returns:
            bool: New looping state
        """
        self._ensure_initialized()
        
        try:
            # Update player
            loop_state = self.player.set_loop(enabled)
            
            # Store in config
            self.config["loop_playback"] = loop_state
            self._save_config()
            
            return loop_state
        except Exception as e:
            logger.error(f"Failed to set loop state: {e}")
            return False
    
    def get_loop(self) -> bool:
        """
        Get current looping state.
        
        Returns:
            bool: Whether looping is enabled
        """
        if not self.initialized or not self.player:
            return self.config.get("loop_playback", False)
        
        try:
            return self.player.get_loop()
        except Exception:
            return self.config.get("loop_playback", False)
    
    def _ensure_initialized(self) -> None:
        """
        Ensure the controller is initialized.
        
        Raises:
            AudioError: If controller is not initialized
        """
        if not self.initialized:
            raise AudioError("Audio controller not initialized")


# Module-level controller instance
_controller: Optional[AudioController] = None


def initialize() -> bool:
    """
    Initialize the audio module.
    
    Returns:
        bool: True if initialization successful
    """
    global _controller
    
    if _controller is not None:
        return True
    
    try:
        _controller = AudioController()
        return _controller.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize audio module: {e}")
        return False


def shutdown() -> None:
    """Perform clean shutdown of audio module."""
    global _controller
    
    if _controller:
        _controller.shutdown()
        _controller = None
        logger.info("Audio module shutdown complete")


def play(media_path: str) -> bool:
    """
    Play audio from the specified path.
    
    Args:
        media_path (str): Path to the media file
    
    Returns:
        bool: True if playback started successfully
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.error("Cannot play: audio module not initialized")
            return False
    
    try:
        return _controller.play(media_path)
    except Exception as e:
        logger.error(f"Playback error: {e}")
        return False


def pause() -> bool:
    """
    Pause current playback.
    
    Returns:
        bool: True if paused successfully
    """
    global _controller
    
    if not _controller:
        logger.warning("Cannot pause: audio module not initialized")
        return False
    
    return _controller.pause()


def resume() -> bool:
    """
    Resume paused playback.
    
    Returns:
        bool: True if resumed successfully
    """
    global _controller
    
    if not _controller:
        logger.warning("Cannot resume: audio module not initialized")
        return False
    
    return _controller.resume()


def stop() -> bool:
    """
    Stop current playback.
    
    Returns:
        bool: True if stopped successfully
    """
    global _controller
    
    if not _controller:
        return True
    
    return _controller.stop()


def seek(position_seconds: int) -> bool:
    """
    Seek to a specific position in the current track.
    
    Args:
        position_seconds (int): Position in seconds
    
    Returns:
        bool: True if seek successful
    """
    global _controller
    
    if not _controller:
        logger.warning("Cannot seek: audio module not initialized")
        return False
    
    return _controller.seek(position_seconds)


def set_volume(level: int) -> int:
    """
    Set volume level.
    
    Args:
        level (int): Volume level (0-100)
    
    Returns:
        int: New volume level
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot set volume: audio module not initialized")
            return 0
    
    return _controller.set_volume(level)


def get_volume() -> int:
    """
    Get current volume level.
    
    Returns:
        int: Current volume level (0-100)
    """
    global _controller
    
    if not _controller:
        logger.warning("Cannot get volume: audio module not initialized")
        return 50
    
    return _controller.get_volume()


def mute() -> bool:
    """
    Mute audio output.
    
    Returns:
        bool: True if muted
    """
    global _controller
    
    if not _controller:
        logger.warning("Cannot mute: audio module not initialized")
        return False
    
    return _controller.mute()


def unmute() -> bool:
    """
    Unmute audio output.
    
    Returns:
        bool: True if unmuted
    """
    global _controller
    
    if not _controller:
        logger.warning("Cannot unmute: audio module not initialized")
        return False
    
    return _controller.unmute()


def get_playback_status() -> Dict:
    """
    Get current playback status.
    
    Returns:
        dict: Playback status
    """
    global _controller
    
    if not _controller:
        return {
            "state": "stopped",
            "position": 0,
            "duration": 0,
            "media_path": None,
            "volume": 50
        }
    
    return _controller.get_playback_status()


def is_playing() -> bool:
    """
    Check if audio is currently playing.
    
    Returns:
        bool: True if audio is playing
    """
    global _controller
    
    if not _controller:
        return False
    
    return _controller.is_playing()


def play_system_sound(sound_type: str) -> bool:
    """
    Play a system notification sound.
    
    Args:
        sound_type (str): Type of sound ('error', 'success', etc.)
    
    Returns:
        bool: True if sound played successfully
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot play system sound: audio module not initialized")
            return False
    
    return _controller.play_system_sound(sound_type)


def play_error_sound() -> bool:
    """
    Play the error notification sound.
    
    Returns:
        bool: True if sound played successfully
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot play error sound: audio module not initialized")
            return False
    
    return _controller.play_error_sound()


def play_success_sound() -> bool:
    """
    Play the success notification sound.
    
    Returns:
        bool: True if sound played successfully
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot play success sound: audio module not initialized")
            return False
    
    return _controller.play_success_sound()


def start_discovery(timeout: int = 30) -> bool:
    """
    Start discovery for Bluetooth devices.
    
    Args:
        timeout (int, optional): Discovery timeout in seconds
    
    Returns:
        bool: True if discovery started
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot start discovery: audio module not initialized")
            return False
    
    return _controller.start_discovery(timeout)


def stop_discovery() -> bool:
    """
    Stop Bluetooth discovery.
    
    Returns:
        bool: True if discovery stopped
    """
    global _controller
    
    if not _controller:
        return True
    
    return _controller.stop_discovery()


def get_discovered_devices() -> List[Dict]:
    """
    Get list of discovered Bluetooth devices.
    
    Returns:
        list: List of device dictionaries
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot get devices: audio module not initialized")
            return []
    
    return _controller.get_discovered_devices()


def connect_device(device_address: str) -> bool:
    """
    Connect to a Bluetooth device.
    
    Args:
        device_address (str): Bluetooth device address
    
    Returns:
        bool: True if connected successfully
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot connect: audio module not initialized")
            return False
    
    return _controller.connect_device(device_address)


def disconnect_device() -> bool:
    """
    Disconnect the current Bluetooth device.
    
    Returns:
        bool: True if disconnected successfully
    """
    global _controller
    
    if not _controller:
        return True
    
    return _controller.disconnect_device()


def forget_device(device_address: str) -> bool:
    """
    Remove a paired Bluetooth device.
    
    Args:
        device_address (str): Bluetooth device address
    
    Returns:
        bool: True if device was forgotten
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot forget device: audio module not initialized")
            return False
    
    return _controller.forget_device(device_address)


def get_connected_device() -> Optional[Dict]:
    """
    Get information about the currently connected Bluetooth device.
    
    Returns:
        dict or None: Device information or None if not connected
    """
    global _controller
    
    if not _controller:
        return None
    
    return _controller.get_connected_device()


def is_device_connected() -> bool:
    """
    Check if a Bluetooth device is connected.
    
    Returns:
        bool: True if device is connected
    """
    global _controller
    
    if not _controller:
        return False
    
    return _controller.is_device_connected()


def get_paired_devices() -> List[Dict]:
    """
    Get all paired Bluetooth devices.
    
    Returns:
        list: List of paired device dictionaries
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot get paired devices: audio module not initialized")
            return []
    
    return _controller.get_paired_devices()


def reconnect_last_device() -> bool:
    """
    Attempt to reconnect to the last used Bluetooth device.
    
    Returns:
        bool: True if reconnection was successful
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot reconnect: audio module not initialized")
            return False
    
    return _controller.reconnect_last_device()


def set_auto_reconnect(enabled: bool) -> None:
    """
    Enable or disable automatic reconnection to Bluetooth devices.
    
    Args:
        enabled (bool): Whether to enable auto-reconnect
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot set auto-reconnect: audio module not initialized")
            return
    
    _controller.set_auto_reconnect(enabled)


def get_bluetooth_status() -> Dict:
    """
    Get Bluetooth system status information.
    
    Returns:
        dict: Bluetooth status
    """
    global _controller
    
    if not _controller:
        # Return basic status
        from .bluetooth_manager import get_bluetooth_status as get_basic_status
        return get_basic_status()
    
    # Get status directly from controller but avoid calling self.get_bluetooth_status()
    # to prevent recursion
    # Import here to avoid circular import
    from .bluetooth_manager import get_bluetooth_status as get_basic_status
    status = get_basic_status()
    
    # Add controller-specific info
    if _controller.initialized and _controller.bt_manager:
        connected_device = _controller.bt_manager.get_connected_device()
        status["connected"] = connected_device is not None
        status["device"] = connected_device
        status["auto_reconnect"] = _controller.auto_reconnect
    else:
        status["connected"] = False
        status["device"] = None
        status["auto_reconnect"] = _controller.auto_reconnect
    
    return status


def test_audio_output() -> bool:
    """
    Test audio output using a test sound.
    
    Returns:
        bool: True if test was successful
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot test audio: audio module not initialized")
            return False
        
    return _controller.test_audio_output()

def set_loop(enabled: bool) -> bool:
    """
    Enable or disable looping playback.
    
    Args:
        enabled (bool): Whether to enable looping
        
    Returns:
        bool: New looping state
    """
    global _controller
    
    if not _controller:
        if not initialize():
            logger.warning("Cannot set loop: audio module not initialized")
            return False
    
    return _controller.set_loop(enabled)

def get_loop() -> bool:
    """
    Get current looping state.
    
    Returns:
        bool: Whether looping is enabled
    """
    global _controller
    
    if not _controller:
        return False
    
    return _controller.get_loop()
