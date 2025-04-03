"""
System sounds module for NFC music player.

This module provides functionality to play system notification sounds
like success, error, and information alerts.
"""

import os
import glob
import logging
import threading
import time
from typing import Dict, List, Optional

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

from .exceptions import SystemSoundError

# Configure logging
logger = logging.getLogger(__name__)

# Initialize GStreamer
Gst.init(None)


class SystemSoundPlayer:
    """Handles system notification sounds."""
    
    def __init__(self, sounds_dir: str = None):
        """
        Initialize system sound player.
        
        Args:
            sounds_dir (str, optional): Directory containing sound files.
                Default is ~/sounds or /usr/share/sounds if it exists.
        """
        # Find sounds directory
        self.sounds_dir = sounds_dir
        if not self.sounds_dir:
            # Try home directory first
            home_sounds = os.path.expanduser("~/sounds")
            if os.path.isdir(home_sounds):
                self.sounds_dir = home_sounds
            # Fall back to system sounds
            elif os.path.isdir("/usr/share/sounds"):
                self.sounds_dir = "/usr/share/sounds"
            else:
                # Create the directory if it doesn't exist
                os.makedirs(home_sounds, exist_ok=True)
                self.sounds_dir = home_sounds
        
        # Sound file cache
        self.sounds = {}
        self.is_playing = False
        self.current_player = None
        
        # Initialize player
        self.playbin = Gst.ElementFactory.make("playbin", "sysplayer")
        if not self.playbin:
            logger.error("Failed to create GStreamer playbin for system sounds")
            return
        
        # Set up message bus
        self.bus = self.playbin.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._on_bus_message)
        
        # Set lower volume for system sounds (70% of normal)
        self.playbin.set_property("volume", 0.7)
        
        # Load available sounds
        self._load_sound_files()
        
        logger.info(f"System sound player initialized with directory: {self.sounds_dir}")
    
    def _load_sound_files(self) -> None:
        """Scan sound directory and load available sounds."""
        try:
            # Search for wav, mp3 and ogg files
            sound_files = []
            for ext in ["wav", "mp3", "ogg"]:
                sound_files.extend(glob.glob(os.path.join(self.sounds_dir, f"*.{ext}")))
                sound_files.extend(glob.glob(os.path.join(self.sounds_dir, f"**/*.{ext}")))
            
            # Store sounds by name (without extension)
            for sound_file in sound_files:
                name = os.path.splitext(os.path.basename(sound_file))[0].lower()
                self.sounds[name] = sound_file
            
            logger.info(f"Loaded {len(self.sounds)} system sounds")
        except Exception as e:
            logger.error(f"Failed to load system sounds: {e}")
    
    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message) -> None:
        """
        Handle GStreamer bus messages.
        
        Args:
            bus: GStreamer bus
            message: GStreamer message
        """
        t = message.type
        
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"System sound error: {err}, {debug}")
            self._reset_player()
        
        elif t == Gst.MessageType.EOS:
            logger.debug("System sound playback complete")
            self._reset_player()
    
    def _reset_player(self) -> None:
        """Reset player state after playback."""
        self.playbin.set_state(Gst.State.NULL)
        self.is_playing = False
        self.current_player = None
    
    def play(self, sound_type: str, blocking: bool = False) -> bool:
        """
        Play a system sound.
        
        Args:
            sound_type (str): Type of sound ('error', 'success', etc.)
            blocking (bool, optional): Wait for sound to complete
        
        Returns:
            bool: True if sound played successfully
        
        Raises:
            SystemSoundError: If sound cannot be played
        """
        # Convert to lowercase for lookup
        sound_type = sound_type.lower()
        
        # Check if sound exists
        if sound_type not in self.sounds:
            logger.warning(f"Sound not found: {sound_type}")
            return False
        
        # Get sound file path
        sound_path = self.sounds[sound_type]
        
        try:
            # Check if already playing something
            if self.is_playing:
                # Stop current playback
                self.playbin.set_state(Gst.State.NULL)
            
            # Set up URI
            sound_uri = Gst.filename_to_uri(sound_path)
            self.playbin.set_property("uri", sound_uri)
            
            # Start playback
            self.playbin.set_state(Gst.State.PLAYING)
            self.is_playing = True
            
            # If blocking, wait for completion
            if blocking:
                while self.is_playing:
                    time.sleep(0.1)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to play system sound {sound_type}: {e}")
            self._reset_player()
            raise SystemSoundError(f"Failed to play system sound: {e}")
    
    def play_async(self, sound_type: str) -> bool:
        """
        Play a system sound asynchronously.
        
        Args:
            sound_type (str): Type of sound ('error', 'success', etc.)
        
        Returns:
            bool: True if sound started playing
        """
        try:
            t = threading.Thread(target=self.play, args=(sound_type, False))
            t.daemon = True
            t.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start async sound playback: {e}")
            return False
    
    def get_available_sounds(self) -> List[str]:
        """
        Get list of available system sounds.
        
        Returns:
            list: List of available sound types
        """
        return sorted(list(self.sounds.keys()))
    
    def add_custom_sound(self, sound_type: str, sound_path: str) -> bool:
        """
        Add a custom system sound.
        
        Args:
            sound_type (str): Type of sound
            sound_path (str): Path to sound file
        
        Returns:
            bool: True if sound added successfully
        """
        # Validate sound file
        if not os.path.exists(sound_path):
            logger.error(f"Sound file not found: {sound_path}")
            return False
        
        try:
            # Copy file to sounds directory
            sound_type = sound_type.lower()
            file_ext = os.path.splitext(sound_path)[1]
            target_path = os.path.join(self.sounds_dir, f"{sound_type}{file_ext}")
            
            # Read source file and write to target
            with open(sound_path, 'rb') as src, open(target_path, 'wb') as dst:
                dst.write(src.read())
            
            # Add to sounds dictionary
            self.sounds[sound_type] = target_path
            
            logger.info(f"Added custom sound: {sound_type}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add custom sound: {e}")
            return False
    
    def shutdown(self) -> None:
        """Clean up resources before shutdown."""
        try:
            if self.is_playing:
                self.playbin.set_state(Gst.State.NULL)
            
            self.bus.remove_signal_watch()
            logger.info("System sound player shutdown complete")
        
        except Exception as e:
            logger.error(f"Error during system sound player shutdown: {e}")


# Module-level instance for simple usage
_system_sounds: Optional[SystemSoundPlayer] = None


def initialize_system_sounds(sounds_dir: str = None) -> bool:
    """
    Initialize system sounds from directory.
    
    Args:
        sounds_dir (str, optional): Directory containing sound files
    
    Returns:
        bool: True if initialization successful
    """
    global _system_sounds
    
    try:
        _system_sounds = SystemSoundPlayer(sounds_dir)
        return True
    except Exception as e:
        logger.error(f"Failed to initialize system sounds: {e}")
        return False


def play_sound(sound_type: str, blocking: bool = False) -> bool:
    """
    Play a system sound.
    
    Args:
        sound_type (str): Type of sound ('error', 'success', etc.)
        blocking (bool, optional): Wait for sound to complete
    
    Returns:
        bool: True if sound played successfully
    """
    global _system_sounds
    
    if not _system_sounds:
        logger.warning("System sounds not initialized")
        return False
    
    try:
        if blocking:
            return _system_sounds.play(sound_type, True)
        else:
            return _system_sounds.play_async(sound_type)
    except Exception as e:
        logger.error(f"Error playing system sound {sound_type}: {e}")
        return False


def get_available_sounds() -> List[str]:
    """
    Get list of available system sounds.
    
    Returns:
        list: List of available sound types
    """
    global _system_sounds
    
    if not _system_sounds:
        logger.warning("System sounds not initialized")
        return []
    
    return _system_sounds.get_available_sounds()


def add_custom_sound(sound_type: str, sound_path: str) -> bool:
    """
    Add a custom system sound.
    
    Args:
        sound_type (str): Type of sound
        sound_path (str): Path to sound file
    
    Returns:
        bool: True if sound added successfully
    """
    global _system_sounds
    
    if not _system_sounds:
        logger.warning("System sounds not initialized")
        return False
    
    return _system_sounds.add_custom_sound(sound_type, sound_path)


def shutdown() -> None:
    """Clean up system sounds resources."""
    global _system_sounds
    
    if _system_sounds:
        _system_sounds.shutdown()
        _system_sounds = None