"""
metadata_processor.py - Process and store media metadata for the NFC music player.

This module handles metadata extraction, embedding, and thumbnail generation.
"""

import os
import re
import tempfile
import ffmpeg
import urllib.request
from typing import Dict, Tuple, Optional

from backend.utils.logger import get_logger
from backend.utils.file_utils import ensure_dir, safe_filename

# Setup logger
logger = get_logger(__name__)


def extract_metadata(file_path: str) -> Dict:
    """
    Extract metadata from an audio file.

    Args:
        file_path (str): Path to audio file

    Returns:
        dict: Metadata including title, artist, duration, etc.
    """
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return {}
    
    try:
        # Use ffmpeg to probe the file and extract metadata
        probe = ffmpeg.probe(file_path)
        
        # Extract format information
        format_info = probe.get('format', {})
        
        # Extract audio stream information
        audio_stream = next((stream for stream in probe.get('streams', []) 
                             if stream.get('codec_type') == 'audio'), None)
        
        # Extract tags
        format_tags = format_info.get('tags', {})
        stream_tags = audio_stream.get('tags', {}) if audio_stream else {}
        
        # Combine all tags, with stream tags taking precedence
        all_tags = {**format_tags, **stream_tags}
        
        # Normalize tag keys to lowercase
        normalized_tags = {k.lower(): v for k, v in all_tags.items()}
        
        # Create metadata dictionary
        metadata = {
            'duration': float(format_info.get('duration', 0)),
            'size_bytes': int(format_info.get('size', 0)),
            'format': format_info.get('format_name', ''),
            'bit_rate': int(format_info.get('bit_rate', 0)),
            'title': normalized_tags.get('title', os.path.splitext(os.path.basename(file_path))[0]),
            'artist': normalized_tags.get('artist', normalized_tags.get('album_artist', '')),
            'album': normalized_tags.get('album', ''),
            'year': normalized_tags.get('date', normalized_tags.get('year', '')),
            'genre': normalized_tags.get('genre', ''),
            'track': normalized_tags.get('track', ''),
            'comment': normalized_tags.get('comment', ''),
        }
        
        # Handle audio-specific properties if available
        if audio_stream:
            metadata.update({
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'codec': audio_stream.get('codec_name', ''),
            })
        
        return metadata
        
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error extracting metadata: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Error extracting metadata: {str(e)}")
        return {}


def embed_metadata(file_path: str, metadata: Dict) -> bool:
    """
    Embed metadata into an audio file.

    Args:
        file_path (str): Path to audio file
        metadata (dict): Metadata to embed

    Returns:
        bool: True if successful
    """
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return False
    
    try:
        # Create a temporary file for the output
        output_fd, output_path = tempfile.mkstemp(suffix=os.path.splitext(file_path)[1])
        os.close(output_fd)  # Close the file descriptor
        
        # Prepare metadata arguments
        metadata_args = {}
        for key, value in metadata.items():
            if value and isinstance(value, (str, int, float)):
                metadata_args[f"metadata:g:{key}"] = str(value)
        
        # Process the file with ffmpeg
        (
            ffmpeg
            .input(file_path)
            .output(output_path, **metadata_args, codec='copy')
            .overwrite_output()
            .run(quiet=True)
        )
        
        # Replace the original file with the new one
        os.replace(output_path, file_path)
        
        logger.info(f"Successfully embedded metadata into {file_path}")
        return True
        
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error embedding metadata: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
        # Cleanup temporary file if it exists
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
        return False
    except Exception as e:
        logger.error(f"Error embedding metadata: {str(e)}")
        # Cleanup temporary file if it exists
        if 'output_path' in locals() and os.path.exists(output_path):
            os.remove(output_path)
        return False


def generate_thumbnail(source: str, output_path: str, size: Tuple[int, int] = (300, 300)) -> str:
    """
    Generate thumbnail for media.

    Args:
        source (str): Source (file path or URL)
        output_path (str): Path to save thumbnail
        size (tuple, optional): Thumbnail dimensions

    Returns:
        str: Path to generated thumbnail
    """
    try:
        # Ensure output directory exists
        ensure_dir(os.path.dirname(output_path))
        
        # Check if source is a URL or a file path
        is_url = source.startswith(('http://', 'https://'))
        
        if is_url:
            # If it's a URL, download the image first
            temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(source)[1])
            os.close(temp_fd)
            
            try:
                urllib.request.urlretrieve(source, temp_path)
                source_path = temp_path
            except Exception as e:
                logger.error(f"Error downloading thumbnail from URL: {str(e)}")
                os.remove(temp_path)
                return ""
        else:
            # Local file
            source_path = source
            
        # Generate thumbnail using ffmpeg
        (
            ffmpeg
            .input(source_path)
            .filter('scale', size[0], size[1])
            .output(output_path)
            .overwrite_output()
            .run(quiet=True)
        )
        
        # Cleanup temp file if we downloaded from URL
        if is_url and os.path.exists(temp_path):
            os.remove(temp_path)
        
        logger.info(f"Generated thumbnail at {output_path}")
        return output_path
        
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error generating thumbnail: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
        return ""
    except Exception as e:
        logger.error(f"Error generating thumbnail: {str(e)}")
        return ""


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to be filesystem-safe.

    Args:
        filename (str): Input filename

    Returns:
        str: Sanitized filename
    """
    # Use the safe_filename utility from file_utils
    return safe_filename(filename)
