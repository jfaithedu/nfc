# Audio Module - Implementation Guide

## Overview

The Audio Module is responsible for handling all audio playback functionality for the NFC music player. It manages Bluetooth connectivity, audio streaming, volume control, and playback status. This module provides a reliable audio interface that works with Bluetooth speakers and ensures consistent playback experience.

## Core Responsibilities

1. Manage Bluetooth device connections
2. Control audio playback (play, pause, stop, seek)
3. Handle volume adjustments and mute functionality
4. Manage playback state and provide status information
5. Play system sounds (error, success notifications)
6. Support Bluetooth device discovery and pairing

## Implementation Details

### File Structure

```
audio/
├── __init__.py                 # Package initialization
├── audio_controller.py         # Main controller exposed to other modules
├── bluetooth_manager.py        # Bluetooth device management
├── playback_handler.py         # Audio playback functionality
├── system_sounds.py            # System notification sounds
└── exceptions.py               # Audio-specific exception definitions
```

### Key Components

#### 1. Audio Controller (`audio_controller.py`)

This is the main interface exposed to other modules:

```python
def initialize():
    """
    Initialize the audio subsystem.
    Connect to the last used Bluetooth device if available.

    Returns:
        bool: True if initialization successful
    """

def shutdown():
    """
    Perform clean shutdown of audio subsystem.
    """

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

def pause():
    """
    Pause current playback.

    Returns:
        bool: True if paused successfully
    """

def resume():
    """
    Resume paused playback.

    Returns:
        bool: True if resumed successfully
    """

def stop():
    """
    Stop current playback.

    Returns:
        bool: True if stopped successfully
    """

def seek(position_seconds):
    """
    Seek to a specific position in the current track.

    Args:
        position_seconds (int): Position in seconds

    Returns:
        bool: True if seek successful
    """

def set_volume(level):
    """
    Set volume level.

    Args:
        level (int): Volume level (0-100)

    Returns:
        int: New volume level
    """

def get_volume():
    """
    Get current volume level.

    Returns:
        int: Current volume level (0-100)
    """

def mute():
    """
    Mute audio output.

    Returns:
        bool: True if muted
    """

def unmute():
    """
    Unmute audio output.

    Returns:
        bool: True if unmuted
    """

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

def play_system_sound(sound_type):
    """
    Play a system notification sound.

    Args:
        sound_type (str): Type of sound ('error', 'success', etc.)

    Returns:
        bool: True if sound played successfully
    """

def play_error_sound():
    """
    Play the error notification sound.

    Returns:
        bool: True if sound played successfully
    """

def play_success_sound():
    """
    Play the success notification sound.

    Returns:
        bool: True if sound played successfully
    """
```

#### 2. Bluetooth Manager (`bluetooth_manager.py`)

Handles Bluetooth device management:

```python
class BluetoothManager:
    """
    Manages Bluetooth connections and device discovery.
    """

    def __init__(self):
        """
        Initialize the Bluetooth manager.
        """

    def start_discovery(self, timeout=30):
        """
        Start discovery for Bluetooth devices.

        Args:
            timeout (int, optional): Discovery timeout in seconds

        Returns:
            bool: True if discovery started
        """

    def get_discovered_devices(self):
        """
        Get list of discovered devices.

        Returns:
            list: List of device dictionaries with name, address, and type
        """

    def stop_discovery(self):
        """
        Stop the discovery process.

        Returns:
            bool: True if discovery stopped
        """

    def connect_device(self, device_address):
        """
        Connect to a Bluetooth device.

        Args:
            device_address (str): Bluetooth device address

        Returns:
            bool: True if connected successfully

        Raises:
            BluetoothConnectionError: If connection fails
        """

    def disconnect_device(self):
        """
        Disconnect the current device.

        Returns:
            bool: True if disconnected successfully
        """

    def get_connected_device(self):
        """
        Get information about the currently connected device.

        Returns:
            dict or None: Device information or None if not connected
        """

    def is_device_connected(self, device_address=None):
        """
        Check if a device is connected.

        Args:
            device_address (str, optional): Device to check, or current device if None

        Returns:
            bool: True if device is connected
        """

    def save_paired_device(self, device_address, device_name):
        """
        Save a device as the preferred device.

        Args:
            device_address (str): Bluetooth device address
            device_name (str): Human-readable device name

        Returns:
            bool: True if saved successfully
        """

    def get_saved_devices(self):
        """
        Get all saved devices.

        Returns:
            list: List of saved device dictionaries
        """
```

#### 3. Playback Handler (`playback_handler.py`)

Handles audio playback functionality:

```python
class AudioPlayer:
    """
    Handles audio playback using PulseAudio and BlueAlsa.
    """

    def __init__(self):
        """
        Initialize the audio player.
        """

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

    def play(self):
        """
        Start playback of loaded media.

        Returns:
            bool: True if playback started
        """

    def pause(self):
        """
        Pause current playback.

        Returns:
            bool: True if paused
        """

    def resume(self):
        """
        Resume paused playback.

        Returns:
            bool: True if resumed
        """

    def stop(self):
        """
        Stop current playback.

        Returns:
            bool: True if stopped
        """

    def seek(self, position_seconds):
        """
        Seek to position in current media.

        Args:
            position_seconds (int): Position in seconds

        Returns:
            bool: True if seek successful
        """

    def get_position(self):
        """
        Get current playback position.

        Returns:
            int: Current position in seconds
        """

    def get_duration(self):
        """
        Get loaded media duration.

        Returns:
            int: Duration in seconds
        """

    def set_volume(self, level):
        """
        Set volume level.

        Args:
            level (int): Volume level (0-100)

        Returns:
            int: New volume level
        """

    def get_volume(self):
        """
        Get current volume level.

        Returns:
            int: Current volume level (0-100)
        """

    def mute(self):
        """
        Mute audio output.

        Returns:
            bool: True if muted
        """

    def unmute(self):
        """
        Unmute audio output.

        Returns:
            bool: True if unmuted
        """

    def get_state(self):
        """
        Get current playback state.

        Returns:
            str: State ('playing', 'paused', 'stopped')
        """
```

#### 4. System Sounds (`system_sounds.py`)

Handles system notification sounds:

```python
def initialize_system_sounds(sounds_dir):
    """
    Initialize system sounds from directory.

    Args:
        sounds_dir (str): Directory containing sound files

    Returns:
        bool: True if initialization successful
    """

def play_sound(sound_type, blocking=False):
    """
    Play a system sound.

    Args:
        sound_type (str): Type of sound ('error', 'success', etc.)
        blocking (bool, optional): Wait for sound to complete

    Returns:
        bool: True if sound played successfully
    """

def get_available_sounds():
    """
    Get list of available system sounds.

    Returns:
        list: List of available sound types
    """

def add_custom_sound(sound_type, sound_path):
    """
    Add a custom system sound.

    Args:
        sound_type (str): Type of sound
        sound_path (str): Path to sound file

    Returns:
        bool: True if sound added successfully
    """
```

#### 5. Exceptions (`exceptions.py`)

Define audio-specific exceptions:

```python
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
```

### Bluetooth Audio Integration

#### 1. Setting up Bluetooth Audio

For Bluetooth audio on Raspberry Pi Zero 2 W, follow these guidelines:

1. **BlueAlsa Configuration**:

   - Use `bluealsa` as the primary audio backend
   - Configure for high-quality audio profiles (A2DP)
   - Handle automatic reconnection to paired devices

2. **Device Management**:

   - Use D-Bus for communication with BlueZ (Bluetooth stack)
   - Implement proper power management for Bluetooth
   - Handle pairing and connection security

3. **Audio Routing**:
   - Route audio through PulseAudio to BlueAlsa
   - Configure proper audio sink selection
   - Handle fallback to local audio if Bluetooth unavailable

#### 2. Connection Management

1. **Device Discovery**:

   - Implement efficient Bluetooth scanning
   - Filter for audio-capable devices only
   - Handle discovery timeouts gracefully

2. **Pairing Process**:

   - Implement secure pairing procedures
   - Store paired device information securely
   - Handle pairing failures with clear error messages

3. **Connection Reliability**:
   - Implement automatic reconnection to last paired device
   - Handle connection drops gracefully
   - Provide clear feedback on connection status

### Audio Playback

#### 1. Playback Implementation

1. **Playback Engine**:

   - Use reliable audio libraries (e.g., GStreamer)
   - Support multiple audio formats (MP3, WAV, OGG, etc.)
   - Implement proper buffering for smooth playback

2. **Stream Management**:

   - Handle audio streaming without gaps
   - Implement proper queuing for continuous playback
   - Support seeking and position control

3. **Format Support**:
   - Verify format compatibility with Bluetooth device
   - Implement format conversion if necessary
   - Handle metadata extraction from audio files

#### 2. Volume and Equalization

1. **Volume Control**:

   - Implement smooth volume transitions
   - Support device-specific volume ranges
   - Store and restore previous volume levels

2. **Audio Processing**:
   - Consider implementing basic equalization for children's audio
   - Limit maximum volume to protect young ears
   - Normalize audio levels across different sources

### Performance Considerations

#### 1. Latency

1. **Bluetooth Latency**:

   - Optimize Bluetooth connections for minimal latency
   - Pre-buffer audio to compensate for Bluetooth delay
   - Implement adaptive buffering based on connection quality

2. **Playback Responsiveness**:
   - Minimize delay between tag detection and audio playback
   - Optimize file loading and stream initialization
   - Cache frequently played audio for instant playback

#### 2. Resource Usage

1. **CPU Usage**:

   - Monitor and optimize CPU usage during playback
   - Implement proper thread management
   - Consider dedicated audio processing thread

2. **Memory Management**:
   - Implement proper buffer management
   - Avoid memory leaks in long-running playback
   - Release resources properly when not in use

### Error Handling and Resilience

#### 1. Connection Issues

1. **Connection Failures**:

   - Implement automatic retry for Bluetooth connections
   - Provide clear feedback for connection failures
   - Gracefully handle device unavailability

2. **Playback Recovery**:
   - Auto-resume playback after connection drops
   - Maintain playback state during connectivity issues
   - Implement timeout and retry logic for transient errors

#### 2. Audio Problems

1. **Playback Errors**:

   - Handle corrupt or incompatible audio files
   - Implement fallback options for failed playback
   - Log detailed error information for troubleshooting

2. **Device Compatibility**:
   - Handle different Bluetooth audio profiles
   - Address common compatibility issues with popular speakers
   - Provide workarounds for known device-specific problems

### System Integration

#### 1. System Audio

1. **System Sounds**:

   - Implement system sound playback without interrupting media
   - Use separate audio channel for system notifications
   - Allow configuration of system sound volume

2. **Audio Mixing**:
   - Handle prioritization between media and system sounds
   - Implement temporary volume reduction (ducking) for notifications
   - Ensure smooth transitions between audio sources

#### 2. Power Management

1. **Battery Impact**:

   - Optimize Bluetooth power usage
   - Implement sleep modes when not playing
   - Balance power efficiency with connection reliability

2. **Device Handling**:
   - Properly handle device sleep and wake situations
   - Monitor device battery levels when available
   - Implement proper shutdown procedures

### Security Considerations

1. **Bluetooth Security**:

   - Use secure pairing methods
   - Implement proper PIN handling if required
   - Protect against unauthorized device connections

2. **Audio Content**:
   - Validate audio sources before playback
   - Implement proper error handling for malformed content
   - Protect against potentially harmful audio files

### Testing

#### 1. Bluetooth Testing

1. **Device Compatibility**:

   - Test with a variety of Bluetooth speakers
   - Verify compatibility with common speaker brands
   - Document any device-specific considerations

2. **Connection Stability**:
   - Test long-duration connections
   - Test reconnection after power cycles
   - Test behavior with multiple devices in range

#### 2. Audio Quality Testing

1. **Playback Quality**:

   - Test various audio formats and bitrates
   - Verify consistent volume levels across sources
   - Test playback behavior with different content types

2. **Stress Testing**:
   - Test rapid playback changes
   - Test behavior under low memory conditions
   - Test concurrent operations (e.g., playback during device discovery)

## Common Issues and Solutions

#### 1. Bluetooth Connection Problems

- Issue: Device fails to connect or frequently disconnects
- Solution: Implement connection retry logic with exponential backoff
- Solution: Check for conflicting Bluetooth services
- Solution: Update Bluetooth firmware and drivers

#### 2. Audio Latency

- Issue: High delay between command and playback
- Solution: Optimize audio buffering parameters
- Solution: Use compatible Bluetooth codecs when available
- Solution: Pre-cache frequently used audio

#### 3. Audio Quality Issues

- Issue: Poor audio quality or dropouts
- Solution: Check for WiFi interference and adjust channels
- Solution: Implement audio normalization
- Solution: Verify proper audio format support

## Resources and References

#### 1. Bluetooth Audio

- [BlueALSA GitHub Repository](https://github.com/Arkq/bluez-alsa)
- [Raspberry Pi Bluetooth Audio Guide](https://www.raspberrypi.org/documentation/configuration/bluetooth/audio.md)
- [Bluetooth Audio Profiles](https://www.bluetooth.com/specifications/profiles-overview/)

#### 2. Audio Libraries

- [GStreamer Audio Documentation](https://gstreamer.freedesktop.org/documentation/)
- [PulseAudio Documentation](https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/)
- [pydbus Documentation](https://github.com/LEW21/pydbus)

#### 3. Audio Processing

- [Audio normalization techniques](https://en.wikipedia.org/wiki/Audio_normalization)
- [FFmpeg Audio Filtering Guide](https://ffmpeg.org/ffmpeg-filters.html#Audio-Filters)
