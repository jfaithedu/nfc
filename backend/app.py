#!/usr/bin/env python3
"""
NFC-Based Toddler-Friendly Music Player - Main Application

This is the entry point for the NFC-based music player application. It initializes
all necessary components and manages the main application loop for NFC tag detection
and media playback.
"""

import time
import logging
import sys
import os

# Add the parent directory to Python path to allow backend.* imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.nfc import nfc_controller
from modules.database import db_manager
from modules.media import media_manager
from modules.audio import audio_controller
from modules.api import api_server
from config import CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nfc_player.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def initialize_components():
    """Initialize all application components."""
    logger.info("Initializing NFC Music Player components...")
    
    # Initialize database
    db_manager.initialize()
    
    # Initialize NFC controller
    nfc_controller.initialize()
    
    # Initialize media manager if not already initialized
    if not media_manager.is_initialized():
        media_manager.initialize()
    
    # Initialize audio controller
    audio_controller.initialize()
    
    # Start API server in a separate thread
    api_server.start()
    
    logger.info("All components initialized successfully")

def main_loop():
    """Main application loop for NFC tag detection and playback."""
    logger.info("Entering main application loop")
    
    try:
        # Track previous tag to detect tag removal
        previous_tag_uid = None
        
        while True:
            # Poll for NFC tag
            poll_result = nfc_controller.poll_for_tag()
            
            # Initialize variables
            tag_uid = None
            ndef_info = None 
            media_info = None
            
            # Check if tag was detected
            if poll_result is not None:
                if isinstance(poll_result, tuple) and len(poll_result) == 2:
                    tag_uid, ndef_info = poll_result
                else:
                    # Handle case where only UID is returned (not a tuple)
                    tag_uid = poll_result
            
            # Tag removal detection
            if previous_tag_uid and not tag_uid:
                logger.info("Tag removed, stopping playback")
                audio_controller.stop()
                previous_tag_uid = None
            
            # Tag placement detection (new tag or different tag)
            elif tag_uid and tag_uid != previous_tag_uid:
                logger.info(f"New tag detected: {tag_uid}")
                
                # NDEF Handling - Check if ndef_info contains a valid URI
                if ndef_info and ndef_info.get('type') == 'uri':
                    url = ndef_info.get('uri')
                    # Validate if the URI is a YouTube or YouTube Music URL
                    if url and ('youtube.com' in url or 'youtu.be' in url or 'music.youtube.com' in url):
                        logger.info(f"Found valid YouTube URL in NDEF data: {url}")
                        # Add or get media by URL, possibly associating with this tag UID
                        media_info = db_manager.add_or_get_media_by_url(url, tag_uid)
                        logger.info(f"Media {'found' if media_info else 'could not be found/created'} for URL")
                
                # UID Handling (if no valid NDEF URL was found or processed)
                if media_info is None:
                    logger.info("No valid NDEF URL found, looking up by tag UID")
                    media_info = db_manager.get_media_for_tag(tag_uid)
                
                # Playback
                if media_info:
                    try:
                        # Stop any currently playing media
                        audio_controller.stop()
                        
                        # Check if media_info has a source_url
                        if not media_info.get('source_url') and not media_info.get('url'):
                            logger.warning(f"Tag {tag_uid} has a media entry but no source URL")
                            audio_controller.play_error_sound()
                        else:
                            # Prepare and play the media
                            media_path = media_manager.prepare_media(media_info)
                            audio_controller.play(media_path)
                            
                            # Save current tag UID
                            previous_tag_uid = tag_uid
                    except Exception as e:
                        logger.error(f"Error during media playback: {e}")
                        audio_controller.play_error_sound()
                else:
                    logger.warning(f"Unknown tag: UID={tag_uid}, NDEF={ndef_info}")
                    audio_controller.play_error_sound()
            
            # Small delay to prevent CPU overuse
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.exception(f"Unexpected error in main loop: {e}")
    finally:
        shutdown()

def shutdown():
    """Perform graceful shutdown of all components."""
    logger.info("Shutting down NFC Music Player...")
    
    # Stop API server
    api_server.stop()
    
    # Stop audio playback
    audio_controller.shutdown()
    
    # Shutdown media manager if initialized
    if hasattr(media_manager, 'is_initialized') and media_manager.is_initialized():
        media_manager.shutdown()
    
    # Shutdown NFC controller
    nfc_controller.shutdown()
    
    # Close database connections
    db_manager.shutdown()
    
    logger.info("Shutdown complete")

if __name__ == "__main__":
    try:
        initialize_components()
        main_loop()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        exit(1)
