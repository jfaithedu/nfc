"""
Audio playback handler for the NFC music player.

This module provides audio playback functionality using GStreamer and BlueALSA.
It handles media loading, playback control, and volume management.
"""

import os
import time
import logging
import threading
import subprocess
import json
from typing import Dict, Optional, List, Any, Tuple

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

from .exceptions import (
    AudioError,
    AudioPlaybackError,
    MediaLoadError
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize GStreamer
Gst.init(None)


class AudioPlayer:
    """Handles audio playback using GStreamer and BlueALSA."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize the audio player.
        
        Args:
            config_path (str, optional): Path to the configuration file.
                Default is ~/.audio_player_config.json
        """
        # Configuration
        self.config_path = config_path or os.path.expanduser("~/.audio_player_config.json")
        self.config = self._load_config()
        
        # GStreamer components
        self.playbin = Gst.ElementFactory.make("playbin", "player")
        if not self.playbin:
            raise AudioError("Failed to create GStreamer playbin")
        
        # Playback state tracking
        self.is_loaded = False
        self.current_media = None
        self.duration = -1
        self.muted = False
        self.previous_volume = 50  # Store volume when muted
        
        # Events and threading
        self.bus = self.playbin.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._on_bus_message)
        
        # Set initial volume
        self.set_volume(self.config.get("volume", 50))
        
        # Set up BlueALSA sink
        self._configure_audio_sink()
        
        logger.info("Audio player initialized")
    
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
            return {"volume": 50}
        except Exception as e:
            logger.warning(f"Failed to load audio player config: {e}")
            return {"volume": 50}
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save audio player config: {e}")
    
    def _configure_audio_sink(self) -> None:
        """Configure the audio sink for BlueALSA."""
        try:
            # Check if we should use BlueALSA or default sink
            use_bluealsa = self._is_bluealsa_available()
            
            if use_bluealsa:
                # Get the device path for the connected Bluetooth device
                device_mac = self._get_connected_bluetooth_device()
                if device_mac:
                    # Set up BlueALSA sink
                    audiosink = Gst.ElementFactory.make("alsasink", "audiosink")
                    if audiosink:
                        # Set device property to use BlueALSA
                        device = f"bluealsa:DEV={device_mac},PROFILE=a2dp"
                        audiosink.set_property("device", device)
                        
                        # Configure playbin to use our sink
                        self.playbin.set_property("audio-sink", audiosink)
                        logger.info(f"Using BlueALSA sink for device: {device_mac}")
                        return
            
            # Default: use autoaudiosink (system default)
            audiosink = Gst.ElementFactory.make("autoaudiosink", "audiosink")
            if audiosink:
                self.playbin.set_property("audio-sink", audiosink)
                logger.info("Using default audio sink")
        except Exception as e:
            logger.warning(f"Failed to configure audio sink: {e}")
            logger.info("Falling back to default sink")
    
    def _is_bluealsa_available(self) -> bool:
        """
        Check if BlueALSA is available and running.
        
        Returns:
            bool: True if BlueALSA is available
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "bluealsa"],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() == "active"
        except Exception:
            return False
    
    def _get_connected_bluetooth_device(self) -> Optional[str]:
        """
        Get the MAC address of the connected Bluetooth device.
        
        Returns:
            str or None: MAC address of the connected device or None
        """
        try:
            # Try using bluetoothctl to get connected devices
            result = subprocess.run(
                ["bluetoothctl", "info"],
                capture_output=True,
                text=True
            )
            
            if "Connected: yes" in result.stdout:
                # Extract MAC address from the output
                for line in result.stdout.splitlines():
                    if line.strip().startswith("Device "):
                        return line.strip().split(" ")[1]
            
            # Alternative: check bluealsa-aplay -l output
            result = subprocess.run(
                ["bluealsa-aplay", "-l"],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.splitlines():
                if ":" in line:  # MAC addresses contain colons
                    parts = line.split(" ")
                    for part in parts:
                        if ":" in part and len(part) == 17:  # Standard MAC address length
                            return part
            
            return None
        except Exception as e:
            logger.warning(f"Failed to get connected Bluetooth device: {e}")
            return None
    
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
            logger.error(f"GStreamer error: {err}, {debug}")
            self.stop()
        
        elif t == Gst.MessageType.EOS:
            logger.info("End of stream reached")
            self.stop()
        
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.playbin:
                old_state, new_state, pending_state = message.parse_state_changed()
                
                # Update duration when transitioning to PAUSED or PLAYING
                if (new_state == Gst.State.PAUSED or new_state == Gst.State.PLAYING) and self.duration < 0:
                    self._update_duration()
    
    def _update_duration(self) -> None:
        """Update the duration of the current media."""
        success, duration = self.playbin.query_duration(Gst.Format.TIME)
        if success:
            self.duration = duration / Gst.SECOND
            logger.debug(f"Media duration: {self.duration} seconds")
    
    def load_media(self, media_path: str) -> bool:
        """
        Load a media file for playback.
        
        Args:
            media_path (str): Path to media file
        
        Returns:
            bool: True if media loaded successfully
        
        Raises:
            MediaLoadError: If media cannot be loaded
        """
        if not os.path.exists(media_path):
            raise MediaLoadError(f"Media file not found: {media_path}")
        
        try:
            # Stop any current playback
            if self.is_loaded:
                self.stop()
            
            # Update sink configuration (in case Bluetooth status changed)
            self._configure_audio_sink()
            
            # Set the URI
            media_uri = Gst.filename_to_uri(media_path)
            self.playbin.set_property("uri", media_uri)
            
            # Reset duration
            self.duration = -1
            
            # Pre-roll to PAUSED state to prepare media
            self.playbin.set_state(Gst.State.PAUSED)
            
            # Wait for pre-roll to complete
            state_change_result = self.playbin.get_state(Gst.CLOCK_TIME_NONE)
            if state_change_result[0] != Gst.StateChangeReturn.SUCCESS:
                raise MediaLoadError(
                    f"Failed to pre-roll media: {state_change_result[0]}"
                )
            
            # Update duration
            self._update_duration()
            
            # Update state
            self.is_loaded = True
            self.current_media = media_path
            
            logger.info(f"Media loaded: {media_path}")
            return True
        
        except Exception as e:
            # Clean up on failure
            self.playbin.set_state(Gst.State.NULL)
            self.is_loaded = False
            self.current_media = None
            
            logger.error(f"Failed to load media {media_path}: {e}")
            raise MediaLoadError(f"Failed to load media: {e}")
    
    def play(self) -> bool:
        """
        Start playback of loaded media.
        
        Returns:
            bool: True if playback started
        
        Raises:
            AudioPlaybackError: If playback cannot be started
        """
        if not self.is_loaded:
            raise AudioPlaybackError("No media loaded")
        
        try:
            result = self.playbin.set_state(Gst.State.PLAYING)
            if result == Gst.StateChangeReturn.FAILURE:
                raise AudioPlaybackError("Failed to start playback")
            
            logger.info(f"Started playback of {self.current_media}")
            return True
        
        except Exception as e:
            logger.error(f"Playback error: {e}")
            raise AudioPlaybackError(f"Playback error: {e}")
    
    def pause(self) -> bool:
        """
        Pause current playback.
        
        Returns:
            bool: True if paused
        """
        if not self.is_loaded:
            logger.warning("Cannot pause: no media loaded")
            return False
        
        try:
            self.playbin.set_state(Gst.State.PAUSED)
            logger.info("Playback paused")
            return True
        
        except Exception as e:
            logger.error(f"Failed to pause: {e}")
            return False
    
    def resume(self) -> bool:
        """
        Resume paused playback.
        
        Returns:
            bool: True if resumed
        """
        if not self.is_loaded:
            logger.warning("Cannot resume: no media loaded")
            return False
        
        # Check if currently paused
        _, current_state, _ = self.playbin.get_state(0)
        if current_state != Gst.State.PAUSED:
            logger.warning("Cannot resume: not paused")
            return False
        
        try:
            self.playbin.set_state(Gst.State.PLAYING)
            logger.info("Playback resumed")
            return True
        
        except Exception as e:
            logger.error(f"Failed to resume: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop current playback.
        
        Returns:
            bool: True if stopped
        """
        try:
            self.playbin.set_state(Gst.State.NULL)
            logger.info("Playback stopped")
            return True
        
        except Exception as e:
            logger.error(f"Failed to stop: {e}")
            return False
        
        finally:
            # Reset state regardless of success
            self.is_loaded = False
            self.current_media = None
            self.duration = -1
    
    def seek(self, position_seconds: int) -> bool:
        """
        Seek to position in current media.
        
        Args:
            position_seconds (int): Position in seconds
        
        Returns:
            bool: True if seek successful
        """
        if not self.is_loaded:
            logger.warning("Cannot seek: no media loaded")
            return False
        
        try:
            # Convert to nanoseconds
            position_ns = position_seconds * Gst.SECOND
            
            # Perform seek
            result = self.playbin.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                position_ns
            )
            
            if result:
                logger.info(f"Seeked to position {position_seconds}s")
            else:
                logger.warning(f"Failed to seek to {position_seconds}s")
                
            return result
        
        except Exception as e:
            logger.error(f"Seek error: {e}")
            return False
    
    def get_position(self) -> int:
        """
        Get current playback position.
        
        Returns:
            int: Current position in seconds or -1 if unknown
        """
        if not self.is_loaded:
            return -1
        
        try:
            success, position = self.playbin.query_position(Gst.Format.TIME)
            if success:
                return int(position / Gst.SECOND)
            return -1
        
        except Exception:
            return -1
    
    def get_duration(self) -> int:
        """
        Get loaded media duration.
        
        Returns:
            int: Duration in seconds or -1 if unknown
        """
        if not self.is_loaded or self.duration < 0:
            # Try to update duration
            self._update_duration()
            
        return int(self.duration)
    
    def set_volume(self, level: int) -> int:
        """
        Set volume level.
        
        Args:
            level (int): Volume level (0-100)
        
        Returns:
            int: New volume level
        """
        # Ensure level is within valid range
        level = max(0, min(100, level))
        
        try:
            # Convert to GStreamer volume (0.0 to 1.0)
            volume = level / 100.0
            self.playbin.set_property("volume", volume)
            
            # Update config
            self.config["volume"] = level
            self._save_config()
            
            # If we were muted, we're not anymore
            if self.muted:
                self.muted = False
            
            logger.info(f"Volume set to {level}")
            return level
        
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return self.get_volume()
    
    def get_volume(self) -> int:
        """
        Get current volume level.
        
        Returns:
            int: Current volume level (0-100)
        """
        try:
            volume = self.playbin.get_property("volume")
            # Convert from GStreamer volume (0.0 to 1.0) to percentage
            return int(volume * 100)
        
        except Exception:
            return self.config.get("volume", 50)
    
    def mute(self) -> bool:
        """
        Mute audio output.
        
        Returns:
            bool: True if muted
        """
        if self.muted:
            return True
        
        try:
            self.previous_volume = self.get_volume()
            self.playbin.set_property("volume", 0.0)
            self.muted = True
            logger.info("Audio muted")
            return True
        
        except Exception as e:
            logger.error(f"Failed to mute: {e}")
            return False
    
    def unmute(self) -> bool:
        """
        Unmute audio output.
        
        Returns:
            bool: True if unmuted
        """
        if not self.muted:
            return True
        
        try:
            volume = self.previous_volume / 100.0
            self.playbin.set_property("volume", volume)
            self.muted = False
            logger.info("Audio unmuted")
            return True
        
        except Exception as e:
            logger.error(f"Failed to unmute: {e}")
            return False
    
    def get_state(self) -> str:
        """
        Get current playback state.
        
        Returns:
            str: State ('playing', 'paused', 'stopped')
        """
        if not self.is_loaded:
            return "stopped"
        
        try:
            _, state, _ = self.playbin.get_state(0)
            
            if state == Gst.State.PLAYING:
                return "playing"
            elif state == Gst.State.PAUSED:
                return "paused"
            else:
                return "stopped"
        
        except Exception:
            return "stopped"
    
    def get_status(self) -> Dict:
        """
        Get complete playback status.
        
        Returns:
            dict: Playback status
        """
        return {
            "state": self.get_state(),
            "position": self.get_position(),
            "duration": self.get_duration(),
            "volume": self.get_volume(),
            "muted": self.muted,
            "media": self.current_media
        }
    
    def shutdown(self) -> None:
        """Perform cleanup before shutdown."""
        try:
            # Stop playback
            self.stop()
            
            # Save config
            self._save_config()
            
            # Remove signal watch
            self.bus.remove_signal_watch()
            
            logger.info("Audio player shutdown complete")
        
        except Exception as e:
            logger.error(f"Error during audio player shutdown: {e}")


def test_audio_output(device_address: str = None) -> bool:
    """
    Test audio output using BlueALSA.
    
    Args:
        device_address (str, optional): Bluetooth device address to test.
            If None, uses the system default audio output.
    
    Returns:
        bool: True if test was successful
    """
    try:
        test_file = "/usr/share/sounds/alsa/Front_Center.wav"
        
        # Use bluealsa-aplay if device address is provided and test file exists
        if device_address and os.path.exists(test_file):
            result = subprocess.run(
                ["bluealsa-aplay", device_address, test_file],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        
        # Otherwise use regular aplay
        elif os.path.exists(test_file):
            result = subprocess.run(
                ["aplay", test_file],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        
        logger.warning("Test audio file not found")
        return False
    
    except Exception as e:
        logger.error(f"Audio test failed: {e}")
        return False