#!/bin/bash
# Comprehensive setup script for the entire NFC project
# Sets up both backend (Python) and frontend (React)

set -e  # Exit on error

# --- Configuration ---
# Default start step
start_step=1
total_steps=5
skip_prereqs=false

# --- Argument Parsing ---
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --start-step)
            if [[ "$2" =~ ^[1-9][0-9]*$ ]] && [ "$2" -le $total_steps ]; then
                start_step="$2"
                echo "Starting setup from step $start_step."
                shift # past argument
            else
                echo "Error: --start-step requires a valid number between 1 and $total_steps." >&2
                exit 1
            fi
            ;;
        --skip-prereqs)
            skip_prereqs=true
            echo "Skipping prerequisite system package installation."
            ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift # past argument or value
done


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

# Function to create virtual environment and install dependencies (Step 1)
setup_python_venv() {
    echo -e "\n[1/$total_steps] Setting up Python virtual environment..."

    VENV_DIR="$PROJECT_ROOT/venv"

    if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        echo "Found existing virtual environment at $VENV_DIR."
    else
        echo "No valid virtual environment found. Creating new one..."
        # Remove potentially incomplete venv if activation script is missing
        if [ -d "$VENV_DIR" ]; then
            echo "Removing incomplete venv directory..."
            rm -rf "$VENV_DIR"
        fi
        # Create virtual environment WITH system packages to use system's python3-gi
        echo "Creating new virtual environment (with system packages)..."
        # Make sure python3-venv and python3-full are installed for proper venv creation
        apt-get install -y python3-venv python3-full
        python3 -m venv "$VENV_DIR" --system-site-packages

        # Set ownership early if creating venv as root
        if [ -n "$SUDO_USER" ]; then
            chown -R $SUDO_USER:$SUDO_USER "$VENV_DIR"
        fi
    fi

    # Activate virtual environment
    echo "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"

    # Clear pip cache
    echo "Clearing pip cache..."
    pip cache purge

    # Upgrade pip
    echo "Upgrading pip..."
    pip install --upgrade pip

    # Upgrade setuptools and wheel
    echo "Upgrading setuptools and wheel..."
    pip install --upgrade setuptools wheel

    # Install Python dependencies for all modules
    echo "Installing Python dependencies for all modules..."
    # Skip PyGObject installation since we're using system packages
    grep -v "PyGObject" "$PROJECT_ROOT/backend/requirements.txt" > "$PROJECT_ROOT/backend/requirements_filtered.txt"
    pip install -r "$PROJECT_ROOT/backend/requirements_filtered.txt"
    pip install -r "$PROJECT_ROOT/backend/modules/audio/requirements.txt"
    pip install -r "$PROJECT_ROOT/backend/modules/nfc/requirements.txt"
    rm "$PROJECT_ROOT/backend/requirements_filtered.txt"

    # Ensure test scripts are executable (idempotent)
    chmod +x "$PROJECT_ROOT/backend/modules/audio/interactive_test.py"
    chmod +x "$PROJECT_ROOT/backend/modules/audio/test_imports.py"
    chmod +x "$PROJECT_ROOT/backend/modules/nfc/test_nfc.py"

    # Ensure script ownership is correct (important if venv existed but script ownership was wrong)
    if [ -n "$SUDO_USER" ]; then
        chown $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/backend/modules/audio/interactive_test.py"
        chown $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/backend/modules/audio/test_imports.py"
        chown $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/backend/modules/nfc/test_nfc.py"
        # Re-apply ownership to venv just in case pip created root-owned files inside
        chown -R $SUDO_USER:$SUDO_USER "$VENV_DIR"
    fi

    echo "Python virtual environment setup/update completed"
}
# Function to configure audio system (Step 2)
setup_audio_system_deps() {
    echo -e "\n[2/$total_steps] Configuring audio module system dependencies..."

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
# Function to setup the NFC module system dependencies (Step 3)
setup_nfc_system_deps() {
    echo -e "\n[3/$total_steps] Configuring NFC module system dependencies..."

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
# Function to setup frontend dependencies (Step 4)
setup_frontend() {
    echo -e "\n[4/$total_steps] Setting up frontend..."

    # Install Node.js dependencies
    cd "$PROJECT_ROOT/frontend"
    
    echo "Installing frontend dependencies..."
    # Use memory-optimized npm install to prevent Pi from crashing
    NODE_OPTIONS="--max_old_space_size=256" npm install --no-save --no-audit --no-fund --prefer-offline --production=false
    
    # Return to project root
    cd "$PROJECT_ROOT"
    
    # Set proper ownership if running as sudo
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER "$PROJECT_ROOT/frontend"
    fi
    
    echo "Frontend setup completed"
}
# Function to verify the setup (Step 5)
verify_setup() {
    echo -e "\n[5/$total_steps] Verifying setup..."

    # Activate venv if it exists and isn't already active (needed if skipping steps)
    VENV_DIR="$PROJECT_ROOT/venv"
    if [ -z "$VIRTUAL_ENV" ] && [ -f "$VENV_DIR/bin/activate" ]; then
        echo "Activating virtual environment for verification..."
        source "$VENV_DIR/bin/activate"
    fi

    # Verify Python virtual environment
    if [ -d "$VENV_DIR" ]; then
        echo "✅ Python virtual environment exists"
    else
        echo "❌ Python virtual environment does not exist"
    fi
    
    # Verify RPi.GPIO is available
    if source "$PROJECT_ROOT/venv/bin/activate" && python3 -c "import RPi.GPIO" 2>/dev/null; then
        echo "✅ RPi.GPIO is properly installed"
    else
        echo "❌ RPi.GPIO is not properly installed"
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

# Main execution logic
main() {
    echo "Starting comprehensive project setup..."
    local current_step=0 # Use 0 for pre-requisite steps

    # --- Pre-requisite System Dependencies (Conditionally Run) ---
    if [ "$skip_prereqs" = false ]; then
        echo -e "\n[Pre-requisites] Ensuring core system packages are installed..."
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
        gobject-introspection \
        python3-cairo \
        python3-gi \
        python3-gi-cairo \
        gir1.2-gtk-3.0 \
        python3-cairo-dev \
        libcairo-gobject2 \
        ffmpeg

    # Run ldconfig to ensure library cache is updated
    ldconfig

    # Install all remaining system dependencies (Considered part of pre-requisites)
    echo "Installing remaining system dependencies..."
    apt-get install -y --no-install-recommends \
        build-essential \
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
        python3-rpi.gpio \
        i2c-tools \
        python3-venv \
        python3-full \
        libgpiod2 \
            nodejs \
            npm
    else
         echo -e "\nSkipping [Pre-requisites] system package installation as requested."
    fi

    # --- Step 1: Python Virtual Environment ---
    current_step=1
    if [[ $start_step -le $current_step ]]; then
        setup_python_venv
    else
        echo -e "\nSkipping Step $current_step/$total_steps: Python virtual environment setup."
    fi

    # --- Step 2: Audio System Dependencies ---
    current_step=2
    if [[ $start_step -le $current_step ]]; then
        setup_audio_system_deps
    else
        echo -e "\nSkipping Step $current_step/$total_steps: Audio module system dependencies setup."
    fi

    # --- Step 3: NFC System Dependencies ---
    current_step=3
    if [[ $start_step -le $current_step ]]; then
        setup_nfc_system_deps
    else
        echo -e "\nSkipping Step $current_step/$total_steps: NFC module system dependencies setup."
    fi

    # --- Step 4: Frontend Setup ---
    current_step=4
    if [[ $start_step -le $current_step ]]; then
        setup_frontend
    else
        echo -e "\nSkipping Step $current_step/$total_steps: Frontend setup."
    fi

    # --- Step 5: Verification ---
    current_step=5
    if [[ $start_step -le $current_step ]]; then
        # Verify PyGObject installation (needs venv)
        VENV_DIR="$PROJECT_ROOT/venv"
        if [ -f "$VENV_DIR/bin/activate" ]; then
             echo "Verifying PyGObject installation..."
             source "$VENV_DIR/bin/activate"
             python3 -c "import gi; print('PyGObject (gi) is properly installed and accessible in the virtual environment')" || echo "Warning: PyGObject verification failed."
        else
             echo "Warning: Cannot verify PyGObject, virtual environment not found."
        fi
        verify_setup
    else
        echo -e "\nSkipping Step $current_step/$total_steps: Setup verification."
    fi


    echo -e "\n============================================================="
    if [[ $start_step -eq 1 ]]; then
        echo "          Full Setup Process Completed Successfully           "
    else
        echo "        Setup Process (from step $start_step) Completed Successfully      "
    fi
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
