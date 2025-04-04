"""
NFC-Based Toddler-Friendly Music Player - Media Routes

This module implements the API routes for managing media.
"""

import os
import uuid
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename

from ...database import db_manager
from ...media import media_manager
from ...audio import audio_controller
from ..exceptions import ResourceNotFoundError, InvalidRequestError
from ..middleware.auth import require_auth
from backend.utils.logger import get_logger
from backend.config import CONFIG

logger = get_logger(__name__)


def register_routes(app):
    """
    Register media-related routes with the Flask application.

    Args:
        app: Flask application instance
    """
    
    @app.route('/api/media', methods=['GET'])
    @require_auth
    def get_all_media():
        """Get all media entries."""
        # Get query parameters for pagination
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get media from database
        media_items = db_manager.get_all_media(limit, offset)
        total = db_manager.get_media_count()
        
        return jsonify({
            'success': True,
            'data': {
                'media': media_items,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
            }
        })

    @app.route('/api/media/<media_id>', methods=['GET'])
    @require_auth
    def get_media(media_id):
        """Get a specific media entry."""
        media = db_manager.get_media(media_id)
        
        if not media:
            raise ResourceNotFoundError(f"Media with ID {media_id} not found")
        
        # Get associated tags for this media
        associated_tags = db_manager.get_tags_for_media(media_id)
        
        # Get cache status
        cache_status = media_manager.get_media_cache_status(media_id)
        
        # Combine all information
        media_info = {
            **media,
            'tags': associated_tags,
            'cache_status': cache_status
        }
        
        return jsonify({
            'success': True,
            'data': {
                'media': media_info
            }
        })

    @app.route('/api/media/youtube', methods=['POST'])
    @require_auth
    def add_youtube_media():
        """Add a new YouTube media source."""
        data = request.get_json()
        
        if not data:
            raise InvalidRequestError("Missing request body")
        
        # Required fields
        if 'url' not in data:
            raise InvalidRequestError("YouTube URL is required")
        
        url = data['url']
        # Validate if it's a YouTube or YouTube Music URL
        if not ('youtube.com' in url or 'youtu.be' in url or 'music.youtube.com' in url):
            raise InvalidRequestError("URL must be a valid YouTube or YouTube Music URL")
        
        # Optional fields with defaults
        title = data.get('title', '')
        description = data.get('description', '')
        
        # Process the URL to extract info if title not provided
        if not title:
            try:
                # Extract media info from YouTube
                info = media_manager.get_media_info(url)
                title = info.get('title', f"YouTube {uuid.uuid4().hex[:8]}")
                if not description and 'description' in info:
                    description = info.get('description', '')
            except Exception as e:
                logger.error(f"Error fetching YouTube info: {e}")
                title = f"YouTube {uuid.uuid4().hex[:8]}"
        
        # Add to database
        media = db_manager.add_media(
            title=title,
            description=description,
            source_url=url,
            media_type='youtube'
        )
        
        # Start caching in background if requested
        if data.get('cache', False):
            try:
                media_manager.queue_for_caching(media['id'])
            except Exception as e:
                logger.error(f"Error queuing for caching: {e}")
        
        return jsonify({
            'success': True,
            'data': {
                'media': media
            }
        }), 201

    @app.route('/api/media/upload', methods=['POST'])
    @require_auth
    def upload_media():
        """Upload a local media file."""
        # Check if file is in request
        if 'file' not in request.files:
            raise InvalidRequestError("No file part in the request")
        
        file = request.files['file']
        
        # Check if file was selected
        if file.filename == '':
            raise InvalidRequestError("No file selected")
        
        # Get form data
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        
        # If no title provided, use filename
        if not title:
            title = os.path.splitext(file.filename)[0]
        
        # Validate file type
        filename = secure_filename(file.filename)
        file_extension = os.path.splitext(filename)[1].lower()[1:]  # Remove the dot
        
        allowed_formats = CONFIG['media']['allowed_formats']
        if file_extension not in allowed_formats:
            raise InvalidRequestError(
                f"File format not allowed. Allowed formats: {', '.join(allowed_formats)}"
            )
        
        # Create media entry in database
        media = db_manager.add_media(
            title=title,
            description=description,
            source_url=None,
            media_type='local',
            file_name=filename
        )
        
        # Save the file
        try:
            media_path = media_manager.save_uploaded_media(media['id'], file)
            # Update media with path
            db_manager.update_media(media['id'], {'local_path': media_path})
        except Exception as e:
            # Clean up on failure
            db_manager.delete_media(media['id'])
            logger.error(f"Error saving uploaded file: {e}")
            raise
        
        return jsonify({
            'success': True,
            'data': {
                'media': media
            }
        }), 201

    @app.route('/api/media/<media_id>', methods=['DELETE'])
    @require_auth
    def delete_media(media_id):
        """Delete a media entry."""
        # Verify media exists
        media = db_manager.get_media(media_id)
        if not media:
            raise ResourceNotFoundError(f"Media with ID {media_id} not found")
        
        # Delete from cache if cached
        try:
            media_manager.delete_from_cache(media_id)
        except Exception as e:
            logger.error(f"Error deleting from cache: {e}")
        
        # Delete from database
        success = db_manager.delete_media(media_id)
        
        return jsonify({
            'success': success,
            'data': {
                'message': f"Media {media_id} deleted successfully"
            }
        })

    @app.route('/api/media/<media_id>/test', methods=['POST'])
    @require_auth
    def test_playback(media_id):
        """Test playback of a media entry."""
        # Verify media exists
        media = db_manager.get_media(media_id)
        if not media:
            raise ResourceNotFoundError(f"Media with ID {media_id} not found")
        
        # Get current playback state to restore later
        was_playing = audio_controller.is_playing()
        
        # Stop any current playback
        if was_playing:
            audio_controller.stop()
        
        # Prepare media for playback
        try:
            # This will download/cache if needed
            media_path = media_manager.prepare_media({'id': media_id})
            
            # Play the media
            audio_controller.play(media_path)
            
            return jsonify({
                'success': True,
                'data': {
                    'message': f"Playing {media['title']}",
                    'path': media_path
                }
            })
        except Exception as e:
            # If there was an error, try to restore previous playback
            logger.error(f"Error testing playback: {e}")
            raise

    @app.route('/api/media/playback/stop', methods=['POST'])
    @require_auth
    def stop_playback():
        """Stop current playback."""
        audio_controller.stop()
        return jsonify({
            'success': True,
            'data': {
                'message': "Playback stopped"
            }
        })

    @app.route('/api/media/<media_id>/download', methods=['GET'])
    @require_auth
    def download_media(media_id):
        """Download the media file."""
        # Verify media exists
        media = db_manager.get_media(media_id)
        if not media:
            raise ResourceNotFoundError(f"Media with ID {media_id} not found")
        
        # Prepare media (cache if needed)
        try:
            media_path = media_manager.prepare_media({'id': media_id})
            
            # Check if file exists
            if not os.path.exists(media_path):
                raise ResourceNotFoundError("Media file not found")
            
            # Send file for download
            return send_file(
                media_path,
                as_attachment=True,
                attachment_filename=media.get('file_name', f"{media['title']}.mp3")
            )
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            raise

    @app.route('/api/media/cache/status', methods=['GET'])
    @require_auth
    def get_cache_status():
        """Get media cache status."""
        status = media_manager.get_cache_status()
        return jsonify({
            'success': True,
            'data': {
                'cache_status': status
            }
        })

    @app.route('/api/media/cache/clean', methods=['POST'])
    @require_auth
    def clean_cache():
        """Clean the media cache."""
        data = request.get_json() or {}
        force = data.get('force', False)
        
        result = media_manager.clean_cache(force=force)
        
        return jsonify({
            'success': True,
            'data': {
                'cleaned_bytes': result.get('cleaned_bytes', 0),
                'deleted_files': result.get('deleted_files', 0),
                'message': result.get('message', "Cache cleaned successfully")
            }
        })
    
    logger.info("Media routes registered")
