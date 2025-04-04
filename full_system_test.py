#!/usr/bin/env python3
"""
Full Backend System Test

This script provides an interactive interface to test all components of the NFC music player:
- NFC tag detection and writing
- Bluetooth audio connectivity
- Media management (YouTube and local files)
- API server functionality
- Database operations

Run this script from the project root directory.
"""

import os
import sys
import time
import threading
import json
from pathlib import Path

# Add the project directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import backend modules
from backend.modules.nfc import nfc_controller
from backend.modules.audio import audio_controller, bluetooth_manager
from backend.modules.media import media_manager
from backend.modules.database import db_manager
from backend.modules.api import api_server
from backend.config import CONFIG

# NFC tag detection globals
nfc_detection_thread = None
nfc_detection_running = False
_nfc_exit_event = None  # Event to signal the continuous polling to stop
_last_detected_tag = None  # Track the last detected tag UID for tag removal detection

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def print_subheader(title):
    """Print a formatted subheader."""
    print("\n" + "-" * 50)
    print(f" {title}")
    print("-" * 50)

def print_menu(title, options):
    """Print a formatted menu."""
    print_subheader(title)
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")
    print()

def wait_for_key():
    """Wait for the user to press Enter."""
    input("\nPress Enter to continue...")

def initialize_system():
    """Initialize all system components."""
    print_header("Initializing System Components")
    
    # Initialize database
    print("Initializing database...")
    if db_manager.initialize():
        print("✅ Database initialized successfully")
    else:
        print("❌ Database initialization failed")
    
    # Initialize NFC controller
    print("\nInitializing NFC controller...")
    if nfc_controller.initialize():
        print("✅ NFC controller initialized successfully")
    else:
        print("❌ NFC controller initialization failed")
    
    # Initialize media manager
    print("\nInitializing media manager...")
    if media_manager.initialize():
        print("✅ Media manager initialized successfully")
    else:
        print("❌ Media manager initialization failed")
    
    # Initialize audio controller
    print("\nInitializing audio controller...")
    if audio_controller.initialize():
        print("✅ Audio controller initialized successfully")
    else:
        print("❌ Audio controller initialization failed")
    
    # Initialize API server
    print("\nInitializing API server...")
    if api_server.initialize():
        print("✅ API server initialized successfully")
    else:
        print("❌ API server initialization failed")
    
    # Start API server
    print("\nStarting API server...")
    if api_server.start():
        print(f"✅ API server started at {api_server.get_server_url()}")
    else:
        print("❌ API server failed to start")
    
    print("\nSystem initialization complete!")

def shutdown_system():
    """Shut down all system components."""
    print_header("Shutting Down System Components")
    
    # Stop NFC detection if running
    global nfc_detection_running
    if nfc_detection_running:
        stop_nfc_detection()
    
    # Stop API server
    print("Stopping API server...")
    if api_server.stop():
        print("✅ API server stopped")
    else:
        print("❌ API server failed to stop")
    
    # Shut down audio controller
    print("\nShutting down audio controller...")
    audio_controller.shutdown()
    print("✅ Audio controller shut down")
    
    # Shut down media manager
    print("\nShutting down media manager...")
    media_manager.shutdown()
    print("✅ Media manager shut down")
    
    # Shut down NFC controller
    print("\nShutting down NFC controller...")
    nfc_controller.shutdown()
    print("✅ NFC controller shut down")
    
    # Shut down database
    print("\nShutting down database...")
    db_manager.shutdown()
    print("✅ Database shut down")
    
    print("\nSystem shutdown complete!")

def test_bluetooth():
    """Test Bluetooth functionality."""
    print_header("Bluetooth Test")
    
    while True:
        options = [
            "Show Bluetooth status",
            "Scan for devices",
            "Connect to device",
            "Disconnect current device",
            "Test audio playback",
            "Back to main menu"
        ]
        
        print_menu("Bluetooth Menu", options)
        choice = input("Enter choice (1-6): ").strip()
        
        if choice == '1':
            # Show Bluetooth status
            status = audio_controller.get_bluetooth_status()
            print_subheader("Bluetooth Status")
            print(f"  Bluetooth available: {status.get('available', False)}")
            print(f"  Bluetooth powered: {status.get('powered', False)}")
            print(f"  BlueALSA running: {status.get('bluealsa_running', False)}")
            
            connected_device = audio_controller.get_connected_device()
            print("\nConnected device:")
            if connected_device:
                print(f"  Name: {connected_device.get('name', 'Unknown')}")
                print(f"  Address: {connected_device.get('address', 'Unknown')}")
                print(f"  Connected: {connected_device.get('connected', False)}")
                print(f"  Audio Sink: {connected_device.get('audio_sink', False)}")
            else:
                print("  No device connected")
            
        elif choice == '2':
            # Scan for devices
            print_subheader("Scanning for Bluetooth devices")
            print("Starting discovery (up to 10 seconds)...")
            audio_controller.start_discovery(10)
            
            # Show a countdown
            for i in range(10, 0, -1):
                print(f"Scanning... {i} seconds remaining", end="\r")
                time.sleep(1)
            print("\nDiscovery complete")
            
            # Stop discovery
            audio_controller.stop_discovery()
            
            # Show discovered devices
            devices = audio_controller.get_discovered_devices()
            paired_devices = audio_controller.get_paired_devices()
            
            # Create a set of paired device addresses for quick lookup
            paired_addresses = {d.get('address') for d in paired_devices if d.get('address')}
            
            print("\nDiscovered devices:")
            if devices:
                for i, device in enumerate(devices, 1):
                    paired = "✅ Paired" if device.get('address') in paired_addresses else "❌ Not paired"
                    name = device.get('name', 'Unknown')
                    address = device.get('address', 'Unknown')
                    print(f"  {i}. {name} ({address}) - {paired}")
            else:
                print("  No devices found")
            
        elif choice == '3':
            # Connect to device
            # First scan for devices if needed
            print_subheader("Connect to Bluetooth Device")
            devices = audio_controller.get_discovered_devices()
            
            if not devices:
                print("No devices found. Scanning for devices...")
                audio_controller.start_discovery(5)
                time.sleep(5)
                audio_controller.stop_discovery()
                devices = audio_controller.get_discovered_devices()
            
            # Show devices
            if devices:
                print("\nAvailable devices:")
                for i, device in enumerate(devices, 1):
                    name = device.get('name', 'Unknown')
                    address = device.get('address', 'Unknown')
                    print(f"  {i}. {name} ({address})")
                
                # Ask for selection
                selection = input("\nSelect device by number (or press Enter to cancel): ").strip()
                if selection and selection.isdigit() and 0 < int(selection) <= len(devices):
                    device_index = int(selection) - 1
                    device = devices[device_index]
                    address = device.get('address')
                    
                    print(f"Connecting to {device.get('name')} ({address})...")
                    if audio_controller.connect_device(address):
                        print(f"✅ Successfully connected to {device.get('name')}")
                    else:
                        print(f"❌ Failed to connect to {device.get('name')}")
                else:
                    print("Connection cancelled")
            else:
                print("No devices found")
            
        elif choice == '4':
            # Disconnect current device
            print_subheader("Disconnect Bluetooth Device")
            connected_device = audio_controller.get_connected_device()
            
            if connected_device:
                print(f"Disconnecting from {connected_device.get('name')} ({connected_device.get('address')})...")
                if audio_controller.disconnect_device():
                    print("✅ Successfully disconnected")
                else:
                    print("❌ Failed to disconnect")
            else:
                print("No device currently connected")
            
        elif choice == '5':
            # Test audio playback
            print_subheader("Test Audio Playback")
            
            # Check if we have a connected Bluetooth device
            connected_device = audio_controller.get_connected_device()
            if not connected_device:
                print("⚠️ No Bluetooth device connected")
                print("Attempting to play through default audio output...")
            else:
                print(f"Connected to: {connected_device.get('name', 'Unknown')}")
            
            print("\nChoose what to play:")
            print("  1. System test sound")
            print("  2. Sample MP3 file")
            print("  3. Cancel")
            
            test_choice = input("\nEnter choice (1-3): ").strip()
            
            if test_choice == '1':
                print("Playing test sound...")
                if audio_controller.test_audio_output():
                    print("✅ Audio test successful")
                else:
                    print("❌ Audio test failed")
            elif test_choice == '2':
                # Play a sample MP3 file
                sample_path = os.path.join(current_dir, "backend/modules/audio/sample.mp3")
                if os.path.exists(sample_path):
                    print(f"Playing sample MP3: {sample_path}")
                    
                    try:
                        if audio_controller.play(sample_path):
                            print("✅ Playback started")
                            
                            # Wait for playback to complete or user interruption
                            print("Press Enter to stop playback...")
                            input()
                            audio_controller.stop()
                            print("Playback stopped")
                        else:
                            print("❌ Failed to start playback")
                    except Exception as e:
                        print(f"❌ Error playing sample: {e}")
                else:
                    print(f"❌ Sample file not found at: {sample_path}")
            else:
                print("Test cancelled")
            
        elif choice == '6':
            # Back to main menu
            return
        
        wait_for_key()

def test_nfc():
    """Test NFC functionality."""
    print_header("NFC Test")
    
    while True:
        options = [
            "Show NFC hardware info",
            "Poll for NFC tag (once)",
            "Start continuous tag detection",
            "Stop tag detection",
            "Write NDEF URL to tag",
            "Read NDEF data from tag",
            "Back to main menu"
        ]
        
        print_menu("NFC Menu", options)
        choice = input("Enter choice (1-7): ").strip()
        
        if choice == '1':
            # Show NFC hardware info
            info = nfc_controller.get_hardware_info()
            print_subheader("NFC Hardware Information")
            
            if info:
                for key, value in info.items():
                    print(f"  {key}: {value}")
            else:
                print("  Could not retrieve hardware information")
            
        elif choice == '2':
            # Poll for NFC tag (once) - using approach from test_tag_detection in test_nfc.py
            print_subheader("Polling for NFC Tag")
            print("Please place a tag on the reader...")
            print("Waiting for tag (10 seconds)...")
            
            # Try for up to 10 seconds
            start_time = time.time()
            detected = False
            
            try:
                while time.time() - start_time < 10:
                    # Just get the UID first, like in test_nfc.py
                    result = nfc_controller.poll_for_tag(read_ndef=False)
                    
                    if result:
                        detected = True
                        
                        # Handle the return value which could be just a UID or a tuple
                        uid = result
                        if isinstance(result, tuple) and len(result) == 2:
                            uid, _ = result
                            
                        print(f"\n✅ Tag detected! UID: {uid}")
                        
                        # Check if tag has media association
                        media_info = db_manager.get_media_for_tag(uid)
                        if media_info:
                            print(f"  Tag is associated with media: {media_info.get('title')}")
                        else:
                            print("  Tag is not associated with any media")
                        
                        # Now try to read NDEF data separately with proper error handling
                        try:
                            ndef_data = nfc_controller.read_ndef_data()
                            if ndef_data:
                                print("\nNDEF data found:")
                                print(f"  Type: {ndef_data.get('type', 'Unknown')}")
                                
                                if 'records' in ndef_data:
                                    for i, record in enumerate(ndef_data['records']):
                                        print(f"\n  Record {i+1}:")
                                        
                                        # Show TNF and type info
                                        tnf = record.get('type_name_format', record.get('tnf', 'Unknown'))
                                        record_type = record.get('type', 'Unknown')
                                        print(f"    TNF: {tnf}")
                                        print(f"    Type: {record_type}")
                                        
                                        # Show decoded info if available
                                        if 'decoded' in record:
                                            decoded_type = record['decoded'].get('type')
                                            print(f"    Decoded Type: {decoded_type}")
                                            
                                            if decoded_type == 'uri':
                                                uri = record['decoded'].get('uri')
                                                print(f"    URI: {uri}")
                                            elif decoded_type == 'text':
                                                text = record['decoded'].get('text')
                                                print(f"    Text: {text}")
                                            else:
                                                print(f"    Decoded Data: {record['decoded']}")
                                        # Show raw payload if no decoded info
                                        elif 'payload' in record:
                                            payload = record.get('payload')
                                            if isinstance(payload, bytes):
                                                try:
                                                    payload_str = payload.decode('utf-8')
                                                    print(f"    Payload (text): {payload_str}")
                                                except UnicodeDecodeError:
                                                    print(f"    Payload (hex): {payload.hex()}")
                                            else:
                                                print(f"    Payload: {payload}")
                                        else:
                                            print(f"    Raw: {record}")
                            else:
                                print("\nNo NDEF data found on tag")
                        except Exception as e:
                            print(f"\nCould not read NDEF data: {e}")
                        
                        break
                    
                    # Visual feedback during polling
                    print(".", end="", flush=True)
                    time.sleep(0.1)
                
                if not detected:
                    print("\n❌ No tag detected within 10 seconds")
            except Exception as e:
                print(f"\n❌ Error during tag detection: {e}")
            
        elif choice == '3':
            # Start continuous tag detection
            global nfc_detection_thread, nfc_detection_running, _nfc_exit_event
            
            if nfc_detection_running:
                print("Tag detection is already running")
                continue
            
            print_subheader("Starting Continuous Tag Detection")
            print("Monitoring for NFC tags. Place and remove tags to see detection in action.")
            print("Press Enter to stop...")
            
            # Clean up any existing exit event
            if _nfc_exit_event is not None:
                _nfc_exit_event.set()
                _nfc_exit_event = None
                
            # Create and start a new detection thread
            nfc_detection_running = True
            nfc_detection_thread = threading.Thread(
                target=nfc_detection_worker,
                name="NFC-Detection-Thread"
            )
            nfc_detection_thread.daemon = True
            nfc_detection_thread.start()
            
            # Give the thread a moment to start
            time.sleep(0.5)
            
            # Check if it started successfully
            if not nfc_detection_thread.is_alive():
                print("❌ NFC detection failed to start")
                nfc_detection_running = False
                continue
                
            print("✅ NFC detection running - waiting for tags")
            
        elif choice == '4':
            # Stop tag detection
            if not nfc_detection_running:
                print("Tag detection is not currently running")
                continue
            
            stop_nfc_detection()
            print("✅ Tag detection stopped")
            
        elif choice == '5':
            # Write NDEF URL to tag
            print_subheader("Write NDEF URL to Tag")
            url = input("Enter URL to write (e.g., https://youtube.com/watch?v=...): ").strip()
            
            if not url:
                print("No URL provided, cancelling operation")
                continue
            
            print("\nPlace tag on reader and press Enter to write...")
            input()
            
            # First detect the tag to ensure it's present
            try:
                # Poll for the tag first (without reading NDEF data)
                result = nfc_controller.poll_for_tag(read_ndef=False)
                if not result:
                    print("❌ No tag detected! Please make sure the tag is on the reader.")
                    continue
                
                # Convert the result to a UID string
                if isinstance(result, tuple) and len(result) == 2:
                    uid = result[0]  # Unpack tuple
                else:
                    uid = result
                
                print(f"✅ Tag detected: {uid}")
                print(f"Writing URL: {url}")
                
                # Now write to the tag
                if nfc_controller.write_ndef_uri(url):
                    print("✅ Successfully wrote URL to tag")
                    
                    # Verify by reading back
                    try:
                        print("Verifying by reading NDEF data...")
                        ndef_data = nfc_controller.read_ndef_data()
                        
                        if ndef_data:
                            found_url = None
                            
                            # Check direct URI in message
                            if ndef_data.get('type') == 'uri':
                                found_url = ndef_data.get('uri')
                            
                            # Check in records
                            elif 'records' in ndef_data:
                                for record in ndef_data['records']:
                                    if 'decoded' in record and record['decoded'].get('type') == 'uri':
                                        found_url = record['decoded'].get('uri')
                                        break
                            
                            if found_url and found_url == url:
                                print("✅ Verification successful - URL was written correctly")
                            elif found_url:
                                print(f"⚠️ Found URL: {found_url} (differs from written URL)")
                            else:
                                print("⚠️ Could not find URL in NDEF data after writing")
                        else:
                            print("⚠️ Could not read NDEF data for verification")
                    except Exception as verify_e:
                        print(f"⚠️ Could not verify data: {verify_e}")
                else:
                    print("❌ Failed to write URL to tag")
            except Exception as e:
                print(f"❌ Error writing to tag: {e}")
            
        elif choice == '6':
            # Read NDEF data from tag
            print_subheader("Read NDEF Data from Tag")
            print("Place tag on reader and press Enter to read...")
            input()
            
            # First make sure we have the tag
            uid = None
            try:
                # Poll for tag first to ensure it's present (without reading NDEF yet)
                result = nfc_controller.poll_for_tag(read_ndef=False)
                if not result:
                    print("❌ No tag detected. Please make sure the tag is on the reader.")
                    continue
                
                # Handle the return value which could be just a UID or a tuple
                uid = result
                if isinstance(result, tuple) and len(result) == 2:
                    uid, _ = result
                
                print(f"✅ Tag detected: {uid}")
                
                # Now try to read NDEF data
                ndef_data = nfc_controller.read_ndef_data()
                
                if ndef_data:
                    print("✅ NDEF data found:")
                    print(f"  Message type: {ndef_data.get('type', 'Unknown')}")
                    
                    # Show top-level URI or text if available
                    if ndef_data.get('type') == 'uri':
                        print(f"  URI: {ndef_data.get('uri')}")
                    elif ndef_data.get('type') == 'text':
                        print(f"  Text: {ndef_data.get('text')}")
                    
                    # Process all records
                    records = ndef_data.get('records', [])
                    print(f"\n  Number of records: {len(records)}")
                    
                    for i, record in enumerate(records, 1):
                        print(f"\n  Record {i}:")
                        
                        # Show TNF and type info
                        tnf = record.get('type_name_format', record.get('tnf', 'Unknown'))
                        record_type = record.get('type', 'Unknown')
                        print(f"    TNF: {tnf}")
                        print(f"    Type: {record_type}")
                        
                        # Show decoded info if available
                        if 'decoded' in record:
                            decoded_type = record['decoded'].get('type')
                            print(f"    Decoded Type: {decoded_type}")
                            
                            if decoded_type == 'uri':
                                uri = record['decoded'].get('uri')
                                print(f"    URI: {uri}")
                            elif decoded_type == 'text':
                                text = record['decoded'].get('text')
                                language = record['decoded'].get('language', 'en')
                                print(f"    Text: {text}")
                                print(f"    Language: {language}")
                            else:
                                print(f"    Decoded Data: {record['decoded']}")
                                
                        # Show raw payload if available
                        if 'payload' in record:
                            try:
                                payload = record.get('payload')
                                if isinstance(payload, bytes):
                                    try:
                                        payload_str = payload.decode('utf-8', errors='replace')
                                        print(f"    Payload (text): {payload_str}")
                                    except:
                                        print(f"    Payload (hex): {payload.hex()}")
                                else:
                                    print(f"    Payload: {payload}")
                            except Exception as payload_e:
                                print(f"    Payload: [Cannot display: {payload_e}]")
                else:
                    print("❌ No NDEF data found on tag")
                    
                    # For debugging, try to read raw data from block 4
                    try:
                        print("\nReading raw data from block 4 for debugging:")
                        raw_data = nfc_controller.read_tag_data(4)
                        print(f"  Block 4 (hex): {raw_data.hex()}")
                        print(f"  Block 4 (ASCII): {raw_data.decode('ascii', errors='replace')}")
                    except Exception as raw_e:
                        print(f"  Could not read raw data: {raw_e}")
                    
            except Exception as e:
                if uid:
                    print(f"❌ Error reading NDEF data: {e}")
                else:
                    print(f"❌ Error detecting tag: {e}")
            
        elif choice == '7':
            # Back to main menu
            # Make sure to stop detection if running
            if nfc_detection_running:
                print("Stopping NFC detection before returning to main menu...")
                stop_nfc_detection()
                print("Returning to main menu")
            return
        
        wait_for_key()

def tag_callback(uid, ndef_info=None):
    """
    Callback function for tag detection.
    Handles both callback signatures (with and without NDEF info).
    """
    # Handle tuple return value from poll_for_tag when read_ndef=True
    if isinstance(uid, tuple) and len(uid) == 2:
        uid_str, ndef_data = uid
        if ndef_info is None:
            ndef_info = ndef_data
        uid = uid_str
    
    print(f"\n✅ Tag detected: {uid}")
    
    # Check if tag has media association
    media_info = db_manager.get_media_for_tag(uid)
    if media_info:
        print(f"  Tag associated with: {media_info.get('title', 'Unknown')}")
        
        # Get the media path and play
        try:
            print("  Preparing media for playback...")
            
            # Check if we have a connected Bluetooth device
            connected_device = audio_controller.get_connected_device()
            if not connected_device:
                print("  ⚠️ Warning: No Bluetooth device connected")
                print("  Will attempt to play through default audio output")
            else:
                print(f"  Audio will play through: {connected_device.get('name', 'Unknown device')}")
            
            # Prepare the media (download/cache if needed)
            media_path = media_manager.prepare_media(media_info)
            print(f"  Playing {media_path}...")
            
            # Start playback
            if audio_controller.play(media_path):
                print("  ✅ Playback started")
                print("  To stop playback, place the tag on the reader again or remove it")
                # Note: We don't wait for input here because this is in the continuous detection mode
                # The user can stop playback by interrupting the detection
            else:
                print("  ❌ Failed to start playback")
        except Exception as e:
            print(f"  ❌ Error playing media: {e}")
    else:
        print("  No media associated with this tag")
        
        # Check for NDEF URL - we might need to read NDEF data separately if it wasn't provided
        if ndef_info is None:
            try:
                ndef_info = nfc_controller.read_ndef_data()
                print("  Read NDEF data separately")
            except Exception as e:
                print(f"  Could not read NDEF data: {e}")
                ndef_info = None
        
        # Process NDEF data if available
        if ndef_info:
            # Look for URI records in NDEF data
            uri = None
            
            # Try to get URI directly from NDEF structure
            if ndef_info.get('type') == 'uri':
                uri = ndef_info.get('uri')
                print(f"  Found URL in tag: {uri}")
                
            # Otherwise, search through records for a URI
            elif 'records' in ndef_info:
                for record in ndef_info['records']:
                    if 'decoded' in record and record['decoded'].get('type') == 'uri':
                        uri = record['decoded'].get('uri')
                        print(f"  Found URL in tag records: {uri}")
                        break
            
            # If we have a URI, check if it's a YouTube URL
            if uri and ('youtube.com' in uri or 'youtu.be' in uri):
                try:
                    print("  Found YouTube URL in tag")
                    print(f"  URL: {uri}")
                    print("  Getting YouTube info...")
                    
                    # Fetch video information
                    youtube_info = media_manager.get_media_info(uri)
                    if youtube_info:
                        print(f"  ✅ Title: {youtube_info.get('title')}")
                        print(f"  Duration: {youtube_info.get('duration')} seconds")
                        print(f"  Channel: {youtube_info.get('uploader', 'Unknown')}")
                        
                        # Ask if we should play it
                        play_it = input("  Play this YouTube video? (y/n): ").strip().lower() == 'y'
                        if play_it:
                            print("  Adding to database...")
                            media_id = db_manager.add_or_get_media_by_url(uri, tag_uid=uid)
                            if media_id:
                                media_info = db_manager.get_media_info(media_id)
                                
                                # Check Bluetooth connectivity
                                connected_device = audio_controller.get_connected_device()
                                if not connected_device:
                                    print("  ⚠️ Warning: No Bluetooth device connected")
                                    print("  Will attempt to play through default audio output")
                                else:
                                    print(f"  Audio will play through: {connected_device.get('name', 'Unknown device')}")
                                
                                print("  Preparing media for playback...")
                                try:
                                    # Prepare and play media
                                    media_path = media_manager.prepare_media(media_info)
                                    print(f"  Playing {media_path}...")
                                    
                                    if audio_controller.play(media_path):
                                        print("  ✅ Playback started")
                                        print("  To stop playback, place the tag on the reader again or remove it")
                                    else:
                                        print("  ❌ Failed to start playback")
                                except Exception as play_e:
                                    print(f"  ❌ Error during playback: {play_e}")
                            else:
                                print("  ❌ Failed to add media to database")
                    else:
                        print("  ❌ Could not retrieve YouTube video information")
                except Exception as e:
                    print(f"  ❌ Error processing YouTube URL: {e}")

def nfc_detection_worker():
    """Worker function for continuous tag detection."""
    global nfc_detection_running
    
    # Create an exit event to signal when to stop polling
    exit_event = threading.Event()
    
    print("Starting continuous NFC tag detection...")
    
    # This variable is shared between this function and stop_nfc_detection
    # We need to store it in a global variable to signal when to stop
    global _nfc_exit_event
    _nfc_exit_event = exit_event
    
    try:
        # Set up tag detection callback
        def tag_callback_wrapper(uid, ndef_info=None):
            global _last_detected_tag
            
            # Only process if still running
            if nfc_detection_running:
                try:
                    # Handle tuple return value from poll_for_tag when read_ndef=True
                    if isinstance(uid, tuple) and len(uid) == 2:
                        uid_str, ndef_data = uid
                        if ndef_info is None:
                            ndef_info = ndef_data
                        uid = uid_str
                    
                    # Check if this is a new tag or tag removal
                    if uid is None or uid == "":
                        # No tag detected, which could mean a tag was removed
                        if _last_detected_tag:
                            print(f"\n🔄 Tag {_last_detected_tag} removed")
                            
                            # Stop any ongoing playback when tag is removed
                            try:
                                print("Stopping audio playback...")
                                audio_controller.stop()
                            except Exception as audio_e:
                                print(f"Error stopping audio: {audio_e}")
                            
                            # Reset last detected tag
                            _last_detected_tag = None
                    else:
                        # Check if this is the same tag as before
                        if uid != _last_detected_tag:
                            # It's a new tag or a different tag
                            # Stop any existing playback before handling new tag
                            if _last_detected_tag:
                                try:
                                    audio_controller.stop()
                                except:
                                    pass
                            
                            # Call our tag callback for the new tag
                            tag_callback(uid, ndef_info)
                            
                            # Update last detected tag
                            _last_detected_tag = uid
                            
                            # Sleep briefly to avoid immediate re-detection of the same tag
                            # and to give user time to process the result
                            print("\nWaiting for 2 seconds before detecting next tag...")
                            time.sleep(2)
                            print("Ready for next tag")
                        else:
                            # Same tag detected again, no need to process
                            pass
                except Exception as e:
                    print(f"❌ Error in tag callback: {e}")
            
        # Start the continuous polling (this will run until exit_event is set)
        nfc_controller.continuous_poll(
            callback=tag_callback_wrapper,
            interval=0.1, 
            exit_event=exit_event,
            read_ndef=True
        )
    except Exception as e:
        print(f"❌ Error during NFC detection: {e}")
    finally:
        # Make sure the exit event is set
        exit_event.set()
        print("NFC detection worker stopped")
        nfc_detection_running = False

def stop_nfc_detection():
    """Stop NFC tag detection."""
    global nfc_detection_running, nfc_detection_thread, _nfc_exit_event, _last_detected_tag
    
    # First signal the exit event to tell the continuous polling to stop
    if '_nfc_exit_event' in globals() and _nfc_exit_event is not None:
        _nfc_exit_event.set()
    
    # Set the running flag to false
    nfc_detection_running = False
    
    # If a tag was detected, clear it and stop any playback
    if _last_detected_tag is not None:
        print(f"Stopping any playback from tag {_last_detected_tag}")
        try:
            audio_controller.stop()
        except:
            pass
        _last_detected_tag = None
    
    # Wait for the detection thread to terminate
    if nfc_detection_thread and nfc_detection_thread.is_alive():
        print("Waiting for NFC detection to stop...")
        nfc_detection_thread.join(2.0)
        if nfc_detection_thread.is_alive():
            print("Warning: NFC detection thread is still running")
        else:
            print("NFC detection thread stopped")
    
    # Clean up
    nfc_detection_thread = None
    if '_nfc_exit_event' in globals():
        _nfc_exit_event = None

def test_media():
    """Test media functionality."""
    print_header("Media Management Test")
    
    while True:
        options = [
            "Show cache status",
            "Add YouTube media",
            "List all media",
            "Play media by ID",
            "Delete media from cache",
            "Clean cache",
            "Back to main menu"
        ]
        
        print_menu("Media Menu", options)
        choice = input("Enter choice (1-7): ").strip()
        
        if choice == '1':
            # Show cache status
            print_subheader("Media Cache Status")
            
            status = media_manager.get_cache_status()
            print(f"  Cache directory: {status.get('cache_dir')}")
            print(f"  Cache exists: {status.get('cache_exists')}")
            print(f"  Total files: {status.get('total_files')}")
            print(f"  Total size: {status.get('total_size_mb', 0):.2f} MB")
            print(f"  Maximum size: {status.get('max_size_mb')} MB")
            
            if status.get('newest_file'):
                print(f"  Newest file: {status.get('newest_file')}")
                print(f"  Newest timestamp: {status.get('newest_timestamp')}")
            
            if status.get('oldest_file'):
                print(f"  Oldest file: {status.get('oldest_file')}")
                print(f"  Oldest timestamp: {status.get('oldest_timestamp')}")
            
        elif choice == '2':
            # Add YouTube media
            print_subheader("Add YouTube Media")
            url = input("Enter YouTube URL: ").strip()
            
            if not url:
                print("No URL provided, cancelling operation")
                continue
            
            print("\nGetting information from YouTube...")
            try:
                info = media_manager.get_media_info(url)
                
                print("\nVideo information:")
                print(f"  Title: {info.get('title')}")
                print(f"  Duration: {info.get('duration')} seconds")
                print(f"  Uploader: {info.get('uploader')}")
                
                confirm = input("\nAdd this video to the library? (y/n): ").strip().lower() == 'y'
                if confirm:
                    # Add to database
                    media_id = db_manager.add_or_get_media_by_url(url)
                    if media_id:
                        print(f"✅ Media added with ID: {media_id}")
                        
                        # Ask if we want to associate with a tag
                        associate = input("\nAssociate with an NFC tag? (y/n): ").strip().lower() == 'y'
                        if associate:
                            print("\nPlace the tag on the reader and press Enter...")
                            input()
                            
                            # Try to read the tag
                            result = nfc_controller.poll_for_tag(read_ndef=True)
                            if result:
                                # Handle both possible return types
                                if isinstance(result, tuple) and len(result) == 2:
                                    tag_uid, _ = result  # Unpack tuple
                                else:
                                    tag_uid = result  # Just the UID
                                
                                # Associate tag with media
                                if db_manager.associate_tag_with_media(tag_uid, media_id):
                                    print(f"✅ Tag {tag_uid} associated with media {media_id}")
                                else:
                                    print("❌ Failed to associate tag with media")
                            else:
                                print("❌ No tag detected")
                    else:
                        print("❌ Failed to add media to database")
                else:
                    print("Operation cancelled")
                    
            except Exception as e:
                print(f"❌ Error getting YouTube info: {e}")
            
        elif choice == '3':
            # List all media
            print_subheader("Media Library")
            
            # Get all media from database
            media_list = db_manager.get_all_media()
            
            if media_list:
                print(f"Found {len(media_list)} media items:")
                for i, media in enumerate(media_list, 1):
                    title = media.get('title', 'Unknown')
                    media_id = media.get('id', 'Unknown')
                    media_type = media.get('type', 'Unknown')
                    source = media.get('source_url', '')
                    if len(source) > 40:
                        source = source[:37] + "..."
                    
                    # Check if in cache
                    cache_status = media_manager.get_media_cache_status(media_id)
                    cached = "✅ Cached" if cache_status.get('cached') else "❌ Not cached"
                    
                    # Check if has tag associations
                    tags = db_manager.get_tags_for_media(media_id)
                    tag_count = len(tags) if tags else 0
                    
                    print(f"  {i}. {title} (ID: {media_id})")
                    print(f"     Type: {media_type} | {cached} | Tags: {tag_count}")
                    if source:
                        print(f"     Source: {source}")
                    print()
            else:
                print("No media found in the database")
            
        elif choice == '4':
            # Play media by ID
            print_subheader("Play Media")
            
            media_id = input("Enter media ID: ").strip()
            if not media_id:
                print("No media ID provided, cancelling operation")
                continue
            
            # Get media info
            media_info = db_manager.get_media_info(media_id)
            
            if not media_info:
                print(f"❌ Media with ID {media_id} not found")
                continue
            
            print(f"Preparing media: {media_info.get('title')}")
            try:
                # Prepare and play media
                media_path = media_manager.prepare_media(media_info)
                print(f"Playing {media_path}...")
                
                if audio_controller.play(media_path):
                    print("✅ Playback started")
                    
                    # Wait for playback to complete or user interruption
                    print("Press Enter to stop playback...")
                    input()
                    audio_controller.stop()
                    print("Playback stopped")
                else:
                    print("❌ Failed to start playback")
            except Exception as e:
                print(f"❌ Error playing media: {e}")
            
        elif choice == '5':
            # Delete media from cache
            print_subheader("Delete Media from Cache")
            
            media_id = input("Enter media ID to delete from cache: ").strip()
            if not media_id:
                print("No media ID provided, cancelling operation")
                continue
            
            # Check if in cache
            cache_status = media_manager.get_media_cache_status(media_id)
            
            if not cache_status.get('cached'):
                print(f"Media {media_id} is not in cache")
                continue
            
            # Delete from cache
            print(f"Deleting media {media_id} from cache...")
            try:
                if media_manager.delete_from_cache(media_id):
                    print("✅ Media deleted from cache")
                else:
                    print("❌ Failed to delete media from cache")
            except Exception as e:
                print(f"❌ Error deleting media: {e}")
            
        elif choice == '6':
            # Clean cache
            print_subheader("Clean Media Cache")
            
            # Get current cache status
            status = media_manager.get_cache_status()
            current_size = status.get('total_size_mb', 0)
            max_size = status.get('max_size_mb')
            
            print(f"Current cache size: {current_size:.2f} MB / {max_size} MB")
            
            # Ask how to clean
            print("\nCleaning options:")
            print("  1. Clean files older than X days")
            print("  2. Clean cache to stay under size limit")
            print("  3. Force clean everything")
            print("  4. Cancel")
            
            clean_choice = input("\nSelect option (1-4): ").strip()
            
            if clean_choice == '1':
                days = input("Delete files older than how many days? ").strip()
                if days and days.isdigit():
                    days = int(days)
                    print(f"Cleaning files older than {days} days...")
                    result = media_manager.clean_cache(older_than=days)
                    print(f"✅ {result.get('deleted_files')} files deleted ({result.get('cleaned_bytes') / (1024*1024):.2f} MB)")
                else:
                    print("Invalid input, cancelling operation")
            
            elif clean_choice == '2':
                print("Cleaning cache to stay under size limit...")
                result = media_manager.clean_cache()
                print(f"✅ {result.get('deleted_files')} files deleted ({result.get('cleaned_bytes') / (1024*1024):.2f} MB)")
            
            elif clean_choice == '3':
                confirm = input("This will delete ALL cached media. Continue? (y/n): ").strip().lower() == 'y'
                if confirm:
                    print("Force cleaning all cached media...")
                    result = media_manager.clean_cache(force=True)
                    print(f"✅ {result.get('deleted_files')} files deleted ({result.get('cleaned_bytes') / (1024*1024):.2f} MB)")
                else:
                    print("Operation cancelled")
            
            elif clean_choice == '4':
                print("Cleaning cancelled")
            
            else:
                print("Invalid choice, cancelling operation")
            
        elif choice == '7':
            # Back to main menu
            return
        
        wait_for_key()

def test_database():
    """Test database functionality."""
    print_header("Database Management Test")
    
    while True:
        options = [
            "Show database statistics",
            "List all tags",
            "List all media",
            "Create tag-media association",
            "Delete tag-media association",
            "Export database to JSON",
            "Back to main menu"
        ]
        
        print_menu("Database Menu", options)
        choice = input("Enter choice (1-7): ").strip()
        
        if choice == '1':
            # Show database statistics
            print_subheader("Database Statistics")
            
            # Get counts
            tag_count = db_manager.get_tag_count()
            active_tag_count = db_manager.get_active_tag_count()
            media_count = db_manager.get_media_count()
            youtube_count = db_manager.get_media_count_by_type('youtube')
            local_count = db_manager.get_media_count_by_type('local')
            
            print(f"  Total tags: {tag_count}")
            print(f"  Active tags (with media): {active_tag_count}")
            print(f"  Total media: {media_count}")
            print(f"  YouTube media: {youtube_count}")
            print(f"  Local media: {local_count}")
            
            # Get database file info
            db_path = CONFIG['database']['path']
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)
                db_modified = time.ctime(os.path.getmtime(db_path))
                print(f"\n  Database path: {db_path}")
                print(f"  Database size: {db_size / 1024:.2f} KB")
                print(f"  Last modified: {db_modified}")
            else:
                print(f"\n  Database path: {db_path} (file not found)")
            
        elif choice == '2':
            # List all tags
            print_subheader("NFC Tags")
            
            # Get all tags
            tags = db_manager.get_all_tags()
            
            if tags:
                print(f"Found {len(tags)} tags:")
                for i, tag in enumerate(tags, 1):
                    uid = tag.get('uid', 'Unknown')
                    last_seen = tag.get('last_seen', 0)
                    if last_seen:
                        last_seen_str = time.ctime(last_seen)
                    else:
                        last_seen_str = "Never"
                    
                    # Get associated media
                    media_info = db_manager.get_media_for_tag(uid)
                    if media_info:
                        media_title = media_info.get('title', 'Unknown')
                        media_id = media_info.get('id', 'Unknown')
                        media_str = f"{media_title} (ID: {media_id})"
                    else:
                        media_str = "None"
                    
                    print(f"  {i}. UID: {uid}")
                    print(f"     Last seen: {last_seen_str}")
                    print(f"     Associated media: {media_str}")
                    print()
            else:
                print("No tags found in the database")
            
        elif choice == '3':
            # List all media
            print_subheader("Media Library")
            
            # Get all media
            media_list = db_manager.get_all_media()
            
            if media_list:
                print(f"Found {len(media_list)} media items:")
                for i, media in enumerate(media_list, 1):
                    title = media.get('title', 'Unknown')
                    media_id = media.get('id', 'Unknown')
                    media_type = media.get('type', 'Unknown')
                    source = media.get('source_url', '')
                    if len(source) > 40:
                        source = source[:37] + "..."
                    
                    # Get tags for this media
                    tags = db_manager.get_tags_for_media(media_id)
                    if tags:
                        tag_str = ", ".join([t.get('uid', 'Unknown') for t in tags])
                    else:
                        tag_str = "None"
                    
                    print(f"  {i}. {title} (ID: {media_id})")
                    print(f"     Type: {media_type}")
                    print(f"     Associated tags: {tag_str}")
                    if source:
                        print(f"     Source: {source}")
                    print()
            else:
                print("No media found in the database")
            
        elif choice == '4':
            # Create tag-media association
            print_subheader("Create Tag-Media Association")
            
            # First, get the tag
            print("Place the tag on the reader and press Enter...")
            input()
            
            result = nfc_controller.poll_for_tag(read_ndef=False)
            if not result:
                print("❌ No tag detected")
                continue
            
            # Handle both possible return types
            if isinstance(result, tuple) and len(result) == 2:
                tag_uid, _ = result  # Unpack tuple
            else:
                tag_uid = result  # Just the UID
            
            print(f"✅ Tag detected: {tag_uid}")
            
            # Check if tag already has an association
            current_media = db_manager.get_media_for_tag(tag_uid)
            if current_media:
                print(f"⚠️ This tag is already associated with: {current_media.get('title', 'Unknown')}")
                overwrite = input("Overwrite this association? (y/n): ").strip().lower() == 'y'
                if not overwrite:
                    print("Operation cancelled")
                    continue
            
            # Now, select media
            media_list = db_manager.get_all_media()
            if not media_list:
                print("❌ No media found in the database. Add media first.")
                continue
            
            print("\nAvailable media:")
            for i, media in enumerate(media_list, 1):
                title = media.get('title', 'Unknown')
                media_id = media.get('id', 'Unknown')
                print(f"  {i}. {title} (ID: {media_id})")
            
            # Ask for selection
            selection = input("\nSelect media by number (or press Enter to cancel): ").strip()
            if selection and selection.isdigit() and 0 < int(selection) <= len(media_list):
                media_index = int(selection) - 1
                media = media_list[media_index]
                media_id = media.get('id')
                
                # Create association
                print(f"Associating tag {tag_uid} with media {media.get('title')}...")
                if db_manager.associate_tag_with_media(tag_uid, media_id):
                    print("✅ Association created successfully")
                else:
                    print("❌ Failed to create association")
            else:
                print("Operation cancelled")
            
        elif choice == '5':
            # Delete tag-media association
            print_subheader("Delete Tag-Media Association")
            
            # First, get the tag
            print("Place the tag on the reader and press Enter...")
            input()
            
            result = nfc_controller.poll_for_tag(read_ndef=False)
            if not result:
                print("❌ No tag detected")
                continue
            
            # Handle both possible return types
            if isinstance(result, tuple) and len(result) == 2:
                tag_uid, _ = result  # Unpack tuple
            else:
                tag_uid = result  # Just the UID
            
            print(f"✅ Tag detected: {tag_uid}")
            
            # Check if tag has an association
            current_media = db_manager.get_media_for_tag(tag_uid)
            if not current_media:
                print("⚠️ This tag has no media association")
                continue
            
            print(f"This tag is associated with: {current_media.get('title', 'Unknown')}")
            confirm = input("Delete this association? (y/n): ").strip().lower() == 'y'
            
            if confirm:
                # Delete association
                if db_manager.remove_tag_media_association(tag_uid):
                    print("✅ Association deleted successfully")
                else:
                    print("❌ Failed to delete association")
            else:
                print("Operation cancelled")
            
        elif choice == '6':
            # Export database to JSON
            print_subheader("Export Database to JSON")
            
            filename = input("Enter output filename (default: db_export.json): ").strip()
            if not filename:
                filename = "db_export.json"
            
            # Ensure the filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Create export data
            export_data = {
                'tags': db_manager.get_all_tags(),
                'media': db_manager.get_all_media(),
                'export_date': time.ctime(),
                'version': '1.0'
            }
            
            # Write to file
            try:
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                print(f"✅ Database exported to {filename}")
                print(f"   Tags: {len(export_data['tags'])}")
                print(f"   Media: {len(export_data['media'])}")
            except Exception as e:
                print(f"❌ Error exporting database: {e}")
            
        elif choice == '7':
            # Back to main menu
            return
        
        wait_for_key()

def test_api():
    """Test API server functionality."""
    print_header("API Server Test")
    
    while True:
        options = [
            "Show API server status",
            "Start API server",
            "Stop API server",
            "Open API in web browser",
            "Back to main menu"
        ]
        
        print_menu("API Server Menu", options)
        choice = input("Enter choice (1-5): ").strip()
        
        if choice == '1':
            # Show API server status
            print_subheader("API Server Status")
            
            status = api_server.get_api_status()
            
            print(f"  Running: {status.get('running', False)}")
            
            if status.get('running'):
                print(f"  URL: {status.get('url')}")
                print(f"  Uptime: {status.get('uptime_formatted')}")
                print(f"  Request count: {status.get('request_count', 0)}")
            
        elif choice == '2':
            # Start API server
            print_subheader("Start API Server")
            
            if api_server.is_running():
                print("API server is already running")
                continue
            
            print("Starting API server...")
            if api_server.start():
                print(f"✅ API server started at {api_server.get_server_url()}")
            else:
                print("❌ Failed to start API server")
            
        elif choice == '3':
            # Stop API server
            print_subheader("Stop API Server")
            
            if not api_server.is_running():
                print("API server is not running")
                continue
            
            print("Stopping API server...")
            if api_server.stop():
                print("✅ API server stopped")
            else:
                print("❌ Failed to stop API server")
            
        elif choice == '4':
            # Open API in web browser
            print_subheader("Open API in Web Browser")
            
            if not api_server.is_running():
                print("API server is not running")
                continue
            
            url = api_server.get_server_url()
            print(f"API server is running at: {url}")
            
            try:
                # Try to open in browser
                import webbrowser
                if webbrowser.open(url):
                    print("✅ Opened in browser")
                else:
                    print("❌ Failed to open browser")
                    print(f"Manually navigate to: {url}")
            except Exception as e:
                print(f"❌ Error opening browser: {e}")
                print(f"Manually navigate to: {url}")
            
        elif choice == '5':
            # Back to main menu
            return
        
        wait_for_key()

def main():
    """Main function."""
    try:
        # Initialize system components
        initialize_system()
        
        # Main loop
        while True:
            print_header("NFC Music Player System Test")
            
            options = [
                "Test Bluetooth functionality",
                "Test NFC functionality",
                "Test Media functionality",
                "Test Database functionality",
                "Test API server",
                "Reinitialize system",
                "Exit"
            ]
            
            print_menu("Main Menu", options)
            choice = input("Enter choice (1-7): ").strip()
            
            if choice == '1':
                test_bluetooth()
            elif choice == '2':
                test_nfc()
            elif choice == '3':
                test_media()
            elif choice == '4':
                test_database()
            elif choice == '5':
                test_api()
            elif choice == '6':
                print_header("Reinitializing System")
                # Shutdown first
                shutdown_system()
                time.sleep(1)
                # Then initialize again
                initialize_system()
                print("\nSystem reinitialized!")
                wait_for_key()
            elif choice == '7':
                # Exit
                # Make sure continuous NFC detection is stopped before exiting
                if nfc_detection_running:
                    print("Stopping NFC detection before exit...")
                    stop_nfc_detection()
                break
            else:
                print("Invalid choice. Please try again.")
    
    except KeyboardInterrupt:
        print("\nProgram interrupted")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        # Perform cleanup
        print("\nShutting down system...")
        shutdown_system()
        print("\nGoodbye!")

if __name__ == "__main__":
    main()