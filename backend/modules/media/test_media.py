"""
Test script for the media module functionality.

This script demonstrates the key functionality of the media module, including:
- YouTube download and playback
- Media library management
- Cache operations
"""

import os
import sys
import time
from pprint import pprint

# Add the root directory to path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '../../..'))
sys.path.insert(0, root_dir)

from backend import config
config.load_config()  # Ensure config is loaded

import backend.modules.media as media
from backend.modules.media.exceptions import (
    MediaError,
    InvalidURLError,
    DownloadError,
    UnsupportedFormatError
)


def print_divider(title):
    """Print a section divider with title."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80 + "\n")


def test_initialization():
    """Test media module initialization."""
    print_divider("Testing Media Module Initialization")
    
    # Initialize the media module
    success = media.initialize()
    print(f"Media module initialization: {'Success' if success else 'Failed'}")
    
    # Check cache status
    cache_status = media.get_cache_status()
    print("\nInitial cache status:")
    pprint(cache_status)
    
    return success


def test_youtube_download(url):
    """Test downloading from YouTube."""
    print_divider(f"Testing YouTube Download: {url}")
    
    try:
        # Add YouTube media
        print(f"Downloading YouTube URL: {url}")
        start_time = time.time()
        media_id = media.add_youtube_media(url, tags=["test", "demo"])
        download_time = time.time() - start_time
        
        print(f"Download successful! Media ID: {media_id}")
        print(f"Download completed in {download_time:.2f} seconds")
        
        # Get media info
        media_info = media.get_media_info(media_id)
        print("\nMedia Info:")
        pprint(media_info)
        
        # Prepare the media (should use cached version)
        print("\nPreparing media for playback...")
        file_path = media.prepare_media(media_info)
        print(f"Media file ready at: {file_path}")
        
        # Verify file exists
        if os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            print(f"File exists: {os.path.basename(file_path)} ({file_size_mb:.2f} MB)")
        else:
            print("ERROR: File does not exist!")
        
        return media_id
    
    except InvalidURLError as e:
        print(f"Invalid URL Error: {e}")
    except DownloadError as e:
        print(f"Download Error: {e}")
    except MediaError as e:
        print(f"Media Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")
    
    return None


def test_media_operations(media_id):
    """Test various operations on an existing media item."""
    print_divider(f"Testing Media Operations for ID: {media_id}")
    
    if not media_id:
        print("No media ID provided, skipping tests.")
        return
    
    try:
        # Get all media
        all_media = media.get_all_media()
        print(f"Total media in library: {len(all_media)}")
        
        # Search media
        media_info = media.get_media_info(media_id)
        search_term = media_info.get('title', '').split()[0]  # Use first word of title
        
        print(f"\nSearching for term: '{search_term}'")
        search_results = media.search_media(search_term)
        print(f"Found {len(search_results)} results")
        
        # Get by tag
        print("\nSearching for tag: 'test'")
        tag_results = media.get_media_by_tag("test")
        print(f"Found {len(tag_results)} results with tag 'test'")
        
        # Get cache status after adding media
        cache_status = media.get_cache_status()
        print("\nCurrent cache status:")
        pprint(cache_status)
        
    except Exception as e:
        print(f"Error during media operations: {e}")


def test_cleanup(media_id=None):
    """Test cleanup operations."""
    print_divider("Testing Cleanup Operations")
    
    try:
        if media_id:
            # Remove specific media
            print(f"Removing media: {media_id}")
            result = media.remove_media(media_id)
            print(f"Media removal result: {'Success' if result else 'Failed'}")
        
        # Get final cache status
        cache_status = media.get_cache_status()
        print("\nFinal cache status:")
        pprint(cache_status)
        
        # Shutdown
        print("\nShutting down media module...")
        media.shutdown()
        print("Shutdown complete")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")


def main():
    """Main test function."""
    test_url = "https://www.youtube.com/watch?v=DkoTsoxEk3g"  # Default test URL
    
    # Allow specifying a different URL via command line
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    print("\n=== MEDIA MODULE TEST ===\n")
    print(f"Using test URL: {test_url}")
    
    # Run tests
    if test_initialization():
        media_id = test_youtube_download(test_url)
        if media_id:
            test_media_operations(media_id)
            
            # Ask if the user wants to keep the downloaded media
            keep_media = input("\nKeep downloaded media? (y/n): ").lower().strip()
            if keep_media != 'y':
                test_cleanup(media_id)
            else:
                test_cleanup()
        else:
            test_cleanup()
    
    print("\n=== TEST COMPLETE ===\n")


if __name__ == "__main__":
    main()
