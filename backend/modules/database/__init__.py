"""
Database module for NFC Music Player.

This module provides persistent data storage for managing NFC tags,
media information, playback history, and system settings.
"""

from .db_manager import (
    # Database initialization and management
    initialize, shutdown, set_database_path,
    backup_database, restore_database,
    
    # Tag management
    get_media_for_tag, associate_tag_with_media, 
    remove_tag_association, get_all_tags,
    
    # Media management
    add_or_get_media_by_url, save_media_info, get_media_info, 
    get_all_media, remove_media,
    
    # Playback history
    log_playback, get_playback_history,
    
    # Settings management
    get_setting, set_setting
)

from .exceptions import (
    DatabaseError, DatabaseConnectionError, 
    DatabaseQueryError, DatabaseMigrationError,
    DatabaseConstraintError, DatabaseBackupError
)
