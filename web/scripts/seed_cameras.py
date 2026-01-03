"""
Seed script to initialize camera metadata in Redis.

Run this script to populate camera metadata for the vehicle tracking system.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.vehicle_tracker import VehicleTracker

def seed_cameras():
    """Seed camera metadata."""
    try:
        tracker = VehicleTracker()
        
        # Default cameras
        cameras = [
            {
                "id": "camera1",
                "lat": 12.968194,
                "lon": 79.155917,
                "name": "Main Gate"
            },
            {
                "id": "camera2",
                "lat": 12.968806,
                "lon": 79.155306,
                "name": "GDN CAM 2"
            }
        ]
        
        print("📷 Seeding camera metadata...")
        for cam in cameras:
            tracker.set_camera_metadata(cam["id"], cam["lat"], cam["lon"], cam["name"])
            print(f"   ✅ {cam['id']}: {cam['name']} ({cam['lat']}, {cam['lon']})")
        
        print("\n✅ Camera metadata seeded successfully!")
        
    except Exception as e:
        print(f"❌ Error seeding cameras: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    seed_cameras()





