"""
hardware_interface.py - Low-level NFC reader interface for I2C communication.
"""

import time
import logging

# Create logger
logger = logging.getLogger(__name__)

# Try to import smbus2, fall back to smbus if not available
try:
    from smbus2 import SMBus
    logger.info("Using smbus2 library")
except ImportError:
    try:
        from smbus import SMBus
        logger.info("Using smbus library instead of smbus2")
    except ImportError:
        raise ImportError("Neither smbus2 nor smbus library found. Please install one: sudo pip3 install smbus2 or sudo apt-get install python3-smbus")
from .exceptions import NFCHardwareError, NFCReadError, NFCWriteError, NFCNoTagError, NFCAuthenticationError

# NFC HAT Command codes - these would need to be adjusted for the specific hardware
CMD_RESET = 0x01
CMD_VERSION = 0x02
CMD_POLL = 0x03
CMD_READ_BLOCK = 0x04
CMD_WRITE_BLOCK = 0x05
CMD_AUTHENTICATE = 0x06

# Response codes
RESP_SUCCESS = 0x00
RESP_ERROR = 0xFF
RESP_NO_TAG = 0xFE

class NFCReader:
    """
    Low-level NFC reader interface for I2C communication.

    Attributes:
        i2c_bus (int): I2C bus number
        i2c_address (int): I2C device address
        _device: SMBus device instance
    """

    def __init__(self, i2c_bus=1, i2c_address=0x24):
        """
        Initialize NFC reader with I2C parameters.

        Args:
            i2c_bus (int): I2C bus number (usually 1 on Raspberry Pi)
            i2c_address (int): I2C device address of the NFC HAT
        """
        self.i2c_bus = i2c_bus
        self.i2c_address = i2c_address
        self._device = None
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
            self._device = SMBus(self.i2c_bus)
            
            # Try to read version to confirm communication
            version = self.get_version()
            if version:
                self._connected = True
                logger.info(f"Connected to NFC hardware: {version}")
                return True
            
            # Close the bus if we couldn't communicate
            self._device.close()
            self._device = None
            logger.error("Failed to communicate with NFC hardware")
            return False
            
        except Exception as e:
            logger.error(f"Error connecting to NFC hardware: {str(e)}")
            if self._device:
                try:
                    self._device.close()
                except:
                    pass
                self._device = None
            return False

    def disconnect(self):
        """Close connection to NFC hardware."""
        if self._device:
            try:
                self._device.close()
                logger.info("Disconnected from NFC hardware")
            except Exception as e:
                logger.error(f"Error disconnecting from NFC hardware: {str(e)}")
            finally:
                self._device = None
                self._connected = False

    def reset(self):
        """Hard reset the NFC hardware."""
        if not self._connected:
            raise NFCHardwareError("Not connected to NFC hardware")
        
        try:
            self.send_command(CMD_RESET)
            time.sleep(0.1)  # Wait for reset to complete
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
        try:
            response = self.send_command(CMD_VERSION)
            if response and len(response) >= 2:
                major = response[0]
                minor = response[1]
                return f"v{major}.{minor}"
            return None
        except Exception as e:
            logger.error(f"Error getting NFC hardware version: {str(e)}")
            return None

    def send_command(self, command, params=None):
        """
        Send a command to the NFC hardware.

        Args:
            command (int): Command code
            params (bytes, optional): Command parameters

        Returns:
            bytes: Response data
            
        Raises:
            NFCHardwareError: If communication fails
        """
        if not self._device:
            raise NFCHardwareError("Not connected to NFC hardware")
        
        # Prepare command packet
        packet = bytearray([command])
        if params:
            packet.extend(params)
        
        try:
            # Write command to device
            for byte in packet:
                self._device.write_byte(self.i2c_address, byte)
                time.sleep(0.001)  # Small delay between bytes
            
            time.sleep(0.05)  # Wait for processing
            
            # Read response length
            response_length = self._device.read_byte(self.i2c_address)
            
            # If length is zero, return empty response
            if response_length == 0:
                return b''
                
            # Read response data
            response = bytearray()
            for _ in range(response_length):
                response.append(self._device.read_byte(self.i2c_address))
                time.sleep(0.001)  # Small delay between reads
            
            # Check for error response
            if response and response[0] == RESP_ERROR:
                error_code = response[1] if len(response) > 1 else 0
                error_msg = f"NFC hardware returned error: {error_code}"
                logger.error(error_msg)
                
                if error_code == RESP_NO_TAG:
                    raise NFCNoTagError("No NFC tag detected")
                    
                raise NFCHardwareError(error_msg)
                
            return bytes(response)
            
        except NFCNoTagError:
            # Re-raise specific exceptions
            raise
        except NFCHardwareError:
            # Re-raise hardware errors
            raise
        except Exception as e:
            error_msg = f"I2C communication error: {str(e)}"
            logger.error(error_msg)
            raise NFCHardwareError(error_msg)

    def poll(self):
        """
        Poll for tag presence.

        Returns:
            bytes or None: Tag UID if detected, None otherwise
        """
        try:
            response = self.send_command(CMD_POLL)
            
            # Check if a tag was found (non-empty response)
            if response and len(response) >= 4:  # UID is typically 4-7 bytes
                self._last_tag_uid = response
                return response
            
            self._last_tag_uid = None
            return None
            
        except NFCNoTagError:
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
        if not self._last_tag_uid:
            # Try polling first to see if there's a tag
            if not self.poll():
                raise NFCNoTagError("No NFC tag detected")
        
        try:
            # Send read command with block number
            params = bytearray([block_number])
            response = self.send_command(CMD_READ_BLOCK, params)
            
            if not response or len(response) < 16:
                raise NFCReadError(f"Invalid data read from block {block_number}")
                
            return response
            
        except NFCNoTagError:
            # Re-raise no tag error
            raise
        except NFCHardwareError as e:
            # Convert hardware errors during reading to NFCReadError
            raise NFCReadError(f"Hardware error while reading block {block_number}: {str(e)}")
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
        if not self._last_tag_uid:
            # Try polling first to see if there's a tag
            if not self.poll():
                raise NFCNoTagError("No NFC tag detected")
        
        # Verify data length
        if not data or len(data) != 16:
            raise NFCWriteError("Data length must be exactly 16 bytes")
        
        try:
            # Send write command with block number and data
            params = bytearray([block_number]) + bytearray(data)
            response = self.send_command(CMD_WRITE_BLOCK, params)
            
            # Check success response
            if response and response[0] == RESP_SUCCESS:
                logger.info(f"Successfully wrote data to block {block_number}")
                return True
                
            raise NFCWriteError(f"Failed to write to block {block_number}")
            
        except NFCNoTagError:
            # Re-raise no tag error
            raise
        except NFCHardwareError as e:
            # Convert hardware errors during writing to NFCWriteError
            raise NFCWriteError(f"Hardware error while writing block {block_number}: {str(e)}")
        except NFCWriteError:
            # Re-raise write errors
            raise
        except Exception as e:
            error_msg = f"Error writing to block {block_number}: {str(e)}"
            logger.error(error_msg)
            raise NFCWriteError(error_msg)

    def authenticate(self, block_number, key_type, key):
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
        if not self._last_tag_uid:
            # Try polling first to see if there's a tag
            if not self.poll():
                raise NFCNoTagError("No NFC tag detected")
        
        # Verify key
        if not key or len(key) != 6:
            raise NFCAuthenticationError("Authentication key must be exactly 6 bytes")
        
        # Key type byte (0 for A, 1 for B)
        key_type_byte = 0 if key_type.upper() == 'A' else 1
        
        try:
            # Send authenticate command with block, key type, and key
            params = bytearray([block_number, key_type_byte]) + bytearray(key)
            response = self.send_command(CMD_AUTHENTICATE, params)
            
            # Check success response
            if response and response[0] == RESP_SUCCESS:
                logger.info(f"Successfully authenticated for block {block_number}")
                return True
                
            raise NFCAuthenticationError(f"Authentication failed for block {block_number}")
            
        except NFCNoTagError:
            # Re-raise no tag error
            raise
        except NFCHardwareError as e:
            # Convert hardware errors during authentication to NFCAuthenticationError
            raise NFCAuthenticationError(f"Hardware error during authentication: {str(e)}")
        except NFCAuthenticationError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            error_msg = f"Error during authentication: {str(e)}"
            logger.error(error_msg)
            raise NFCAuthenticationError(error_msg)
