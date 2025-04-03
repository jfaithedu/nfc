# Database Module - Implementation Guide

## Overview

The Database Module is responsible for managing persistent data storage for the NFC music player application. It provides a SQLite-based data store that handles NFC tag associations, media information, playback history, and system settings. This module ensures data integrity and provides interfaces for other modules to access and modify stored information.

## Core Responsibilities

1. Initialize and maintain the SQLite database schema
2. Provide an interface for NFC tag to media mappings
3. Store and retrieve media metadata
4. Track playback history and usage statistics
5. Handle application settings persistence
6. Implement proper error handling and database migrations

## Implementation Details

### File Structure

```
database/
├── __init__.py               # Package initialization
├── db_manager.py             # Main controller, exposed to other modules
├── models.py                 # Database models and schema definitions
├── migrations.py             # Database migration handling
└── exceptions.py             # Database-specific exception definitions
```

### Key Components

#### 1. Database Manager (`db_manager.py`)

This is the main interface exposed to other modules:

```python
def initialize():
    """
    Initialize the database connection and ensure schema is up to date.

    Returns:
        bool: True if initialization successful
    """

def shutdown():
    """
    Properly close database connections.
    """

def get_media_for_tag(tag_uid):
    """
    Look up the media associated with an NFC tag.

    Args:
        tag_uid (str): The UID of the NFC tag

    Returns:
        dict or None: Media information if found, None otherwise
    """

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

def remove_tag_association(tag_uid):
    """
    Remove the association for a tag.

    Args:
        tag_uid (str): The UID of the NFC tag

    Returns:
        bool: True if association was removed
    """

def get_all_tags():
    """
    Get all registered tags and their associations.

    Returns:
        list: List of dictionaries with tag information
    """

def save_media_info(media_id, info):
    """
    Save or update media information in the database.

    Args:
        media_id (str): The ID of the media
        info (dict): Media information (title, source, duration, etc.)

    Returns:
        bool: True if save successful
    """

def get_media_info(media_id):
    """
    Get media information from the database.

    Args:
        media_id (str): The ID of the media

    Returns:
        dict or None: Media information if found, None otherwise
    """

def get_all_media():
    """
    Get all media entries in the database.

    Returns:
        list: List of dictionaries with media information
    """

def remove_media(media_id):
    """
    Remove media information from the database.

    Args:
        media_id (str): The ID of the media

    Returns:
        bool: True if removal successful
    """

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

def get_playback_history(limit=100, tag_uid=None):
    """
    Get playback history, optionally filtered by tag.

    Args:
        limit (int, optional): Maximum number of records to return
        tag_uid (str, optional): Filter by tag UID

    Returns:
        list: List of dictionaries with playback history
    """

def get_setting(key, default=None):
    """
    Get an application setting.

    Args:
        key (str): Setting key
        default: Default value if setting not found

    Returns:
        The setting value, or default if not found
    """

def set_setting(key, value):
    """
    Save an application setting.

    Args:
        key (str): Setting key
        value: Setting value (must be JSON serializable)

    Returns:
        bool: True if setting was saved
    """

def backup_database(backup_path):
    """
    Create a backup of the database.

    Args:
        backup_path (str): Path to save the backup

    Returns:
        bool: True if backup successful
    """

def restore_database(backup_path):
    """
    Restore the database from a backup.

    Args:
        backup_path (str): Path to the backup file

    Returns:
        bool: True if restore successful
    """
```

#### 2. Database Models (`models.py`)

Define the database schema:

```python
import sqlite3
import json
import time

def create_tables(conn):
    """
    Create database tables if they don't exist.

    Args:
        conn: SQLite connection
    """
    cursor = conn.cursor()

    # Tags table - stores NFC tag information
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tags (
        uid TEXT PRIMARY KEY,
        name TEXT,
        media_id TEXT,
        last_used INTEGER,
        created_at INTEGER
    )
    ''')

    # Media table - stores media information
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media (
        id TEXT PRIMARY KEY,
        title TEXT,
        source TEXT,
        source_url TEXT,
        duration INTEGER,
        thumbnail_path TEXT,
        local_path TEXT,
        metadata TEXT,
        created_at INTEGER,
        last_played INTEGER
    )
    ''')

    # Playback history table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS playback_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tag_uid TEXT,
        media_id TEXT,
        timestamp INTEGER,
        duration INTEGER,
        FOREIGN KEY (tag_uid) REFERENCES tags (uid),
        FOREIGN KEY (media_id) REFERENCES media (id)
    )
    ''')

    # Settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at INTEGER
    )
    ''')

    conn.commit()

class DatabaseConnection:
    """
    Context manager for database connections.
    """

    def __init__(self, db_path):
        """
        Initialize connection to database.

        Args:
            db_path (str): Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None

    def __enter__(self):
        """
        Open connection on context enter.
        """
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close connection on context exit.
        """
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

def dict_to_json(d):
    """Convert dictionary to JSON string."""
    return json.dumps(d) if d else None

def json_to_dict(j):
    """Convert JSON string to dictionary."""
    return json.loads(j) if j else {}
```

#### 3. Database Migrations (`migrations.py`)

Handle database schema upgrades:

```python
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
        return int(result[0]) if result else 0
    except sqlite3.OperationalError:
        # Settings table might not exist yet
        return 0

def set_db_version(conn, version):
    """
    Set the database schema version.

    Args:
        conn: SQLite connection
        version (int): Schema version to set
    """
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ('schema_version', str(version), int(time.time()))
    )
    conn.commit()

def migrate_database(conn):
    """
    Run necessary database migrations.

    Args:
        conn: SQLite connection

    Returns:
        bool: True if migrations were applied
    """
    current_version = get_db_version(conn)
    latest_version = 1  # Update this as new migrations are added

    if current_version >= latest_version:
        return False  # No migrations needed

    # Apply migrations sequentially
    if current_version < 1:
        migrate_to_v1(conn)

    # Add more version checks and migrations as needed

    # Update the version
    set_db_version(conn, latest_version)
    return True

def migrate_to_v1(conn):
    """
    Migrate database to version 1.

    Args:
        conn: SQLite connection
    """
    cursor = conn.cursor()

    # Add any missing columns or tables for version 1
    # For example, add a new column to the media table:
    try:
        cursor.execute("ALTER TABLE media ADD COLUMN thumbnail_path TEXT")
    except sqlite3.OperationalError:
        # Column might already exist
        pass

    conn.commit()
```

#### 4. Exceptions (`exceptions.py`)

Define database-specific exceptions:

```python
class DatabaseError(Exception):
    """Base exception for all database related errors."""
    pass

class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    pass

class DatabaseQueryError(DatabaseError):
    """Exception raised when a database query fails."""
    pass

class DatabaseMigrationError(DatabaseError):
    """Exception raised when database migration fails."""
    pass

class DatabaseConstraintError(DatabaseError):
    """Exception raised when a database constraint is violated."""
    pass

class DatabaseBackupError(DatabaseError):
    """Exception raised when database backup or restore fails."""
    pass
```

### SQLite Database Design

#### 1. Database File Location

- Store the database file in a user-writable location
- Use a clear naming convention like `nfc_player.db`
- Consider a separate location for database backups

#### 2. Schema Design

The database schema consists of four main tables:

1. **Tags Table**:

   - `uid` (TEXT): Primary key, the unique identifier of the NFC tag
   - `name` (TEXT): Human-readable name for the tag
   - `media_id` (TEXT): Foreign key to the media table
   - `last_used` (INTEGER): Unix timestamp of last usage
   - `created_at` (INTEGER): Unix timestamp of creation

2. **Media Table**:

   - `id` (TEXT): Primary key, unique identifier for the media
   - `title` (TEXT): Title of the media
   - `source` (TEXT): Source type (youtube, local, etc.)
   - `source_url` (TEXT): Original URL for remote media
   - `duration` (INTEGER): Duration in seconds
   - `thumbnail_path` (TEXT): Path to thumbnail image
   - `local_path` (TEXT): Path to cached local file
   - `metadata` (TEXT): JSON-encoded additional metadata
   - `created_at` (INTEGER): Unix timestamp of creation
   - `last_played` (INTEGER): Unix timestamp of last playback

3. **Playback History Table**:

   - `id` (INTEGER): Primary key, auto-incrementing
   - `tag_uid` (TEXT): Foreign key to tags table
   - `media_id` (TEXT): Foreign key to media table
   - `timestamp` (INTEGER): Unix timestamp of playback
   - `duration` (INTEGER): Playback duration in seconds

4. **Settings Table**:
   - `key` (TEXT): Primary key, setting name
   - `value` (TEXT): JSON-encoded setting value
   - `updated_at` (INTEGER): Unix timestamp of last update

#### 3. Indexing Strategy

- Add indexes for frequently queried columns
- Consider adding an index on `tag_uid` in the `playback_history` table
- Consider adding an index on `last_played` in the `media` table

### Database Management

#### 1. Connection Handling

- Use a connection pool or context manager for database connections
- Implement proper error handling for connection failures
- Ensure connections are properly closed after use

#### 2. Query Construction

- Use parameterized queries to prevent SQL injection
- Implement proper error handling for query failures
- Use transactions for operations that modify multiple tables

#### 3. Data Validation

- Validate all data before insertion
- Implement appropriate constraints in the schema
- Handle constraint violations gracefully

### Performance Considerations

#### 1. Query Optimization

- Keep queries simple and efficient
- Use indexes for frequently queried columns
- Avoid complex joins and subqueries

#### 2. Connection Management

- Minimize the number of database connections
- Use connection pooling if necessary
- Keep transactions short and focused

#### 3. Database Size

- Implement periodic cleanup of old data
- Consider archiving old playback history
- Monitor database size and performance

### Error Handling and Resilience

#### 1. Database Corruption

- Implement automatic backup before schema changes
- Provide tools for database recovery
- Implement integrity checks during initialization

#### 2. Concurrent Access

- Use proper locking mechanisms for multi-threaded access
- Implement retry logic for busy database
- Handle "database locked" errors gracefully

#### 3. Disk Space Issues

- Check available disk space before operations
- Handle disk full errors gracefully
- Implement cleanup procedures for low disk situations

### Security Considerations

#### 1. Data Protection

- Use appropriate file permissions for the database
- Consider encrypting sensitive data
- Implement proper backup security

#### 2. Input Validation

- Sanitize all inputs before using in queries
- Use parameterized queries exclusively
- Validate data types and ranges

### Backup and Recovery

#### 1. Backup Strategy

- Implement periodic automatic backups
- Store backups in a separate location
- Limit the number of backup files to save space

#### 2. Recovery Process

- Provide tools for database restoration
- Implement verification of backup integrity
- Document the recovery process for administrators

### Testing

#### 1. Unit Testing

- Test all database operations with a test database
- Verify proper error handling
- Test edge cases and constraints

#### 2. Performance Testing

- Test database performance with large datasets
- Verify query efficiency
- Test concurrent access scenarios

#### 3. Migration Testing

- Test migration process with test databases
- Verify data integrity after migrations
- Test recovery from failed migrations

## Common Issues and Solutions

#### 1. Database Locking

- Issue: "database is locked" errors during concurrent access
- Solution: Implement proper connection management and retry logic
- Solution: Keep transactions short and focused

#### 2. Performance Degradation

- Issue: Slow queries as the database grows
- Solution: Add appropriate indexes
- Solution: Implement periodic cleanup and optimization

#### 3. Data Corruption

- Issue: Database corruption due to improper shutdown
- Solution: Use WAL journal mode for better resilience
- Solution: Implement periodic integrity checks

## Resources and References

#### 1. SQLite Documentation

- [SQLite Official Documentation](https://www.sqlite.org/docs.html)
- [SQLite Python Interface](https://docs.python.org/3/library/sqlite3.html)
- [SQLite3 API Documentation](https://pypi.org/project/sqlite3-api/)

#### 2. Database Design

- [SQLite Database Design Best Practices](https://www.sqlite.org/draft/bestpractice.html)
- [Index usage in SQLite](https://www.sqlite.org/queryplanner.html)

#### 3. Backup and Recovery

- [SQLite Backup API](https://www.sqlite.org/backup.html)
- [Online Backup Strategies](https://www.sqlite.org/backup.html)
