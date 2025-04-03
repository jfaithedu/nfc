"""
system_utils.py - System-level utilities for the NFC music player application.

This module provides utilities for interacting with the Raspberry Pi system.
"""

import os
import subprocess
import platform
import socket
import time
from typing import Dict, List, Optional, Union, Any

try:
    import psutil
except ImportError:
    psutil = None

try:
    from gpiozero import Device, Pin
    from gpiozero.pins.mock import MockFactory
    # Use MockFactory if not running on RPi (for development/testing)
    if not os.path.exists('/sys/class/gpio'):
        Device.pin_factory = MockFactory()
except ImportError:
    Pin = None

from .exceptions import SystemError
from .logger import get_logger

logger = get_logger("system_utils")


def get_system_info() -> Dict[str, Any]:
    """
    Get system information.

    Returns:
        dict: System information including:
            - os_name: Operating system name
            - os_version: Operating system version
            - hostname: System hostname
            - uptime: System uptime in seconds
            - cpu_usage: CPU usage as a percentage
            - memory_usage: Memory usage as a percentage
            - disk_usage: Disk usage as a percentage
    """
    info = {
        'os_name': platform.system(),
        'os_version': platform.release(),
        'hostname': socket.gethostname(),
        'uptime': None,
        'cpu_usage': None,
        'memory_usage': None,
        'disk_usage': None
    }
    
    # Get uptime
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            info['uptime'] = uptime_seconds
    except:
        logger.warning("Failed to get uptime from /proc/uptime")
    
    # Use psutil for resource information if available
    if psutil:
        try:
            info['cpu_usage'] = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            info['memory_usage'] = memory.percent
            disk = psutil.disk_usage('/')
            info['disk_usage'] = disk.percent
        except Exception as e:
            logger.warning(f"Error getting system resources with psutil: {e}")
    
    return info


def restart_service(service_name: str) -> bool:
    """
    Restart a system service.

    Args:
        service_name (str): Name of the service

    Returns:
        bool: True if restart successful
    """
    try:
        # Check if systemctl is available
        if os.path.exists('/bin/systemctl'):
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', service_name],
                capture_output=True,
                text=True,
                check=True
            )
            return result.returncode == 0
        else:
            # Fallback to service command
            result = subprocess.run(
                ['sudo', 'service', service_name, 'restart'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to restart service {service_name}: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error restarting service {service_name}: {str(e)}")
        return False


def check_network_status() -> Dict[str, Any]:
    """
    Check network connectivity.

    Returns:
        dict: Network status information including:
            - connected: True if connected to a network
            - interface: Active network interface
            - ip_address: IP address
            - wifi_strength: WiFi signal strength if applicable
    """
    status = {
        'connected': False,
        'interface': None,
        'ip_address': None,
        'wifi_strength': None
    }
    
    try:
        # Check if we have an IP address (other than localhost)
        if psutil:
            for interface, addresses in psutil.net_if_addrs().items():
                for addr in addresses:
                    # Skip loopback addresses
                    if addr.address == '127.0.0.1' or addr.address == '::1':
                        continue
                    
                    # Found a valid IP address
                    if addr.family == socket.AF_INET:
                        status['connected'] = True
                        status['interface'] = interface
                        status['ip_address'] = addr.address
                        break
                
                if status['connected']:
                    break
        
        # If not connected according to psutil, try socket
        if not status['connected']:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Try to connect to a public DNS server (doesn't actually send packets)
            s.connect(("8.8.8.8", 80))
            status['ip_address'] = s.getsockname()[0]
            status['connected'] = True
            s.close()
            
        # Get WiFi signal strength if connected via WiFi
        if status['interface'] and 'wlan' in status['interface']:
            try:
                result = subprocess.run(
                    ['iwconfig', status['interface']],
                    capture_output=True,
                    text=True
                )
                output = result.stdout
                
                # Parse signal level
                if 'Signal level=' in output:
                    signal_part = output.split('Signal level=')[1].split(' ')[0]
                    if 'dBm' in signal_part:
                        status['wifi_strength'] = int(signal_part.replace('dBm', ''))
                    else:
                        status['wifi_strength'] = int(signal_part)
            except Exception as e:
                logger.warning(f"Failed to get WiFi signal strength: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error checking network status: {str(e)}")
    
    return status


def check_process_running(process_name: str) -> bool:
    """
    Check if a process is running.

    Args:
        process_name (str): Process name

    Returns:
        bool: True if process is running
    """
    if psutil:
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == process_name:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking process status with psutil: {str(e)}")
    
    # Fallback to pgrep
    try:
        result = subprocess.run(
            ['pgrep', '-f', process_name],
            capture_output=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking process status with pgrep: {str(e)}")
        return False


def reboot_system() -> bool:
    """
    Reboot the system (requires appropriate permissions).

    Returns:
        bool: True if reboot command was issued
    """
    try:
        logger.warning("System reboot initiated")
        result = subprocess.run(
            ['sudo', 'reboot'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to reboot system: {str(e)}")
        return False


def shutdown_system() -> bool:
    """
    Shutdown the system (requires appropriate permissions).

    Returns:
        bool: True if shutdown command was issued
    """
    try:
        logger.warning("System shutdown initiated")
        result = subprocess.run(
            ['sudo', 'shutdown', '-h', 'now'],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to shutdown system: {str(e)}")
        return False


def get_bluetooth_devices() -> List[Dict[str, str]]:
    """
    Get list of bluetooth devices.

    Returns:
        list: List of bluetooth device dictionaries with keys:
            - address: Device MAC address
            - name: Device name
            - connected: True if connected
    """
    devices = []
    
    try:
        # Use bluetoothctl to list devices
        result = subprocess.run(
            ['bluetoothctl', 'devices'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            device_lines = result.stdout.splitlines()
            
            for line in device_lines:
                # Parse device lines: "Device 00:11:22:33:44:55 DeviceName"
                if line.startswith("Device "):
                    parts = line.split(" ", 2)
                    if len(parts) >= 3:
                        address = parts[1]
                        name = parts[2]
                        
                        # Check if device is connected
                        info_result = subprocess.run(
                            ['bluetoothctl', 'info', address],
                            capture_output=True,
                            text=True
                        )
                        connected = "Connected: yes" in info_result.stdout
                        
                        devices.append({
                            'address': address,
                            'name': name,
                            'connected': connected
                        })
    except Exception as e:
        logger.error(f"Error getting Bluetooth devices: {str(e)}")
    
    return devices


def get_gpio_pin(pin_number: int) -> Optional[Pin]:
    """
    Get a GPIO pin object.

    Args:
        pin_number (int): BCM pin number

    Returns:
        Pin: GPIO pin object or None if gpiozero not available
    """
    if Pin is None:
        logger.error("gpiozero module not available, GPIO operations not supported")
        return None
        
    try:
        return Pin(pin_number)
    except Exception as e:
        logger.error(f"Error accessing GPIO pin {pin_number}: {str(e)}")
        return None


def is_running_on_pi() -> bool:
    """
    Check if code is running on a Raspberry Pi.
    
    Returns:
        bool: True if running on a Raspberry Pi
    """
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return 'Raspberry Pi' in f.read() or 'BCM' in f.read()
    except:
        return False
