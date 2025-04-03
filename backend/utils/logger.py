"""
logger.py - Logging utilities for the NFC music player application.

This module provides consistent logging functionality across all modules of the application.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with consistent formatting.

    Args:
        name (str): Logger name, typically the module name
        log_file (str, optional): Path to log file, if None logs to console only
        level (int, optional): Logging level

    Returns:
        Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Add file handler if log_file is provided
    if log_file:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Create rotating file handler (10 MB per file, max 5 files)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name):
    """
    Get a logger instance by name. If the logger doesn't exist, creates a basic one.

    Args:
        name (str): Logger name

    Returns:
        Logger: Logger instance
    """
    logger = logging.getLogger(name)
    
    # If the logger has no handlers, set up a basic one
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
    return logger


def set_global_log_level(level):
    """
    Set the log level for all loggers.

    Args:
        level (int): Logging level (e.g., logging.INFO)
    """
    for logger_name in logging.root.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
    
    # Also set the root logger
    logging.getLogger().setLevel(level)


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.

    Usage:
        class MyClass(LoggerMixin):
            def __init__(self):
                self.setup_logger()

            def some_method(self):
                self.logger.info("Some message")
    """
    
    def setup_logger(self, name=None):
        """
        Set up logger for this instance.

        Args:
            name (str, optional): Logger name, defaults to class name
        """
        if not name:
            name = self.__class__.__name__
            
        self.logger = get_logger(name)
