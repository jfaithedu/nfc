"""
NFC-Based Toddler-Friendly Music Player - NFC Writer Routes

This module implements the API routes for writing to NFC tags.
"""

import threading
import time
from flask import request, jsonify

from ...nfc import nfc_controller
from ..exceptions import ResourceNotFoundError, InvalidRequestError, TagWriteError
from ..middleware.auth import require_auth
from . import get_logger

logger = get_logger(__name__)

# Track write mode state
write_mode = {
    'active': False,
    'start_time': None,
    'data_to_write': None,
    'tag_uid': None
}

# Thread for write mode
write_mode_thread = None
write_mode_stop_event = threading.Event()


def register_routes(app):
    """
    Register NFC writer routes with the Flask application.

    Args:
        app: Flask application instance
    """
    
    @app.route('/api/nfc/write/start', methods=['POST'])
    @require_auth
    def start_write_mode():
        """Start NFC tag writing mode."""
        global write_mode, write_mode_thread, write_mode_stop_event
        
        # Check if already in write mode
        if write_mode['active']:
            return jsonify({
                'success': True,
                'data': {
                    'message': "Write mode already active",
                    'status': write_mode
                }
            })
        
        # Get request data
        data = request.get_json() or {}
        timeout = data.get('timeout', 60)  # Default 60 seconds timeout
        data_to_write = data.get('data')
        tag_uid = data.get('tag_uid')
        
        # Start write mode
        write_mode_stop_event.clear()
        write_mode = {
            'active': True,
            'start_time': time.time(),
            'timeout': timeout,
            'data_to_write': data_to_write,
            'tag_uid': tag_uid
        }
        
        # Start write mode in a separate thread
        write_mode_thread = threading.Thread(
            target=_write_mode_thread,
            args=(write_mode_stop_event, timeout)
        )
        write_mode_thread.daemon = True
        write_mode_thread.start()
        
        return jsonify({
            'success': True,
            'data': {
                'message': "Write mode started",
                'status': write_mode
            }
        })

    @app.route('/api/nfc/write/stop', methods=['POST'])
    @require_auth
    def stop_write_mode():
        """Stop NFC tag writing mode."""
        global write_mode, write_mode_stop_event
        
        # Check if write mode is active
        if not write_mode['active']:
            return jsonify({
                'success': True,
                'data': {
                    'message': "Write mode not active",
                    'status': write_mode
                }
            })
        
        # Stop write mode
        write_mode_stop_event.set()
        write_mode['active'] = False
        
        return jsonify({
            'success': True,
            'data': {
                'message': "Write mode stopped",
                'status': write_mode
            }
        })

    @app.route('/api/nfc/write/status', methods=['GET'])
    @require_auth
    def get_write_status():
        """Get the status of write mode."""
        global write_mode
        
        # Add elapsed time if active
        if write_mode['active'] and write_mode['start_time']:
            elapsed = time.time() - write_mode['start_time']
            timeout = write_mode['timeout']
            remaining = max(0, timeout - elapsed)
            
            status = {
                **write_mode,
                'elapsed': elapsed,
                'remaining': remaining
            }
        else:
            status = write_mode
        
        return jsonify({
            'success': True,
            'data': {
                'status': status
            }
        })

    @app.route('/api/nfc/write/<tag_uid>', methods=['POST'])
    @require_auth
    def write_tag(tag_uid):
        """Write data to a specific tag."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'data' not in data:
            raise InvalidRequestError("Data to write is required")
        
        # Get data to write
        raw_data = data['data']
        
        try:
            success = nfc_controller.write_tag(tag_uid, raw_data)
            
            if not success:
                raise TagWriteError(f"Failed to write to tag {tag_uid}")
            
            return jsonify({
                'success': True,
                'data': {
                    'message': f"Data written to tag {tag_uid}",
                    'tag_uid': tag_uid
                }
            })
        except Exception as e:
            logger.error(f"Error writing to tag: {e}")
            raise TagWriteError(str(e))

    @app.route('/api/nfc/read', methods=['GET'])
    @require_auth
    def read_tag_data():
        """Read raw data from a detected tag."""
        # Poll for tag
        tag_uid, raw_data = nfc_controller.read_tag_data()
        
        if not tag_uid:
            return jsonify({
                'success': False,
                'data': {
                    'message': "No tag detected"
                }
            })
        
        return jsonify({
            'success': True,
            'data': {
                'tag_uid': tag_uid,
                'raw_data': raw_data
            }
        })

    @app.route('/api/nfc/ndef/read', methods=['GET'])
    @require_auth
    def read_ndef_data():
        """Read and parse NDEF formatted data from a detected tag."""
        # Poll for tag
        tag_uid, ndef_data = nfc_controller.read_ndef_data()
        
        if not tag_uid:
            return jsonify({
                'success': False,
                'data': {
                    'message': "No tag detected"
                }
            })
        
        return jsonify({
            'success': True,
            'data': {
                'tag_uid': tag_uid,
                'ndef_data': ndef_data
            }
        })

    @app.route('/api/nfc/ndef/write', methods=['POST'])
    @require_auth
    def write_ndef_data():
        """Write NDEF formatted data to a detected tag.
        
        Request body should include either url or text or both:
        {
            "url": "https://example.com",
            "text": "Example text"
        }
        """
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # At least one of url or text is required
        if 'url' not in data and 'text' not in data:
            raise InvalidRequestError("Either url or text is required")
        
        # Get data to write
        url = data.get('url')
        text = data.get('text')
        
        try:
            # First detect a tag
            tag_uid, _ = nfc_controller.poll_for_tag()
            
            if not tag_uid:
                return jsonify({
                    'success': False,
                    'data': {
                        'message': "No tag detected"
                    }
                })
            
            # Write NDEF data
            if url:
                success = nfc_controller.write_ndef_url(tag_uid, url)
                if not success:
                    raise TagWriteError(f"Failed to write URL to tag {tag_uid}")
            
            if text:
                success = nfc_controller.write_ndef_text(tag_uid, text)
                if not success:
                    raise TagWriteError(f"Failed to write text to tag {tag_uid}")
            
            return jsonify({
                'success': True,
                'data': {
                    'message': "NDEF data written successfully",
                    'tag_uid': tag_uid,
                    'url': url,
                    'text': text
                }
            })
        except Exception as e:
            logger.error(f"Error writing NDEF data: {e}")
            raise TagWriteError(str(e))
    
    logger.info("NFC writer routes registered")


def _write_mode_thread(stop_event, timeout):
    """
    Thread function for handling write mode.
    
    Args:
        stop_event: Threading event for stopping the thread
        timeout: Timeout in seconds
    """
    global write_mode
    
    logger.info(f"Write mode thread started (timeout: {timeout}s)")
    
    try:
        start_time = time.time()
        
        while not stop_event.is_set():
            # Check for timeout
            if time.time() - start_time > timeout:
                logger.info("Write mode timed out")
                break
            
            # If specific data and tag UID provided, look for that tag
            if write_mode['data_to_write'] and write_mode['tag_uid']:
                uid, _ = nfc_controller.poll_for_tag()
                
                if uid and uid == write_mode['tag_uid']:
                    try:
                        nfc_controller.write_tag(uid, write_mode['data_to_write'])
                        logger.info(f"Data written to tag {uid}")
                        # Stop after successful write
                        break
                    except Exception as e:
                        logger.error(f"Error writing to tag: {e}")
            
            # Small delay to prevent CPU overuse
            time.sleep(0.1)
    
    except Exception as e:
        logger.error(f"Error in write mode thread: {e}")
    
    finally:
        # Ensure write mode is deactivated
        write_mode['active'] = False
        logger.info("Write mode thread ended")
