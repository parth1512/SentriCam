"""
Background worker for handling Redis timer expirations.

This worker monitors expired timer keys and triggers on_timer_expire callbacks.
Can be used as fallback if Redis keyspace notifications are not available.
"""

import time
import redis
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TimerWorker:
    """Background worker to handle timer expirations."""
    
    def __init__(self, tracker, poll_interval: float = 2.0):
        """
        Initialize timer worker.
        
        Args:
            tracker: VehicleTracker instance
            poll_interval: How often to poll for expired timers (seconds)
        """
        self.tracker = tracker
        self.redis = tracker.redis
        self.poll_interval = poll_interval
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the background worker thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        logger.info("Timer worker started")
    
    def stop(self):
        """Stop the background worker thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
        logger.info("Timer worker stopped")
    
    def _worker_loop(self):
        """Main worker loop that polls for expired timers."""
        while self.running:
            try:
                # Find all timer keys
                timer_keys = self.redis.keys("car:*:timer")
                
                for timer_key in timer_keys:
                    # Check if timer has expired (TTL <= 0)
                    ttl = self.redis.ttl(timer_key)
                    
                    if ttl == -2:  # Key doesn't exist (already expired and cleaned)
                        continue
                    elif ttl == -1:  # Key exists but no TTL (shouldn't happen)
                        logger.warning(f"Timer key {timer_key} has no TTL")
                        continue
                    elif ttl == 0:  # Just expired
                        # Extract plate number from key
                        plate = timer_key.replace("car:", "").replace(":timer", "")
                        
                        # Trigger expiry handler
                        try:
                            self.tracker.on_timer_expire(plate)
                            logger.info(f"Processed timer expiry for {plate}")
                        except Exception as e:
                            logger.error(f"Error processing timer expiry for {plate}: {e}")
                
                time.sleep(self.poll_interval)
            
            except Exception as e:
                logger.error(f"Error in timer worker loop: {e}")
                time.sleep(self.poll_interval)


# Global worker instance
_worker = None

def start_timer_worker(tracker):
    """Start the global timer worker."""
    global _worker
    if _worker is None:
        _worker = TimerWorker(tracker)
        _worker.start()
    return _worker

def stop_timer_worker():
    """Stop the global timer worker."""
    global _worker
    if _worker:
        _worker.stop()
        _worker = None





