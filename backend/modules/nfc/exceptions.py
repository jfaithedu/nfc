"""
exceptions.py - Custom exception classes for the NFC module.
"""

class NFCError(Exception):
    """Base exception for all NFC related errors."""
    pass

class NFCHardwareError(NFCError):
    """Exception raised when there's a hardware communication error."""
    pass

class NFCNoTagError(NFCError):
    """Exception raised when an operation requires a tag but none is present."""
    pass

class NFCReadError(NFCError):
    """Exception raised when tag reading fails."""
    pass

class NFCWriteError(NFCError):
    """Exception raised when tag writing fails."""
    pass

class NFCAuthenticationError(NFCError):
    """Exception raised when tag authentication fails."""
    pass

class NFCTagNotWritableError(NFCWriteError):
    """Exception raised when attempting to write NDEF data to a non-writable or incorrectly formatted tag."""
    pass
