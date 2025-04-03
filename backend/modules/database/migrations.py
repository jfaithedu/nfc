import sqlite3
import time
from .exceptions import DatabaseMigrationError

def get_db_version(conn):
    """
    Get the current database schema version.

    Args:
        conn: SQLite connection

    Returns:
        int: Current schema version
    """
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT value FROM settings WHERE key = 'schema_version'")
        result = cursor.fetchone()
        return int(result['value']) if result else 0
    except sqlite3.OperationalError:
        # Settings table might not exist yet
        return 0
    except Exception as e:
        raise DatabaseMigrationError(f"Failed to get database version: {str(e)}")

def set_db_version(conn, version):
    """
    Set the database schema version.

    Args:
        conn: SQLite connection
        version (int): Schema version to set
    """
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            ('schema_version', str(version), int(time.time()))
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise DatabaseMigrationError(f"Failed to set database version: {str(e)}")

def migrate_database(conn):
    """
    Run necessary database migrations.

    Args:
        conn: SQLite connection

    Returns:
        bool: True if migrations were applied
    """
    try:
        current_version = get_db_version(conn)
        latest_version = 2  # Update this as new migrations are added

        if current_version >= latest_version:
            return False  # No migrations needed

        # Apply migrations sequentially
        if current_version < 1:
            migrate_to_v1(conn)
            
        if current_version < 2:
            migrate_to_v2(conn)

        # Add more version checks and migrations as needed

        # Update the version
        set_db_version(conn, latest_version)
        return True
    except Exception as e:
        conn.rollback()
        raise DatabaseMigrationError(f"Failed to migrate database: {str(e)}")

def migrate_to_v1(conn):
    """
    Migrate database to version 1.

    Args:
        conn: SQLite connection
    """
    cursor = conn.cursor()

    try:
        # Add any missing columns or tables for version 1
        # For example, add a new column to the media table:
        try:
            cursor.execute("ALTER TABLE media ADD COLUMN thumbnail_path TEXT")
        except sqlite3.OperationalError:
            # Column might already exist
            pass

        # Create any indexes that should be part of v1
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_playback_tag ON playback_history(tag_uid)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_playback_media ON playback_history(media_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_last_played ON media(last_played)')
        except sqlite3.OperationalError as e:
            # Table might not exist yet
            pass

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise DatabaseMigrationError(f"Failed to migrate to version 1: {str(e)}")

def migrate_to_v2(conn):
    """
    Migrate database to version 2.
    Adds URL column to media table and creates index for URL lookups.

    Args:
        conn: SQLite connection
    """
    cursor = conn.cursor()

    try:
        # Add the URL column to the media table
        try:
            cursor.execute("ALTER TABLE media ADD COLUMN url TEXT UNIQUE")
        except sqlite3.OperationalError:
            # Column might already exist
            pass

        # Create index for URL lookups
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_url ON media(url)')
        except sqlite3.OperationalError:
            # Index might already exist
            pass

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise DatabaseMigrationError(f"Failed to migrate to version 2: {str(e)}")
