#!/usr/bin/env python3
"""
Quick test script for the Media Module.

This script allows testing the media module independently of the rest
of the application. It demonstrates downloading, caching, and basic functions.
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path to allow importing the modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from backend.modules.media import media_manager
from backend.modules.media.exceptions import MediaError
from backend.config import CONFIG

def print_section(title):
    """Print a section title."""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)

def main():
    """Main function to test the media module."""
    print_section("MEDIA MODULE TEST")
    
    # Check configuration
    print(f"Cache directory: {CONFIG['media']['cache_dir']}")
    print(f"Max cache size: {CONFIG['media']['max_cache_size_mb']} MB")
    
    # Initialize media manager
    print("\nInitializing media manager...")
    try:
        if media_manager.initialize():
            print("✅ Media manager initialized successfully")
        else:
            print("❌ Failed to initialize media manager")
            return
    except Exception as e:
        print(f"❌ Error initializing media manager: {e}")
        return
    
    try:
        # Get cache status
        print_section("CACHE STATUS")
        cache = media_manager.get_cache_status()
        print(f"Files in cache: {cache['total_files']}")
        print(f"Cache size: {cache['total_size_mb']:.2f} MB")
        print(f"Max cache size: {cache['max_size_mb']} MB")
        
        # YouTube info test
        print_section("YOUTUBE INFO TEST")
        youtube_url = input("Enter a YouTube URL to test (or press Enter to skip): ")
        
        if youtube_url:
            try:
                print("Getting info...")
                info = media_manager.get_media_info(youtube_url)
                print("✅ Successfully retrieved info:")
                print(f"Title: {info['title']}")
                print(f"Duration: {info['duration']} seconds")
                
                # Ask if user wants to download
                if input("\nDownload this video? (y/n): ").lower() == 'y':
                    print("Creating placeholder media record...")
                    
                    # We'd normally use the database here, but for testing
                    # we'll just generate a test ID
                    import uuid
                    media_id = str(uuid.uuid4())
                    
                    # Create a placeholder media_info
                    media_info = {
                        'id': media_id,
                        'url': youtube_url
                    }
                    
                    print(f"Downloading media ID: {media_id}")
                    path = media_manager.prepare_media(media_info)
                    print(f"✅ Downloaded to: {path}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Cache test
        print_section("CACHE MANAGEMENT TEST")
        
        # See if we want to clean cache
        if input("Clean cache? (y/n): ").lower() == 'y':
            result = media_manager.clean_cache(force=True)
            print(f"Cleaned {result['deleted_files']} files ({result['cleaned_bytes'] / (1024*1024):.2f} MB)")
    
    finally:
        # Shutdown
        print_section("SHUTDOWN")
        media_manager.shutdown()
        print("Media manager shut down")

if __name__ == "__main__":
    main()