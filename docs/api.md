# API Documentation

## Base URL

All endpoints are relative to the base URL of the service:

```
http://localhost:5002
```

## Endpoints

### Health Check

**Endpoint:** `GET /health`

**Description:** Check the health status of the service.

**Response:**
```json
{
  "status": "healthy",
  "service": "whatsapp-avatar-service",
  "timestamp": 1621234567.89
}
```

**Status Codes:**
- `200 OK`: Service is healthy

### Create Avatar

**Endpoint:** `POST /create_avatar`

**Description:** Create a combined avatar image from two team logos.

**Request Body:**
```json
{
  "team1_id": "7557",
  "team2_id": "9590"
}
```

**Parameters:**
- `team1_id` (string, required): ID of the first team
- `team2_id` (string, required): ID of the second team

**Response:**
- Content-Type: `image/png`
- Body: Binary image data

**Status Codes:**
- `200 OK`: Avatar created successfully
- `400 Bad Request`: Missing or invalid parameters
- `500 Internal Server Error`: Error processing the image

**Error Response:**
```json
{
  "error": "Error message"
}
```

## Error Handling

The API returns appropriate HTTP status codes and error messages in JSON format:

```json
{
  "error": "Description of the error"
}
```

Common error scenarios:
- Missing team IDs in the request
- Invalid team IDs
- Network errors when fetching team logos
- Image processing errors

## Example Usage

### Using curl

```bash
curl -X POST \
  http://localhost:5002/create_avatar \
  -H 'Content-Type: application/json' \
  -d '{
    "team1_id": "7557",
    "team2_id": "9590"
  }' \
  --output combined_avatar.png
```

### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:5002/create_avatar",
    json={
        "team1_id": "7557",
        "team2_id": "9590"
    }
)

if response.status_code == 200:
    with open("combined_avatar.png", "wb") as f:
        f.write(response.content)
else:
    print(f"Error: {response.json()['error']}")
```
