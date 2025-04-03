# Audio Module - Implementation Guide

> **CRITICAL: BlueALSA INTEGRATION ISSUE - NEW APPROACH**
>
> The previous BlueALSA implementation strategy was problematic. This document outlines a new, simplified approach using standard Raspberry Pi OS packages instead of custom-compiled solutions.

## Overview

The Audio Module is responsible for handling all audio playback functionality for the NFC music player. It manages Bluetooth connectivity, audio streaming, volume control, and playback status. This module provides a reliable audio interface that works with Bluetooth speakers and ensures consistent playback experience.

## New Implementation Strategy

### Key Design Principles

1. **Use standard packages** - Avoid compiling from source
2. **Simplify architecture** - Choose a single audio backend
3. **Separate concerns** - Bluetooth connection management vs audio playback
4. **Resource efficiency** - Optimized for Raspberry Pi Zero

### Recommended Approach

1. **Use standard Raspberry Pi OS packages**:
   - Use `bluealsa` from repositories instead of compiling `bluez-alsa` from source
   - Use Pi's native Bluetooth stack with `pi-bluetooth`
   - Remove PulseAudio to prevent conflicts and save resources

2. **Direct control via D-Bus**:
   - Implement D-Bus communication with BlueZ
   - Avoid unnecessary layers and dependencies

3. **Lightweight playback**:
   - Use GStreamer with minimal plugins for playback
   - Implement proper resource management

## Installation Setup

### Required Packages

```bash
# System packages
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  bluetooth \
  bluez \
  bluez-tools \
  pi-bluetooth \
  bluealsa \
  alsa-utils \
  dbus \
  python3-dbus \
  python3-gi \
  gstreamer1.0-tools \
  gstreamer1.0-plugins-base \
  gstreamer1.0-plugins-good \
  gstreamer1.0-alsa

# Python packages
pip install pydbus dbus-python pygobject pexpect
```

### Repository Setup

The setup script must explicitly add the Raspberry Pi repository if not running on Raspberry Pi OS:

```bash
# Add Raspberry Pi repository (if not on Raspberry Pi OS)
if ! grep -q "raspbian" /etc/apt/sources.list /etc/apt/sources.list.d/*; then
  echo "Adding Raspberry Pi repository..."
  echo "deb http://archive.raspberrypi.org/debian/ buster main" | sudo tee /etc/apt/sources.list.d/raspi.list
  wget -qO - https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | sudo apt-key add -
  sudo apt-get update
fi
```

### BlueALSA Setup

1. **Install packages**:
   ```bash
   sudo apt-get install -y bluealsa
   ```

2. **Create service** (only if it doesn't exist):
   ```bash
   # Create bluealsa service file if not already present
   if [ ! -f /etc/systemd/system/bluealsa.service ]; then
     sudo bash -c 'cat > /etc/systemd/system/bluealsa.service << EOF
   [Unit]
   Description=BluALSA service
   After=bluetooth.service
   Requires=bluetooth.service

   [Service]
   Type=simple
   ExecStart=/usr/bin/bluealsa -p a2dp-sink -p a2dp-source
   Restart=on-failure

   [Install]
   WantedBy=multi-user.target
   EOF'
   fi
   ```

3. **Enable and start services**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable bluetooth
   sudo systemctl start bluetooth
   sudo systemctl enable bluealsa
   sudo systemctl start bluealsa
   ```

## Implementation Details

### File Structure

```
audio/
├── __init__.py                 # Main API interface
├── exceptions.py               # Audio-specific exceptions
├── bluetooth_manager.py        # Bluetooth connectivity
├── playback_handler.py         # Audio playback
├── system_sounds.py            # System notification sounds
└── utils.py                    # Utility functions
```

### Key Components

#### 1. Audio Controller (`__init__.py`)

Provides the main API interface that other modules will use:

```python
def initialize():
    """Initialize Bluetooth and audio subsystems."""
    
def shutdown():
    """Clean shutdown of audio subsystems."""
    
def play(media_path):
    """Play audio from the specified path."""
    
def pause():
    """Pause current playback."""
    
def resume():
    """Resume paused playback."""
    
def stop():
    """Stop current playback."""
    
def set_volume(level):
    """Set volume level (0-100)."""
    
def get_volume():
    """Get current volume level."""
    
def get_playback_status():
    """Get current playback status."""
    
def play_system_sound(sound_type):
    """Play a system notification sound."""
```

#### 2. Bluetooth Manager (`bluetooth_manager.py`)

Handles Bluetooth device discovery and connection:

```python
class BluetoothManager:
    """Manages Bluetooth connections using D-Bus."""
    
    def start_discovery(self, timeout=30):
        """Start Bluetooth device discovery."""
        
    def get_discovered_devices(self):
        """Get list of discovered devices."""
        
    def connect_device(self, device_address):
        """Connect to a Bluetooth device."""
        
    def disconnect_device(self):
        """Disconnect current device."""
        
    def get_connected_device(self):
        """Get info about currently connected device."""
```

#### 3. Playback Handler (`playback_handler.py`)

Handles audio playback via GStreamer:

```python
class AudioPlayer:
    """Handles audio playback."""
    
    def load_media(self, media_path):
        """Load media file for playback."""
        
    def play(self):
        """Start playback."""
        
    def pause(self):
        """Pause playback."""
        
    def resume(self):
        """Resume playback."""
        
    def stop(self):
        """Stop playback."""
        
    def set_volume(self, level):
        """Set volume level."""
```

## Troubleshooting Common Issues

### Bluetooth Discovery Problems

If devices aren't being discovered:

```bash
# Verify Bluetooth is powered on
bluetoothctl show

# Reset Bluetooth service
sudo systemctl restart bluetooth
sudo systemctl restart bluealsa

# Enable discovery mode
bluetoothctl discoverable on
```

### Audio Playback Issues

If audio doesn't play through Bluetooth:

```bash
# Check device connection
bluetoothctl info [MAC_ADDRESS]

# Verify BlueALSA is running
systemctl status bluealsa

# Check audio devices
aplay -l

# Test direct audio output
aplay -D bluealsa:DEV=[MAC_ADDRESS],PROFILE=a2dp /usr/share/sounds/alsa/Front_Center.wav
```

### Connection Problems

If devices connect but disconnect immediately:

```bash
# Check bluetoothd logs
journalctl -u bluetooth -f

# Check if device is trusted
bluetoothctl trust [MAC_ADDRESS]

# Verify correct audio profile
bluetoothctl info [MAC_ADDRESS] | grep "Audio Sink"
```

## Testing

Use the included testing script to verify functionality:

```bash
sudo ./setup_and_test_pi.sh
```

The script will:
1. Install all required packages
2. Configure BlueALSA properly
3. Verify Bluetooth functionality
4. Run audio module tests

## Performance Optimization

1. **Minimize latency**:
   - Pre-buffer audio when possible
   - Use ALSA direct when feasible 

2. **Battery life**:
   - Disconnect Bluetooth when not in use
   - Implement power-saving modes

3. **Memory usage**:
   - Use efficient buffering
   - Ensure proper cleanup after playback

## Security Considerations

1. **Bluetooth pairing**:
   - Use secure pairing methods
   - Store paired devices securely

2. **Input validation**:
   - Validate all file paths before playback
   - Check file types to prevent playback attacks