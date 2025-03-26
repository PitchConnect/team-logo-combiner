# Use Image.LANCZOS directly
from PIL import Image # Remove ImageResampling from here
import requests
from io import BytesIO
import argparse
import logging
import pathlib

# --- Constants and Paths ---
BASE_LOGO_URL = "https://staticcdn.svenskfotboll.se/img/teams/"
SCRIPT_DIR = pathlib.Path(__file__).parent.resolve() # Get the directory where the script is located
ASSETS_DIR_NAME = "assets" # Define the assets folder name
DEFAULT_BG_FILENAME = "grass_turf.jpg" # Define the default background filename
DEFAULT_BG_PATH = SCRIPT_DIR / ASSETS_DIR_NAME / DEFAULT_BG_FILENAME # Construct the full default path

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def crop_transparent_border(image):
    """
    Automatically crops transparent borders from an image.
    """
    if image.mode != 'RGBA':
        return image
    bbox = image.getbbox()
    if bbox:
        cropped_image = image.crop(bbox)
        return cropped_image
    else:
        # Handle fully transparent images
        logging.warning("Attempted to crop a fully transparent image. Returning original.")
        return image

def merge_images_from_urls(url1, url2, output_path, background_image_path=None):
    """
    Merges two images from URLs, CROPPING TRANSPARENT BORDERS first,
    RESIZING the larger logo to match the height of the smaller one,
    and then combining them side-by-side into a SQUARE canvas with padding,
    with an optional background image (cropped to square).
    """
    try:
        logging.info(f"Fetching logo 1 from: {url1}")
        response1 = requests.get(url1, stream=True)
        response1.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        image1 = Image.open(BytesIO(response1.content)).convert("RGBA")

        logging.info("Cropping transparent border for logo 1")
        image1_cropped = crop_transparent_border(image1)
        if not image1_cropped or image1_cropped.size == (0, 0): # Check if cropping failed or resulted in zero size
             logging.error(f"Logo 1 from {url1} seems to be fully transparent or invalid after cropping.")
             return # Exit the function early if a logo is unusable

        logging.info(f"Fetching logo 2 from: {url2}")
        response2 = requests.get(url2, stream=True)
        response2.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        image2 = Image.open(BytesIO(response2.content)).convert("RGBA")

        logging.info("Cropping transparent border for logo 2")
        image2_cropped = crop_transparent_border(image2)
        if not image2_cropped or image2_cropped.size == (0, 0): # Check if cropping failed or resulted in zero size
             logging.error(f"Logo 2 from {url2} seems to be fully transparent or invalid after cropping.")
             return # Exit the function early

        # Get dimensions of cropped images
        width1, height1 = image1_cropped.size
        width2, height2 = image2_cropped.size

        # Determine target height (using the smaller height)
        if height1 <= 0 or height2 <= 0: # Use <= 0 for safety
            logging.error("One or both logos have zero or negative height after cropping. Cannot proceed.")
            return
        target_height = min(height1, height2)

        # Resize the larger image to match the target height, maintaining aspect ratio
        if height1 > target_height: # Check if resizing is actually needed
            logging.info(f"Resizing logo 1 (height {height1}) to match target height ({target_height})")
            ratio = target_height / float(height1)
            new_width1 = int(width1 * ratio)
            if new_width1 > 0 and target_height > 0:
                 # Use Image.LANCZOS directly
                 image1_cropped = image1_cropped.resize((new_width1, target_height), Image.Resampling.LANCZOS)
                 width1, height1 = image1_cropped.size # Update dimensions
            else:
                 logging.warning("Skipping resize for logo 1 due to zero dimension calculation.")
        elif height2 > target_height: # Check if resizing is actually needed
            logging.info(f"Resizing logo 2 (height {height2}) to match target height ({target_height})")
            ratio = target_height / float(height2)
            new_width2 = int(width2 * ratio)
            if new_width2 > 0 and target_height > 0:
                 # Use Image.LANCZOS directly
                 image2_cropped = image2_cropped.resize((new_width2, target_height), Image.Resampling.LANCZOS)
                 width2, height2 = image2_cropped.size # Update dimensions
            else:
                 logging.warning("Skipping resize for logo 2 due to zero dimension calculation.")

        # Now use the RESIZED and CROPPED images for merging
        combined_width = width1 + width2
        # Ensure combined_height is based on the actual (potentially resized) heights
        combined_height = target_height # Since we resized to target_height

        if combined_width <= 0 or combined_height <= 0:
            logging.error("Cannot create image with zero or negative width or height after processing logos.")
            return

        padding_horizontal = int(combined_width * 0.10)
        padding_vertical = int(combined_height * 0.10)

        # Ensure canvas size is at least 1x1
        # Use max() correctly, comparing pairs
        canvas_size = max(1, combined_width + 2 * padding_horizontal, combined_height + 2 * padding_vertical)


        new_image = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0)) # Create transparent canvas

        # --- Background Image Handling ---
        bg_path_to_use = background_image_path if background_image_path else DEFAULT_BG_PATH

        try:
            logging.info(f"Attempting to load background image from: {bg_path_to_use}")
            background = Image.open(bg_path_to_use).convert('RGBA') # Open background, convert to RGBA

            # Crop background to square based on smallest dimension
            bg_width, bg_height = background.size
            if bg_width <= 0 or bg_height <= 0:
                logging.warning(f"Background image '{bg_path_to_use}' has zero or negative dimension. Skipping background.")
            else:
                min_bg_dimension = min(bg_width, bg_height)
                left = (bg_width - min_bg_dimension) // 2
                top = (bg_height - min_bg_dimension) // 2
                right = left + min_bg_dimension
                bottom = top + min_bg_dimension
                cropped_background = background.crop((left, top, right, bottom))
                logging.info("Background image cropped to square")

                # Resize cropped background to canvas size
                # Use Image.LANCZOS directly
                resized_background = cropped_background.resize((canvas_size, canvas_size), Image.Resampling.LANCZOS)
                new_image.paste(resized_background, (0, 0)) # Paste background onto canvas
                logging.info(f"Successfully applied background image: {bg_path_to_use}")

        except FileNotFoundError:
            logging.warning(f"Background image not found at '{bg_path_to_use}'. Using transparent background.")
        except Exception as e: # Catch other potential issues with background image
            logging.warning(f"Error processing background image '{bg_path_to_use}': {e}. Using transparent background.")


        # --- Paste Logos (same as before, but now on top of background) ---
        x_offset1 = padding_horizontal
        y_offset1 = (canvas_size - height1) // 2
        x_offset2 = x_offset1 + width1
        # Use target_height for y_offset2 as well for consistency after resizing
        y_offset2 = (canvas_size - height2) // 2 # height1 and height2 should be target_height now

        # Ensure logos have alpha masks before pasting if they are RGBA
        mask1 = image1_cropped if image1_cropped.mode == 'RGBA' else None
        mask2 = image2_cropped if image2_cropped.mode == 'RGBA' else None

        new_image.paste(image1_cropped, (x_offset1, y_offset1), mask=mask1)
        new_image.paste(image2_cropped, (x_offset2, y_offset2), mask=mask2)

        try:
            # Save the final image
            output_path_obj = pathlib.Path(output_path)
            final_image_format = output_path_obj.suffix.upper()[1:]

            # Ensure parent directory exists
            output_path_obj.parent.mkdir(parents=True, exist_ok=True)

            if final_image_format in ['JPG', 'JPEG']:
                 # JPEG doesn't support transparency, convert to RGB
                 save_image = new_image.convert('RGB')
                 save_image.save(output_path, quality=95) # Add quality for JPEG
                 logging.info(f"Merged image saved as JPEG to: {output_path}")
            else:
                 # Save formats supporting transparency (like PNG) as is
                 new_image.save(output_path)
                 logging.info(f"Merged image saved to: {output_path}")

        except Exception as e:
            logging.error(f"Failed to save the final image to {output_path}: {e}")


    except requests.exceptions.HTTPError as e:
         logging.error(f"HTTP error fetching logo: {e}") # Catch HTTP errors raised by raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error downloading image: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during image processing: {e}", exc_info=True) # Add traceback


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Merge team logos side-by-side from Svenskfotboll CDN into a square image with padding, cropping borders, resizing logos, and adding an optional background.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter # Show default values in help
    )
    parser.add_argument("team_id1", type=str, help="ID of the first team (number).")
    parser.add_argument("team_id2", type=str, help="ID of the second team (number).")
    parser.add_argument("-o", "--output", dest="output_path", default="combined_logos.png",
                        help="Path to save the combined image.")
    # Updated help message and default value for background image
    parser.add_argument("-b", "--background-image", dest="background_image_path", default=str(DEFAULT_BG_PATH),
                        help=f"Path to a background image. Defaults to '{ASSETS_DIR_NAME}/{DEFAULT_BG_FILENAME}' relative to the script.")

    args = parser.parse_args()

    team_id1 = args.team_id1
    team_id2 = args.team_id2
    output_image_path = args.output_path
    background_image_path = args.background_image_path

    logo_url1 = f"{BASE_LOGO_URL}{team_id1}.png"
    logo_url2 = f"{BASE_LOGO_URL}{team_id2}.png"

    logging.info(f"--- Starting Logo Merge ---")
    logging.info(f"Team ID 1: {team_id1} ({logo_url1})")
    logging.info(f"Team ID 2: {team_id2} ({logo_url2})")
    logging.info(f"Output Path: {output_image_path}")
    logging.info(f"Background Image Path: {background_image_path}")

    merge_images_from_urls(logo_url1, logo_url2, output_image_path, background_image_path)
    logging.info(f"--- Logo Merge Finished ---")