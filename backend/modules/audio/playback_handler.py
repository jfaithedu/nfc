"""
Audio playback handler for the NFC music player.

Handles audio playback using GStreamer and provides interface for controlling media playback.
"""

import os
import logging
import time
import threading
import gi

# Import GStreamer
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

from .exceptions import MediaLoadError, AudioPlaybackError

# Set up logger
logger = logging.getLogger(__name__)

# Playback states
STATE_STOPPED = 'stopped'
STATE_PLAYING = 'playing'
STATE_PAUSED = 'paused'

class AudioPlayer:
    """
    Handles audio playback using GStreamer.
    """

    def __init__(self):
        """
        Initialize the audio player.
        """
        # Initialize GStreamer
        Gst.init(None)
        
        # Create GStreamer pipeline and elements
        self._pipeline = Gst.Pipeline.new("audio-player")
        self._source = Gst.ElementFactory.make("filesrc", "file-source")
        self._decoder = Gst.ElementFactory.make("decodebin", "decoder")
        self._converter = Gst.ElementFactory.make("audioconvert", "converter")
        self._volume = Gst.ElementFactory.make("volume", "volume")
        self._sink = Gst.ElementFactory.make("autoaudiosink", "audio-sink")
        
        # Check if all elements were created successfully
        elements = [self._pipeline, self._source, self._decoder, 
                   self._converter, self._volume, self._sink]
        
        if any(element is None for element in elements):
            missing = [name for name, element in zip(
                ["Pipeline", "Source", "Decoder", "Converter", "Volume", "Sink"], 
                elements) if element is None]
            logger.error(f"Failed to create GStreamer elements: {', '.join(missing)}")
            raise AudioPlaybackError(f"Could not create GStreamer elements: {', '.join(missing)}")
        
        # Add elements to pipeline
        self._pipeline.add(self._source)
        self._pipeline.add(self._decoder)
        self._pipeline.add(self._converter)
        self._pipeline.add(self._volume)
        self._pipeline.add(self._sink)
        
        # Link elements that can be linked statically
        self._source.link(self._decoder)
        self._converter.link(self._volume)
        self._volume.link(self._sink)
        
        # Connect dynamic link function for decoder
        self._decoder.connect("pad-added", self._on_pad_added)
        
        # Create bus to get events from GStreamer pipeline
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._on_message)
        
        # Set up mainloop for GStreamer
        self._main_loop = GLib.MainLoop()
        self._thread = threading.Thread(target=self._main_loop.run)
        self._thread.daemon = True
        self._thread.start()
        
        # Initialize state
        self._current_media = None
        self._state = STATE_STOPPED
        self._duration = -1
        self._volume_level = 100  # 0-100 range
        self._muted = False
        self._prev_volume = 100
        
        logger.debug("AudioPlayer initialized")

    def _on_pad_added(self, element, pad):
        """Handle dynamic pad connection when decoder finds stream info."""
        if pad.get_current_caps().to_string().startswith("audio/"):
            if not pad.is_linked():
                sink_pad = self._converter.get_static_pad("sink")
                if not sink_pad.is_linked():
                    pad.link(sink_pad)

    def _on_message(self, bus, message):
        """Handle GStreamer message bus events."""
        t = message.type
        
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"GStreamer error: {err} ({debug})")
            self.stop()
            
        elif t == Gst.MessageType.EOS:
            logger.debug("End of stream reached")
            self.stop()
            
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self._pipeline:
                old_state, new_state, pending_state = message.parse_state_changed()
                logger.debug(f"Pipeline state changed from {old_state.value_nick} to {new_state.value_nick}")
                
                # Update internal state tracking
                if new_state == Gst.State.PLAYING:
                    self._state = STATE_PLAYING
                elif new_state == Gst.State.PAUSED:
                    self._state = STATE_PAUSED
                elif new_state == Gst.State.NULL:
                    self._state = STATE_STOPPED

    def load_media(self, media_path):
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
            logger.error(f"Media file not found: {media_path}")
            raise MediaLoadError(f"File not found: {media_path}")
        
        logger.debug(f"Loading media: {media_path}")
        
        # Stop any current playback
        self.stop()
        
        # Set new source path
        self._source.set_property("location", media_path)
        self._current_media = media_path
        
        # Reset state
        self._duration = -1
        
        # Try to get duration by loading media in paused state
        if self._pipeline.set_state(Gst.State.PAUSED) == Gst.StateChangeReturn.FAILURE:
            logger.error(f"Failed to load media: {media_path}")
            self._pipeline.set_state(Gst.State.NULL)
            raise MediaLoadError(f"Failed to load media: {media_path}")
        
        # Query duration (with timeout to prevent blocking)
        start_time = time.time()
        while self._duration < 0 and time.time() - start_time < 3.0:
            success, duration = self._pipeline.query_duration(Gst.Format.TIME)
            if success:
                self._duration = duration / Gst.SECOND
                break
            time.sleep(0.1)
        
        logger.debug(f"Media loaded: {media_path} (Duration: {self._duration:.2f}s)")
        return True

    def play(self):
        """
        Start playback of loaded media.

        Returns:
            bool: True if playback started
        """
        if not self._current_media:
            logger.warning("Cannot play: No media loaded")
            return False
        
        logger.debug("Starting playback")
        result = self._pipeline.set_state(Gst.State.PLAYING)
        
        if result == Gst.StateChangeReturn.FAILURE:
            logger.error("Failed to start playback")
            raise AudioPlaybackError("Failed to start playback")
        
        self._state = STATE_PLAYING
        return True

    def pause(self):
        """
        Pause current playback.

        Returns:
            bool: True if paused
        """
        if self._state != STATE_PLAYING:
            logger.warning("Cannot pause: Not currently playing")
            return False
        
        logger.debug("Pausing playback")
        result = self._pipeline.set_state(Gst.State.PAUSED)
        
        if result == Gst.StateChangeReturn.FAILURE:
            logger.error("Failed to pause playback")
            raise AudioPlaybackError("Failed to pause playback")
        
        self._state = STATE_PAUSED
        return True

    def resume(self):
        """
        Resume paused playback.

        Returns:
            bool: True if resumed
        """
        if self._state != STATE_PAUSED:
            logger.warning("Cannot resume: Not currently paused")
            return False
        
        logger.debug("Resuming playback")
        return self.play()

    def stop(self):
        """
        Stop current playback.

        Returns:
            bool: True if stopped
        """
        logger.debug("Stopping playback")
        result = self._pipeline.set_state(Gst.State.NULL)
        
        if result == Gst.StateChangeReturn.FAILURE:
            logger.error("Failed to stop playback")
            raise AudioPlaybackError("Failed to stop playback")
        
        self._state = STATE_STOPPED
        return True

    def seek(self, position_seconds):
        """
        Seek to position in current media.

        Args:
            position_seconds (int): Position in seconds

        Returns:
            bool: True if seek successful
        """
        if not self._current_media:
            logger.warning("Cannot seek: No media loaded")
            return False
        
        # Ensure position is within valid range
        position_seconds = max(0, min(position_seconds, self.get_duration()))
        position_ns = position_seconds * Gst.SECOND
        
        logger.debug(f"Seeking to position: {position_seconds:.2f}s")
        
        # Perform seek operation
        result = self._pipeline.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            position_ns
        )
        
        if not result:
            logger.error(f"Failed to seek to position: {position_seconds:.2f}s")
            raise AudioPlaybackError(f"Failed to seek to position: {position_seconds:.2f}s")
        
        return True

    def get_position(self):
        """
        Get current playback position.

        Returns:
            int: Current position in seconds
        """
        if not self._current_media or self._state == STATE_STOPPED:
            return 0
        
        success, position = self._pipeline.query_position(Gst.Format.TIME)
        
        if not success:
            logger.warning("Failed to query position")
            return 0
        
        return position / Gst.SECOND

    def get_duration(self):
        """
        Get loaded media duration.

        Returns:
            int: Duration in seconds
        """
        if self._duration > 0:
            return self._duration
        
        if not self._current_media:
            return 0
        
        success, duration = self._pipeline.query_duration(Gst.Format.TIME)
        
        if not success:
            logger.warning("Failed to query duration")
            return 0
        
        self._duration = duration / Gst.SECOND
        return self._duration

    def set_volume(self, level):
        """
        Set volume level.

        Args:
            level (int): Volume level (0-100)

        Returns:
            int: New volume level
        """
        # Ensure level is within valid range
        level = max(0, min(100, level))
        
        # Convert to GStreamer volume (0.0 to 1.0)
        gst_volume = level / 100.0
        
        logger.debug(f"Setting volume to {level}% ({gst_volume:.2f})")
        self._volume.set_property("volume", gst_volume)
        
        self._volume_level = level
        self._muted = (level == 0)
        
        return level

    def get_volume(self):
        """
        Get current volume level.

        Returns:
            int: Current volume level (0-100)
        """
        # Get volume from GStreamer
        gst_volume = self._volume.get_property("volume")
        
        # Convert to 0-100 range
        self._volume_level = int(gst_volume * 100)
        
        return self._volume_level

    def mute(self):
        """
        Mute audio output.

        Returns:
            bool: True if muted
        """
        if not self._muted:
            logger.debug("Muting audio")
            self._prev_volume = self.get_volume()
            self.set_volume(0)
            self._muted = True
        
        return True

    def unmute(self):
        """
        Unmute audio output.

        Returns:
            bool: True if unmuted
        """
        if self._muted:
            logger.debug(f"Unmuting audio (restoring volume to {self._prev_volume}%)")
            self.set_volume(self._prev_volume)
            self._muted = False
        
        return True

    def get_state(self):
        """
        Get current playback state.

        Returns:
            str: State ('playing', 'paused', 'stopped')
        """
        return self._state
