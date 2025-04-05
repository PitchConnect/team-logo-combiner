from PIL import Image, UnidentifiedImageError
import requests
from io import BytesIO
import logging
import pathlib
import os

# Import error handler if running as part of the Flask app
try:
    from error_handler import ValidationError, ResourceNotFoundError, ProcessingError
    HAS_ERROR_HANDLER = True
except ImportError:
    HAS_ERROR_HANDLER = False

# --- Constants and Paths ---
BASE_LOGO_URL = "https://staticcdn.svenskfotboll.se/img/teams/"
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
ASSETS_DIR_NAME = "assets"
DEFAULT_BG_FILENAME = "grass_turf.jpg"
DEFAULT_BG_PATH = SCRIPT_DIR / ASSETS_DIR_NAME / DEFAULT_BG_FILENAME

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def crop_transparent_border(image):
    """Automatically crops transparent borders from an image."""
    if image.mode != 'RGBA':
        return image
    bbox = image.getbbox()
    if bbox:
        cropped_image = image.crop(bbox)
        return cropped_image
    else:
        logging.warning("Attempted to crop a fully transparent image. Returning original.")
        return image

def merge_images_from_urls(url1, url2, background_image_path=None):
    """
    Merges two images from URLs, crops borders, resizes, and combines into a square canvas.
    Returns a PIL Image object.

    Raises:
        requests.exceptions.HTTPError: If the logo URLs return non-200 status codes
        requests.exceptions.ConnectionError: If there's a network error
        UnidentifiedImageError: If the image data cannot be processed
        ProcessingError: If image processing fails
        ResourceNotFoundError: If resources like background images are not found
    """
    try:
        # Validate URLs
        if not url1 or not isinstance(url1, str):
            error_msg = "Invalid URL for logo 1"
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ValidationError(error_msg, {"url": url1})
            return None

        if not url2 or not isinstance(url2, str):
            error_msg = "Invalid URL for logo 2"
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ValidationError(error_msg, {"url": url2})
            return None

        # Fetch and process first logo
        logging.info(f"Fetching logo 1 from: {url1}")
        try:
            response1 = requests.get(url1, stream=True, timeout=10)
            response1.raise_for_status()
            image1 = Image.open(BytesIO(response1.content)).convert("RGBA")
        except requests.exceptions.HTTPError as e:
            error_msg = f"Failed to fetch logo 1: HTTP error {e.response.status_code}"
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ResourceNotFoundError(error_msg, {"url": url1, "status_code": e.response.status_code})
            return None
        except (requests.exceptions.RequestException, UnidentifiedImageError) as e:
            error_msg = f"Error processing logo 1: {str(e)}"
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url1})
            return None

        logging.info("Cropping transparent border for logo 1")
        image1_cropped = crop_transparent_border(image1)
        if not image1_cropped or image1_cropped.size == (0, 0):
            error_msg = f"Logo 1 from {url1} seems to be fully transparent or invalid after cropping."
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url1})
            return None

        # Fetch and process second logo
        logging.info(f"Fetching logo 2 from: {url2}")
        try:
            response2 = requests.get(url2, stream=True, timeout=10)
            response2.raise_for_status()
            image2 = Image.open(BytesIO(response2.content)).convert("RGBA")
        except requests.exceptions.HTTPError as e:
            error_msg = f"Failed to fetch logo 2: HTTP error {e.response.status_code}"
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ResourceNotFoundError(error_msg, {"url": url2, "status_code": e.response.status_code})
            return None
        except (requests.exceptions.RequestException, UnidentifiedImageError) as e:
            error_msg = f"Error processing logo 2: {str(e)}"
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url2})
            return None

        logging.info("Cropping transparent border for logo 2")
        image2_cropped = crop_transparent_border(image2)
        if not image2_cropped or image2_cropped.size == (0, 0):
            error_msg = f"Logo 2 from {url2} seems to be fully transparent or invalid after cropping."
            logging.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url2})
            return None

        width1, height1 = image1_cropped.size
        width2, height2 = image2_cropped.size

        if height1 <= 0 or height2 <= 0:
            logging.error("One or both logos have zero or negative height after cropping. Cannot proceed.")
            return None
        target_height = min(height1, height2)

        if height1 > target_height:
            logging.info(f"Resizing logo 1 (height {height1}) to target height ({target_height})")
            ratio = target_height / float(height1)
            new_width1 = int(width1 * ratio)
            if new_width1 > 0 and target_height > 0:
                 image1_cropped = image1_cropped.resize((new_width1, target_height), Image.Resampling.LANCZOS)
                 width1, height1 = image1_cropped.size
            else:
                 logging.warning("Skipping resize for logo 1 due to zero dimension calculation.")
        elif height2 > target_height:
            logging.info(f"Resizing logo 2 (height {height2}) to target height ({target_height})")
            ratio = target_height / float(height2)
            new_width2 = int(width2 * ratio)
            if new_width2 > 0 and target_height > 0:
                 image2_cropped = image2_cropped.resize((new_width2, target_height), Image.Resampling.LANCZOS)
                 width2, height2 = image2_cropped.size
            else:
                 logging.warning("Skipping resize for logo 2 due to zero dimension calculation.")

        combined_width = width1 + width2
        combined_height = target_height

        if combined_width <= 0 or combined_height <= 0:
            logging.error("Cannot create image with zero width or height after processing logos.")
            return None

        padding_horizontal = int(combined_width * 0.10)
        padding_vertical = int(combined_height * 0.10)
        canvas_size = max(1, combined_width + 2 * padding_horizontal, combined_height + 2 * padding_vertical)

        new_image = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))

        bg_path_to_use = background_image_path if background_image_path else DEFAULT_BG_PATH

        try:
            logging.info(f"Loading background image from: {bg_path_to_use}")
            if not os.path.exists(bg_path_to_use):
                error_msg = f"Background image not found at '{bg_path_to_use}'"
                logging.warning(f"{error_msg}. Using transparent background.")
                if HAS_ERROR_HANDLER:
                    # Non-fatal error, just log a warning
                    logging.warning(error_msg)
            else:
                try:
                    background = Image.open(bg_path_to_use).convert('RGBA')
                    bg_width, bg_height = background.size
                    if bg_width <= 0 or bg_height <= 0:
                        logging.warning(f"Background image '{bg_path_to_use}' has zero dimension. Skipping background.")
                    else:
                        min_bg_dimension = min(bg_width, bg_height)
                        left = (bg_width - min_bg_dimension) // 2
                        top = (bg_height - min_bg_dimension) // 2
                        right = left + min_bg_dimension
                        bottom = top + min_bg_dimension
                        cropped_background = background.crop((left, top, right, bottom))
                        resized_background = cropped_background.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
                        new_image.paste(resized_background, (0, 0))
                        logging.info(f"Applied background image: {bg_path_to_use}")
                except UnidentifiedImageError as e:
                    error_msg = f"Invalid background image format at '{bg_path_to_use}': {e}"
                    logging.warning(f"{error_msg}. Using transparent background.")
                    if HAS_ERROR_HANDLER:
                        # Non-fatal error, just log a warning
                        logging.warning(error_msg)
                except Exception as e:
                    error_msg = f"Error processing background image '{bg_path_to_use}': {e}"
                    logging.warning(f"{error_msg}. Using transparent background.")
                    if HAS_ERROR_HANDLER:
                        # Non-fatal error, just log a warning
                        logging.warning(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error with background image '{bg_path_to_use}': {e}"
            logging.warning(f"{error_msg}. Using transparent background.")
            if HAS_ERROR_HANDLER:
                # Non-fatal error, just log a warning
                logging.warning(error_msg)

        x_offset1 = padding_horizontal
        y_offset1 = (canvas_size - height1) // 2
        x_offset2 = x_offset1 + width1
        y_offset2 = (canvas_size - height2) // 2

        mask1 = image1_cropped if image1_cropped.mode == 'RGBA' else None
        mask2 = image2_cropped if image2_cropped.mode == 'RGBA' else None

        new_image.paste(image1_cropped, (x_offset1, y_offset1), mask=mask1)
        new_image.paste(image2_cropped, (x_offset2, y_offset2), mask=mask2)

        return new_image # Return the PIL Image object

    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error fetching logo: {e}"
        logging.error(error_msg)
        if HAS_ERROR_HANDLER:
            raise ResourceNotFoundError(error_msg, {"url": e.request.url if hasattr(e, 'request') else "unknown"})
        return None
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error downloading image: {e}"
        logging.error(error_msg)
        if HAS_ERROR_HANDLER:
            raise ProcessingError(error_msg, {"url": e.request.url if hasattr(e, 'request') else "unknown"})
        return None
    except UnidentifiedImageError as e:
        error_msg = f"Invalid image format: {e}"
        logging.error(error_msg)
        if HAS_ERROR_HANDLER:
            raise ProcessingError(error_msg)
        return None
    except Exception as e:
        error_msg = f"An unexpected error occurred during image processing: {e}"
        logging.error(error_msg, exc_info=True)
        if HAS_ERROR_HANDLER:
            raise ProcessingError(error_msg)
        return None

if __name__ == "__main__":
    # Example usage (for testing the script directly)
    # You can still run this script directly to test the core logic
    team_id1 = "7557"  # Example team ID
    team_id2 = "9590"  # Example team ID
    logo_url1 = f"{BASE_LOGO_URL}{team_id1}.png"
    logo_url2 = f"{BASE_LOGO_URL}{team_id2}.png"
    output_path = "combined_logos_test.png" # Output path for direct script execution
    background_image_path = str(DEFAULT_BG_PATH) # Use default background

    logging.info(f"--- Starting Logo Merge (Direct Test) ---")
    logging.info(f"Team ID 1: {team_id1} ({logo_url1})")
    logging.info(f"Team ID 2: {team_id2} ({logo_url2})")
    logging.info(f"Output Path: {output_path}")
    logging.info(f"Background Image Path: {background_image_path}")

    combined_image = merge_images_from_urls(logo_url1, logo_url2, background_image_path)

    if combined_image:
        try:
            output_path_obj = pathlib.Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            combined_image.save(output_path)
            logging.info(f"Merged image saved to: {output_path}")
        except Exception as e:
            logging.error(f"Failed to save the test image: {e}")
    else:
        logging.error("Failed to generate combined image in direct test.")

    logging.info(f"--- Logo Merge Finished (Direct Test) ---")