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
            # Read data from the specified block
            data = self._pn532.mifare_classic_read_block(block_number)
            
            if not data or len(data) != 16:
                raise NFCReadError(f"Invalid data read from block {block_number}")
                
            return bytes(data)
            
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
            # Write data to the specified block
            self._pn532.mifare_classic_write_block(block_number, data)
            logger.info(f"Successfully wrote data to block {block_number}")
            return True
            
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
