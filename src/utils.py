"""
Utility functions for ALPR project
"""
from datetime import datetime, timezone

def timestamp():
    """Get current timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()




