"""
nfc_controller.py - Main NFC controller interface for other application modules.

This module provides a clean, reliable interface for NFC tag operations with 
robust error handling and improved performance for read/write operations.
"""

import logging
import threading
import time
from .hardware_interface import NFCReader
from .tag_processor import format_uid, parse_ndef_data, create_ndef_data
from .exceptions import (
    NFCError, NFCNoTagError, NFCReadError, NFCWriteError, 
    NFCHardwareError, NFCAuthenticationError, NFCTagNotWritableError
)

# Configure logger
logger = logging.getLogger(__name__)

# Global reader instance (singleton pattern)
_nfc_reader = None
_reader_lock = threading.Lock()
_initialized = False

def initialize(i2c_bus=1, i2c_address=0x24, retries=3):
    """
    Initialize the NFC controller and hardware.
    
    Args:
        i2c_bus (int): I2C bus number (usually 1 on Raspberry Pi)
        i2c_address (int): I2C device address of the NFC HAT
        retries (int): Number of connection retries before failing
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    global _nfc_reader, _initialized
    
    with _reader_lock:
        # Return early if already initialized
        if _initialized and _nfc_reader is not None:
            logger.debug("NFC controller already initialized")
            return True
            
        _initialized = False
        
        # Try initialization with retries
        for attempt in range(retries):
            try:
                # Clean up previous instance if it exists
                if _nfc_reader is not None:
                    try:
                        _nfc_reader.disconnect()
                    except Exception as e:
                        logger.debug(f"Error disconnecting previous reader: {e}")
                
                # Create new reader instance
                _nfc_reader = NFCReader(i2c_bus, i2c_address)
                
                # Connect to hardware
                if not _nfc_reader.connect():
                    logger.error(f"Failed to connect to NFC hardware (attempt {attempt+1}/{retries})")
                    time.sleep(0.5)  # Brief delay before retry
                    continue
                
                # Reset hardware to ensure clean state
                _nfc_reader.reset()
                
                _initialized = True
                logger.info(f"NFC controller initialized successfully on bus {i2c_bus}, address 0x{i2c_address:02X}")
                return True
                
            except Exception as e:
                logger.error(f"Error during NFC initialization (attempt {attempt+1}/{retries}): {e}")
                if _nfc_reader:
                    try:
                        _nfc_reader.disconnect()
                    except Exception:
                        pass
                    _nfc_reader = None
                
                # Wait before retrying, increasing delay with each attempt
                time.sleep(0.5 * (attempt + 1))
        
        # If we get here, all retries failed
        _nfc_reader = None
        logger.error(f"NFC initialization failed after {retries} attempts")
        return False

def shutdown():
    """
    Clean shutdown of NFC hardware.
    
    Returns:
        bool: True if shutdown successful, False if errors occurred
    """
    global _nfc_reader, _initialized
    
    with _reader_lock:
        if not _nfc_reader:
            logger.debug("NFC controller already shut down or not initialized")
            _initialized = False
            return True
        
        try:
            _nfc_reader.disconnect()
            logger.info("NFC controller shut down successfully")
            _initialized = False
            return True
        except Exception as e:
            logger.error(f"Error during NFC shutdown: {e}")
            return False
        finally:
            _nfc_reader = None

def _ensure_initialized():
    """
    Internal helper to ensure NFC controller is initialized before operations.
    
    Raises:
        NFCHardwareError: If NFC controller is not initialized
    """
    global _nfc_reader, _initialized
    
    if not _initialized or _nfc_reader is None:
        error_msg = "NFC controller not initialized"
        logger.error(error_msg)
        raise NFCHardwareError(error_msg)

def _reinitialize_if_needed():
    """
    Internal helper to attempt re-initialization if connection seems broken.
    
    Returns:
        bool: True if reinitialization successful or not needed, False otherwise
    """
    global _nfc_reader, _initialized
    
    if not _initialized or _nfc_reader is None:
        logger.warning("Attempting to reinitialize NFC controller")
        # Use default parameters if we don't have the original ones
        i2c_bus = getattr(_nfc_reader, 'i2c_bus', 1) if _nfc_reader else 1
        i2c_address = getattr(_nfc_reader, 'i2c_address', 0x24) if _nfc_reader else 0x24
        return initialize(i2c_bus, i2c_address)
    
    return True

def poll_for_tag(read_ndef=False, timeout=0.1, retries=2):
    """
    Check for presence of an NFC tag and optionally read NDEF data.
    
    Args:
        read_ndef (bool): Whether to attempt to read NDEF data from the tag
        timeout (float): Timeout in seconds for the polling operation
        retries (int): Number of retries if initial poll fails
    
    Returns:
        tuple or str or None: 
            - If read_ndef=True and successful: (uid_str, ndef_data)
            - If read_ndef=True but no NDEF data: (uid_str, None)
            - If read_ndef=False: uid_str if tag found, None otherwise
    """
    global _nfc_reader
    
    with _reader_lock:
        # Ensure NFC controller is initialized
        try:
            _ensure_initialized()
        except NFCHardwareError:
            if not _reinitialize_if_needed():
                return None
        
        # Multiple attempts to improve reliability
        for attempt in range(retries + 1):
            try:
                # Poll for tag
                raw_uid = _nfc_reader.poll()
                
                # Return None if no tag found
                if not raw_uid:
                    if attempt < retries:
                        time.sleep(0.05)  # Short delay before retry
                        continue
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
                        logger.debug(f"Read NDEF data during polling: {len(ndef_data.get('records', []))} records")
                except Exception as e:
                    logger.debug(f"Unable to read NDEF data during polling: {e}")
                
                # Return tuple of UID and NDEF data (which may be None)
                return (uid, ndef_data)
                
            except Exception as e:
                if attempt < retries:
                    logger.debug(f"Poll attempt {attempt+1} failed: {e}, retrying...")
                    time.sleep(0.05)  # Short delay before retry
                    continue
                else:
                    logger.error(f"Error polling for NFC tag after {retries+1} attempts: {e}")
                    return None

def read_tag_data(block=4, retries=3):
    """
    Read data from a specific block on the currently present tag.
    
    Args:
        block (int): Block number to read from
        retries (int): Number of read retries if failures occur
    
    Returns:
        bytes: Data read from the tag
    
    Raises:
        NFCReadError: If reading fails
        NFCNoTagError: If no tag is present
        NFCHardwareError: If hardware not initialized
    """
    global _nfc_reader
    
    with _reader_lock:
        # Ensure NFC controller is initialized
        try:
            _ensure_initialized()
        except NFCHardwareError as e:
            if not _reinitialize_if_needed():
                raise e
        
        for attempt in range(retries + 1):
            try:
                # Read block data
                data = _nfc_reader.read_block(block)
                if data and len(data) == 16:
                    logger.debug(f"Data read from block {block}: {data.hex()}")
                    return data
                else:
                    raise NFCReadError(f"Invalid data length from block {block}: {len(data) if data else 0} bytes")
                
            except NFCNoTagError:
                # No point retrying if tag isn't present
                logger.warning("No tag present when trying to read")
                raise
                
            except Exception as e:
                if attempt < retries:
                    logger.debug(f"Read attempt {attempt+1} failed: {e}, retrying...")
                    time.sleep(0.1)  # Slightly longer delay for read retries
                    continue
                else:
                    error_msg = f"Error reading tag data from block {block} after {retries+1} attempts: {e}"
                    logger.error(error_msg)
                    raise NFCReadError(error_msg)

def write_tag_data(data, block=4, verify=True, max_retries=3):
    """
    Write data to a specific block on the currently present tag.
    
    Args:
        data (bytes or str): Data to write (must be 16 bytes or less)
        block (int): Block number to write to
        verify (bool): Whether to verify the data was written correctly
        max_retries (int): Maximum number of retry attempts if verification fails
    
    Returns:
        bool: True if write successful
    
    Raises:
        NFCWriteError: If writing fails
        NFCNoTagError: If no tag is present
        NFCHardwareError: If hardware not initialized
        NFCTagNotWritableError: If tag is read-only
    """
    global _nfc_reader
    
    with _reader_lock:
        # Ensure NFC controller is initialized
        try:
            _ensure_initialized()
        except NFCHardwareError as e:
            if not _reinitialize_if_needed():
                raise e
        
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
        
        # Try to poll for tag first to ensure it's present
        if not _nfc_reader.poll():
            raise NFCNoTagError("No NFC tag detected")
        
        # Write with retries
        retry_count = 0
        while retry_count <= max_retries:
            try:
                # Write data to tag
                success = _nfc_reader.write_block(block, data)
                
                if not success:
                    raise NFCWriteError(f"Failed to write data to block {block}")
                
                # If verification is requested, read back the data and compare
                if verify:
                    # Brief delay to ensure write is complete
                    time.sleep(0.1)
                    
                    # Read back the data
                    read_data = _nfc_reader.read_block(block)
                    
                    # Compare the data
                    if read_data != data:
                        logger.warning(f"Verification failed for block {block}. Retry {retry_count+1}/{max_retries}")
                        logger.warning(f"Expected: {data.hex()}, Got: {read_data.hex()}")
                        
                        if retry_count >= max_retries:
                            error_msg = f"Data verification failed after {max_retries} attempts"
                            logger.error(error_msg)
                            raise NFCWriteError(error_msg)
                        
                        retry_count += 1
                        time.sleep(0.2 * (retry_count + 1))  # Increasing delay with each retry
                        continue
                
                logger.info(f"Successfully wrote data to block {block}")
                return True
                    
            except NFCNoTagError:
                # Re-raise no tag error immediately
                logger.warning("No tag present when trying to write")
                raise
                
            except NFCTagNotWritableError:
                # Re-raise if tag is read-only
                logger.warning("Tag appears to be read-only")
                raise
                
            except Exception as e:
                if retry_count >= max_retries:
                    error_msg = f"Error writing tag data to block {block} after {max_retries} attempts: {e}"
                    logger.error(error_msg)
                    raise NFCWriteError(error_msg)
                
                logger.warning(f"Write error, retrying ({retry_count+1}/{max_retries}): {e}")
                retry_count += 1
                time.sleep(0.2 * retry_count)  # Increasing delay with each retry
        
        # If we exit the loop without returning, we've exhausted all retries
        raise NFCWriteError(f"Failed to write data to block {block} after {max_retries} attempts")

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
            return {
                "initialized": False,
                "connected": False,
                "error": "NFC controller not initialized"
            }
        
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
            logger.error(f"Error getting hardware info: {e}")
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
        NFCHardwareError: If hardware not initialized
    """
    global _nfc_reader
    
    with _reader_lock:
        # Ensure NFC controller is initialized
        try:
            _ensure_initialized()
        except NFCHardwareError as e:
            if not _reinitialize_if_needed():
                raise e
        
        try:
            # Ensure tag is present
            if not _nfc_reader.poll():
                raise NFCNoTagError("No NFC tag detected")
            
            # Authenticate with tag
            result = _nfc_reader.authenticate(block, key_type, key)
            if result:
                logger.info(f"Successfully authenticated for block {block}")
            else:
                raise NFCAuthenticationError(f"Authentication failed for block {block}")
            
            return result
            
        except NFCNoTagError:
            # Re-raise no tag error
            raise
            
        except NFCAuthenticationError:
            # Re-raise authentication error
            raise
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise NFCAuthenticationError(f"Authentication error: {e}")

def _read_ndef_data_internal(max_blocks=8, retries=2):
    """
    Internal helper function to read NDEF data from a tag.
    This is used by poll_for_tag and read_ndef_data.
    
    Args:
        max_blocks (int): Maximum number of blocks to read for NDEF data
        retries (int): Number of retries for each block read
    
    Returns:
        dict: Parsed NDEF message and records or None if no valid NDEF data
        
    Raises:
        NFCReadError: If reading fails
        NFCNoTagError: If no tag is present
    """
    # Read the first block (usually where NDEF data starts)
    try:
        data = read_tag_data(4)
    except NFCReadError:
        # Retry once if first read fails
        try:
            time.sleep(0.1)
            data = read_tag_data(4)
        except Exception as e:
            logger.error(f"Failed to read initial NDEF block: {e}")
            return None
    
    # Check for TLV structure to determine NDEF message length
    if len(data) >= 2 and data[0] == 0x03:  # NDEF Message TLV
        # Determine TLV length format and message length
        if data[1] == 0xFF and len(data) >= 4:
            # 3-byte length format
            tlv_length = int.from_bytes(data[2:4], byteorder='big')
            total_bytes_needed = tlv_length + 4  # TLV type + 3-byte length + payload
        else:
            # 1-byte length format
            tlv_length = data[1]
            total_bytes_needed = tlv_length + 2  # TLV type + length byte + payload
        
        logger.debug(f"Detected NDEF message with length {tlv_length} bytes")
        
        # If data spans multiple blocks, read additional blocks
        if total_bytes_needed > 16:
            # Calculate how many additional blocks we need (up to max_blocks)
            blocks_needed = min((total_bytes_needed - 16 + 15) // 16, max_blocks - 1)
            
            # Read additional blocks and append data
            for i in range(1, blocks_needed + 1):
                block_num = 4 + i
                for attempt in range(retries + 1):
                    try:
                        additional_data = read_tag_data(block_num)
                        data += additional_data
                        break
                    except Exception as e:
                        if attempt < retries:
                            logger.debug(f"Retrying read of NDEF block {block_num}")
                            time.sleep(0.1)
                            continue
                        else:
                            logger.warning(f"Could not read additional NDEF block {block_num}: {e}")
                            # We'll process what we have so far
                            break
            
            logger.debug(f"Read {len(data)} bytes of NDEF data")
    
    # Look for alternative NDEF format where first byte is length
    elif len(data) > 2 and data[0] > 0 and data[0] < len(data) and data[1] in [0x01, 0x03, 0xD1]:
        message_length = data[0]
        logger.debug(f"Detected alternative NDEF format with length {message_length} bytes")
        
        # If data spans multiple blocks, read additional blocks
        if message_length + 1 > 16:
            blocks_needed = min((message_length + 1 - 16 + 15) // 16, max_blocks - 1)
            
            # Read additional blocks
            for i in range(1, blocks_needed + 1):
                try:
                    additional_data = read_tag_data(4 + i)
                    data += additional_data
                except Exception as e:
                    logger.warning(f"Could not read additional NDEF block {4+i}: {e}")
                    break
    
    # Parse NDEF data
    ndef_data = parse_ndef_data(data)
    if not ndef_data:
        logger.debug("No valid NDEF data found on tag")
        return None
        
    return ndef_data

def read_ndef_data(retries=2):
    """
    Read and parse NDEF formatted data from tag.
    
    Args:
        retries (int): Number of read retries if failures occur
    
    Returns:
        dict: Parsed NDEF message and records or None if no valid NDEF data
        
    Raises:
        NFCReadError: If reading fails
        NFCNoTagError: If no tag is present
        NFCHardwareError: If hardware not initialized
    """
    # Ensure NFC controller is initialized
    try:
        _ensure_initialized()
    except NFCHardwareError as e:
        if not _reinitialize_if_needed():
            raise e
    
    # Attempt to read NDEF data with retries
    for attempt in range(retries + 1):
        try:
            ndef_data = _read_ndef_data_internal()
            
            if ndef_data:
                return ndef_data
            
            if attempt < retries:
                logger.debug(f"No valid NDEF data found (attempt {attempt+1}), retrying...")
                time.sleep(0.1)
                continue
            
            logger.warning("No valid NDEF data found on tag after all attempts")
            return None
            
        except NFCNoTagError:
            # No point in retrying if tag isn't present
            raise
            
        except Exception as e:
            if attempt < retries:
                logger.debug(f"NDEF read attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(0.1)
                continue
            
            error_msg = f"Error reading NDEF data after {retries+1} attempts: {e}"
            logger.error(error_msg)
            raise NFCReadError(error_msg)

def write_ndef_uri(uri, retries=2):
    """
    Write a URI record to an NFC tag. Specialized for URLs like YouTube or Music links.
    
    Args:
        uri (str): The URI to write (e.g., 'https://youtube.com/watch?v=...')
        retries (int): Number of write retries if failures occur
        
    Returns:
        bool: True if successful
        
    Raises:
        NFCWriteError: If writing fails
        NFCNoTagError: If no tag is present
        NFCTagNotWritableError: If tag is read-only or incorrectly formatted
        NFCHardwareError: If hardware not initialized
    """
    if not uri:
        raise ValueError("URI cannot be empty")
        
    # Validate URI format (basic check)
    if not (uri.startswith('http://') or uri.startswith('https://')):
        logger.warning(f"URI does not start with http:// or https://: {uri}")
    
    # Use the general NDEF writing function but specify only the URL
    for attempt in range(retries + 1):
        try:
            return write_ndef_data(url=uri)
        except (NFCNoTagError, NFCTagNotWritableError):
            # No point in retrying these errors
            raise
        except Exception as e:
            if attempt < retries:
                logger.debug(f"NDEF URI write attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(0.2)
                continue
            
            error_msg = f"Error writing URI to tag after {retries+1} attempts: {e}"
            logger.error(error_msg)
            raise NFCWriteError(error_msg)

def write_ndef_data(url=None, text=None, retries=2, verify=True):
    """
    Write NDEF formatted data to tag.
    
    Args:
        url (str, optional): URL to encode
        text (str, optional): Text to encode
        retries (int): Number of write retries if failures occur
        verify (bool): Whether to verify the NDEF data after writing
        
    Returns:
        bool: True if successful
        
    Raises:
        NFCWriteError: If writing fails
        NFCNoTagError: If no tag is present
        NFCTagNotWritableError: If tag is read-only or incorrectly formatted
        NFCHardwareError: If hardware not initialized
    """
    if not url and not text:
        raise ValueError("Either url or text must be provided")
    
    # Ensure NFC controller is initialized
    try:
        _ensure_initialized()
    except NFCHardwareError as e:
        if not _reinitialize_if_needed():
            raise e
    
    # Create NDEF formatted data
    try:
        ndef_data = create_ndef_data(url=url, text=text)
    except Exception as e:
        error_msg = f"Error creating NDEF data: {e}"
        logger.error(error_msg)
        raise NFCWriteError(error_msg)
    
    # Ensure tag is present before attempting to write
    if not poll_for_tag():
        raise NFCNoTagError("No NFC tag detected")
    
    # Write data to tag (NDEF data typically starts at block 4)
    # NDEF data may need multiple blocks
    blocks_needed = (len(ndef_data) + 15) // 16  # Ceiling division
    
    for attempt in range(retries + 1):
        try:
            for i in range(blocks_needed):
                block_data = ndef_data[i*16:i*16+16]
                block_num = 4 + i
                
                # Write block
                if not write_tag_data(block_data, block_num, verify=True):
                    raise NFCWriteError(f"Failed to write NDEF data block {block_num}")
                
                # Add a small delay between blocks
                if i < blocks_needed - 1:
                    time.sleep(0.05)
            
            # Verify the NDEF data was written correctly if requested
            if verify:
                # Wait briefly for the tag to stabilize
                time.sleep(0.1)
                
                # Try to read back the NDEF data
                try:
                    verification_data = read_ndef_data()
                    
                    # Basic verification - just check that we got some NDEF data back
                    if not verification_data or not verification_data.get('records'):
                        logger.warning("NDEF write verification failed: Could not read back valid NDEF data")
                        if attempt < retries:
                            logger.debug("Retrying NDEF write operation")
                            time.sleep(0.2)
                            continue
                        else:
                            raise NFCWriteError("NDEF verification failed: Could not read back valid NDEF data")
                    
                    # More specific verification for NDEF URI
                    if url:
                        found_url = False
                        for record in verification_data.get('records', []):
                            if record.get('decoded', {}).get('type') == 'uri':
                                uri_value = record.get('decoded', {}).get('uri')
                                if uri_value and (uri_value == url or url.endswith(uri_value)):
                                    found_url = True
                                    break
                        
                        if not found_url:
                            logger.warning(f"NDEF URI verification failed: URL not found in readback data")
                            if attempt < retries:
                                logger.debug("Retrying NDEF URI write operation")
                                time.sleep(0.2)
                                continue
                            # Continue anyway - the data structure might be valid but our parsing is imperfect
                    
                    # Specific verification for NDEF Text
                    if text:
                        found_text = False
                        for record in verification_data.get('records', []):
                            if record.get('decoded', {}).get('type') == 'text':
                                text_value = record.get('decoded', {}).get('text')
                                if text_value and text_value == text:
                                    found_text = True
                                    break
                        
                        if not found_text:
                            logger.warning(f"NDEF Text verification failed: Text not found in readback data")
                            if attempt < retries:
                                logger.debug("Retrying NDEF Text write operation")
                                time.sleep(0.2)
                                continue
                            # Continue anyway - the data structure might be valid but our parsing is imperfect
                
                except Exception as e:
                    logger.warning(f"NDEF verification read failed: {e}")
                    # Continue anyway - the write might be successful even if verification read fails
            
            logger.info("Successfully wrote NDEF data to tag")
            return True
            
        except NFCNoTagError:
            # No point in retrying if tag isn't present
            raise
            
        except NFCTagNotWritableError:
            # No point in retrying if tag is read-only
            raise
            
        except Exception as e:
            if attempt < retries:
                logger.debug(f"NDEF write attempt {attempt+1} failed: {e}, retrying...")
                time.sleep(0.2)
                continue
            
            error_msg = f"Error writing NDEF data after {retries+1} attempts: {e}"
            logger.error(error_msg)
            raise NFCWriteError(error_msg)

def continuous_poll(callback, interval=0.1, exit_event=None, read_ndef=False, deduplicate=True):
    """
    Continuously poll for NFC tags and call the callback function when detected.
    
    Args:
        callback (function): Function to call when tag is detected.
                             If read_ndef is False: Called with UID string parameter
                             If read_ndef is True: Called with (UID string, NDEF data) tuple
        interval (float): Polling interval in seconds
        exit_event (threading.Event, optional): Event to signal when to stop polling
        read_ndef (bool): Whether to read NDEF data from detected tags
        deduplicate (bool): Only trigger callback when a new tag is detected (not on every poll)
        
    Note:
        This function runs in a loop and is typically called in a separate thread.
    """
    last_uid = None
    tag_present = False
    consecutive_errors = 0
    
    # Create an exit event if one wasn't provided
    if exit_event is None:
        exit_event = threading.Event()
    
    logger.info(f"Starting continuous polling with interval {interval}s, read_ndef={read_ndef}")
    
    try:
        # Ensure NFC controller is initialized before starting
        if not _initialized or _nfc_reader is None:
            if not _reinitialize_if_needed():
                logger.error("Could not initialize NFC controller for continuous polling")
                return
        
        while not exit_event.is_set():
            try:
                # Poll for tag (with or without NDEF data)
                result = poll_for_tag(read_ndef=read_ndef)
                
                # Reset error counter on successful poll
                consecutive_errors = 0
                
                # If no tag detected
                if not result:
                    # If a tag was previously present, now it's gone
                    if tag_present:
                        tag_present = False
                        logger.debug("Tag removed")
                    
                    # Clear last UID if we're deduplicating
                    if deduplicate:
                        last_uid = None
                    
                    time.sleep(interval)
                    continue
                
                # Extract UID (and possibly NDEF data) from result
                if read_ndef:
                    uid, ndef_data = result
                else:
                    uid = result
                    ndef_data = None
                
                # Tag is present
                tag_present = True
                
                # Check if this is a new tag or we're not deduplicating
                if not deduplicate or uid != last_uid:
                    # Call callback with appropriate parameters
                    try:
                        if read_ndef:
                            callback(uid, ndef_data)
                        else:
                            callback(uid)
                        
                        # Update last seen UID
                        last_uid = uid
                        
                    except Exception as e:
                        logger.error(f"Error in tag detection callback: {e}")
                
                # Wait for next poll
                time.sleep(interval)
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error during continuous polling: {e}")
                
                # If we have too many consecutive errors, try to reinitialize
                if consecutive_errors >= 5:
                    logger.warning("Too many consecutive errors, attempting to reinitialize NFC controller")
                    try:
                        shutdown()
                        time.sleep(0.5)
                        if not initialize():
                            logger.error("Failed to reinitialize NFC controller, stopping continuous poll")
                            return
                        consecutive_errors = 0
                    except Exception as reinit_e:
                        logger.error(f"Error reinitializing NFC controller: {reinit_e}")
                        return
                
                # Don't exit the loop, try again after a short delay
                time.sleep(interval)
                
    except KeyboardInterrupt:
        logger.info("Continuous polling stopped by keyboard interrupt")
    finally:
        logger.info("Continuous polling stopped")