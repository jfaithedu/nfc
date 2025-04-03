# Media Module - Implementation Guide

## Overview

The Media Module is responsible for managing media content for the NFC music player. It handles fetching audio from YouTube, caching content for offline playback, and maintaining the media library. This module ensures efficient media retrieval and provides interfaces for media management to other system components.

## Core Responsibilities

1. Fetch audio content from YouTube using yt-dlp
2. Manage local media cache to optimize performance and reduce network usage
3. Handle media metadata (title, duration, thumbnail, etc.)
4. Support offline operation when possible
5. Provide clean, error-handled interfaces to other system components

## Implementation Details

### File Structure

```
media/
├── __init__.py               # Package initialization
├── media_manager.py          # Main controller, exposed to other modules
├── youtube_handler.py        # YouTube download and processing
├── cache_manager.py          # Local cache management
├── metadata_processor.py     # Process and store media metadata
└── exceptions.py             # Media-specific exception definitions
```

### Key Components

#### 1. Media Manager (`media_manager.py`)

This is the main interface exposed to other modules:

```python
def initialize():
    """
    Initialize the media manager.

    Returns:
        bool: True if initialization successful
    """

def shutdown():
    """
    Perform cleanup operations before shutdown.
    """

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

def get_media_info(media_id):
    """
    Get detailed information about a media item.

    Args:
        media_id (str): Media identifier

    Returns:
        dict: Media details including path, title, duration, etc.
    """

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

def remove_media(media_id):
    """
    Remove media from the library and cache.

    Args:
        media_id (str): Media identifier

    Returns:
        bool: True if successfully removed
    """

def get_cache_status():
    """
    Get status of the media cache.

    Returns:
        dict: Cache status including size, item count, etc.
    """

def clear_cache(older_than=None):
    """
    Clear media cache.

    Args:
        older_than (int, optional): Clear items older than this many days

    Returns:
        int: Number of items cleared
    """
```

#### 2. YouTube Handler (`youtube_handler.py`)

Handles YouTube content downloading and processing:

```python
class YouTubeDownloader:
    """
    Handles downloading content from YouTube using yt-dlp.
    """

    def __init__(self, output_dir, yt_dlp_options=None):
        """
        Initialize YouTube downloader.

        Args:
            output_dir (str): Directory to save downloaded files
            yt_dlp_options (dict, optional): Options for yt-dlp
        """

    def validate_url(self, url):
        """
        Validate if URL is a valid YouTube URL.

        Args:
            url (str): URL to validate

        Returns:
            bool: True if valid YouTube URL
        """

    def get_video_info(self, url):
        """
        Get information about a YouTube video without downloading.

        Args:
            url (str): YouTube URL

        Returns:
            dict: Video information (title, duration, thumbnail, etc.)

        Raises:
            YouTubeInfoError: If info cannot be retrieved
        """

    def download(self, url, custom_filename=None):
        """
        Download audio from YouTube video.

        Args:
            url (str): YouTube URL
            custom_filename (str, optional): Custom filename for the downloaded file

        Returns:
            str: Path to downloaded file

        Raises:
            YouTubeDownloadError: If download fails
        """

    def download_with_progress(self, url, progress_callback=None):
        """
        Download with progress reporting via callback.

        Args:
            url (str): YouTube URL
            progress_callback (callable, optional): Function to call with progress updates

        Returns:
            str: Path to downloaded file
        """
```

#### 3. Cache Manager (`cache_manager.py`)

Manages the local media cache:

```python
class MediaCache:
    """
    Manages cached media files.
    """

    def __init__(self, cache_dir, max_size_mb=1000):
        """
        Initialize media cache.

        Args:
            cache_dir (str): Directory for cache
            max_size_mb (int, optional): Maximum cache size in MB
        """

    def get_cached_path(self, media_id):
        """
        Get path to cached media file if it exists.

        Args:
            media_id (str): Media identifier

        Returns:
            str or None: Path to cached file or None if not cached
        """

    def add_to_cache(self, source_path, media_id, metadata=None):
        """
        Add a file to the cache.

        Args:
            source_path (str): Path to the source file
            media_id (str): Media identifier
            metadata (dict, optional): Metadata to associate with the file

        Returns:
            str: Path to cached file
        """

    def remove_from_cache(self, media_id):
        """
        Remove a file from the cache.

        Args:
            media_id (str): Media identifier

        Returns:
            bool: True if file was removed
        """

    def get_cache_size(self):
        """
        Get current cache size.

        Returns:
            int: Size in bytes
        """

    def cleanup_cache(self, max_age_days=None):
        """
        Clean up cache by removing old or excess files.

        Args:
            max_age_days (int, optional): Remove files older than this

        Returns:
            int: Number of files removed
        """

    def optimize_cache(self):
        """
        Optimize cache by removing least recently used files if needed.

        Returns:
            int: Space freed in bytes
        """
```

#### 4. Metadata Processor (`metadata_processor.py`)

Handles media metadata extraction and management:

```python
def extract_metadata(file_path):
    """
    Extract metadata from an audio file.

    Args:
        file_path (str): Path to audio file

    Returns:
        dict: Metadata including title, artist, duration, etc.
    """

def embed_metadata(file_path, metadata):
    """
    Embed metadata into an audio file.

    Args:
        file_path (str): Path to audio file
        metadata (dict): Metadata to embed

    Returns:
        bool: True if successful
    """

def generate_thumbnail(source, output_path, size=(300, 300)):
    """
    Generate thumbnail for media.

    Args:
        source (str): Source (file path or URL)
        output_path (str): Path to save thumbnail
        size (tuple, optional): Thumbnail dimensions

    Returns:
        str: Path to generated thumbnail
    """

def sanitize_filename(filename):
    """
    Sanitize filename to be filesystem-safe.

    Args:
        filename (str): Input filename

    Returns:
        str: Sanitized filename
    """
```

#### 5. Exceptions (`exceptions.py`)

Define media-specific exceptions:

```python
class MediaError(Exception):
    """Base exception for all media related errors."""
    pass

class MediaPreparationError(MediaError):
    """Exception raised when media cannot be prepared for playback."""
    pass

class DownloadError(MediaError):
    """Exception raised when media cannot be downloaded."""
    pass

class InvalidURLError(MediaError):
    """Exception raised when URL is invalid."""
    pass

class UnsupportedFormatError(MediaError):
    """Exception raised when media format is not supported."""
    pass

class CacheError(MediaError):
    """Exception raised for cache-related issues."""
    pass

class YouTubeError(MediaError):
    """Base exception for YouTube-related errors."""
    pass

class YouTubeInfoError(YouTubeError):
    """Exception raised when YouTube info cannot be retrieved."""
    pass

class YouTubeDownloadError(YouTubeError):
    """Exception raised when YouTube download fails."""
    pass
```

### YouTube Integration

For the YouTube integration with yt-dlp, follow these guidelines:

1. **Setting Up yt-dlp**:

   - Use the yt-dlp Python library, not the command-line tool
   - Configure yt-dlp for audio-only downloads to save bandwidth
   - Set appropriate quality settings (192kbps MP3 is recommended)

2. **URL Validation**:

   - Implement strict validation of YouTube URLs
   - Support various YouTube URL formats (short links, playlist links, etc.)
   - Sanitize URLs to prevent command injection

3. **Download Process**:

   - Implement proper error handling for network issues
   - Support downloading in a background thread to prevent UI blocking
   - Provide progress feedback for long downloads

4. **Content Filtering**:
   - Implement safeguards against inappropriate content
   - Restrict playlist access to pre-approved playlists only
   - Consider implementing duration limits (e.g., no videos longer than 10 min)

### Caching Strategy

1. **Cache Organization**:

   - Store files with consistent naming scheme based on media_id
   - Maintain index file with metadata (last access time, size, etc.)
   - Use subdirectories to prevent too many files in one directory

2. **Cache Optimization**:

   - Implement least-recently-used (LRU) eviction policy
   - Set maximum cache size and automatically clean up when exceeded
   - Schedule periodic cleanup of old cache files

3. **Cache Integrity**:
   - Implement validation of cached files before use
   - Recover from corrupt cache files by re-downloading
   - Log cache operations for debugging

### Offline Operation

1. **Offline Detection**:

   - Detect network connectivity before attempting downloads
   - Fall back gracefully to cached content when offline
   - Provide clear feedback when content is unavailable offline

2. **Content Pre-caching**:
   - Implement option to pre-cache frequently used content
   - Allow specifying content that should always be kept in cache
   - Provide functions to manage offline content

### Performance Considerations

1. **Download Optimization**:

   - Use concurrent downloads for efficiency
   - Implement bandwidth throttling to prevent network saturation
   - Prioritize downloads based on usage patterns

2. **Storage Management**:

   - Monitor available disk space before downloads
   - Implement automatic cleanup when storage is low
   - Compress audio files if necessary to save space

3. **Metadata Handling**:
   - Cache metadata separately from content for quick access
   - Use efficient formats for metadata storage (JSON, SQLite)
   - Implement lazy loading of metadata to improve startup time

### Error Handling and Resilience

1. **Network Issues**:

   - Implement proper timeouts for network operations
   - Retry failed downloads with exponential backoff
   - Log detailed network diagnostics for troubleshooting

2. **Content Issues**:

   - Handle region-restricted or age-restricted content
   - Validate downloaded files to ensure they're playable
   - Implement fallback mechanisms for failed content

3. **Recovery Mechanisms**:
   - Maintain journal of in-progress operations for crash recovery
   - Implement automatic repair of corrupted cache index
   - Provide tools for manual cache management

### Security Considerations

1. **URL Handling**:

   - Sanitize all URLs before processing
   - Use allowlists for approved domains (youtube.com, youtu.be)
   - Prevent potential command injection in download processes

2. **Content Validation**:

   - Scan downloaded files for corruption or malformed content
   - Validate file types match expected formats
   - Use secure temporary directories during processing

3. **External Tools**:
   - Run yt-dlp with minimal permissions
   - Sanitize all command-line arguments
   - Monitor and limit resource usage

### Testing

1. **Unit Testing**:

   - Test URL validation with various input formats
   - Mock YouTube API responses for testing without network
   - Test cache operations with simulated disk constraints

2. **Integration Testing**:

   - Test actual downloads with sample YouTube videos
   - Verify media playback with the audio module
   - Test offline operation by disabling network

3. **Performance Testing**:
   - Measure download speeds and optimization effectiveness
   - Test with large cache sizes to ensure scaling
   - Verify memory usage during extended operation

## Common Issues and Solutions

1. **Slow Downloads**:

   - Check network bandwidth limitations
   - Verify yt-dlp is configured for optimal performance
   - Consider implementing parallel downloads

2. **Cache Corruption**:

   - Implement checksums for cached files
   - Create automatic recovery procedures
   - Maintain backup index of cache contents

3. **YouTube API Changes**:
   - Keep yt-dlp updated to latest version
   - Implement fallback methods for content access
   - Monitor logs for YouTube-related errors

## Resources and References

1. **yt-dlp Documentation**:

   - [yt-dlp GitHub repository](https://github.com/yt-dlp/yt-dlp)
   - [yt-dlp Python library usage](https://github.com/yt-dlp/yt-dlp#embedding-yt-dlp)

2. **Audio Format Information**:

   - [MP3 specification](https://www.loc.gov/preservation/digital/formats/fdd/fdd000012.shtml)
   - [Audio file format comparison](https://en.wikipedia.org/wiki/Comparison_of_audio_coding_formats)

3. **Caching Strategies**:
   - [Cache replacement policies](https://en.wikipedia.org/wiki/Cache_replacement_policies)
   - [Efficient file caching techniques](https://www.usenix.org/legacy/events/fast05/tech/full_papers/weil/weil.pdf)
