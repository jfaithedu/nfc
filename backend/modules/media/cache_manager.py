"""
cache_manager.py - Local cache management for the NFC music player.

This module manages the local cache of media files, implementing LRU eviction and size management.
"""

import os
import json
import time
import shutil
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from backend.utils.logger import LoggerMixin
from backend.utils.file_utils import ensure_dir, file_size, copy_file_safe, delete_file_safe
from .exceptions import CacheError


class MediaCache(LoggerMixin):
    """
    Manages cached media files.
    """

    def __init__(self, cache_dir: str, max_size_mb: int = 1000):
        """
        Initialize media cache.

        Args:
            cache_dir (str): Directory for cache
            max_size_mb (int, optional): Maximum cache size in MB
        """
        self.setup_logger()
        self.cache_dir = ensure_dir(cache_dir)
        self.metadata_file = os.path.join(self.cache_dir, 'cache_metadata.json')
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        self.metadata = self._load_metadata()
        
        # Initial cleanup if cache exceeds max size
        if self.get_cache_size() > self.max_size_bytes:
            self.optimize_cache()
    
    def _load_metadata(self) -> Dict:
        """
        Load cache metadata from file, or create new metadata if file doesn't exist.

        Returns:
            dict: Cache metadata
        """
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    metadata = json.load(f)
                self.logger.info(f"Loaded cache metadata: {len(metadata['files'])} entries")
                return metadata
            except Exception as e:
                self.logger.error(f"Failed to load cache metadata: {e}")
                # If metadata file is corrupted, create a new one
        
        # Default metadata structure
        default_metadata = {
            'version': 1,
            'created': datetime.now().isoformat(),
            'files': {}
        }
        
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(default_metadata, f, indent=2)
            self.logger.info("Created new cache metadata file")
        except Exception as e:
            self.logger.error(f"Failed to create cache metadata file: {e}")
        
        return default_metadata
    
    def _save_metadata(self) -> bool:
        """
        Save cache metadata to file.

        Returns:
            bool: True if successful
        """
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save cache metadata: {e}")
            return False
    
    def _update_access_time(self, media_id: str) -> None:
        """
        Update last access time for a file in cache.

        Args:
            media_id (str): Media identifier
        """
        if media_id in self.metadata['files']:
            self.metadata['files'][media_id]['last_accessed'] = time.time()
            self._save_metadata()
    
    def get_cached_path(self, media_id: str) -> Optional[str]:
        """
        Get path to cached media file if it exists.

        Args:
            media_id (str): Media identifier

        Returns:
            str or None: Path to cached file or None if not cached
        """
        if media_id not in self.metadata['files']:
            return None
        
        file_info = self.metadata['files'][media_id]
        file_path = file_info['path']
        
        # Check if file exists
        if not os.path.exists(file_path):
            self.logger.warning(f"Cache entry exists but file not found: {file_path}")
            # Remove invalid entry
            del self.metadata['files'][media_id]
            self._save_metadata()
            return None
        
        # Update access time
        self._update_access_time(media_id)
        
        return file_path
    
    def add_to_cache(self, source_path: str, media_id: str, metadata: Optional[Dict] = None) -> str:
        """
        Add a file to the cache.

        Args:
            source_path (str): Path to the source file
            media_id (str): Media identifier
            metadata (dict, optional): Metadata to associate with the file

        Returns:
            str: Path to cached file

        Raises:
            CacheError: If file cannot be added to cache
        """
        if not os.path.exists(source_path):
            raise CacheError(f"Source file does not exist: {source_path}")
        
        # Create cache directory if it doesn't exist
        ensure_dir(self.cache_dir)
        
        # Generate cache file path
        # Use subdirectories based on first 2 chars of ID to avoid too many files in one dir
        if len(media_id) >= 2:
            subdir = os.path.join(self.cache_dir, media_id[:2])
            ensure_dir(subdir)
            cached_path = os.path.join(subdir, f"{media_id}{os.path.splitext(source_path)[1]}")
        else:
            cached_path = os.path.join(self.cache_dir, f"{media_id}{os.path.splitext(source_path)[1]}")
        
        # Check if we need to optimize cache before adding new file
        source_size = file_size(source_path)
        if self.get_cache_size() + source_size > self.max_size_bytes:
            self.optimize_cache(needed_bytes=source_size)
        
        # Copy the file to cache
        try:
            copy_file_safe(source_path, cached_path, overwrite=True)
        except Exception as e:
            raise CacheError(f"Failed to copy file to cache: {e}")
        
        # Update metadata
        current_time = time.time()
        file_metadata = {
            'path': cached_path,
            'size': file_size(cached_path),
            'added': current_time,
            'last_accessed': current_time,
            'source': source_path
        }
        
        # Add any additional metadata
        if metadata:
            file_metadata['metadata'] = metadata
        
        self.metadata['files'][media_id] = file_metadata
        self._save_metadata()
        
        self.logger.info(f"Added file to cache: {media_id} -> {cached_path}")
        return cached_path
    
    def remove_from_cache(self, media_id: str) -> bool:
        """
        Remove a file from the cache.

        Args:
            media_id (str): Media identifier

        Returns:
            bool: True if file was removed
        """
        if media_id not in self.metadata['files']:
            return False
        
        file_path = self.metadata['files'][media_id]['path']
        
        # Delete the file
        try:
            if os.path.exists(file_path):
                delete_file_safe(file_path)
        except Exception as e:
            self.logger.error(f"Failed to delete cache file {file_path}: {e}")
            # Continue to remove metadata even if file deletion failed
        
        # Remove metadata
        del self.metadata['files'][media_id]
        self._save_metadata()
        
        self.logger.info(f"Removed file from cache: {media_id}")
        return True
    
    def get_cache_size(self) -> int:
        """
        Get current cache size.

        Returns:
            int: Size in bytes
        """
        total_size = 0
        # Use metadata for quick calculation
        for media_id, info in self.metadata['files'].items():
            total_size += info.get('size', 0)
        return total_size
    
    def _get_lru_files(self) -> List[Tuple[str, float]]:
        """
        Get files sorted by least recently used.

        Returns:
            list: List of tuples (media_id, last_accessed_time)
        """
        files = []
        for media_id, info in self.metadata['files'].items():
            last_accessed = info.get('last_accessed', 0)
            files.append((media_id, last_accessed))
        
        # Sort by last_accessed time (oldest first)
        return sorted(files, key=lambda x: x[1])
    
    def cleanup_cache(self, max_age_days: Optional[int] = None) -> int:
        """
        Clean up cache by removing old or excess files.

        Args:
            max_age_days (int, optional): Remove files older than this

        Returns:
            int: Number of files removed
        """
        removed_count = 0
        
        # If max_age_days is specified, remove files older than that
        if max_age_days is not None:
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            
            # Find files older than cutoff_time
            files_to_remove = []
            for media_id, info in self.metadata['files'].items():
                if info.get('last_accessed', 0) < cutoff_time:
                    files_to_remove.append(media_id)
            
            # Remove the files
            for media_id in files_to_remove:
                if self.remove_from_cache(media_id):
                    removed_count += 1
        
        # Also check for and remove any orphaned files in the cache directory
        known_paths = {info['path'] for info in self.metadata['files'].values()}
        
        for root, _, files in os.walk(self.cache_dir):
            for filename in files:
                # Skip the metadata file
                if filename == os.path.basename(self.metadata_file):
                    continue
                
                file_path = os.path.join(root, filename)
                if file_path not in known_paths:
                    try:
                        delete_file_safe(file_path)
                        removed_count += 1
                        self.logger.info(f"Removed orphaned file: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Failed to delete orphaned file {file_path}: {e}")
        
        return removed_count
    
    def optimize_cache(self, needed_bytes: int = 0) -> int:
        """
        Optimize cache by removing least recently used files if needed.

        Args:
            needed_bytes (int, optional): Additional space needed

        Returns:
            int: Space freed in bytes
        """
        current_size = self.get_cache_size()
        target_size = self.max_size_bytes - needed_bytes
        
        # If we're already under the target size, no optimization needed
        if current_size <= target_size:
            return 0
        
        # Calculate how much space we need to free
        bytes_to_free = current_size - target_size
        
        # Get files sorted by least recently used
        lru_files = self._get_lru_files()
        
        bytes_freed = 0
        for media_id, _ in lru_files:
            if bytes_freed >= bytes_to_free:
                break
            
            # Get file size before removing
            file_size_bytes = self.metadata['files'][media_id].get('size', 0)
            
            # Remove the file
            if self.remove_from_cache(media_id):
                bytes_freed += file_size_bytes
        
        self.logger.info(f"Optimized cache: freed {bytes_freed} bytes")
        return bytes_freed
