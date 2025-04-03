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

# Function to install system dependencies
install_system_deps() {
    echo "=== Installing system dependencies ==="
    apt-get update
    
    # Install Bluetooth dependencies
    apt-get install -y --no-install-recommends \
        bluetooth \
        bluez \
        bluez-tools \
        bluez-alsa \
        pi-bluetooth \
        dbus \
        python3-dbus \
        python3-gi
    
    # Install GStreamer dependencies
    apt-get install -y --no-install-recommends \
        gstreamer1.0-tools \
        gstreamer1.0-plugins-base \
        gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad \
        gstreamer1.0-alsa \
        python3-gst-1.0
    
    # Install audio utilities
    apt-get install -y --no-install-recommends \
        alsa-utils \
        pulseaudio \
        pulseaudio-module-bluetooth
    
    # Install Python development tools
    apt-get install -y --no-install-recommends \
        python3-pip \
        python3-dev \
        python3-setuptools \
        python3-venv
    
    echo "System dependencies installed."
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
    echo "=== Configuring Bluetooth audio ==="
    
    # Enable Bluetooth service
    systemctl enable bluetooth
    systemctl start bluetooth
    
    # Enable BlueALSA
    systemctl enable bluealsad
    systemctl start bluealsad
    
    # Add current user to bluetooth group
    usermod -a -G bluetooth $SUDO_USER
    
    # Configure Bluetooth to be discoverable
    sed -i 's/#DiscoverableTimeout = 0/DiscoverableTimeout = 0/' /etc/bluetooth/main.conf
    sed -i 's/#Discoverable = false/Discoverable = true/' /etc/bluetooth/main.conf
    
    # Restart Bluetooth service to apply changes
    systemctl restart bluetooth
    
    echo "Bluetooth audio configured."
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
        # Create empty sound files if sox is not available
        touch $SOUNDS_DIR/error.wav
        touch $SOUNDS_DIR/success.wav
        touch $SOUNDS_DIR/info.wav
        touch $SOUNDS_DIR/warning.wav
        
        echo "Created empty sound files in $SOUNDS_DIR (install sox for real sounds)."
        echo "Run: sudo apt-get install sox to get proper sound generation."
    fi
    
    # Set proper ownership of the sounds directory
    if [ -n "$SUDO_USER" ]; then
        chown -R $SUDO_USER:$SUDO_USER $SOUNDS_DIR
    fi
}

# Function to run tests
run_tests() {
    echo "=== Running audio module tests ==="
    
    # Run tests
    cd "$(dirname "$0")/../../../" && python -m pytest -v backend/modules/audio/test_audio.py
    
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
}

# Main function
main() {
    # Check if running as root
    check_root
    
    # Install system dependencies
    install_system_deps
    
    # Configure Bluetooth
    configure_bluetooth
    
    # Setup test sound files
    setup_sound_files
    
    # Setup Python environment
    setup_python_env
    
    # Print Bluetooth status
    print_bluetooth_status
    
    echo -e "\n=== Setup completed successfully ==="
    echo "To run tests, use: cd $(pwd) && source venv/bin/activate && python -m pytest -v backend/modules/audio/test_audio.py"
    
    # Ask if we should run tests now
    read -p "Do you want to run tests now? (y/n): " run_tests_now
    if [[ $run_tests_now == "y" || $run_tests_now == "Y" ]]; then
        echo "Running tests..."
        
        # Deactivate and reactivate venv to ensure clean environment
        deactivate 2>/dev/null || true
        source venv/bin/activate
        
        # Run tests
        run_tests
    else
        echo "Skipping tests. You can run them later using the command above."
    fi
    
    echo -e "\n=== Audio Module Setup Complete ==="
    echo "You can now use the audio module for Bluetooth audio playback."
}

# Execute main function
main "$@"
