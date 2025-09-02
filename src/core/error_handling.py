"""
Enhanced error handling for Team Logo Combiner service.

This module provides comprehensive error handling with circuit breaker patterns,
retry logic, and detailed error context for image processing operations.
"""

import functools
import time
from typing import Any, Callable, Dict, Optional, Tuple, Union

from .logging_config import get_logger, log_error_context


# Custom exception classes for image processing
class ImageProcessingError(Exception):
    """Base exception for image processing errors."""
    pass


class ImageDownloadError(ImageProcessingError):
    """Exception raised when image download fails."""
    pass


class ImageValidationError(ImageProcessingError):
    """Exception raised when image validation fails."""
    pass


class ImageCombineError(ImageProcessingError):
    """Exception raised when image combination fails."""
    pass


class ImageSaveError(ImageProcessingError):
    """Exception raised when image saving fails."""
    pass


class ConfigurationError(ImageProcessingError):
    """Exception raised when configuration is invalid."""
    pass


class ImageProcessingCircuitBreaker:
    """Circuit breaker for image processing operations."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise ImageProcessingError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Handle successful operation."""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'


# Global circuit breaker instance - can be reset for testing
_circuit_breaker = ImageProcessingCircuitBreaker()


def reset_circuit_breaker():
    """Reset the circuit breaker state - useful for testing."""
    global _circuit_breaker
    _circuit_breaker = ImageProcessingCircuitBreaker()


def handle_image_processing_errors(operation_name: str, component: str = "image_processor"):
    """
    Decorator for handling image processing errors with enhanced logging.
    
    Args:
        operation_name: Name of the operation being performed
        component: Component name for logging context
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__, component)
            start_time = time.time()
            
            logger.info(f"Starting {operation_name}")
            
            try:
                # Execute with circuit breaker protection
                result = _circuit_breaker.call(func, *args, **kwargs)
                
                duration = time.time() - start_time
                logger.info(f"Successfully completed {operation_name} in {duration:.2f}s")
                
                return result
                
            except ImageProcessingError as e:
                duration = time.time() - start_time
                context = {
                    'operation': operation_name,
                    'duration': duration,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
                
                log_error_context(logger, e, operation_name, context)
                raise
                
            except Exception as e:
                duration = time.time() - start_time
                context = {
                    'operation': operation_name,
                    'duration': duration,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
                
                # Wrap unexpected errors in ImageProcessingError
                wrapped_error = ImageProcessingError(f"Unexpected error in {operation_name}: {str(e)}")
                log_error_context(logger, wrapped_error, operation_name, context)
                raise wrapped_error from e
        
        return wrapper
    return decorator


def handle_api_errors(operation_name: str, component: str = "api"):
    """
    Decorator for handling API errors with enhanced logging.
    
    Args:
        operation_name: Name of the API operation being performed
        component: Component name for logging context
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger(func.__module__, component)
            start_time = time.time()
            
            logger.info(f"Starting {operation_name}")
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"Successfully completed {operation_name} in {duration:.2f}s")
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                context = {
                    'operation': operation_name,
                    'duration': duration,
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                }
                
                log_error_context(logger, e, operation_name, context)
                raise
        
        return wrapper
    return decorator


def safe_image_operation(
    operation: Callable,
    *args,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    **kwargs
) -> Any:
    """
    Execute image operation with retry logic and error handling.
    
    Args:
        operation: Function to execute
        *args: Arguments for the operation
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        **kwargs: Keyword arguments for the operation
        
    Returns:
        Result of the operation
        
    Raises:
        ImageProcessingError: If operation fails after all retries
    """
    logger = get_logger(__name__, 'safe_operation')
    
    for attempt in range(max_retries + 1):
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                logger.error(f"Operation failed after {max_retries} retries: {str(e)}")
                raise ImageProcessingError(f"Operation failed after {max_retries} retries") from e
            
            logger.warning(f"Operation attempt {attempt + 1} failed, retrying in {retry_delay}s: {str(e)}")
            time.sleep(retry_delay)


def validate_image_parameters(
    width: Optional[int] = None,
    height: Optional[int] = None,
    format: Optional[str] = None,
    url1: Optional[str] = None,
    url2: Optional[str] = None
) -> None:
    """
    Validate image processing parameters.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        format: Image format (PNG, JPG, JPEG)
        url1: First image URL
        url2: Second image URL
        
    Raises:
        ImageValidationError: If parameters are invalid
    """
    if width is not None:
        if not isinstance(width, int) or width <= 0 or width > 10000:
            raise ImageValidationError(f"Invalid width: {width}. Must be between 1 and 10000 pixels.")
    
    if height is not None:
        if not isinstance(height, int) or height <= 0 or height > 10000:
            raise ImageValidationError(f"Invalid height: {height}. Must be between 1 and 10000 pixels.")
    
    if format is not None:
        valid_formats = ['PNG', 'JPG', 'JPEG']
        if format.upper() not in valid_formats:
            raise ImageValidationError(f"Invalid format: {format}. Must be one of {valid_formats}.")
    
    if url1 is not None:
        if not isinstance(url1, str) or not url1.strip():
            raise ImageValidationError("url1 must be a non-empty string.")
        if not (url1.startswith('http://') or url1.startswith('https://')):
            raise ImageValidationError("url1 must be a valid HTTP/HTTPS URL.")
    
    if url2 is not None:
        if not isinstance(url2, str) or not url2.strip():
            raise ImageValidationError("url2 must be a non-empty string.")
        if not (url2.startswith('http://') or url2.startswith('https://')):
            raise ImageValidationError("url2 must be a valid HTTP/HTTPS URL.")
