#!/usr/bin/env python3
"""
Test suite for the media module.

This script tests the functionality of the media module, including YouTube
downloads, caching, and media preparation.
"""

import os
import time
import unittest
import tempfile
import shutil
from pathlib import Path

# Add parent directory to path to allow importing the modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from backend.modules.media import media_manager
from backend.modules.media.exceptions import MediaError

class MediaManagerTest(unittest.TestCase):
    """Test cases for the media_manager module."""
    
    def setUp(self):
        """Set up temporary directories and initialize media manager."""
        # Create a temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.test_dir, 'cache')
        
        # Mock CONFIG for testing
        media_manager.CONFIG = {
            'media': {
                'cache_dir': self.cache_dir,
                'max_cache_size_mb': 100
            }
        }
        
        # Initialize the media manager with test config
        self.assertTrue(media_manager.initialize())
    
    def tearDown(self):
        """Clean up after tests."""
        # Shutdown the media manager
        media_manager.shutdown()
        
        # Remove the temporary directory
        shutil.rmtree(self.test_dir)
    
    def test_initialization(self):
        """Test that the media manager initializes correctly."""
        # Verify the cache directory was created
        self.assertTrue(os.path.exists(self.cache_dir))
        
        # Verify the media manager is initialized
        self.assertTrue(media_manager.is_initialized())
    
    def test_cache_functions(self):
        """Test cache management functions."""
        # Test get_cache_status when cache is empty
        status = media_manager.get_cache_status()
        self.assertEqual(status['total_files'], 0)
        self.assertEqual(status['total_size_bytes'], 0)
        
        # Test get_cache_size
        size = media_manager.get_cache_size()
        self.assertEqual(size, 0)
        
        # Create a test file in the cache
        test_file = os.path.join(self.cache_dir, 'test.mp3')
        with open(test_file, 'wb') as f:
            f.write(b'x' * 1024)  # 1KB test file
        
        # Test updated cache status
        status = media_manager.get_cache_status()
        self.assertEqual(status['total_files'], 1)
        self.assertGreaterEqual(status['total_size_bytes'], 1024)
        
        # Test clean_cache with force=True
        result = media_manager.clean_cache(force=True)
        self.assertEqual(result['deleted_files'], 1)
        self.assertFalse(os.path.exists(test_file))
    
    def test_get_youtube_info(self):
        """Test getting info from a YouTube URL."""
        # This test requires internet connectivity
        try:
            # Use a stable test video (YouTube's own test video)
            url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            info = media_manager._get_youtube_info(url)
            
            # Verify basic info was retrieved
            self.assertIn('title', info)
            self.assertIn('duration', info)
            self.assertGreater(info['duration'], 0)
            
        except Exception as e:
            # Skip test if no internet connection
            if "Failed to get YouTube info" in str(e):
                self.skipTest("No internet connection or YouTube API issue")
            else:
                raise
    
    def test_error_handling(self):
        """Test error handling for various scenarios."""
        # Test with invalid media_info
        with self.assertRaises(MediaError):
            media_manager.prepare_media(None)
        
        # Test with missing media_id
        with self.assertRaises(MediaError):
            media_manager.prepare_media({})
        
        # Test with invalid media_id
        with self.assertRaises(MediaError):
            media_manager.prepare_media({'id': 'nonexistent_id'})
    
    def test_media_cache_status(self):
        """Test getting cache status for a specific media ID."""
        # Test with non-existent media
        status = media_manager.get_media_cache_status('nonexistent_id')
        self.assertFalse(status['cached'])
        
        # Create a test file in the cache for a specific media ID
        media_id = 'test_media_id'
        test_file = os.path.join(self.cache_dir, f'{media_id}.mp3')
        with open(test_file, 'wb') as f:
            f.write(b'x' * 1024)  # 1KB test file
        
        # Test cache status for existing media
        status = media_manager.get_media_cache_status(media_id)
        self.assertTrue(status['cached'])
        self.assertEqual(status['path'], test_file)
        self.assertGreaterEqual(status['size_bytes'], 1024)

if __name__ == '__main__':
    unittest.main()