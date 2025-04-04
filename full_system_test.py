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

# NFC tag detection thread
nfc_detection_thread = None
nfc_detection_running = False

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
            print("Playing test sound...")
            
            if audio_controller.test_audio_output():
                print("✅ Audio test successful")
            else:
                print("❌ Audio test failed")
            
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
            # Poll for NFC tag (once)
            print_subheader("Polling for NFC Tag")
            print("Waiting for tag (10 seconds)...")
            
            # Try for up to 10 seconds
            tag_found = False
            for i in range(10):
                tag_uid, ndef_info = nfc_controller.poll_for_tag(read_ndef=True)
                
                if tag_uid:
                    tag_found = True
                    print(f"\n✅ Tag detected: {tag_uid}")
                    
                    # Check if tag has media association
                    media_info = db_manager.get_media_for_tag(tag_uid)
                    if media_info:
                        print(f"  Tag is associated with media: {media_info.get('title')}")
                    else:
                        print("  Tag is not associated with any media")
                    
                    # Check for NDEF data
                    if ndef_info:
                        print("\nNDEF data found:")
                        print(f"  Type: {ndef_info.get('type')}")
                        if ndef_info.get('type') == 'uri':
                            print(f"  URI: {ndef_info.get('uri')}")
                        elif ndef_info.get('type') == 'text':
                            print(f"  Text: {ndef_info.get('text')}")
                    else:
                        print("\nNo NDEF data found on tag")
                    
                    break
                
                print(".", end="", flush=True)
                time.sleep(1)
            
            if not tag_found:
                print("\n❌ No tag detected within 10 seconds")
            
        elif choice == '3':
            # Start continuous tag detection
            global nfc_detection_thread, nfc_detection_running
            
            if nfc_detection_running:
                print("Tag detection is already running")
                continue
            
            print_subheader("Starting Continuous Tag Detection")
            print("Monitoring for NFC tags. Press Enter to stop...")
            
            # Start detection in a separate thread
            nfc_detection_running = True
            nfc_detection_thread = threading.Thread(target=nfc_detection_worker)
            nfc_detection_thread.daemon = True
            nfc_detection_thread.start()
            
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
            
            try:
                # Try to write the URL
                if nfc_controller.write_ndef_uri(url):
                    print("✅ Successfully wrote URL to tag")
                else:
                    print("❌ Failed to write URL to tag")
            except Exception as e:
                print(f"❌ Error writing to tag: {e}")
            
        elif choice == '6':
            # Read NDEF data from tag
            print_subheader("Read NDEF Data from Tag")
            print("Place tag on reader and press Enter to read...")
            input()
            
            try:
                # Try to read NDEF data
                ndef_data = nfc_controller.read_ndef_data()
                
                if ndef_data:
                    print("✅ NDEF data found:")
                    print(f"  Message type: {ndef_data.get('type')}")
                    
                    if ndef_data.get('type') == 'uri':
                        print(f"  URI: {ndef_data.get('uri')}")
                    elif ndef_data.get('type') == 'text':
                        print(f"  Text: {ndef_data.get('text')}")
                    
                    records = ndef_data.get('records', [])
                    print(f"\n  Number of records: {len(records)}")
                    
                    for i, record in enumerate(records, 1):
                        print(f"\n  Record {i}:")
                        print(f"    Type: {record.get('type')}")
                        print(f"    TNF: {record.get('tnf')}")
                        if 'payload' in record:
                            # Try to show payload in a readable format
                            try:
                                payload = record.get('payload')
                                if isinstance(payload, bytes):
                                    try:
                                        payload_str = payload.decode('utf-8')
                                        print(f"    Payload: {payload_str}")
                                    except:
                                        print(f"    Payload (hex): {payload.hex()}")
                                else:
                                    print(f"    Payload: {payload}")
                            except:
                                print("    Payload: [Cannot display]")
                else:
                    print("❌ No NDEF data found on tag")
            except Exception as e:
                print(f"❌ Error reading tag: {e}")
            
        elif choice == '7':
            # Back to main menu
            # Make sure to stop detection if running
            if nfc_detection_running:
                stop_nfc_detection()
            return
        
        wait_for_key()

def nfc_detection_worker():
    """Worker function for continuous tag detection."""
    global nfc_detection_running
    last_detected_tag = None
    
    while nfc_detection_running:
        try:
            # Poll for tag
            tag_uid, ndef_info = nfc_controller.poll_for_tag(read_ndef=True)
            
            if tag_uid and tag_uid != last_detected_tag:
                print(f"\n✅ Tag detected: {tag_uid}")
                
                # Check if tag has media association
                media_info = db_manager.get_media_for_tag(tag_uid)
                if media_info:
                    print(f"  Tag associated with: {media_info.get('title', 'Unknown')}")
                    
                    # Get the media path and play
                    try:
                        print("  Preparing media for playback...")
                        media_path = media_manager.prepare_media(media_info)
                        print(f"  Playing {media_path}...")
                        audio_controller.play(media_path)
                    except Exception as e:
                        print(f"  ❌ Error playing media: {e}")
                else:
                    print("  No media associated with this tag")
                    
                    # Check for NDEF URL
                    if ndef_info and ndef_info.get('type') == 'uri':
                        url = ndef_info.get('uri')
                        print(f"  Found URL in tag: {url}")
                        
                        # Check if it's a YouTube URL
                        if 'youtube.com' in url or 'youtu.be' in url:
                            try:
                                print("  Getting YouTube info...")
                                youtube_info = media_manager.get_media_info(url)
                                print(f"  Title: {youtube_info.get('title')}")
                                
                                # Ask if we should play it
                                play_it = input("  Play this YouTube video? (y/n): ").strip().lower() == 'y'
                                if play_it:
                                    print("  Adding to database...")
                                    media_id = db_manager.add_or_get_media_by_url(url, tag_uid=tag_uid)
                                    if media_id:
                                        media_info = db_manager.get_media_info(media_id)
                                        print("  Preparing media for playback...")
                                        media_path = media_manager.prepare_media(media_info)
                                        print(f"  Playing {media_path}...")
                                        audio_controller.play(media_path)
                                    else:
                                        print("  ❌ Failed to add media to database")
                            except Exception as e:
                                print(f"  ❌ Error processing YouTube URL: {e}")
                
                last_detected_tag = tag_uid
            
            # Small delay to prevent CPU overuse
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error in NFC detection worker: {e}")
            time.sleep(1)
    
    print("NFC detection worker stopped")

def stop_nfc_detection():
    """Stop NFC tag detection."""
    global nfc_detection_running, nfc_detection_thread
    
    nfc_detection_running = False
    if nfc_detection_thread and nfc_detection_thread.is_alive():
        # Wait for thread to terminate gracefully
        nfc_detection_thread.join(2.0)
    nfc_detection_thread = None

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
                            tag_uid, _ = nfc_controller.poll_for_tag()
                            if tag_uid:
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
            
            tag_uid, _ = nfc_controller.poll_for_tag()
            if not tag_uid:
                print("❌ No tag detected")
                continue
            
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
            
            tag_uid, _ = nfc_controller.poll_for_tag()
            if not tag_uid:
                print("❌ No tag detected")
                continue
            
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