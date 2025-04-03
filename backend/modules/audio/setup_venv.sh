#!/bin/bash
# Script to set up a virtual environment with system packages for audio module

echo "=== Setting up Python virtual environment with system packages ==="

# Remove existing venv if present
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# Create virtual environment with system packages
echo "Creating new virtual environment with system packages..."
python3 -m venv venv --system-site-packages

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install pydbus pytest pytest-cov pexpect

# Make test scripts executable
echo "Making test scripts executable..."
chmod +x backend/modules/audio/interactive_test.py
chmod +x backend/modules/audio/test_imports.py

echo -e "\n=== Setup Complete ==="
echo "To test imports, run:"
echo "  source venv/bin/activate"
echo "  python backend/modules/audio/test_imports.py"
echo ""
echo "To run the interactive test, run:"
echo "  source venv/bin/activate"
echo "  python backend/modules/audio/interactive_test.py"