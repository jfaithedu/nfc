#!/usr/bin/env python3
"""
NFC-Based Toddler-Friendly Music Player - Main Application

This is the entry point for the NFC-based music player application. It initializes
all necessary components and manages the main application loop for NFC tag detection
and media playback.
"""

import time
import logging
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
    
    # Initialize media manager
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
        while True:
            # Poll for NFC tag
            tag_uid = nfc_controller.poll_for_tag()
            
            if tag_uid:
                logger.info(f"Tag detected: {tag_uid}")
                
                # Look up tag in database
                media_info = db_manager.get_media_for_tag(tag_uid)
                
                if media_info:
                    # Stop any currently playing media
                    audio_controller.stop()
                    
                    # Prepare and play the media
                    media_path = media_manager.prepare_media(media_info)
                    audio_controller.play(media_path)
                else:
                    logger.warning(f"Unknown tag: {tag_uid}")
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
    
    # Shutdown media manager
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
