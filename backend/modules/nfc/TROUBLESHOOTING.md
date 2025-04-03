# Troubleshooting NFC Module Setup

This document covers common issues and solutions when setting up the NFC module on Raspberry Pi.

## Package Installation Issues

### Package Lock Problems

If you see errors like:

```
E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process XXX (unattended-upgr)
```

This means the system's automatic update process is running. You have several options:

1. **Wait for it to finish**

   - The unattended-upgrade process usually completes within 5-10 minutes
   - You can check its status with: `ps -p PROCESS_ID -o cmd=`

2. **Check if it's actually doing something**:

   ```bash
   sudo lsof /var/lib/dpkg/lock-frontend
   ```

3. **Wait with notification when it's done**:

   ```bash
   while sudo fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do
     echo "Waiting for package manager to release lock..."
     sleep 10
   done
   echo "Package manager lock released, proceeding with installation"
   ```

4. **If it's hung and you need to force it (use with caution)**:

   ```bash
   # First identify the process
   ps aux | grep unattended

   # Then stop it (replace PID with actual process ID)
   sudo kill PID

   # If lock files remain, remove them
   sudo rm /var/lib/apt/lists/lock
   sudo rm /var/lib/dpkg/lock-frontend
   sudo rm /var/lib/dpkg/lock

   # Then clean up and reconfigure packages
   sudo dpkg --configure -a
   sudo apt-get update
   ```

## I2C Issues

### I2C Not Detecting NFC Hardware

If `i2cdetect -y 1` doesn't show your NFC device:

1. **Check Hardware Connections**

   - Ensure the NFC HAT is properly seated on the GPIO pins
   - Check for bent or damaged pins
   - Verify power connections

2. **Verify I2C Address**

   - The default address for most NFC HATs is 0x24, but it might be different
   - Check the documentation for your specific NFC hardware
   - Try scanning both I2C buses: `i2cdetect -y 0` and `i2cdetect -y 1`

3. **Confirm I2C is Properly Enabled**

   ```bash
   # Check if i2c-dev module is loaded
   lsmod | grep i2c_dev

   # If not loaded, load it
   sudo modprobe i2c-dev
   ```

4. **Reboot the Raspberry Pi**
   Sometimes a simple reboot resolves I2C detection issues:
   ```bash
   sudo reboot
   ```

## Python and Module Issues

### ModuleNotFoundError for Adafruit Libraries

If you see errors like `ModuleNotFoundError: No module named 'adafruit_pn532'` or `No module named 'board'`:

1. **Install the required libraries**:

   ```bash
   sudo pip3 install adafruit-circuitpython-pn532 adafruit-blinka RPi.GPIO
   ```

2. **Check if they're installed correctly**:

   ```bash
   pip3 list | grep adafruit
   ```

3. **For board/busio errors**:
   Make sure adafruit-blinka is installed, as it provides these modules:
   ```bash
   sudo pip3 install adafruit-blinka
   ```

### Permission Issues

If you get permission errors when accessing I2C:

1. **Add user to i2c group** (then log out and back in):

   ```bash
   sudo usermod -a -G i2c $USER
   ```

2. **Run the script with sudo** (temporary workaround):
   ```bash
   sudo python3 test_nfc.py
   ```

## Hardware-Specific Issues

### MFRC522 NFC HAT

If you're using the common MFRC522 NFC HAT:

1. **SPI vs I2C**

   - Some MFRC522 HATs use SPI rather than I2C
   - In this case, you'll need to enable SPI instead through raspi-config
   - The hardware_interface.py file would need to be modified to use SPI

2. **Different Address**
   - Some HATs use address 0x28 rather than 0x24
   - Try: `python3 test_nfc.py -a 0x28`

### PN532 NFC HAT

If you're using a PN532-based HAT:

1. **UART Mode**
   - Some PN532 HATs default to UART mode, not I2C
   - Check for jumpers or switches on the HAT to set I2C mode

## Testing Tips

1. **Try a Simple Test First**

   ```bash
   python3 test_nfc.py -t hardware -v
   ```

2. **Try Different I2C Bus**

   ```bash
   python3 test_nfc.py -b 0 -t hardware
   ```

3. **Increase Verbosity**

   ```bash
   python3 -v test_nfc.py -v
   ```

4. **Trace Module Loading**
   ```bash
   python3 -v test_nfc.py 2>&1 | grep smbus
   ```

## NFC Read/Write Operation Errors

### "Received unexpected command response!"

This common error indicates a communication issue between the NFC hardware and tag:

1. **Check tag compatibility**

   - Different tag types require different commands
   - See [TAG_COMPATIBILITY.md](./TAG_COMPATIBILITY.md) for details on supported tags
   - Try using NTAG213/215/216 or MIFARE Ultralight tags which often have better compatibility

2. **Check tag placement**

   - Ensure the tag is properly centered on the NFC reader
   - Hold the tag steady during read/write operations
   - Try multiple positions if necessary

3. **Check tag integrity**

   - The tag may be damaged or have corrupted sectors
   - Try scanning with an NFC-enabled phone to verify tag is functional

4. **Lower-level debugging**

   - Run with verbose mode: `python3 test_nfc.py -v --debug`
   - Try accessing different blocks: `python3 test_nfc.py -t readwrite -b 6`
   - Some blocks (esp. sector trailers) may be protected from reading/writing

5. **Hardware configuration**
   - Try adjusting the I2C clock speed: `sudo nano /boot/config.txt` and add/modify:
     ```
     dtparam=i2c_arm=on,i2c_arm_baudrate=100000
     ```
   - Verify proper power supply to the Raspberry Pi (at least 2.5A recommended)

## Raspberry Pi 5 Specific Issues

If you're using a Raspberry Pi 5:

1. **Different I2C Bus Numbers**

   - The Pi 5 might use different I2C bus numbers
   - Try: `i2cdetect -l` to list all I2C buses

2. **Updated Driver Requirements**
   - You might need updated drivers
   - Ensure your system is fully updated: `sudo apt-get update && sudo apt-get upgrade`
