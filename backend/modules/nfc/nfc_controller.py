"""
nfc_controller.py - Main NFC controller interface for other application modules.
"""

import logging
import threading
import time
from .hardware_interface import NFCReader
from .tag_processor import format_uid, parse_ndef_data, create_ndef_data
from .exceptions import (
    NFCError, NFCNoTagError, NFCReadError, NFCWriteError, NFCHardwareError,
    NFCTagNotWritableError
)

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


def poll_for_tag():
    """
    Check for presence of an NFC tag.
    
    Returns:
        str or None: Tag UID if detected, None otherwise.
    """
    global _nfc_reader
    
    with _reader_lock:
        if not _nfc_reader:
            logger.error("NFC controller not initialized")
            return None
        
        try:
            # Poll for tag
            raw_uid = _nfc_reader.poll()
            
            # Format and return UID if found
            if raw_uid:
                uid = format_uid(raw_uid)
                logger.debug(f"NFC tag detected: {uid}")
                return uid
                
            return None
            
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

# --- Restored NDEF Functions ---

def read_ndef_data():
    """
    Read and parse NDEF formatted data from tag.
    
    Returns:
        dict: Parsed NDEF message and records, or None if no valid NDEF data found.
        
    Raises:
        NFCReadError: If reading fails critically.
        NFCNoTagError: If no tag is present.
        NFCHardwareError: If the controller is not initialized.
    """
    global _nfc_reader
    with _reader_lock:
        if not _nfc_reader:
            error_msg = "NFC controller not initialized"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)

        try:
            # NDEF data typically starts at block 4, but may span multiple blocks
            # Read first block to determine TLV length
            data = read_tag_data(4) # Use the existing read_tag_data which reads one block
            
            # Check for TLV structure to determine total length
            if len(data) >= 2 and data[0] == 0x03:  # NDEF Message TLV
                start_offset = 2
                if data[1] == 0xFF and len(data) >= 4: # 3-byte length format
                    tlv_length = int.from_bytes(data[2:4], byteorder='big')
                    start_offset = 4
                else: # 1-byte length format
                    tlv_length = data[1]

                total_bytes_needed = tlv_length + start_offset
                
                # If data spans multiple blocks, read additional blocks
                if total_bytes_needed > 16:
                    num_blocks_to_read = (total_bytes_needed + 15) // 16 # Total blocks needed
                    # Read additional blocks and append data
                    for i in range(1, num_blocks_to_read):
                        block_num = 4 + i
                        try:
                            additional_data = read_tag_data(block_num)
                            data += additional_data
                        except NFCReadError as block_e:
                            logger.warning(f"Could not read additional NDEF block {block_num}: {str(block_e)}")
                            # Return partial data if possible, or None if critical read failed
                            break # Stop reading further blocks
                        except NFCNoTagError:
                            logger.warning(f"Tag removed while reading NDEF block {block_num}")
                            raise # Propagate NoTagError
                        except Exception as block_e:
                             logger.error(f"Unexpected error reading NDEF block {block_num}: {str(block_e)}")
                             break # Stop reading further blocks

                    logger.debug(f"Read {len(data)} bytes of NDEF data across {num_blocks_to_read} blocks")
            
            # Parse NDEF data using the function from tag_processor
            ndef_info = parse_ndef_data(data)
            if not ndef_info:
                logger.info("No valid NDEF data found on tag after reading blocks.")
                return None
                
            logger.info("Successfully read and parsed NDEF data.")
            return ndef_info # Return the full parsed dictionary

        except NFCNoTagError:
            logger.debug("No tag present while attempting to read NDEF data.")
            raise # Re-raise to be handled by caller
        except NFCReadError as e:
            logger.warning(f"NFC Read Error while reading NDEF data: {str(e)}")
            raise # Re-raise critical read errors
        except Exception as e:
            logger.error(f"Unexpected error reading NDEF data: {str(e)}")
            # Raise a generic NFCReadError for unexpected issues during NDEF read
            raise NFCReadError(f"Unexpected error reading NDEF data: {str(e)}")


def write_ndef_data(url=None, text=None):
    """
    Write NDEF formatted data (URI or Text) to the currently present tag.
    
    Args:
        url (str, optional): URL to encode.
        text (str, optional): Text to encode. Only one of url or text should be provided.
        
    Returns:
        bool: True if write successful.
        
    Raises:
        NFCNoTagError: If no tag is present during the operation.
        NFCTagNotWritableError: If the tag is read-only or cannot be written to.
        NFCWriteError: For other write-related failures.
        NFCHardwareError: If the controller is not initialized.
        ValueError: If neither url nor text is provided.
    """
    global _nfc_reader
    with _reader_lock:
        if not _nfc_reader:
            error_msg = "NFC controller not initialized"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)

        # Ensure a tag is present before attempting to write
        if not _nfc_reader._last_tag_uid:
             # Try polling once more to be sure
            if not poll_for_tag(): # Check only UID part of the tuple
                raise NFCNoTagError("No NFC tag detected to write NDEF data to")

        if not url and not text:
             raise ValueError("Either url or text must be provided to write_ndef_data")
        if url and text:
             logger.warning("Both url and text provided to write_ndef_data, using url.")
             text = None # Prioritize URL if both given

        log_target = f"URI '{url}'" if url else f"Text '{text[:20]}...'"
        logger.info(f"Attempting to write NDEF {log_target}")

        try:
            # Create NDEF formatted data (including TLV and padding)
            ndef_data_bytes = create_ndef_data(url=url, text=text)
            logger.debug(f"Generated NDEF data ({len(ndef_data_bytes)} bytes): {ndef_data_bytes.hex()}")

            # Check if tag is writable *before* attempting write
            if _nfc_reader.is_tag_read_only():
                 logger.error("Tag is read-only or write-protected. Cannot write NDEF data.")
                 raise NFCTagNotWritableError("Tag is read-only or write-protected")

            # Write data to tag starting at block 4
            num_blocks = (len(ndef_data_bytes) + 15) // 16
            logger.info(f"Writing {len(ndef_data_bytes)} bytes ({num_blocks} blocks) starting at block 4...")

            for i in range(num_blocks):
                start_index = i * 16
                end_index = start_index + 16
                block_data = ndef_data_bytes[start_index:end_index]
                block_num = 4 + i

                # Pad the last block if necessary (should already be padded by create_ndef_data)
                if len(block_data) < 16:
                    block_data = block_data.ljust(16, b'\x00')

                logger.debug(f"Writing block {block_num} with data: {block_data.hex()}")
                # Use write_tag_data with verify=True by default
                if not write_tag_data(block_data, block_num, verify=True):
                    logger.error(f"write_tag_data returned False for block {block_num}, expected exception on failure.")
                    raise NFCWriteError(f"Failed to write block {block_num} during NDEF write operation")

            logger.info(f"Successfully wrote NDEF data to tag.")
            return True

        except NFCNoTagError:
            logger.error("Tag removed during NDEF write operation.")
            raise # Re-raise
        except NFCTagNotWritableError as e:
             logger.error(f"Cannot write NDEF data: {str(e)}")
             raise # Re-raise specific error
        except NFCWriteError as e:
            logger.error(f"Failed to write NDEF data: {str(e)}")
            raise # Re-raise write errors
        except Exception as e:
            logger.error(f"Unexpected error writing NDEF data: {str(e)}")
            # Raise a generic NFCWriteError for unexpected issues
            raise NFCWriteError(f"Unexpected error writing NDEF data: {str(e)}")

# --- Restored NDEF Functions ---

def read_ndef_data():
    """
    Read and parse NDEF formatted data from tag.
    
    Returns:
        dict: Parsed NDEF message and records, or None if no valid NDEF data found.
        
    Raises:
        NFCReadError: If reading fails critically.
        NFCNoTagError: If no tag is present.
        NFCHardwareError: If the controller is not initialized.
    """
    global _nfc_reader
    with _reader_lock:
        if not _nfc_reader:
            error_msg = "NFC controller not initialized"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)

        try:
            # NDEF data typically starts at block 4, but may span multiple blocks
            # Read first block to determine TLV length
            data = read_tag_data(4) # Use the existing read_tag_data which reads one block
            
            # Check for TLV structure to determine total length
            if len(data) >= 2 and data[0] == 0x03:  # NDEF Message TLV
                start_offset = 2
                if data[1] == 0xFF and len(data) >= 4: # 3-byte length format
                    tlv_length = int.from_bytes(data[2:4], byteorder='big')
                    start_offset = 4
                else: # 1-byte length format
                    tlv_length = data[1]

                total_bytes_needed = tlv_length + start_offset
                
                # If data spans multiple blocks, read additional blocks
                if total_bytes_needed > 16:
                    num_blocks_to_read = (total_bytes_needed + 15) // 16 # Total blocks needed
                    # Read additional blocks and append data
                    for i in range(1, num_blocks_to_read):
                        block_num = 4 + i
                        try:
                            additional_data = read_tag_data(block_num)
                            data += additional_data
                        except NFCReadError as block_e:
                            logger.warning(f"Could not read additional NDEF block {block_num}: {str(block_e)}")
                            # Return partial data if possible, or None if critical read failed
                            break # Stop reading further blocks
                        except NFCNoTagError:
                            logger.warning(f"Tag removed while reading NDEF block {block_num}")
                            raise # Propagate NoTagError
                        except Exception as block_e:
                             logger.error(f"Unexpected error reading NDEF block {block_num}: {str(block_e)}")
                             break # Stop reading further blocks

                    logger.debug(f"Read {len(data)} bytes of NDEF data across {num_blocks_to_read} blocks")
            
            # Parse NDEF data using the function from tag_processor
            ndef_info = parse_ndef_data(data)
            if not ndef_info:
                logger.info("No valid NDEF data found on tag after reading blocks.")
                return None
                
            logger.info("Successfully read and parsed NDEF data.")
            return ndef_info # Return the full parsed dictionary

        except NFCNoTagError:
            logger.debug("No tag present while attempting to read NDEF data.")
            raise # Re-raise to be handled by caller
        except NFCReadError as e:
            logger.warning(f"NFC Read Error while reading NDEF data: {str(e)}")
            raise # Re-raise critical read errors
        except Exception as e:
            logger.error(f"Unexpected error reading NDEF data: {str(e)}")
            # Raise a generic NFCReadError for unexpected issues during NDEF read
            raise NFCReadError(f"Unexpected error reading NDEF data: {str(e)}")


def write_ndef_data(url=None, text=None):
    """
    Write NDEF formatted data (URI or Text) to the currently present tag.
    
    Args:
        url (str, optional): URL to encode.
        text (str, optional): Text to encode. Only one of url or text should be provided.
        
    Returns:
        bool: True if write successful.
        
    Raises:
        NFCNoTagError: If no tag is present during the operation.
        NFCTagNotWritableError: If the tag is read-only or cannot be written to.
        NFCWriteError: For other write-related failures.
        NFCHardwareError: If the controller is not initialized.
        ValueError: If neither url nor text is provided.
    """
    global _nfc_reader
    with _reader_lock:
        if not _nfc_reader:
            error_msg = "NFC controller not initialized"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)

        # Ensure a tag is present before attempting to write
        if not _nfc_reader._last_tag_uid:
             # Try polling once more to be sure
            if not poll_for_tag(): # Check only UID part of the tuple
                raise NFCNoTagError("No NFC tag detected to write NDEF data to")

        if not url and not text:
             raise ValueError("Either url or text must be provided to write_ndef_data")
        if url and text:
             logger.warning("Both url and text provided to write_ndef_data, using url.")
             text = None # Prioritize URL if both given

        log_target = f"URI '{url}'" if url else f"Text '{text[:20]}...'"
        logger.info(f"Attempting to write NDEF {log_target}")

        try:
            # Create NDEF formatted data (including TLV and padding)
            ndef_data_bytes = create_ndef_data(url=url, text=text)
            logger.debug(f"Generated NDEF data ({len(ndef_data_bytes)} bytes): {ndef_data_bytes.hex()}")

            # Check if tag is writable *before* attempting write
            if _nfc_reader.is_tag_read_only():
                 logger.error("Tag is read-only or write-protected. Cannot write NDEF data.")
                 raise NFCTagNotWritableError("Tag is read-only or write-protected")

            # Write data to tag starting at block 4
            num_blocks = (len(ndef_data_bytes) + 15) // 16
            logger.info(f"Writing {len(ndef_data_bytes)} bytes ({num_blocks} blocks) starting at block 4...")

            for i in range(num_blocks):
                start_index = i * 16
                end_index = start_index + 16
                block_data = ndef_data_bytes[start_index:end_index]
                block_num = 4 + i

                # Pad the last block if necessary (should already be padded by create_ndef_data)
                if len(block_data) < 16:
                    block_data = block_data.ljust(16, b'\x00')

                logger.debug(f"Writing block {block_num} with data: {block_data.hex()}")
                # Use write_tag_data with verify=True by default
                if not write_tag_data(block_data, block_num, verify=True):
                    logger.error(f"write_tag_data returned False for block {block_num}, expected exception on failure.")
                    raise NFCWriteError(f"Failed to write block {block_num} during NDEF write operation")

            logger.info(f"Successfully wrote NDEF data to tag.")
            return True

        except NFCNoTagError:
            logger.error("Tag removed during NDEF write operation.")
            raise # Re-raise
        except NFCTagNotWritableError as e:
             logger.error(f"Cannot write NDEF data: {str(e)}")
             raise # Re-raise specific error
        except NFCWriteError as e:
            logger.error(f"Failed to write NDEF data: {str(e)}")
            raise # Re-raise write errors
        except Exception as e:
            logger.error(f"Unexpected error writing NDEF data: {str(e)}")
            # Raise a generic NFCWriteError for unexpected issues
            raise NFCWriteError(f"Unexpected error writing NDEF data: {str(e)}")

# --- End Restored NDEF Functions ---


def continuous_poll(callback, interval=0.1, exit_event=None):
"""
nfc_controller.py - Main NFC controller interface for other application modules.
"""

import logging
import threading
import time
from .hardware_interface import NFCReader
from .tag_processor import format_uid, parse_ndef_data, create_ndef_data
from .exceptions import (
    NFCError, NFCNoTagError, NFCReadError, NFCWriteError, NFCHardwareError,
    NFCTagNotWritableError
)

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
# Remove the internal helper and the specific write_ndef_uri function
# def _read_ndef_data_internal(): ... (Removed)
# def write_ndef_uri(uri: str): ... (Removed)


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
