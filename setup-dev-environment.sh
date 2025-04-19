#!/bin/bash
# Setup script for TeamLogoCombiner development environment
# This script sets up everything needed for development on a new machine

echo "Setting up TeamLogoCombiner development environment..."

# Check if Python 3.9+ is installed
python_version=$(python3 --version 2>&1 | awk '{print $2}')
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 9 ]); then
    echo "Error: Python 3.9 or higher is required."
    echo "Current version: $python_version"
    echo "Please install Python 3.9+ and try again."
    exit 1
fi

echo "✅ Python $python_version detected"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "⚠️ Docker is not installed. Some features may not work."
    echo "Please install Docker from https://docs.docker.com/get-docker/"
else
    echo "✅ Docker is installed"
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        echo "⚠️ Docker Compose is not installed. Some features may not work."
        echo "Please install Docker Compose from https://docs.docker.com/compose/install/"
    else
        echo "✅ Docker Compose is installed"
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Make scripts executable
echo "Making scripts executable..."
chmod +x run_tests.sh
chmod +x start-service.sh
chmod +x setup-dev-environment.sh
echo "✅ Scripts are now executable"

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    echo "Creating logs directory..."
    mkdir -p logs
    echo "✅ Logs directory created"
else
    echo "✅ Logs directory already exists"
fi

echo ""
echo "🎉 Setup complete! Your development environment is ready."
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "  ./run_tests.sh"
echo ""
echo "To start the service locally:"
echo "  ./start-service.sh"
echo ""
echo "To build and run with Docker:"
echo "  docker-compose up --build"
echo ""
