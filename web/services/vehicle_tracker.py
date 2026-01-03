"""
Production-ready vehicle tracking service using Redis for state management.

Implements deterministic tracking logic with 30-second windows, path recording,
and last-seen location determination.
"""

import json
import os
import redis
import time
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
from pathlib import Path
import logging
import logging.handlers
from threading import Lock

# Configure logging
log_dir = Path(__file__).resolve().parent.parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

event_logger = logging.getLogger("vehicle_events")
event_logger.setLevel(logging.INFO)
event_handler = logging.handlers.RotatingFileHandler(
    log_dir / "vehicle_events.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
event_formatter = logging.Formatter(
    '%(message)s'  # JSON format, no extra formatting
)
event_handler.setFormatter(event_formatter)
event_logger.addHandler(event_handler)
event_logger.propagate = False

# Redis connection
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
TRACKER_WINDOW_SECONDS = int(os.getenv("TRACKER_WINDOW_SECONDS", "30"))
ENTRY_CAMERA = os.getenv("ENTRY_CAMERA", "camera1")  # Default entry camera

# Redis client (thread-safe)
_redis_client = None
_redis_lock = Lock()

def get_redis_client():
    """Get or create Redis client (singleton pattern)."""
    global _redis_client
    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                _redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                try:
                    _redis_client.ping()
                except redis.ConnectionError as e:
                    raise RuntimeError(f"Failed to connect to Redis: {e}")
    return _redis_client


class VehicleTracker:
    """Vehicle tracking service with Redis-backed state management."""
    
    def __init__(self):
        self.redis = get_redis_client()
        self.window_seconds = TRACKER_WINDOW_SECONDS
        self.entry_camera = ENTRY_CAMERA
        self._setup_keyspace_notifications()
    
    def _setup_keyspace_notifications(self):
        """Configure Redis keyspace notifications for timer expiry."""
        try:
            # Enable keyspace notifications for expired keys
            self.redis.config_set('notify-keyspace-events', 'Ex')
        except redis.RedisError as e:
            logging.warning(f"Could not configure keyspace notifications: {e}")
            logging.info("Falling back to background worker for timer expiry")
    
    def normalize_plate(self, plate: str) -> str:
        """Normalize license plate: uppercase, remove spaces."""
        return plate.upper().replace(" ", "").strip()
    
    def is_entry_camera(self, camera_id: str) -> bool:
        """Check if camera is the entry camera."""
        return camera_id == self.entry_camera
    
    def _get_vehicle_key(self, plate: str) -> str:
        """Get Redis key for vehicle record."""
        return f"car:{plate}"
    
    def _get_timer_key(self, plate: str) -> str:
        """Get Redis key for vehicle timer."""
        return f"car:{plate}:timer"
    
    def _get_camera_key(self, camera_id: str) -> str:
        """Get Redis key for camera metadata."""
        return f"camera:{camera_id}"
    
    def _log_event(self, plate: str, camera_id: str, old_status: str, 
                   new_status: str, reason: str, detections: int, path_len: int):
        """Log vehicle event to structured log file."""
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "plate": plate,
            "camera_id": camera_id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
            "detections": detections,
            "path_len": path_len
        }
        event_logger.info(json.dumps(event))
    
    def _get_vehicle_record(self, plate: str) -> Optional[Dict]:
        """Get vehicle record from Redis."""
        key = self._get_vehicle_key(plate)
        data = self.redis.hgetall(key)
        if not data:
            return None
        
        # Parse JSON fields
        if data.get('path_history'):
            data['path_history'] = json.loads(data['path_history'])
        else:
            data['path_history'] = []
        
        return data
    
    def _set_vehicle_record(self, plate: str, record: Dict):
        """Store vehicle record in Redis."""
        key = self._get_vehicle_key(plate)
        # Convert path_history to JSON string
        record_copy = record.copy()
        if 'path_history' in record_copy:
            record_copy['path_history'] = json.dumps(record_copy['path_history'])
        
        # Use pipeline for atomic update
        pipe = self.redis.pipeline()
        pipe.hset(key, mapping=record_copy)
        pipe.execute()
    
    def _reset_timer(self, plate: str):
        """Reset vehicle timer TTL to window_seconds."""
        timer_key = self._get_timer_key(plate)
        self.redis.set(timer_key, "1", ex=self.window_seconds)
    
    def _cancel_timer(self, plate: str):
        """Cancel vehicle timer."""
        timer_key = self._get_timer_key(plate)
        self.redis.delete(timer_key)
    
    def _move_to_archive(self, plate: str, record: Dict):
        """Move vehicle record to archive."""
        archive_key = f"vehicle_archive:{plate}"
        record['archived_ts'] = datetime.now(timezone.utc).isoformat()
        self.redis.hset(archive_key, mapping={
            k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
            for k, v in record.items()
        })
        # Set archive retention (12 hours)
        self.redis.expire(archive_key, 12 * 3600)
        
        # Remove from active tracking
        self.redis.delete(self._get_vehicle_key(plate))
        self.redis.delete(self._get_timer_key(plate))
    
    def on_detect(self, plate: str, camera_id: str, ts: str) -> Dict:
        """
        Handle vehicle detection event.
        
        Returns:
            Dict with status, action, and vehicle info
        """
        plate = self.normalize_plate(plate)
        now = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        now_ts = now.timestamp()
        
        # Use Redis WATCH for optimistic locking
        vehicle_key = self._get_vehicle_key(plate)
        timer_key = self._get_timer_key(plate)
        
        # Retry loop for concurrent updates
        max_retries = 5
        for attempt in range(max_retries):
            try:
                pipe = self.redis.pipeline()
                pipe.watch(vehicle_key, timer_key)
                
                rec = self._get_vehicle_record(plate)
                
                if not rec:
                    # New vehicle - ENTRY
                    path_entry = {"camera_id": camera_id, "ts": ts}
                    new_record = {
                        "plate": plate,
                        "status": "ENTERED",
                        "last_seen_camera": camera_id,
                        "last_seen_ts": ts,
                        "first_seen_ts": ts,
                        "detections": 1,
                        "path_history": json.dumps([path_entry])
                    }
                    
                    pipe.multi()
                    pipe.hset(vehicle_key, mapping=new_record)
                    pipe.set(timer_key, "1", ex=self.window_seconds)
                    pipe.execute()
                    
                    self._log_event(plate, camera_id, "NONE", "ENTERED", 
                                  "ENTRY_SUCCESS", 1, 1)
                    
                    return {
                        "status": "ok",
                        "action": "ENTRY",
                        "plate": plate,
                        "last_seen": camera_id,
                        "msg": f"Entry recorded. Timer started {self.window_seconds}s"
                    }
                
                else:
                    # Existing vehicle
                    old_status = rec.get('status', 'UNKNOWN')
                    path_history = rec.get('path_history', [])
                    last_seen_camera = rec.get('last_seen_camera')
                    last_seen_ts = rec.get('last_seen_ts')
                    detections = int(rec.get('detections', 0))
                    
                    # Deduplicate: ignore if same camera within 0.5 seconds
                    if camera_id == last_seen_camera and last_seen_ts:
                        last_ts = datetime.fromisoformat(last_seen_ts.replace('Z', '+00:00')).timestamp()
                        if (now_ts - last_ts) < 0.5:
                            return {
                                "status": "ok",
                                "action": "DUPLICATE",
                                "plate": plate,
                                "msg": "Duplicate detection ignored"
                            }
                    
                    pipe.multi()
                    
                    if camera_id == last_seen_camera:
                        # Same camera detection
                        if (old_status in ['ENTERED', 'MOVING'] and 
                            self.is_entry_camera(camera_id) and 
                            len(path_history) == 1):
                            # Exit condition: detected again at entry camera with only one detection
                            # Check if within window
                            first_ts = datetime.fromisoformat(rec.get('first_seen_ts', ts).replace('Z', '+00:00')).timestamp()
                            if (now_ts - first_ts) <= self.window_seconds:
                                # EXIT
                                rec['status'] = 'EXITED'
                                rec['last_seen_ts'] = ts
                                rec['detections'] = detections + 1
                                
                                pipe.hset(vehicle_key, mapping={
                                    k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
                                    for k, v in rec.items()
                                })
                                pipe.delete(timer_key)
                                pipe.execute()
                                
                                self._log_event(plate, camera_id, old_status, "EXITED",
                                              "EXIT_DETECTED", detections + 1, len(path_history))
                                
                                # Move to archive
                                self._move_to_archive(plate, rec)
                                
                                return {
                                    "status": "ok",
                                    "action": "EXIT",
                                    "plate": plate,
                                    "msg": "Vehicle exited, removed from active tracking"
                                }
                        
                        # Update same camera
                        rec['last_seen_ts'] = ts
                        rec['detections'] = detections + 1
                        path_entry = {"camera_id": camera_id, "ts": ts}
                        if path_history and path_history[-1].get('camera_id') != camera_id:
                            path_history.append(path_entry)
                        elif not path_history:
                            path_history = [path_entry]
                        rec['path_history'] = path_history
                        
                        pipe.hset(vehicle_key, mapping={
                            k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
                            for k, v in rec.items()
                        })
                        pipe.expire(timer_key, self.window_seconds)
                        pipe.execute()
                        
                        self._log_event(plate, camera_id, old_status, old_status,
                                      "UPDATE_SAME_CAMERA", detections + 1, len(path_history))
                        
                        return {
                            "status": "ok",
                            "action": "UPDATE_SAME_CAMERA",
                            "plate": plate,
                            "last_seen": camera_id,
                            "msg": "Updated same camera detection"
                        }
                    
                    else:
                        # Different camera - MOVEMENT
                        path_entry = {"camera_id": camera_id, "ts": ts}
                        path_history.append(path_entry)
                        
                        rec['last_seen_camera'] = camera_id
                        rec['last_seen_ts'] = ts
                        rec['status'] = 'MOVING'
                        rec['detections'] = detections + 1
                        rec['path_history'] = path_history
                        
                        pipe.hset(vehicle_key, mapping={
                            k: (json.dumps(v) if isinstance(v, (dict, list)) else str(v))
                            for k, v in rec.items()
                        })
                        pipe.expire(timer_key, self.window_seconds)
                        pipe.execute()
                        
                        path_str = " -> ".join([p['camera_id'] for p in path_history])
                        self._log_event(plate, camera_id, old_status, "MOVING",
                                      "MOVED", detections + 1, len(path_history))
                        
                        return {
                            "status": "ok",
                            "action": "MOVED",
                            "plate": plate,
                            "path": [p['camera_id'] for p in path_history],
                            "last_seen": camera_id,
                            "msg": "Path updated"
                        }
            
            except redis.WatchError:
                # Retry on concurrent modification
                if attempt < max_retries - 1:
                    time.sleep(0.01 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise RuntimeError(f"Failed to update vehicle {plate} after {max_retries} retries")
        
        raise RuntimeError("Unexpected error in on_detect")
    
    def on_timer_expire(self, plate: str) -> Dict:
        """
        Handle timer expiration for a vehicle.
        
        Called when car:<plate>:timer expires.
        """
        plate = self.normalize_plate(plate)
        rec = self._get_vehicle_record(plate)
        
        if not rec:
            # Already archived or doesn't exist
            return {"status": "ok", "action": "NO_ACTION", "msg": "Vehicle not found"}
        
        old_status = rec.get('status', 'UNKNOWN')
        path_history = rec.get('path_history', [])
        last_seen_camera = rec.get('last_seen_camera')
        
        # Determine new status
        if old_status == 'ENTERED' and len(path_history) == 1:
            # No further camera - parked near entry
            new_status = f"PARKED_NEAR_{last_seen_camera}"
        elif old_status == 'MOVING':
            # Was moving, now parked at last camera
            new_status = "PARKED"
        else:
            new_status = "PARKED"
        
        rec['status'] = new_status
        rec['last_seen_ts'] = datetime.now(timezone.utc).isoformat()
        
        # Persist event
        self._log_event(plate, last_seen_camera, old_status, new_status,
                       "TIMER_EXPIRED", int(rec.get('detections', 0)), len(path_history))
        
        # Move to archive
        self._move_to_archive(plate, rec)
        
        return {
            "status": "ok",
            "action": "PARKED",
            "plate": plate,
            "last_seen_camera": last_seen_camera,
            "final_status": new_status,
            "msg": f"Vehicle marked as {new_status}"
        }
    
    def get_vehicle(self, plate: str) -> Optional[Dict]:
        """Get current vehicle state."""
        plate = self.normalize_plate(plate)
        rec = self._get_vehicle_record(plate)
        if rec:
            # Check if timer is still active
            timer_key = self._get_timer_key(plate)
            ttl = self.redis.ttl(timer_key)
            rec['timer_remaining_seconds'] = max(0, ttl) if ttl > 0 else 0
        return rec
    
    def get_active_vehicles(self) -> List[Dict]:
        """Get all actively tracked vehicles."""
        pattern = "car:*"
        keys = self.redis.keys(pattern)
        vehicles = []
        for key in keys:
            if ":timer" not in key:  # Skip timer keys
                plate = key.replace("car:", "")
                vehicle = self.get_vehicle(plate)
                if vehicle:
                    vehicles.append(vehicle)
        return vehicles
    
    def set_camera_metadata(self, camera_id: str, lat: float, lon: float, name: str):
        """Store camera metadata."""
        key = self._get_camera_key(camera_id)
        self.redis.hset(key, mapping={
            "camera_id": camera_id,
            "lat": str(lat),
            "lon": str(lon),
            "name": name
        })
    
    def get_camera_metadata(self, camera_id: str) -> Optional[Dict]:
        """Get camera metadata."""
        key = self._get_camera_key(camera_id)
        data = self.redis.hgetall(key)
        if data:
            data['lat'] = float(data.get('lat', 0))
            data['lon'] = float(data.get('lon', 0))
        return data if data else None

