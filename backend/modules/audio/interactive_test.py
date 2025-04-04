#!/usr/bin/env python3
"""
Interactive test script for the audio module.

This script provides a command-line interface to test various
functions of the audio module including Bluetooth connectivity
and audio playback.

Run with: python3 backend/modules/audio/interactive_test.py
"""

import os
import sys
import time
import select
import argparse
from typing import Dict, List, Any, Optional

# Add parent directory to path to allow imports
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(script_dir, '../../../')))

# Import from audio module
from backend.modules.audio.audio_controller import AudioController

# Create a global controller
audio_controller = None


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)


def print_device_info(device: Dict) -> None:
    """Print information about a Bluetooth device."""
    print(f"  Name: {device.get('name', 'Unknown')}")
    print(f"  Address: {device.get('address', 'Unknown')}")
    print(f"  Paired: {device.get('paired', False)}")
    print(f"  Trusted: {device.get('trusted', False)}")
    print(f"  Connected: {device.get('connected', False)}")
    print(f"  Audio Sink: {device.get('audio_sink', False)}")


def discover_devices() -> None:
    """Discover and display Bluetooth devices."""
    global audio_controller
    print_header("Bluetooth Discovery")
    
    try:
        print("Starting discovery...")
        if not audio_controller.start_discovery(timeout=30):
            print("Failed to start discovery.")
            return
        
        print("Discovering devices for 30 seconds. Press Ctrl+C to stop early.")
        
        try:
            # Show progress
            for i in range(30):
                sys.stdout.write(f"\rDiscovering... {i+1}/30s")
                sys.stdout.flush()
                time.sleep(1)
            print("\rDiscovery complete!             ")
        except KeyboardInterrupt:
            print("\rDiscovery stopped by user.      ")
        
        devices = audio_controller.get_discovered_devices()
        print(f"\nDiscovered {len(devices)} devices:")
        
        for i, device in enumerate(devices):
            print(f"\nDevice {i+1}:")
            print_device_info(device)
        
    finally:
        audio_controller.stop_discovery()


def show_paired_devices() -> None:
    """Display paired Bluetooth devices."""
    global audio_controller
    print_header("Paired Devices")
    
    devices = audio_controller.get_paired_devices()
    if not devices:
        print("No paired devices found.")
        return
    
    print(f"Found {len(devices)} paired devices:")
    for i, device in enumerate(devices):
        print(f"\nDevice {i+1}:")
        print_device_info(device)


def show_connected_device() -> None:
    """Display the currently connected Bluetooth device."""
    global audio_controller
    print_header("Connected Device")
    
    device = audio_controller.get_connected_device()
    if not device:
        print("No device is currently connected.")
        return
    
    print("Currently connected to:")
    print_device_info(device)


def connect_to_device() -> None:
    """Connect to a Bluetooth device."""
    global audio_controller
    print_header("Connect to Device")
    
    # Show paired devices first
    devices = audio_controller.get_paired_devices()
    if devices:
        print("Paired devices:")
        for i, device in enumerate(devices):
            print(f"{i+1}. {device.get('name', 'Unknown')} ({device.get('address')})")
    
    # Ask for device address
    print("\nEnter the Bluetooth address of the device to connect to")
    print("(format: 00:11:22:33:44:55)")
    
    if devices:
        print("Or enter a number to select from the list above")
        
    address = input("Device: ").strip()
    
    # Check if input is a number for selection from list
    if devices and address.isdigit():
        index = int(address) - 1
        if 0 <= index < len(devices):
            address = devices[index].get('address')
        else:
            print("Invalid selection.")
            return
    
    print(f"Connecting to {address}...")
    if audio_controller.connect_device(address):
        print("Successfully connected!")
        
        # Show connected device details
        device = audio_controller.get_connected_device()
        if device:
            print_device_info(device)
    else:
        print("Failed to connect to device.")


def disconnect_current_device() -> None:
    """Disconnect from the current Bluetooth device."""
    global audio_controller
    print_header("Disconnect Device")
    
    device = audio_controller.get_connected_device()
    if not device:
        print("No device is currently connected.")
        return
    
    print(f"Disconnecting from {device.get('name')} ({device.get('address')})...")
    if audio_controller.disconnect_device():
        print("Successfully disconnected.")
    else:
        print("Failed to disconnect.")


def forget_paired_device() -> None:
    """Forget (unpair) a Bluetooth device."""
    global audio_controller
    print_header("Forget Device")
    
    # Show paired devices
    devices = audio_controller.get_paired_devices()
    if not devices:
        print("No paired devices found.")
        return
    
    print("Paired devices:")
    for i, device in enumerate(devices):
        print(f"{i+1}. {device.get('name', 'Unknown')} ({device.get('address')})")
    
    # Ask for device to forget
    print("\nEnter the number of the device to forget, or address:")
    choice = input("Device: ").strip()
    
    # Get address from selection or direct input
    address = None
    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(devices):
            address = devices[index].get('address')
        else:
            print("Invalid selection.")
            return
    else:
        address = choice
    
    # Confirm before forgetting
    print(f"Are you sure you want to forget device {address}? (y/n)")
    confirm = input().strip().lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    print(f"Forgetting device {address}...")
    if audio_controller.forget_device(address):
        print("Device successfully forgotten.")
    else:
        print("Failed to forget device.")


def test_audio() -> None:
    """Test audio output."""
    global audio_controller
    print_header("Audio Output Test")
    
    device = audio_controller.get_connected_device()
    if device:
        print(f"Testing audio output to {device.get('name')} ({device.get('address')})...")
    else:
        print("Testing audio output to default audio device...")
    
    try:
        if audio_controller.test_audio_output():
            print("Audio test successful!")
        else:
            print("Audio test failed.")
    except Exception as e:
        print(f"Error: {e}")


def play_audio_file() -> None:
    """Play an audio file."""
    global audio_controller
    print_header("Play Audio File")
    
    print("Enter the path to an audio file to play:")
    file_path = input("File path: ").strip()
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
    
    print(f"Playing {file_path}...")
    if audio_controller.play(file_path):
        print("Playback started.")
        print("Commands: [p]ause, [r]esume, [s]top, [q]uit playback")
        
        while audio_controller.is_playing():
            # Show playback status
            status = audio_controller.get_playback_status()
            position = status.get('position', 0)
            duration = status.get('duration', 0)
            
            if duration > 0:
                percentage = (position / duration) * 100
                sys.stdout.write(f"\rPosition: {position}/{duration}s ({percentage:.0f}%) ")
            else:
                sys.stdout.write(f"\rPosition: {position}s ")
                
            sys.stdout.flush()
            
            # Check for commands
            if sys.stdin in select.select([sys.stdin], [], [], 0.5)[0]:
                cmd = sys.stdin.read(1).lower()
                if cmd == 'p':
                    audio_controller.pause()
                    print("\nPlayback paused.")
                elif cmd == 'r':
                    audio_controller.resume()
                    print("\nPlayback resumed.")
                elif cmd == 's' or cmd == 'q':
                    audio_controller.stop()
                    print("\nPlayback stopped.")
                    break
            
            # Short sleep to avoid high CPU
            time.sleep(0.5)
    else:
        print("Failed to start playback.")


def volume_control() -> None:
    """Control audio volume."""
    global audio_controller
    print_header("Volume Control")
    
    current = audio_controller.get_volume()
    print(f"Current volume: {current}%")
    
    print("\nOptions:")
    print("1. Increase volume (+10%)")
    print("2. Decrease volume (-10%)")
    print("3. Set specific volume")
    print("4. Mute/Unmute")
    print("5. Back to main menu")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        new_level = min(100, current + 10)
        audio_controller.set_volume(new_level)
        print(f"Volume increased to {new_level}%")
    
    elif choice == '2':
        new_level = max(0, current - 10)
        audio_controller.set_volume(new_level)
        print(f"Volume decreased to {new_level}%")
    
    elif choice == '3':
        level = input("Enter volume level (0-100): ").strip()
        if level.isdigit():
            new_level = max(0, min(100, int(level)))
            audio_controller.set_volume(new_level)
            print(f"Volume set to {new_level}%")
        else:
            print("Invalid input.")
    
    elif choice == '4':
        # Check if already muted based on volume
        if current == 0:
            audio_controller.set_volume(50)  # Default to 50% when unmuting
            print("Unmuted. Volume set to 50%")
        else:
            audio_controller.mute()
            print("Muted.")
    
    elif choice != '5':
        print("Invalid choice.")


def show_bluetooth_status() -> None:
    """Display Bluetooth system status."""
    global audio_controller
    print_header("Bluetooth Status")
    
    status = audio_controller.get_bluetooth_status()
    
    print("Bluetooth System Status:")
    print(f"  Available: {status.get('available', False)}")
    print(f"  Powered: {status.get('powered', False)}")
    print(f"  BlueALSA running: {status.get('bluealsa_running', False)}")
    print(f"  Device connected: {status.get('connected', False)}")
    print(f"  Auto-reconnect: {status.get('auto_reconnect', False)}")
    
    device = status.get('device')
    if device:
        print("\nConnected device:")
        print_device_info(device)


def toggle_auto_reconnect() -> None:
    """Toggle automatic Bluetooth reconnection."""
    global audio_controller
    print_header("Auto-Reconnect Setting")
    
    status = audio_controller.get_bluetooth_status()
    current = status.get('auto_reconnect', False)
    
    print(f"Auto-reconnect is currently: {'Enabled' if current else 'Disabled'}")
    print(f"Do you want to {'disable' if current else 'enable'} it? (y/n)")
    
    choice = input().strip().lower()
    if choice == 'y':
        audio_controller.set_auto_reconnect(not current)
        print(f"Auto-reconnect {'enabled' if not current else 'disabled'}.")
    else:
        print("Setting unchanged.")


def main() -> None:
    """Main function for the interactive test script."""
    global audio_controller
    
    parser = argparse.ArgumentParser(description="Audio module interactive test")
    parser.add_argument("--no-init", action="store_true", help="Skip module initialization")
    args = parser.parse_args()
    
    # Initialize the controller
    try:
        print("Initializing audio controller...")
        audio_controller = AudioController()
        if not audio_controller.initialize():
            print("Failed to initialize audio controller.")
            return 1
    except Exception as e:
        print(f"Initialization error: {e}")
        return 1
    
    try:
        while True:
            # Clear screen
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print_header("Audio Module Interactive Test")
            
            # Show connection status
            status = audio_controller.get_bluetooth_status()
            device = audio_controller.get_connected_device()
            
            if device:
                print(f"Connected to: {device.get('name')} ({device.get('address')})")
            else:
                print("No Bluetooth device connected")
            
            print(f"BlueALSA status: {'Running' if status.get('bluealsa_running') else 'Not running'}")
            print(f"Volume: {audio_controller.get_volume()}%")
            
            # Main menu
            print("\nOptions:")
            print("1.  Discover Bluetooth devices")
            print("2.  Show paired devices")
            print("3.  Show connected device")
            print("4.  Connect to device")
            print("5.  Disconnect current device")
            print("6.  Forget (unpair) device")
            print("7.  Test audio output")
            print("8.  Play audio file")
            print("9.  Volume control")
            print("10. Show Bluetooth status")
            print("11. Toggle auto-reconnect")
            print("q.  Quit")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == '1':
                discover_devices()
            elif choice == '2':
                show_paired_devices()
            elif choice == '3':
                show_connected_device()
            elif choice == '4':
                connect_to_device()
            elif choice == '5':
                disconnect_current_device()
            elif choice == '6':
                forget_paired_device()
            elif choice == '7':
                test_audio()
            elif choice == '8':
                play_audio_file()
            elif choice == '9':
                volume_control()
            elif choice == '10':
                show_bluetooth_status()
            elif choice == '11':
                toggle_auto_reconnect()
            elif choice == 'q':
                break
            else:
                print("Invalid choice. Press Enter to continue.")
                input()
                continue
            
            print("\nPress Enter to continue...")
            input()
    
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if audio_controller:
            print("Shutting down audio controller...")
            try:
                audio_controller.shutdown()
            except Exception as e:
                print(f"Error during shutdown: {e}")
            
        print("Goodbye!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
