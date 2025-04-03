"""
nfc_controller.py - Main NFC controller interface for other application modules.
"""

import logging
import threading
import time
from .hardware_interface import NFCReader
from .tag_processor import format_uid, parse_ndef_data, create_ndef_data
from .exceptions import NFCError, NFCNoTagError, NFCReadError, NFCWriteError, NFCHardwareError

# Create logger
logger = logging.getLogger(__name__)

# Global instance for singleton pattern
_nfc_reader = None
_reader_lock = threading.Lock()

def initialize(i2c_bus=1, i2c_address=0x24):
    """
    Initialize the NFC controller and hardware.
    
    Args:
        i2c_bus (int): I2C bus number (usually 1 on Raspberry Pi)
        i2c_address (int): I2C device address of the NFC HAT
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global _nfc_reader
    
    with _reader_lock:
        try:
            # If already initialized, disconnect first
            if _nfc_reader is not None:
                _nfc_reader.disconnect()
            
            # Create new reader instance
            _nfc_reader = NFCReader(i2c_bus, i2c_address)
            
            # Connect to hardware
            if not _nfc_reader.connect():
                logger.error("Failed to connect to NFC hardware")
                _nfc_reader = None
                return False
            
            # Perform a reset to ensure clean state
            _nfc_reader.reset()
            
            logger.info("NFC controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during NFC initialization: {str(e)}")
            if _nfc_reader:
                try:
                    _nfc_reader.disconnect()
                except:
                    pass
                _nfc_reader = None
            return False

def shutdown():
    """
    Clean shutdown of NFC hardware.
    """
    global _nfc_reader
    
    with _reader_lock:
        if _nfc_reader:
            try:
                _nfc_reader.disconnect()
                logger.info("NFC controller shut down successfully")
            except Exception as e:
                logger.error(f"Error during NFC shutdown: {str(e)}")
            finally:
                _nfc_reader = None

def poll_for_tag(read_ndef=False):
    """
    Check for presence of an NFC tag and optionally read NDEF data.
    
    Args:
        read_ndef (bool): Whether to attempt to read NDEF data from the tag
    
    Returns:
        tuple or str or None: 
            - If read_ndef=True and successful: (uid_str, ndef_data)
            - If read_ndef=True but no NDEF data: (uid_str, None)
            - If read_ndef=False: uid_str if tag found, None otherwise
    """
    global _nfc_reader
    
    with _reader_lock:
        if not _nfc_reader:
            logger.error("NFC controller not initialized")
            return None
        
        try:
            # Poll for tag
            raw_uid = _nfc_reader.poll()
            
            # Return None if no tag found
            if not raw_uid:
                return None
            
            # Format UID
            uid = format_uid(raw_uid)
            logger.debug(f"NFC tag detected: {uid}")
            
            # If we don't need to read NDEF data, just return the UID
            if not read_ndef:
                return uid
            
            # Attempt to read NDEF data from the tag
            ndef_data = None
            try:
                ndef_data = _read_ndef_data_internal()
                if ndef_data:
                    logger.debug(f"Read NDEF data during polling: {len(ndef_data['records'])} records")
            except Exception as e:
                logger.debug(f"Unable to read NDEF data during polling: {str(e)}")
            
            # Return tuple of UID and NDEF data (which may be None)
            return (uid, ndef_data)
            
        except Exception as e:
            logger.error(f"Error polling for NFC tag: {str(e)}")
            return None

def read_tag_data(block=4):
    """
    Read data from a specific block on the currently present tag.
    
    Args:
        block (int): Block number to read from
    
    Returns:
        bytes: Data read from the tag
    
    Raises:
        NFCReadError: If reading fails
        NFCNoTagError: If no tag is present
    """
    global _nfc_reader
    
    with _reader_lock:
        if not _nfc_reader:
            error_msg = "NFC controller not initialized"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)
        
        try:
            # Read block data
            data = _nfc_reader.read_block(block)
            logger.debug(f"Data read from block {block}: {data.hex()}")
            return data
            
        except NFCNoTagError:
            # Re-raise no tag error
            logger.warning("No tag present when trying to read")
            raise
        except Exception as e:
            error_msg = f"Error reading tag data from block {block}: {str(e)}"
            logger.error(error_msg)
            raise NFCReadError(error_msg)

def write_tag_data(data, block=4, verify=True, max_retries=3):
    """
    Write data to a specific block on the currently present tag.
    
    Args:
        data (bytes): Data to write (must be 16 bytes or less)
        block (int): Block number to write to
        verify (bool): Whether to verify the data was written correctly
        max_retries (int): Maximum number of retry attempts if verification fails
    
    Returns:
        bool: True if write successful
    
    Raises:
        NFCWriteError: If writing fails
        NFCNoTagError: If no tag is present
    """
    global _nfc_reader
    
    with _reader_lock:
        if not _nfc_reader:
            error_msg = "NFC controller not initialized"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)
        
        # Ensure data is bytes
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Validate data length
        if len(data) > 16:
            error_msg = f"Data too long ({len(data)} bytes). Maximum is 16 bytes per block."
            logger.error(error_msg)
            raise NFCWriteError(error_msg)
        
        # Pad data to 16 bytes if needed
        if len(data) < 16:
            data = data.ljust(16, b'\x00')
        
        retry_count = 0
        
        try:
            while retry_count <= max_retries:
                try:
                    # Write data to tag
                    success = _nfc_reader.write_block(block, data)
                    
                    if not success:
                        raise NFCWriteError(f"Failed to write data to block {block}")
                    
                    # If verification is requested, read back the data and compare
                    if verify:
                        # Small delay to ensure write is complete
                        time.sleep(0.05)
                        
                        # Read back the data
                        read_data = _nfc_reader.read_block(block)
                        
                        # Compare the data
                        if read_data != data:
                            logger.warning(f"Verification failed for block {block}. Retry {retry_count+1}/{max_retries}")
                            logger.warning(f"Expected: {data.hex()}, Got: {read_data.hex()}")
                            
                            # If we've reached max retries, raise an error
                            if retry_count >= max_retries:
                                error_msg = f"Data verification failed after {max_retries} attempts"
                                logger.error(error_msg)
                                raise NFCWriteError(error_msg)
                            
                            # Otherwise, retry
                            retry_count += 1
                            continue
                    
                    logger.info(f"Successfully wrote data to block {block}")
                    return True
                        
                except NFCNoTagError:
                    # Re-raise no tag error immediately
                    logger.warning("No tag present when trying to write")
                    raise
                except NFCWriteError as e:
                    # Re-raise write errors if it's the last retry
                    if retry_count >= max_retries:
                        raise
                    logger.warning(f"Write error, retrying ({retry_count+1}/{max_retries}): {str(e)}")
                    retry_count += 1
                except Exception as e:
                    error_msg = f"Error writing tag data to block {block}: {str(e)}"
                    logger.error(error_msg)
                    
                    # If we've reached max retries, raise an error
                    if retry_count >= max_retries:
                        raise NFCWriteError(error_msg)
                    
                    retry_count += 1
            
            # If we exit the loop without returning, we've exhausted all retries
            raise NFCWriteError(f"Failed to write data to block {block} after {max_retries} attempts")
                
        except NFCNoTagError:
            # Re-raise no tag error
            raise
        except NFCWriteError:
            # Re-raise write errors
            raise
        except Exception as e:
            error_msg = f"Error writing tag data to block {block}: {str(e)}"
            logger.error(error_msg)
            raise NFCWriteError(error_msg)

def get_hardware_info():
    """
    Get information about the NFC hardware.
    
    Returns:
        dict: Hardware information including model, firmware version
    """
    global _nfc_reader
    
    with _reader_lock:
        if not _nfc_reader:
            logger.error("NFC controller not initialized")
            return None
        
        try:
            # Get firmware version
            version = _nfc_reader.get_version()
            
            info = {
                "initialized": True,
                "connected": True,
                "i2c_bus": _nfc_reader.i2c_bus,
                "i2c_address": f"0x{_nfc_reader.i2c_address:02X}",
                "firmware_version": version or "Unknown"
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting hardware info: {str(e)}")
            return {
                "initialized": True,
                "connected": False,
                "error": str(e)
            }

def authenticate_tag(block, key_type='A', key=b'\xFF\xFF\xFF\xFF\xFF\xFF'):
    """
    Authenticate with a MIFARE tag before reading/writing protected blocks.
    
    Args:
        block (int): Block number to authenticate
        key_type (str): Type of key ('A' or 'B')
        key (bytes): 6-byte authentication key (default is the factory default)
        
    Returns:
        bool: True if authentication successful
        
    Raises:
        NFCAuthenticationError: If authentication fails
        NFCNoTagError: If no tag is present
    """
    global _nfc_reader
    
    with _reader_lock:
        if not _nfc_reader:
            error_msg = "NFC controller not initialized"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)
        
        try:
            # Authenticate with tag
            result = _nfc_reader.authenticate(block, key_type, key)
            if result:
                logger.info(f"Successfully authenticated for block {block}")
            return result
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise

def _read_ndef_data_internal():
    """
    Internal helper function to read NDEF data from a tag.
    This is used by poll_for_tag and read_ndef_data.
    
    Returns:
        dict: Parsed NDEF message and records or None if no valid NDEF data
        
    Raises:
        NFCReadError: If reading fails
        NFCNoTagError: If no tag is present
    """
    # NDEF data typically starts at block 4, but may span multiple blocks
    # Read first block to determine TLV length
    data = read_tag_data(4)
    
    # Check for TLV structure to determine total length
    if len(data) >= 2 and data[0] == 0x03:  # NDEF Message TLV
        # Check for 3-byte length format
        if data[1] == 0xFF and len(data) >= 4:
            tlv_length = int.from_bytes(data[2:4], byteorder='big')
            total_bytes_needed = tlv_length + 4  # TLV type + 3-byte length + payload
        else:
            tlv_length = data[1]
            total_bytes_needed = tlv_length + 2  # TLV type + length byte + payload
        
        # If data spans multiple blocks, read additional blocks
        if total_bytes_needed > 16:
            # Calculate how many additional blocks we need
            additional_blocks = (total_bytes_needed - 16 + 15) // 16  # Ceiling division
            
            # Read additional blocks and append data
            for i in range(1, additional_blocks + 1):
                try:
                    additional_data = read_tag_data(4 + i)
                    data += additional_data
                except Exception as block_e:
                    logger.warning(f"Could not read additional NDEF block {4+i}: {str(block_e)}")
                    break
                    
            logger.debug(f"Read {len(data)} bytes of NDEF data across {additional_blocks + 1} blocks")
    
    # Parse NDEF data
    ndef_data = parse_ndef_data(data)
    if not ndef_data:
        logger.debug("No valid NDEF data found on tag")
        return None
        
    return ndef_data

def read_ndef_data():
    """
    Read and parse NDEF formatted data from tag.
    
    Returns:
        dict: Parsed NDEF message and records
        
    Raises:
        NFCReadError: If reading fails
        NFCNoTagError: If no tag is present
    """
    try:
        ndef_data = _read_ndef_data_internal()
        if not ndef_data:
            logger.warning("No valid NDEF data found on tag")
        return ndef_data
    except Exception as e:
        logger.error(f"Error reading NDEF data: {str(e)}")
        raise

def write_ndef_uri(uri):
    """
    Write a URI record to an NFC tag. This is specialized for URLs like YouTube or Music links.
    
    Args:
        uri (str): The URI to write (e.g., 'https://youtube.com/watch?v=...')
        
    Returns:
        bool: True if successful
        
    Raises:
        NFCWriteError: If writing fails
        NFCNoTagError: If no tag is present
        NFCTagNotWritableError: If tag is read-only or incorrectly formatted
    """
    if not uri:
        raise ValueError("URI cannot be empty")
        
    # Validate URI format (basic check)
    if not (uri.startswith('http://') or uri.startswith('https://')):
        logger.warning(f"URI does not start with http:// or https://: {uri}")
    
    try:
        # Use the general NDEF writing function but specify only the URL
        return write_ndef_data(url=uri)
    except Exception as e:
        logger.error(f"Error writing URI to tag: {str(e)}")
        raise

def write_ndef_data(url=None, text=None):
    """
    Write NDEF formatted data to tag.
    
    Args:
        url (str, optional): URL to encode
        text (str, optional): Text to encode
        
    Returns:
        bool: True if successful
        
    Raises:
        NFCWriteError: If writing fails
        NFCNoTagError: If no tag is present
        NFCTagNotWritableError: If tag is read-only or incorrectly formatted
    """
    try:
        # Create NDEF formatted data
        ndef_data = create_ndef_data(url=url, text=text)
        
        # Write data to tag (NDEF typically starts at block 4)
        # We may need multiple blocks for longer data
        for i in range(0, len(ndef_data), 16):
            block_data = ndef_data[i:i+16]
            block_num = 4 + (i // 16)
            
            # Write block
            write_tag_data(block_data, block_num)
            
        logger.info("Successfully wrote NDEF data to tag")
        return True
        
    except Exception as e:
        logger.error(f"Error writing NDEF data: {str(e)}")
        raise

def continuous_poll(callback, interval=0.1, exit_event=None, read_ndef=False):
    """
    Continuously poll for NFC tags and call the callback function when detected.
    
    Args:
        callback (function): Function to call when tag is detected.
                             If read_ndef is False: Called with UID string parameter
                             If read_ndef is True: Called with (UID string, NDEF data) tuple
        interval (float): Polling interval in seconds
        exit_event (threading.Event, optional): Event to signal when to stop polling
        read_ndef (bool): Whether to read NDEF data from detected tags
        
    Note:
        This function runs in a loop and is typically called in a separate thread.
    """
    last_uid = None
    if exit_event is None:
        exit_event = threading.Event()
    
    logger.info(f"Starting continuous polling with interval {interval}s, read_ndef={read_ndef}")
    
    try:
        while not exit_event.is_set():
            try:
                # Poll for tag (with or without NDEF data)
                result = poll_for_tag(read_ndef=read_ndef)
                
                # If no tag detected
                if not result:
                    last_uid = None
                    time.sleep(interval)
                    continue
                
                # Extract UID (and possibly NDEF data) from result
                if read_ndef:
                    uid, ndef_data = result
                else:
                    uid = result
                    ndef_data = None
                
                # If tag detected and it's different from last time
                if uid and uid != last_uid:
                    # Call callback with appropriate parameters
                    try:
                        if read_ndef:
                            callback(uid, ndef_data)
                        else:
                            callback(uid)
                    except Exception as e:
                        logger.error(f"Error in tag detection callback: {str(e)}")
                    
                    # Update last seen UID
                    last_uid = uid
                
                # Wait for next poll
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error during continuous polling: {str(e)}")
                # Don't exit the loop, try again after a short delay
                time.sleep(interval)
                
    except KeyboardInterrupt:
        logger.info("Continuous polling stopped by keyboard interrupt")
    finally:
        logger.info("Continuous polling stopped")
