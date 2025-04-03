#!/usr/bin/env python3
"""
Test script for the database module.

This script tests all the main functionality of the database module.
Run it with Python 3.
"""

import os
import sys
import unittest
import tempfile
import shutil
import time
import json
import random
import string

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from modules.database import (
    initialize, shutdown, set_database_path,
    get_media_for_tag, associate_tag_with_media, remove_tag_association, get_all_tags,
    save_media_info, get_media_info, get_all_media, remove_media,
    log_playback, get_playback_history,
    get_setting, set_setting,
    backup_database, restore_database,
    DatabaseError
)

def random_string(length=10):
    """Generate a random string of fixed length."""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(length))

class TestDatabaseModule(unittest.TestCase):
    """Test cases for the database module."""

    def setUp(self):
        """Set up a test database before each test."""
        # Create temporary directory for test database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test_nfc_player.db')
        set_database_path(self.db_path)
        
        # Initialize the database
        self.assertTrue(initialize())
        
        # Create some test data
        self.test_tag_uid = f"test_tag_{random_string()}"
        self.test_media_id = f"test_media_{random_string()}"
        self.test_media_info = {
            'title': 'Test Song',
            'source': 'youtube',
            'source_url': 'https://youtube.com/watch?v=test',
            'duration': 180,
            'thumbnail_path': '/path/to/thumbnail.jpg',
            'local_path': '/path/to/media.mp3',
            'artist': 'Test Artist',  # This should go to metadata
            'album': 'Test Album'     # This should go to metadata
        }

    def tearDown(self):
        """Clean up after each test."""
        shutdown()
        # Remove the test directory
        shutil.rmtree(self.test_dir)

    def test_media_operations(self):
        """Test media CRUD operations."""
        # Test saving media info
        self.assertTrue(save_media_info(self.test_media_id, self.test_media_info))
        
        # Test retrieving media info
        media = get_media_info(self.test_media_id)
        self.assertIsNotNone(media)
        self.assertEqual(media['title'], self.test_media_info['title'])
        self.assertEqual(media['source'], self.test_media_info['source'])
        
        # Test metadata
        self.assertIn('metadata', media)
        metadata = media['metadata']
        self.assertEqual(metadata['artist'], self.test_media_info['artist'])
        self.assertEqual(metadata['album'], self.test_media_info['album'])
        
        # Test getting all media
        all_media = get_all_media()
        self.assertEqual(len(all_media), 1)
        
        # Test removing media
        self.assertTrue(remove_media(self.test_media_id))
        self.assertIsNone(get_media_info(self.test_media_id))
        all_media = get_all_media()
        self.assertEqual(len(all_media), 0)

    def test_tag_operations(self):
        """Test tag operations."""
        # First save media info
        save_media_info(self.test_media_id, self.test_media_info)
        
        # Test associating tag with media
        self.assertTrue(associate_tag_with_media(
            self.test_tag_uid, 
            self.test_media_id, 
            "Test Tag"
        ))
        
        # Test getting media for tag
        media = get_media_for_tag(self.test_tag_uid)
        self.assertIsNotNone(media)
        self.assertEqual(media['id'], self.test_media_id)
        
        # Test getting all tags
        tags = get_all_tags()
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0]['uid'], self.test_tag_uid)
        
        # Test removing tag association
        self.assertTrue(remove_tag_association(self.test_tag_uid))
        self.assertIsNone(get_media_for_tag(self.test_tag_uid))
        tags = get_all_tags()
        self.assertEqual(len(tags), 0)

    def test_playback_history(self):
        """Test playback history operations."""
        # Setup
        save_media_info(self.test_media_id, self.test_media_info)
        associate_tag_with_media(self.test_tag_uid, self.test_media_id, "Test Tag")
        
        # Test logging playback
        history_id = log_playback(self.test_tag_uid, self.test_media_id, 120)
        self.assertIsNotNone(history_id)
        
        # Test getting playback history
        history = get_playback_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['tag_uid'], self.test_tag_uid)
        self.assertEqual(history[0]['media_id'], self.test_media_id)
        self.assertEqual(history[0]['duration'], 120)
        
        # Test filtering by tag
        history = get_playback_history(tag_uid=self.test_tag_uid)
        self.assertEqual(len(history), 1)
        
        # Test with a non-existent tag
        history = get_playback_history(tag_uid="non_existent_tag")
        self.assertEqual(len(history), 0)

    def test_settings(self):
        """Test settings operations."""
        # Test string setting
        self.assertTrue(set_setting('test_string', 'test_value'))
        self.assertEqual(get_setting('test_string'), 'test_value')
        
        # Test numeric setting
        self.assertTrue(set_setting('test_number', 42))
        self.assertEqual(get_setting('test_number'), 42)
        
        # Test dictionary setting
        test_dict = {'key1': 'value1', 'key2': [1, 2, 3]}
        self.assertTrue(set_setting('test_dict', test_dict))
        result = get_setting('test_dict')
        self.assertEqual(result, test_dict)
        
        # Test default value
        self.assertEqual(get_setting('non_existent', 'default'), 'default')

    def test_backup_restore(self):
        """Test database backup and restore."""
        # Setup some data
        save_media_info(self.test_media_id, self.test_media_info)
        associate_tag_with_media(self.test_tag_uid, self.test_media_id, "Test Tag")
        
        # Create backup
        backup_path = os.path.join(self.test_dir, 'backup.db')
        self.assertTrue(backup_database(backup_path))
        self.assertTrue(os.path.exists(backup_path))
        
        # Modify data
        new_media_id = f"new_media_{random_string()}"
        new_media_info = dict(self.test_media_info)
        new_media_info['title'] = 'New Test Song'
        save_media_info(new_media_id, new_media_info)
        
        # Verify modification
        self.assertEqual(len(get_all_media()), 2)
        
        # Restore from backup
        self.assertTrue(restore_database(backup_path))
        
        # Verify restored data
        media_list = get_all_media()
        self.assertEqual(len(media_list), 1)
        self.assertEqual(media_list[0]['id'], self.test_media_id)
        
        # Check tag association was restored
        media = get_media_for_tag(self.test_tag_uid)
        self.assertIsNotNone(media)
        self.assertEqual(media['id'], self.test_media_id)

if __name__ == '__main__':
    unittest.main()