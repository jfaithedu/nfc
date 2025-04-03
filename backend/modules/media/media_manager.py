"""
media_manager.py - Main controller module for media management in the NFC music player.

This module serves as the main interface for other modules to interact with media functionality.
It integrates YouTube handling, cache management, and metadata processing.
"""

import os
import uuid
import time
import json
from typing import Dict, List, Optional, Tuple, Union, Callable

from backend.utils.logger import LoggerMixin
from backend.utils.file_utils import (
    ensure_dir, 
    file_size, 
    is_media_file, 
    get_file_extension,
    copy_file_safe
)
from backend.config import CONFIG

from .youtube_handler import YouTubeDownloader
from .cache_manager import MediaCache
from . import metadata_processor
from .exceptions import (
    MediaError, 
    MediaPreparationError,
    InvalidURLError, 
    DownloadError,
    UnsupportedFormatError
)


class MediaManager(LoggerMixin):
    """
    Main controller for media functionality.
    """
    
    def __init__(self, config=None):
        """
        Initialize the media manager.
        
        Args:
            config (dict, optional): Configuration, defaults to global CONFIG
        """
        self.setup_logger()
        
        # Use global config if not provided
        self.config = config or CONFIG.get('media', {})
        
        # Ensure media directories exist
        self.cache_dir = ensure_dir(self.config.get('cache_dir', 'data/media_cache'))
        self.thumbnails_dir = ensure_dir(os.path.join(self.cache_dir, 'thumbnails'))
        
        # Allowed media formats
        self.allowed_formats = self.config.get('allowed_formats', ['mp3', 'wav', 'ogg', 'm4a'])
        
        # Maximum cache size in MB
        self.max_cache_size_mb = self.config.get('max_cache_size_mb', 1000)
        
        # Initialize components
        self.youtube_downloader = YouTubeDownloader(
            output_dir=self.cache_dir,
            yt_dlp_options=self.config.get('yt_dlp_options', None)
        )
        
        self.cache = MediaCache(
            cache_dir=self.cache_dir,
            max_size_mb=self.max_cache_size_mb
        )
        
        # Media library file to track media items
        self.library_file = os.path.join(self.cache_dir, 'media_library.json')
        self.library = self._load_library()
        
        self.logger.info("Media manager initialized")
    
    def _load_library(self) -> Dict:
        """
        Load the media library from file.
        
        Returns:
            dict: The media library data
        """
        if os.path.exists(self.library_file):
            try:
                with open(self.library_file, 'r') as f:
                    library = json.load(f)
                self.logger.info(f"Loaded media library with {len(library.get('items', {}))} items")
                return library
            except Exception as e:
                self.logger.error(f"Failed to load media library: {e}")
                # Fall back to creating a new library
        
        # Create new library structure
        library = {
            'version': 1,
            'created': time.time(),
            'last_modified': time.time(),
            'items': {}
        }
        
        # Save the new library
        self._save_library(library)
        
        return library
    
    def _save_library(self, library=None) -> bool:
        """
        Save the media library to file.
        
        Args:
            library (dict, optional): Library to save, defaults to self.library
            
        Returns:
            bool: True if successful
        """
        library = library or self.library
        
        try:
            # Update last modified timestamp
            library['last_modified'] = time.time()
            
            with open(self.library_file, 'w') as f:
                json.dump(library, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save media library: {e}")
            return False
    
    def initialize(self) -> bool:
        """
        Initialize the media manager.

        Returns:
            bool: True if initialization successful
        """
        try:
            # Make sure all required directories exist
            ensure_dir(self.cache_dir)
            ensure_dir(self.thumbnails_dir)
            
            # Check library file
            if not os.path.exists(self.library_file):
                self._save_library()
            
            # Optimize cache if needed
            if self.cache.get_cache_size() > self.max_cache_size_mb * 1024 * 1024:
                self.cache.optimize_cache()
            
            # Validate library entries (ensure files exist)
            self._validate_library()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize media manager: {e}")
            return False
    
    def _validate_library(self) -> None:
        """
        Validate all entries in the library, removing invalid ones.
        """
        invalid_ids = []
        
        for media_id, info in self.library.get('items', {}).items():
            # Check if file exists in cache
            cache_path = self.cache.get_cached_path(media_id)
            if not cache_path:
                invalid_ids.append(media_id)
                continue
            
            # Check if file is a valid media file
            if not os.path.exists(cache_path) or not is_media_file(cache_path, self.allowed_formats):
                invalid_ids.append(media_id)
        
        # Remove invalid entries
        for media_id in invalid_ids:
            self.logger.warning(f"Removing invalid library entry: {media_id}")
            self.library['items'].pop(media_id, None)
        
        # Save changes
        if invalid_ids:
            self._save_library()
            self.logger.info(f"Removed {len(invalid_ids)} invalid library entries")
    
    def shutdown(self) -> None:
        """
        Perform cleanup operations before shutdown.
        """
        # Save library
        self._save_library()
        
        # Clean up any temporary files
        self.logger.info("Media manager shutdown complete")
    
    def _generate_media_id(self) -> str:
        """
        Generate a unique media ID.
        
        Returns:
            str: Unique media ID
        """
        # Generate a UUID and remove hyphens
        return uuid.uuid4().hex
    
    def prepare_media(self, media_info: Dict) -> str:
        """
        Prepare media for playback based on media_info from database.

        Will download from YouTube if not cached or use cached version if available.
        Prioritizes URL field if present (for NDEF URL handling).

        Args:
            media_info (dict): Media information containing source, URL, etc.

        Returns:
            str: Path to media file ready for playback

        Raises:
            MediaPreparationError: If media cannot be prepared
        """
        if not media_info or 'id' not in media_info:
            raise MediaPreparationError("Invalid media info provided")
        
        media_id = media_info['id']
        
        # Check if we have this media item in cache
        cached_path = self.cache.get_cached_path(media_id)
        if cached_path and os.path.exists(cached_path):
            self.logger.info(f"Using cached media: {media_id}")
            return cached_path
        
        # If not in cache, we need to fetch/prepare it
        try:
            # First check if media_info has a url field (from NDEF tag)
            if 'url' in media_info and media_info['url']:
                url = media_info['url']
                if ('youtube.com' in url or 'youtu.be' in url or 'music.youtube.com' in url):
                    self.logger.info(f"Preparing media from URL field: {url}")
                    # Create YouTube info with the URL
                    youtube_info = media_info.copy()
                    youtube_info['source_type'] = 'youtube'
                    return self._prepare_youtube_media(youtube_info)
            
            # Fall back to traditional source_type based handling
            source_type = media_info.get('source_type', 'unknown')
            if source_type == 'youtube':
                return self._prepare_youtube_media(media_info)
            elif source_type == 'local':
                return self._prepare_local_media(media_info)
            else:
                raise MediaPreparationError(f"Unsupported media source type: {source_type}")
        except Exception as e:
            self.logger.error(f"Failed to prepare media {media_id}: {e}")
            raise MediaPreparationError(f"Failed to prepare media: {str(e)}")
    
    def _prepare_youtube_media(self, media_info: Dict) -> str:
        """
        Prepare YouTube media for playback.
        
        Args:
            media_info (dict): Media information
            
        Returns:
            str: Path to media file
            
        Raises:
            MediaPreparationError: If media cannot be prepared
        """
        media_id = media_info['id']
        url = media_info.get('url')
        
        if not url:
            raise MediaPreparationError(f"No URL provided for YouTube media: {media_id}")
        
        try:
            # Download the media
            self.logger.info(f"Downloading YouTube media: {url}")
            downloaded_path = self.youtube_downloader.download(url)
            
            # Add to cache
            cache_path = self.cache.add_to_cache(downloaded_path, media_id, metadata=media_info)
            
            # Update library
            self._update_library_entry(media_id, media_info, file_path=cache_path)
            
            return cache_path
        
        except Exception as e:
            self.logger.error(f"Failed to prepare YouTube media {media_id}: {e}")
            raise MediaPreparationError(f"Failed to prepare YouTube media: {str(e)}")
    
    def _prepare_local_media(self, media_info: Dict) -> str:
        """
        Prepare local media for playback.
        
        Args:
            media_info (dict): Media information
            
        Returns:
            str: Path to media file
            
        Raises:
            MediaPreparationError: If media cannot be prepared
        """
        media_id = media_info['id']
        file_path = media_info.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            raise MediaPreparationError(f"Invalid file path for local media: {media_id}")
        
        try:
            # Add to cache
            cache_path = self.cache.add_to_cache(file_path, media_id, metadata=media_info)
            
            # Update library
            self._update_library_entry(media_id, media_info, file_path=cache_path)
            
            return cache_path
        
        except Exception as e:
            self.logger.error(f"Failed to prepare local media {media_id}: {e}")
            raise MediaPreparationError(f"Failed to prepare local media: {str(e)}")
    
    def _update_library_entry(self, media_id: str, media_info: Dict, file_path: str = None) -> None:
        """
        Update or create a library entry for a media item.
        
        Args:
            media_id (str): Media identifier
            media_info (dict): Media information
            file_path (str, optional): Path to the media file
        """
        # Get existing entry or create new one
        entry = self.library['items'].get(media_id, {})
        
        # Update with new info
        entry.update(media_info)
        
        # Add file info if provided
        if file_path and os.path.exists(file_path):
            # Extract metadata
            file_metadata = metadata_processor.extract_metadata(file_path)
            
            # Update entry with file metadata
            entry.update({
                'file_path': file_path,
                'size_bytes': file_size(file_path),
                'last_accessed': time.time(),
                'format': get_file_extension(file_path),
                'metadata': file_metadata
            })
        
        # Store in library
        self.library['items'][media_id] = entry
        
        # Save library
        self._save_library()
    
    def get_media_info(self, media_id: str) -> Dict:
        """
        Get detailed information about a media item.

        Args:
            media_id (str): Media identifier

        Returns:
            dict: Media details including path, title, duration, etc.
        """
        # Check if media exists in library
        if media_id not in self.library['items']:
            return {}
        
        media_info = self.library['items'][media_id].copy()
        
        # Get cached file path
        cached_path = self.cache.get_cached_path(media_id)
        if cached_path:
            media_info['file_path'] = cached_path
            
            # Update last accessed time
            self.library['items'][media_id]['last_accessed'] = time.time()
            self._save_library()
        
        return media_info
    
    def add_youtube_media(self, url: str, title: Optional[str] = None, tags: Optional[List[str]] = None) -> str:
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
        # Validate URL
        if not self.youtube_downloader.validate_url(url):
            raise InvalidURLError(f"Invalid YouTube URL: {url}")
        
        try:
            # Generate a unique media ID
            media_id = self._generate_media_id()
            
            # Get video info
            video_info = self.youtube_downloader.get_video_info(url)
            
            # Use provided title or the one from YouTube
            media_title = title or video_info.get('title', 'Unknown Title')
            
            # Create media info
            media_info = {
                'id': media_id,
                'title': media_title,
                'source_type': 'youtube',
                'url': url,
                'original_title': video_info.get('title', ''),
                'duration': video_info.get('duration', 0),
                'thumbnail': video_info.get('thumbnail', ''),
                'added': time.time(),
                'tags': tags or []
            }
            
            # Download the media
            self.logger.info(f"Adding YouTube media: {url}")
            downloaded_path = self.youtube_downloader.download(url, custom_filename=media_title)
            
            # Add to cache
            cache_path = self.cache.add_to_cache(downloaded_path, media_id, metadata=media_info)
            
            # Update library
            self._update_library_entry(media_id, media_info, file_path=cache_path)
            
            # Generate thumbnail if not existing
            thumbnail_path = os.path.join(self.thumbnails_dir, f"{media_id}.jpg")
            if video_info.get('thumbnail') and not os.path.exists(thumbnail_path):
                try:
                    metadata_processor.generate_thumbnail(
                        video_info['thumbnail'], 
                        thumbnail_path, 
                        size=(300, 300)
                    )
                    media_info['thumbnail_path'] = thumbnail_path
                    self._update_library_entry(media_id, media_info)
                except Exception as e:
                    self.logger.warning(f"Failed to generate thumbnail: {e}")
            
            return media_id
            
        except Exception as e:
            self.logger.error(f"Failed to add YouTube media: {e}")
            raise DownloadError(f"Failed to add YouTube media: {str(e)}")
    
    def add_local_media(self, file_path: str, title: Optional[str] = None, tags: Optional[List[str]] = None) -> str:
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
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if format is supported
        file_ext = get_file_extension(file_path)
        if file_ext not in self.allowed_formats:
            raise UnsupportedFormatError(
                f"Unsupported file format: {file_ext}. Allowed formats: {', '.join(self.allowed_formats)}"
            )
        
        try:
            # Generate a unique media ID
            media_id = self._generate_media_id()
            
            # Extract metadata from file
            file_metadata = metadata_processor.extract_metadata(file_path)
            
            # Use provided title, metadata title, or filename
            if title:
                media_title = title
            elif file_metadata.get('title'):
                media_title = file_metadata['title']
            else:
                media_title = os.path.splitext(os.path.basename(file_path))[0]
            
            # Create media info
            media_info = {
                'id': media_id,
                'title': media_title,
                'source_type': 'local',
                'file_path': file_path,
                'original_path': file_path,
                'duration': file_metadata.get('duration', 0),
                'added': time.time(),
                'tags': tags or [],
                'metadata': file_metadata
            }
            
            # Add to cache
            cache_path = self.cache.add_to_cache(file_path, media_id, metadata=media_info)
            
            # Update library
            self._update_library_entry(media_id, media_info, file_path=cache_path)
            
            # Generate thumbnail from audio file if possible
            thumbnail_path = os.path.join(self.thumbnails_dir, f"{media_id}.jpg")
            try:
                metadata_processor.generate_thumbnail(
                    file_path, 
                    thumbnail_path, 
                    size=(300, 300)
                )
                media_info['thumbnail_path'] = thumbnail_path
                self._update_library_entry(media_id, media_info)
            except Exception as e:
                self.logger.warning(f"Failed to generate thumbnail: {e}")
            
            return media_id
            
        except (FileNotFoundError, UnsupportedFormatError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Failed to add local media: {e}")
            raise MediaError(f"Failed to add local media: {str(e)}")
    
    def remove_media(self, media_id: str) -> bool:
        """
        Remove media from the library and cache.

        Args:
            media_id (str): Media identifier

        Returns:
            bool: True if successfully removed
        """
        if media_id not in self.library['items']:
            return False
        
        try:
            # Get media info
            media_info = self.library['items'][media_id]
            
            # Remove from cache
            self.cache.remove_from_cache(media_id)
            
            # Remove thumbnail if exists
            thumbnail_path = media_info.get('thumbnail_path')
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    os.remove(thumbnail_path)
                except Exception as e:
                    self.logger.warning(f"Failed to remove thumbnail {thumbnail_path}: {e}")
            
            # Remove from library
            del self.library['items'][media_id]
            self._save_library()
            
            self.logger.info(f"Removed media: {media_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove media {media_id}: {e}")
            return False
    
    def get_cache_status(self) -> Dict:
        """
        Get status of the media cache.

        Returns:
            dict: Cache status including size, item count, etc.
        """
        # Get cache size
        cache_size_bytes = self.cache.get_cache_size()
        
        return {
            'size_bytes': cache_size_bytes,
            'size_mb': round(cache_size_bytes / (1024 * 1024), 2),
            'max_size_mb': self.max_cache_size_mb,
            'usage_percent': round((cache_size_bytes / (self.max_cache_size_mb * 1024 * 1024)) * 100, 2),
            'item_count': len(self.library['items']),
            'cache_dir': self.cache_dir
        }
    
    def clear_cache(self, older_than: Optional[int] = None) -> int:
        """
        Clear media cache.

        Args:
            older_than (int, optional): Clear items older than this many days

        Returns:
            int: Number of items cleared
        """
        if older_than is not None:
            # Clear items older than specified days
            return self.cache.cleanup_cache(max_age_days=older_than)
        else:
            # Clear all items
            cleared_count = 0
            for media_id in list(self.library['items'].keys()):
                if self.cache.remove_from_cache(media_id):
                    cleared_count += 1
            
            # Reset library
            self.library['items'] = {}
            self._save_library()
            
            return cleared_count
    
    def download_with_progress(self, url: str, progress_callback: Callable[[float], None]) -> str:
        """
        Download YouTube media with progress reporting.
        
        Args:
            url (str): YouTube URL
            progress_callback (callable): Function to call with progress (0-100)
            
        Returns:
            str: Media ID of the downloaded media
            
        Raises:
            InvalidURLError: If URL is not valid
            DownloadError: If download fails
        """
        # Validate URL
        if not self.youtube_downloader.validate_url(url):
            raise InvalidURLError(f"Invalid YouTube URL: {url}")
        
        try:
            # Generate a unique media ID
            media_id = self._generate_media_id()
            
            # Get video info
            video_info = self.youtube_downloader.get_video_info(url)
            
            # Create media info
            media_info = {
                'id': media_id,
                'title': video_info.get('title', 'Unknown Title'),
                'source_type': 'youtube',
                'url': url,
                'duration': video_info.get('duration', 0),
                'thumbnail': video_info.get('thumbnail', ''),
                'added': time.time()
            }
            
            # Download with progress reporting
            downloaded_path = self.youtube_downloader.download_with_progress(url, progress_callback)
            
            # Add to cache
            cache_path = self.cache.add_to_cache(downloaded_path, media_id, metadata=media_info)
            
            # Update library
            self._update_library_entry(media_id, media_info, file_path=cache_path)
            
            return media_id
            
        except Exception as e:
            self.logger.error(f"Failed to download media with progress: {e}")
            raise DownloadError(f"Failed to download media: {str(e)}")
    
    def get_all_media(self) -> List[Dict]:
        """
        Get all media items in the library.
        
        Returns:
            list: List of media info dictionaries
        """
        return [self.get_media_info(media_id) for media_id in self.library['items']]
    
    def search_media(self, query: str) -> List[Dict]:
        """
        Search for media items in the library.
        
        Args:
            query (str): Search query
            
        Returns:
            list: List of matching media info dictionaries
        """
        query = query.lower()
        results = []
        
        for media_id, info in self.library['items'].items():
            # Search in title
            if query in info.get('title', '').lower():
                results.append(self.get_media_info(media_id))
                continue
            
            # Search in tags
            if any(query in tag.lower() for tag in info.get('tags', [])):
                results.append(self.get_media_info(media_id))
                continue
            
            # Search in metadata
            metadata = info.get('metadata', {})
            if any(query in str(v).lower() for v in metadata.values() if v):
                results.append(self.get_media_info(media_id))
                continue
        
        return results
    
    def get_media_by_tag(self, tag: str) -> List[Dict]:
        """
        Get media items with a specific tag.
        
        Args:
            tag (str): Tag to search for
            
        Returns:
            list: List of matching media info dictionaries
        """
        tag = tag.lower()
        results = []
        
        for media_id, info in self.library['items'].items():
            if tag in [t.lower() for t in info.get('tags', [])]:
                results.append(self.get_media_info(media_id))
        
        return results
