# Team Logo Combiner Service

A service that combines two team logos into a single avatar image.

## Setup and Running with Docker Compose

### Prerequisites

- Docker and Docker Compose installed
- The `fogis-network` Docker network should exist (or modify the docker-compose.yml file)

### Running the Service

To start the service:

```bash
# Start the service in detached mode
docker-compose up -d
```

To stop the service:

```bash
# Stop the service but keep the containers
docker-compose stop

# Stop and remove the containers
docker-compose down
```

To rebuild and restart the service:

```bash
# Rebuild the image and restart the service
docker-compose up -d --build
```

### Viewing Logs

```bash
# View logs
docker-compose logs

# Follow logs
docker-compose logs -f
```

## API Usage

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "whatsapp-avatar-service",
  "timestamp": 1621234567.89
}
```

### Create Avatar

**Endpoint:** `POST /create_avatar`

**Request Body:**
```json
{
  "team1_id": "7557",
  "team2_id": "9590"
}
```

**Response:** PNG image of the combined team logos

## Development

### Customizing Assets

The service uses a background image located in the `assets` directory. You can replace this image without rebuilding the Docker image as the directory is mounted as a volume.

### Environment Variables

The following environment variables can be set in the docker-compose.yml file:

- `FLASK_ENV`: Set to "development" for debug mode or "production" for production mode
- `LOG_LEVEL`: Set the logging level (DEBUG, INFO, WARNING, ERROR)
