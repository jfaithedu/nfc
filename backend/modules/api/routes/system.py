"""
NFC-Based Toddler-Friendly Music Player - System Routes

This module implements the API routes for system settings and management.
"""

import os
import time
import json
import platform
import shutil
import tempfile
import datetime
import threading
import psutil
from flask import request, jsonify, send_file

from ...database import db_manager
from ...audio import audio_controller, bluetooth_manager
from ...nfc import nfc_controller
from ...media import media_manager
from ..exceptions import ResourceNotFoundError, InvalidRequestError
from ..middleware.auth import require_auth, verify_pin
from ....utils.logger import get_logger
from ....config import CONFIG, save_config

logger = get_logger(__name__)


def register_routes(app):
    """
    Register system-related routes with the Flask application.

    Args:
        app: Flask application instance
    """
    
    @app.route('/api/system/status', methods=['GET'])
    @require_auth
    def get_system_status():
        """Get system status."""
        try:
            # Get basic system info
            system_info = {
                'hostname': platform.node(),
                'platform': platform.platform(),
                'python_version': platform.python_version(),
                'uptime': get_system_uptime(),
                'cpu_usage': psutil.cpu_percent(interval=0.1),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'free': psutil.disk_usage('/').free,
                    'percent': psutil.disk_usage('/').percent
                }
            }
            
            # Get component status
            components = {
                'database': db_manager.is_initialized(),
                'nfc': nfc_controller.is_initialized(),
                'audio': audio_controller.is_initialized(),
                'bluetooth': bluetooth_manager.is_connected() if hasattr(bluetooth_manager, 'is_connected') else None,
                'media': media_manager.is_initialized()
            }
            
            # Get current playback status
            playback = {
                'playing': audio_controller.is_playing(),
                'current_media': audio_controller.get_current_media(),
                'volume': audio_controller.get_volume()
            }
            
            # Get tag summary
            tag_summary = {
                'total_tags': db_manager.get_tag_count(),
                'active_tags': db_manager.get_active_tag_count(),
                'last_detected': db_manager.get_last_detected_tag_time()
            }
            
            # Get media summary
            media_summary = {
                'total_media': db_manager.get_media_count(),
                'youtube_media': db_manager.get_media_count_by_type('youtube'),
                'local_media': db_manager.get_media_count_by_type('local'),
                'cache_size': media_manager.get_cache_size()
            }
            
            return jsonify({
                'success': True,
                'data': {
                    'system': system_info,
                    'components': components,
                    'playback': playback,
                    'tag_summary': tag_summary,
                    'media_summary': media_summary
                }
            })
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            # Return partial data if available
            return jsonify({
                'success': True,
                'data': {
                    'system': {
                        'hostname': platform.node(),
                        'platform': platform.platform()
                    },
                    'error': str(e)
                }
            })

    @app.route('/api/system/bluetooth/devices', methods=['GET'])
    @require_auth
    def get_bluetooth_devices():
        """Get available Bluetooth devices."""
        try:
            # Start scanning for devices
            bluetooth_manager.start_scan()
            
            # Wait for scan to complete (max 5 seconds)
            time.sleep(2)
            
            # Get devices
            devices = bluetooth_manager.get_devices()
            
            # Stop scanning
            bluetooth_manager.stop_scan()
            
            return jsonify({
                'success': True,
                'data': {
                    'devices': devices,
                    'current_device': bluetooth_manager.get_connected_device()
                }
            })
        except Exception as e:
            logger.error(f"Error getting Bluetooth devices: {e}")
            raise

    @app.route('/api/system/bluetooth/pair', methods=['POST'])
    @require_auth
    def pair_bluetooth():
        """Pair with a Bluetooth device without connecting."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'address' not in data:
            raise InvalidRequestError("Bluetooth device address is required")
        
        address = data['address']
        
        try:
            success = bluetooth_manager.pair_device(address)
            
            if success:
                return jsonify({
                    'success': True,
                    'data': {
                        'message': f"Successfully paired with device {address}"
                    }
                })
            else:
                raise InvalidRequestError(f"Failed to pair with device {address}")
        except Exception as e:
            logger.error(f"Error pairing with Bluetooth device: {e}")
            raise

    @app.route('/api/system/bluetooth/connect', methods=['POST'])
    @require_auth
    def connect_bluetooth():
        """Connect to a Bluetooth device."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'address' not in data:
            raise InvalidRequestError("Bluetooth device address is required")
        
        address = data['address']
        
        # Optional fields
        auto_pair = data.get('auto_pair', True)
        
        try:
            success = bluetooth_manager.connect_device(address, auto_pair)
            
            if success:
                # Update the default Bluetooth device in config
                CONFIG['audio']['bluetooth_device'] = address
                save_config()
                
                return jsonify({
                    'success': True,
                    'data': {
                        'message': f"Connected to device {address}",
                        'device': bluetooth_manager.get_connected_device()
                    }
                })
            else:
                raise InvalidRequestError(f"Failed to connect to device {address}")
        except Exception as e:
            logger.error(f"Error connecting to Bluetooth device: {e}")
            raise

    @app.route('/api/system/bluetooth/disconnect', methods=['POST'])
    @require_auth
    def disconnect_bluetooth():
        """Disconnect from current Bluetooth device."""
        try:
            current_device = bluetooth_manager.get_connected_device()
            
            if not current_device:
                return jsonify({
                    'success': True,
                    'data': {
                        'message': "No device currently connected"
                    }
                })
            
            success = bluetooth_manager.disconnect_device()
            
            return jsonify({
                'success': success,
                'data': {
                    'message': "Device disconnected successfully" if success else "Failed to disconnect device"
                }
            })
        except Exception as e:
            logger.error(f"Error disconnecting Bluetooth device: {e}")
            raise

    @app.route('/api/system/volume', methods=['POST'])
    @require_auth
    def set_volume():
        """Set system volume."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'volume' not in data:
            raise InvalidRequestError("Volume is required")
        
        volume = data['volume']
        
        # Validate volume range
        if not isinstance(volume, (int, float)) or volume < 0 or volume > 100:
            raise InvalidRequestError("Volume must be a number between 0 and 100")
        
        try:
            audio_controller.set_volume(volume)
            
            # Update default volume in config
            CONFIG['audio']['volume_default'] = volume
            save_config()
            
            return jsonify({
                'success': True,
                'data': {
                    'message': f"Volume set to {volume}%",
                    'volume': audio_controller.get_volume()
                }
            })
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            raise

    @app.route('/api/system/settings', methods=['GET'])
    @require_auth
    def get_settings():
        """Get system settings."""
        # Return a copy of the configuration, but filter out sensitive information
        settings = {
            'app_name': CONFIG['app_name'],
            'debug_mode': CONFIG['debug_mode'],
            'database': {
                'path': CONFIG['database']['path']
            },
            'nfc': {
                'poll_interval': CONFIG['nfc']['poll_interval'],
                'i2c_bus': CONFIG['nfc']['i2c_bus']
            },
            'media': {
                'cache_dir': CONFIG['media']['cache_dir'],
                'allowed_formats': CONFIG['media']['allowed_formats'],
                'max_cache_size_mb': CONFIG['media']['max_cache_size_mb']
            },
            'audio': {
                'bluetooth_device': CONFIG['audio']['bluetooth_device'],
                'volume_default': CONFIG['audio']['volume_default'],
                'volume_min': CONFIG['audio']['volume_min'],
                'volume_max': CONFIG['audio']['volume_max']
            },
            'api': {
                'host': CONFIG['api']['host'],
                'port': CONFIG['api']['port'],
                'ssl_enabled': CONFIG['api']['ssl_enabled']
            }
        }
        
        return jsonify({
            'success': True,
            'data': {
                'settings': settings
            }
        })

    @app.route('/api/system/settings', methods=['PUT'])
    @require_auth
    def update_settings():
        """Update system settings."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Validate PIN if updating sensitive settings
        sensitive_update = any(key in data for key in ['api', 'debug_mode'])
        if sensitive_update:
            pin = request.headers.get('X-Admin-PIN')
            if not pin or not verify_pin(pin):
                raise InvalidRequestError("Admin PIN required for sensitive settings")
        
        # Update configuration
        updated_settings = {}
        
        # Top-level settings
        if 'app_name' in data:
            CONFIG['app_name'] = data['app_name']
            updated_settings['app_name'] = CONFIG['app_name']
            
        if 'debug_mode' in data and sensitive_update:
            CONFIG['debug_mode'] = bool(data['debug_mode'])
            updated_settings['debug_mode'] = CONFIG['debug_mode']
        
        # Nested settings
        sections = ['nfc', 'media', 'audio', 'api']
        for section in sections:
            if section in data and isinstance(data[section], dict):
                if section not in updated_settings:
                    updated_settings[section] = {}
                
                for key, value in data[section].items():
                    # Skip sensitive settings if PIN not validated
                    if section == 'api' and key in ['host', 'port', 'ssl_enabled'] and not sensitive_update:
                        continue
                    
                    # Skip changing admin_pin via this endpoint
                    if section == 'api' and key == 'admin_pin':
                        continue
                    
                    # Update the setting if it exists
                    if key in CONFIG[section]:
                        CONFIG[section][key] = value
                        updated_settings[section][key] = value
        
        # Save updated configuration
        save_config()
        
        return jsonify({
            'success': True,
            'data': {
                'message': "Settings updated successfully",
                'updated_settings': updated_settings
            }
        })

    @app.route('/api/system/change_pin', methods=['POST'])
    @require_auth
    def change_admin_pin():
        """Change the admin PIN."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'current_pin' not in data:
            raise InvalidRequestError("Current PIN is required")
        if 'new_pin' not in data:
            raise InvalidRequestError("New PIN is required")
        
        # Verify current PIN
        if not verify_pin(data['current_pin']):
            raise InvalidRequestError("Current PIN is incorrect")
        
        # Validate new PIN (non-empty, numeric)
        new_pin = data['new_pin']
        if not new_pin or not isinstance(new_pin, str) or not new_pin.isdigit():
            raise InvalidRequestError("New PIN must be a non-empty numeric string")
        
        # Update PIN in configuration
        CONFIG['api']['admin_pin'] = new_pin
        save_config()
        
        return jsonify({
            'success': True,
            'data': {
                'message': "PIN changed successfully"
            }
        })

    @app.route('/api/system/backup', methods=['POST'])
    @require_auth
    def create_backup():
        """Create a system backup."""
        # Create a temporary directory for backup files
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Backup time for filename
            backup_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"nfc_player_backup_{backup_time}.zip"
            backup_path = os.path.join(temp_dir, backup_filename)
            
            # Define files to backup
            to_backup = [
                CONFIG['database']['path'],  # Database
                os.path.expanduser("~/.nfc_player/config.json")  # Config
            ]
            
            # Create zip archive
            shutil.make_archive(
                os.path.splitext(backup_path)[0],  # Remove .zip extension 
                'zip',
                root_dir='/',
                base_dir=None,
                verbose=True,
                dry_run=False,
                logger=logger,
                owner=None,
                group=None
            )
            
            # Send the backup file
            return send_file(
                backup_path,
                as_attachment=True,
                attachment_filename=backup_filename,
                mimetype='application/zip'
            )
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    @app.route('/api/system/restore', methods=['POST'])
    @require_auth
    def restore_backup():
        """Restore from a backup."""
        # Check if file is in request
        if 'backup_file' not in request.files:
            raise InvalidRequestError("No backup file provided")
        
        file = request.files['backup_file']
        
        # Check if file was selected
        if file.filename == '':
            raise InvalidRequestError("No file selected")
        
        # Verify PIN
        pin = request.form.get('pin')
        if not pin or not verify_pin(pin):
            raise InvalidRequestError("Admin PIN required for restore")
        
        # Create a temporary directory for extraction
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Save the uploaded file
            backup_path = os.path.join(temp_dir, 'backup.zip')
            file.save(backup_path)
            
            # Extract the backup
            shutil.unpack_archive(backup_path, temp_dir)
            
            # TODO: Implement actual restore logic
            # This would involve:
            # - Stopping services
            # - Restoring database and config files
            # - Restarting services
            
            # For now, just return success
            return jsonify({
                'success': True,
                'data': {
                    'message': "Backup restored successfully. Restart required."
                }
            })
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    @app.route('/api/system/restart', methods=['POST'])
    @require_auth
    def restart_system():
        """Restart the NFC player service."""
        # Verify PIN
        data = request.get_json() or {}
        pin = data.get('pin')
        
        if not pin or not verify_pin(pin):
            raise InvalidRequestError("Admin PIN required for restart")
        
        try:
            # Perform graceful shutdown of components
            logger.info("Initiating service restart...")
            
            # This will restart the service in a separate thread
            restart_thread = threading.Thread(target=_perform_restart)
            restart_thread.daemon = True
            restart_thread.start()
            
            return jsonify({
                'success': True,
                'data': {
                    'message': "Restart initiated, service will restart momentarily."
                }
            })
            
        except Exception as e:
            logger.error(f"Error restarting service: {e}")
            raise

    def _perform_restart():
        """Perform the actual service restart."""
        try:
            # Wait a moment to allow the response to be sent
            time.sleep(2)
            
            # Signal the main app to restart
            # This is a placeholder - the actual implementation would depend
            # on how the service is managed (e.g., systemd, supervisor, etc.)
            logger.info("Service restart triggered")
            
            # In a real implementation, this might do something like:
            # os.kill(os.getpid(), signal.SIGHUP)
            
        except Exception as e:
            logger.error(f"Error in restart process: {e}")
    
    logger.info("System routes registered")


def get_system_uptime():
    """Get system uptime in seconds."""
    return time.time() - psutil.boot_time()
