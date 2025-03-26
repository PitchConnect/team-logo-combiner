from PIL import Image
import requests
from io import BytesIO
import argparse

BASE_LOGO_URL = "https://staticcdn.svenskfotboll.se/img/teams/"

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
        return image

def merge_images_from_urls(url1, url2, output_path):
    """
    Merges two images from URLs, CROPPING TRANSPARENT BORDERS first,
    and then combining them side-by-side into a SQUARE canvas with padding.
    """
    try:
        # Download and open the first image, convert to RGBA
        response1 = requests.get(url1, stream=True)
        response1.raise_for_status()
        image1 = Image.open(BytesIO(response1.content)).convert("RGBA")

        # Crop transparent border from the first image
        image1_cropped = crop_transparent_border(image1)

        # Download and open the second image, convert to RGBA
        response2 = requests.get(url2, stream=True)
        response2.raise_for_status()
        image2 = Image.open(BytesIO(response2.content)).convert("RGBA")

        # Crop transparent border from the second image
        image2_cropped = crop_transparent_border(image2)

        # Get dimensions of cropped images
        width1, height1 = image1_cropped.size
        width2, height2 = image2_cropped.size

        # Determine target height (using the smaller height)
        target_height = min(height1, height2)

        # Resize the larger image to match the target height, maintaining aspect ratio
        if height1 > height2:
            ratio = target_height / float(height1)
            new_width1 = int(width1 * ratio)
            image1_cropped = image1_cropped.resize((new_width1, target_height),
                                                   Image.Resampling.LANCZOS)  # Use LANCZOS for good quality
            width1, height1 = image1_cropped.size  # Update dimensions
        elif height2 > height1:
            ratio = target_height / float(height2)
            new_width2 = int(width2 * ratio)
            image2_cropped = image2_cropped.resize((new_width2, target_height),
                                                   Image.Resampling.LANCZOS)  # Use LANCZOS for good quality
            width2, height2 = image2_cropped.size  # Update dimensions

        # Now use the RESIZED and CROPPED images for merging
        combined_width = width1 + width2
        combined_height = max(height1, height2)  # height1 and height2 should be approximately equal now

        padding_horizontal = int(combined_width * 0.10)
        padding_vertical = int(combined_height * 0.10)

        canvas_size = max(combined_width + 2 * padding_horizontal, combined_height + 2 * padding_vertical)

        new_image = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))

        x_offset1 = padding_horizontal
        y_offset1 = (canvas_size - height1) // 2

        x_offset2 = x_offset1 + width1
        y_offset2 = (canvas_size - height2) // 2

        new_image.paste(image1_cropped, (x_offset1, y_offset1), mask=image1_cropped)
        new_image.paste(image2_cropped, (x_offset2, y_offset2), mask=image2_cropped)

        rgb_image = new_image.convert('RGB')
        rgb_image.save(output_path)
        print(
            f"Merged image saved to: {output_path} (Square with padding, TRANSPARENT BORDERS CROPPED, LOGOS RESIZED FOR BALANCE)")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
    except Exception as e:
        print(f"Error processing images: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge team logos side-by-side from Svenskfotboll CDN into a square image with padding, with transparent borders cropped.")
    parser.add_argument("team_id1", type=str, help="ID of the first team (number).")
    parser.add_argument("team_id2", type=str, help="ID of the second team (number).")
    parser.add_argument("-o", "--output", dest="output_path", default="combined_logos.png",
                        help="Path to save the combined image (default: combined_logos.png).")

    args = parser.parse_args()

    team_id1 = args.team_id1
    team_id2 = args.team_id2
    output_image_path = args.output_path

    logo_url1 = f"{BASE_LOGO_URL}{team_id1}.png"
    logo_url2 = f"{BASE_LOGO_URL}{team_id2}.png"

    print(f"Fetching logo 1 from: {logo_url1}")
    print(f"Fetching logo 2 from: {logo_url2}")

    merge_images_from_urls(logo_url1, logo_url2, output_image_path)
    print(f"Done! Combined image saved to: {output_image_path}")