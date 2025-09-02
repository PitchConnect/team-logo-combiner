"""
Enhanced logging configuration for Team Logo Combiner service.

This module provides enterprise-grade structured logging following the v2.1.0 standard
established in the match-list-processor service. It includes service context, component
separation, location information, and comprehensive error handling for image processing.
"""

import logging
import logging.handlers
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class TeamLogoCombinerFormatter(logging.Formatter):
    """Enhanced formatter for Team Logo Combiner service with structured output."""
    
    def __init__(self, enable_structured: bool = True):
        self.enable_structured = enable_structured
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with enhanced structure and context."""
        # Generate timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")
        
        # Service context
        service_name = "team-logo-combiner"
        
        # Component context (from logger adapter or module name)
        component = getattr(record, 'component', None)
        if not component:
            # Extract component from logger name
            logger_parts = record.name.split('.')
            if len(logger_parts) > 1:
                component = logger_parts[-1]
            else:
                component = 'app'
        
        # Location information
        location = f"{record.filename}:{record.funcName}:{record.lineno}"
        
        # Filter sensitive information
        message = self._filter_sensitive_data(record.getMessage())
        
        if self.enable_structured:
            # Structured format: timestamp - service - component - level - location - message
            return f"{timestamp} - {service_name} - {component} - {record.levelname} - {location} - {message}"
        else:
            # Simple format for console in development
            return f"[{record.levelname}] {component}:{record.funcName}:{record.lineno} - {message}"
    
    def _filter_sensitive_data(self, message: str) -> str:
        """Filter sensitive information from log messages."""
        patterns = [
            # API keys and tokens
            (r'(api[_-]?key|token|secret|password|pwd)[\s=:]+[^\s&]+', r'\1=[FILTERED]'),
            
            # URLs with sensitive parameters
            (r'(\?|&)(key|token|secret|password)=[^&\s]+', r'\1\2=[FILTERED]'),
            
            # Image processing URLs that might contain sensitive parameters
            (r'(\?|&)(key|token|secret)=[^&\s]+', r'\1\2=[FILTERED]'),
        ]
        
        filtered_message = message
        for pattern, replacement in patterns:
            filtered_message = re.sub(pattern, replacement, filtered_message, flags=re.IGNORECASE)
        
        return filtered_message


def get_logger(name: str, component: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger for the Team Logo Combiner service.
    
    Args:
        name: Logger name (typically __name__)
        component: Optional component name for context
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Add component context if provided
    if component:
        logger = logging.LoggerAdapter(logger, {'component': component})
    
    return logger


def configure_logging(
    log_level: str = 'INFO',
    enable_console: bool = True,
    enable_file: bool = True,
    enable_structured: bool = True,
    log_dir: str = 'logs',
    log_file: str = 'team-logo-combiner.log'
) -> None:
    """
    Configure enhanced logging for Team Logo Combiner service.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_console: Enable console logging
        enable_file: Enable file logging with rotation
        enable_structured: Enable structured logging format
        log_dir: Directory for log files
        log_file: Log file name
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set root logger level
    root_logger.setLevel(numeric_level)
    
    # Create formatter
    formatter = TeamLogoCombinerFormatter(enable_structured=enable_structured)
    
    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Create log directory if it doesn't exist
    if enable_file:
        os.makedirs(log_dir, exist_ok=True)
    
    # File handler with rotation
    if enable_file:
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, log_file),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Reduce verbosity of third-party libraries
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    # Log configuration success
    logger = get_logger(__name__, 'logging_config')
    logger.info(f"Logging configured: level={log_level}, console={enable_console}, "
                f"file={enable_file}, structured={enable_structured}")


def log_error_context(
    logger: logging.Logger,
    error: Exception,
    operation: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log error with comprehensive context information.
    
    Args:
        logger: Logger instance
        error: Exception that occurred
        operation: Operation being performed when error occurred
        context: Additional context information
    """
    context = context or {}
    
    # Filter sensitive information from context
    filtered_context = {}
    for key, value in context.items():
        if any(sensitive in key.lower() for sensitive in ['url', 'path', 'token', 'key', 'secret']):
            if isinstance(value, str):
                # Keep only filename for paths/URLs
                filtered_context[key] = os.path.basename(value) if value else None
            else:
                filtered_context[key] = '[FILTERED]'
        else:
            filtered_context[key] = value
    
    logger.error(
        f"Error in {operation}: {error.__class__.__name__}: {str(error)}",
        extra={
            'operation': operation,
            'error_type': error.__class__.__name__,
            'context': filtered_context
        },
        exc_info=True
    )


def log_image_processing_metrics(
    logger: logging.Logger,
    operation: str,
    processing_time: float,
    image_info: Dict[str, Any],
    success: bool = True
) -> None:
    """
    Log image processing metrics and performance information.
    
    Args:
        logger: Logger instance
        operation: Image processing operation name
        processing_time: Time taken for processing in seconds
        image_info: Information about processed images
        success: Whether the operation was successful
    """
    status = "success" if success else "failed"
    
    # Filter sensitive information from image_info
    filtered_info = {}
    for key, value in image_info.items():
        if 'url' in key.lower() or 'path' in key.lower():
            # Keep only filename for paths/URLs
            if isinstance(value, str):
                filtered_info[key] = os.path.basename(value) if value else None
            else:
                filtered_info[key] = '[FILTERED]'
        else:
            filtered_info[key] = value
    
    logger.info(
        f"Image processing {status}: {operation} completed in {processing_time:.3f}s",
        extra={
            'operation': operation,
            'processing_time': processing_time,
            'image_info': filtered_info,
            'success': success
        }
    )
