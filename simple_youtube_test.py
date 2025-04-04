#!/usr/bin/env python3
"""
Simple script to download a YouTube video and play it through the audio system.
This script bypasses the database dependency for basic testing.
"""

import os
import sys
import time
import uuid
import tempfile
import subprocess
from pathlib import Path

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import audio controller
from backend.modules.audio.audio_controller import AudioController

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

def download_youtube_audio(url, output_path=None):
    """
    Download audio from a YouTube URL using yt-dlp directly.
    Returns the path to the downloaded file.
    """
    if not output_path:
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, "audio.mp3")
    
    print(f"Downloading from {url} to {output_path}...")
    
    # Prepare yt-dlp command
    cmd = [
        "yt-dlp",
        "-f", "bestaudio",  # Best audio format
        "--extract-audio",  # Extract audio
        "--audio-format", "mp3",  # Convert to mp3
        "--audio-quality", "192K",  # Use 192K quality
        "--no-cache-dir",  # Don't use cache
        "--no-cookies",  # Don't use cookies
        "--embed-metadata",  # Include metadata
        "--prefer-ffmpeg",  # Prefer using ffmpeg for conversion
        "--ignore-errors",  # Ignore errors during extraction
        "-o", output_path,  # Output file
        url  # YouTube URL
    ]
    
    try:
        # Run the command
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Check if file exists with various possible extensions
        possible_files = [
            output_path,  # Original path
            output_path + ".mp3",  # With mp3 extension
            output_path + ".webm",  # With webm extension
            output_path + ".m4a",   # With m4a extension
            # Try removing extension if one was added and try with proper mp3
            os.path.splitext(output_path)[0] + ".mp3"
        ]
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                print(f"✅ Successfully downloaded to {file_path}")
                return file_path
        
        # List files in directory to see what was actually created
        directory = os.path.dirname(output_path)
        print(f"Looking for files in {directory}:")
        if os.path.exists(directory):
            files = os.listdir(directory)
            # Get base name without path and extension
            base_name = os.path.basename(os.path.splitext(output_path)[0])
            for file in files:
                # If our generated filename is part of a file in the directory
                if base_name in file:
                    # This might be our file with a different name
                    full_path = os.path.join(directory, file)
                    print(f"Found possible match: {full_path}")
                    return full_path
            
            print(f"Files in directory: {files}")
        
        print(f"❌ Download seemed to succeed but file not found at {output_path}")
        print(f"Output: {process.stdout}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Main function for the simple YouTube audio test."""
    print_header("Simple YouTube Audio Test")
    
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
        
        # Main loop
        while True:
            print_header("Main Menu")
            print("1. Download and play a YouTube video")
            print("2. Play a downloaded audio file")
            print("3. Show connected device")
            print("4. Quit")
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == '1':
                # Ask for YouTube URL
                print_header("YouTube Download and Play")
                youtube_url = input("Enter a YouTube URL: ").strip()
                if not youtube_url:
                    print("No URL provided, cancelling.")
                    continue
                
                # Create download directory if it doesn't exist
                download_dir = os.path.join(current_dir, "downloads")
                os.makedirs(download_dir, exist_ok=True)
                
                # Generate a filename
                filename = f"youtube_audio_{uuid.uuid4()}"  # Without extension
                output_path = os.path.join(download_dir, filename)
                
                # Download the audio
                audio_file = download_youtube_audio(youtube_url, output_path)
                if not audio_file:
                    print("Failed to download audio.")
                    continue
                    
                # Make sure we have the correct file to play
                if not os.path.exists(audio_file):
                    print(f"Warning: Expected file {audio_file} not found.")
                    # Check common extensions
                    for ext in ['.mp3', '.webm', '.m4a']:
                        if os.path.exists(audio_file + ext):
                            audio_file = audio_file + ext
                            print(f"Found alternative file: {audio_file}")
                            break
                
                # Play the audio
                print(f"Playing {audio_file}...")
                if audio_controller.play(audio_file):
                    print("✅ Playback started")
                    
                    # Wait for playback to complete
                    while audio_controller.is_playing():
                        time.sleep(1)
                    
                    print("Playback completed.")
                else:
                    print("❌ Failed to start playback")
            
            elif choice == '2':
                # Play an existing audio file
                print_header("Play Audio File")
                
                # Check if downloads directory exists
                download_dir = os.path.join(current_dir, "downloads")
                if os.path.exists(download_dir):
                    # List downloaded files
                    files = [f for f in os.listdir(download_dir) if f.endswith('.mp3')]
                    
                    if files:
                        print("Available audio files:")
                        for i, file in enumerate(files):
                            print(f"{i+1}. {file}")
                        
                        # Ask for selection
                        file_choice = input("\nSelect file by number (or press Enter to cancel): ").strip()
                        if file_choice and file_choice.isdigit() and 0 < int(file_choice) <= len(files):
                            index = int(file_choice) - 1
                            audio_file = os.path.join(download_dir, files[index])
                            
                            # Play the file
                            print(f"Playing {audio_file}...")
                            if audio_controller.play(audio_file):
                                print("✅ Playback started")
                                
                                # Wait for playback to complete
                                while audio_controller.is_playing():
                                    time.sleep(1)
                                
                                print("Playback completed.")
                            else:
                                print("❌ Failed to start playback")
                        else:
                            print("Invalid selection or cancelled.")
                    else:
                        print("No audio files found in downloads directory.")
                        file_path = input("Enter full path to an audio file: ").strip()
                        if file_path and os.path.exists(file_path):
                            # Play the file
                            print(f"Playing {file_path}...")
                            if audio_controller.play(file_path):
                                print("✅ Playback started")
                                
                                # Wait for playback to complete
                                while audio_controller.is_playing():
                                    time.sleep(1)
                                
                                print("Playback completed.")
                            else:
                                print("❌ Failed to start playback")
                        else:
                            print("Invalid file path or file doesn't exist.")
                else:
                    print("Downloads directory not found.")
                    file_path = input("Enter full path to an audio file: ").strip()
                    if file_path and os.path.exists(file_path):
                        # Play the file
                        print(f"Playing {file_path}...")
                        if audio_controller.play(file_path):
                            print("✅ Playback started")
                            
                            # Wait for playback to complete
                            while audio_controller.is_playing():
                                time.sleep(1)
                            
                            print("Playback completed.")
                        else:
                            print("❌ Failed to start playback")
                    else:
                        print("Invalid file path or file doesn't exist.")
            
            elif choice == '3':
                # Show connected device
                device = audio_controller.get_connected_device()
                print("\nConnected device:")
                print_device_info(device)
            
            elif choice == '4':
                # Quit
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
    sys.exit(main())