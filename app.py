from flask import Flask, request, send_file, jsonify
import team_logo_combiner
from io import BytesIO
import os
import time
import error_handler
from error_handler import ValidationError, ProcessingError
import logging_config

# --- Logging Setup for Flask App ---
logging_config.configure_logging()
app_logger = logging_config.get_logger(__name__) # Get logger for this Flask app

# --- Initialize Flask App ---
app = Flask(__name__)

# Register error handlers
app = error_handler.register_error_handlers(app)

# --- Define Assets Path (within Docker image) ---
ASSETS_DIR = "/app/assets" # Assuming 'assets' folder will be in the root of the Docker image
DEFAULT_BACKGROUND_PATH = os.path.join(ASSETS_DIR, "grass_turf.jpg")

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Docker health checks and monitoring.
    Returns basic service status and uptime information.
    """
    app_logger.debug("Health check endpoint called")
    return jsonify({
        "status": "healthy",
        "service": "whatsapp-avatar-service",
        "timestamp": time.time()
    })

@app.route('/create_avatar', methods=['POST'])
def create_avatar():
    """Create a combined avatar image from two team logos."""
    # Validate request data
    data = request.get_json()
    if not data:
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
    team1_id = str(data['team1_id']).strip() # Ensure IDs are strings and trim whitespace
    team2_id = str(data['team2_id']).strip()

    if not team1_id:
        raise ValidationError("team1_id cannot be empty")
    if not team2_id:
        raise ValidationError("team2_id cannot be empty")

    # Construct logo URLs
    logo_url1 = f"{team_logo_combiner.BASE_LOGO_URL}{team1_id}.png"
    logo_url2 = f"{team_logo_combiner.BASE_LOGO_URL}{team2_id}.png"

    app_logger.info(f"Creating avatar for team IDs: {team1_id}, {team2_id}")

    # Process images
    combined_image = team_logo_combiner.merge_images_from_urls(
        logo_url1, logo_url2, background_image_path=DEFAULT_BACKGROUND_PATH
    )

    if not combined_image:
        app_logger.error("Failed to generate combined image in team_logo_combiner.")
        raise ProcessingError(
            "Failed to generate combined avatar image",
            details={
                "team1_id": team1_id,
                "team2_id": team2_id,
                "logo_url1": logo_url1,
                "logo_url2": logo_url2
            }
        )

    # Return the image
    app_logger.info("Successfully generated combined image.")
    img_io = BytesIO()
    combined_image.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
    logging.info("After app.run() - Did app.run() return unexpectedly?") # Add this line
