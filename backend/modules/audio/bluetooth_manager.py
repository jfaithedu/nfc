"""
Bluetooth manager for audio device connections.

Handles Bluetooth device discovery, connection, and management for audio devices.
Uses D-Bus to communicate with BlueZ (Linux Bluetooth stack).
"""

import os
import logging
import json
import time
import threading
import subprocess
from pathlib import Path

import dbus
import dbus.mainloop.glib
from gi.repository import GLib

from .exceptions import BluetoothError, BluetoothDiscoveryError, BluetoothConnectionError

# Set up logger
logger = logging.getLogger(__name__)

# BlueZ D-Bus constants
BLUEZ_SERVICE_NAME = "org.bluez"
ADAPTER_INTERFACE = "org.bluez.Adapter1"
DEVICE_INTERFACE = "org.bluez.Device1"
MEDIA_TRANSPORT_INTERFACE = "org.bluez.MediaTransport1"
MEDIA_PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"

# Profiles for audio
A2DP_SINK_UUID = "0000110b-0000-1000-8000-00805f9b34fb"  # A2DP Sink (music from device)
A2DP_SOURCE_UUID = "0000110a-0000-1000-8000-00805f9b34fb"  # A2DP Source (music to device)
HFP_HF_UUID = "0000111e-0000-1000-8000-00805f9b34fb"  # Hands-Free unit


class BluetoothManager:
    """
    Manages Bluetooth connections and device discovery.
    """

    def __init__(self):
        """
        Initialize the Bluetooth manager.
        """
        # Initialize D-Bus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self._bus = dbus.SystemBus()
        
        # Start main loop in a thread
        self._main_loop = GLib.MainLoop()
        self._thread = threading.Thread(target=self._main_loop.run)
        self._thread.daemon = True
        self._thread.start()
        
        # State variables
        self._adapter = None
        self._adapter_path = None
        self._discovering = False
        self._discovered_devices = {}
        self._connected_device = None
        self._device_connection_timeout = 30  # seconds
        
        # Storage for paired devices
        self._config_dir = Path.home() / ".config" / "nfc-player"
        self._paired_devices_file = self._config_dir / "paired_devices.json"
        self._saved_devices = self._load_saved_devices()
        
        # Initialize adapter
        self._find_adapter()
        
        logger.debug("BluetoothManager initialized")

    def _find_adapter(self):
        """Find and initialize the default Bluetooth adapter."""
        try:
            # Get object manager
            obj_manager = dbus.Interface(
                self._bus.get_object(BLUEZ_SERVICE_NAME, "/"),
                OBJECT_MANAGER_INTERFACE
            )
            
            # Get all BlueZ objects
            objects = obj_manager.GetManagedObjects()
            
            # Find the first adapter
            for path, interfaces in objects.items():
                if ADAPTER_INTERFACE in interfaces:
                    self._adapter_path = path
                    self._adapter = dbus.Interface(
                        self._bus.get_object(BLUEZ_SERVICE_NAME, path),
                        ADAPTER_INTERFACE
                    )
                    logger.debug(f"Found Bluetooth adapter: {path}")
                    
                    # Get adapter properties
                    adapter_props = dbus.Interface(
                        self._bus.get_object(BLUEZ_SERVICE_NAME, path),
                        PROPERTIES_INTERFACE
                    )
                    
                    # Ensure adapter is powered on
                    if not adapter_props.Get(ADAPTER_INTERFACE, "Powered"):
                        adapter_props.Set(ADAPTER_INTERFACE, "Powered", dbus.Boolean(True))
                        logger.debug("Powered on Bluetooth adapter")
                    
                    return True
            
            # No adapter found
            logger.error("No Bluetooth adapter found")
            return False
            
        except dbus.exceptions.DBusException as e:
            logger.error(f"D-Bus error finding adapter: {str(e)}")
            return False

    def start_discovery(self, timeout=30):
        """
        Start discovery for Bluetooth devices.

        Args:
            timeout (int, optional): Discovery timeout in seconds

        Returns:
            bool: True if discovery started
        """
        if not self._adapter:
            logger.error("Cannot start discovery: No Bluetooth adapter")
            raise BluetoothDiscoveryError("No Bluetooth adapter available")
        
        try:
            # Clear previous discovery results
            self._discovered_devices = {}
            
            # Register signal handlers for device discovery
            self._bus.add_signal_receiver(
                self._interfaces_added_handler,
                dbus_interface=OBJECT_MANAGER_INTERFACE,
                signal_name="InterfacesAdded"
            )
            self._bus.add_signal_receiver(
                self._interfaces_removed_handler,
                dbus_interface=OBJECT_MANAGER_INTERFACE,
                signal_name="InterfacesRemoved"
            )
            self._bus.add_signal_receiver(
                self._properties_changed_handler,
                dbus_interface=PROPERTIES_INTERFACE,
                signal_name="PropertiesChanged",
                arg0=DEVICE_INTERFACE,
                path_keyword="path"
            )
            
            # Start discovery
            self._adapter.StartDiscovery()
            self._discovering = True
            logger.debug("Started Bluetooth device discovery")
            
            # Set up timeout
            if timeout > 0:
                def stop_discovery_timeout():
                    time.sleep(timeout)
                    if self._discovering:
                        self.stop_discovery()
                
                timeout_thread = threading.Thread(target=stop_discovery_timeout)
                timeout_thread.daemon = True
                timeout_thread.start()
            
            return True
            
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to start discovery: {str(e)}")
            raise BluetoothDiscoveryError(f"Failed to start discovery: {str(e)}")

    def _interfaces_added_handler(self, path, interfaces):
        """Handle when a new device is discovered."""
        if DEVICE_INTERFACE in interfaces:
            self._update_device(path)

    def _interfaces_removed_handler(self, path, interfaces):
        """Handle when a device is removed."""
        if DEVICE_INTERFACE in interfaces and path in self._discovered_devices:
            del self._discovered_devices[path]
            logger.debug(f"Device removed: {path}")

    def _properties_changed_handler(self, interface, changed, invalidated, path):
        """Handle when device properties change."""
        if path.startswith(self._adapter_path) and interface == DEVICE_INTERFACE:
            self._update_device(path)

    def _update_device(self, path):
        """Update or add a device in the discovered devices list."""
        try:
            device_obj = self._bus.get_object(BLUEZ_SERVICE_NAME, path)
            device_props = dbus.Interface(device_obj, PROPERTIES_INTERFACE)
            
            # Get device properties
            props = device_props.GetAll(DEVICE_INTERFACE)
            
            # Only include devices with names and audio profiles
            if "Name" in props and "UUIDs" in props:
                uuids = [str(uuid) for uuid in props["UUIDs"]]
                
                # Check if device supports audio profiles
                if any(uuid in uuids for uuid in [A2DP_SINK_UUID, A2DP_SOURCE_UUID, HFP_HF_UUID]):
                    # Create device info dictionary
                    device_info = {
                        "name": str(props["Name"]),
                        "address": str(props["Address"]),
                        "path": path,
                        "paired": bool(props.get("Paired", False)),
                        "trusted": bool(props.get("Trusted", False)),
                        "connected": bool(props.get("Connected", False)),
                        "audio_profiles": {
                            "a2dp_sink": A2DP_SINK_UUID in uuids,
                            "a2dp_source": A2DP_SOURCE_UUID in uuids,
                            "hfp_hf": HFP_HF_UUID in uuids
                        }
                    }
                    
                    self._discovered_devices[path] = device_info
                    logger.debug(f"Updated device: {device_info['name']} ({device_info['address']})")
                    
                    # If this is the currently connected device, update status
                    if self._connected_device and self._connected_device["path"] == path:
                        self._connected_device["connected"] = device_info["connected"]
        
        except dbus.exceptions.DBusException as e:
            logger.error(f"Error updating device {path}: {str(e)}")

    def get_discovered_devices(self):
        """
        Get list of discovered devices.

        Returns:
            list: List of device dictionaries with name, address, and type
        """
        return list(self._discovered_devices.values())

    def stop_discovery(self):
        """
        Stop the discovery process.

        Returns:
            bool: True if discovery stopped
        """
        if not self._adapter or not self._discovering:
            logger.debug("Discovery not active, nothing to stop")
            return True
        
        try:
            self._adapter.StopDiscovery()
            self._discovering = False
            logger.debug("Stopped Bluetooth device discovery")
            return True
            
        except dbus.exceptions.DBusException as e:
            logger.error(f"Failed to stop discovery: {str(e)}")
            return False

    def connect_device(self, device_address):
        """
        Connect to a Bluetooth device.

        Args:
            device_address (str): Bluetooth device address

        Returns:
            bool: True if connected successfully

        Raises:
            BluetoothConnectionError: If connection fails
        """
        # First, stop discovery if active
        if self._discovering:
            self.stop_discovery()
        
        # Find device by address
        device_path = None
        device_info = None
        
        for path, info in self._discovered_devices.items():
            if info["address"] == device_address:
                device_path = path
                device_info = info
                break
        
        if not device_path:
            logger.error(f"Device not found: {device_address}")
            raise BluetoothConnectionError(f"Device not found: {device_address}")
        
        try:
            device_obj = self._bus.get_object(BLUEZ_SERVICE_NAME, device_path)
            device = dbus.Interface(device_obj, DEVICE_INTERFACE)
            device_props = dbus.Interface(device_obj, PROPERTIES_INTERFACE)
            
            # Check if already connected
            if device_props.Get(DEVICE_INTERFACE, "Connected"):
                logger.debug(f"Device already connected: {device_info['name']}")
                self._connected_device = device_info
                return True
            
            # Trust device if not trusted
            if not device_props.Get(DEVICE_INTERFACE, "Trusted"):
                device_props.Set(DEVICE_INTERFACE, "Trusted", dbus.Boolean(True))
                logger.debug(f"Setting device as trusted: {device_info['name']}")
            
            # Connect to device
            logger.debug(f"Connecting to device: {device_info['name']}")
            device.Connect()
            
            # Wait for connection to complete
            start_time = time.time()
            while time.time() - start_time < self._device_connection_timeout:
                time.sleep(0.5)
                if device_props.Get(DEVICE_INTERFACE, "Connected"):
                    logger.debug(f"Successfully connected to device: {device_info['name']}")
                    self._connected_device = device_info
                    
                    # Save device as paired
                    self.save_paired_device(device_address, device_info['name'])
                    
                    return True
            
            # Timeout reached without successful connection
            logger.error(f"Connection timeout: {device_info['name']}")
            raise BluetoothConnectionError(f"Connection timeout: {device_info['name']}")
            
        except dbus.exceptions.DBusException as e:
            logger.error(f"Connection error: {str(e)}")
            raise BluetoothConnectionError(f"Failed to connect: {str(e)}")

    def disconnect_device(self):
        """
        Disconnect the current device.

        Returns:
            bool: True if disconnected successfully
        """
        if not self._connected_device:
            logger.debug("No device connected")
            return True
        
        try:
            device_obj = self._bus.get_object(BLUEZ_SERVICE_NAME, self._connected_device["path"])
            device = dbus.Interface(device_obj, DEVICE_INTERFACE)
            
            logger.debug(f"Disconnecting from device: {self._connected_device['name']}")
            device.Disconnect()
            
            # Update state
            self._connected_device = None
            return True
            
        except dbus.exceptions.DBusException as e:
            logger.error(f"Disconnection error: {str(e)}")
            return False

    def get_connected_device(self):
        """
        Get information about the currently connected device.

        Returns:
            dict or None: Device information or None if not connected
        """
        return self._connected_device

    def is_device_connected(self, device_address=None):
        """
        Check if a device is connected.

        Args:
            device_address (str, optional): Device to check, or current device if None

        Returns:
            bool: True if device is connected
        """
        if device_address is None:
            return self._connected_device is not None
        
        if self._connected_device and self._connected_device["address"] == device_address:
            # Refresh connection status
            try:
                device_obj = self._bus.get_object(BLUEZ_SERVICE_NAME, self._connected_device["path"])
                device_props = dbus.Interface(device_obj, PROPERTIES_INTERFACE)
                return bool(device_props.Get(DEVICE_INTERFACE, "Connected"))
            except dbus.exceptions.DBusException:
                return False
        
        return False

    def _load_saved_devices(self):
        """Load saved devices from file."""
        if not self._paired_devices_file.exists():
            return {}
        
        try:
            with open(self._paired_devices_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load paired devices: {str(e)}")
            return {}

    def save_paired_device(self, device_address, device_name):
        """
        Save a device as the preferred device.

        Args:
            device_address (str): Bluetooth device address
            device_name (str): Human-readable device name

        Returns:
            bool: True if saved successfully
        """
        try:
            # Create config directory if it doesn't exist
            self._config_dir.mkdir(parents=True, exist_ok=True)
            
            # Update saved devices
            self._saved_devices[device_address] = {
                "name": device_name,
                "address": device_address,
                "last_connected": time.time()
            }
            
            # Write to file
            with open(self._paired_devices_file, 'w') as f:
                json.dump(self._saved_devices, f, indent=2)
            
            logger.debug(f"Saved paired device: {device_name} ({device_address})")
            return True
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to save paired device: {str(e)}")
            return False

    def get_saved_devices(self):
        """
        Get all saved devices.

        Returns:
            list: List of saved device dictionaries
        """
        return list(self._saved_devices.values())
