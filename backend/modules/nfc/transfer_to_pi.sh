#!/bin/bash
# Simple script to transfer NFC module files to Raspberry Pi

# Configuration
PI_USER="j"
PI_HOST="192.168.1.53"
PI_PASS="123456789"
PI_PATH="/home/j/nfc_module"

echo "==================================================="
echo "  Transferring NFC Module Files to Raspberry Pi    "
echo "==================================================="
echo "Target: $PI_USER@$PI_HOST:$PI_PATH"

# Get directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Source: $SCRIPT_DIR"

# Create the remote directory structure (using password explicitly for better diagnostics)
echo -e "\n[1/3] Creating remote directory..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no $PI_USER@$PI_HOST "mkdir -p $PI_PATH/backend/modules/nfc"

# List all files we want to transfer
FILES=(
  "$SCRIPT_DIR/__init__.py"
  "$SCRIPT_DIR/exceptions.py"
  "$SCRIPT_DIR/hardware_interface.py"
  "$SCRIPT_DIR/nfc_controller.py"
  "$SCRIPT_DIR/tag_processor.py"
  "$SCRIPT_DIR/test_nfc.py"
  "$SCRIPT_DIR/requirements.txt"
  "$SCRIPT_DIR/setup_and_test_pi.sh"
)

# Transfer each file individually
echo -e "\n[2/3] Copying files one by one..."
for file in "${FILES[@]}"; do
  filename=$(basename "$file")
  echo "  Copying $filename..."
  sshpass -p "$PI_PASS" scp -o StrictHostKeyChecking=no "$file" "$PI_USER@$PI_HOST:$PI_PATH/backend/modules/nfc/"
  if [ $? -eq 0 ]; then
    echo "  ✅ Successfully copied $filename"
  else
    echo "  ❌ Failed to copy $filename"
  fi
done

# Set executable permissions on scripts
echo -e "\n[3/3] Setting executable permissions..."
sshpass -p "$PI_PASS" ssh -o StrictHostKeyChecking=no $PI_USER@$PI_HOST "chmod +x $PI_PATH/backend/modules/nfc/*.py $PI_PATH/backend/modules/nfc/*.sh 2>/dev/null || true"

echo -e "\n==================================================="
echo "              Transfer Complete                     "
echo "==================================================="
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
echo "==================================================="
