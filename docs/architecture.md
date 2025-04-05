# Team Logo Combiner Architecture

## System Overview

The Team Logo Combiner service is a Flask-based web application that combines two team logos into a single avatar image. The service is containerized using Docker and can be deployed using Docker Compose.

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                Docker Container                             │
│                                                             │
│  ┌─────────────┐        ┌──────────────────────────┐        │
│  │             │        │                          │        │
│  │  Flask App  │◄─────► │  Team Logo Combiner      │        │
│  │  (app.py)   │        │  (team_logo_combiner.py) │        │
│  │             │        │                          │        │
│  └─────────────┘        └──────────────────────────┘        │
│         ▲                           ▲                       │
│         │                           │                       │
│         ▼                           ▼                       │
│  ┌─────────────┐        ┌──────────────────────────┐        │
│  │             │        │                          │        │
│  │  HTTP API   │        │  Assets Directory        │        │
│  │  Endpoints  │        │  (Background Images)     │        │
│  │             │        │                          │        │
│  └─────────────┘        └──────────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Component Description

### Flask Application (app.py)
- Handles HTTP requests and responses
- Provides API endpoints for health checks and avatar creation
- Manages error handling and logging

### Team Logo Combiner (team_logo_combiner.py)
- Core image processing logic
- Fetches team logos from URLs
- Processes and combines images
- Handles image manipulation (cropping, resizing, etc.)

### Assets Directory
- Contains background images used in the avatar creation
- Mounted as a volume for easy updates without rebuilding

## Request Flow

1. Client sends a POST request to `/create_avatar` with team IDs
2. Flask app validates the request
3. Team logo URLs are constructed based on team IDs
4. Team Logo Combiner fetches the logos from the URLs
5. Images are processed and combined with a background
6. The resulting image is returned to the client

## Deployment

The service is deployed using Docker Compose, which manages:
- Container creation and lifecycle
- Network configuration
- Volume mounting
- Health checks
- Restart policies
