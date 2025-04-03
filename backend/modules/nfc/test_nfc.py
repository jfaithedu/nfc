#!/usr/bin/env python3
"""
test_nfc.py - Test script for the NFC module.

This script allows testing the NFC hardware and module functionality.
"""

import os
import sys
import time
import threading
import logging
import argparse
from datetime import datetime

# Parse command line arguments first to set up logging
parser = argparse.ArgumentParser(description="Test NFC hardware and module functionality")
parser.add_argument('-b', '--bus', type=int, default=1, help="I2C bus number (default: 1)")
parser.add_argument('-a', '--address', type=int, default=0x24, help="I2C device address (default: 0x24)")
parser.add_argument('-t', '--test', type=str, default='all', 
                    choices=['hardware', 'detect', 'readwrite', 'ndef', 'poll', 'all'],
                    help="Test to run (default: all)")
parser.add_argument('-d', '--duration', type=int, default=10, help="Duration in seconds for polling tests (default: 10)")
parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose debugging output")
parser.add_argument('--debug', action='store_true', help="Enable debug level logging")
args = parser.parse_args()

# Setup logging based on arguments
log_level = logging.DEBUG if args.debug or args.verbose else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NFCTest")

# Enable verbose mode if requested
if args.verbose:
    # Set all loggers to DEBUG level
    for name in logging.root.manager.loggerDict:
        if name.startswith('backend.modules.nfc'):
            logging.getLogger(name).setLevel(logging.DEBUG)
    logger.debug("Verbose debugging enabled")

# Ensure we can import our module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# Add the parent directory to sys.path to ensure proper importing
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Try to import the modules with absolute imports first
try:
    from backend.modules.nfc import nfc_controller
    from backend.modules.nfc import hardware_interface
    from backend.modules.nfc import tag_processor
    from backend.modules.nfc import exceptions
    
    # Import the specific functions and classes we need
    initialize = nfc_controller.initialize
    shutdown = nfc_controller.shutdown
    poll_for_tag = nfc_controller.poll_for_tag
    read_tag_data = nfc_controller.read_tag_data
    write_tag_data = nfc_controller.write_tag_data
    get_hardware_info = nfc_controller.get_hardware_info
    authenticate_tag = nfc_controller.authenticate_tag
    read_ndef_data = nfc_controller.read_ndef_data
    write_ndef_data = nfc_controller.write_ndef_data
    continuous_poll = nfc_controller.continuous_poll
    NFCError = exceptions.NFCError
    NFCNoTagError = exceptions.NFCNoTagError
    
    logger.info("Successfully imported NFC module with absolute imports")
except ImportError:
    # Fallback to direct imports if the package structure doesn't match
    try:
        # Add the current directory to the path for direct imports
        sys.path.insert(0, current_dir)
        
        import nfc_controller
        import hardware_interface
        import tag_processor
        import exceptions
        
        # Now import the specific functions and classes we need
        initialize = nfc_controller.initialize
        shutdown = nfc_controller.shutdown
        poll_for_tag = nfc_controller.poll_for_tag
        read_tag_data = nfc_controller.read_tag_data
        write_tag_data = nfc_controller.write_tag_data
        get_hardware_info = nfc_controller.get_hardware_info
        authenticate_tag = nfc_controller.authenticate_tag
        read_ndef_data = nfc_controller.read_ndef_data
        write_ndef_data = nfc_controller.write_ndef_data
        continuous_poll = nfc_controller.continuous_poll
        NFCError = exceptions.NFCError
        NFCNoTagError = exceptions.NFCNoTagError
        
        logger.info("Successfully imported NFC module with direct imports")
    except ImportError as e:
        logger.error(f"Failed to import NFC module: {e}")
        print("\n========== ERROR ==========")
        print("Failed to import the NFC module components. Make sure:")
        print("  1. You have installed the required dependencies:")
        print("     sudo apt-get install python3-pip python3-smbus i2c-tools")
        print("     sudo pip3 install smbus2")
        print("  2. All module files are in the correct directory:")
        print(f"     {current_dir}")
        print("  3. You have proper permissions for I2C devices")
        print("     (user should be in the i2c group)")
        print("  4. If running the script directly, try activating the virtual environment:")
        print(f"     source {os.path.join(parent_dir, 'venv/bin/activate')}")
        print("     and run script as a module:")
        print("     python -m backend.modules.nfc.test_nfc")
        print("\nDetailed error:", str(e))
        print("===========================\n")
        sys.exit(1)

def test_hardware_connection(i2c_bus=1, i2c_address=0x24):
    """Test connecting to the NFC hardware."""
    print("\n=== Testing Hardware Connection ===")
    
    try:
        # Initialize NFC controller
        success = initialize(i2c_bus, i2c_address)
        if not success:
            print("❌ Failed to initialize NFC controller")
            return False
        
        print("✅ NFC controller initialized successfully")
        
        # Get hardware info
        info = get_hardware_info()
        if not info:
            print("❌ Failed to get hardware info")
            return False
        
        print("✅ Hardware Info:")
        for key, value in info.items():
            print(f"  - {key}: {value}")
        
        # Shutdown to clean up
        shutdown()
        print("✅ NFC controller shut down")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during hardware test: {str(e)}")
        try:
            shutdown()
        except:
            pass
        return False

def test_tag_detection(i2c_bus=1, i2c_address=0x24, poll_time=10):
    """Test detecting NFC tags by polling for a set period."""
    print("\n=== Testing Tag Detection ===")
    print(f"Polling for NFC tags for {poll_time} seconds...")
    print("Please place a tag on the reader...")
    
    try:
        # Initialize NFC controller
        if not initialize(i2c_bus, i2c_address):
            print("❌ Failed to initialize NFC controller")
            return False
        
        # Poll for tag for specified time
        start_time = time.time()
        detected = False
        
        while time.time() - start_time < poll_time:
            uid = poll_for_tag()
            if uid:
                print(f"✅ Tag detected! UID: {uid}")
                detected = True
                # Exit after detection
                break
            
            # Sleep between polls
            time.sleep(0.1)
        
        if not detected:
            print("❌ No tag detected within the polling time")
        
        # Shutdown to clean up
        shutdown()
        print("✅ NFC controller shut down")
        
        return detected
        
    except Exception as e:
        print(f"❌ Error during tag detection test: {str(e)}")
        try:
            shutdown()
        except:
            pass
        return False

def test_read_write(i2c_bus=1, i2c_address=0x24, block=4):
    """Test reading and writing data to a tag block."""
    print("\n=== Testing Tag Read/Write ===")
    print("Please place a tag on the reader...")
    
    try:
        # Initialize NFC controller
        if not initialize(i2c_bus, i2c_address):
            print("❌ Failed to initialize NFC controller")
            return False
        
        # Wait for tag
        uid = None
        for _ in range(50):  # Try for ~5 seconds
            uid = poll_for_tag()
            if uid:
                print(f"✅ Tag detected! UID: {uid}")
                break
            time.sleep(0.1)
        
        if not uid:
            print("❌ No tag detected")
            shutdown()
            return False
        
        # Read initial data
        try:
            print(f"Reading data from block {block}...")
            initial_data = read_tag_data(block)
            print(f"✅ Initial data: {initial_data.hex()}")
        except NFCNoTagError:
            print("❌ Tag was removed before reading")
            shutdown()
            return False
        except Exception as e:
            print(f"❌ Error reading initial data: {str(e)}")
            shutdown()
            return False
        
        # Write test data
        try:
            print(f"Writing test data to block {block}...")
            timestamp = datetime.now().strftime("%H:%M:%S")
            test_data = f"TEST {timestamp}".encode('utf-8').ljust(16, b'\x00')
            
            success = write_tag_data(test_data, block)
            if not success:
                print("❌ Failed to write test data")
                shutdown()
                return False
                
            print(f"✅ Wrote test data: {test_data.hex()}")
        except NFCNoTagError:
            print("❌ Tag was removed before writing")
            shutdown()
            return False
        except Exception as e:
            print(f"❌ Error writing test data: {str(e)}")
            shutdown()
            return False
        
        # Read back the data to verify
        try:
            print("Reading back the data...")
            read_data = read_tag_data(block)
            print(f"✅ Read back data: {read_data.hex()}")
            
            if read_data == test_data:
                print("✅ Read data matches what was written!")
            else:
                print("❌ Read data does not match what was written")
                print(f"  Expected: {test_data.hex()}")
                print(f"  Got: {read_data.hex()}")
        except NFCNoTagError:
            print("❌ Tag was removed before verification")
            shutdown()
            return False
        except Exception as e:
            print(f"❌ Error during verification: {str(e)}")
            shutdown()
            return False
        
        # Write back the original data to be nice
        try:
            print("Restoring original data...")
            write_tag_data(initial_data, block)
            print("✅ Original data restored")
        except Exception as e:
            print(f"⚠️ Could not restore original data: {str(e)}")
        
        # Shutdown to clean up
        shutdown()
        print("✅ NFC controller shut down")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during read/write test: {str(e)}")
        try:
            shutdown()
        except:
            pass
        return False

def test_ndef_data(i2c_bus=1, i2c_address=0x24):
    """Test reading and writing NDEF formatted data."""
    print("\n=== Testing NDEF Data Read/Write ===")
    print("Please place a tag on the reader...")
    
    try:
        # Initialize NFC controller
        if not initialize(i2c_bus, i2c_address):
            print("❌ Failed to initialize NFC controller")
            return False
        
        # Wait for tag
        uid = None
        for _ in range(50):  # Try for ~5 seconds
            uid = poll_for_tag()
            if uid:
                print(f"✅ Tag detected! UID: {uid}")
                break
            time.sleep(0.1)
        
        if not uid:
            print("❌ No tag detected")
            shutdown()
            return False
        
        # First, read any existing NDEF data
        try:
            print("Reading current NDEF data...")
            current_ndef = read_ndef_data()
            if current_ndef:
                print("✅ Current NDEF data:", current_ndef)
            else:
                print("ℹ️ No valid NDEF data found on tag")
        except Exception as e:
            print(f"ℹ️ Error reading current NDEF data: {str(e)}")
            print("Continuing with test...")
        
        # Write test NDEF data
        try:
            print("Writing test NDEF text record...")
            text = f"NFC Test {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            success = write_ndef_data(text=text)
            if not success:
                print("❌ Failed to write NDEF data")
                shutdown()
                return False
                
            print(f"✅ Wrote NDEF text: '{text}'")
        except NFCNoTagError:
            print("❌ Tag was removed before writing")
            shutdown()
            return False
        except Exception as e:
            print(f"❌ Error writing NDEF data: {str(e)}")
            shutdown()
            return False
        
        # Read back to verify
        try:
            print("Reading back NDEF data...")
            read_ndef = read_ndef_data()
            
            if not read_ndef:
                print("❌ No NDEF data could be read back")
                shutdown()
                return False
                
            print("✅ Read back NDEF data:", read_ndef)
            
            # Check if our text is in there
            found_text = False
            for record in read_ndef.get('records', []):
                if 'decoded' in record and record['decoded'].get('type') == 'text':
                    if record['decoded'].get('text') == text:
                        found_text = True
                        break
            
            if found_text:
                print("✅ Successfully verified NDEF text data!")
            else:
                print("❌ Could not verify NDEF text data")
        except NFCNoTagError:
            print("❌ Tag was removed before verification")
            shutdown()
            return False
        except Exception as e:
            print(f"❌ Error during NDEF verification: {str(e)}")
            shutdown()
            return False
        
        # Now test with URL
        try:
            print("\nWriting test NDEF URL record...")
            url = "https://example.com/nfc-test"
            success = write_ndef_data(url=url)
            if not success:
                print("❌ Failed to write NDEF URL")
                shutdown()
                return False
                
            print(f"✅ Wrote NDEF URL: '{url}'")
            
            # Read back to verify
            print("Reading back NDEF URL data...")
            read_ndef = read_ndef_data()
            
            if not read_ndef:
                print("❌ No NDEF URL data could be read back")
                shutdown()
                return False
                
            print("✅ Read back NDEF URL data:", read_ndef)
            
            # Check if our URL is in there
            found_url = False
            for record in read_ndef.get('records', []):
                if 'decoded' in record and record['decoded'].get('type') == 'uri':
                    if record['decoded'].get('uri') == url:
                        found_url = True
                        break
            
            if found_url:
                print("✅ Successfully verified NDEF URL data!")
            else:
                print("❌ Could not verify NDEF URL data")
        except Exception as e:
            print(f"❌ Error during NDEF URL test: {str(e)}")
        
        # Shutdown to clean up
        shutdown()
        print("✅ NFC controller shut down")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during NDEF test: {str(e)}")
        try:
            shutdown()
        except:
            pass
        return False

def test_continuous_poll(i2c_bus=1, i2c_address=0x24, duration=10):
    """Test continuous polling functionality."""
    print("\n=== Testing Continuous Polling ===")
    print(f"Running continuous poll for {duration} seconds...")
    print("Please touch and remove tag multiple times...")
    
    try:
        # Initialize NFC controller
        if not initialize(i2c_bus, i2c_address):
            print("❌ Failed to initialize NFC controller")
            return False
            
        # Tag detection callback
        def tag_callback(uid):
            print(f"✅ [Callback] Tag detected: {uid} at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
            
        # Set up exit event for the continuous poll
        exit_event = threading.Event()
        
        # Start continuous polling in a separate thread
        poll_thread = threading.Thread(
            target=continuous_poll,
            args=(tag_callback, 0.1, exit_event)
        )
        poll_thread.daemon = True
        poll_thread.start()
        
        # Run for specified duration
        print(f"Continuous polling started. Running for {duration} seconds...")
        time.sleep(duration)
        
        # Stop polling
        exit_event.set()
        poll_thread.join(timeout=2)
        
        print("Continuous polling completed.")
        
        # Shutdown to clean up
        shutdown()
        print("✅ NFC controller shut down")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during continuous polling test: {str(e)}")
        try:
            shutdown()
        except:
            pass
        return False

def main():
    """Main function to run the tests."""
    parser = argparse.ArgumentParser(description='Test the NFC module functionality')
    parser.add_argument('-b', '--bus', type=int, default=1, help='I2C bus number (default: 1)')
    parser.add_argument('-a', '--address', type=int, default=0x24, help='I2C device address (default: 0x24)', 
                        metavar='ADDR')
    parser.add_argument('-t', '--test', type=str, choices=['all', 'hardware', 'detect', 'readwrite', 'ndef', 'poll'], 
                        default='all', help='Test to run (default: all)')
    parser.add_argument('-d', '--duration', type=int, default=10, 
                        help='Duration in seconds for polling tests (default: 10)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Convert address from decimal to hex if needed
    i2c_address = args.address
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        print("Verbose logging enabled")
    
    print("===========================================")
    print("          NFC Module Test Script          ")
    print("===========================================")
    print(f"I2C Bus: {args.bus}")
    print(f"I2C Address: 0x{i2c_address:02X}")
    print(f"Test: {args.test}")
    print(f"Duration: {args.duration} seconds")
    print("===========================================")
    
    # Run the selected test(s)
    if args.test == 'all' or args.test == 'hardware':
        test_hardware_connection(args.bus, i2c_address)
    
    if args.test == 'all' or args.test == 'detect':
        test_tag_detection(args.bus, i2c_address, args.duration)
    
    if args.test == 'all' or args.test == 'readwrite':
        test_read_write(args.bus, i2c_address)
    
    if args.test == 'all' or args.test == 'ndef':
        test_ndef_data(args.bus, i2c_address)
    
    if args.test == 'all' or args.test == 'poll':
        test_continuous_poll(args.bus, i2c_address, args.duration)
    
    print("\n===========================================")
    print("          Test Script Completed           ")
    print("===========================================")

if __name__ == "__main__":
    main()
