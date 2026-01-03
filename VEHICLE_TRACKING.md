# Vehicle Tracking System Documentation

## Overview

The vehicle tracking system implements a production-ready, Redis-based ALPR tracking logic with deterministic state management, 30-second tracking windows, path recording, and last-seen location determination.

## Architecture

- **Backend**: Flask (Python)
- **State Store**: Redis with TTL-based timers
- **Notifications**: Pluggable webhook system (Telegram, generic webhooks)
- **Logging**: Structured JSON logs to `logs/vehicle_events.log`

## Setup

### Prerequisites

1. **Redis**: Required for state management
   ```bash
   # Install Redis locally
   # macOS:
   brew install redis
   brew services start redis
   
   # Linux:
   sudo apt-get install redis-server
   sudo systemctl start redis
   ```

2. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Tracking Configuration
TRACKER_WINDOW_SECONDS=30  # Default: 30 seconds
ENTRY_CAMERA=camera1        # Default entry camera ID

# Notification Configuration (optional)
NOTIFY_WEBHOOK=https://your-webhook-url.com/notify
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## API Endpoints

### POST /api/detections

Submit a vehicle detection event.

**Request:**
```json
{
  "camera_id": "camera1",
  "plate": "MH20EE7598",
  "ts": "2025-11-07T03:36:15Z"
}
```

**Response Examples:**

Entry:
```json
{
  "status": "ok",
  "action": "ENTRY",
  "plate": "MH20EE7598",
  "last_seen": "camera1",
  "msg": "Entry recorded. Timer started 30s"
}
```

Movement:
```json
{
  "status": "ok",
  "action": "MOVED",
  "plate": "MH20EE7598",
  "path": ["camera1", "camera2"],
  "last_seen": "camera2",
  "msg": "Path updated"
}
```

Exit:
```json
{
  "status": "ok",
  "action": "EXIT",
  "plate": "MH20EE7598",
  "msg": "Vehicle exited, removed from active tracking"
}
```

**Example cURL:**
```bash
curl -X POST http://localhost:5002/api/detections \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "camera1",
    "plate": "MH20EE7598",
    "ts": "2025-11-07T03:36:15Z"
  }'
```

### GET /api/vehicle/:plate

Get current vehicle state and path history.

**Response:**
```json
{
  "status": "ok",
  "vehicle": {
    "plate": "MH20EE7598",
    "status": "MOVING",
    "last_seen_camera": "camera2",
    "last_seen_ts": "2025-11-07T03:36:20Z",
    "first_seen_ts": "2025-11-07T03:36:15Z",
    "detections": 2,
    "path_history": [
      {"camera_id": "camera1", "ts": "2025-11-07T03:36:15Z"},
      {"camera_id": "camera2", "ts": "2025-11-07T03:36:20Z"}
    ],
    "timer_remaining_seconds": 25.5
  }
}
```

### POST /api/camera/:id

Update camera metadata (latitude, longitude, name).

**Request:**
```json
{
  "lat": 12.968194,
  "lng": 79.155917,
  "name": "Main Gate"
}
```

### GET /api/vehicles/active

List all actively tracked vehicles.

**Response:**
```json
{
  "status": "ok",
  "count": 2,
  "vehicles": [
    {
      "plate": "MH20EE7598",
      "status": "MOVING",
      "last_seen_camera": "camera2",
      ...
    }
  ]
}
```

## Tracking Logic

### State Machine

- **IDLE**: Vehicle not tracked
- **ENTERED**: First detection at entry camera
- **MOVING**: Vehicle detected at different camera
- **PARKED**: Timer expired, vehicle parked
- **PARKED_NEAR_<camera>**: Timer expired at entry camera with no movement
- **EXITED**: Vehicle detected again at entry camera (exit)

### Decision Rules

1. **New Detection (Entry)**:
   - Create record with status `ENTERED`
   - Start 30-second timer
   - Log `ENTRY_SUCCESS`
   - Send notification

2. **Same Camera Detection**:
   - If entry camera + only 1 path entry + within window → **EXIT**
   - Otherwise → Update last_seen_ts, increment detections, reset timer

3. **Different Camera Detection**:
   - Append to path_history
   - Set status to `MOVING`
   - Reset timer to 30 seconds
   - Log `MOVED`

4. **Timer Expiry**:
   - If `ENTERED` + 1 path entry → `PARKED_NEAR_<camera>`
   - If `MOVING` → `PARKED` at last camera
   - Move to archive
   - Send notification

### Deduplication

Detections within 0.5 seconds at the same camera are treated as duplicates and ignored.

## Data Model

### Redis Keys

- `car:<plate>`: Vehicle record (hash)
- `car:<plate>:timer`: Timer key with TTL (string)
- `camera:<id>`: Camera metadata (hash)
- `vehicle_archive:<plate>`: Archived vehicle record (hash, 12h TTL)

### Vehicle Record Structure

```json
{
  "plate": "MH20EE7598",
  "status": "MOVING",
  "last_seen_camera": "camera2",
  "last_seen_ts": "2025-11-07T03:36:20Z",
  "first_seen_ts": "2025-11-07T03:36:15Z",
  "detections": 2,
  "path_history": "[{\"camera_id\":\"camera1\",\"ts\":\"...\"}, ...]"
}
```

## Timer Management

The system uses Redis TTL for timer management:

1. **Redis Keyspace Notifications**: Primary method (if enabled)
2. **Background Worker**: Fallback polling every 2 seconds

Timer keys expire after `TRACKER_WINDOW_SECONDS` (default: 30s), triggering `on_timer_expire()`.

## Logging

All events are logged to `logs/vehicle_events.log` in JSON format:

```json
{
  "ts": "2025-11-07T03:36:15Z",
  "plate": "MH20EE7598",
  "camera_id": "camera1",
  "old_status": "NONE",
  "new_status": "ENTERED",
  "reason": "ENTRY_SUCCESS",
  "detections": 1,
  "path_len": 1
}
```

## Notifications

The system supports multiple notification backends:

1. **Telegram Bot**: Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
2. **Generic Webhook**: Set `NOTIFY_WEBHOOK`


Notifications are sent for:
- Entry events
- Exit events
- Parked/last-seen events

## Testing

Run unit and integration tests:

```bash
# Install test dependencies
pip install pytest pytest-redis

# Run tests
cd web
pytest tests/test_tracking.py -v

# Run with coverage
pytest tests/test_tracking.py --cov=services --cov-report=html
```

### Test Scenarios

1. **Entry → No Next → Last Seen**:
   - POST detection at cam0
   - Wait >30s or simulate timer expiry
   - Verify `PARKED_NEAR_cam0` status

2. **Entry → Seen cam1 → Path Recorded**:
   - POST detection at cam0
   - POST detection at cam1 within 30s
   - Verify path_history = [cam0, cam1], status=MOVING

3. **Entry → Seen Again cam0 → Exit**:
   - POST detection at cam0
   - POST detection at cam0 again within 30s
   - Verify EXITED status and removal from active list

## Running the System

1. **Start Redis**:
   ```bash
   # macOS
   brew services start redis
   
   # Linux
   sudo systemctl start redis
   ```

2. **Start Backend**:
   ```bash
   cd web
   source ../.venv/bin/activate
   python app.py
   ```

3. **Verify**:
   ```bash
   # Check Redis connection
   redis-cli ping
   
   # Test detection endpoint
   curl -X POST http://localhost:5002/api/detections \
     -H "Content-Type: application/json" \
     -d '{"camera_id":"camera1","plate":"TEST123"}'
   ```

## Migration from Legacy Mode

The system maintains backward compatibility with the legacy in-memory tracking. If Redis is unavailable, the system falls back to legacy mode automatically.

To migrate existing data:
1. Ensure Redis is running
2. Restart the backend
3. The system will automatically use Redis-based tracking

## Troubleshooting

### Redis Connection Errors

- Verify Redis is running: `redis-cli ping`
- Check `REDIS_HOST` and `REDIS_PORT` environment variables
- Check firewall/network settings

### Timer Not Expiring

- Verify keyspace notifications: `redis-cli CONFIG GET notify-keyspace-events`
- Check timer worker is running (check logs)
- Manually test: `redis-cli SET car:TEST:timer 1 EX 5`

### Notifications Not Sending

- Check environment variables are set correctly
- Verify webhook URLs are accessible
- Check logs for notification errors

## Performance Considerations

- **Concurrency**: Uses Redis WATCH for optimistic locking
- **Scalability**: Multiple backend instances can share Redis state
- **Memory**: Archived records expire after 12 hours
- **Rate Limiting**: Consider adding rate limiting for production

## Security Notes

- Do not commit `.env` files with secrets
- Use environment variables or secret management for tokens
- Enable Redis authentication in production
- Use HTTPS for webhook endpoints





