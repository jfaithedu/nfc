"""
file_utils.py - File system utilities for the NFC music player application.

This module provides safe file operations with consistent error handling.
"""

import os
import shutil
import re
from pathlib import Path
from typing import List, Optional, Union

from .exceptions import FileOperationError


def ensure_dir(directory: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory (str): Directory path

    Returns:
        str: Directory path

    Raises:
        FileOperationError: If directory creation fails
    """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
        return directory
    except Exception as e:
        raise FileOperationError(f"Failed to create directory: {directory}", 
                                {"error": str(e)})


def safe_filename(filename: str) -> str:
    """
    Convert a string to a safe filename.

    Args:
        filename (str): Original filename

    Returns:
        str: Safe filename with invalid characters removed
    """
    # Replace invalid characters with underscores
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", filename)
    
    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip().strip(".")
    
    # If the filename is empty after sanitization, use a default name
    if not safe_name:
        safe_name = "unnamed_file"
        
    return safe_name


def get_file_extension(filename: str) -> str:
    """
    Get the extension of a file.

    Args:
        filename (str): Filename

    Returns:
        str: File extension without the dot, or empty string if none
    """
    _, ext = os.path.splitext(filename)
    
    # Remove the dot and return lowercase extension
    return ext[1:].lower() if ext else ""


def file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.

    Args:
        file_path (str): Path to file

    Returns:
        int: File size in bytes

    Raises:
        FileOperationError: If file doesn't exist or can't be accessed
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        raise FileOperationError(f"Failed to get size of file: {file_path}", 
                                {"error": str(e)})


def is_media_file(file_path: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """
    Check if a file is a supported media file.

    Args:
        file_path (str): Path to file
        allowed_extensions (list, optional): List of allowed extensions

    Returns:
        bool: True if file is a supported media file
    """
    if not allowed_extensions:
        # Default list of common media extensions
        allowed_extensions = [
            "mp3", "wav", "flac", "ogg", "aac", "m4a",  # Audio
            "mp4", "avi", "mkv", "mov", "webm"          # Video
        ]
    
    # Get extension and check if it's in the allowed list
    ext = get_file_extension(file_path)
    return ext in allowed_extensions


def copy_file_safe(source: str, destination: str, overwrite: bool = False) -> bool:
    """
    Safely copy a file with error handling.

    Args:
        source (str): Source file path
        destination (str): Destination file path
        overwrite (bool, optional): Overwrite destination if it exists

    Returns:
        bool: True if copy successful

    Raises:
        FileOperationError: If copy operation fails
    """
    try:
        # Check if source exists
        if not os.path.exists(source):
            raise FileOperationError(f"Source file does not exist: {source}")
            
        # Check if destination exists and overwrite is not allowed
        if os.path.exists(destination) and not overwrite:
            raise FileOperationError(f"Destination file already exists: {destination}")
            
        # Create destination directory if it doesn't exist
        dest_dir = os.path.dirname(destination)
        if dest_dir:
            ensure_dir(dest_dir)
            
        # Copy the file
        shutil.copy2(source, destination)
        return True
        
    except FileOperationError:
        # Re-raise FileOperationError exceptions
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to copy file from {source} to {destination}", 
                                {"error": str(e)})


def delete_file_safe(file_path: str) -> bool:
    """
    Safely delete a file with error handling.

    Args:
        file_path (str): Path to file

    Returns:
        bool: True if deletion successful

    Raises:
        FileOperationError: If deletion fails
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileOperationError(f"File does not exist: {file_path}")
            
        # Delete the file
        os.remove(file_path)
        return True
        
    except FileOperationError:
        # Re-raise FileOperationError exceptions
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to delete file: {file_path}", 
                                {"error": str(e)})


def list_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
    """
    List all files in a directory with specified extensions.

    Args:
        directory (str): Directory path
        extensions (list): List of file extensions to include (without dots)

    Returns:
        list: List of file paths

    Raises:
        FileOperationError: If directory doesn't exist or can't be accessed
    """
    try:
        # Check if directory exists
        if not os.path.exists(directory):
            raise FileOperationError(f"Directory does not exist: {directory}")
            
        # Ensure extensions don't have dots
        clean_extensions = [ext.lower().lstrip('.') for ext in extensions]
        
        result = []
        for root, _, files in os.walk(directory):
            for file in files:
                if get_file_extension(file) in clean_extensions:
                    result.append(os.path.join(root, file))
                    
        return result
        
    except FileOperationError:
        # Re-raise FileOperationError exceptions
        raise
    except Exception as e:
        raise FileOperationError(f"Failed to list files in directory: {directory}", 
                                {"error": str(e)})
