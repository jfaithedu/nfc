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

The setup script (`setup_and_test_pi.sh`) has been updated to use the correct package names and service names. When you run the setup script, it will:

1. Install the `bluez-alsa` package instead of `bluealsa`
2. Configure the system service as `bluealsad` instead of `bluealsa`

## Troubleshooting

If you encounter issues:

1. Make sure the correct package is installed:

   ```
   sudo apt-get install bluez-alsa
   ```

2. Check if the service is running:

   ```
   systemctl status bluealsad
   ```

3. Restart the service if needed:
   ```
   sudo systemctl restart bluealsad
   ```

## Further Information

For more details on the changes in the BlueALSA project, see:

- [BlueALSA GitHub Wiki - Migrating from release 4.3.1 or earlier](https://github.com/Arkq/bluez-alsa/wiki/Migrating-from-release-4.3.1-or-earlier)
- [BlueALSA GitHub Repository](https://github.com/Arkq/bluez-alsa)
