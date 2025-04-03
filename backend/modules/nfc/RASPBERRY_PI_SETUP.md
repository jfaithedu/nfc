# Setting Up NFC Module on Raspberry Pi

This document provides step-by-step instructions for setting up and testing the NFC module on a Raspberry Pi.

## Prerequisites

- Raspberry Pi (any model) with Raspberry Pi OS
- NFC HAT or shield connected to the Pi via I2C
- Internet connection on the Pi (for installing packages)

## Setup Steps

1. **Install Required Packages**

   First, make sure your system is up to date and has the required packages:

   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-smbus i2c-tools libgpiod2
   ```

2. **Enable I2C Interface**

   If not already enabled:

   ```bash
   sudo raspi-config
   ```

   Navigate to "Interfacing Options" > "I2C" and select "Yes" to enable the I2C interface.

3. **Install Python Dependencies**

   Install the required Python packages:

   ```bash
   sudo pip3 install adafruit-circuitpython-pn532 adafruit-blinka RPi.GPIO
   ```

4. **Verify I2C Connection**

   Check if your NFC hardware is detected on the I2C bus:

   ```bash
   sudo i2cdetect -y 1
   ```

   Look for a detected device (usually at address 0x24 or similar).

5. **Add User to I2C Group**

   To allow running the test script without sudo:

   ```bash
   sudo usermod -a -G i2c $USER
   ```

   You may need to log out and log back in for this to take effect.

## Running the Tests

1. **Basic Hardware Detection Test**

   This will check if the Pi can communicate with the NFC hardware:

   ```bash
   cd /path/to/nfc/backend/modules/nfc
   python3 test_nfc.py -t hardware
   ```

2. **Tag Detection Test**

   This will poll for an NFC tag for a specified duration:

   ```bash
   python3 test_nfc.py -t detect -d 5
   ```

   Place an NFC tag on the reader when prompted.

3. **Run All Tests**

   To run all tests:

   ```bash
   python3 test_nfc.py
   ```

## Troubleshooting

If you encounter issues:

1. **Ensure I2C is enabled properly**

   ```bash
   ls -l /dev/i2c*
   ```

   You should see at least one I2C device (e.g., /dev/i2c-1).

2. **Check I2C permissions**

   ```bash
   groups
   ```

   Ensure that 'i2c' is listed in your groups.

3. **Verify all required dependencies are installed**

   ```bash
   pip3 list | grep smbus2
   ```

   You should see smbus2 listed.

4. **Check for hardware-specific issues**

   Make sure the connections between the NFC HAT and the Raspberry Pi are secure.

## NFC Module Integration

After successful testing, you can integrate the NFC module with the rest of your application by importing and using the API functions:

```python
from modules.nfc import initialize, poll_for_tag, read_tag_data, shutdown

# Initialize NFC hardware
initialize()

# Poll for tag
uid = poll_for_tag()
if uid:
    print(f"Tag detected: {uid}")

# Clean up
shutdown()
```

For continuous tag detection, use the continuous_poll function with a callback.
