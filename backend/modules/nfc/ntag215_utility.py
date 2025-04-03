#!/usr/bin/env python3
"""
ntag215_utility.py - Utility script for working with NTAG215 tags

This script provides specialized functions for working with NTAG215 tags,
including reading all user memory, writing data, and checking protection status.
"""

import sys
import os
import argparse
import logging
import time
from datetime import datetime

# Setup path to ensure module imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from backend.modules.nfc import (
        initialize, shutdown, poll_for_tag, read_tag_data, write_tag_data
    )
    from backend.modules.nfc.hardware_interface import NFCReader
except ImportError:
    # Fallback to direct imports if the package structure doesn't match
    sys.path.insert(0, current_dir)
    from nfc_controller import (
        initialize, shutdown, poll_for_tag, read_tag_data, write_tag_data
    )
    from hardware_interface import NFCReader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NTAG215Utility")

def read_full_tag(i2c_bus=1, i2c_address=0x24):
    """Read all available user memory from an NTAG215 tag."""
    print("\n=== Reading NTAG215 Tag ===")
    print("Please place tag on the reader...")
    
    # Initialize NFC reader
    if not initialize(i2c_bus, i2c_address):
        print("❌ Failed to initialize NFC controller")
        return
    
    try:
        # Wait for tag (up to 5 seconds)
        start_time = time.time()
        uid = None
        while time.time() - start_time < 5:
            uid = poll_for_tag()
            if uid:
                break
            time.sleep(0.1)
        
        if not uid:
            print("❌ No tag detected within timeout")
            return
        
        print(f"✅ Tag detected! UID: {uid}")
        
        # Create direct access to hardware interface for tag type detection
        reader = NFCReader(i2c_bus, i2c_address)
        reader.connect()
        reader.poll()  # This will set _last_tag_uid
        
        tag_type = reader.detect_tag_type()
        print(f"📋 Tag type: {tag_type}")
        
        if tag_type != "ntag215":
            print("⚠️ Tag may not be an NTAG215. Reading may not work as expected.")
        
        # Read all user memory (pages 4-130 for NTAG215)
        # This translates to blocks 1-32 (since 1 block = 4 pages)
        print("\n=== NTAG215 Memory Content ===")
        print("Block | Pages | Content (hex) | ASCII")
        print("------+-------+--------------+-------")
        
        all_data = {}
        for block in range(0, 33):  # Block 0-32 (pages 0-130)
            try:
                start_page = block * 4
                end_page = start_page + 3
                
                # Skip blocks beyond page 130
                if start_page > 130:
                    continue
                
                data = read_tag_data(block)
                all_data[block] = data
                
                # Try to convert to ASCII for display
                ascii_str = ""
                for byte in data:
                    if 32 <= byte <= 126:  # Printable ASCII
                        ascii_str += chr(byte)
                    else:
                        ascii_str += "."
                
                print(f"{block:5d} | {start_page:3d}-{min(end_page, 130):3d} | {data.hex()} | {ascii_str}")
                
            except Exception as e:
                print(f"{block:5d} | {start_page:3d}-{min(end_page, 130):3d} | Error: {str(e)}")
        
        return all_data
        
    except Exception as e:
        print(f"❌ Error during tag reading: {str(e)}")
    finally:
        shutdown()
        print("\n✅ NFC controller shut down")

def write_text_to_tag(text, block=1, i2c_bus=1, i2c_address=0x24):
    """Write text to an NTAG215 tag."""
    print(f"\n=== Writing Text to NTAG215 Tag ===")
    print(f"Text: {text}")
    print("Please place tag on the reader...")
    
    # Initialize NFC reader
    if not initialize(i2c_bus, i2c_address):
        print("❌ Failed to initialize NFC controller")
        return False
    
    try:
        # Wait for tag (up to 5 seconds)
        start_time = time.time()
        uid = None
        while time.time() - start_time < 5:
            uid = poll_for_tag()
            if uid:
                break
            time.sleep(0.1)
        
        if not uid:
            print("❌ No tag detected within timeout")
            return False
        
        print(f"✅ Tag detected! UID: {uid}")
        
        # Create direct access to hardware interface for tag type detection
        reader = NFCReader(i2c_bus, i2c_address)
        reader.connect()
        reader.poll()  # This will set _last_tag_uid
        
        tag_type = reader.detect_tag_type()
        print(f"📋 Tag type: {tag_type}")
        
        if tag_type != "ntag215":
            print("⚠️ Tag may not be an NTAG215. Writing may not work as expected.")
        
        # Convert text to bytes and pad to 16 bytes
        data = text.encode('utf-8')
        if len(data) > 16:
            print(f"⚠️ Text too long, truncating to 16 bytes")
            data = data[:16]
        
        data = data.ljust(16, b'\x00')
        
        # Write to specified block
        print(f"Writing data to block {block} (pages {block*4}-{block*4+3})...")
        if write_tag_data(data, block):
            print(f"✅ Successfully wrote text to block {block}")
            return True
        else:
            print(f"❌ Failed to write text to block {block}")
            return False
            
    except Exception as e:
        print(f"❌ Error during tag writing: {str(e)}")
        return False
    finally:
        shutdown()
        print("\n✅ NFC controller shut down")

def check_protection_status(i2c_bus=1, i2c_address=0x24):
    """Check protection status of an NTAG215 tag."""
    print("\n=== Checking NTAG215 Protection Status ===")
    print("Please place tag on the reader...")
    
    # Initialize NFC reader
    if not initialize(i2c_bus, i2c_address):
        print("❌ Failed to initialize NFC controller")
        return
    
    try:
        # Wait for tag (up to 5 seconds)
        start_time = time.time()
        uid = None
        while time.time() - start_time < 5:
            uid = poll_for_tag()
            if uid:
                break
            time.sleep(0.1)
        
        if not uid:
            print("❌ No tag detected within timeout")
            return
        
        print(f"✅ Tag detected! UID: {uid}")
        
        # Create direct access to hardware interface
        reader = NFCReader(i2c_bus, i2c_address)
        reader.connect()
        reader.poll()  # This will set _last_tag_uid
        
        tag_type = reader.detect_tag_type()
        print(f"📋 Tag type: {tag_type}")
        
        if tag_type != "ntag215":
            print("⚠️ Tag may not be an NTAG215. Protection check may not be accurate.")
        
        # Check if the tag is read-only
        is_read_only = reader.is_tag_read_only()
        if is_read_only:
            print("🔒 Tag appears to be READ-ONLY or write-protected")
        else:
            print("✅ Tag appears to be WRITABLE")
        
        # Read static lock bytes (pages 2-3)
        try:
            lock_data = read_tag_data(0)  # Block 0 contains pages 0-3
            # Lock bytes are at the end of page 2 and beginning of page 3
            lock_bytes = lock_data[10:12]
            print(f"\nStatic Lock Bytes: {lock_bytes.hex()}")
            
            if lock_bytes[0] != 0 or lock_bytes[1] != 0:
                print("🔒 Static lock bytes are set - some pages may be locked")
                # Detailed lock bit analysis could be added here
            else:
                print("✅ No static lock bits are set")
                
        except Exception as e:
            print(f"❌ Error reading lock bytes: {str(e)}")
        
        # Read dynamic lock bytes (page 130)
        try:
            # Block 32 contains pages 128-131
            config_data = read_tag_data(32)
            # Dynamic lock bytes are in page 130 (3rd page in the block)
            dynamic_lock = config_data[8:12]
            print(f"\nDynamic Lock Bytes: {dynamic_lock.hex()}")
            
            if any(b != 0 for b in dynamic_lock):
                print("🔒 Dynamic lock bytes are set - some pages may be locked")
                # Detailed lock bit analysis could be added here
            else:
                print("✅ No dynamic lock bits are set")
                
        except Exception as e:
            print(f"❌ Error reading dynamic lock bytes: {str(e)}")
        
        # Check for password protection (pages 133-134)
        try:
            # Page 133 is in block 33 (beyond normal range)
            # Create a direct reader instance to access it
            auth_data = None
            try:
                start_page = 133
                # Use reader's page-level methods to directly access
                # the configuration pages
                auth_data = reader._pn532.ntag2xx_read_block(133)
                print(f"\nPassword Protection: {auth_data.hex() if auth_data else 'None'}")
                
                if auth_data and auth_data[0] != 0:
                    print("🔒 Password protection appears to be enabled")
                else:
                    print("✅ No password protection detected")
            except Exception as e:
                print(f"👉 Password protection status: Could not determine ({str(e)})")
                
        except Exception as e:
            print(f"❌ Error checking password protection: {str(e)}")
            
    except Exception as e:
        print(f"❌ Error during protection check: {str(e)}")
    finally:
        try:
            if reader:
                reader.disconnect()
        except:
            pass
        shutdown()
        print("\n✅ NFC controller shut down")

def main():
    parser = argparse.ArgumentParser(description='NTAG215 Tag Utility Script')
    parser.add_argument('-b', '--bus', type=int, default=1, help='I2C bus number (default: 1)')
    parser.add_argument('-a', '--address', type=int, default=0x24, help='I2C device address (default: 0x24)')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Read command
    read_parser = subparsers.add_parser('read', help='Read tag data')
    
    # Write command
    write_parser = subparsers.add_parser('write', help='Write text to tag')
    write_parser.add_argument('text', type=str, help='Text to write to the tag')
    write_parser.add_argument('-b', '--block', type=int, default=1, 
                             help='Block number to write to (default: 1, which is pages 4-7)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Check tag protection status')
    
    args = parser.parse_args()
    
    if args.command == 'read':
        read_full_tag(args.bus, args.address)
    elif args.command == 'write':
        write_text_to_tag(args.text, args.block, args.bus, args.address)
    elif args.command == 'status':
        check_protection_status(args.bus, args.address)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
