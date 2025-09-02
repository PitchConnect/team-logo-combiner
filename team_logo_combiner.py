from PIL import Image, UnidentifiedImageError
import requests
from io import BytesIO
import pathlib
import os
import time
import random

# Import enhanced logging and error handling
try:
    from src.core import (
        get_logger,
        handle_image_processing_errors,
        safe_image_operation,
        validate_image_parameters,
        ImageDownloadError,
        ImageValidationError,
        ImageCombineError,
        ImageProcessingError,
        log_image_processing_metrics,
    )
    HAS_ENHANCED_LOGGING = True
    logger = get_logger(__name__, 'image_processor')
except ImportError:
    HAS_ENHANCED_LOGGING = False
    # Fallback to legacy logging
    try:
        import logging_config
        logger = logging_config.get_logger(__name__)
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logger = logging.getLogger(__name__)

# Import legacy error handler for compatibility
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


def sanitize_image_data(image_data):
    """
    Validate and potentially fix image data that might cause processing errors.

    For PNG files, null bytes are actually part of the valid format structure,
    so we should NOT remove them. Instead, we validate the PNG structure and
    only sanitize if we detect actual corruption patterns.

    Args:
        image_data (bytes): Raw image data that may contain null bytes

    Returns:
        bytes: Original or sanitized image data, or None if corrupted beyond repair
    """
    if not image_data:
        logger.warning("Empty image data provided for sanitization")
        return image_data

    original_size = len(image_data)

    # Check for null bytes
    if b'\x00' not in image_data:
        logger.debug("No null bytes found in image data")
        return image_data

    # Count null bytes for logging
    null_count = image_data.count(b'\x00')
    logger.info(f"Found {null_count} null bytes in image data (size: {original_size} bytes)")

    # For PNG files, null bytes are legitimate parts of the format
    # PNG signature: \x89PNG\r\n\x1a\n
    if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
        logger.info("Image appears to be a valid PNG format - null bytes are part of structure")
        return image_data

    # For JPEG files, null bytes might be padding or metadata
    if image_data.startswith(b'\xff\xd8\xff'):
        logger.info("Image appears to be JPEG format - checking for trailing null padding")
        # Remove only trailing null bytes (padding)
        stripped_data = image_data.rstrip(b'\x00')
        if len(stripped_data) < len(image_data):
            removed = len(image_data) - len(stripped_data)
            logger.info(f"Removed {removed} trailing null bytes from JPEG")
            return stripped_data
        return image_data

    # For other formats or unknown data, be more cautious
    # Check if null bytes are clustered at the end (likely padding)
    last_non_null = len(image_data) - 1
    while last_non_null >= 0 and image_data[last_non_null] == 0:
        last_non_null -= 1

    trailing_nulls = len(image_data) - 1 - last_non_null

    if trailing_nulls > 0:
        logger.info(f"Found {trailing_nulls} trailing null bytes - removing padding")
        sanitized_data = image_data[:last_non_null + 1]
        logger.info(f"Removed trailing null padding: {len(image_data)} -> {len(sanitized_data)} bytes")
        return sanitized_data

    # If null bytes are scattered throughout and it's not a recognized format,
    # this might be actual corruption. Return original data and let PIL handle it.
    logger.warning("Null bytes found throughout unrecognized image format - returning original data")
    return image_data


@handle_image_processing_errors("download_image", "downloader") if HAS_ENHANCED_LOGGING else lambda f: f
def download_with_retry(url, max_retries=3, base_delay=1.0, timeout=10):
    """
    Download content from URL with exponential backoff retry logic and enhanced logging.

    Args:
        url (str): URL to download from
        max_retries (int): Maximum number of retry attempts
        base_delay (float): Base delay between retries in seconds
        timeout (int): Request timeout in seconds

    Returns:
        requests.Response: HTTP response object if successful, None if failed

    Raises:
        ImageDownloadError: If download fails after all retries (when enhanced logging is available)
    """
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Downloading from {os.path.basename(url)} (attempt {attempt + 1})")
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()

            # Get content length from headers or actual content
            content_length = response.headers.get('content-length', 'unknown')
            if content_length == 'unknown' and hasattr(response, 'content'):
                try:
                    content_length = len(response.content)
                except (TypeError, AttributeError):
                    content_length = 'stream'

            logger.debug(f"Successfully downloaded {os.path.basename(url)} ({content_length} bytes)")
            return response

        except requests.exceptions.HTTPError as e:
            # Don't retry 4xx errors, but retry 5xx errors
            if e.response and 400 <= e.response.status_code < 500:
                error_msg = f"Client error {e.response.status_code} for {os.path.basename(url)} - not retrying"
                logger.error(error_msg)
                if HAS_ENHANCED_LOGGING:
                    raise ImageDownloadError(error_msg) from e
                raise
            elif attempt == max_retries:
                status = e.response.status_code if e.response else 'unknown'
                error_msg = f"Server error {status} for {os.path.basename(url)} - final attempt failed"
                logger.error(error_msg)
                if HAS_ENHANCED_LOGGING:
                    raise ImageDownloadError(error_msg) from e
                raise
            else:
                status = e.response.status_code if e.response else 'unknown'
                logger.warning(f"Server error {status} for {os.path.basename(url)} - will retry")

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt == max_retries:
                error_msg = f"Network error for {os.path.basename(url)} after {max_retries + 1} attempts: {e}"
                logger.error(error_msg)
                if HAS_ENHANCED_LOGGING:
                    raise ImageDownloadError(error_msg) from e
                raise
            else:
                logger.warning(f"Network error for {os.path.basename(url)} (attempt {attempt + 1}): {e} - will retry")

        # Calculate delay with jitter for next attempt
        if attempt < max_retries:
            delay = base_delay * (2 ** attempt)
            jitter = random.uniform(0.1, 0.3) * delay
            total_delay = delay + jitter
            logger.info(f"Waiting {total_delay:.2f} seconds before retry...")
            time.sleep(total_delay)

    return None


def create_fallback_logo(team_id, size=(200, 200)):
    """
    Create a simple fallback logo when the original cannot be processed.

    Args:
        team_id (str): Team ID for generating a unique color
        size (tuple): Size of the fallback logo

    Returns:
        PIL.Image.Image: Simple colored logo
    """
    try:
        # Generate a color based on team ID
        import hashlib
        hash_obj = hashlib.md5(str(team_id).encode())
        hash_hex = hash_obj.hexdigest()

        # Extract RGB values from hash
        r = int(hash_hex[0:2], 16)
        g = int(hash_hex[2:4], 16)
        b = int(hash_hex[4:6], 16)

        # Ensure colors are not too dark or too light
        r = max(80, min(200, r))
        g = max(80, min(200, g))
        b = max(80, min(200, b))

        # Create a simple colored circle
        image = Image.new('RGBA', size, (0, 0, 0, 0))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)

        # Draw a colored circle
        margin = size[0] // 8
        draw.ellipse([margin, margin, size[0] - margin, size[1] - margin],
                     fill=(r, g, b, 255), outline=(255, 255, 255, 255), width=3)

        logger.info(f"Created fallback logo for team {team_id} with color ({r}, {g}, {b})")
        return image

    except Exception as e:
        logger.error(f"Failed to create fallback logo for team {team_id}: {e}")
        # Ultimate fallback - simple gray circle
        image = Image.new('RGBA', size, (0, 0, 0, 0))
        try:
            from PIL import ImageDraw
            draw = ImageDraw.Draw(image)
            margin = size[0] // 8
            draw.ellipse([margin, margin, size[0] - margin, size[1] - margin],
                         fill=(128, 128, 128, 255), outline=(255, 255, 255, 255), width=3)
        except Exception:
            pass
        return image


def process_image_response(response, url):
    """
    Process image response with sanitization and validation.

    Args:
        response (requests.Response): HTTP response containing image data
        url (str): URL for logging purposes

    Returns:
        PIL.Image.Image: Processed image or None if failed
    """
    try:
        # Sanitize the image data
        sanitized_data = sanitize_image_data(response.content)
        if sanitized_data is None:
            logger.error(f"Image data from {url} too corrupted to process")
            return None

        # Try to open and process the image
        image_stream = BytesIO(sanitized_data)
        image = Image.open(image_stream)

        # Convert to RGBA for consistent processing
        image = image.convert("RGBA")

        # Basic validation
        width, height = image.size
        if width <= 0 or height <= 0:
            logger.error(f"Invalid image dimensions from {url}: {width}x{height}")
            return None

        logger.info(f"Successfully processed image from {url}: {width}x{height}")
        return image

    except Exception as e:
        logger.error(f"Failed to process image from {url}: {e}")
        return None


def crop_transparent_border(image):
    """Automatically crops transparent borders from an image."""
    if image.mode != 'RGBA':
        return image
    bbox = image.getbbox()
    if bbox:
        cropped_image = image.crop(bbox)
        return cropped_image
    else:
        logger.warning("Attempted to crop a fully transparent image. Returning original.")
        return image


@handle_image_processing_errors("merge_images", "combiner") if HAS_ENHANCED_LOGGING else lambda f: f
def merge_images_from_urls(url1, url2, background_image_path=None):
    """
    Merges two images from URLs, crops borders, resizes, and combines into a square canvas.
    Returns a PIL Image object with enhanced logging and error handling.

    Args:
        url1 (str): URL for the first team logo
        url2 (str): URL for the second team logo
        background_image_path (str, optional): Path to background image

    Returns:
        PIL.Image: Combined image or None if processing fails

    Raises:
        ImageDownloadError: If logo URLs cannot be downloaded
        ImageValidationError: If URLs are invalid
        ImageCombineError: If image combination fails
        ImageProcessingError: If any other processing error occurs
    """
    start_time = time.time()

    try:
        # Enhanced URL validation
        if HAS_ENHANCED_LOGGING:
            validate_image_parameters(url1=url1, url2=url2)
        else:
            # Legacy validation
            if not url1 or not isinstance(url1, str):
                error_msg = "Invalid URL for logo 1"
                logger.error(error_msg)
                if HAS_ERROR_HANDLER:
                    raise ValidationError(error_msg, {"url": url1})
                return None

            if not url2 or not isinstance(url2, str):
                error_msg = "Invalid URL for logo 2"
                logger.error(error_msg)
                if HAS_ERROR_HANDLER:
                    raise ValidationError(error_msg, {"url": url2})
                return None

        # Fetch and process first logo
        logger.info(f"Fetching logo 1 from: {os.path.basename(url1)}")
        try:
            response1 = download_with_retry(url1, max_retries=3, base_delay=2.0, timeout=10)
            if response1 is None:
                error_msg = f"Failed to download logo 1 after retries"
                logger.error(error_msg)
                if HAS_ENHANCED_LOGGING:
                    raise ImageDownloadError(error_msg)
                elif HAS_ERROR_HANDLER:
                    raise ProcessingError(error_msg, {"url": os.path.basename(url1)})
                return None

            image1 = process_image_response(response1, url1)
            if image1 is None:
                logger.warning(f"Failed to process logo 1 from: {os.path.basename(url1)}, using fallback")
                # Extract team ID from URL for fallback
                team1_id = url1.split('/')[-1].replace('.png', '')
                image1 = create_fallback_logo(team1_id)
                if image1 is None:
                    error_msg = f"Failed to create fallback logo for team {team1_id}"
                    logger.error(error_msg)
                    if HAS_ENHANCED_LOGGING:
                        raise ImageProcessingError(error_msg)
                    elif HAS_ERROR_HANDLER:
                        raise ProcessingError(error_msg, {"team_id": team1_id})
                    return None

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 'unknown'
            error_msg = f"Failed to fetch logo 1: HTTP error {status}"
            logger.error(error_msg)
            if HAS_ENHANCED_LOGGING:
                raise ImageDownloadError(error_msg) from e
            elif HAS_ERROR_HANDLER:
                raise ResourceNotFoundError(error_msg, {"url": os.path.basename(url1), "status_code": status})
            return None
        except (requests.exceptions.RequestException, UnidentifiedImageError) as e:
            error_msg = f"Error processing logo 1: {str(e)}"
            logger.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url1})
            return None

        logger.info("Cropping transparent border for logo 1")
        image1_cropped = crop_transparent_border(image1)
        if not image1_cropped or image1_cropped.size == (0, 0):
            error_msg = f"Logo 1 from {url1} seems to be fully transparent or invalid after cropping."
            logger.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url1})
            return None

        # Fetch and process second logo
        logger.info(f"Fetching logo 2 from: {url2}")
        try:
            response2 = download_with_retry(url2, max_retries=3, base_delay=2.0, timeout=10)
            if response2 is None:
                error_msg = f"Failed to download logo 2 after retries: {url2}"
                logger.error(error_msg)
                if HAS_ERROR_HANDLER:
                    raise ProcessingError(error_msg, {"url": url2})
                return None

            image2 = process_image_response(response2, url2)
            if image2 is None:
                logger.warning(f"Failed to process logo 2 from: {url2}, using fallback")
                # Extract team ID from URL for fallback
                team2_id = url2.split('/')[-1].replace('.png', '')
                image2 = create_fallback_logo(team2_id)
                if image2 is None:
                    error_msg = f"Failed to create fallback logo for team {team2_id}"
                    logger.error(error_msg)
                    if HAS_ERROR_HANDLER:
                        raise ProcessingError(error_msg, {"url": url2})
                    return None

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else 'unknown'
            error_msg = f"Failed to fetch logo 2: HTTP error {status}"
            logger.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ResourceNotFoundError(error_msg, {"url": url2, "status_code": status})
            return None
        except (requests.exceptions.RequestException, UnidentifiedImageError) as e:
            error_msg = f"Error processing logo 2: {str(e)}"
            logger.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url2})
            return None

        logger.info("Cropping transparent border for logo 2")
        image2_cropped = crop_transparent_border(image2)
        if not image2_cropped or image2_cropped.size == (0, 0):
            error_msg = f"Logo 2 from {url2} seems to be fully transparent or invalid after cropping."
            logger.error(error_msg)
            if HAS_ERROR_HANDLER:
                raise ProcessingError(error_msg, {"url": url2})
            return None

        width1, height1 = image1_cropped.size
        width2, height2 = image2_cropped.size

        if height1 <= 0 or height2 <= 0:
            logger.error("One or both logos have zero or negative height after cropping. Cannot proceed.")
            return None
        target_height = min(height1, height2)

        if height1 > target_height:
            logger.info(f"Resizing logo 1 (height {height1}) to target height ({target_height})")
            ratio = target_height / float(height1)
            new_width1 = int(width1 * ratio)
            if new_width1 > 0 and target_height > 0:
                image1_cropped = image1_cropped.resize((new_width1, target_height), Image.Resampling.LANCZOS)
                width1, height1 = image1_cropped.size
            else:
                logger.warning("Skipping resize for logo 1 due to zero dimension calculation.")
        elif height2 > target_height:
            logger.info(f"Resizing logo 2 (height {height2}) to target height ({target_height})")
            ratio = target_height / float(height2)
            new_width2 = int(width2 * ratio)
            if new_width2 > 0 and target_height > 0:
                image2_cropped = image2_cropped.resize((new_width2, target_height), Image.Resampling.LANCZOS)
                width2, height2 = image2_cropped.size
            else:
                logger.warning("Skipping resize for logo 2 due to zero dimension calculation.")

        combined_width = width1 + width2
        combined_height = target_height

        if combined_width <= 0 or combined_height <= 0:
            logger.error("Cannot create image with zero width or height after processing logos.")
            return None

        padding_horizontal = int(combined_width * 0.10)
        padding_vertical = int(combined_height * 0.10)
        canvas_size = max(1, combined_width + 2 * padding_horizontal, combined_height + 2 * padding_vertical)

        new_image = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))

        bg_path_to_use = background_image_path if background_image_path else DEFAULT_BG_PATH

        try:
            logger.info(f"Loading background image from: {bg_path_to_use}")
            if not os.path.exists(bg_path_to_use):
                error_msg = f"Background image not found at '{bg_path_to_use}'"
                logger.warning(f"{error_msg}. Using transparent background.")
                if HAS_ERROR_HANDLER:
                    # Non-fatal error, just log a warning
                    logger.warning(error_msg)
            else:
                try:
                    background = Image.open(bg_path_to_use).convert('RGBA')
                    bg_width, bg_height = background.size
                    if bg_width <= 0 or bg_height <= 0:
                        logger.warning(f"Background image '{bg_path_to_use}' has zero dimension. Skipping background.")
                    else:
                        min_bg_dimension = min(bg_width, bg_height)
                        left = (bg_width - min_bg_dimension) // 2
                        top = (bg_height - min_bg_dimension) // 2
                        right = left + min_bg_dimension
                        bottom = top + min_bg_dimension
                        cropped_background = background.crop((left, top, right, bottom))
                        resized_background = cropped_background.resize(
                            (canvas_size, canvas_size), Image.Resampling.LANCZOS)
                        new_image.paste(resized_background, (0, 0))
                        logger.info(f"Applied background image: {bg_path_to_use}")
                except UnidentifiedImageError as e:
                    error_msg = f"Invalid background image format at '{bg_path_to_use}': {e}"
                    logger.warning(f"{error_msg}. Using transparent background.")
                    if HAS_ERROR_HANDLER:
                        # Non-fatal error, just log a warning
                        logger.warning(error_msg)
                except Exception as e:
                    error_msg = f"Error processing background image '{bg_path_to_use}': {e}"
                    logger.warning(f"{error_msg}. Using transparent background.")
                    if HAS_ERROR_HANDLER:
                        # Non-fatal error, just log a warning
                        logger.warning(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error with background image '{bg_path_to_use}': {e}"
            logger.warning(f"{error_msg}. Using transparent background.")
            if HAS_ERROR_HANDLER:
                # Non-fatal error, just log a warning
                logger.warning(error_msg)

        x_offset1 = padding_horizontal
        y_offset1 = (canvas_size - height1) // 2
        x_offset2 = x_offset1 + width1
        y_offset2 = (canvas_size - height2) // 2

        mask1 = image1_cropped if image1_cropped.mode == 'RGBA' else None
        mask2 = image2_cropped if image2_cropped.mode == 'RGBA' else None

        new_image.paste(image1_cropped, (x_offset1, y_offset1), mask=mask1)
        new_image.paste(image2_cropped, (x_offset2, y_offset2), mask=mask2)

        return new_image  # Return the PIL Image object

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
        logger.error(error_msg, exc_info=True)
        if HAS_ERROR_HANDLER:
            raise ProcessingError(error_msg)
        return None


if __name__ == "__main__":
    # Example usage (for testing the script directly)
    # You can still run this script directly to test the core logic
    team_id1 = "12910"  # IF Haga - known problematic team with null bytes
    team_id2 = "9332"   # Herrestads AIF - known problematic team
    logo_url1 = f"{BASE_LOGO_URL}{team_id1}.png"
    logo_url2 = f"{BASE_LOGO_URL}{team_id2}.png"
    output_path = "combined_logos_test.png"  # Output path for direct script execution
    background_image_path = str(DEFAULT_BG_PATH)  # Use default background

    logger.info("--- Starting Logo Merge (Direct Test) ---")
    logger.info(f"Team ID 1: {team_id1} ({logo_url1})")
    logger.info(f"Team ID 2: {team_id2} ({logo_url2})")
    logger.info(f"Output Path: {output_path}")
    logger.info(f"Background Image Path: {background_image_path}")

    combined_image = merge_images_from_urls(logo_url1, logo_url2, background_image_path)

    if combined_image:
        try:
            output_path_obj = pathlib.Path(output_path)
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)
            combined_image.save(output_path)
            logger.info(f"Merged image saved to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to save the test image: {e}")
    else:
        logger.error("Failed to generate combined image in direct test.")

    logger.info("--- Logo Merge Finished (Direct Test) ---")
