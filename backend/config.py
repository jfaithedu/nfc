"""
NFC-Based Toddler-Friendly Music Player - Configuration

This module contains all the configuration settings for the application.
"""

import os
import json

# Default configuration
DEFAULT_CONFIG = {
    # Application settings
    "app_name": "NFC Music Player",
    "debug_mode": False,
    
    # Database settings
    "database": {
        "path": "data/nfc_player.db",
    },
    
    # NFC settings
    "nfc": {
        "poll_interval": 0.1,  # seconds
        "i2c_bus": 1,
        "i2c_address": 0x24,  # Replace with actual address of your NFC HAT
    },
    
    # Media settings
    "media": {
        "cache_dir": "data/media_cache",
        "allowed_formats": ["mp3", "wav", "ogg", "m4a"],
        "max_cache_size_mb": 10000,  # 10 GB - increased for permanent caching
        "cache_cleanup_disabled": True,  # Disable automatic cache cleanup
        "yt_dlp_options": {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        },
    },
    
    # Audio settings
    "audio": {
        "bluetooth_device": "",  # Will be populated from saved device or user selection
        "volume_default": 70,  # percent
        "volume_min": 10,  # percent
        "volume_max": 90,  # percent
        "error_sound": "resources/error.mp3",
        "success_sound": "resources/success.mp3",
    },
    
    # API settings
    "api": {
        "host": "0.0.0.0",  # Listen on all interfaces
        "port": 5000,
        "ssl_enabled": False,
        "ssl_cert": "resources/cert.pem",
        "ssl_key": "resources/key.pem",
        "admin_pin": "1234",  # Default PIN, should be changed
    },
}

# Path to user configuration file
CONFIG_PATH = os.path.expanduser("~/.nfc_player/config.json")

# Global CONFIG object
CONFIG = {}

def load_config():
    """Load configuration from file or create default if not exists."""
    global CONFIG
    
    # Start with default config
    CONFIG = DEFAULT_CONFIG.copy()
    
    # Create config directory if not exists
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    
    # Try to load user config
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                user_config = json.load(f)
                
            # Merge user config with defaults (shallow update for each section)
            for section, values in user_config.items():
                if section in CONFIG and isinstance(CONFIG[section], dict) and isinstance(values, dict):
                    CONFIG[section].update(values)
                else:
                    CONFIG[section] = values
                    
        except Exception as e:
            print(f"Error loading config: {e}")
            # Continue with default config
    else:
        # Save default config
        save_config()
        
    # Create required directories
    os.makedirs(os.path.dirname(CONFIG["database"]["path"]), exist_ok=True)
    os.makedirs(CONFIG["media"]["cache_dir"], exist_ok=True)

def save_config():
    """Save current configuration to file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(CONFIG, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

# Load configuration at module import
load_config()
