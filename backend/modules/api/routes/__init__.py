"""
NFC-Based Toddler-Friendly Music Player - API Routes

This package contains all route handlers for the API server.
"""

import os
import sys
import importlib.util
import logging

# Helper function to import modules that can't be imported via relative imports
def import_module_from_path(module_name, file_path):
    """Import a module from a file path."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Error importing {module_name} from {file_path}: {e}")
        return None

# Get the backend directory path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
config_path = os.path.join(backend_dir, 'config.py')
utils_dir = os.path.join(backend_dir, 'utils')

# Add the backend directory to the path if it's not already there
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import CONFIG
config_module = import_module_from_path("config", config_path)
if config_module:
    CONFIG = config_module.CONFIG
else:
    # Fallback config
    CONFIG = {
        'api': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False
        }
    }

from . import tags, media, system, nfc_writer

__all__ = ['tags', 'media', 'system', 'nfc_writer', 'CONFIG', 'import_module_from_path']
