#!/bin/bash

# Stop any existing service and start a fresh instance
echo "Starting Team Logo Combiner service with Docker Compose..."

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if the fogis-network exists, create it if it doesn't
if ! docker network inspect fogis-network &> /dev/null; then
    echo "Creating fogis-network..."
    docker network create fogis-network
fi

# Build and start the service
echo "Building and starting the service..."
docker-compose up -d --build

# Check if the service started successfully
if [ $? -eq 0 ]; then
    echo "Service started successfully!"
    echo "The service is now running at http://localhost:5002"
    echo "To view logs, run: docker-compose logs -f"
else
    echo "Failed to start the service. Check the logs for more information."
    exit 1
fi
