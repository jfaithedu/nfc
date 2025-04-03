"""
Unit tests for the audio module.

This module contains tests for Bluetooth functionality and audio playback.
Run with: python -m pytest -v backend/modules/audio/test_audio.py
"""

import os
import time
import pytest

from backend.modules.audio import (
    initialize,
    shutdown,
    start_discovery,
    stop_discovery,
    get_discovered_devices,
    get_connected_device,
    is_device_connected,
    get_bluetooth_status,
    get_volume,
    set_volume,
    test_audio_output
)


def test_initialize():
    """Test that the audio module can initialize."""
    result = initialize()
    assert result == True, "Audio module should initialize successfully"
    shutdown()


def test_bluetooth_status():
    """Test retrieving Bluetooth status."""
    initialize()
    status = get_bluetooth_status()
    
    # Check that the status has required keys
    assert "available" in status, "Bluetooth status should include 'available'"
    assert "powered" in status, "Bluetooth status should include 'powered'"
    assert "bluealsa_running" in status, "Bluetooth status should include 'bluealsa_running'"
    assert "connected" in status, "Bluetooth status should include 'connected'"
    assert "auto_reconnect" in status, "Bluetooth status should include 'auto_reconnect'"
    
    # Log status for debugging
    print(f"Bluetooth status: {status}")
    
    shutdown()


def test_volume_control():
    """Test volume control functionality."""
    initialize()
    
    # Get initial volume
    initial_volume = get_volume()
    
    # Set volume to 75%
    new_volume = set_volume(75)
    assert new_volume == 75, "Volume should be set to 75"
    
    # Set volume to 25%
    new_volume = set_volume(25)
    assert new_volume == 25, "Volume should be set to 25"
    
    # Verify getting volume
    current_volume = get_volume()
    assert current_volume == 25, "Current volume should be 25"
    
    # Restore original volume
    set_volume(initial_volume)
    
    shutdown()


@pytest.mark.skipif(os.environ.get("CI") == "true", reason="Skipping in CI environment")
def test_discovery():
    """Test Bluetooth discovery (optional, may be skipped)."""
    initialize()
    
    # Start discovery
    result = start_discovery(timeout=10)
    assert result == True, "Discovery should start successfully"
    
    # Wait a moment for discovery
    time.sleep(5)
    
    # Get discovered devices
    devices = get_discovered_devices()
    print(f"Discovered {len(devices)} Bluetooth devices")
    
    # Log devices for debugging
    for device in devices:
        print(f"Device: {device.get('name')} ({device.get('address')})")
    
    # Stop discovery
    stop_discovery()
    
    shutdown()


@pytest.mark.skipif(
    not is_device_connected() or os.environ.get("CI") == "true",
    reason="Requires connected Bluetooth device"
)
def test_audio_output_function():
    """Test audio playback (requires connected Bluetooth device)."""
    initialize()
    
    # Get connected device
    device = get_connected_device()
    assert device is not None, "Should have a connected device"
    print(f"Testing audio output to {device.get('name')} ({device.get('address')})")
    
    # Test audio output
    result = test_audio_output()
    assert result == True, "Audio output test should succeed"
    
    shutdown()


if __name__ == "__main__":
    print("Running audio module tests...")
    
    # Initialize the module
    if not initialize():
        print("Failed to initialize audio module")
        exit(1)
    
    print("\n--- Bluetooth Status ---")
    status = get_bluetooth_status()
    for key, value in status.items():
        print(f"{key}: {value}")
    
    print("\n--- Connected Device ---")
    device = get_connected_device()
    if device:
        print(f"Connected to: {device.get('name')} ({device.get('address')})")
    else:
        print("No device connected")
    
    print("\n--- Starting Discovery ---")
    if start_discovery(timeout=15):
        print("Discovering devices for 15 seconds...")
        time.sleep(15)
        
        devices = get_discovered_devices()
        print(f"\nDiscovered {len(devices)} devices:")
        for device in devices:
            print(f"- {device.get('name', 'Unknown')} ({device.get('address')})")
            print(f"  Paired: {device.get('paired', False)}")
            print(f"  Connected: {device.get('connected', False)}")
            print(f"  Audio Sink: {device.get('audio_sink', False)}")
        
        stop_discovery()
    else:
        print("Failed to start discovery")
    
    # Clean up
    print("\nShutting down audio module...")
    shutdown()
    print("Tests completed.")