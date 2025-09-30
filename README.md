# Team Logo Combiner Service

A service that combines two team logos into a single avatar image with a background. This service is designed to create WhatsApp group avatars for matches between two teams.

## Project Status

This project includes comprehensive error handling, logging, testing, and Redis pub/sub integration. It is ready for production use.

**Version:** 2.2.0
**Redis Integration:** v1.0.0
**Enhanced Logging:** v2.1.0

## Architecture

The service is built using the following technologies:

- **Flask**: Web framework for the HTTP API
- **Redis**: Pub/sub messaging for asynchronous communication
- **Pillow**: Image processing library
- **Docker**: Containerization
- **Docker Compose**: Container orchestration

### Component Overview

- **app.py**: Flask application with dual-mode operation (HTTP + Redis)
- **team_logo_combiner.py**: Core image processing logic
- **src/redis_integration/**: Redis pub/sub integration module
  - **config.py**: Redis configuration management
  - **connection_manager.py**: Redis connection pooling
  - **publisher.py**: Avatar result publishing
  - **subscriber.py**: Avatar request subscription
  - **message_formatter.py**: Message formatting utilities
- **Dockerfile**: Container definition
- **docker-compose.yml**: Service configuration with Redis

### Communication Modes

The service supports three communication modes:

1. **Dual Mode (default)**: Both HTTP and Redis pub/sub enabled
2. **HTTP Mode**: Only HTTP endpoints (legacy mode)
3. **Redis Mode**: Only Redis pub/sub (no HTTP server)

Set via `COMMUNICATION_MODE` environment variable.

## Setup and Running with Docker Compose

### Prerequisites

- Docker and Docker Compose installed
- The `fogis-network` Docker network should exist (or modify the docker-compose.yml file)

### Configuration

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Key configuration options:

```bash
# Communication mode: 'http', 'redis', or 'dual' (default)
COMMUNICATION_MODE=dual

# Redis configuration
REDIS_URL=redis://fogis-redis:6379
REDIS_PUBSUB_ENABLED=true
REDIS_AVATAR_REQUESTS_CHANNEL=fogis:avatars:requests
REDIS_AVATAR_RESULTS_CHANNEL=fogis:avatars:results

# Processing configuration
AVATAR_RESULT_STORAGE=base64
AVATAR_PROCESSING_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
```

### Running the Service

To start the service (includes Redis):

```bash
# Start all services in detached mode
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f whatsapp-avatar-service
docker-compose logs -f fogis-redis
```

To stop the service:

```bash
# Stop the service but keep the containers
docker-compose stop

# Stop and remove the containers
docker-compose down

# Stop and remove containers + volumes (clears Redis data)
docker-compose down -v
```

To rebuild and restart the service:

```bash
# Rebuild the image and restart the service
docker-compose up -d --build
```

### Viewing Logs

```bash
# View all logs
docker-compose logs

# Follow logs for specific service
docker-compose logs -f whatsapp-avatar-service

# View Redis logs
docker-compose logs -f fogis-redis
```

## API Usage

### HTTP API (Legacy/Dual Mode)

#### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "team-logo-combiner",
  "version": "2.2.0",
  "timestamp": 1621234567.89,
  "enhanced_logging": "v2.1.0",
  "redis_integration": "v1.0.0",
  "redis_enabled": true,
  "redis_connected": true,
  "communication_mode": "dual",
  "subscriber_stats": {
    "running": true,
    "stats": {
      "total_received": 10,
      "successful_processed": 9,
      "failed_processed": 1
    }
  },
  "publisher_stats": {
    "redis_enabled": true,
    "redis_connected": true,
    "publishing_stats": {
      "total_published": 9,
      "successful_publishes": 9,
      "failed_publishes": 0
    }
  }
}
```

#### Create Avatar

**Endpoint:** `POST /create_avatar`

**Request Body:**
```json
{
  "team1_id": "7557",
  "team2_id": "9590"
}
```

**Response:** PNG image of the combined team logos

### Redis Pub/Sub API (Recommended)

#### Avatar Request Message

**Channel:** `fogis:avatars:requests`

**Message Format:**
```json
{
  "message_id": "uuid-v4",
  "timestamp": "2025-09-30T12:34:56.789Z",
  "source": "match-list-processor",
  "version": "1.0",
  "type": "avatar_request",
  "payload": {
    "team1_id": "7557",
    "team2_id": "9590",
    "team1_organization_id": "12345",
    "team2_organization_id": "67890",
    "match_id": "optional-match-id",
    "priority": "normal",
    "callback_channel": "fogis:avatars:results",
    "metadata": {
      "requester": "match-processor",
      "request_context": "whatsapp_group_creation"
    }
  }
}
```

#### Avatar Result Message (Success)

**Channel:** `fogis:avatars:results`

**Message Format:**
```json
{
  "message_id": "uuid-v4",
  "request_id": "original-request-uuid",
  "timestamp": "2025-09-30T12:34:57.123Z",
  "source": "team-logo-combiner",
  "version": "1.0",
  "type": "avatar_result",
  "payload": {
    "status": "success",
    "team1_id": "7557",
    "team2_id": "9590",
    "avatar_data": "base64-encoded-png-data",
    "processing_time_ms": 1234,
    "metadata": {
      "image_size": "512x512",
      "format": "PNG",
      "background": "grass_turf.jpg"
    }
  }
}
```

#### Avatar Result Message (Error)

**Channel:** `fogis:avatars:results`

**Message Format:**
```json
{
  "message_id": "uuid-v4",
  "request_id": "original-request-uuid",
  "timestamp": "2025-09-30T12:34:57.123Z",
  "source": "team-logo-combiner",
  "version": "1.0",
  "type": "avatar_result",
  "payload": {
    "status": "error",
    "team1_id": "7557",
    "team2_id": "9590",
    "error_type": "ImageDownloadError",
    "error_message": "Failed to download team logo after 3 retries",
    "processing_time_ms": 5678,
    "metadata": {
      "failed_url": "https://staticcdn.svenskfotboll.se/img/teams/7557.png",
      "retry_count": 3
    }
  }
}
```

### Testing Redis Integration

#### Using redis-cli

```bash
# Subscribe to results channel
docker exec -it fogis-redis redis-cli
> SUBSCRIBE fogis:avatars:results

# In another terminal, publish a test request
docker exec -it fogis-redis redis-cli
> PUBLISH fogis:avatars:requests '{"message_id":"test-123","payload":{"team1_id":"7557","team2_id":"9590"}}'
```

#### Using Python

```python
import redis
import json

# Connect to Redis
r = redis.from_url("redis://localhost:6379", decode_responses=True)

# Publish avatar request
request = {
    "message_id": "test-123",
    "payload": {
        "team1_id": "7557",
        "team2_id": "9590"
    }
}
r.publish("fogis:avatars:requests", json.dumps(request))

# Subscribe to results
pubsub = r.pubsub()
pubsub.subscribe("fogis:avatars:results")

for message in pubsub.listen():
    if message["type"] == "message":
        result = json.loads(message["data"])
        print(f"Received result: {result}")
        break
```

## Development

### Project Structure

```
./
|-- app.py                  # Flask application with Redis integration
|-- team_logo_combiner.py   # Core image processing logic
|-- src/
|   |-- core/               # Core utilities (logging, error handling)
|   |-- redis_integration/  # Redis pub/sub integration
|       |-- __init__.py
|       |-- config.py       # Redis configuration
|       |-- connection_manager.py  # Connection pooling
|       |-- publisher.py    # Result publishing
|       |-- subscriber.py   # Request subscription
|       |-- message_formatter.py   # Message formatting
|-- assets/                 # Background images and other assets
|   |-- grass_turf.jpg      # Default background image
|-- Dockerfile              # Container definition
|-- docker-compose.yml      # Service configuration (includes Redis)
|-- requirements.txt        # Python dependencies
|-- .env.example            # Environment configuration template
|-- tests/                  # Test suite
|   |-- conftest.py         # Test configuration
|   |-- test_app.py         # API tests
|   |-- test_team_logo_combiner.py  # Core logic tests
|   |-- redis_integration/  # Redis integration tests
|       |-- test_redis_config.py
|       |-- test_redis_connection.py
|       |-- test_redis_publisher.py
|       |-- test_redis_subscriber.py
|       |-- test_message_formatter.py
|       |-- test_integration.py
|-- run_tests.sh            # Script to run tests
```

### Running Tests

The project includes a comprehensive test suite with 79 tests covering all functionality.

```bash
# Run all tests
./run_tests.sh

# Or use pytest directly
pytest tests/ -v

# Run specific test categories
pytest tests/test_app.py -v                    # HTTP API tests
pytest tests/test_team_logo_combiner.py -v     # Image processing tests
pytest tests/redis_integration/ -v             # Redis integration tests

# Run with coverage report
pytest tests/ --cov=src --cov=app --cov=team_logo_combiner --cov-report=html

# Run integration tests only
pytest tests/redis_integration/test_integration.py -v
```

**Test Coverage:**
- HTTP API: 5 tests
- Image Processing: 16 tests
- Redis Integration: 58 tests
  - Configuration: 6 tests
  - Connection Manager: 12 tests
  - Publisher: 9 tests
  - Subscriber: 9 tests
  - Message Formatter: 14 tests
  - Integration: 8 tests

### Customizing Assets

The service uses a background image located in the `assets` directory. You can replace this image without rebuilding the Docker image as the directory is mounted as a volume.

### Environment Variables

The following environment variables can be configured (see `.env.example`):

**Flask Configuration:**
- `FLASK_ENV`: Set to "development" or "production"
- `FLASK_HOST`: Host to bind to (default: 0.0.0.0)
- `FLASK_PORT`: Port to listen on (default: 5002)
- `FLASK_DEBUG`: Enable debug mode (default: false)

**Logging Configuration:**
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_ENABLE_CONSOLE`: Enable console logging (default: true)
- `LOG_ENABLE_FILE`: Enable file logging (default: true)
- `LOG_ENABLE_STRUCTURED`: Enable structured logging (default: true)
- `LOG_DIR`: Log directory (default: logs)
- `LOG_FILE`: Log file name (default: team-logo-combiner.log)

**Redis Configuration:**
- `REDIS_URL`: Redis connection URL (default: redis://fogis-redis:6379)
- `REDIS_PUBSUB_ENABLED`: Enable Redis pub/sub (default: true)
- `REDIS_AVATAR_REQUESTS_CHANNEL`: Request channel (default: fogis:avatars:requests)
- `REDIS_AVATAR_RESULTS_CHANNEL`: Results channel (default: fogis:avatars:results)
- `REDIS_SERVICE_STATUS_CHANNEL`: Status channel (default: fogis:avatars:status)

**Processing Configuration:**
- `AVATAR_RESULT_STORAGE`: Storage method - 'base64', 'google_drive', or 'url' (default: base64)
- `AVATAR_PROCESSING_TIMEOUT`: Processing timeout in seconds (default: 30)

**Communication Mode:**
- `COMMUNICATION_MODE`: 'http', 'redis', or 'dual' (default: dual)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

### Development Workflow

1. Make changes to the code
2. Run tests to ensure functionality: `./run_tests.sh`
3. Build and run the service locally: `docker-compose up --build`
4. Test the API endpoints
5. Commit and push your changes

### CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment:

- **Automated Testing**: All tests are automatically run on every push and pull request
- **Code Quality**: Linting is performed to ensure code quality
- **Docker Image Building**: Docker images are automatically built and published to GitHub Container Registry
- **Deployment**: Changes to the main branch are automatically deployed to production

The CI/CD pipeline configuration can be found in `.github/workflows/ci-cd.yml`.

## Troubleshooting

### Common Issues

**Service won't start:**
- Check if port 5002 is already in use: `lsof -i :5002`
- Check if port 6379 (Redis) is already in use: `lsof -i :6379`
- Verify Docker network exists: `docker network ls | grep fogis-network`

**Network errors:**
- Ensure the fogis-network exists: `docker network create fogis-network`
- Or modify docker-compose.yml to remove the `external: true` flag

**Image processing errors:**
- Verify team IDs are valid
- Check logo URLs are accessible: `curl https://staticcdn.svenskfotboll.se/img/teams/7557.png`
- Check service logs: `docker-compose logs whatsapp-avatar-service`

**Redis connection issues:**
- Check Redis is running: `docker-compose ps fogis-redis`
- Test Redis connection: `docker exec -it fogis-redis redis-cli ping`
- Check Redis logs: `docker-compose logs fogis-redis`
- Verify REDIS_URL environment variable is correct

**Subscriber not receiving messages:**
- Check COMMUNICATION_MODE is set to 'dual' or 'redis'
- Verify REDIS_PUBSUB_ENABLED is 'true'
- Check subscriber stats in health endpoint: `curl http://localhost:5002/health`
- Verify correct channel names in configuration

**Publisher not sending results:**
- Check publisher stats in health endpoint
- Verify Redis connection is established
- Check for errors in service logs

### Monitoring

**Health Check:**
```bash
# Check service health
curl http://localhost:5002/health | jq

# Monitor Redis stats
docker exec -it fogis-redis redis-cli INFO stats

# Monitor pub/sub channels
docker exec -it fogis-redis redis-cli PUBSUB CHANNELS
```

**Logs:**
```bash
# Follow all logs
docker-compose logs -f

# Filter for errors
docker-compose logs | grep ERROR

# Check Redis pub/sub activity
docker-compose logs fogis-redis | grep publish
```

## Migration Guide

### Migrating from HTTP-only to Redis Pub/Sub

1. **Update docker-compose.yml** to include Redis service (already done in this version)

2. **Set environment variables:**
   ```bash
   COMMUNICATION_MODE=dual  # Enable both HTTP and Redis
   REDIS_PUBSUB_ENABLED=true
   ```

3. **Deploy updated service:**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify Redis integration:**
   ```bash
   curl http://localhost:5002/health | jq '.redis_enabled'
   ```

5. **Update consuming services** to use Redis pub/sub instead of HTTP

6. **Monitor both endpoints** during transition period

7. **Switch to Redis-only mode** once all consumers migrated:
   ```bash
   COMMUNICATION_MODE=redis
   ```

### Backward Compatibility

The service maintains backward compatibility with HTTP endpoints when running in `dual` mode (default). This allows gradual migration of consuming services from HTTP to Redis pub/sub.

## Performance

**Typical Processing Times:**
- Avatar creation: 100-500ms
- Redis message publishing: <10ms
- HTTP response: 150-600ms (includes network overhead)

**Scalability:**
- Multiple instances can subscribe to the same Redis channel
- Redis pub/sub supports thousands of messages per second
- Horizontal scaling supported in Redis mode

**Resource Usage:**
- Memory: ~100MB per instance
- CPU: Minimal (image processing is I/O bound)
- Redis: ~10MB for pub/sub (no persistence needed for messages)
