"""
Core modules for Team Logo Combiner service.

This package contains the enhanced logging and error handling infrastructure
following the v2.1.0 standard, specifically designed for image processing operations.
"""

from .error_handling import (
    ConfigurationError,
    ImageCombineError,
    ImageDownloadError,
    ImageProcessingCircuitBreaker,
    ImageProcessingError,
    ImageSaveError,
    ImageValidationError,
    handle_api_errors,
    handle_image_processing_errors,
    reset_circuit_breaker,
    safe_image_operation,
    validate_image_parameters,
)
from .logging_config import (
    configure_logging,
    get_logger,
    log_error_context,
    log_image_processing_metrics,
)

__all__ = [
    # Error handling
    'ConfigurationError',
    'ImageCombineError',
    'ImageDownloadError',
    'ImageProcessingCircuitBreaker',
    'ImageProcessingError',
    'ImageSaveError',
    'ImageValidationError',
    'handle_api_errors',
    'handle_image_processing_errors',
    'reset_circuit_breaker',
    'safe_image_operation',
    'validate_image_parameters',
    # Logging
    'configure_logging',
    'get_logger',
    'log_error_context',
    'log_image_processing_metrics',
]
