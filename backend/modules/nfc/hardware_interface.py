"""
hardware_interface.py - Low-level NFC reader interface using Adafruit PN532 library.
"""

import time
import logging
import board
import busio
from adafruit_pn532.i2c import PN532_I2C
from .exceptions import NFCHardwareError, NFCReadError, NFCWriteError, NFCNoTagError, NFCAuthenticationError

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
        
        try:
            # First try to read directly without authentication (for NTAG/Ultralight tags)
            # These tags don't require authentication for reading
            try:
                data = self._pn532.ntag2xx_read_block(block_number)
                if data and len(data) == 16:
                    logger.debug(f"Read block {block_number} as NTAG/Ultralight")
                    return bytes(data)
            except Exception as e:
                logger.debug(f"NTAG read attempt failed: {str(e)}, trying as MIFARE")
            
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
        
        # Verify data length
        if not data or len(data) != 16:
            raise NFCWriteError("Data length must be exactly 16 bytes")
        
        try:
            # First try as NTAG/Ultralight
            try:
                self._pn532.ntag2xx_write_block(block_number, data)
                logger.info(f"Successfully wrote data to block {block_number} as NTAG/Ultralight")
                return True
            except Exception as e:
                logger.debug(f"NTAG write attempt failed: {str(e)}, trying as MIFARE")
            
            # Try as MIFARE Classic if NTAG fails
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
                # Fall through to the final error
            
            # If we got here, all write attempts failed
            raise NFCWriteError(f"All write methods failed for block {block_number}")
            
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
