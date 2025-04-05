from flask import Flask, request, send_file, jsonify
import team_logo_combiner
from io import BytesIO
import logging
import os
import time

app = Flask(__name__)

# --- Logging Setup for Flask App ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
app_logger = logging.getLogger(__name__) # Get logger for this Flask app

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
    try:
        data = request.get_json()
        if not data or 'team1_id' not in data or 'team2_id' not in data:
            app_logger.warning("Bad request: Missing team IDs in JSON body.")
            return jsonify({"error": "Missing team IDs (team1_id, team2_id) in request body"}), 400

        team1_id = str(data['team1_id']) # Ensure IDs are strings
        team2_id = str(data['team2_id'])

        logo_url1 = f"{team_logo_combiner.BASE_LOGO_URL}{team1_id}.png"
        logo_url2 = f"{team_logo_combiner.BASE_LOGO_URL}{team2_id}.png"

        app_logger.info(f"Creating avatar for team IDs: {team1_id}, {team2_id}")

        combined_image = team_logo_combiner.merge_images_from_urls(
            logo_url1, logo_url2, background_image_path=DEFAULT_BACKGROUND_PATH
        )

        if combined_image:
            app_logger.info("Successfully generated combined image.")
            img_io = BytesIO()
            combined_image.save(img_io, 'PNG')
            img_io.seek(0)
            return send_file(img_io, mimetype='image/png')
        else:
            app_logger.error("Failed to generate combined image in team_logo_combiner.")
            return jsonify({"error": "Failed to generate combined avatar image"}), 500

    except Exception as e:
        app_logger.error(f"Internal server error: {e}", exc_info=True) # Log full exception
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
    logging.info("After app.run() - Did app.run() return unexpectedly?") # Add this line
