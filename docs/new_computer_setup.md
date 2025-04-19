# Setting Up TeamLogoCombiner on a New Computer

This guide will help you set up the TeamLogoCombiner project on a new computer.

## Prerequisites

Before you begin, ensure you have the following installed:

- Git
- Python 3.9 or higher
- Docker and Docker Compose (optional, but recommended for full functionality)

## Setup Steps

### 1. Clone the Repository

```bash
git clone https://github.com/timmybird/TeamLogoCombiner.git
cd TeamLogoCombiner
```

### 2. Automated Setup (Recommended)

Run the setup script to automatically configure your development environment:

```bash
./setup-dev-environment.sh
```

This script will:
- Check for required dependencies
- Create a Python virtual environment
- Install project dependencies
- Make scripts executable
- Create necessary directories

### 3. Manual Setup (Alternative)

If you prefer to set up manually:

1. Create a virtual environment:
   ```bash
   python3 -m venv .venv
   ```

2. Activate the virtual environment:
   ```bash
   # On macOS/Linux
   source .venv/bin/activate
   
   # On Windows
   .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Make scripts executable (macOS/Linux):
   ```bash
   chmod +x run_tests.sh
   chmod +x start-service.sh
   ```

5. Create logs directory:
   ```bash
   mkdir -p logs
   ```

## Running the Application

### Local Development

1. Activate the virtual environment (if not already activated):
   ```bash
   source .venv/bin/activate
   ```

2. Run the Flask application:
   ```bash
   python app.py
   ```

### Using Docker

1. Build and start the service:
   ```bash
   ./start-service.sh
   ```
   
   Or manually:
   ```bash
   docker-compose up --build
   ```

## Running Tests

Run the test suite:

```bash
./run_tests.sh
```

Or manually:

```bash
pytest
```

## Troubleshooting

If you encounter any issues during setup:

1. Ensure all prerequisites are installed
2. Check that you have the correct Python version
3. Verify that all environment variables are set correctly
4. For Docker-related issues, ensure Docker is running

For more detailed troubleshooting, refer to the main README.md file.
