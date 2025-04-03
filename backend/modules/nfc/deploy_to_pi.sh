#!/bin/bash
# Deploy NFC module to Raspberry Pi

# Default connection parameters
PI_USER="j"
PI_HOST="192.168.1.53"
PI_PATH="/home/j/nfc_module"
SSH_PASS="123456789"

# Print header
echo "============================================================="
echo "         Deploying NFC Module to Raspberry Pi                "
echo "============================================================="

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--host)
      PI_HOST="$2"
      shift 2
      ;;
    -u|--user)
      PI_USER="$2"
      shift 2
      ;;
    -p|--path)
      PI_PATH="$2"
      shift 2
      ;;
    *)
      echo "Unknown parameter: $1"
      echo "Usage: $0 [-h|--host hostname] [-u|--user username] [-p|--path remote_path]"
      exit 1
      ;;
  esac
done

# Configure sshpass for non-interactive authentication
export SSHPASS="$SSH_PASS"

# Get the directory of this script
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
MODULE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "Deploying from: $SCRIPT_DIR"
echo "To: $PI_USER@$PI_HOST:$PI_PATH"

# Check if sshpass is installed
if ! command -v sshpass &> /dev/null; then
    echo "sshpass is not installed. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y sshpass
    elif command -v yum &> /dev/null; then
        sudo yum install -y sshpass
    else
        echo "Error: Could not install sshpass. Please install it manually."
        exit 1
    fi
fi

# Create remote directory if it doesn't exist
echo -e "\n[1/3] Creating remote directory..."
sshpass -e ssh -o StrictHostKeyChecking=no $PI_USER@$PI_HOST "mkdir -p $PI_PATH/backend/modules/nfc"

# Copy NFC module files to the Pi
echo -e "\n[2/3] Copying NFC module files..."
sshpass -e scp -o StrictHostKeyChecking=no -r $SCRIPT_DIR/* $PI_USER@$PI_HOST:$PI_PATH/backend/modules/nfc/

# Make scripts executable on the Pi
echo -e "\n[3/3] Setting executable permissions..."
sshpass -e ssh -o StrictHostKeyChecking=no $PI_USER@$PI_HOST "chmod +x $PI_PATH/backend/modules/nfc/*.py $PI_PATH/backend/modules/nfc/*.sh"

# Provide next steps
echo -e "\n============================================================="
echo "                   Deployment Complete                         "
echo "============================================================="
echo -e "\nNext steps:"
echo "1. Connect to the Raspberry Pi:"
echo "   ssh $PI_USER@$PI_HOST"
echo
echo "2. Navigate to the NFC module directory:"
echo "   cd $PI_PATH/backend/modules/nfc"
echo
echo "3. Run the setup script:"
echo "   ./setup_and_test_pi.sh"
echo
echo "4. After setup, run tests with:"
echo "   ./test_nfc.py"
echo "============================================================="
