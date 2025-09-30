# Team Logo Combiner Architecture

## System Overview

The Team Logo Combiner service is a Flask-based web application with Redis pub/sub integration that combines two team logos into a single avatar image. The service supports both synchronous HTTP requests and asynchronous Redis messaging for flexible integration patterns.

**Version:** 2.2.0
**Redis Integration:** v1.0.0
**Enhanced Logging:** v2.1.0

### Dual-Mode Architecture (Default)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Team Logo Combiner Service Container                  │
│                                                                           │
│  ┌─────────────────────┐              ┌──────────────────────────┐      │
│  │   HTTP Server       │              │   Redis Subscriber       │      │
│  │   (Flask)           │              │   (Background Thread)    │      │
│  │   Port: 5002        │              │   Channel: requests      │      │
│  └──────────┬──────────┘              └───────────┬──────────────┘      │
│             │                                     │                      │
│             │ HTTP POST /create_avatar            │ Redis Message        │
│             │                                     │                      │
│             ▼                                     ▼                      │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              Avatar Request Handler                           │       │
│  │              (handle_avatar_request_from_redis)              │       │
│  └──────────────────────────┬───────────────────────────────────┘       │
│                             │                                            │
│                             ▼                                            │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              Team Logo Combiner Core                          │       │
│  │              (team_logo_combiner.py)                         │       │
│  │              - Download logos                                 │       │
│  │              - Process & combine images                       │       │
│  │              - Apply background                               │       │
│  └──────────────────────────┬───────────────────────────────────┘       │
│                             │                                            │
│                             ▼                                            │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              Redis Publisher                                  │       │
│  │              (AvatarResultPublisher)                         │       │
│  │              Channel: results                                 │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
         │                                              │
         │ HTTP Response (PNG)                          │ Redis Pub/Sub
         ▼                                              ▼
┌──────────────────┐                    ┌────────────────────────────────┐
│  HTTP Clients    │                    │  Redis Container               │
│  (Legacy)        │                    │  (fogis-redis)                 │
└──────────────────┘                    │  Port: 6379                    │
                                        │                                │
                                        │  Channels:                     │
                                        │  - fogis:avatars:requests      │
                                        │  - fogis:avatars:results       │
                                        │  - fogis:avatars:status        │
                                        └────────────┬───────────────────┘
                                                     │
                                                     ▼
                                        ┌────────────────────────────────┐
                                        │  Consuming Services            │
                                        │  - match-list-processor        │
                                        │  - Other microservices         │
                                        └────────────────────────────────┘
```

## Component Description

### Flask Application (app.py)
- **HTTP Server**: Handles synchronous HTTP requests (backward compatibility)
- **Redis Subscriber**: Background thread listening for avatar requests
- **Request Handler**: Unified handler for both HTTP and Redis requests
- **Health Check**: Enhanced endpoint with Redis statistics
- **Error Handling**: Comprehensive error handling with enhanced logging
- **Dual-Mode Support**: Configurable communication modes (HTTP/Redis/Dual)

### Redis Integration Module (src/redis_integration/)

#### Configuration (config.py)
- Environment-based configuration
- Channel name management
- Connection settings
- Feature flags (enabled/disabled)

#### Connection Manager (connection_manager.py)
- Redis connection pooling
- Health checking
- Automatic reconnection
- Graceful degradation

#### Publisher (publisher.py)
- Publishes avatar results to Redis
- Publishes service status updates
- Message formatting and serialization
- Statistics tracking
- Detailed message logging

#### Subscriber (subscriber.py)
- Subscribes to avatar request channel
- Background thread for message processing
- Message validation and parsing
- Error handling and retry logic
- Statistics tracking

#### Message Formatter (message_formatter.py)
- Standardized message schemas
- JSON serialization/deserialization
- Message validation
- Timestamp management
- UUID generation

### Team Logo Combiner (team_logo_combiner.py)
- Core image processing logic
- Fetches team logos from external URLs
- Image sanitization and validation
- Processes and combines images
- Handles image manipulation (cropping, resizing, transparency)
- Background image composition

### Assets Directory
- Contains background images used in avatar creation
- Mounted as a volume for easy updates without rebuilding
- Default: grass_turf.jpg

## Communication Modes

The service supports three communication modes via the `COMMUNICATION_MODE` environment variable:

### 1. Dual Mode (Default - Recommended)
- **Value**: `COMMUNICATION_MODE=dual`
- **Behavior**: Both HTTP and Redis pub/sub enabled
- **Use Case**: Transition period, backward compatibility
- **Benefits**: Allows gradual migration of consuming services

### 2. HTTP Mode (Legacy)
- **Value**: `COMMUNICATION_MODE=http`
- **Behavior**: Only HTTP endpoints active
- **Use Case**: Legacy deployments, no Redis available
- **Limitations**: Synchronous only, no pub/sub benefits

### 3. Redis Mode (Recommended for Production)
- **Value**: `COMMUNICATION_MODE=redis`
- **Behavior**: Only Redis pub/sub, no HTTP server
- **Use Case**: Fully migrated microservices architecture
- **Benefits**: Lower resource usage, better scalability

## Request Flow

### HTTP Request Flow (Legacy/Dual Mode)

```
1. Client → HTTP POST /create_avatar
   ↓
2. Flask App validates request
   ↓
3. Construct logo URLs from team IDs
   ↓
4. Team Logo Combiner downloads logos
   ↓
5. Process & combine images
   ↓
6. Return PNG image in HTTP response
```

### Redis Pub/Sub Flow (Redis/Dual Mode)

```
1. Service publishes request to fogis:avatars:requests
   {
     "message_id": "uuid",
     "payload": {
       "team1_id": "7557",
       "team2_id": "9590"
     }
   }
   ↓
2. Subscriber receives message
   ↓
3. Validate message format
   ↓
4. Extract team IDs
   ↓
5. Construct logo URLs
   ↓
6. Team Logo Combiner downloads logos
   ↓
7. Process & combine images
   ↓
8. Convert to base64
   ↓
9. Publisher publishes result to fogis:avatars:results
   {
     "request_id": "uuid",
     "payload": {
       "status": "success",
       "avatar_data": "base64...",
       "processing_time_ms": 1234
     }
   }
   ↓
10. Consuming service receives result
```

## Message Schemas

### Avatar Request Message

```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-09-30T12:34:56.789Z",
  "source": "match-list-processor",
  "version": "1.0",
  "type": "avatar_request",
  "payload": {
    "team1_id": "7557",
    "team2_id": "9590",
    "team1_organization_id": "12345",
    "team2_organization_id": "67890",
    "match_id": "match-123",
    "priority": "normal",
    "callback_channel": "fogis:avatars:results",
    "metadata": {
      "requester": "match-processor",
      "request_context": "whatsapp_group_creation"
    }
  }
}
```

### Avatar Result Message (Success)

```json
{
  "message_id": "660e8400-e29b-41d4-a716-446655440001",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-09-30T12:34:57.123Z",
  "source": "team-logo-combiner",
  "version": "1.0",
  "type": "avatar_result",
  "payload": {
    "status": "success",
    "team1_id": "7557",
    "team2_id": "9590",
    "avatar_data": "iVBORw0KGgoAAAANSUhEUgAA...",
    "processing_time_ms": 1234,
    "metadata": {
      "image_size": "512x512",
      "format": "PNG",
      "background": "grass_turf.jpg"
    }
  }
}
```

### Avatar Result Message (Error)

```json
{
  "message_id": "770e8400-e29b-41d4-a716-446655440002",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-09-30T12:34:57.456Z",
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

## Deployment Architecture

### Docker Compose Setup

The service is deployed using Docker Compose with two containers:

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Compose                           │
│                                                              │
│  ┌────────────────────────────────────────────────┐         │
│  │  whatsapp-avatar-service                       │         │
│  │  - Image: whatsapp-avatar-app                  │         │
│  │  - Port: 5002:5002                             │         │
│  │  - Depends on: fogis-redis                     │         │
│  │  - Environment: COMMUNICATION_MODE=dual        │         │
│  │  - Volumes: ./assets:/app/assets               │         │
│  └────────────────────────────────────────────────┘         │
│                         │                                    │
│                         │ Redis Connection                   │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────┐         │
│  │  fogis-redis                                   │         │
│  │  - Image: redis:7-alpine                       │         │
│  │  - Port: 6379:6379                             │         │
│  │  - Volume: redis-data:/data                    │         │
│  │  - Command: redis-server --appendonly yes      │         │
│  └────────────────────────────────────────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         │ External Network                   │
         ▼                                    ▼
┌──────────────────┐              ┌──────────────────┐
│  fogis-network   │              │  Persistent      │
│  (external)      │              │  Volume          │
└──────────────────┘              │  redis-data      │
                                  └──────────────────┘
```

### Container Management

**whatsapp-avatar-service:**
- Container creation and lifecycle
- Network configuration (fogis-network)
- Volume mounting (assets directory)
- Health checks (HTTP endpoint)
- Restart policies (unless-stopped)
- Environment variable injection
- Dependency management (waits for Redis)

**fogis-redis:**
- Redis 7.x Alpine (lightweight)
- AOF persistence enabled
- Health checks (redis-cli ping)
- Data persistence via volume
- Automatic restart on failure

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     fogis-network (Bridge)                   │
│                                                              │
│  ┌──────────────────┐              ┌──────────────────┐    │
│  │  avatar-service  │◄────────────►│  fogis-redis     │    │
│  │  (5002)          │   Internal   │  (6379)          │    │
│  └────────┬─────────┘   Network    └──────────────────┘    │
│           │                                                  │
└───────────┼──────────────────────────────────────────────────┘
            │
            │ Port Mapping
            ▼
    ┌───────────────┐
    │  Host Network │
    │  Port 5002    │
    │  Port 6379    │
    └───────────────┘
```

## Scalability and Performance

### Horizontal Scaling

**Redis Mode (Recommended):**
```
┌─────────────────┐
│  Load Balancer  │
│  (Redis)        │
└────────┬────────┘
         │
         ├──────────┬──────────┬──────────┐
         ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │Instance│ │Instance│ │Instance│ │Instance│
    │   1    │ │   2    │ │   3    │ │   N    │
    └────────┘ └────────┘ └────────┘ └────────┘
         │          │          │          │
         └──────────┴──────────┴──────────┘
                     │
                     ▼
              ┌────────────┐
              │   Redis    │
              │  (Pub/Sub) │
              └────────────┘
```

**Benefits:**
- Multiple instances can subscribe to the same channel
- Automatic load distribution via Redis
- No session affinity required
- Stateless service design

### Performance Characteristics

**Processing Times:**
- Image download: 50-200ms (network dependent)
- Image processing: 50-300ms
- Total avatar creation: 100-500ms
- Redis publish: <10ms
- HTTP overhead: 50-100ms

**Throughput:**
- Single instance: ~10-20 requests/second
- Redis pub/sub: 1000s of messages/second
- Bottleneck: External logo downloads

**Resource Usage:**
- Memory: ~100MB per instance
- CPU: Low (I/O bound)
- Redis memory: ~10MB (pub/sub only, no persistence needed)

## Error Handling and Resilience

### Graceful Degradation

1. **Redis Unavailable:**
   - Service continues in HTTP-only mode (if dual mode)
   - Logs warnings about Redis connection
   - Retries connection automatically
   - No service downtime

2. **Logo Download Failures:**
   - Retry logic with exponential backoff
   - Maximum 3 retry attempts
   - Error result published to Redis
   - Detailed error information in response

3. **Image Processing Errors:**
   - Comprehensive error handling
   - Error results published with details
   - Service remains operational
   - Logging for debugging

### Monitoring and Health Checks

**Health Endpoint (`/health`):**
```json
{
  "status": "healthy",
  "redis_enabled": true,
  "redis_connected": true,
  "subscriber_stats": {
    "running": true,
    "stats": {
      "total_received": 100,
      "successful_processed": 95,
      "failed_processed": 5
    }
  },
  "publisher_stats": {
    "total_published": 95,
    "successful_publishes": 95,
    "failed_publishes": 0
  }
}
```

**Metrics to Monitor:**
- Redis connection status
- Message processing rate
- Error rate
- Processing latency
- Queue depth (if using Redis Streams in future)

## Security Considerations

1. **Redis Security:**
   - Internal network only (not exposed externally)
   - No authentication required (trusted network)
   - Consider Redis AUTH for production

2. **Input Validation:**
   - Team ID validation
   - Message schema validation
   - URL sanitization

3. **Resource Limits:**
   - Processing timeout (30s default)
   - Image size limits
   - Memory limits via Docker

## Future Enhancements

1. **Redis Streams:**
   - Replace pub/sub with Streams for guaranteed delivery
   - Consumer groups for load balancing
   - Message persistence and replay

2. **Caching:**
   - Cache generated avatars in Redis
   - TTL-based expiration
   - Reduce redundant processing

3. **Metrics:**
   - Prometheus metrics export
   - Grafana dashboards
   - Alert rules

4. **Distributed Tracing:**
   - OpenTelemetry integration
   - Request correlation across services
   - Performance profiling
