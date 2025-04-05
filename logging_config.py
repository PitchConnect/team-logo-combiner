"""
Logging configuration for the Team Logo Combiner service.
Provides centralized logging configuration with different handlers and formatters.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

# Default log levels for different environments
LOG_LEVELS = {
    'development': logging.DEBUG,
    'production': logging.INFO,
    'testing': logging.DEBUG
}

# Get environment from environment variable or default to development
ENV = os.environ.get('FLASK_ENV', 'development').lower()

# Get log level from environment variable or use default based on environment
LOG_LEVEL = os.environ.get('LOG_LEVEL', None)
if LOG_LEVEL:
    # Convert string log level to logging constant
    numeric_level = getattr(logging, LOG_LEVEL.upper(), None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {LOG_LEVEL}", file=sys.stderr)
        numeric_level = LOG_LEVELS[ENV]
else:
    numeric_level = LOG_LEVELS[ENV]

# Log file configuration
LOG_DIR = Path('logs')
LOG_FILE = LOG_DIR / 'team_logo_combiner.log'
LOG_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_FILE_BACKUP_COUNT = 5

# Create logs directory if it doesn't exist
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Console formatter - colorized and concise for development
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""
    
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91m\033[1m', # Bold Red
        'RESET': '\033[0m'    # Reset
    }
    
    def format(self, record):
        log_message = super().format(record)
        level_name = record.levelname
        if level_name in self.COLORS:
            return f"{self.COLORS[level_name]}{log_message}{self.COLORS['RESET']}"
        return log_message

def configure_logging():
    """Configure logging for the application."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set the root logger level
    root_logger.setLevel(numeric_level)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    
    # Create file handler
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, 
        maxBytes=LOG_FILE_MAX_BYTES, 
        backupCount=LOG_FILE_BACKUP_COUNT
    )
    file_handler.setLevel(numeric_level)
    
    # Create formatters
    if ENV == 'development':
        # Colorized, concise format for console in development
        console_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        console_formatter = ColoredFormatter(console_format, datefmt='%H:%M:%S')
    else:
        # More detailed format for production console
        console_format = '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s'
        console_formatter = logging.Formatter(console_format)
    
    # Detailed format for file logs
    file_format = '%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s'
    file_formatter = logging.Formatter(file_format)
    
    # Set formatters
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Create a logger for this module
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured. Environment: {ENV}, Log level: {logging.getLevelName(numeric_level)}")
    
    return root_logger

def get_logger(name):
    """Get a logger with the given name."""
    return logging.getLogger(name)
