from flask import Flask, request, send_file, jsonify
import team_logo_combiner
from io import BytesIO
import os
import time
import base64

# Import enhanced logging and error handling
from src.core import (
    configure_logging,
    get_logger,
    handle_api_errors,
    ImageValidationError,
    ImageProcessingError,
    validate_image_parameters,
)

# Import Redis integration
from src.redis_integration import (
    AvatarRequestSubscriber,
    AvatarResultPublisher,
    get_redis_config,
)

# Use enhanced logging error classes instead of legacy ones
# ValidationError -> ImageValidationError
# ProcessingError -> ImageProcessingError

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

# --- Initialize Redis Integration ---
redis_config = get_redis_config()
publisher = AvatarResultPublisher()
subscriber = None  # Will be initialized in main

# Register enhanced logging error handlers
@app.errorhandler(ImageValidationError)
def handle_validation_errors(error):
    """Handle image validation errors with enhanced logging."""
    app_logger.error(f"Image validation error: {str(error)}")
    return jsonify({
        "error": str(error),
        "type": error.__class__.__name__
    }), 400

@app.errorhandler(ImageProcessingError)
def handle_processing_errors(error):
    """Handle image processing errors with enhanced logging."""
    app_logger.error(f"Image processing error: {str(error)}")
    return jsonify({
        "error": str(error),
        "type": error.__class__.__name__
    }), 500

@app.errorhandler(Exception)
def handle_generic_error(error):
    """Handle generic errors with enhanced logging."""
    app_logger.error(f"Unexpected error: {str(error)}")
    return jsonify({
        "error": "Internal server error",
        "type": error.__class__.__name__
    }), 500

# --- Define Assets Path (within Docker image) ---
ASSETS_DIR = "/app/assets"  # Assuming 'assets' folder will be in the root of the Docker image
DEFAULT_BACKGROUND_PATH = os.path.join(ASSETS_DIR, "grass_turf.jpg")


def handle_avatar_request_from_redis(request_id: str, payload: dict):
    """
    Handle avatar request from Redis pub/sub.

    Args:
        request_id: Unique request ID from Redis message
        payload: Request payload containing team IDs and metadata
    """
    start_time = time.time()

    try:
        team1_id = payload.get("team1_id")
        team2_id = payload.get("team2_id")

        app_logger.info(f"📨 Processing Redis avatar request {request_id} for teams {team1_id} vs {team2_id}")

        # Construct logo URLs
        logo_url1 = f"{team_logo_combiner.BASE_LOGO_URL}{team1_id}.png"
        logo_url2 = f"{team_logo_combiner.BASE_LOGO_URL}{team2_id}.png"

        # Process images
        combined_image = team_logo_combiner.merge_images_from_urls(
            logo_url1, logo_url2, background_image_path=DEFAULT_BACKGROUND_PATH
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        if combined_image:
            # Convert image to base64 for Redis publishing
            img_io = BytesIO()
            combined_image.save(img_io, 'PNG')
            img_io.seek(0)
            avatar_data = base64.b64encode(img_io.read()).decode('utf-8')

            # Publish success result
            result = publisher.publish_avatar_result(
                request_id=request_id,
                team1_id=team1_id,
                team2_id=team2_id,
                status="success",
                avatar_data=avatar_data,
                processing_time_ms=processing_time_ms,
                metadata={
                    "image_size": f"{combined_image.width}x{combined_image.height}",
                    "format": "PNG",
                    "background": "grass_turf.jpg",
                }
            )

            if result.success:
                app_logger.info(f"✅ Published avatar result for request {request_id} ({processing_time_ms}ms)")
            else:
                app_logger.error(f"❌ Failed to publish avatar result: {result.error}")
        else:
            # Publish error result
            publisher.publish_avatar_result(
                request_id=request_id,
                team1_id=team1_id,
                team2_id=team2_id,
                status="error",
                error={"type": "ImageProcessingError", "message": "Failed to create avatar"},
                processing_time_ms=processing_time_ms,
            )
            app_logger.error(f"❌ Failed to create avatar for request {request_id}")

    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        app_logger.error(f"❌ Error processing Redis request {request_id}: {str(e)}")

        # Publish error result
        publisher.publish_avatar_result(
            request_id=request_id,
            team1_id=payload.get("team1_id", "unknown"),
            team2_id=payload.get("team2_id", "unknown"),
            status="error",
            error={"type": type(e).__name__, "message": str(e)},
            processing_time_ms=processing_time_ms,
        )


@app.route('/health', methods=['GET'])
def health_check():
    """
    Optimized health check endpoint with minimal logging.
    Returns basic service status and uptime information.
    """
    start_time = time.time()

    response = {
        "status": "healthy",
        "service": "team-logo-combiner",
        "version": "2.2.0",
        "timestamp": time.time(),
        "enhanced_logging": "v2.1.0",
        "redis_integration": "v1.0.0",
        "redis_enabled": redis_config.enabled,
        "redis_connected": publisher.connection_manager.is_connected() if redis_config.enabled else False,
        "communication_mode": os.environ.get('COMMUNICATION_MODE', 'dual'),
    }

    # Add subscriber stats if available
    if subscriber and redis_config.enabled:
        response["subscriber_stats"] = subscriber.get_stats()

    # Add publisher stats if available
    if redis_config.enabled:
        response["publisher_stats"] = publisher.get_publishing_stats()

    duration = time.time() - start_time
    app_logger.info(f"✅ Health check OK ({duration:.3f}s)")

    return jsonify(response)


@app.route('/create_avatar', methods=['POST'])
@handle_api_errors("create_avatar", "app")
def create_avatar():
    """Create a combined avatar image from two team logos with enhanced logging."""
    # Validate request data
    data = request.get_json()
    if not data:
        app_logger.warning("Request missing JSON body")
        raise ImageValidationError("Missing JSON body in request")

    # Validate required fields
    missing_fields = []
    if 'team1_id' not in data:
        missing_fields.append('team1_id')
    if 'team2_id' not in data:
        missing_fields.append('team2_id')

    if missing_fields:
        app_logger.warning(f"Bad request: Missing fields in JSON body: {', '.join(missing_fields)}")
        raise ImageValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    # Validate field values
    team1_id = str(data['team1_id']).strip()  # Ensure IDs are strings and trim whitespace
    team2_id = str(data['team2_id']).strip()

    if not team1_id:
        app_logger.warning("team1_id is empty after validation")
        raise ImageValidationError("team1_id cannot be empty")
    if not team2_id:
        app_logger.warning("team2_id is empty after validation")
        raise ImageValidationError("team2_id cannot be empty")

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
            raise ImageProcessingError("Failed to generate combined avatar image")

        # Return the image
        app_logger.info(f"Successfully generated combined image in {processing_time:.3f}s")
        img_io = BytesIO()
        combined_image.save(img_io, 'PNG')
        img_io.seek(0)
        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        app_logger.error(f"Error processing avatar creation: {str(e)}")
        if isinstance(e, (ImageValidationError, ImageProcessingError)):
            raise
        else:
            raise ImageProcessingError(f"Unexpected error during image processing: {str(e)}")


if __name__ == '__main__':
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5002))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    communication_mode = os.environ.get('COMMUNICATION_MODE', 'dual')

    app_logger.info(f"Starting Team Logo Combiner service on {host}:{port}")
    app_logger.info(f"Debug mode: {debug}")
    app_logger.info(f"Log level: {os.environ.get('LOG_LEVEL', 'INFO')}")
    app_logger.info("Enhanced logging v2.1.0 standard enabled")
    app_logger.info(f"Communication mode: {communication_mode}")

    # Initialize Redis subscriber if enabled
    if communication_mode in ['dual', 'redis'] and redis_config.enabled:
        app_logger.info("🚀 Initializing Redis pub/sub integration...")
        subscriber = AvatarRequestSubscriber(handle_avatar_request_from_redis)
        subscriber.start()

        # Publish service startup status
        publisher.publish_service_status(
            status="started",
            details={
                "version": "2.2.0",
                "mode": communication_mode,
                "host": host,
                "port": port,
            }
        )
        app_logger.info("✅ Redis pub/sub integration started")
    else:
        app_logger.info("📡 Redis pub/sub disabled or not in redis/dual mode")

    # Start Flask app if in HTTP or dual mode
    if communication_mode in ['dual', 'http']:
        app_logger.info(f"🌐 Starting HTTP server on {host}:{port}")
        try:
            app.run(host=host, port=port, debug=debug)
        except Exception as e:
            app_logger.error(f"Failed to start application: {str(e)}")
            raise
        finally:
            # Stop subscriber on shutdown
            if subscriber:
                app_logger.info("🛑 Stopping Redis subscriber...")
                subscriber.stop()
                publisher.publish_service_status(status="stopped")
    elif communication_mode == 'redis':
        # Redis-only mode: keep the process running
        app_logger.info("📡 Running in Redis-only mode (no HTTP server)")
        try:
            import signal
            import sys

            def signal_handler(sig, frame):
                app_logger.info("🛑 Received shutdown signal")
                if subscriber:
                    subscriber.stop()
                    publisher.publish_service_status(status="stopped")
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Keep the process running
            app_logger.info("✅ Service running in Redis-only mode. Press Ctrl+C to stop.")
            signal.pause()
        except Exception as e:
            app_logger.error(f"Error in Redis-only mode: {str(e)}")
            if subscriber:
                subscriber.stop()
            raise
    else:
        app_logger.error(f"Invalid COMMUNICATION_MODE: {communication_mode}. Must be 'http', 'redis', or 'dual'")
        raise ValueError(f"Invalid COMMUNICATION_MODE: {communication_mode}")
