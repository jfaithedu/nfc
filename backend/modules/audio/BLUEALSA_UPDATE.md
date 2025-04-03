# BlueALSA Update Information

## Changes in BlueALSA Package

The audio module has been updated to use `bluez-alsa` instead of `bluealsa`. This change was made to align with the latest naming conventions and availability in Ubuntu-based distributions.

### Important Changes

1. The package name has changed:

   - Old: `bluealsa`
   - New: `bluez-alsa`

2. The daemon name has changed:

   - Old: `bluealsa`
   - New: `bluealsad`

3. System service changes:
   - Old: `systemctl enable/start bluealsa`
   - New: `systemctl enable/start bluealsad`

## Installation

The setup script (`setup_and_test_pi.sh`) has been updated to install BlueALSA from source code since the package may not be available in all Ubuntu repositories. When you run the setup script, it will:

1. Install the necessary build dependencies
2. Clone and build the BlueALSA source from GitHub
3. Install the compiled software
4. Create and configure the system service as `bluealsad`

### Manual Installation

If you need to manually install BlueALSA, follow these steps:

```bash
# Install build dependencies
sudo apt-get install -y build-essential git automake libtool pkg-config \
  libasound2-dev libbluetooth-dev libdbus-1-dev libglib2.0-dev libsbc-dev

# Clone repository
git clone https://github.com/Arkq/bluez-alsa.git
cd bluez-alsa

# Build and install
autoreconf --install
mkdir build && cd build
../configure --enable-aac
make
sudo make install

# Create service file
sudo bash -c 'cat > /etc/systemd/system/bluealsad.service << EOF
[Unit]
Description=BlueALSA service
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=simple
ExecStart=/usr/local/bin/bluealsad -p a2dp-sink -p a2dp-source
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF'

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable bluealsad
sudo systemctl start bluealsad
```

## Troubleshooting

If you encounter issues:

1. Check if the service is running:

   ```
   systemctl status bluealsad
   ```

2. Restart the service if needed:

   ```
   sudo systemctl restart bluealsad
   ```

3. Check build logs if compilation failed:

   ```
   cd /tmp/*/bluez-alsa/build
   cat config.log
   ```

4. Verify that the BlueALSA daemon is available:
   ```
   which bluealsad
   ```

## Further Information

For more details on the changes in the BlueALSA project, see:

- [BlueALSA GitHub Wiki - Migrating from release 4.3.1 or earlier](https://github.com/Arkq/bluez-alsa/wiki/Migrating-from-release-4.3.1-or-earlier)
- [BlueALSA GitHub Repository](https://github.com/Arkq/bluez-alsa)
