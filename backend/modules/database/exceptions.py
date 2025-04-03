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