import pytest
import os
from unittest.mock import patch, MagicMock
from io import BytesIO
from PIL import Image
import requests
import team_logo_combiner

@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
    return img

@pytest.fixture
def sample_transparent_image():
    """Create a sample image with transparency for testing."""
    img = Image.new('RGBA', (100, 100), color=(0, 0, 0, 0))
    # Add some non-transparent pixels
    for x in range(25, 75):
        for y in range(25, 75):
            img.putpixel((x, y), (0, 255, 0, 255))
    return img

def test_crop_transparent_border(sample_transparent_image):
    """Test cropping transparent borders from an image."""
    # This function should be implemented in team_logo_combiner
    cropped = team_logo_combiner.crop_transparent_border(sample_transparent_image)
    
    # The cropped image should be smaller than the original
    assert cropped.width <= sample_transparent_image.width
    assert cropped.height <= sample_transparent_image.height
    
    # The cropped image should only contain the non-transparent part
    assert cropped.width == 50
    assert cropped.height == 50

@patch('requests.get')
def test_merge_images_from_urls_success(mock_get, sample_image, test_assets_dir):
    """Test successful merging of two images from URLs."""
    # Create a mock response for requests.get
    mock_response = MagicMock()
    mock_response.content = BytesIO()
    sample_image.save(mock_response.content, format='PNG')
    mock_response.content.seek(0)
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    # Create a test background image
    bg_path = os.path.join(test_assets_dir, 'test_bg.jpg')
    sample_image.convert('RGB').save(bg_path, format='JPEG')
    
    # Call the function
    result = team_logo_combiner.merge_images_from_urls(
        'http://example.com/logo1.png',
        'http://example.com/logo2.png',
        background_image_path=bg_path
    )
    
    # Verify the result
    assert result is not None
    assert isinstance(result, Image.Image)
    assert result.mode == 'RGBA'
    
    # Clean up
    os.remove(bg_path)

@patch('requests.get')
def test_merge_images_http_error(mock_get):
    """Test handling of HTTP errors when fetching images."""
    # Mock an HTTP error
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_get.return_value = mock_response
    
    # Call the function
    result = team_logo_combiner.merge_images_from_urls(
        'http://example.com/logo1.png',
        'http://example.com/logo2.png'
    )
    
    # Verify the result
    assert result is None

@patch('requests.get')
def test_merge_images_network_error(mock_get):
    """Test handling of network errors when fetching images."""
    # Mock a network error
    mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
    
    # Call the function
    result = team_logo_combiner.merge_images_from_urls(
        'http://example.com/logo1.png',
        'http://example.com/logo2.png'
    )
    
    # Verify the result
    assert result is None

@patch('requests.get')
def test_merge_images_invalid_image(mock_get):
    """Test handling of invalid image data."""
    # Mock an invalid image response
    mock_response = MagicMock()
    mock_response.content = b'not an image'
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response
    
    # Call the function
    result = team_logo_combiner.merge_images_from_urls(
        'http://example.com/logo1.png',
        'http://example.com/logo2.png'
    )
    
    # Verify the result
    assert result is None
