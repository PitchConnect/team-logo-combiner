# Team Logo Combiner Service

A service that combines two team logos into a single avatar image with a background. This service is designed to create WhatsApp group avatars for matches between two teams.

## Project Status

This project includes comprehensive error handling, logging, and testing. It is ready for production use.

## Architecture

The service is built using the following technologies:

- **Flask**: Web framework for the API
- **Pillow**: Image processing library
- **Docker**: Containerization
- **Docker Compose**: Container orchestration

### Component Overview

- **app.py**: Flask application that handles HTTP requests
- **team_logo_combiner.py**: Core image processing logic
- **Dockerfile**: Container definition
- **docker-compose.yml**: Service configuration

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

### Project Structure

```
./
|-- app.py                  # Flask application
|-- team_logo_combiner.py   # Core image processing logic
|-- assets/                 # Background images and other assets
|   |-- grass_turf.jpg      # Default background image
|-- Dockerfile              # Container definition
|-- docker-compose.yml      # Service configuration
|-- requirements.txt        # Python dependencies
|-- tests/                  # Test suite
|   |-- conftest.py         # Test configuration
|   |-- test_app.py         # API tests
|   |-- test_team_logo_combiner.py  # Core logic tests
|-- run_tests.sh            # Script to run tests
```

### Running Tests

The project includes a comprehensive test suite. To run the tests:

```bash
# Run all tests
./run_tests.sh

# Run specific tests
pytest tests/test_app.py -v
```

### Customizing Assets

The service uses a background image located in the `assets` directory. You can replace this image without rebuilding the Docker image as the directory is mounted as a volume.

### Environment Variables

The following environment variables can be set in the docker-compose.yml file:

- `FLASK_ENV`: Set to "development" for debug mode or "production" for production mode
- `LOG_LEVEL`: Set the logging level (DEBUG, INFO, WARNING, ERROR)

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

- **Service won't start**: Check if port 5002 is already in use
- **Network errors**: Ensure the fogis-network exists or modify the docker-compose.yml file
- **Image processing errors**: Verify that the team IDs are valid and the logo URLs are accessible
