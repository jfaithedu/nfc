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

    # Create indexes for improved query performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_playback_tag ON playback_history(tag_uid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_playback_media ON playback_history(media_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_media_last_played ON media(last_played)')

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
        
        # Enable foreign keys
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Use WAL mode for better concurrency and resilience
        cursor.execute("PRAGMA journal_mode = WAL")
        
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