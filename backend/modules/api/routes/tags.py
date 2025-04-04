"""
NFC-Based Toddler-Friendly Music Player - Tag Routes

This module implements the API routes for managing NFC tags.
"""

from flask import request, jsonify
import time

from ...database import db_manager
from ...nfc import nfc_controller
from ..exceptions import ResourceNotFoundError, InvalidRequestError
from ..middleware.auth import require_auth
from . import get_logger

logger = get_logger(__name__)

# Keep track of last detected tag for UI feedback
last_detected_tag = {
    'uid': None,
    'ndef_info': None,
    'timestamp': None
}


def register_routes(app):
    """
    Register tag-related routes with the Flask application.

    Args:
        app: Flask application instance
    """
    
    @app.route('/api/tags', methods=['GET'])
    @require_auth
    def get_all_tags():
        """Get all registered NFC tags."""
        # Check for filter parameter
        filter_type = request.args.get('filter')
        
        if filter_type == 'missing_url':
            # Find tags with no associated URL
            tags = db_manager.get_tags_without_media()
        else:
            # Get all tags
            tags = db_manager.get_all_tags()
            
        return jsonify({
            'success': True,
            'data': {
                'tags': tags
            }
        })

    @app.route('/api/tags/<tag_uid>', methods=['GET'])
    @require_auth
    def get_tag(tag_uid):
        """Get a specific tag by UID."""
        tag = db_manager.get_tag(tag_uid)
        
        if not tag:
            raise ResourceNotFoundError(f"Tag with UID {tag_uid} not found")
        
        return jsonify({
            'success': True,
            'data': {
                'tag': tag
            }
        })

    @app.route('/api/tags', methods=['POST'])
    @require_auth
    def create_tag():
        """Register a new tag."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'uid' not in data:
            raise InvalidRequestError("Tag UID is required")
        
        # Optional fields with defaults
        name = data.get('name', f"Tag {data['uid']}")
        description = data.get('description', '')
        media_id = data.get('media_id')
        
        # Create the tag in the database
        tag = db_manager.create_tag(
            uid=data['uid'],
            name=name,
            description=description,
            media_id=media_id
        )
        
        return jsonify({
            'success': True,
            'data': {
                'tag': tag
            }
        }), 201

    @app.route('/api/tags/<tag_uid>', methods=['PUT'])
    @require_auth
    def update_tag(tag_uid):
        """Update a tag's information."""
        # Verify tag exists
        tag = db_manager.get_tag(tag_uid)
        if not tag:
            raise ResourceNotFoundError(f"Tag with UID {tag_uid} not found")
        
        # Get request data
        data = request.get_json()
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Update fields
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'description' in data:
            updates['description'] = data['description']
        if 'media_id' in data:
            updates['media_id'] = data['media_id']
        
        # Update in database
        updated_tag = db_manager.update_tag(tag_uid, updates)
        
        return jsonify({
            'success': True,
            'data': {
                'tag': updated_tag
            }
        })

    @app.route('/api/tags/<tag_uid>', methods=['DELETE'])
    @require_auth
    def delete_tag(tag_uid):
        """Delete a tag registration."""
        # Verify tag exists
        tag = db_manager.get_tag(tag_uid)
        if not tag:
            raise ResourceNotFoundError(f"Tag with UID {tag_uid} not found")
        
        # Delete from database
        success = db_manager.delete_tag(tag_uid)
        
        return jsonify({
            'success': success,
            'data': {
                'message': f"Tag {tag_uid} deleted successfully"
            }
        })

    @app.route('/api/tags/<tag_uid>/associate', methods=['POST'])
    @require_auth
    def associate_tag(tag_uid):
        """Associate a tag with media."""
        # Verify tag exists
        tag = db_manager.get_tag(tag_uid)
        if not tag:
            raise ResourceNotFoundError(f"Tag with UID {tag_uid} not found")
        
        # Get request data
        data = request.get_json()
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Allow associating by media_id or directly by URL
        if 'media_id' in data:
            # Verify media exists
            media = db_manager.get_media(data['media_id'])
            if not media:
                raise ResourceNotFoundError(f"Media with ID {data['media_id']} not found")
            
            # Associate tag with media
            updated_tag = db_manager.update_tag(tag_uid, {'media_id': data['media_id']})
            
            return jsonify({
                'success': True,
                'data': {
                    'tag': updated_tag,
                    'media': media
                }
            })
        elif 'url' in data:
            # Create/get media by URL and associate with tag
            try:
                media = db_manager.add_or_get_media_by_url(data['url'], tag_uid)
                if not media:
                    raise InvalidRequestError(f"Failed to create or find media for URL: {data['url']}")
                
                # Re-fetch tag with updated association
                updated_tag = db_manager.get_tag(tag_uid)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'tag': updated_tag,
                        'media': media
                    }
                })
            except Exception as e:
                logger.error(f"Error associating tag with URL: {e}")
                raise InvalidRequestError(f"Failed to associate tag with URL: {str(e)}")
        else:
            raise InvalidRequestError("Either media_id or url is required")

    @app.route('/api/tags/last-detected', methods=['GET'])
    @require_auth
    def get_last_detected_tag():
        """Get information about the most recently detected tag."""
        global last_detected_tag
        
        # If there is a last detected tag, get more info from DB
        tag_data = None
        if last_detected_tag['uid']:
            tag_data = db_manager.get_tag(last_detected_tag['uid'])
        
        return jsonify({
            'success': True,
            'data': {
                'last_detected': last_detected_tag,
                'tag_data': tag_data
            }
        })

    @app.route('/api/tags/history', methods=['GET'])
    @require_auth
    def get_tag_history():
        """Get tag usage history."""
        # Get query parameters
        limit = request.args.get('limit', 10, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get history from database
        history = db_manager.get_tag_history(limit, offset)
        total = db_manager.get_tag_history_count()
        
        return jsonify({
            'success': True,
            'data': {
                'history': history,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
            }
        })
    
    # Hook into NFC controller to track last detected tag
    def on_tag_detected_callback(uid, ndef_info):
        """Callback for when a tag is detected by the NFC controller."""
        global last_detected_tag
        last_detected_tag = {
            'uid': uid,
            'ndef_info': ndef_info,
            'timestamp': time.time()
        }
    
    # Register callback with NFC controller if available
    if hasattr(nfc_controller, 'register_tag_callback'):
        nfc_controller.register_tag_callback(on_tag_detected_callback)
    
    logger.info("Tag routes registered")
