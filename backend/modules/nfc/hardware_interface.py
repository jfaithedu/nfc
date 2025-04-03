"""
hardware_interface.py - Low-level NFC reader interface using Adafruit PN532 library.
"""

import time
import logging
import board
import busio
from adafruit_pn532.i2c import PN532_I2C
from .exceptions import NFCHardwareError, NFCReadError, NFCWriteError, NFCNoTagError, NFCAuthenticationError, NFCTagNotWritableError

# Create logger
logger = logging.getLogger(__name__)

class NFCReader:
    """
    NFC reader interface using the Adafruit PN532 library.

    Attributes:
        i2c_bus (int): I2C bus number (not used in Adafruit implementation, kept for API compatibility)
        i2c_address (int): I2C device address
        _pn532: PN532 device instance
        _i2c: I2C bus instance
    """

    def __init__(self, i2c_bus=1, i2c_address=0x24):
        """
        Initialize NFC reader with I2C parameters.

        Args:
            i2c_bus (int): I2C bus number (kept for API compatibility)
            i2c_address (int): I2C device address of the NFC HAT (default 0x24)
        """
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self._pn532 = None
        self._i2c = None
        self._connected = False
        self._last_tag_uid = None
        logger.info(f"Initializing NFC reader on I2C bus {i2c_bus}, address 0x{i2c_address:02X}")

    def connect(self):
        """
        Establish connection to the NFC hardware.

        Returns:
            bool: True if connected successfully
        """
        try:
            # Initialize I2C bus
            self._i2c = busio.I2C(board.SCL, board.SDA)
            
            # Create PN532 instance
            self._pn532 = PN532_I2C(self._i2c, address=self.i2c_address, debug=False)
            
            # Get firmware version to check connection
            try:
                firmware_data = self._pn532.firmware_version
                ic, ver, rev, support = firmware_data
                version = f"v{ver}.{rev}"
                logger.info(f"Connected to PN532 NFC reader: IC={ic}, Version={version}, Support={support}")
                
                # Configure to read MiFare cards
                self._pn532.SAM_configuration()
                
                self._connected = True
                return True
                
            except Exception as e:
                logger.error(f"Failed to get firmware version: {str(e)}")
                self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to NFC hardware: {str(e)}")
            self.disconnect()
            return False

    def disconnect(self):
        """Close connection to NFC hardware."""
        try:
            if self._i2c:
                self._i2c.deinit()
                logger.info("Disconnected from NFC hardware")
        except Exception as e:
            logger.error(f"Error disconnecting from NFC hardware: {str(e)}")
        finally:
            self._pn532 = None
            self._i2c = None
            self._connected = False

    def reset(self):
        """
        Reset the NFC hardware.
        Note: Adafruit library doesn't expose a direct reset command,
        but we can reinitialize the device.
        """
        if not self._connected:
            raise NFCHardwareError("Not connected to NFC hardware")
        
        try:
            # Configure PN532 back to default settings
            self._pn532.SAM_configuration()
            logger.info("NFC hardware reset completed")
            return True
        except Exception as e:
            logger.error(f"Error resetting NFC hardware: {str(e)}")
            raise NFCHardwareError(f"Failed to reset NFC hardware: {str(e)}")

    def get_version(self):
        """
        Get firmware version from the NFC hardware.
        
        Returns:
            str: Version string or None if failed
        """
        if not self._connected or not self._pn532:
            logger.error("Not connected to NFC hardware")
            return None
            
        try:
            firmware_data = self._pn532.firmware_version
            ic, ver, rev, support = firmware_data
            version = f"v{ver}.{rev}"
            return version
        except Exception as e:
            logger.error(f"Error getting NFC hardware version: {str(e)}")
            return None

    def poll(self):
        """
        Poll for tag presence.

        Returns:
            bytes or None: Tag UID if detected, None otherwise
        """
        if not self._connected or not self._pn532:
            logger.error("Not connected to NFC hardware")
            return None
            
        try:
            # read_passive_target will return None if no card is available
            uid = self._pn532.read_passive_target(timeout=0.1)
            
            if uid is not None:
                self._last_tag_uid = bytes(uid)
                logger.debug(f"Tag detected with UID: {self._last_tag_uid.hex()}")
                return self._last_tag_uid
                
            self._last_tag_uid = None
            return None
            
        except Exception as e:
            logger.error(f"Error polling for NFC tag: {str(e)}")
            self._last_tag_uid = None
            return None

    def detect_tag_type(self):
        """
        Attempt to detect the tag type based on the UID and other characteristics.
        
        Returns:
            str: Tag type string ('ntag215', 'mifare_classic', 'unknown', etc.)
        """
        if not self._last_tag_uid:
            return "unknown"
            
        # NTAG215 typically has 7-byte UIDs
        if len(self._last_tag_uid) == 7:
            # Try reading first page with ntag2xx method
            try:
                # Try to read page 0 (manufacturer info)
                data = self._pn532.ntag2xx_read_block(0)
                if data:
                    logger.info(f"Detected NTAG2xx tag (likely NTAG215) with UID: {self._last_tag_uid.hex()}")
                    return "ntag215"
            except Exception:
                pass
        
        # MIFARE Classic typically has 4-byte or 7-byte UIDs
        if len(self._last_tag_uid) in [4, 7]:
            # Try authenticating with MIFARE Classic method
            try:
                key = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]  # Factory default key
                auth_result = self._pn532.mifare_classic_authenticate_block(
                    self._last_tag_uid, 4, 0x60, key
                )
                if auth_result:
                    logger.info(f"Detected MIFARE Classic tag with UID: {self._last_tag_uid.hex()}")
                    return "mifare_classic"
            except Exception:
                pass
        
        # Default fallback
        logger.info(f"Unknown tag type with UID: {self._last_tag_uid.hex()}")
        return "unknown"
        
    def read_block(self, block_number):
        """
        Read a data block from the currently detected tag.

        Args:
            block_number (int): Block number to read

        Returns:
            bytes: Block data (16 bytes)
            
        Raises:
            NFCNoTagError: If no tag is present
            NFCReadError: If reading fails
        """
        if not self._connected or not self._pn532:
            raise NFCHardwareError("Not connected to NFC hardware")
            
        if not self._last_tag_uid:
            # Try polling first to see if there's a tag
            if not self.poll():
                raise NFCNoTagError("No NFC tag detected")
        
        # For NTAG215, convert block number to page number if needed
        # NTAG215 pages are 4 bytes, blocks are typically considered 16 bytes
        # So one block = 4 NTAG215 pages
        tag_type = self.detect_tag_type()
        
        try:
            # Special handling for NTAG215 tags
            if tag_type == "ntag215":
                # For NTAG215, we need to read 4 consecutive pages to get 16 bytes
                start_page = block_number * 4
                combined_data = bytearray()
                
                # Read 4 consecutive pages (each page is 4 bytes)
                for page in range(start_page, start_page + 4):
                    # Skip pages beyond the tag's capacity (NTAG215 has 135 pages, 0-134)
                    if page > 134:
                        # Pad with zeros if we exceed the tag's capacity
                        combined_data.extend(bytes(4))
                        continue
                        
                    try:
                        page_data = self._pn532.ntag2xx_read_block(page)
                        if page_data and len(page_data) == 4:
                            combined_data.extend(page_data)
                        else:
                            # Pad with zeros if page read fails
                            combined_data.extend(bytes(4))
                    except Exception as e:
                        logger.debug(f"Error reading NTAG215 page {page}: {str(e)}")
                        # Pad with zeros if page read fails
                        combined_data.extend(bytes(4))
                
                if len(combined_data) == 16:
                    logger.debug(f"Read block {block_number} (pages {start_page}-{start_page+3}) from NTAG215")
                    return bytes(combined_data)
                else:
                    logger.warning(f"Invalid data length {len(combined_data)} from NTAG215 read")
            
            # Try NTAG2xx read method for any tag (might work for NTAG215 and others)
            try:
                data = self._pn532.ntag2xx_read_block(block_number)
                if data and len(data) == 16:
                    logger.debug(f"Read block {block_number} as NTAG/Ultralight")
                    return bytes(data)
                elif data and len(data) == 4:
                    # Got a single page, need to pad to 16 bytes
                    padded_data = bytearray(data)
                    padded_data.extend(bytes(12))  # Pad to 16 bytes
                    logger.debug(f"Read page {block_number} as NTAG/Ultralight (padded to 16 bytes)")
                    return bytes(padded_data)
            except Exception as e:
                logger.debug(f"NTAG read attempt failed: {str(e)}, trying other methods")
            
            # If NTAG read fails, try as MIFARE Classic
            try:
                # Authenticate before reading - MIFARE blocks require authentication
                # Calculate the sector (each sector has 4 blocks)
                sector = block_number // 4
                
                # Try both key A and key B with factory defaults
                keys = [
                    (0x60, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),  # Key A default
                    (0x61, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),  # Key B default
                    (0x60, [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7]),  # Another common Key A
                    (0x60, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5])   # Another common Key A
                ]
                
                auth_success = False
                for key_type, key in keys:
                    try:
                        auth_result = self._pn532.mifare_classic_authenticate_block(
                            self._last_tag_uid, block_number, key_type, key
                        )
                        if auth_result:
                            auth_success = True
                            logger.debug(f"Authentication succeeded with key_type {key_type}")
                            break
                    except Exception as auth_e:
                        logger.debug(f"Authentication attempt failed: {str(auth_e)}")
                        continue
                
                if not auth_success:
                    logger.warning(f"All authentication attempts failed for block {block_number}, trying to read anyway")
                
                # Read data from the specified block
                data = self._pn532.mifare_classic_read_block(block_number)
                
                if not data or len(data) != 16:
                    raise NFCReadError(f"Invalid data read from block {block_number}")
                    
                return bytes(data)
                
            except Exception as mifare_e:
                logger.debug(f"MIFARE read attempt failed: {str(mifare_e)}")
                
            # As a last resort, try a direct block read without specifying tag type
            # This might work for some tags or PN532 implementations
            try:
                # This is a generic command to read a block
                # Using raw commands as a fallback
                command = bytearray([0x40])  # InDataExchange command
                command.extend([0x30, block_number])  # MIFARE Read command + block number
                
                logger.debug(f"Trying direct block read for block {block_number}")
                response = self._pn532._write_frame(command)
                
                if response and len(response) >= 16:
                    return bytes(response[:16])
                else:
                    raise NFCReadError(f"Invalid response from direct read: {response}")
            except Exception as direct_e:
                logger.debug(f"Direct read attempt failed: {str(direct_e)}")
                # Fall through to the final error
                
            # If we got here, all read attempts failed
            raise NFCReadError(f"All read methods failed for block {block_number}")
            
        except NFCNoTagError:
            # Re-raise no tag error
            raise
        except Exception as e:
            error_msg = f"Error reading block {block_number}: {str(e)}"
            logger.error(error_msg)
            raise NFCReadError(error_msg)

    def is_tag_read_only(self):
        """
        Check if the currently detected tag is read-only.
        
        Returns:
            bool: True if tag appears to be read-only, False otherwise
        """
        if not self._connected or not self._pn532 or not self._last_tag_uid:
            return False
            
        # Try to determine if this is a read-only tag
        # Strategy: Try to read a block, then try to write the same data back
        try:
            # Use block 4 which is typically a data block on most tags
            test_block = 4
            
            # Try to read the block first
            original_data = None
            try:
                original_data = self.read_block(test_block)
                logger.debug(f"Read data for read-only test: {original_data.hex()}")
            except Exception as e:
                logger.debug(f"Could not read block {test_block} for read-only test: {str(e)}")
                return False  # If we can't read, we can't determine
                
            # Try to write the same data back (this shouldn't modify the tag)
            try:
                # Use the _write_block_internal method which doesn't call is_tag_read_only
                self._write_block_internal(test_block, original_data)
                return False  # If write succeeds, tag is not read-only
            except Exception as e:
                logger.debug(f"Write failed in read-only test: {str(e)}")
                return True  # If write fails but read works, tag is likely read-only
                
        except Exception as e:
            logger.debug(f"Error in read-only test: {str(e)}")
            return False  # Default to assuming it's not read-only if test fails
    
    def _write_block_internal(self, block_number, data):
        """
        Internal method to write to a block without calling is_tag_read_only.
        This prevents infinite recursion when is_tag_read_only calls this method.
        
        Args:
            block_number (int): Block number to write
            data (bytes): Data to write (must be 16 bytes)
            
        Returns:
            bool: True if write successful
            
        Raises:
            NFCNoTagError: If no tag is present
            NFCWriteError: If writing fails
        """
        # Verify data length
        if not data or len(data) != 16:
            raise NFCWriteError("Data length must be exactly 16 bytes")
        
        tag_type = self.detect_tag_type()
        
        # Special handling for NTAG215 tags
        if tag_type == "ntag215":
            start_page = block_number * 4
            
            # NTAG215 has pages 0-134, with some reserved
            # Pages 0-4: Reserved (manufacturer, serial number, etc.)
            # Pages 5-130: User data (504 bytes)
            # Pages 131-134: Configuration and lock bytes
            
            if start_page < 4:
                raise NFCWriteError(f"Cannot write to NTAG215 pages {start_page}-{start_page+3} (reserved pages)")
            
            if start_page > 130:
                raise NFCWriteError(f"Cannot write to NTAG215 pages {start_page}-{start_page+3} (beyond user memory)")
            
            # Write 4 pages (4 bytes each) for a 16-byte block
            success = True
            for i in range(4):
                page = start_page + i
                page_data = data[i*4:(i+1)*4]
                
                if page <= 130:  # Only write to valid user memory pages
                    try:
                        self._pn532.ntag2xx_write_block(page, page_data)
                        logger.debug(f"Successfully wrote data to NTAG215 page {page}")
                    except Exception as e:
                        success = False
                        logger.error(f"Failed to write to NTAG215 page {page}: {str(e)}")
                        # Continue to try other pages
            
            if success:
                logger.info(f"Successfully wrote data to NTAG215 block {block_number} (pages {start_page}-{start_page+3})")
                return True
            else:
                raise NFCWriteError(f"Failed to write all pages for NTAG215 block {block_number}")
        
        # Try standard NTAG2xx write (works for some tags)
        try:
            self._pn532.ntag2xx_write_block(block_number, data[:4])  # Only write first 4 bytes
            logger.info(f"Successfully wrote data to block {block_number} as NTAG/Ultralight (first 4 bytes)")
            return True
        except Exception as e:
            logger.debug(f"NTAG write attempt failed: {str(e)}, trying as MIFARE")
        
        # Try as MIFARE Classic
        try:
            # Authenticate before writing - MIFARE blocks require authentication
            # Calculate the sector (each sector has 4 blocks)
            sector = block_number // 4
            
            # Try both key A and key B with factory defaults
            keys = [
                (0x60, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),  # Key A default
                (0x61, [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]),  # Key B default
                (0x60, [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7]),  # Another common Key A
                (0x60, [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5])   # Another common Key A
            ]
            
            auth_success = False
            for key_type, key in keys:
                try:
                    auth_result = self._pn532.mifare_classic_authenticate_block(
                        self._last_tag_uid, block_number, key_type, key
                    )
                    if auth_result:
                        auth_success = True
                        logger.debug(f"Authentication succeeded with key_type {key_type}")
                        break
                except Exception as auth_e:
                    logger.debug(f"Authentication attempt failed: {str(auth_e)}")
                    continue
            
            if not auth_success:
                raise NFCWriteError(f"All authentication attempts failed for block {block_number}")
            
            # Write data to the specified block
            self._pn532.mifare_classic_write_block(block_number, data)
            logger.info(f"Successfully wrote data to block {block_number} as MIFARE Classic")
            return True
            
        except Exception as mifare_e:
            logger.debug(f"MIFARE write attempt failed: {str(mifare_e)}")
            
        # As a last resort, try a direct block write without specifying tag type
        try:
            # This is a generic command to write a block
            # Using raw commands as a fallback
            command = bytearray([0x40])  # InDataExchange command
            command.extend([0xA0, block_number])  # MIFARE Write command + block number
            command.extend(data)  # Add the data to write
            
            logger.debug(f"Trying direct block write for block {block_number}")
            response = self._pn532._write_frame(command)
            
            if response:
                logger.info(f"Successfully wrote data to block {block_number} using direct write")
                return True
            else:
                raise NFCWriteError("No response from direct write command")
        except Exception as direct_e:
            logger.debug(f"Direct write attempt failed: {str(direct_e)}")
        
        # If we got here, all write attempts failed
        raise NFCWriteError(f"All write methods failed for block {block_number}")
    
    def write_block(self, block_number, data):
        """
        Write data to a block on the currently detected tag.

        Args:
            block_number (int): Block number to write
            data (bytes): Data to write (must be 16 bytes)

        Returns:
            bool: True if write successful
            
        Raises:
            NFCNoTagError: If no tag is present
            NFCWriteError: If writing fails
        """
        if not self._connected or not self._pn532:
            raise NFCHardwareError("Not connected to NFC hardware")
            
        if not self._last_tag_uid:
            # Try polling first to see if there's a tag
            if not self.poll():
                raise NFCNoTagError("No NFC tag detected")
        
        # Check if the tag is read-only
        if self.is_tag_read_only():
            # Use our specialized exception for read-only tags
            raise NFCTagNotWritableError("Tag appears to be read-only or write-protected")
        
        try:
            return self._write_block_internal(block_number, data)
            
        except Exception as e:
            error_msg = f"Error writing to block {block_number}: {str(e)}"
            logger.error(error_msg)
            raise NFCWriteError(error_msg)

    def authenticate(self, block_number, key_type='A', key=b'\xFF\xFF\xFF\xFF\xFF\xFF'):
        """
        Authenticate with a MIFARE tag before reading/writing protected blocks.
        
        Args:
            block_number (int): Block number to authenticate
            key_type (str): Type of key ('A' or 'B')
            key (bytes): 6-byte authentication key
            
        Returns:
            bool: True if authentication successful
            
        Raises:
            NFCNoTagError: If no tag is present
            NFCAuthenticationError: If authentication fails
        """
        if not self._connected or not self._pn532:
            raise NFCHardwareError("Not connected to NFC hardware")
            
        if not self._last_tag_uid:
            # Try polling first to see if there's a tag
            if not self.poll():
                raise NFCNoTagError("No NFC tag detected")
        
        # Verify key
        if not key or len(key) != 6:
            raise NFCAuthenticationError("Authentication key must be exactly 6 bytes")
        
        try:
            # Authenticate the block
            auth_method = 0x60 if key_type.upper() == 'A' else 0x61  # 0x60 = auth with key A, 0x61 = auth with key B
            
            # Convert key to list if it's bytes
            key_list = list(key) if isinstance(key, bytes) else key
            
            result = self._pn532.mifare_classic_authenticate_block(
                self._last_tag_uid, block_number, auth_method, key_list
            )
            
            if result:
                logger.info(f"Successfully authenticated for block {block_number}")
                return True
                
            logger.error("Authentication failed")
            raise NFCAuthenticationError(f"Authentication failed for block {block_number}")
            
        except NFCNoTagError:
            # Re-raise no tag error
            raise
        except NFCAuthenticationError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            error_msg = f"Error during authentication: {str(e)}"
            logger.error(error_msg)
            raise NFCAuthenticationError(error_msg)
