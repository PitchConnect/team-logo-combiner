import pytest
import json
from unittest.mock import patch, MagicMock
from io import BytesIO
from PIL import Image

def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'whatsapp-avatar-service'
    assert 'timestamp' in data

def test_create_avatar_missing_team_ids(client):
    """Test create_avatar endpoint with missing team IDs."""
    # Test with empty JSON
    response = client.post('/create_avatar', json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    
    # Test with partial data
    response = client.post('/create_avatar', json={'team1_id': '1234'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

@patch('team_logo_combiner.merge_images_from_urls')
def test_create_avatar_success(mock_merge, client):
    """Test successful avatar creation."""
    # Create a test image
    test_image = Image.new('RGBA', (100, 100), color=(73, 109, 137, 255))
    mock_merge.return_value = test_image
    
    response = client.post('/create_avatar', json={
        'team1_id': '1234',
        'team2_id': '5678'
    })
    
    assert response.status_code == 200
    assert response.mimetype == 'image/png'
    
    # Verify the merge function was called with correct parameters
    mock_merge.assert_called_once()
    args, _ = mock_merge.call_args
    assert '1234' in args[0]
    assert '5678' in args[1]

@patch('team_logo_combiner.merge_images_from_urls')
def test_create_avatar_processing_failure(mock_merge, client):
    """Test avatar creation when image processing fails."""
    # Simulate failure in image processing
    mock_merge.return_value = None
    
    response = client.post('/create_avatar', json={
        'team1_id': '1234',
        'team2_id': '5678'
    })
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data

@patch('team_logo_combiner.merge_images_from_urls')
def test_create_avatar_exception(mock_merge, client):
    """Test avatar creation when an exception occurs."""
    # Simulate an exception
    mock_merge.side_effect = Exception("Test exception")
    
    response = client.post('/create_avatar', json={
        'team1_id': '1234',
        'team2_id': '5678'
    })
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
