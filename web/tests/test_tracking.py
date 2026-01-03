"""
Unit and integration tests for vehicle tracking logic.

Tests cover:
- Entry -> no next -> last-seen
- Entry -> seen cam1 within 30s -> path recorded
- Entry -> seen again cam0 within 30s -> exit
"""

import pytest
import json
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import redis

# Import the tracker
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.vehicle_tracker import VehicleTracker, get_redis_client
from services.notifier import Notifier


@pytest.fixture
def mock_redis():
    """Create a mock Redis client for testing."""
    mock_redis = Mock(spec=redis.Redis)
    mock_redis.ping.return_value = True
    mock_redis.config_set.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.keys.return_value = []
    mock_redis.pipeline.return_value = Mock()
    return mock_redis


@pytest.fixture
def tracker(mock_redis):
    """Create VehicleTracker instance with mocked Redis."""
    with patch('services.vehicle_tracker.get_redis_client', return_value=mock_redis):
        tracker = VehicleTracker()
        tracker.redis = mock_redis
        return tracker


@pytest.fixture
def sample_timestamp():
    """Generate sample ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


class TestEntryNoNext:
    """Test: Entry -> no next -> last-seen"""
    
    def test_entry_creates_record(self, tracker, sample_timestamp):
        """Test that entry creates a new vehicle record."""
        tracker.redis.hgetall.return_value = {}  # No existing record
        tracker.redis.pipeline.return_value.__enter__.return_value = Mock()
        pipe = tracker.redis.pipeline.return_value.__enter__.return_value
        pipe.watch.return_value = None
        pipe.multi.return_value = None
        pipe.hset.return_value = None
        pipe.set.return_value = None
        pipe.execute.return_value = [True, True]
        
        result = tracker.on_detect("MH20EE7598", "camera1", sample_timestamp)
        
        assert result["status"] == "ok"
        assert result["action"] == "ENTRY"
        assert result["plate"] == "MH20EE7598"
        assert "Timer started" in result["msg"]
        
        # Verify Redis calls
        pipe.hset.assert_called_once()
        pipe.set.assert_called_once()
    
    def test_timer_expire_sets_parked(self, tracker, sample_timestamp):
        """Test that timer expiry sets PARKED_NEAR status."""
        # Setup: vehicle in ENTERED state with single path entry
        path_history = [{"camera_id": "camera1", "ts": sample_timestamp}]
        vehicle_record = {
            "plate": "MH20EE7598",
            "status": "ENTERED",
            "last_seen_camera": "camera1",
            "last_seen_ts": sample_timestamp,
            "first_seen_ts": sample_timestamp,
            "detections": 1,
            "path_history": json.dumps(path_history)
        }
        
        tracker.redis.hgetall.return_value = vehicle_record
        tracker.redis.delete.return_value = True
        tracker.redis.hset.return_value = True
        tracker.redis.expire.return_value = True
        
        result = tracker.on_timer_expire("MH20EE7598")
        
        assert result["status"] == "ok"
        assert result["action"] == "PARKED"
        assert "PARKED_NEAR" in result.get("final_status", "")


class TestEntryToNextCamera:
    """Test: Entry -> seen cam1 within 30s -> path recorded"""
    
    def test_entry_then_movement(self, tracker, sample_timestamp):
        """Test vehicle moving from camera1 to camera2."""
        base_time = datetime.now(timezone.utc)
        t0 = base_time.isoformat()
        t1 = (base_time + timedelta(seconds=5)).isoformat()
        
        # First detection - entry
        tracker.redis.hgetall.return_value = {}
        pipe = tracker.redis.pipeline.return_value.__enter__.return_value
        pipe.watch.return_value = None
        pipe.multi.return_value = None
        pipe.execute.return_value = [True, True]
        
        result1 = tracker.on_detect("MH20EE7598", "camera1", t0)
        assert result1["action"] == "ENTRY"
        
        # Second detection - movement
        path_history = [{"camera_id": "camera1", "ts": t0}]
        vehicle_record = {
            "plate": "MH20EE7598",
            "status": "ENTERED",
            "last_seen_camera": "camera1",
            "last_seen_ts": t0,
            "first_seen_ts": t0,
            "detections": 1,
            "path_history": json.dumps(path_history)
        }
        
        tracker.redis.hgetall.return_value = vehicle_record
        pipe.execute.return_value = [True, True]
        
        result2 = tracker.on_detect("MH20EE7598", "camera2", t1)
        
        assert result2["status"] == "ok"
        assert result2["action"] == "MOVED"
        assert "camera1" in result2["path"]
        assert "camera2" in result2["path"]
        assert len(result2["path"]) == 2


class TestEntryToExit:
    """Test: Entry -> seen again cam0 within 30s -> exit"""
    
    def test_entry_then_exit_same_camera(self, tracker, sample_timestamp):
        """Test vehicle exiting at same camera."""
        base_time = datetime.now(timezone.utc)
        t0 = base_time.isoformat()
        t1 = (base_time + timedelta(seconds=10)).isoformat()
        
        # First detection - entry
        tracker.redis.hgetall.return_value = {}
        pipe = tracker.redis.pipeline.return_value.__enter__.return_value
        pipe.watch.return_value = None
        pipe.multi.return_value = None
        pipe.execute.return_value = [True, True]
        
        result1 = tracker.on_detect("MH20EE7598", "camera1", t0)
        assert result1["action"] == "ENTRY"
        
        # Second detection at same camera - exit
        path_history = [{"camera_id": "camera1", "ts": t0}]
        vehicle_record = {
            "plate": "MH20EE7598",
            "status": "ENTERED",
            "last_seen_camera": "camera1",
            "last_seen_ts": t0,
            "first_seen_ts": t0,
            "detections": 1,
            "path_history": json.dumps(path_history)
        }
        
        tracker.redis.hgetall.return_value = vehicle_record
        tracker.redis.delete.return_value = True
        pipe.execute.return_value = [True, True]
        
        result2 = tracker.on_detect("MH20EE7598", "camera1", t1)
        
        assert result2["status"] == "ok"
        assert result2["action"] == "EXIT"
        assert "removed from active tracking" in result2["msg"]


class TestPlateNormalization:
    """Test plate normalization."""
    
    def test_normalize_plate(self, tracker):
        """Test that plates are normalized correctly."""
        assert tracker.normalize_plate("MH20EE7598") == "MH20EE7598"
        assert tracker.normalize_plate("mh20ee7598") == "MH20EE7598"
        assert tracker.normalize_plate("MH 20 EE 7598") == "MH20EE7598"
        assert tracker.normalize_plate("  mh20ee7598  ") == "MH20EE7598"


class TestDuplicateDetection:
    """Test duplicate detection handling."""
    
    def test_duplicate_within_half_second(self, tracker, sample_timestamp):
        """Test that duplicates within 0.5s are ignored."""
        base_time = datetime.now(timezone.utc)
        t0 = base_time.isoformat()
        t1 = (base_time + timedelta(milliseconds=300)).isoformat()
        
        # First detection
        tracker.redis.hgetall.return_value = {}
        pipe = tracker.redis.pipeline.return_value.__enter__.return_value
        pipe.watch.return_value = None
        pipe.multi.return_value = None
        pipe.execute.return_value = [True, True]
        
        result1 = tracker.on_detect("MH20EE7598", "camera1", t0)
        assert result1["action"] == "ENTRY"
        
        # Duplicate detection
        path_history = [{"camera_id": "camera1", "ts": t0}]
        vehicle_record = {
            "plate": "MH20EE7598",
            "status": "ENTERED",
            "last_seen_camera": "camera1",
            "last_seen_ts": t0,
            "first_seen_ts": t0,
            "detections": 1,
            "path_history": json.dumps(path_history)
        }
        
        tracker.redis.hgetall.return_value = vehicle_record
        
        result2 = tracker.on_detect("MH20EE7598", "camera1", t1)
        assert result2["action"] == "DUPLICATE"


# Integration test (requires Redis)
@pytest.mark.integration
class TestIntegrationTracking:
    """Integration tests with real Redis (optional)."""
    
    @pytest.fixture
    def real_tracker(self):
        """Create tracker with real Redis (if available)."""
        try:
            tracker = VehicleTracker()
            # Clear test data
            tracker.redis.flushdb()
            yield tracker
            # Cleanup
            tracker.redis.flushdb()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
    
    def test_full_flow_entry_to_parked(self, real_tracker):
        """Test complete flow: entry -> timer expire -> parked."""
        base_time = datetime.now(timezone.utc)
        t0 = base_time.isoformat()
        
        # Entry
        result = real_tracker.on_detect("TEST123", "camera1", t0)
        assert result["action"] == "ENTRY"
        
        # Check vehicle exists
        vehicle = real_tracker.get_vehicle("TEST123")
        assert vehicle is not None
        assert vehicle["status"] == "ENTERED"
        
        # Simulate timer expiry
        result = real_tracker.on_timer_expire("TEST123")
        assert result["action"] == "PARKED"
        
        # Vehicle should be archived
        vehicle = real_tracker.get_vehicle("TEST123")
        assert vehicle is None  # Moved to archive


if __name__ == "__main__":
    pytest.main([__file__, "-v"])





