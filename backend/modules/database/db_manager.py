import os
import sqlite3
import time
import shutil
import json
import logging
from .models import DatabaseConnection, create_tables, dict_to_json, json_to_dict
from .migrations import migrate_database
from .exceptions import (
    DatabaseError, DatabaseConnectionError, DatabaseQueryError,
    DatabaseMigrationError, DatabaseConstraintError, DatabaseBackupError
)

# Configure logging
logger = logging.getLogger(__name__)

# Database file path
DEFAULT_DB_PATH = os.path.expanduser("~/.nfc_player/nfc_player.db")
db_path = DEFAULT_DB_PATH

def set_database_path(path):
    """
    Set custom database path.

    Args:
        path (str): Path to database file
    """
    global db_path
    db_path = path
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

def initialize():
    """
    Initialize the database connection and ensure schema is up to date.

    Returns:
        bool: True if initialization successful
    """
    try:
        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        with DatabaseConnection(db_path) as conn:
            create_tables(conn)
            migrate_database(conn)
            
            # Check database integrity
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result['integrity_check'] != 'ok':
                logger.error(f"Database integrity check failed: {result['integrity_check']}")
                return False
                
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

def shutdown():
    """
    Properly close database connections.
    """
    # Since we use context managers, we don't need explicit shutdown code,
    # but could add any cleanup needed here
    logger.info("Database connections closed")

def get_media_for_tag(tag_uid):
    """
    Look up the media associated with an NFC tag.

    Args:
        tag_uid (str): The UID of the NFC tag

    Returns:
        dict or None: Media information if found, None otherwise
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Update last_used timestamp
            current_time = int(time.time())
            cursor.execute(
                "UPDATE tags SET last_used = ? WHERE uid = ?",
                (current_time, tag_uid)
            )
            
            # First get the tag
            cursor.execute(
                "SELECT media_id FROM tags WHERE uid = ?",
                (tag_uid,)
            )
            tag_row = cursor.fetchone()
            
            if not tag_row or not tag_row['media_id']:
                return None
                
            # Then get the associated media
            cursor.execute(
                "SELECT * FROM media WHERE id = ?",
                (tag_row['media_id'],)
            )
            media_row = cursor.fetchone()
            
            if not media_row:
                return None
                
            # Convert row to dict and handle JSON fields
            media_dict = dict(media_row)
            if media_dict.get('metadata'):
                media_dict['metadata'] = json_to_dict(media_dict['metadata'])
                
            return media_dict
    except Exception as e:
        logger.error(f"Error retrieving media for tag {tag_uid}: {str(e)}")
        raise DatabaseQueryError(f"Failed to get media for tag: {str(e)}")

def associate_tag_with_media(tag_uid, media_id, name=None):
    """
    Create or update an association between an NFC tag and media.

    Args:
        tag_uid (str): The UID of the NFC tag
        media_id (str): The ID of the media
        name (str, optional): Human-readable name for this association

    Returns:
        bool: True if association was created/updated successfully
    """
    try:
        current_time = int(time.time())
        
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if media exists
            cursor.execute("SELECT id FROM media WHERE id = ?", (media_id,))
            if not cursor.fetchone():
                raise DatabaseConstraintError(f"Media ID {media_id} does not exist")
            
            # Check if tag already exists
            cursor.execute("SELECT uid FROM tags WHERE uid = ?", (tag_uid,))
            tag_exists = cursor.fetchone() is not None
            
            if tag_exists:
                # Update existing tag
                cursor.execute(
                    "UPDATE tags SET media_id = ?, name = ?, last_used = ? WHERE uid = ?",
                    (media_id, name, current_time, tag_uid)
                )
            else:
                # Create new tag
                cursor.execute(
                    "INSERT INTO tags (uid, media_id, name, last_used, created_at) VALUES (?, ?, ?, ?, ?)",
                    (tag_uid, media_id, name, current_time, current_time)
                )
            
            return True
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error associating tag {tag_uid} with media {media_id}: {str(e)}")
        raise DatabaseConstraintError(f"Failed to associate tag with media: {str(e)}")
    except Exception as e:
        logger.error(f"Error associating tag {tag_uid} with media {media_id}: {str(e)}")
        raise DatabaseQueryError(f"Failed to associate tag with media: {str(e)}")

def remove_tag_association(tag_uid):
    """
    Remove the association for a tag.

    Args:
        tag_uid (str): The UID of the NFC tag

    Returns:
        bool: True if association was removed
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tags WHERE uid = ?", (tag_uid,))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error removing tag association for {tag_uid}: {str(e)}")
        raise DatabaseQueryError(f"Failed to remove tag association: {str(e)}")

def get_all_tags():
    """
    Get all registered tags and their associations.

    Returns:
        list: List of dictionaries with tag information
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, m.title as media_title 
                FROM tags t
                LEFT JOIN media m ON t.media_id = m.id
                ORDER BY t.last_used DESC
            """)
            
            result = []
            for row in cursor.fetchall():
                tag_dict = dict(row)
                result.append(tag_dict)
                
            return result
    except Exception as e:
        logger.error(f"Error retrieving all tags: {str(e)}")
        raise DatabaseQueryError(f"Failed to get all tags: {str(e)}")

def save_media_info(media_id, info):
    """
    Save or update media information in the database.

    Args:
        media_id (str): The ID of the media
        info (dict): Media information (title, source, duration, etc.)

    Returns:
        bool: True if save successful
    """
    try:
        current_time = int(time.time())
        
        # Extract fields from info
        title = info.get('title', '')
        source = info.get('source', '')
        source_url = info.get('source_url', '')
        duration = info.get('duration', 0)
        thumbnail_path = info.get('thumbnail_path', '')
        local_path = info.get('local_path', '')
        
        # Store any additional fields as metadata
        metadata = {k: v for k, v in info.items() if k not in 
                   ['title', 'source', 'source_url', 'duration', 'thumbnail_path', 'local_path']}
        
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if media already exists
            cursor.execute("SELECT id FROM media WHERE id = ?", (media_id,))
            media_exists = cursor.fetchone() is not None
            
            if media_exists:
                # Update existing media
                cursor.execute("""
                    UPDATE media 
                    SET title = ?, source = ?, source_url = ?, duration = ?, 
                        thumbnail_path = ?, local_path = ?, metadata = ?
                    WHERE id = ?
                """, (
                    title, source, source_url, duration,
                    thumbnail_path, local_path, dict_to_json(metadata),
                    media_id
                ))
            else:
                # Insert new media
                cursor.execute("""
                    INSERT INTO media (
                        id, title, source, source_url, duration, 
                        thumbnail_path, local_path, metadata, created_at, last_played
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    media_id, title, source, source_url, duration,
                    thumbnail_path, local_path, dict_to_json(metadata),
                    current_time, 0
                ))
            
            return True
    except Exception as e:
        logger.error(f"Error saving media info for {media_id}: {str(e)}")
        raise DatabaseQueryError(f"Failed to save media info: {str(e)}")

def get_media_info(media_id):
    """
    Get media information from the database.

    Args:
        media_id (str): The ID of the media

    Returns:
        dict or None: Media information if found, None otherwise
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media WHERE id = ?", (media_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            media_dict = dict(row)
            if media_dict.get('metadata'):
                media_dict['metadata'] = json_to_dict(media_dict['metadata'])
                
            return media_dict
    except Exception as e:
        logger.error(f"Error retrieving media info for {media_id}: {str(e)}")
        raise DatabaseQueryError(f"Failed to get media info: {str(e)}")

def get_all_media():
    """
    Get all media entries in the database.

    Returns:
        list: List of dictionaries with media information
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media ORDER BY last_played DESC")
            
            result = []
            for row in cursor.fetchall():
                media_dict = dict(row)
                if media_dict.get('metadata'):
                    media_dict['metadata'] = json_to_dict(media_dict['metadata'])
                result.append(media_dict)
                
            return result
    except Exception as e:
        logger.error(f"Error retrieving all media: {str(e)}")
        raise DatabaseQueryError(f"Failed to get all media: {str(e)}")

def remove_media(media_id):
    """
    Remove media information from the database.

    Args:
        media_id (str): The ID of the media

    Returns:
        bool: True if removal successful
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Remove media references from tags
            cursor.execute("UPDATE tags SET media_id = NULL WHERE media_id = ?", (media_id,))
            
            # Delete media entry
            cursor.execute("DELETE FROM media WHERE id = ?", (media_id,))
            
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error removing media {media_id}: {str(e)}")
        raise DatabaseQueryError(f"Failed to remove media: {str(e)}")

def log_playback(tag_uid, media_id, duration=None):
    """
    Log a playback event in the history.

    Args:
        tag_uid (str): The UID of the NFC tag
        media_id (str): The ID of the media
        duration (int, optional): Playback duration in seconds

    Returns:
        int: ID of the new history entry
    """
    try:
        current_time = int(time.time())
        
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Update last_played in media table
            cursor.execute(
                "UPDATE media SET last_played = ? WHERE id = ?",
                (current_time, media_id)
            )
            
            # Insert playback history
            cursor.execute(
                "INSERT INTO playback_history (tag_uid, media_id, timestamp, duration) VALUES (?, ?, ?, ?)",
                (tag_uid, media_id, current_time, duration)
            )
            
            # Get ID of new entry
            cursor.execute("SELECT last_insert_rowid()")
            row_id = cursor.fetchone()[0]
            
            return row_id
    except Exception as e:
        logger.error(f"Error logging playback for tag {tag_uid}, media {media_id}: {str(e)}")
        raise DatabaseQueryError(f"Failed to log playback: {str(e)}")

def get_playback_history(limit=100, tag_uid=None):
    """
    Get playback history, optionally filtered by tag.

    Args:
        limit (int, optional): Maximum number of records to return
        tag_uid (str, optional): Filter by tag UID

    Returns:
        list: List of dictionaries with playback history
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            if tag_uid:
                query = """
                    SELECT h.*, m.title as media_title, t.name as tag_name
                    FROM playback_history h
                    LEFT JOIN media m ON h.media_id = m.id
                    LEFT JOIN tags t ON h.tag_uid = t.uid
                    WHERE h.tag_uid = ?
                    ORDER BY h.timestamp DESC
                    LIMIT ?
                """
                cursor.execute(query, (tag_uid, limit))
            else:
                query = """
                    SELECT h.*, m.title as media_title, t.name as tag_name
                    FROM playback_history h
                    LEFT JOIN media m ON h.media_id = m.id
                    LEFT JOIN tags t ON h.tag_uid = t.uid
                    ORDER BY h.timestamp DESC
                    LIMIT ?
                """
                cursor.execute(query, (limit,))
            
            result = []
            for row in cursor.fetchall():
                result.append(dict(row))
                
            return result
    except Exception as e:
        logger.error(f"Error retrieving playback history: {str(e)}")
        raise DatabaseQueryError(f"Failed to get playback history: {str(e)}")

def get_setting(key, default=None):
    """
    Get an application setting.

    Args:
        key (str): Setting key
        default: Default value if setting not found

    Returns:
        The setting value, or default if not found
    """
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            if result:
                try:
                    # Attempt to parse JSON
                    return json.loads(result['value'])
                except json.JSONDecodeError:
                    # Return as is if not JSON
                    return result['value']
            return default
    except Exception as e:
        logger.error(f"Error retrieving setting {key}: {str(e)}")
        raise DatabaseQueryError(f"Failed to get setting: {str(e)}")

def set_setting(key, value):
    """
    Save an application setting.

    Args:
        key (str): Setting key
        value: Setting value (must be JSON serializable)

    Returns:
        bool: True if setting was saved
    """
    try:
        current_time = int(time.time())
        
        # Convert value to JSON string
        if not isinstance(value, str):
            value = json.dumps(value)
        
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, current_time)
            )
            
            return True
    except Exception as e:
        logger.error(f"Error saving setting {key}: {str(e)}")
        raise DatabaseQueryError(f"Failed to save setting: {str(e)}")

def backup_database(backup_path):
    """
    Create a backup of the database.

    Args:
        backup_path (str): Path to save the backup

    Returns:
        bool: True if backup successful
    """
    try:
        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Create backup using SQLite's built-in backup API
        with DatabaseConnection(db_path) as conn:
            # Perform integrity check before backup
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            if result['integrity_check'] != 'ok':
                raise DatabaseBackupError(f"Database integrity check failed: {result['integrity_check']}")
            
            # Create database backup using file copy (SQLite backup API would be better but requires more code)
            shutil.copy2(db_path, backup_path)
            
            # Record backup in settings
            backup_info = {
                'timestamp': int(time.time()),
                'path': backup_path
            }
            set_setting('last_backup', backup_info)
            
            return True
    except Exception as e:
        logger.error(f"Error backing up database to {backup_path}: {str(e)}")
        raise DatabaseBackupError(f"Failed to create database backup: {str(e)}")

def restore_database(backup_path):
    """
    Restore the database from a backup.

    Args:
        backup_path (str): Path to the backup file

    Returns:
        bool: True if restore successful
    """
    try:
        if not os.path.exists(backup_path):
            raise DatabaseBackupError(f"Backup file does not exist: {backup_path}")
        
        # Close any open connections
        shutdown()
        
        # Create a backup of the current database first
        temp_backup = f"{db_path}.restore_backup.{int(time.time())}"
        if os.path.exists(db_path):
            shutil.copy2(db_path, temp_backup)
        
        try:
            # Restore from backup
            shutil.copy2(backup_path, db_path)
            
            # Verify the restored database
            with DatabaseConnection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if result['integrity_check'] != 'ok':
                    # Restore failed, roll back
                    if os.path.exists(temp_backup):
                        shutil.copy2(temp_backup, db_path)
                    raise DatabaseBackupError(f"Restored database integrity check failed: {result['integrity_check']}")
                
                # Run migrations if needed
                migrate_database(conn)
            
            # Record restore in settings
            restore_info = {
                'timestamp': int(time.time()),
                'source': backup_path
            }
            set_setting('last_restore', restore_info)
            
            return True
        except Exception as e:
            # Restore failed, roll back
            if os.path.exists(temp_backup):
                shutil.copy2(temp_backup, db_path)
            raise e
    except Exception as e:
        logger.error(f"Error restoring database from {backup_path}: {str(e)}")
        raise DatabaseBackupError(f"Failed to restore database: {str(e)}")
    finally:
        # Clean up temporary backup
        if os.path.exists(temp_backup):
            try:
                os.remove(temp_backup)
            except:
                pass