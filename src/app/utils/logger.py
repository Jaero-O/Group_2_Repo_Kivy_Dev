"""Centralized logging configuration for Mangofy application.

Provides structured logging with file rotation and console output.
Replaces scattered print() statements throughout the codebase.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name='mangofy', level=logging.INFO):
    """Configure and return application logger.
    
    Args:
        name: Logger name (default: 'mangofy')
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(levelname)s] [%(asctime)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(levelname)s] %(message)s'
    )
    
    # Console handler (for development/debugging)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (for production logs)
    try:
        # Use roaming app data directory for logs
        if os.name == 'nt':  # Windows
            log_dir = Path(os.environ.get('APPDATA', '')) / 'mangofy' / 'logs'
        else:  # Linux/Mac
            log_dir = Path.home() / '.local' / 'share' / 'mangofy' / 'logs'
        
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / 'app.log'
        
        # Rotate logs: 5MB max, keep 3 backups
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Logging initialized. Log file: {log_file}")
    except Exception as e:
        logger.warning(f"Could not initialize file logging: {e}")
    
    return logger


# Global logger instance for easy import
logger = setup_logger()


def get_logger(module_name):
    """Get a child logger for a specific module.
    
    Args:
        module_name: Name of the module (usually __name__)
    
    Returns:
        Child logger instance
    """
    return logging.getLogger(f'mangofy.{module_name}')
