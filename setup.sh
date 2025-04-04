#!/bin/bash
# Comprehensive setup script for the entire NFC project
# Sets up both backend (Python) and frontend (React)

set -e  # Exit on error

echo "============================================================="
echo "                NFC Project Setup Script                     "
echo "============================================================="

# Get absolute path to project root
PROJECT_ROOT="$(pwd)"
echo "Project root directory: $PROJECT_ROOT"

# Function to check if script is running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root (use sudo)"
        exit 1
    fi
}

# Function to create virtual environment and install dependencies
setup_python_venv() {
    echo -e "\n[1/5] Setting up Python virtual environment..."
    
    # Remove existing venv if present
    if [ -d "$PROJECT_ROOT/venv" ]; then
        echo "Removing existing virtual environment..."
        rm -rf "$PROJECT_ROOT/venv"
    fi
    
    # Create virtual environment with system packages
    echo "Creating new virtual environment with system packages..."
    python3 -m venv "$PROJECT_ROOT/venv" --system-site-packages
    
    # Activate virtual environment
    echo "Activating virtual environment..."
    source "$PROJECT_ROOT/venv/bin/activate"
    
    # Upgrade pip
    echo "Upgrading pip..."
    pip install --upgrade pip
    
    # Install Python dependencies for all modules
    echo "Installing Python dependencies for all modules..."
    pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    pip install -r "$PROJECT_ROOT/backend/modules/audio/requirements.txt"
    pip install -r "$PROJECT_ROOT/backend/modules/nfc/requirements.txt"
    
    # Make test scripts executable
    chmod +x "$PROJECT_ROOT/backend/modules/audio/interactive_test.py"
    chmod +x "$PROJECT_ROOT/backend/modules/audio/test_imports.py"
    chmod +x "$PROJECT_ROOT/backend/modules/nfc/test_nfc.py"
    
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/venv"
        chown $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/backend/modules/audio/interactive_test.py"
        chown $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/backend/modules/audio/test_imports.py"
        chown $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/backend/modules/nfc/test_nfc.py"
    fi
    
    echo "Python virtual environment set up successfully"
}

# Function to configure audio system
setup_audio_system_deps() {
    echo -e "\n[2/5] Configuring audio module..."
    
    # Configure BlueALSA
    echo "Configuring BlueALSA..."
    if [ ! -f /etc/systemd/system/bluealsa.service ]; then
        cat > /etc/systemd/system/bluealsa.service << EOF
[Unit]
Description=BlueALSA service
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/bin/bluealsa -p a2dp-sink -p a2dp-source
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    fi
    
    # Enable and start BlueALSA
    systemctl daemon-reload
    systemctl enable bluealsa
    systemctl restart bluealsa
    
    # Configure Bluetooth
    echo "Configuring Bluetooth..."
    systemctl enable bluetooth
    systemctl start bluetooth
    
    # Add current user to bluetooth group
    usermod -a -G bluetooth $SUDO_USER
    
    # Configure Bluetooth to be discoverable
    sed -i 's/#DiscoverableTimeout = 0/DiscoverableTimeout = 0/' /etc/bluetooth/main.conf
    sed -i 's/#Discoverable = false/Discoverable = true/' /etc/bluetooth/main.conf
    
    # Restart Bluetooth service to apply changes
    systemctl restart bluetooth
    
    # Setup test sound files
    SOUNDS_DIR="$PROJECT_ROOT/sounds"
    mkdir -p $SOUNDS_DIR
    
    # Create test sound files using sox
    sox -n -r 44100 -c 2 $SOUNDS_DIR/error.wav synth 0.5 sine 400 vol 0.5
    sox -n -r 44100 -c 2 $SOUNDS_DIR/success.wav synth 0.5 sine 800 vol 0.5
    sox -n -r 44100 -c 2 $SOUNDS_DIR/info.wav synth 0.5 sine 600 vol 0.5
    sox -n -r 44100 -c 2 $SOUNDS_DIR/warning.wav synth 0.5 sine 300 vol 0.5
    
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER $SOUNDS_DIR
    fi
    
    echo "Audio module system setup completed"
}

# Function to setup the NFC module system dependencies
setup_nfc_system_deps() {
    echo -e "\n[3/5] Configuring NFC module..."
    
    # Setup GPIO and I2C access permissions
    if ! grep -q "^SUBSYSTEM==\"gpio\", GROUP=\"gpio\"" /etc/udev/rules.d/99-com.rules 2>/dev/null; then
        bash -c 'cat > /etc/udev/rules.d/99-com.rules << EOF
# I2C permissions
SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0660"
# GPIO permissions
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
SUBSYSTEM=="gpio*", PROGRAM="/bin/sh -c '\''chown -R root:gpio /sys/class/gpio && chmod -R 770 /sys/class/gpio; chown -R root:gpio /sys/devices/virtual/gpio && chmod -R 770 /sys/devices/virtual/gpio; chown -R root:gpio /sys/devices/platform/soc/*.gpio/gpio && chmod -R 770 /sys/devices/platform/soc/*.gpio/gpio'\''", TAG+="systemd", OWNER="root", GROUP="gpio", MODE="0660"
# SPI permissions
SUBSYSTEM=="spidev", GROUP="spi", MODE="0660"
EOF'
        udevadm control --reload-rules
        udevadm trigger
    fi
    
    # Create necessary groups if they don't exist
    for group in gpio i2c spi; do
        if ! grep -q "^$group:" /etc/group; then
            groupadd -f $group
        fi
        
        # Add user to group
        if ! groups $SUDO_USER | grep -q "\b$group\b"; then
            usermod -a -G $group $SUDO_USER
        fi
    done
    
    # Enable I2C if not already enabled
    REBOOT_REQUIRED=false
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "Enabling I2C in /boot/config.txt..."
        bash -c "echo 'dtparam=i2c_arm=on' >> /boot/config.txt"
        REBOOT_REQUIRED=true
    fi
    
    # Check if i2c-dev is loaded
    if ! lsmod | grep -q "i2c_dev"; then
        modprobe i2c-dev
        # Add to modules to load at boot
        if ! grep -q "^i2c-dev" /etc/modules; then
            bash -c "echo 'i2c-dev' >> /etc/modules"
        fi
    fi
    
    echo "NFC module system setup completed"
    
    if [ "$REBOOT_REQUIRED" = true ]; then
        echo "⚠️  I2C was enabled in config.txt. A reboot will be required after setup completes."
    fi
}

# Function to setup frontend dependencies
setup_frontend() {
    echo -e "\n[4/5] Setting up frontend..."
    
    # Install Node.js dependencies
    cd "$PROJECT_ROOT/frontend"
    
    echo "Installing frontend dependencies..."
    npm install
    
    # Return to project root
    cd "$PROJECT_ROOT"
    
    # Set proper ownership if running as sudo
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/frontend"
    fi
    
    echo "Frontend setup completed"
}

# Function to verify the setup
verify_setup() {
    echo -e "\n[5/5] Verifying setup..."
    
    # Verify Python virtual environment
    if [ -d "$PROJECT_ROOT/venv" ]; then
        echo "✅ Python virtual environment exists"
    else
        echo "❌ Python virtual environment does not exist"
    fi
    
    # Verify audio setup
    if systemctl is-active --quiet bluetooth && systemctl is-active --quiet bluealsa; then
        echo "✅ Bluetooth audio services are running"
    else
        echo "❌ Bluetooth audio services are not running properly"
    fi
    
    # Verify I2C setup
    if grep -q "^dtparam=i2c_arm=on" /boot/config.txt && lsmod | grep -q "i2c_dev"; then
        echo "✅ I2C is properly configured"
    else
        echo "❌ I2C is not properly configured"
    fi
    
    # Check frontend dependencies
    if [ -d "$PROJECT_ROOT/frontend/node_modules" ]; then
        echo "✅ Frontend dependencies are installed"
    else
        echo "❌ Frontend dependencies are not installed"
    fi
    
    echo "Setup verification completed"
}

# Main function
main() {
    echo "Starting comprehensive project setup..."
    
    # Update package lists first
    echo "Updating package lists..."
    apt-get update
    
    # Install Cairo and core dependencies first to fix pip build issues
    echo "Installing Cairo and core dependencies first..."
    apt-get install -y --no-install-recommends \
        libcairo2-dev \
        pkg-config \
        python3-dev \
        libgirepository1.0-dev \
        python3-cairo \
        python3-gi \
        python3-cairo-dev \
        libcairo-gobject2

    # Run ldconfig to ensure library cache is updated
    ldconfig
    
    # Install all remaining system dependencies
    echo "Installing remaining system dependencies..."
    apt-get install -y --no-install-recommends \
        gir1.2-gtk-3.0 \
        bluetooth \
        bluez \
        bluez-tools \
        pi-bluetooth \
        bluealsa \
        dbus \
        python3-dbus \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-alsa \
        python3-gst-1.0 \
        gir1.2-gstreamer-1.0 \
        gir1.2-gst-plugins-base-1.0 \
        alsa-utils \
        sox \
        python3-pip \
        python3-smbus \
        i2c-tools \
        python3-venv \
        python3-full \
        libgpiod2 \
        nodejs \
        npm
    
    # Setup Python virtual environment
    setup_python_venv
    
    # Setup audio system dependencies
    setup_audio_system_deps
    
    # Setup NFC system dependencies
    setup_nfc_system_deps
    
    # Setup frontend
    setup_frontend
    
    # Verify setup
    verify_setup
    
    echo -e "\n============================================================="
    echo "                  Setup Completed Successfully                  "
    echo "============================================================="
    echo
    echo "To use the project:"
    echo
    echo "1. Start the backend:"
    echo "   source venv/bin/activate"
    echo "   python backend/app.py"
    echo
    echo "2. Start the frontend (in a separate terminal):"
    echo "   cd frontend"
    echo "   npm run dev"
    echo
    
    # Provide warning about reboot if needed
    if [ "$REBOOT_REQUIRED" = true ]; then
        echo "⚠️  I2C was enabled in config.txt. Please reboot before using NFC features:"
        echo "    sudo reboot"
        echo
        echo "Do you want to reboot now? (y/N): "
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            echo "Rebooting..."
            reboot
        fi
    fi
    
    echo "You can run tests for individual modules:"
    echo
    echo "Audio module tests:"
    echo "    source venv/bin/activate && python backend/modules/audio/test_audio.py"
    echo
    echo "NFC module tests:"
    echo "    source venv/bin/activate && python -m backend.modules.nfc.test_nfc"
    echo
    echo "To test Bluetooth audio playback:"
    echo "    source venv/bin/activate && python backend/modules/audio/interactive_test.py"
    echo
    echo "For troubleshooting, refer to documentation in the respective module folders."
    echo "============================================================="
}

# Check if running as root
check_root

# Execute main function
main "$@"
