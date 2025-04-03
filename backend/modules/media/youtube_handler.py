"""
youtube_handler.py - YouTube content downloading and processing for the NFC music player.

This module handles downloading audio from YouTube videos using yt-dlp.
"""

import os
import re
import uuid
from typing import Callable, Dict, Optional

import yt_dlp

from backend.utils.logger import LoggerMixin
from backend.utils.file_utils import ensure_dir, safe_filename
from .exceptions import InvalidURLError, YouTubeInfoError, YouTubeDownloadError


class YouTubeDownloader(LoggerMixin):
    """
    Handles downloading content from YouTube using yt-dlp.
    """

    def __init__(self, output_dir: str, yt_dlp_options: Optional[Dict] = None):
        """
        Initialize YouTube downloader.

        Args:
            output_dir (str): Directory to save downloaded files
            yt_dlp_options (dict, optional): Options for yt-dlp
        """
        self.setup_logger()
        self.output_dir = ensure_dir(output_dir)
        
        # Default options for yt-dlp
        self.default_options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'outtmpl': os.path.join(self.output_dir, '%(id)s.%(ext)s')
        }
        
        # Merge with provided options if any
        if yt_dlp_options:
            self.default_options.update(yt_dlp_options)
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is a valid YouTube URL.

        Args:
            url (str): URL to validate

        Returns:
            bool: True if valid YouTube URL
        """
        # YouTube URL patterns
        patterns = [
            r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',     # Regular YouTube URL
            r'^https?://youtu\.be/[\w-]+',                        # Short YouTube URL
            r'^https?://(www\.)?youtube\.com/shorts/[\w-]+',      # YouTube Shorts
            r'^https?://(www\.)?youtube\.com/playlist\?list=[\w-]+',  # Playlist
            r'^https?://(www\.)?youtube\.com/embed/[\w-]+'        # Embedded YouTube
        ]
        
        # Check if URL matches any pattern
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        
        return False
    
    def get_video_info(self, url: str) -> Dict:
        """
        Get information about a YouTube video without downloading.

        Args:
            url (str): YouTube URL

        Returns:
            dict: Video information (title, duration, thumbnail, etc.)

        Raises:
            InvalidURLError: If URL is not a valid YouTube URL
            YouTubeInfoError: If info cannot be retrieved
        """
        if not self.validate_url(url):
            raise InvalidURLError(f"Invalid YouTube URL: {url}")
        
        # Set options for info extraction
        ydl_opts = {
            'format': 'bestaudio/best',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Check if info was retrieved
                if not info:
                    raise YouTubeInfoError(f"Failed to retrieve info for URL: {url}")
                
                # Return relevant info
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'thumbnail': info.get('thumbnail'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'description': info.get('description'),
                    'url': url,
                    'ext': info.get('ext', 'mp3'),
                }
        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"Failed to get video info: {e}")
            raise YouTubeInfoError(f"Failed to retrieve info: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error getting video info: {e}")
            raise YouTubeInfoError(f"Unexpected error: {str(e)}")
    
    def download(self, url: str, custom_filename: Optional[str] = None) -> str:
        """
        Download audio from YouTube video.

        Args:
            url (str): YouTube URL
            custom_filename (str, optional): Custom filename for the downloaded file

        Returns:
            str: Path to downloaded file

        Raises:
            InvalidURLError: If URL is not a valid YouTube URL
            YouTubeDownloadError: If download fails
        """
        if not self.validate_url(url):
            raise InvalidURLError(f"Invalid YouTube URL: {url}")
        
        # Get a unique filename if not provided
        if custom_filename:
            safe_name = safe_filename(custom_filename)
        else:
            try:
                # Get video title for filename
                info = self.get_video_info(url)
                video_title = info.get('title', str(uuid.uuid4()))
                safe_name = safe_filename(video_title)
            except Exception:
                # Use a random UUID if title can't be retrieved
                safe_name = str(uuid.uuid4())
        
        # Create output options with custom filename
        ydl_opts = self.default_options.copy()
        ydl_opts['outtmpl'] = os.path.join(self.output_dir, f"{safe_name}.%(ext)s")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info(f"Downloading audio from: {url}")
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    raise YouTubeDownloadError(f"Download failed for URL: {url}")
                
                # Get the path of the downloaded file
                # After extraction, the extension will be the one from postprocessor
                ext = 'mp3'  # Use the default extension from postprocessor
                if 'postprocessors' in ydl_opts:
                    for pp in ydl_opts['postprocessors']:
                        if pp.get('key') == 'FFmpegExtractAudio':
                            ext = pp.get('preferredcodec', 'mp3')
                
                downloaded_path = os.path.join(self.output_dir, f"{safe_name}.{ext}")
                
                # Verify file exists
                if not os.path.exists(downloaded_path):
                    # Try to find by video ID if the custom filename approach failed
                    if 'id' in info:
                        alt_path = os.path.join(self.output_dir, f"{info['id']}.{ext}")
                        if os.path.exists(alt_path):
                            downloaded_path = alt_path
                        else:
                            raise YouTubeDownloadError(f"Downloaded file not found at {downloaded_path}")
                    else:
                        raise YouTubeDownloadError(f"Downloaded file not found at {downloaded_path}")
                
                self.logger.info(f"Successfully downloaded to: {downloaded_path}")
                return downloaded_path
                
        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"Download error: {e}")
            raise YouTubeDownloadError(f"Download failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}")
            raise YouTubeDownloadError(f"Unexpected error: {str(e)}")
    
    def download_with_progress(self, url: str, progress_callback: Optional[Callable] = None) -> str:
        """
        Download with progress reporting via callback.

        Args:
            url (str): YouTube URL
            progress_callback (callable, optional): Function to call with progress updates

        Returns:
            str: Path to downloaded file
        """
        if not self.validate_url(url):
            raise InvalidURLError(f"Invalid YouTube URL: {url}")
        
        # Get a unique filename
        try:
            # Get video title for filename
            info = self.get_video_info(url)
            video_title = info.get('title', str(uuid.uuid4()))
            safe_name = safe_filename(video_title)
        except Exception:
            # Use a random UUID if title can't be retrieved
            safe_name = str(uuid.uuid4())
        
        # Create output options
        ydl_opts = self.default_options.copy()
        ydl_opts['outtmpl'] = os.path.join(self.output_dir, f"{safe_name}.%(ext)s")
        
        # Add progress hook if callback provided
        if progress_callback:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes'] > 0:
                        percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                        progress_callback(percent)
                    elif 'total_bytes_estimate' in d and d['total_bytes_estimate'] > 0:
                        percent = d['downloaded_bytes'] / d['total_bytes_estimate'] * 100
                        progress_callback(percent)
                elif d['status'] == 'finished':
                    progress_callback(100)
            
            ydl_opts['progress_hooks'] = [progress_hook]
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.logger.info(f"Downloading audio from: {url} with progress reporting")
                info = ydl.extract_info(url, download=True)
                
                if not info:
                    raise YouTubeDownloadError(f"Download failed for URL: {url}")
                
                # Get the path of the downloaded file
                ext = 'mp3'  # Use the default extension from postprocessor
                if 'postprocessors' in ydl_opts:
                    for pp in ydl_opts['postprocessors']:
                        if pp.get('key') == 'FFmpegExtractAudio':
                            ext = pp.get('preferredcodec', 'mp3')
                
                downloaded_path = os.path.join(self.output_dir, f"{safe_name}.{ext}")
                
                # Verify file exists
                if not os.path.exists(downloaded_path):
                    # Try to find by video ID if the custom filename approach failed
                    if 'id' in info:
                        alt_path = os.path.join(self.output_dir, f"{info['id']}.{ext}")
                        if os.path.exists(alt_path):
                            downloaded_path = alt_path
                        else:
                            raise YouTubeDownloadError(f"Downloaded file not found at {downloaded_path}")
                    else:
                        raise YouTubeDownloadError(f"Downloaded file not found at {downloaded_path}")
                
                self.logger.info(f"Successfully downloaded to: {downloaded_path}")
                return downloaded_path
                
        except yt_dlp.utils.DownloadError as e:
            self.logger.error(f"Download error: {e}")
            raise YouTubeDownloadError(f"Download failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}")
            raise YouTubeDownloadError(f"Unexpected error: {str(e)}")
