"""
NFC-Based Toddler-Friendly Music Player - API Module

This module provides a web-based interface to the NFC music player application.
It creates a REST API server that allows the frontend application to manage
media assignments, write NFC tags, and control the system.
"""

from .api_server import initialize, start, stop, is_running, get_server_url, get_api_status

__all__ = [
    'initialize',
    'start',
    'stop',
    'is_running',
    'get_server_url',
    'get_api_status'
]
