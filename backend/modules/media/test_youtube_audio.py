#!/usr/bin/env python3
"""
Test script for streaming YouTube audio through a connected Bluetooth device.

This script combines the audio and media modules to:
1. Connect to a Bluetooth device
2. Download a YouTube video's audio
3. Play it through the connected device

Run with: python3 backend/modules/media/test_youtube_audio.py
"""

import os
import sys
import time
import uuid
from pathlib import Path

# Add parent directory to path to allow importing the modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Import both modules
from backend.modules.audio.audio_controller import AudioController
from backend.modules.media import media_manager

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 50)
    print(f" {title}")
    print("=" * 50)

def print_device_info(device):
    """Print information about a Bluetooth device."""
    if not device:
        print("  No device connected")
        return
    
    print(f"  Name: {device.get('name', 'Unknown')}")
    print(f"  Address: {device.get('address', 'Unknown')}")
    print(f"  Connected: {device.get('connected', False)}")
    print(f"  Audio Sink: {device.get('audio_sink', False)}")

def connect_to_device(audio_controller):
    """Connect to a Bluetooth device."""
    print_header("Connect to Bluetooth Device")
    
    # Show paired devices
    devices = audio_controller.get_paired_devices()
    if devices:
        print("Paired devices:")
        for i, device in enumerate(devices):
            print(f"{i+1}. {device.get('name', 'Unknown')} ({device.get('address')})")
    else:
        print("No paired devices found.")
        if input("Do you want to discover new devices? (y/n): ").lower() == 'y':
            discover_devices(audio_controller)
        return False
    
    # Ask for device selection
    choice = input("\nSelect device by number (or press Enter to skip): ").strip()
    if not choice:
        return False
    
    if choice.isdigit() and 0 < int(choice) <= len(devices):
        index = int(choice) - 1
        address = devices[index].get('address')
        
        print(f"Connecting to {devices[index].get('name')} ({address})...")
        if audio_controller.bt_manager.connect_device(address):
            print("✅ Successfully connected!")
            device = audio_controller.get_connected_device()
            if device:
                print_device_info(device)
            return True
        else:
            print("❌ Failed to connect to device.")
            return False
    else:
        print("Invalid selection.")
        return False

def discover_devices(audio_controller):
    """Discover and display Bluetooth devices."""
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
            
        # Ask if user wants to pair with any discovered device
        if devices:
            pair_choice = input("\nPair with a device? Enter number (or press Enter to skip): ").strip()
            if pair_choice and pair_choice.isdigit() and 0 < int(pair_choice) <= len(devices):
                index = int(pair_choice) - 1
                address = devices[index].get('address')
                
                print(f"Pairing with {devices[index].get('name', 'Unknown')} ({address})...")
                if audio_controller.bt_manager.pair_device(address):
                    print("✅ Successfully paired!")
                    
                    # Ask if they want to connect too
                    if input("Connect to this device now? (y/n): ").lower() == 'y':
                        if audio_controller.bt_manager.connect_device(address):
                            print("✅ Successfully connected!")
                            return True
                else:
                    print("❌ Failed to pair with device.")
        
    finally:
        audio_controller.stop_discovery()
    
    return False

def play_youtube_audio(audio_controller):
    """Download and play audio from a YouTube URL."""
    print_header("YouTube Audio Test")
    
    # Initialize media manager
    print("Initializing media manager...")
    if not media_manager.initialize():
        print("❌ Failed to initialize media manager")
        return False
    
    try:
        # Ask for YouTube URL
        youtube_url = input("Enter a YouTube URL: ").strip()
        if not youtube_url:
            print("No URL provided, cancelling.")
            return False
        
        # Get video info
        print("Getting video information...")
        try:
            info = media_manager.get_media_info(youtube_url)
            print(f"Title: {info['title']}")
            print(f"Duration: {info['duration']} seconds")
        except Exception as e:
            print(f"❌ Error getting video info: {e}")
            return False
        
        # Create test media ID and prepare media
        media_id = str(uuid.uuid4())
        print(f"Test media ID: {media_id}")
        
        # Create a placeholder media_info
        media_info = {
            'id': media_id,
            'url': youtube_url
        }
        
        print("Downloading and preparing media...")
        try:
            media_path = media_manager.prepare_media(media_info)
            print(f"✅ Media prepared: {media_path}")
        except Exception as e:
            print(f"❌ Error preparing media: {e}")
            return False
        
        # Now play the media
        print("Starting playback...")
        if audio_controller.play(media_path):
            print("✅ Playback started")
            
            print("\nControls: [p]ause, [r]esume, [s]top, [q]uit")
            print("Press Enter to stop playback and return to menu")
            
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
                
                # Check for command input
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
                
                # Sleep to avoid high CPU usage
                time.sleep(0.5)
            
            # Make sure playback is stopped
            audio_controller.stop()
            print("\nPlayback ended.")
            return True
        else:
            print("❌ Failed to start playback")
            return False
            
    except Exception as e:
        print(f"❌ Error during YouTube playback: {e}")
        return False
    finally:
        # Shutdown media manager
        media_manager.shutdown()
        print("Media manager shut down")

def main():
    """Main function for the test script."""
    print_header("YouTube Audio Streaming Test")
    
    # Initialize audio controller
    print("Initializing audio controller...")
    audio_controller = None
    try:
        audio_controller = AudioController()
        if not audio_controller.initialize():
            print("❌ Failed to initialize audio controller")
            return 1
        print("✅ Audio controller initialized")
        
        # Check Bluetooth status
        status = audio_controller.get_bluetooth_status()
        print(f"Bluetooth available: {status.get('available', False)}")
        print(f"Bluetooth powered: {status.get('powered', False)}")
        print(f"BlueALSA running: {status.get('bluealsa_running', False)}")
        
        # Get connected device
        device = audio_controller.get_connected_device()
        print("\nConnected device:")
        print_device_info(device)
        
        # Main menu loop
        while True:
            print_header("Main Menu")
            print("1. Connect to Bluetooth device")
            print("2. Discover Bluetooth devices")
            print("3. Play YouTube audio")
            print("4. Show connected device")
            print("5. Quit")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                connect_to_device(audio_controller)
            elif choice == '2':
                discover_devices(audio_controller)
            elif choice == '3':
                device = audio_controller.get_connected_device()
                if device:
                    # We have a connected device
                    play_youtube_audio(audio_controller)
                else:
                    print("No Bluetooth device connected.")
                    if input("Connect to a device first? (y/n): ").lower() == 'y':
                        if connect_to_device(audio_controller):
                            play_youtube_audio(audio_controller)
                    else:
                        print("Using default audio output.")
                        play_youtube_audio(audio_controller)
            elif choice == '4':
                device = audio_controller.get_connected_device()
                print("\nConnected device:")
                print_device_info(device)
            elif choice == '5':
                break
            else:
                print("Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")
    
    except KeyboardInterrupt:
        print("\nProgram interrupted by user.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if audio_controller:
            print("\nShutting down audio controller...")
            try:
                audio_controller.shutdown()
            except Exception as e:
                print(f"Error during shutdown: {e}")
            
        print("Goodbye!")
        return 0

if __name__ == "__main__":
    # Import select here to avoid issues when importing at the top
    import select
    sys.exit(main())