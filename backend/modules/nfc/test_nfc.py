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
    # read_ndef_data = nfc_controller.read_ndef_data # Removed
    # write_ndef_data = nfc_controller.write_ndef_data # Removed
    write_ndef_uri = nfc_controller.write_ndef_uri # Added
    continuous_poll = nfc_controller.continuous_poll
    NFCError = exceptions.NFCError
    NFCNoTagError = exceptions.NFCNoTagError
    NFCReadError = exceptions.NFCReadError # Keep this
    NFCWriteError = exceptions.NFCWriteError # Keep this
    NFCTagNotWritableError = exceptions.NFCTagNotWritableError # Added
    
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
        # read_ndef_data = nfc_controller.read_ndef_data # Removed
        # write_ndef_data = nfc_controller.write_ndef_data # Removed
        write_ndef_uri = nfc_controller.write_ndef_uri # Added
        continuous_poll = nfc_controller.continuous_poll
        NFCError = exceptions.NFCError
        NFCNoTagError = exceptions.NFCNoTagError
        NFCReadError = exceptions.NFCReadError # Keep this
        NFCWriteError = exceptions.NFCWriteError # Keep this
        NFCTagNotWritableError = exceptions.NFCTagNotWritableError # Added
        
        logger.info("Successfully imported NFC module with direct imports")
    except ImportError as e:
        logger.error(f"Failed to import NFC module: {e}")
        print("\n========== ERROR ==========")
        print("Failed to import the NFC module components. Make sure:")
        print("  1. You have installed the required dependencies:")
        print("     sudo apt-get install python3-pip python3-smbus i2c-tools libgpiod2")
        print("     sudo pip3 install adafruit-circuitpython-pn532 adafruit-blinka RPi.GPIO")
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
            uid, ndef_info = poll_for_tag() # Updated return format
            if uid:
                print(f"✅ Tag detected! UID: {uid}")
                if ndef_info:
                    print(f"  NDEF Info: {ndef_info}") # ndef_info is now the decoded dict
                else:
                    print("  No NDEF URI found.")
                detected = True
                # Exit after detection (or continue polling if desired)
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
        uid, initial_ndef_info = None, None # Use different var name
        print("Waiting for tag (up to 5 seconds)...")
        for _ in range(50):  # Try for ~5 seconds
            uid, initial_ndef_info = poll_for_tag() # Updated return format
            if uid:
                print(f"✅ Tag detected! UID: {uid}")
                if initial_ndef_info:
                    print(f"  Initial NDEF Info: {initial_ndef_info}")
                else:
                    print("  No initial NDEF URI found.")
                break
            time.sleep(0.1)
        
        if not uid:
            print("❌ No tag detected within 5 seconds")
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
            print(f"\nWriting test data to block {block}...")
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            test_data = f"TEST {timestamp}".encode('utf-8').ljust(16, b'\x00')
            
            success = write_tag_data(test_data, block, verify=True) # Ensure verify is True
            if not success:
                # write_tag_data should raise on failure after retries
                print("❌ Failed to write test data (write_tag_data returned False unexpectedly)")
                shutdown()
                return False
                
            print(f"✅ Wrote test data: {test_data.hex()}")
        except NFCNoTagError:
            print("❌ Tag was removed before writing")
            shutdown()
            return False
        except NFCTagNotWritableError as e:
             print(f"❌ Tag not writable: {str(e)}")
             # Don't try to restore if tag isn't writable
             shutdown()
             return False # Test technically failed as write wasn't possible
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
            # Still attempt shutdown even if restore fails
        
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


def test_ndef_uri_read_write(i2c_bus=1, i2c_address=0x24): # Renamed function
    """Test reading and writing NDEF URI records."""
    print("\n=== Testing NDEF URI Read/Write ===")
    print("Please place a WRITABLE NDEF-compatible tag (e.g., NTAG215) on the reader...")
    
    try:
        # Initialize NFC controller
        if not initialize(i2c_bus, i2c_address):
            print("❌ Failed to initialize NFC controller")
            return False
        
        # Wait for tag and get initial NDEF info
        uid, initial_ndef_info = None, None
        print("Waiting for tag (up to 5 seconds)...")
        for _ in range(50):
            uid, initial_ndef_info = poll_for_tag()
            if uid:
                print(f"✅ Tag detected! UID: {uid}")
                if initial_ndef_info:
                    print(f"  Initial NDEF Info: {initial_ndef_info}")
                else:
                    print("  No initial NDEF URI found.")
                break
            time.sleep(0.1)
        
        if not uid:
            print("❌ No tag detected within 5 seconds")
            shutdown()
            return False
        
        # Write test NDEF URI
        test_url = f"https://music.youtube.com/watch?v=test_{datetime.now().strftime('%H%M%S')}"
        write_success = False
        try:
            print(f"\nAttempting to write NDEF URI: {test_url}")
            write_success = write_ndef_uri(test_url)
            if write_success:
                print(f"✅ Successfully wrote NDEF URI.")
            else:
                # write_ndef_uri should raise an exception on failure
                print("❌ Failed to write NDEF URI (write_ndef_uri returned False unexpectedly)")
                
        except NFCNoTagError:
            print("❌ Tag was removed before/during writing")
            shutdown()
            return False
        except NFCTagNotWritableError as e:
             print(f"❌ Tag not writable: {str(e)}")
             print("   Skipping verification. Ensure you are using a writable tag.")
             # Test didn't strictly fail, but couldn't complete verification
             shutdown()
             return False # Indicate test couldn't fully complete
        except Exception as e:
            print(f"❌ Error writing NDEF URI: {str(e)}")
            shutdown()
            return False

        # If write failed due to non-writable tag, we already returned False
        if not write_success:
             shutdown()
             return False

        # Read back to verify
        try:
            print("\nReading back NDEF data for verification (waiting 2 seconds)...")
            time.sleep(2) # Give tag/reader time to settle after write
            
            # Poll again to get the latest NDEF data
            # Need to handle potential tag removal between write and read
            read_uid, read_ndef_info = None, None
            for _ in range(10): # Try for 1 second
                 read_uid, read_ndef_info = poll_for_tag()
                 if read_uid == uid: # Make sure it's the same tag
                      break
                 time.sleep(0.1)

            if read_uid != uid:
                 print("❌ Tag removed or different tag detected before verification.")
                 shutdown()
                 return False

            if not read_ndef_info:
                print("❌ No NDEF data could be read back after writing.")
                # Try reading raw blocks for debugging
                try:
                    print("Raw data block 4:", read_tag_data(4).hex()) # Use existing read_tag_data
                    print("Raw data block 5:", read_tag_data(5).hex())
                except Exception as raw_e:
                     print(f"Could not read raw blocks: {raw_e}")
                shutdown()
                return False
                
            print(f"✅ Read back NDEF Info: {read_ndef_info}")
            
            # Check if our URL is in there
            verified_url = read_ndef_info.get('uri')
            
            if verified_url == test_url:
                print("\n✅ Successfully verified NDEF URL data!")
            else:
                print("\n❌ Could not verify NDEF URL data")
                print(f"  Expected URL: {test_url}")
                print(f"  Found URL:    {verified_url}")
                # Show raw data for deeper debugging
                print(f"\nRaw NDEF data from tag (first 64 bytes, hex):")
                try:
                    raw_data = read_tag_data(4) + read_tag_data(5) + read_tag_data(6) + read_tag_data(7)
                    print(f"Blocks 4-7: {raw_data.hex()}")
                except Exception as e:
                     print(f"Could not read raw blocks 4-7: {e}")

        except NFCNoTagError:
            print("❌ Tag was removed before verification")
            shutdown()
            return False
        except Exception as e:
            print(f"❌ Error during NDEF verification: {str(e)}")
            shutdown()
            return False
        
        # Shutdown to clean up
        shutdown()
        print("\n✅ NDEF URI Read/Write test completed.")
        
        return verified_url == test_url # Return True only if verification passed
        
    except Exception as e:
        print(f"❌ Error during NDEF URI test: {str(e)}")
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
            
        # Tag detection callback for continuous poll
        detected_tags = {} # Store detected UIDs and their NDEF info
        def tag_callback(uid, ndef_info): # Callback receives tuple now
            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
            ndef_uri = ndef_info.get('uri', 'None') if ndef_info else 'None'
            
            if uid not in detected_tags or detected_tags[uid] != ndef_uri:
                 print(f"✅ [Callback] Tag Event: UID={uid} | NDEF URI='{ndef_uri}' at {timestamp}")
                 detected_tags[uid] = ndef_uri # Store last seen NDEF URI for this UID
            
        # Set up exit event for the continuous poll
        exit_event = threading.Event()
        
        # Define the polling loop function to pass to the thread
        def poll_loop():
            last_uid = None
            logger.info(f"Continuous polling thread started with interval 0.1s")
            while not exit_event.is_set():
                try:
                    # Poll returns tuple (uid, ndef_info)
                    uid, ndef_info = poll_for_tag() 
                    
                    # If tag detected
                    if uid:
                        # Call callback only if UID is new or NDEF has changed
                        # (Callback now handles printing logic)
                        try:
                            callback(uid, ndef_info) 
                        except Exception as cb_e:
                            logger.error(f"Error in tag detection callback: {str(cb_e)}")
                        last_uid = uid # Keep track of last seen UID
                    # If no tag detected, reset last UID
                    elif last_uid: # Only log removal once
                         logger.debug("Tag removed.")
                         if last_uid in detected_tags:
                              del detected_tags[last_uid] # Clear state for removed tag
                         last_uid = None
                         
                    # Wait for next poll
                    time.sleep(0.1) # Use the interval defined in continuous_poll
                    
                except Exception as poll_e:
                    logger.error(f"Error during continuous polling loop: {str(poll_e)}")
                    # Avoid busy-looping on error
                    time.sleep(0.5)
            logger.info("Continuous polling thread finished.")

        
        # Start continuous polling in a separate thread
        # Pass the loop function, not continuous_poll itself
        poll_thread = threading.Thread(target=poll_loop) 
        poll_thread.daemon = True # Allow exiting even if thread is running
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
    # Args parsing is done at the top now
    
    # Convert address from decimal to hex if needed
    i2c_address = args.address # Use args parsed at the top
    
    # Logging setup is done at the top now
    
    # Print test configuration using args parsed at the top
    print("===========================================")
    print("          NFC Module Test Script          ")
    print("===========================================")
    print(f"I2C Bus: {args.bus}")
    print(f"I2C Address: 0x{i2c_address:02X}") # Use i2c_address var
    print(f"Test: {args.test}")
    print(f"Duration: {args.duration} seconds")
    print(f"Log Level: {logging.getLevelName(logger.getEffectiveLevel())}")
    print("===========================================")
    
    # Run the selected test(s)
    if args.test == 'all' or args.test == 'hardware':
        test_hardware_connection(args.bus, i2c_address)
    
    if args.test == 'all' or args.test == 'detect':
        test_tag_detection(args.bus, i2c_address, args.duration)
    
    if args.test == 'all' or args.test == 'readwrite':
        test_read_write(args.bus, i2c_address)
    
    if args.test == 'all' or args.test == 'ndef_uri': # Renamed test
        test_ndef_uri_read_write(args.bus, i2c_address) # Renamed function call
    
    if args.test == 'all' or args.test == 'poll':
        test_continuous_poll(args.bus, i2c_address, args.duration)
    
    print("\n===========================================")
    print("          Test Script Completed           ")
    print("===========================================")

if __name__ == "__main__":
    main()
