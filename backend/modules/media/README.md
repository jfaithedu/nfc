# Media Module

## Overview

The Media Module is responsible for managing media content for the NFC music player. It handles fetching audio from YouTube, caching content for offline playback, and maintaining the media library. This module ensures efficient media retrieval and provides interfaces for media management to other system components.

## Core Responsibilities

1. Fetch audio content from YouTube using yt-dlp
2. Manage local media cache to optimize performance and reduce network usage
3. Handle media metadata (title, duration, thumbnail, etc.)
4. Support offline operation when possible
5. Provide clean, error-handled interfaces to other system components

## Implementation Architecture

### Key Design Principles

1. **Separation of Concerns**
   - Media module focuses solely on media management, downloading, and caching
   - Audio playback is handled entirely by the Audio module
   - No direct BlueALSA dependencies in Media module

2. **Simplified API**
   - Core function is `prepare_media()` which returns a ready-to-play file path
   - Clear error handling through dedicated exception types
   - Consistent interface for both YouTube and local media

3. **Background Processing**
   - Asynchronous downloads to prevent blocking the main thread
   - Queue-based system for managing multiple download requests

### File Structure

```
media/
├── __init__.py        # Package initialization
├── exceptions.py      # Media-specific exception definitions
└── media_manager.py   # Main controller, handling all media functionality
```

## API Reference

### Main Interface

```python
# Initialization and status
def initialize() -> bool
def shutdown() -> None
def is_initialized() -> bool

# Core media operations
def prepare_media(media_info: dict) -> str
def get_media_info(url: str) -> dict
def save_uploaded_media(media_id: str, file_object) -> str

# Cache management
def get_media_cache_status(media_id: str) -> dict
def queue_for_caching(media_id: str) -> bool
def delete_from_cache(media_id: str) -> bool
def get_cache_status() -> dict
def get_cache_size() -> int
def clean_cache(older_than: int = None, force: bool = False) -> dict
```

### Exception Hierarchy

```
MediaError
├── MediaPreparationError
├── DownloadError
├── InvalidURLError
├── UnsupportedFormatError
├── CacheError
└── YouTubeError
    ├── YouTubeInfoError
    └── YouTubeDownloadError
```

## Usage Examples

### Basic Media Preparation

```python
from backend.modules.media import media_manager

# Initialize module
media_manager.initialize()

# Get media path from a database record
media_info = db_manager.get_media_for_tag("04A2B6C3")
media_path = media_manager.prepare_media(media_info)

# Play the media (using audio module)
audio_controller.play(media_path)
```

### Adding YouTube Content

```python
# Get info about a YouTube video
youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
media_info = media_manager.get_media_info(youtube_url)

# Save to database
media_id = db_manager.add_media(
    title=media_info['title'],
    source_url=youtube_url,
    media_type='youtube'
)

# Queue for background download
media_manager.queue_for_caching(media_id)
```

## YouTube Integration Notes

The media module uses yt-dlp to handle YouTube downloads with these features:

1. **Audio Extraction**
   - Downloads only audio tracks to save bandwidth and storage
   - Converts to MP3 format for maximum compatibility
   - Uses 192kbps quality for good audio fidelity

2. **Error Handling**
   - Handles network issues, geo-restrictions, and unavailable videos
   - Falls back to cached content when offline
   - Detailed error reporting for troubleshooting

3. **Cache Management**
   - Smart caching based on media IDs
   - Automatic cleanup when space gets low
   - Background downloading to avoid UI blocking

## Implementation Details

### Media Manager

The media_manager.py file is a self-contained module that handles all media operations including:

- YouTube downloading through yt-dlp
- Cache management with automatic cleanup
- Media preparation for playback
- Background download queue processing

### Cache Strategy

1. **File Naming**
   - Media files are cached using their database ID as the filename
   - Standard extensions (.mp3, .mp4, etc.) are maintained for compatibility
   - Uploaded files are stored in a separate uploads subdirectory

2. **Cleanup Policy**
   - Least Recently Used (LRU) eviction when cache exceeds configured size
   - Option to clean files older than a specified age
   - Automatic cleanup when space is needed for new downloads

### Offline Support

The module handles offline operation by:

1. Checking for cached content before attempting network operations
2. Providing clear error messages when content is unavailable offline
3. Supporting background pre-caching of frequently used content

## BlueALSA Integration

The media module has been redesigned to have zero direct dependencies on BlueALSA or other audio playback systems:

1. Audio playback is completely handled by the audio module
2. The media module only prepares media files and returns their path
3. The audio module handles all BlueALSA/bluez-alsa interactions

This separation ensures that:
- Changes to BlueALSA won't affect the media module
- Media functionality works even if audio is temporarily unavailable
- The codebase is more maintainable with clear module boundaries

## Testing

Test the media module with:

```python
python -m backend.modules.media.test_media
```

The test suite verifies:
- YouTube URL handling and downloading
- Cache management functions
- Error handling scenarios
- Integration with the database
