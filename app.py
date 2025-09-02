from flask import Flask, request, send_file, jsonify
import team_logo_combiner
from io import BytesIO
import os
import time

# Import enhanced logging and error handling
from src.core import (
    configure_logging,
    get_logger,
    handle_api_errors,
    ImageValidationError,
    ImageProcessingError,
    validate_image_parameters,
)

# Import legacy error handler for compatibility
import error_handler
from error_handler import ValidationError, ProcessingError

# Configure enhanced logging early
configure_logging(
    log_level=os.environ.get('LOG_LEVEL', 'INFO'),
    enable_console=os.environ.get('LOG_ENABLE_CONSOLE', 'true').lower() == 'true',
    enable_file=os.environ.get('LOG_ENABLE_FILE', 'true').lower() == 'true',
    enable_structured=os.environ.get('LOG_ENABLE_STRUCTURED', 'true').lower() == 'true',
    log_dir=os.environ.get('LOG_DIR', 'logs'),
    log_file=os.environ.get('LOG_FILE', 'team-logo-combiner.log')
)

# Get enhanced logger
app_logger = get_logger(__name__, 'app')

# --- Initialize Flask App ---
app = Flask(__name__)

# Register error handlers
app = error_handler.register_error_handlers(app)

# --- Define Assets Path (within Docker image) ---
ASSETS_DIR = "/app/assets"  # Assuming 'assets' folder will be in the root of the Docker image
DEFAULT_BACKGROUND_PATH = os.path.join(ASSETS_DIR, "grass_turf.jpg")


@app.route('/health', methods=['GET'])
@handle_api_errors("health_check", "app")
def health_check():
    """
    Health check endpoint for Docker health checks and monitoring.
    Returns basic service status and uptime information.
    """
    app_logger.info("Health check requested")
    return jsonify({
        "status": "healthy",
        "service": "team-logo-combiner",
        "version": "2.1.0",
        "timestamp": time.time(),
        "enhanced_logging": "v2.1.0"
    })


@app.route('/create_avatar', methods=['POST'])
@handle_api_errors("create_avatar", "app")
def create_avatar():
    """Create a combined avatar image from two team logos with enhanced logging."""
    # Validate request data
    data = request.get_json()
    if not data:
        app_logger.warning("Request missing JSON body")
        raise ValidationError("Missing JSON body in request")

    # Validate required fields
    missing_fields = []
    if 'team1_id' not in data:
        missing_fields.append('team1_id')
    if 'team2_id' not in data:
        missing_fields.append('team2_id')

    if missing_fields:
        app_logger.warning(f"Bad request: Missing fields in JSON body: {', '.join(missing_fields)}")
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )

    # Validate field values
    team1_id = str(data['team1_id']).strip()  # Ensure IDs are strings and trim whitespace
    team2_id = str(data['team2_id']).strip()

    if not team1_id:
        app_logger.warning("team1_id is empty after validation")
        raise ValidationError("team1_id cannot be empty")
    if not team2_id:
        app_logger.warning("team2_id is empty after validation")
        raise ValidationError("team2_id cannot be empty")

    # Construct logo URLs
    logo_url1 = f"{team_logo_combiner.BASE_LOGO_URL}{team1_id}.png"
    logo_url2 = f"{team_logo_combiner.BASE_LOGO_URL}{team2_id}.png"

    app_logger.info(f"Creating avatar for team IDs: {team1_id}, {team2_id}")
    app_logger.debug(f"Logo URLs: {os.path.basename(logo_url1)}, {os.path.basename(logo_url2)}")

    try:
        # Process images with enhanced error handling
        start_time = time.time()
        combined_image = team_logo_combiner.merge_images_from_urls(
            logo_url1, logo_url2, background_image_path=DEFAULT_BACKGROUND_PATH
        )
        processing_time = time.time() - start_time

        if not combined_image:
            app_logger.error("Failed to generate combined image in team_logo_combiner")
            raise ProcessingError(
                "Failed to generate combined avatar image",
                details={
                    "team1_id": team1_id,
                    "team2_id": team2_id,
                    "processing_time": processing_time
                }
            )

        # Return the image
        app_logger.info(f"Successfully generated combined image in {processing_time:.3f}s")
        img_io = BytesIO()
        combined_image.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        app_logger.error(f"Error processing avatar creation: {str(e)}")
        if isinstance(e, (ValidationError, ProcessingError)):
            raise
        else:
            raise ProcessingError(f"Unexpected error during image processing: {str(e)}")


if __name__ == '__main__':
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5002))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    app_logger.info(f"Starting Team Logo Combiner service on {host}:{port}")
    app_logger.info(f"Debug mode: {debug}")
    app_logger.info(f"Log level: {os.environ.get('LOG_LEVEL', 'INFO')}")
    app_logger.info("Enhanced logging v2.1.0 standard enabled")

    try:
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        app_logger.error(f"Failed to start application: {str(e)}")
        raise
