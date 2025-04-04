"""
Bluetooth Manager for the audio module.

This module handles Bluetooth device discovery, pairing, connection,
and management using D-Bus to communicate with BlueZ.
"""

import os
import time
import logging
import threading
import subprocess
import json
from typing import List, Dict, Optional, Tuple, Any

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from .exceptions import (
    BluetoothError,
    BluetoothDiscoveryError,
    BluetoothConnectionError
)

# Configure logging
logger = logging.getLogger(__name__)

# D-Bus constants
BLUEZ_SERVICE = "org.bluez"
ADAPTER_INTERFACE = "org.bluez.Adapter1"
DEVICE_INTERFACE = "org.bluez.Device1"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"


class BluetoothManager:
    """
    Manages Bluetooth connections and device discovery using D-Bus.
    """

    def __init__(self, adapter_path: str = None, config_path: str = None):
        """
        Initialize the Bluetooth manager.

        Args:
            adapter_path (str, optional): D-Bus path to the Bluetooth adapter. 
                If None, the first available adapter will be used.
            config_path (str, optional): Path to the configuration file to 
                store paired devices. Default is ~/.bt_devices.json
        """
        # Initialize D-Bus
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        
        # Configuration
        self.config_path = config_path or os.path.expanduser("~/.bt_devices.json")
        
        # Device tracking
        self.devices = {}  # Discovered devices
        self.connected_device = None  # Currently connected device
        self.discovering = False  # Discovery state
        
        # Load paired devices from config
        self.paired_devices = self._load_paired_devices()
        
        # Set up D-Bus objects
        self._init_bluetooth_objects(adapter_path)
        
        # Set up event loop
        self.mainloop = GLib.MainLoop()
        self.thread = None

    def _init_bluetooth_objects(self, adapter_path: str = None) -> None:
        """
        Initialize D-Bus objects for BlueZ.

        Args:
            adapter_path (str, optional): D-Bus path to the Bluetooth adapter.
                If None, the first available adapter will be used.
        
        Raises:
            BluetoothError: If no Bluetooth adapter is found
        """
        try:
            # Get object manager
            self.obj_manager = dbus.Interface(
                self.bus.get_object(BLUEZ_SERVICE, "/"),
                OBJECT_MANAGER_INTERFACE
            )
            
            # Find the Bluetooth adapter
            if adapter_path:
                self.adapter_path = adapter_path
            else:
                # Find the first available adapter
                self.adapter_path = self._find_adapter()
                
            if not self.adapter_path:
                raise BluetoothError("No Bluetooth adapter found")
                
            # Get adapter object and interface
            self.adapter = self.bus.get_object(BLUEZ_SERVICE, self.adapter_path)
            self.adapter_props = dbus.Interface(self.adapter, PROPERTIES_INTERFACE)
            self.adapter_interface = dbus.Interface(self.adapter, ADAPTER_INTERFACE)
            
            # Register signal handlers
            self.obj_manager.connect_to_signal(
                "InterfacesAdded", self._interfaces_added
            )
            self.obj_manager.connect_to_signal(
                "InterfacesRemoved", self._interfaces_removed
            )
                
            logger.info(f"Bluetooth manager initialized with adapter: {self.adapter_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Bluetooth: {e}")
            raise BluetoothError(f"Failed to initialize Bluetooth: {e}")

    def _find_adapter(self) -> Optional[str]:
        """
        Find the first available Bluetooth adapter.

        Returns:
            str or None: D-Bus path to the first available adapter, or None if not found
        """
        objects = self.obj_manager.GetManagedObjects()
        for path, interfaces in objects.items():
            if ADAPTER_INTERFACE in interfaces:
                return path
        return None

    def _load_paired_devices(self) -> Dict[str, Dict]:
        """
        Load paired devices from configuration file.

        Returns:
            dict: Dictionary of paired devices
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"Failed to load paired devices: {e}")
            return {}

    def _save_paired_devices(self) -> None:
        """Save paired devices to configuration file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.paired_devices, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save paired devices: {e}")

    def _interfaces_added(self, path: str, interfaces: Dict) -> None:
        """
        Handle D-Bus InterfacesAdded signal for device discovery.

        Args:
            path (str): D-Bus path to the object
            interfaces (dict): Interface information
        """
        if DEVICE_INTERFACE in interfaces:
            try:
                properties = interfaces[DEVICE_INTERFACE]
                device_info = self._get_device_info_from_properties(path, properties)
                if device_info:
                    address = device_info.get('address')
                    if address:
                        self.devices[address] = device_info
                        logger.debug(f"Device discovered: {device_info}")
            except Exception as e:
                logger.error(f"Error processing discovered device: {e}")

    def _interfaces_removed(self, path: str, interfaces: List[str]) -> None:
        """
        Handle D-Bus InterfacesRemoved signal.

        Args:
            path (str): D-Bus path to the object
            interfaces (list): List of removed interfaces
        """
        if DEVICE_INTERFACE in interfaces:
            for address, device in list(self.devices.items()):
                if device.get('path') == path:
                    del self.devices[address]
                    logger.debug(f"Device removed: {address}")
                    break

    def _get_device_info_from_properties(
        self, path: str, properties: Dict
    ) -> Optional[Dict]:
        """
        Extract device information from D-Bus properties.

        Args:
            path (str): D-Bus path to the device
            properties (dict): Device properties

        Returns:
            dict or None: Device information dictionary or None if invalid
        """
        try:
            if 'Address' not in properties:
                return None
                
            return {
                'path': path,
                'address': str(properties['Address']),
                'name': str(properties.get('Name', 'Unknown')),
                'paired': bool(properties.get('Paired', False)),
                'trusted': bool(properties.get('Trusted', False)),
                'connected': bool(properties.get('Connected', False)),
                'icon': str(properties.get('Icon', '')),
                'rssi': int(properties.get('RSSI', 0)),
                'audio_sink': 'audio_sink' in properties.get('UUIDs', [])
            }
        except Exception as e:
            logger.error(f"Error extracting device properties: {e}")
            return None

    def _run_event_loop(self) -> None:
        """Run the GLib event loop for D-Bus signals."""
        try:
            self.mainloop.run()
        except Exception as e:
            logger.error(f"Error in Bluetooth event loop: {e}")

    def _get_device_properties(self, device_path: str) -> Dict:
        """
        Get all properties for a Bluetooth device.

        Args:
            device_path (str): D-Bus path to the device

        Returns:
            dict: Device properties
        """
        device = self.bus.get_object(BLUEZ_SERVICE, device_path)
        props_interface = dbus.Interface(device, PROPERTIES_INTERFACE)
        return props_interface.GetAll(DEVICE_INTERFACE)

    def _get_device_path(self, device_address: str) -> Optional[str]:
        """
        Get D-Bus path for a device by its address.

        Args:
            device_address (str): Bluetooth address of the device

        Returns:
            str or None: D-Bus path to the device or None if not found
        """
        # First check our cached devices
        device = self.devices.get(device_address)
        if device and 'path' in device:
            return device['path']
            
        # If not found, query BlueZ
        try:
            objects = self.obj_manager.GetManagedObjects()
            for path, interfaces in objects.items():
                if DEVICE_INTERFACE in interfaces:
                    properties = interfaces[DEVICE_INTERFACE]
                    if str(properties.get('Address', '')).lower() == device_address.lower():
                        return path
            return None
        except Exception as e:
            logger.error(f"Error getting device path: {e}")
            return None

    def _find_device(self, device_address: str) -> Optional[Tuple[Any, Any]]:
        """
        Find a device by its address and return the device object and interface.

        Args:
            device_address (str): Bluetooth address of the device

        Returns:
            tuple or None: (device_object, device_interface) or None if not found
        """
        device_path = self._get_device_path(device_address)
        if not device_path:
            return None
            
        try:
            device = self.bus.get_object(BLUEZ_SERVICE, device_path)
            device_interface = dbus.Interface(device, DEVICE_INTERFACE)
            return (device, device_interface)
        except Exception as e:
            logger.error(f"Error finding device {device_address}: {e}")
            return None

    def start_discovery(self, timeout: int = 30) -> bool:
        """
        Start discovery for Bluetooth devices.

        Args:
            timeout (int, optional): Discovery timeout in seconds (default: 30)

        Returns:
            bool: True if discovery started

        Raises:
            BluetoothDiscoveryError: If discovery cannot be started
        """
        if self.discovering:
            return True
            
        try:
            # Clear previous devices
            self.devices = {}
            
            # Start device discovery
            self.adapter_interface.StartDiscovery()
            self.discovering = True
            
            # Start event loop in a separate thread if not already running
            if not self.thread or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._run_event_loop)
                self.thread.daemon = True
                self.thread.start()
            
            # Set up a timer to stop discovery after timeout
            if timeout > 0:
                def stop_discovery_after_timeout():
                    time.sleep(timeout)
                    if self.discovering:
                        self.stop_discovery()
                
                timer_thread = threading.Thread(target=stop_discovery_after_timeout)
                timer_thread.daemon = True
                timer_thread.start()
            
            logger.info(f"Started Bluetooth discovery (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to start discovery: {e}")
            self.discovering = False
            raise BluetoothDiscoveryError(f"Failed to start discovery: {e}")

    def stop_discovery(self) -> bool:
        """
        Stop the discovery process.

        Returns:
            bool: True if discovery stopped
        """
        if not self.discovering:
            return True
            
        try:
            self.adapter_interface.StopDiscovery()
            self.discovering = False
            logger.info("Stopped Bluetooth discovery")
            return True
        except Exception as e:
            logger.error(f"Failed to stop discovery: {e}")
            return False

    def get_discovered_devices(self) -> List[Dict]:
        """
        Get list of discovered devices.

        Returns:
            list: List of device dictionaries
        """
        # Update device information for all known devices
        updated_devices = {}
        try:
            objects = self.obj_manager.GetManagedObjects()
            for path, interfaces in objects.items():
                if DEVICE_INTERFACE in interfaces:
                    properties = interfaces[DEVICE_INTERFACE]
                    if 'Address' in properties:
                        address = str(properties['Address'])
                        device_info = self._get_device_info_from_properties(path, properties)
                        if device_info:
                            updated_devices[address] = device_info
        except Exception as e:
            logger.error(f"Error updating device list: {e}")
        
        # Update our device cache with the latest information
        for address, device in updated_devices.items():
            self.devices[address] = device
        
        # Return as a list, sorted by name
        return sorted(
            list(self.devices.values()),
            key=lambda x: x.get('name', 'Unknown').lower()
        )

    def pair_device(self, device_address: str) -> bool:
        """
        Pair with a Bluetooth device (establish trusted relationship).
        
        This only pairs the device but does not establish an active connection.
        To use the device, you still need to call connect_device() after pairing.

        Args:
            device_address (str): Bluetooth device address

        Returns:
            bool: True if paired successfully

        Raises:
            BluetoothConnectionError: If pairing fails
        """
        # Ensure device exists
        device_info = self._find_device(device_address)
        if not device_info:
            raise BluetoothConnectionError(f"Device {device_address} not found")
            
        device, device_interface = device_info
        
        try:
            # Stop discovery if active
            if self.discovering:
                self.stop_discovery()
            
            # Get device properties
            props_interface = dbus.Interface(device, PROPERTIES_INTERFACE)
            properties = props_interface.GetAll(DEVICE_INTERFACE)
            
            # Check if already paired
            if properties.get('Paired', False):
                logger.info(f"Device {device_address} is already paired")
                
                # Trust device if not already trusted
                if not properties.get('Trusted', False):
                    props_interface.Set(DEVICE_INTERFACE, 'Trusted', True)
                    logger.info(f"Set device {device_address} as trusted")
                
                return True
            
            # Trust device
            props_interface.Set(DEVICE_INTERFACE, 'Trusted', True)
            logger.info(f"Set device {device_address} as trusted")
            
            # Perform pairing
            logger.info(f"Pairing with device {device_address}...")
            device_interface.Pair()
            
            # Wait for pairing to complete
            for _ in range(10):  # Try up to 10 times with 1s delay
                properties = props_interface.GetAll(DEVICE_INTERFACE)
                if properties.get('Paired', False):
                    # Save to paired devices
                    if device_address not in self.paired_devices:
                        self.paired_devices[device_address] = {
                            'name': str(properties.get('Name', 'Unknown')),
                            'address': device_address,
                            'last_connected': 0  # Not connected yet
                        }
                        self._save_paired_devices()
                    
                    logger.info(f"Successfully paired with {device_address}")
                    return True
                time.sleep(1)
                
            raise BluetoothConnectionError(
                f"Timed out waiting for pairing with {device_address}"
            )
        except Exception as e:
            logger.error(f"Failed to pair with {device_address}: {e}")
            raise BluetoothConnectionError(f"Failed to pair with {device_address}: {e}")
    
    def connect_device(self, device_address: str, auto_pair: bool = True) -> bool:
        """
        Connect to a Bluetooth device.
        
        This establishes an active connection to an already paired device.
        If the device is not paired and auto_pair is True, it will attempt to pair first.

        Args:
            device_address (str): Bluetooth device address
            auto_pair (bool, optional): Whether to automatically pair if not paired

        Returns:
            bool: True if connected successfully

        Raises:
            BluetoothConnectionError: If connection fails
        """
        # Ensure device exists
        device_info = self._find_device(device_address)
        if not device_info:
            raise BluetoothConnectionError(f"Device {device_address} not found")
            
        device, device_interface = device_info
        
        try:
            # Stop discovery if active
            if self.discovering:
                self.stop_discovery()
            
            # Get device properties
            props_interface = dbus.Interface(device, PROPERTIES_INTERFACE)
            properties = props_interface.GetAll(DEVICE_INTERFACE)
            
            # Pair if not already paired and auto_pair is enabled
            if not properties.get('Paired', False):
                if auto_pair:
                    logger.info(f"Device {device_address} not paired, attempting to pair first")
                    if not self.pair_device(device_address):
                        raise BluetoothConnectionError(f"Failed to pair with {device_address}")
                else:
                    raise BluetoothConnectionError(f"Device {device_address} is not paired")
            
            # Connect to the device
            logger.info(f"Connecting to device {device_address}...")
            device_interface.Connect()
            
            # Wait for connection to establish
            for _ in range(10):  # Try up to 10 times with 1s delay
                properties = props_interface.GetAll(DEVICE_INTERFACE)
                if properties.get('Connected', False):
                    # Get updated device info
                    self.connected_device = device_address
                    
                    # Check if device supports audio sink profile (A2DP)
                    uuids = properties.get('UUIDs', [])
                    logger.info(f"Device UUIDs: {uuids}")
                    
                    # The Audio Sink UUID for A2DP
                    a2dp_sink_uuid = '0000110b-0000-1000-8000-00805f9b34fb'
                    
                    # Check if device supports A2DP sink
                    if a2dp_sink_uuid in uuids:
                        logger.info(f"Device {device_address} supports A2DP audio sink")
                        
                        # Ensure A2DP profile is connected
                        try:
                            # Connect specifically to the A2DP profile
                            subprocess.run(
                                ["bluetoothctl", "connect", device_address],
                                capture_output=True,
                                text=True
                            )
                            
                            # Check if bluealsa-aplay recognizes the device
                            result = subprocess.run(
                                ["bluealsa-aplay", "-l"],
                                capture_output=True,
                                text=True
                            )
                            
                            if device_address in result.stdout:
                                logger.info(f"Device {device_address} successfully registered with BlueALSA")
                            else:
                                logger.warning(f"Device {device_address} not found in BlueALSA device list")
                                
                        except Exception as e:
                            logger.warning(f"Error setting up A2DP profile: {e}")
                    else:
                        logger.warning(f"Device {device_address} does not support A2DP audio sink")
                    
                    # Update last connected time in paired devices
                    if device_address in self.paired_devices:
                        self.paired_devices[device_address]['last_connected'] = time.time()
                        self._save_paired_devices()
                    
                    logger.info(f"Successfully connected to {device_address}")
                    return True
                time.sleep(1)
                
            raise BluetoothConnectionError(
                f"Timed out waiting for connection to {device_address}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to {device_address}: {e}")
            raise BluetoothConnectionError(f"Failed to connect to {device_address}: {e}")

    def disconnect_device(self, device_address: str = None) -> bool:
        """
        Disconnect the current device or a specific device.

        Args:
            device_address (str, optional): Bluetooth device address to disconnect.
                If None, disconnects the currently connected device.

        Returns:
            bool: True if disconnected successfully
        """
        # If no address provided, use currently connected device
        if not device_address and self.connected_device:
            device_address = self.connected_device
            
        if not device_address:
            logger.warning("No device to disconnect")
            return False
            
        # Ensure device exists
        device_info = self._find_device(device_address)
        if not device_info:
            logger.warning(f"Device {device_address} not found for disconnection")
            return False
            
        device, device_interface = device_info
        
        try:
            # Check if device is connected
            props_interface = dbus.Interface(device, PROPERTIES_INTERFACE)
            properties = props_interface.GetAll(DEVICE_INTERFACE)
            
            if not properties.get('Connected', False):
                logger.info(f"Device {device_address} is not connected")
                if self.connected_device == device_address:
                    self.connected_device = None
                return True
                
            # Disconnect
            logger.info(f"Disconnecting from {device_address}...")
            device_interface.Disconnect()
            
            # Reset connected device if it was the one we disconnected
            if self.connected_device == device_address:
                self.connected_device = None
                
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect from {device_address}: {e}")
            return False

    def forget_device(self, device_address: str) -> bool:
        """
        Remove a paired device.

        Args:
            device_address (str): Bluetooth device address

        Returns:
            bool: True if device was forgotten
        """
        # Ensure device exists
        device_info = self._find_device(device_address)
        if not device_info:
            logger.warning(f"Device {device_address} not found for removal")
            return False
            
        device, device_interface = device_info
        
        try:
            # Disconnect if connected
            props_interface = dbus.Interface(device, PROPERTIES_INTERFACE)
            properties = props_interface.GetAll(DEVICE_INTERFACE)
            
            if properties.get('Connected', False):
                self.disconnect_device(device_address)
                
            # Remove device
            self.adapter_interface.RemoveDevice(device.object_path)
            
            # Remove from paired devices
            if device_address in self.paired_devices:
                del self.paired_devices[device_address]
                self._save_paired_devices()
                
            logger.info(f"Forgot device {device_address}")
            return True
        except Exception as e:
            logger.error(f"Failed to forget device {device_address}: {e}")
            return False

    def get_connected_device(self) -> Optional[Dict]:
        """
        Get information about the currently connected device.

        Returns:
            dict or None: Device information or None if not connected
        """
        if not self.connected_device:
            return None
            
        device_path = self._get_device_path(self.connected_device)
        if not device_path:
            self.connected_device = None
            return None
            
        try:
            properties = self._get_device_properties(device_path)
            # Verify the device is actually connected
            if not properties.get('Connected', False):
                self.connected_device = None
                return None
                
            return self._get_device_info_from_properties(device_path, properties)
        except Exception as e:
            logger.error(f"Error getting connected device info: {e}")
            return None

    def is_device_connected(self, device_address: str = None) -> bool:
        """
        Check if a device is connected.

        Args:
            device_address (str, optional): Device to check, or current device if None

        Returns:
            bool: True if device is connected
        """
        # If no address provided, use currently connected device
        if not device_address:
            return self.get_connected_device() is not None
            
        device_path = self._get_device_path(device_address)
        if not device_path:
            return False
            
        try:
            properties = self._get_device_properties(device_path)
            return bool(properties.get('Connected', False))
        except Exception:
            return False

    def get_paired_devices(self) -> List[Dict]:
        """
        Get all paired devices.

        Returns:
            list: List of paired device dictionaries
        """
        paired_list = []
        
        # Get data from BlueZ
        try:
            objects = self.obj_manager.GetManagedObjects()
            for path, interfaces in objects.items():
                if DEVICE_INTERFACE in interfaces:
                    properties = interfaces[DEVICE_INTERFACE]
                    if bool(properties.get('Paired', False)):
                        device_info = self._get_device_info_from_properties(path, properties)
                        if device_info:
                            paired_list.append(device_info)
        except Exception as e:
            logger.error(f"Error getting paired devices from BlueZ: {e}")
        
        # Update our paired devices cache from BlueZ data
        for device in paired_list:
            address = device.get('address')
            if address and address not in self.paired_devices:
                self.paired_devices[address] = {
                    'name': device.get('name', 'Unknown'),
                    'address': address,
                    'last_connected': time.time()
                }
        
        self._save_paired_devices()
        return paired_list

    def reconnect_last_device(self) -> bool:
        """
        Attempt to reconnect to the last connected device.

        Returns:
            bool: True if reconnection was successful
        """
        if not self.paired_devices:
            logger.info("No paired devices to reconnect to")
            return False
            
        # Sort devices by last connected time
        sorted_devices = sorted(
            self.paired_devices.items(),
            key=lambda x: x[1].get('last_connected', 0),
            reverse=True
        )
        
        # Try to connect to the most recently used device
        for address, _ in sorted_devices:
            try:
                logger.info(f"Attempting to reconnect to {address}")
                self.connect_device(address)
                return True
            except Exception as e:
                logger.warning(f"Failed to reconnect to {address}: {e}")
                continue
                
        return False

    def get_adapter_info(self) -> Dict:
        """
        Get information about the Bluetooth adapter.

        Returns:
            dict: Adapter information
        """
        try:
            properties = self.adapter_props.GetAll(ADAPTER_INTERFACE)
            return {
                'address': str(properties.get('Address', '')),
                'name': str(properties.get('Name', '')),
                'alias': str(properties.get('Alias', '')),
                'powered': bool(properties.get('Powered', False)),
                'discoverable': bool(properties.get('Discoverable', False)),
                'pairable': bool(properties.get('Pairable', False)),
                'discovering': bool(properties.get('Discovering', False))
            }
        except Exception as e:
            logger.error(f"Error getting adapter info: {e}")
            return {}

    def set_adapter_power(self, powered: bool) -> bool:
        """
        Turn the Bluetooth adapter on or off.

        Args:
            powered (bool): True to power on, False to power off

        Returns:
            bool: True if operation was successful
        """
        try:
            self.adapter_props.Set(ADAPTER_INTERFACE, 'Powered', dbus.Boolean(powered))
            return True
        except Exception as e:
            logger.error(f"Failed to set adapter power to {powered}: {e}")
            return False

    def shutdown(self) -> None:
        """Clean up resources before shutdown."""
        try:
            if self.discovering:
                self.stop_discovery()
                
            if self.mainloop and self.mainloop.is_running():
                self.mainloop.quit()
                
            logger.info("Bluetooth manager shutdown complete")
        except Exception as e:
            logger.error(f"Error during Bluetooth manager shutdown: {e}")


def get_bluetooth_status() -> Dict:
    """
    Get the current status of Bluetooth using system commands.
    
    This is a simple helper function that doesn't require DBus setup.

    Returns:
        dict: Bluetooth status information
    """
    status = {
        'available': False,
        'powered': False,
        'bluealsa_running': False
    }
    
    try:
        # Check if Bluetooth service is running
        result = subprocess.run(
            ["systemctl", "is-active", "bluetooth"], 
            capture_output=True, 
            text=True
        )
        status['available'] = result.stdout.strip() == "active"
        
        # Check if adapter is powered on
        if status['available']:
            result = subprocess.run(
                ["bluetoothctl", "show"], 
                capture_output=True, 
                text=True
            )
            status['powered'] = "Powered: yes" in result.stdout
            
        # Check BlueALSA status
        result = subprocess.run(
            ["systemctl", "is-active", "bluealsa"], 
            capture_output=True, 
            text=True
        )
        status['bluealsa_running'] = result.stdout.strip() == "active"
        
        return status
    except Exception as e:
        logger.error(f"Error checking Bluetooth status: {e}")
        return status
