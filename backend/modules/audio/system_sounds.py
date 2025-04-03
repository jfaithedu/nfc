"""
System sounds handling for audio module.

Provides functionality for managing and playing system notification sounds.
"""

import os
import logging
import threading
from pathlib import Path
import subprocess

from .exceptions import SystemSoundError

# Set up logger
logger = logging.getLogger(__name__)

# Dictionary to store sound paths
_sounds = {}
_sounds_dir = None
_default_sounds = {
    'error': 'error.wav',
    'success': 'success.wav',
    'info': 'info.wav',
    'warning': 'warning.wav',
}

def initialize_system_sounds(sounds_dir):
    """
    Initialize system sounds from directory.

    Args:
        sounds_dir (str): Directory containing sound files

    Returns:
        bool: True if initialization successful
    """
    global _sounds, _sounds_dir
    
    _sounds_dir = Path(sounds_dir)
    
    if not os.path.exists(_sounds_dir):
        logger.warning(f"Sounds directory does not exist: {_sounds_dir}")
        return False
    
    # Load default sounds if they exist
    for sound_type, filename in _default_sounds.items():
        sound_path = _sounds_dir / filename
        if sound_path.exists():
            _sounds[sound_type] = str(sound_path)
            logger.debug(f"Loaded system sound: {sound_type} -> {sound_path}")
        else:
            logger.warning(f"System sound file not found: {sound_path}")
    
    return len(_sounds) > 0

def play_sound(sound_type, blocking=False):
    """
    Play a system sound.

    Args:
        sound_type (str): Type of sound ('error', 'success', etc.)
        blocking (bool, optional): Wait for sound to complete

    Returns:
        bool: True if sound played successfully
    """
    if sound_type not in _sounds:
        logger.error(f"Sound type not found: {sound_type}")
        return False
    
    sound_path = _sounds[sound_type]
    
    try:
        if blocking:
            # Use aplay for direct playback - blocking call
            subprocess.run(['aplay', sound_path], check=True, 
                          stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        else:
            # Use threading for non-blocking playback
            thread = threading.Thread(
                target=lambda: subprocess.run(['aplay', sound_path], 
                                             stderr=subprocess.PIPE, 
                                             stdout=subprocess.PIPE)
            )
            thread.daemon = True
            thread.start()
        
        logger.debug(f"Playing system sound: {sound_type}")
        return True
    
    except (subprocess.SubprocessError, OSError) as e:
        logger.error(f"Failed to play system sound: {str(e)}")
        raise SystemSoundError(f"Failed to play sound '{sound_type}': {str(e)}")

def get_available_sounds():
    """
    Get list of available system sounds.

    Returns:
        list: List of available sound types
    """
    return list(_sounds.keys())

def add_custom_sound(sound_type, sound_path):
    """
    Add a custom system sound.

    Args:
        sound_type (str): Type of sound
        sound_path (str): Path to sound file

    Returns:
        bool: True if sound added successfully
    """
    sound_path = Path(sound_path)
    
    if not sound_path.exists():
        logger.error(f"Sound file not found: {sound_path}")
        return False
    
    _sounds[sound_type] = str(sound_path)
    logger.debug(f"Added custom sound: {sound_type} -> {sound_path}")
    
    return True
