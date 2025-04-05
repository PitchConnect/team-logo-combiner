"""
Error handling module for the Team Logo Combiner service.
Provides centralized error handling for the Flask application.
"""

from flask import jsonify
import requests
from PIL import Image, UnidentifiedImageError

# Import logging configuration if available
try:
    import logging_config
    logger = logging_config.get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base class for API errors."""
    def __init__(self, message, status_code=500, details=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self):
        """Convert error to dictionary for JSON response."""
        error_dict = {
            "error": self.message
        }
        if self.details:
            error_dict["details"] = self.details
        return error_dict

class ValidationError(APIError):
    """Error raised when request validation fails."""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=400, details=details)

class ResourceNotFoundError(APIError):
    """Error raised when a requested resource is not found."""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=404, details=details)

class ProcessingError(APIError):
    """Error raised when image processing fails."""
    def __init__(self, message, details=None):
        super().__init__(message, status_code=500, details=details)

def handle_api_error(error):
    """Handle APIError exceptions."""
    logger.error(f"{error.__class__.__name__}: {error.message}",
                 extra={"details": error.details})
    return jsonify(error.to_dict()), error.status_code

def handle_validation_error(error):
    """Handle request validation errors."""
    return handle_api_error(ValidationError(str(error)))

def handle_http_error(error):
    """Handle HTTP errors from requests library."""
    logger.error(f"HTTP Error: {error}")
    return jsonify({
        "error": "Failed to fetch team logo",
        "details": {
            "status_code": error.response.status_code if hasattr(error, 'response') else None,
            "url": error.request.url if hasattr(error, 'request') else None
        }
    }), 502  # Bad Gateway

def handle_connection_error(error):
    """Handle connection errors from requests library."""
    logger.error(f"Connection Error: {error}")
    return jsonify({
        "error": "Network error while fetching team logo",
        "details": {
            "url": error.request.url if hasattr(error, 'request') else None
        }
    }), 502  # Bad Gateway

def handle_timeout_error(error):
    """Handle timeout errors from requests library."""
    logger.error(f"Timeout Error: {error}")
    return jsonify({
        "error": "Timeout while fetching team logo",
        "details": {
            "url": error.request.url if hasattr(error, 'request') else None
        }
    }), 504  # Gateway Timeout

def handle_image_error(error):
    """Handle PIL image processing errors."""
    logger.error(f"Image Processing Error: {error}")
    return jsonify({
        "error": "Failed to process image",
        "details": {
            "message": str(error)
        }
    }), 500

def handle_generic_error(error):
    """Handle any unhandled exceptions."""
    logger.error(f"Unhandled Exception: {error}", exc_info=True)
    return jsonify({
        "error": "Internal server error",
        "details": {
            "type": error.__class__.__name__,
            "message": str(error)
        }
    }), 500

def register_error_handlers(app):
    """Register error handlers with Flask app."""
    app.register_error_handler(APIError, handle_api_error)
    app.register_error_handler(ValidationError, handle_api_error)
    app.register_error_handler(ResourceNotFoundError, handle_api_error)
    app.register_error_handler(ProcessingError, handle_api_error)
    app.register_error_handler(requests.exceptions.HTTPError, handle_http_error)
    app.register_error_handler(requests.exceptions.ConnectionError, handle_connection_error)
    app.register_error_handler(requests.exceptions.Timeout, handle_timeout_error)
    app.register_error_handler(UnidentifiedImageError, handle_image_error)
    app.register_error_handler(Exception, handle_generic_error)

    logger.info("Registered error handlers with Flask app")
    return app
