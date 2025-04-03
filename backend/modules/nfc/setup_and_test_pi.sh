#!/bin/bash
# Setup and test script for NFC module on Raspberry Pi

# Print header
echo "============================================================="
echo "              NFC Module Setup and Test Script               "
echo "============================================================="

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
  echo "⚠️  Warning: This script is intended to run on Raspberry Pi."
  echo "Continuing anyway, but some operations might fail."
fi

# Install required system packages
echo -e "\n[1/4] Installing required system packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-smbus i2c-tools python3-venv python3-full libgpiod2 &&  echo "Packages installed successfully"

# Setup GPIO and I2C access permissions
echo "Setting up GPIO and I2C permissions..."
if ! grep -q "^SUBSYSTEM==\"gpio\", GROUP=\"gpio\"" /etc/udev/rules.d/99-com.rules 2>/dev/null; then
  sudo bash -c 'cat > /etc/udev/rules.d/99-com.rules << EOF
# I2C permissions
SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0660"
# GPIO permissions
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
SUBSYSTEM=="gpio*", PROGRAM="/bin/sh -c '\''chown -R root:gpio /sys/class/gpio && chmod -R 770 /sys/class/gpio; chown -R root:gpio /sys/devices/virtual/gpio && chmod -R 770 /sys/devices/virtual/gpio; chown -R root:gpio /sys/devices/platform/soc/*.gpio/gpio && chmod -R 770 /sys/devices/platform/soc/*.gpio/gpio'\''", TAG+="systemd", OWNER="root", GROUP="gpio", MODE="0660"
# SPI permissions
SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"
EOF'
  echo "Created GPIO/I2C/SPI permissions file"
  sudo udevadm control --reload-rules
  sudo udevadm trigger
else
  echo "GPIO/I2C/SPI permissions file already exists"
fi

# Create necessary groups if they don't exist
for group in gpio i2c spi; do
  if ! grep -q "^$group:" /etc/group; then
    sudo groupadd -f $group
    echo "Created $group group"
  fi
  
  # Add user to group
  if ! groups $USER | grep -q "\b$group\b"; then
    sudo usermod -a -G $group $USER
    echo "Added user to $group group"
  fi
done

# Enable I2C if not already enabled
echo -e "\n[2/4] Checking I2C configuration..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
  echo "Enabling I2C in /boot/config.txt..."
  sudo bash -c "echo 'dtparam=i2c_arm=on' >> /boot/config.txt"
  echo "I2C enabled. A reboot will be required after this script completes."
  REBOOT_REQUIRED=true
else
  echo "I2C already enabled in /boot/config.txt"
fi

# Check if i2c-dev is loaded
if ! lsmod | grep -q "i2c_dev"; then
  echo "Loading i2c-dev module..."
  sudo modprobe i2c-dev
  # Add to modules to load at boot
  if ! grep -q "^i2c-dev" /etc/modules; then
    sudo bash -c "echo 'i2c-dev' >> /etc/modules"
  fi
else
  echo "i2c-dev module already loaded"
fi

# Check if the user has permissions for I2C devices
echo -e "\nChecking I2C permissions..."
if ! groups | grep -q i2c; then
  echo "Adding user to the i2c group for permissions..."
  sudo usermod -a -G i2c $USER
  echo "⚠️  You will need to log out and log back in for the I2C permissions to take effect."
  echo "Alternatively, you can run the test script with sudo for now."
  I2C_PERMISSION_FIXED=true
else
  echo "User already has I2C permissions"
fi

# Setup virtual environment
echo -e "\n[3/4] Setting up Python virtual environment..."
# Get project root directory (assuming backend/modules/nfc is the current script location)
PROJECT_ROOT=$(realpath "$(dirname "$0")/../../../")
VENV_PATH="$PROJECT_ROOT/venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
  echo "Creating virtual environment at $VENV_PATH"
  python3 -m venv "$VENV_PATH"
else
  echo "Virtual environment already exists at $VENV_PATH"
fi

# Activate virtual environment and install dependencies
echo "Installing required Python packages in virtual environment..."
source "$VENV_PATH/bin/activate"
pip install --upgrade pip
pip install -r "$(dirname "$0")/requirements.txt"
echo "Python packages installed successfully in virtual environment"

# Run I2C detection
echo -e "\n[4/4] Detecting I2C devices..."
echo "Available I2C busses:"
ls -l /dev/i2c-*

echo -e "\nScanning I2C devices on bus 1:"
sudo i2cdetect -y 1

# Provide instructions for testing
echo -e "\n============================================================="
echo "                       Setup Complete                          "
echo "============================================================="

if [ "$REBOOT_REQUIRED" = true ]; then
  echo -e "\n⚠️  I2C was enabled in config.txt. Please reboot before testing:"
  echo "    sudo reboot"
  echo -e "\nAfter rebooting, run the test script with:"
else
  echo -e "\nYou can now run the test script with:"
fi

echo "    source $VENV_PATH/bin/activate && python -m backend.modules.nfc.test_nfc"
echo
echo "Options:"
echo "    -b, --bus BUS        I2C bus number (default: 1)"
echo "    -a, --address ADDR   I2C device address (default: 0x24)"
echo "    -t, --test TEST      Test to run (hardware|detect|readwrite|ndef|poll|all)"
echo "    -d, --duration SEC   Duration for polling tests (default: 10)"
echo "    -v, --verbose        Enable verbose logging"
echo
echo "Example:"
echo "    source $VENV_PATH/bin/activate && python -m backend.modules.nfc.test_nfc -t detect -d 5"
echo
echo "See test_nfc.py --help for more details"
echo "============================================================="

if [ "$REBOOT_REQUIRED" = true ]; then
  echo -e "\nDo you want to reboot now? (y/N): "
  read -r response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "Rebooting..."
    sudo reboot
  else
    echo "Remember to reboot before testing the NFC module."
  fi
fi
