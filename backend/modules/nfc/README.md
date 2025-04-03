# NFC Module - Implementation Guide

## Overview

The NFC Module is responsible for detecting and reading NFC tags placed on the music player device. It interfaces with the NFC HAT connected to the Raspberry Pi via I2C and provides tag information to the rest of the application.

## Core Responsibilities

1. Initialize and configure the NFC reader hardware
2. Continuously poll for NFC tag presence
3. Read tag UID when detected
4. Provide clean, error-handled interfaces to other system components
5. Support diagnostic and testing capabilities

## Implementation Details

### File Structure

```
nfc/
├── __init__.py                 # Package initialization
├── nfc_controller.py           # Main controller, exposed to other modules
├── hardware_interface.py       # Low-level hardware communication
├── tag_processor.py            # Tag data extraction and processing
└── exceptions.py               # NFC-specific exception definitions
```

### Key Components

#### 1. NFC Controller (`nfc_controller.py`)

This is the main interface exposed to other modules. It should implement:

```python
def initialize():
    """
    Initialize the NFC controller and hardware.

    Returns:
        bool: True if initialization successful, False otherwise
    """

def shutdown():
    """
    Clean shutdown of NFC hardware.
    """

def poll_for_tag():
    """
    Check for presence of an NFC tag.

    Returns:
        str or None: Tag UID if detected, None otherwise
    """

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

def write_tag_data(data, block=4):
    """
    Write data to a specific block on the currently present tag.

    Args:
        data (bytes): Data to write (must be 16 bytes or less)
        block (int): Block number to write to

    Returns:
        bool: True if write successful

    Raises:
        NFCWriteError: If writing fails
        NFCNoTagError: If no tag is present
    """

def get_hardware_info():
    """
    Get information about the NFC hardware.

    Returns:
        dict: Hardware information including model, firmware version
    """
```

#### 2. Hardware Interface (`hardware_interface.py`)

This handles low-level communication with the NFC HAT. Implement:

```python
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

    def connect(self):
        """
        Establish connection to the NFC hardware.

        Returns:
            bool: True if connected successfully
        """

    def disconnect(self):
        """Close connection to NFC hardware."""

    def reset(self):
        """Hard reset the NFC hardware."""

    def send_command(self, command, params=None):
        """
        Send a command to the NFC hardware.

        Args:
            command (int): Command code
            params (bytes, optional): Command parameters

        Returns:
            bytes: Response data
        """

    def poll(self):
        """
        Poll for tag presence.

        Returns:
            bytes or None: Tag UID if detected, None otherwise
        """

    def read_block(self, block_number):
        """
        Read a data block from the currently detected tag.

        Args:
            block_number (int): Block number to read

        Returns:
            bytes: Block data (16 bytes)
        """

    def write_block(self, block_number, data):
        """
        Write data to a block on the currently detected tag.

        Args:
            block_number (int): Block number to write
            data (bytes): Data to write (must be 16 bytes)

        Returns:
            bool: True if write successful
        """
```

#### 3. Tag Processor (`tag_processor.py`)

This handles processing and formatting of tag data:

```python
def format_uid(raw_uid):
    """
    Format raw UID bytes to a standardized string format.

    Args:
        raw_uid (bytes): Raw UID from NFC reader

    Returns:
        str: Formatted UID string (hex format, uppercase)
    """

def parse_ndef_data(data):
    """
    Parse NDEF formatted data from tag.

    Args:
        data (bytes): Raw data read from tag

    Returns:
        dict: Parsed NDEF message and records
    """

def create_ndef_data(url=None, text=None):
    """
    Create NDEF formatted data for writing to tag.

    Args:
        url (str, optional): URL to encode
        text (str, optional): Text to encode

    Returns:
        bytes: NDEF formatted data ready for writing
    """
```

#### 4. Exceptions (`exceptions.py`)

Define custom exceptions for NFC operations:

```python
class NFCError(Exception):
    """Base exception for all NFC related errors."""
    pass

class NFCHardwareError(NFCError):
    """Exception raised when there's a hardware communication error."""
    pass

class NFCNoTagError(NFCError):
    """Exception raised when an operation requires a tag but none is present."""
    pass

class NFCReadError(NFCError):
    """Exception raised when tag reading fails."""
    pass

class NFCWriteError(NFCError):
    """Exception raised when tag writing fails."""
    pass

class NFCAuthenticationError(NFCError):
    """Exception raised when tag authentication fails."""
    pass
```

### Hardware Integration

For an I2C-based NFC reader, follow these guidelines:

1. **Hardware Detection**:

   - On initialization, scan the I2C bus for the configured address
   - Implement robust error handling for cases where hardware is not found
   - Support configurable I2C bus and address via configuration file

2. **I2C Communication**:

   - Use the `smbus2` library for I2C communication
   - Implement appropriate delay between commands (usually 50-100ms)
   - Handle I2C bus errors gracefully

3. **Reader Configuration**:

   - Configure the reader for ISO14443A (MIFARE) tag detection
   - Set appropriate RF field strength
   - Implement automatic retries for intermittent failures

4. **NFC HAT Specifics**:
   - Adapt the protocol based on the specific NFC HAT model
   - Implement any required initialization sequences
   - Handle any hardware-specific quirks

### Performance Considerations

1. **Polling Frequency**:

   - Default to 100ms (10 Hz) polling rate
   - Make this configurable via the configuration file
   - Ensure it's not too aggressive to avoid excessive CPU usage

2. **Power Management**:

   - Implement low-power modes when possible
   - Consider reducing field strength when not actively reading

3. **Concurrency**:
   - Ensure thread safety for all operations
   - Use locks when accessing I2C bus to prevent concurrent access

### Error Handling and Resilience

1. **Hardware Failures**:

   - Implement automatic recovery for transient errors
   - Attempt hardware reset after consecutive failures
   - Log detailed diagnostics for persistent issues

2. **Tag Reading Issues**:

   - Handle partial reads and corrupted data
   - Implement read retries (3x) before reporting failure
   - Validate data using checksums when available

3. **System Integration**:
   - Provide clear error messages for higher-level components
   - Ensure that NFC failures don't crash the entire application
   - Support a diagnostic mode for troubleshooting

### Security Considerations

1. **Tag Authentication**:

   - Implement support for MIFARE authentication if using secured tags
   - Store keys securely, not in plain text

2. **Data Validation**:
   - Always validate data read from tags before processing
   - Be cautious about buffer lengths to prevent overflow

### Testing

1. **Hardware Testing**:

   - Develop a test script that validates basic hardware functionality
   - Test with various tag types to ensure compatibility

2. **Mock Testing**:

   - Create a mock interface for testing without hardware
   - Implement hardware simulation for automated testing

3. **Integration Testing**:
   - Test with the database module to verify uid lookup
   - Verify proper error propagation to higher-level modules

## Common Issues and Solutions

1. **Tag Not Detected**:

   - Check I2C address configuration
   - Ensure proper power to the NFC HAT
   - Try adjusting the polling interval
   - Verify the tag is compatible (ISO14443A/MIFARE)

2. **Intermittent Readings**:

   - Implement debouncing logic
   - Check for interference from other devices
   - Try increasing the field strength

3. **Slow Detection**:
   - Optimize the polling interval
   - Check for unnecessary operations in the polling loop
   - Consider using interrupt-based detection if hardware supports it

## Resources and References

1. **I2C Documentation**:

   - [Raspberry Pi I2C Documentation](https://www.raspberrypi.org/documentation/hardware/raspberrypi/i2c/README.md)
   - [smbus2 Library Documentation](https://pypi.org/project/smbus2/)

2. **NFC Standards**:

   - ISO/IEC 14443 (RFID proximity cards)
   - MIFARE Classic specification

3. **Sample Code and Libraries**:
   - [libnfc](http://nfc-tools.org/index.php/Libnfc)
   - [MFRC522 Python library](https://github.com/pimylifeup/MFRC522-python)
