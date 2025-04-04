"""
NFC-Based Toddler-Friendly Music Player - Media Manager

Main media module controller that handles media preparation, caching, and metadata.
Provides interfaces for other system components to access media functionality.
"""

import os
import json
import logging
import uuid
import time
import shutil
import threading
import subprocess
from pathlib import Path
import yt_dlp

from .exceptions import (
    MediaError, MediaPreparationError, DownloadError, InvalidURLError,
    UnsupportedFormatError, CacheError, YouTubeError, YouTubeInfoError, 
    YouTubeDownloadError
)

# Use relative imports correctly within the package
from ..database import db_manager
# Import config using a direct filesystem approach
import os
import sys
import importlib.util

# Get the backend directory path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config_path = os.path.join(backend_dir, 'config.py')

# Add the backend directory to the path if it's not already there
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import the CONFIG from config.py
try:
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    CONFIG = config_module.CONFIG
except Exception as e:
    print(f"Error importing CONFIG: {e}")
    # Provide a default config as fallback
    CONFIG = {
        'media': {
            'cache_dir': os.path.expanduser("~/.nfc_player/media_cache"),
            'max_cache_size_mb': 1000
        }
    }

# Set up logger
logger = logging.getLogger(__name__)

# Global variables
_initialized = False
_cache_dir = None
_download_queue = []
_queue_lock = threading.Lock()
_download_thread = None
_stop_downloads = False

# Constants
DEFAULT_CACHE_DIR = os.path.expanduser("~/.nfc_player/media_cache")
MAX_CACHE_SIZE_MB = 1000  # 1GB default
ALLOWED_FORMATS = ["mp3", "mp4", "m4a", "wav", "ogg"]

# Initialize yt-dlp options
YT_DLP_OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True, 
    'geo_bypass': True,
    'nocheckcertificate': True
}

def initialize():
    """
    Initialize the media manager.

    Returns:
        bool: True if initialization successful
    """
    global _initialized, _cache_dir
    
    try:
        logger.info("Initializing media manager")
        
        # Get configuration
        _cache_dir = CONFIG.get('media', {}).get('cache_dir', DEFAULT_CACHE_DIR)
        
        # Create cache directory if it doesn't exist
        os.makedirs(_cache_dir, exist_ok=True)
        
        # Start background download thread
        _start_download_thread()
        
        _initialized = True
        logger.info("Media manager initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize media manager: {str(e)}")
        return False

def shutdown():
    """
    Perform cleanup operations before shutdown.
    """
    global _initialized, _stop_downloads, _download_thread
    
    logger.info("Shutting down media manager")
    
    # Stop download thread
    if _download_thread and _download_thread.is_alive():
        _stop_downloads = True
        _download_thread.join(timeout=3)
    
    _initialized = False
    logger.info("Media manager shut down")

def is_initialized():
    """
    Check if the media manager is initialized.
    
    Returns:
        bool: True if initialized
    """
    return _initialized

def prepare_media(media_info):
    """
    Prepare media for playback based on media_info from database.

    Will download from YouTube if not cached or use cached version if available.

    Args:
        media_info (dict): Media information containing source, URL, etc.

    Returns:
        str: Path to media file ready for playback

    Raises:
        MediaPreparationError: If media cannot be prepared
    """
    _check_initialized()
    
    if not media_info:
        raise MediaPreparationError("No media information provided")
    
    media_id = media_info.get('id')
    if not media_id:
        raise MediaPreparationError("Media ID is required")
    
    try:
        # Check if we have full media info
        if isinstance(media_info, dict) and len(media_info) <= 2:  # Only has id and maybe one other field
            # Get full media info from database
            media_info = db_manager.get_media_info(media_id)
            if not media_info:
                raise MediaPreparationError(f"Media with ID {media_id} not found in database")
        
        # Check if we have a local path already
        local_path = media_info.get('local_path')
        if local_path and os.path.exists(local_path):
            logger.debug(f"Using existing local file for media {media_id}: {local_path}")
            
            # Update last_played in database
            try:
                current_time = int(time.time())
                db_manager.save_media_info(media_id, {'last_played': current_time})
            except Exception as e:
                logger.warning(f"Failed to update last_played time: {str(e)}")
            
            return local_path
        
        # Check if media is in cache
        cache_path = _get_cached_path(media_id)
        if cache_path:
            logger.debug(f"Using cached file for media {media_id}: {cache_path}")
            
            # Update last_played in database
            try:
                current_time = int(time.time())
                db_manager.save_media_info(media_id, {'last_played': current_time})
            except Exception as e:
                logger.warning(f"Failed to update last_played time: {str(e)}")
            
            return cache_path
        
        # If not cached, we need to download/process
        source_url = media_info.get('source_url') or media_info.get('url')
        if not source_url:
            raise MediaPreparationError(f"No source URL for media {media_id}")
        
        logger.info(f"Media not in cache, downloading: {media_id} from {source_url}")
        
        # Handle different media types
        if 'youtube.com' in source_url or 'youtu.be' in source_url:
            # Download from YouTube
            path = _download_from_youtube(media_id, source_url)
            
            # Update database with path and any new metadata
            info = {'local_path': path}
            db_manager.save_media_info(media_id, info)
            
            return path
        else:
            # For other URL types, assume it's a direct link to a file
            raise MediaPreparationError(f"Unsupported URL type: {source_url}")
        
    except Exception as e:
        logger.error(f"Error preparing media {media_id}: {str(e)}")
        raise MediaPreparationError(f"Failed to prepare media: {str(e)}")

def get_media_info(url):
    """
    Get detailed information about a media item from its URL.

    Args:
        url (str): Media URL (YouTube or direct file URL)

    Returns:
        dict: Media details including title, duration, etc.
    """
    _check_initialized()
    
    try:
        # Handle YouTube URLs
        if 'youtube.com' in url or 'youtu.be' in url:
            return _get_youtube_info(url)
        
        # Handle direct file URLs
        # TODO: Implement direct file URL handling if needed
        
        raise InvalidURLError(f"Unsupported URL type: {url}")
        
    except Exception as e:
        logger.error(f"Error getting media info for URL {url}: {str(e)}")
        raise
        
def get_media_cache_status(media_id):
    """
    Get cache status for a specific media item.

    Args:
        media_id (str): Media identifier

    Returns:
        dict: Cache status including cached path, size, etc.
    """
    _check_initialized()
    
    try:
        cached_path = _get_cached_path(media_id)
        
        if not cached_path:
            return {
                'cached': False,
                'path': None,
                'size_bytes': 0,
                'timestamp': 0
            }
        
        file_stats = os.stat(cached_path)
        
        return {
            'cached': True,
            'path': cached_path,
            'size_bytes': file_stats.st_size,
            'size_mb': round(file_stats.st_size / (1024 * 1024), 2),
            'timestamp': file_stats.st_mtime,
            'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stats.st_mtime))
        }
    except Exception as e:
        logger.error(f"Error getting cache status for media {media_id}: {str(e)}")
        return {'cached': False, 'error': str(e)}

def queue_for_caching(media_id):
    """
    Queue a media item for background caching.

    Args:
        media_id (str): Media identifier

    Returns:
        bool: True if queued successfully
    """
    _check_initialized()
    
    try:
        media_info = db_manager.get_media_info(media_id)
        if not media_info:
            raise MediaError(f"Media with ID {media_id} not found in database")
        
        # Check if already in cache
        if _get_cached_path(media_id):
            logger.debug(f"Media {media_id} already cached, not queuing")
            return True
        
        global _download_queue
        with _queue_lock:
            # Check if already in queue
            if media_id in [item['id'] for item in _download_queue]:
                logger.debug(f"Media {media_id} already in download queue")
                return True
            
            _download_queue.append({
                'id': media_id,
                'url': media_info.get('source_url') or media_info.get('url'),
                'timestamp': time.time()
            })
            logger.debug(f"Media {media_id} added to download queue")
        
        return True
    except Exception as e:
        logger.error(f"Error queueing media {media_id} for caching: {str(e)}")
        raise

def delete_from_cache(media_id):
    """
    Delete a media item from the cache.

    Args:
        media_id (str): Media identifier

    Returns:
        bool: True if deleted successfully
    """
    _check_initialized()
    
    try:
        cached_path = _get_cached_path(media_id)
        if not cached_path:
            logger.debug(f"Media {media_id} not in cache, nothing to delete")
            return True
        
        # Delete the file
        os.remove(cached_path)
        logger.debug(f"Deleted cached media {media_id}: {cached_path}")
        
        return True
    except Exception as e:
        logger.error(f"Error deleting media {media_id} from cache: {str(e)}")
        raise CacheError(f"Failed to delete from cache: {str(e)}")

def get_cache_status():
    """
    Get overall status of the media cache.

    Returns:
        dict: Cache status including size, item count, etc.
    """
    _check_initialized()
    
    try:
        # Get cache directory info
        if not os.path.exists(_cache_dir):
            return {
                'total_files': 0,
                'total_size_bytes': 0,
                'total_size_mb': 0,
                'max_size_mb': CONFIG.get('media', {}).get('max_cache_size_mb', MAX_CACHE_SIZE_MB),
                'cache_dir': _cache_dir,
                'cache_exists': False
            }
        
        # Count files and total size
        total_size = 0
        file_count = 0
        oldest_file = None
        newest_file = None
        oldest_time = float('inf')
        newest_time = 0
        
        for root, dirs, files in os.walk(_cache_dir):
            for file in files:
                if file.endswith(tuple(ALLOWED_FORMATS)):
                    path = os.path.join(root, file)
                    stats = os.stat(path)
                    total_size += stats.st_size
                    file_count += 1
                    
                    # Track oldest and newest
                    if stats.st_mtime < oldest_time:
                        oldest_time = stats.st_mtime
                        oldest_file = file
                    if stats.st_mtime > newest_time:
                        newest_time = stats.st_mtime
                        newest_file = file
        
        return {
            'total_files': file_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'max_size_mb': CONFIG.get('media', {}).get('max_cache_size_mb', MAX_CACHE_SIZE_MB),
            'cache_dir': _cache_dir,
            'cache_exists': True,
            'oldest_file': oldest_file,
            'oldest_timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(oldest_time)) if oldest_file else None,
            'newest_file': newest_file,
            'newest_timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(newest_time)) if newest_file else None
        }
    except Exception as e:
        logger.error(f"Error getting cache status: {str(e)}")
        return {
            'error': str(e),
            'cache_dir': _cache_dir,
            'cache_exists': os.path.exists(_cache_dir)
        }

def get_cache_size():
    """
    Get the current cache size in bytes.

    Returns:
        int: Cache size in bytes
    """
    _check_initialized()
    
    try:
        # Get cache directory size
        total_size = 0
        
        if not os.path.exists(_cache_dir):
            return 0
        
        for root, dirs, files in os.walk(_cache_dir):
            for file in files:
                total_size += os.path.getsize(os.path.join(root, file))
        
        return total_size
    except Exception as e:
        logger.error(f"Error getting cache size: {str(e)}")
        return 0

def clean_cache(older_than=None, force=False):
    """
    Clean media cache, removing old or unused files.

    Args:
        older_than (int, optional): Remove items older than this many days
        force (bool, optional): Force clean even if within size limits

    Returns:
        dict: Results including bytes cleaned, files deleted
    """
    _check_initialized()
    
    try:
        if not os.path.exists(_cache_dir):
            return {
                'cleaned_bytes': 0,
                'deleted_files': 0,
                'message': "Cache directory does not exist"
            }
        
        # Get cache status
        cache_status = get_cache_status()
        max_size_bytes = cache_status['max_size_mb'] * 1024 * 1024
        current_size_bytes = cache_status['total_size_bytes']
        
        # If not forcing and under size limit, check if cleaning needed
        if not force and current_size_bytes < max_size_bytes and not older_than:
            logger.debug(f"Cache size {current_size_bytes} is under limit {max_size_bytes}, not cleaning")
            return {
                'cleaned_bytes': 0,
                'deleted_files': 0,
                'message': "Cache is under size limit, no cleaning needed"
            }
        
        # Collect files to clean
        files_to_clean = []
        current_time = time.time()
        
        for root, dirs, files in os.walk(_cache_dir):
            for file in files:
                path = os.path.join(root, file)
                stats = os.stat(path)
                
                # Check age if older_than specified
                if older_than:
                    file_age_days = (current_time - stats.st_mtime) / (86400)  # seconds in a day
                    if file_age_days >= older_than:
                        files_to_clean.append((path, stats.st_size, stats.st_mtime))
                else:
                    files_to_clean.append((path, stats.st_size, stats.st_mtime))
        
        # Sort by last modified (oldest first)
        files_to_clean.sort(key=lambda x: x[2])
        
        # Delete files until we're under the limit or all files processed
        bytes_cleaned = 0
        files_deleted = 0
        
        for path, size, mtime in files_to_clean:
            # If not forcing and we're below target size, stop cleaning
            if not force and not older_than and (current_size_bytes - bytes_cleaned) < max_size_bytes * 0.8:
                break
                
            try:
                os.remove(path)
                bytes_cleaned += size
                files_deleted += 1
                logger.debug(f"Cleaned cache file: {path}")
            except Exception as e:
                logger.warning(f"Failed to delete cache file {path}: {str(e)}")
        
        message = f"Cleaned {files_deleted} files ({bytes_cleaned / (1024*1024):.2f} MB)"
        if older_than:
            message += f" older than {older_than} days"
            
        logger.info(message)
        
        return {
            'cleaned_bytes': bytes_cleaned,
            'deleted_files': files_deleted,
            'message': message
        }
    except Exception as e:
        logger.error(f"Error cleaning cache: {str(e)}")
        raise CacheError(f"Failed to clean cache: {str(e)}")

def save_uploaded_media(media_id, file_object):
    """
    Save an uploaded media file to the local storage.

    Args:
        media_id (str): Media identifier to associate with the file
        file_object (FileStorage): File object from a form upload

    Returns:
        str: Path to the saved file
    """
    _check_initialized()
    
    try:
        # Create directory for user uploads if it doesn't exist
        uploads_dir = os.path.join(_cache_dir, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Get file extension
        filename = file_object.filename
        extension = os.path.splitext(filename)[1].lower()
        if not extension:
            extension = '.mp3'  # Default extension if none provided
        
        # Create a unique filename
        new_filename = f"{media_id}{extension}"
        file_path = os.path.join(uploads_dir, new_filename)
        
        # Save the file
        file_object.save(file_path)
        logger.info(f"Saved uploaded file: {file_path}")
        
        return file_path
    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}")
        raise MediaError(f"Failed to save uploaded file: {str(e)}")

# Private methods

def _check_initialized():
    """Check if the media manager is initialized."""
    if not _initialized:
        logger.error("Media manager not initialized")
        raise MediaError("Media manager not initialized. Call initialize() first.")

def _get_cached_path(media_id):
    """
    Get path to cached media file if it exists.

    Args:
        media_id (str): Media identifier

    Returns:
        str or None: Path to cached file or None if not cached
    """
    if not media_id:
        return None
    
    # Check for file with various extensions
    for ext in ALLOWED_FORMATS:
        path = os.path.join(_cache_dir, f"{media_id}.{ext}")
        if os.path.exists(path):
            return path
    
    # Check in uploads directory
    uploads_dir = os.path.join(_cache_dir, 'uploads')
    if os.path.exists(uploads_dir):
        for ext in ALLOWED_FORMATS:
            path = os.path.join(uploads_dir, f"{media_id}.{ext}")
            if os.path.exists(path):
                return path
    
    return None

def _download_from_youtube(media_id, url):
    """
    Download audio from YouTube.

    Args:
        media_id (str): Media identifier
        url (str): YouTube URL

    Returns:
        str: Path to downloaded file

    Raises:
        YouTubeDownloadError: If download fails
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(_cache_dir, exist_ok=True)
        
        # Set output filename
        output_path = os.path.join(_cache_dir, f"{media_id}.%(ext)s")
        
        # Configure yt-dlp options
        options = YT_DLP_OPTIONS.copy()
        options['outtmpl'] = output_path
        
        # Download the video
        logger.info(f"Downloading YouTube video: {url}")
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get the output file
            if 'ext' in info:
                downloaded_file = os.path.join(_cache_dir, f"{media_id}.{info['ext']}")
            else:
                # If extraction failed to provide the extension, look for mp3
                downloaded_file = os.path.join(_cache_dir, f"{media_id}.mp3")
            
            # Verify file exists
            if not os.path.exists(downloaded_file):
                # Try finding the file with different extensions
                for ext in ALLOWED_FORMATS:
                    test_file = os.path.join(_cache_dir, f"{media_id}.{ext}")
                    if os.path.exists(test_file):
                        downloaded_file = test_file
                        break
                
                if not os.path.exists(downloaded_file):
                    raise YouTubeDownloadError(f"Download completed but file not found: {media_id}")
            
            logger.info(f"Downloaded YouTube video to: {downloaded_file}")
            return downloaded_file
            
    except Exception as e:
        logger.error(f"Error downloading YouTube video {url}: {str(e)}")
        raise YouTubeDownloadError(f"Failed to download YouTube video: {str(e)}")

def _get_youtube_info(url):
    """
    Get information about a YouTube video without downloading.

    Args:
        url (str): YouTube URL

    Returns:
        dict: Video information (title, duration, thumbnail, etc.)

    Raises:
        YouTubeInfoError: If info cannot be retrieved
    """
    try:
        # Configure yt-dlp options for info only
        options = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'skip_download': True
        }
        
        # Get video info
        logger.debug(f"Fetching YouTube info: {url}")
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract relevant fields
            result = {
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', ''),
                'view_count': info.get('view_count', 0),
                'url': url
            }
            
            return result
            
    except Exception as e:
        logger.error(f"Error getting YouTube info for {url}: {str(e)}")
        raise YouTubeInfoError(f"Failed to get YouTube info: {str(e)}")

def _start_download_thread():
    """Start the background download thread for queued items."""
    global _download_thread, _stop_downloads
    
    _stop_downloads = False
    
    if _download_thread and _download_thread.is_alive():
        logger.debug("Download thread already running")
        return
    
    _download_thread = threading.Thread(target=_download_worker, daemon=True)
    _download_thread.start()
    logger.debug("Started background download thread")

def _download_worker():
    """Worker function for processing the download queue."""
    global _download_queue, _stop_downloads
    
    logger.debug("Download worker thread started")
    
    while not _stop_downloads:
        try:
            # Get item from queue
            media_to_download = None
            with _queue_lock:
                if _download_queue:
                    media_to_download = _download_queue.pop(0)
            
            if not media_to_download:
                # Queue is empty, sleep and check again
                time.sleep(1)
                continue
            
            media_id = media_to_download.get('id')
            url = media_to_download.get('url')
            
            if not media_id or not url:
                logger.warning(f"Invalid download queue item: {media_to_download}")
                continue
            
            logger.info(f"Processing queued download: {media_id} from {url}")
            
            # Check if already cached
            if _get_cached_path(media_id):
                logger.debug(f"Media {media_id} already cached, skipping download")
                continue
            
            # Check cache size before download
            cache_status = get_cache_status()
            if cache_status['total_size_mb'] > cache_status['max_size_mb']:
                logger.info("Cache full, cleaning before download")
                clean_cache()
            
            # Download the file
            if 'youtube.com' in url or 'youtu.be' in url:
                try:
                    # Download from YouTube
                    path = _download_from_youtube(media_id, url)
                    
                    # Update database with path and metadata
                    media_info = _get_youtube_info(url)
                    media_info['local_path'] = path
                    db_manager.save_media_info(media_id, media_info)
                    
                    logger.info(f"Successfully downloaded and cached: {media_id}")
                except Exception as e:
                    logger.error(f"Failed to download media {media_id}: {str(e)}")
            else:
                logger.warning(f"Unsupported URL type for download: {url}")
        
        except Exception as e:
            logger.error(f"Error in download worker: {str(e)}")
            time.sleep(5)  # Delay on error
    
    logger.debug("Download worker thread stopping")