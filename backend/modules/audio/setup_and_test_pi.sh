#!/bin/bash
# Raspberry Pi setup and test script for the audio module
# This script will install all necessary dependencies for Bluetooth audio
# and set up the audio module for testing.

set -e  # Exit on error

echo "=== Audio Module Setup for Raspberry Pi ==="
echo "This script will install Bluetooth audio dependencies and set up the audio module."
echo

# Function to check if script is running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root (use sudo)"
        exit 1
    fi
}

# Function to add Raspberry Pi repository if needed
add_repositories() {
    echo "=== Checking for required repositories ==="
    
    # Add Raspberry Pi repository if not already present and not on Raspberry Pi OS
    if ! grep -q "raspbian\|raspberrypi" /etc/apt/sources.list /etc/apt/sources.list.d/* 2>/dev/null; then
        echo "Adding Raspberry Pi repository..."
        echo "deb http://archive.raspberrypi.org/debian/ buster main" | tee /etc/apt/sources.list.d/raspi.list
        wget -qO - https://archive.raspberrypi.org/debian/raspberrypi.gpg.key | apt-key add -
        apt-get update
    else
        echo "Raspberry Pi repository is already configured."
    fi
}

# Function to install system dependencies
install_system_deps() {
    echo "=== Installing system dependencies ==="
    apt-get update
    
    # Install Bluetooth dependencies
    apt-get install -y --no-install-recommends \
        bluetooth \
        bluez \
        bluez-tools \
        pi-bluetooth \
        bluealsa \
        dbus \
        python3-dbus \
        python3-gi \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-alsa \
        python3-gst-1.0 \
        alsa-utils \
        python3-pip \
        python3-dev \
        python3-setuptools \
        python3-venv
    
    echo "System dependencies installed."
}

# Function to configure BlueALSA
configure_bluealsa() {
    echo "=== Configuring BlueALSA ==="
    
    # Create BlueALSA service file if it doesn't exist
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
    
    echo "BlueALSA configured and started."
}

# Function to setup Python virtual environment and install dependencies
setup_python_env() {
    echo "=== Setting up Python environment ==="
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install Python dependencies
    pip install -r backend/modules/audio/requirements.txt
    
    echo "Python environment set up and dependencies installed."
}

# Function to configure Bluetooth audio
configure_bluetooth() {
    echo "=== Configuring Bluetooth ==="
    
    # Enable Bluetooth service
    systemctl enable bluetooth
    systemctl start bluetooth
    
    # Add current user to bluetooth group
    usermod -a -G bluetooth $SUDO_USER
    
    # Configure Bluetooth to be discoverable
    sed -i 's/#DiscoverableTimeout = 0/DiscoverableTimeout = 0/' /etc/bluetooth/main.conf
    sed -i 's/#Discoverable = false/Discoverable = true/' /etc/bluetooth/main.conf
    
    # Restart Bluetooth service to apply changes
    systemctl restart bluetooth
    
    echo "Bluetooth configured."
}

# Function to setup test sound files
setup_sound_files() {
    echo "=== Setting up test sound files ==="
    
    # Create sounds directory if it doesn't exist
    SOUNDS_DIR="$(pwd)/sounds"
    mkdir -p $SOUNDS_DIR
    
    # Generate test sound files using sox
    if command -v sox &> /dev/null; then
        # Create error sound
        sox -n -r 44100 -c 2 $SOUNDS_DIR/error.wav synth 0.5 sine 400 vol 0.5
        
        # Create success sound
        sox -n -r 44100 -c 2 $SOUNDS_DIR/success.wav synth 0.5 sine 800 vol 0.5
        
        # Create info sound
        sox -n -r 44100 -c 2 $SOUNDS_DIR/info.wav synth 0.5 sine 600 vol 0.5
        
        # Create warning sound
        sox -n -r 44100 -c 2 $SOUNDS_DIR/warning.wav synth 0.5 sine 300 vol 0.5
        
        echo "Test sound files created in $SOUNDS_DIR"
    else
        # Install sox
        apt-get install -y sox
        
        # Create sounds
        sox -n -r 44100 -c 2 $SOUNDS_DIR/error.wav synth 0.5 sine 400 vol 0.5
        sox -n -r 44100 -c 2 $SOUNDS_DIR/success.wav synth 0.5 sine 800 vol 0.5
        sox -n -r 44100 -c 2 $SOUNDS_DIR/info.wav synth 0.5 sine 600 vol 0.5
        sox -n -r 44100 -c 2 $SOUNDS_DIR/warning.wav synth 0.5 sine 300 vol 0.5
        
        echo "Test sound files created in $SOUNDS_DIR"
    fi
    
    # Set proper ownership of the sounds directory
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER $SOUNDS_DIR
    fi
}

# Function to run tests
run_tests() {
    echo "=== Running audio module tests ==="
    
    # Run tests if they exist
    if [ -f backend/modules/audio/test_audio.py ]; then
        cd "$(dirname "$0")/../../../" && python -m pytest -v backend/modules/audio/test_audio.py
    else
        echo "No test file found. Skipping tests."
    fi
    
    echo "Tests completed."
}

# Function to print Bluetooth status
print_bluetooth_status() {
    echo "=== Bluetooth Status ==="
    
    # Check if Bluetooth is available
    if ! command -v bluetoothctl &> /dev/null; then
        echo "bluetoothctl not found. Is Bluetooth installed?"
        return 1
    fi
    
    # Get Bluetooth controller info
    echo "Bluetooth controller:"
    bluetoothctl show
    
    # List known devices
    echo -e "\nKnown devices:"
    bluetoothctl devices
    
    # Show audio cards
    echo -e "\nAudio cards:"
    aplay -l
    
    # Show BlueALSA status
    echo -e "\nBlueALSA status:"
    systemctl status bluealsa
    
    # Show BlueALSA devices if available
    if command -v bluealsa-aplay &> /dev/null; then
        echo -e "\nBlueALSA devices:"
        bluealsa-aplay -l 2>/dev/null || echo "No BlueALSA devices found or command failed."
    fi
}

# Function to test audio playback
test_audio_playback() {
    echo "=== Testing Audio Playback ==="
    
    # Test local audio playback
    echo "Testing local audio playback:"
    if [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
        aplay /usr/share/sounds/alsa/Front_Center.wav
    else
        echo "Test audio file not found."
    fi
    
    # Ask user if they want to test Bluetooth playback
    echo -e "\nDo you want to test Bluetooth audio playback? (y/n): "
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo "Available BlueALSA devices:"
        bluealsa-aplay -l
        
        echo -e "\nEnter the MAC address of your Bluetooth speaker (e.g., 00:11:22:33:44:55): "
        read -r mac_address
        
        echo "Testing playback to Bluetooth device $mac_address..."
        if [ -f /usr/share/sounds/alsa/Front_Center.wav ]; then
            bluealsa-aplay "$mac_address" /usr/share/sounds/alsa/Front_Center.wav || echo "Playback failed. Check your Bluetooth connection."
        else
            echo "Test audio file not found."
        fi
    else
        echo "Skipping Bluetooth playback test."
    fi
}

# Main function
main() {
    # Check if running as root
    check_root
    
    # Add repositories if needed
    add_repositories
    
    # Install system dependencies
    install_system_deps
    
    # Configure BlueALSA
    configure_bluealsa
    
    # Configure Bluetooth
    configure_bluetooth
    
    # Setup test sound files
    setup_sound_files
    
    # Setup Python environment
    setup_python_env
    
    # Print Bluetooth status
    print_bluetooth_status
    
    # Test audio playback
    test_audio_playback
    
    echo -e "\n=== Setup completed successfully ==="
    echo "BlueALSA has been configured for Bluetooth audio playback."
    echo "To pair with a Bluetooth speaker, use:"
    echo "  bluetoothctl"
    echo "  [bluetooth]# power on"
    echo "  [bluetooth]# agent on"
    echo "  [bluetooth]# default-agent"
    echo "  [bluetooth]# scan on"
    echo "  [bluetooth]# pair [MAC_ADDRESS]"
    echo "  [bluetooth]# connect [MAC_ADDRESS]"
    echo "  [bluetooth]# trust [MAC_ADDRESS]"
    
    # Ask if we should run tests
    echo -e "\nDo you want to run additional tests? (y/n): "
    read -r run_tests_now
    if [[ "$run_tests_now" =~ ^[Yy]$ ]]; then
        echo "Running tests..."
        
        # Deactivate and reactivate venv to ensure clean environment
        deactivate 2>/dev/null || true
        source venv/bin/activate
        
        # Run tests
        run_tests
    else
        echo "Skipping additional tests."
    fi
    
    echo -e "\n=== Audio Module Setup Complete ==="
    echo "You can now use the audio module for Bluetooth audio playback."
}

# Execute main function
main "$@"