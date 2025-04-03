"""
Media Module for the NFC music player.

This module is responsible for managing media content, including:
- Fetching audio from YouTube
- Managing local media cache
- Handling media metadata
- Supporting offline operation
"""

from .media_manager import MediaManager
from .exceptions import (
    MediaError,
    MediaPreparationError,
    DownloadError,
    InvalidURLError,
    UnsupportedFormatError,
    CacheError,
    YouTubeError,
    YouTubeInfoError,
    YouTubeDownloadError
)

# Create a singleton instance of MediaManager
_media_manager = None


def get_manager():
    """
    Get the singleton media manager instance.
    
    Returns:
        MediaManager: The media manager instance
    """
    global _media_manager
    if _media_manager is None:
        _media_manager = MediaManager()
    return _media_manager


def initialize():
    """
    Initialize the media manager.

    Returns:
        bool: True if initialization successful
    """
    return get_manager().initialize()


def shutdown():
    """
    Perform cleanup operations before shutdown.
    """
    if _media_manager is not None:
        _media_manager.shutdown()


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
    return get_manager().prepare_media(media_info)


def get_media_info(media_id):
    """
    Get detailed information about a media item.

    Args:
        media_id (str): Media identifier

    Returns:
        dict: Media details including path, title, duration, etc.
    """
    return get_manager().get_media_info(media_id)


def add_youtube_media(url, title=None, tags=None):
    """
    Add a YouTube video/audio to the media library.

    Args:
        url (str): YouTube URL
        title (str, optional): Custom title for the media
        tags (list, optional): List of tags to associate with this media

    Returns:
        str: Media ID of the added media

    Raises:
        InvalidURLError: If URL is not a valid YouTube URL
        DownloadError: If media cannot be downloaded
    """
    return get_manager().add_youtube_media(url, title, tags)


def add_local_media(file_path, title=None, tags=None):
    """
    Add a local audio file to the media library.

    Args:
        file_path (str): Path to local audio file
        title (str, optional): Custom title for the media
        tags (list, optional): List of tags to associate with this media

    Returns:
        str: Media ID of the added media

    Raises:
        FileNotFoundError: If file does not exist
        UnsupportedFormatError: If file format is not supported
    """
    return get_manager().add_local_media(file_path, title, tags)


def remove_media(media_id):
    """
    Remove media from the library and cache.

    Args:
        media_id (str): Media identifier

    Returns:
        bool: True if successfully removed
    """
    return get_manager().remove_media(media_id)


def get_cache_status():
    """
    Get status of the media cache.

    Returns:
        dict: Cache status including size, item count, etc.
    """
    return get_manager().get_cache_status()


def clear_cache(older_than=None):
    """
    Clear media cache.

    Args:
        older_than (int, optional): Clear items older than this many days

    Returns:
        int: Number of items cleared
    """
    return get_manager().clear_cache(older_than)


def search_media(query):
    """
    Search for media items in the library.
    
    Args:
        query (str): Search query
        
    Returns:
        list: List of matching media info dictionaries
    """
    return get_manager().search_media(query)


def get_all_media():
    """
    Get all media items in the library.
    
    Returns:
        list: List of media info dictionaries
    """
    return get_manager().get_all_media()


def get_media_by_tag(tag):
    """
    Get media items with a specific tag.
    
    Args:
        tag (str): Tag to search for
        
    Returns:
        list: List of matching media info dictionaries
    """
    return get_manager().get_media_by_tag(tag)


# Additional internal exports for advanced usage
download_with_progress = lambda url, progress_callback: get_manager().download_with_progress(url, progress_callback)

# Version
__version__ = '1.0.0'
