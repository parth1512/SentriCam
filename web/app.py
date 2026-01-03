from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import cv2
import base64
import threading
import time
from datetime import datetime
from pathlib import Path
import sys
import json
import math
import os
from werkzeug.utils import secure_filename
import numpy as np

# Load environment variables from .env file
load_dotenv()

# Add src directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detector import PlateDetector
from ocr_reader import OCR
from augmentations import preprocess_for_ocr
from utils import timestamp

# Import vehicle tracking services (optional - only if Redis is available)
try:
    from services.vehicle_tracker import VehicleTracker
    from services.notifier import get_notifier
    REDIS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Redis services not available: {e}")
    print("   Continuing without Redis-based vehicle tracking")
    VehicleTracker = None
    get_notifier = None
    REDIS_AVAILABLE = False

# Import database models
from models import db, Vehicle

# Import Telegram services
from services.telegram_service import get_telegram_service
from services.telegram_bot import get_telegram_bot, start_bot_thread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alpr_secret_key_2024'
# Database configuration - store in web directory
db_path = Path(__file__).resolve().parent / 'vehicles.db'
# Use as_posix() for cross-platform compatibility (converts to forward slashes)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path.as_posix()}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

# Trial mode configuration
UPLOAD_FOLDER = Path(__file__).resolve().parent / 'trial_images'
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

# Initialize database
db.init_app(app)
# Configure Socket.IO with better connection stability
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=10*1024*1024,  # 10MB for large frames
    async_mode='threading',
    logger=False,
    engineio_logger=False
)

# Global state
detector = None
ocr = None
cameras = {
    'camera1': {'cap': None, 'location': {'lat': 12.968194, 'lng': 79.155917, 'name': 'Camera 1'}, 'active': False, 'is_trial': False},
    'camera2': {'cap': None, 'location': {'lat': 12.968806, 'lng': 79.155306, 'name': 'Camera 2'}, 'active': False, 'is_trial': False}
}
detections_history = {}  # {plate_number: [{camera_id, timestamp, location, confidence}]}
plate_camera_status = {}  # {plate_number: {camera_id: 'entry'|'exit'}} - tracks entry/exit status per camera
vehicle_timers = {}  # {plate_number: {'timer': threading.Timer, 'first_camera': str, 'current_camera': str, 'location': dict, 'start_time': float, 'path': list, 'detection_count': int}}
vehicle_exits = {}  # {plate_number: True} - tracks vehicles that have exited
vehicle_first_seen = {}  # {plate_number: first_camera_id} - tracks vehicles that have been seen and their first camera
camera1_detection_count = {}  # {plate_number: count} - tracks how many times a vehicle has been detected on camera1
timer_lock = threading.Lock()  # Lock for thread-safe timer operations
active_clients = set()

# Vehicle tracking service (Redis-based)
vehicle_tracker = None
notifier = None

# Initialize database tables
def init_database():
    """Initialize database and create tables"""
    with app.app_context():
        db.create_all()
        print("✅ Database initialized successfully")
        
        # Check if telegram_chat_id column exists, if not, add it
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('vehicles')]
            if 'telegram_chat_id' not in columns:
                print("⚠️  telegram_chat_id column not found. Run migrate_add_telegram.py to add it.")
                print("   Alternatively, the column will be added automatically on next schema update.")
        except Exception as e:
            print(f"⚠️  Could not check database schema: {e}")

# Initialize detector and OCR
def init_models():
    global detector, ocr, vehicle_tracker, notifier
    weights_path = str(Path(__file__).resolve().parent.parent / "weights" / "plate_detector.pt")
    
    # Try to load models, but don't fail if weights are missing
    try:
        if Path(weights_path).exists():
            print(f"📦 Loading YOLO detector from {weights_path}...")
            detector = PlateDetector(weights_path=weights_path, device="mps")
            print(f"   ✅ Detector loaded successfully")
        else:
            print(f"   ⚠️  Warning: Weights file not found at {weights_path}")
            print("   ⚠️  Detection will be disabled. Please train the model or download weights.")
            detector = None
    except Exception as e:
        print(f"   ❌ Error loading detector: {e}")
        detector = None
    
    try:
        print(f"📦 Loading OCR models (PaddleOCR + EasyOCR combined)...")
        ocr = OCR()
        if ocr.primary is not None and ocr.fallback is not None:
            print(f"   ✅ OCR loaded successfully (using PaddleOCR + EasyOCR together)")
        elif ocr.primary is not None:
            print(f"   ⚠️  OCR loaded (using PaddleOCR only)")
        elif ocr.fallback is not None:
            print(f"   ⚠️  OCR loaded (using EasyOCR only)")
        else:
            print(f"   ❌ No OCR engine available")
    except Exception as e:
        print(f"   ❌ Error loading OCR: {e}")
        ocr = None
    
    print("\n" + "-" * 60)
    if detector and ocr:
        print("✅ All models loaded successfully - System ready!")
        
        # Initialize vehicle tracker and notifier (if Redis is available)
        if REDIS_AVAILABLE and VehicleTracker and get_notifier:
            try:
                vehicle_tracker = VehicleTracker()
                notifier = get_notifier()
                print("✅ Vehicle tracking service initialized (Redis-based)")
                
                # Initialize camera metadata in Redis
                for cam_id, cam_data in cameras.items():
                    loc = cam_data.get('location', {})
                    vehicle_tracker.set_camera_metadata(
                        cam_id,
                        loc.get('lat', 0),
                        loc.get('lng', 0),
                        loc.get('name', cam_id)
                    )
                
                # Start background timer worker (fallback if keyspace notifications fail)
                try:
                    from services.timer_worker import start_timer_worker
                    start_timer_worker(vehicle_tracker)
                    print("✅ Timer worker started")
                except ImportError:
                    print("⚠️  Timer worker not available")
            except Exception as e:
                print(f"⚠️  Warning: Vehicle tracking service not available: {e}")
                print("   Continuing without Redis-based tracking (using legacy mode)")
                vehicle_tracker = None
                notifier = None
        else:
            print("⚠️  Redis not available - using legacy tracking mode")
            vehicle_tracker = None
            notifier = None
    else:
        print("⚠️  Running in limited mode - some features may not work")
    print("-" * 60 + "\n")

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS coordinates in meters (Haversine formula)"""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def on_timer_expire(plate_number, timer_info_param):
    """Called when 30-second timer expires - mark last camera location as last seen"""
    print(f"\n{'='*60}")
    print(f"⏱️  TIMER EXPIRED for {plate_number}")
    print(f"{'='*60}")
    
    # Use timer_info_param directly (passed from timer) or try to get from vehicle_timers
    # This handles cases where timer_info might have been updated in vehicle_timers
    with timer_lock:
        # Try to get latest timer info from vehicle_timers first
        if plate_number in vehicle_timers:
            timer_data = vehicle_timers[plate_number]
            # Use the stored timer_data if it exists (it should be more up-to-date)
            last_camera = timer_data.get('current_camera', timer_info_param.get('current_camera'))
            last_location = timer_data.get('location', timer_info_param.get('location'))
        else:
            # Fallback to passed parameter
            print(f"   ⚠️  Timer for {plate_number} not in vehicle_timers, using passed timer_info")
            last_camera = timer_info_param.get('current_camera', 'unknown')
            last_location = timer_info_param.get('location', {})
        
        # Validate location data
        if not last_location:
            print(f"   ❌ ERROR: No location data for {plate_number}")
            print(f"   ❌ Cannot send notification without location")
            if plate_number in vehicle_timers:
                del vehicle_timers[plate_number]
            print(f"{'='*60}\n")
            return
        
        location_name = last_location.get('name', last_camera) if last_location else last_camera
        lat = last_location.get('lat')
        lng = last_location.get('lng')
        
        print(f"   📍 Last camera: {last_camera}")
        print(f"   📍 Location: {location_name}")
        print(f"   📍 Coordinates: {lat}, {lng}")
        
        # Validate coordinates
        if not lat or not lng:
            print(f"   ❌ ERROR: Missing coordinates in location data")
            print(f"   ❌ Location data: {last_location}")
            print(f"   ❌ Cannot send notification without coordinates")
            if plate_number in vehicle_timers:
                del vehicle_timers[plate_number]
            print(f"{'='*60}\n")
            return
        
        # Update the last detection in history to use this camera's location
        if plate_number in detections_history and len(detections_history[plate_number]) > 0:
            # Create a new detection record with current timestamp but last camera's location
            last_record = detections_history[plate_number][-1].copy()
            last_record['camera_id'] = last_camera
            last_record['location'] = last_location
            last_record['timestamp'] = timestamp()
            last_record['status'] = 'last_seen'
            detections_history[plate_number].append(last_record)
            
            # Keep only recent detections (last 100 per plate)
            if len(detections_history[plate_number]) > 100:
                detections_history[plate_number] = detections_history[plate_number][-100:]
        
        # Send Telegram notification if vehicle is registered and has Telegram chat ID
        print(f"   📤 Sending Telegram notification for {plate_number}...")
        print(f"   📤 Event type: last_seen")
        print(f"   📤 Location: {location_name} ({lat}, {lng})")
        
        try:
            success = send_telegram_notification(plate_number, last_camera, last_location, event_type='last_seen', include_location=True)
            if success:
                print(f"   ✅ Telegram notification sent successfully for {plate_number}")
            else:
                print(f"   ⚠️  Telegram notification failed for {plate_number}")
                print(f"   💡 Check if vehicle is registered and has Telegram chat ID linked")
        except Exception as e:
            print(f"   ❌ Exception sending notification: {e}")
            import traceback
            traceback.print_exc()
        
        # Clean up timer
        if plate_number in vehicle_timers:
            del vehicle_timers[plate_number]
            print(f"   🗑️  Timer cleaned up for {plate_number}")
        
        print(f"{'='*60}\n")

def send_telegram_notification(plate_number, camera_id, location, event_type='last_seen', path=None, include_location=True):
    """
    Send Telegram notification for vehicle events
    
    Args:
        plate_number: Vehicle plate number
        camera_id: Camera ID where detected
        location: Location dict with lat, lng, name
        event_type: 'entry', 'movement', 'exit', 'last_seen'
        path: Movement path (for movement events)
        include_location: Whether to include location info (for first entry, set to False)
    
    Returns:
        True if notification was sent successfully, False otherwise
    """
    try:
        # Normalize plate number (uppercase, remove spaces)
        normalized_plate = plate_number.upper().strip()
        
        # Get location details (only if include_location is True)
        location_name = location.get('name', camera_id) if location and include_location else None
        location_coords = location if location and include_location else None
        
        # Get Telegram bot instance (will use Flask app from current context)
        telegram_bot = get_telegram_bot(flask_app=app)
        
        if not telegram_bot:
            print(f"   ⚠️  Telegram bot not available - skipping notification for {normalized_plate}")
            return False
        
        # Send notification using bot service
        event_timestamp = timestamp()
        success = telegram_bot.send_vehicle_event(
            vehicle_number=normalized_plate,
            event_type=event_type,
            camera_name=location_name,
            location=location_coords,
            path=path,
            timestamp=event_timestamp,
            include_location=include_location
        )
        
        if success:
            print(f"   ✅ Telegram {event_type} notification sent for {normalized_plate}")
        else:
            print(f"   ⚠️  Failed to send Telegram {event_type} notification for {normalized_plate}")
            print(f"   💡 Possible reasons:")
            print(f"      - Vehicle {normalized_plate} not registered in database")
            print(f"      - Vehicle {normalized_plate} has no Telegram chat ID linked")
            print(f"      - User needs to register via Telegram bot first")
        
        return success
    
    except Exception as e:
        # Don't let Telegram errors break the detection logic
        print(f"   ❌ Error sending Telegram notification: {e}")
        import traceback
        traceback.print_exc()
        return False

def calculate_vehicle_range(plate_number):
    """Calculate the estimated range where the vehicle is located based on detections"""
    if plate_number not in detections_history or len(detections_history[plate_number]) < 1:
        return None
    
    detections = detections_history[plate_number]
    
    # Get first and last detection
    first_detection = detections[0]
    last_detection = detections[-1]
    
    if first_detection['camera_id'] == last_detection['camera_id']:
        # Same camera, return camera location with small radius
        return {
            'center': first_detection['location'],
            'radius_meters': 50,
            'first_seen': first_detection['timestamp'],
            'last_seen': last_detection['timestamp']
        }
    
    # Different cameras - calculate range between them
    loc1 = first_detection['location']
    loc2 = last_detection['location']
    
    distance = calculate_distance(
        loc1['lat'], loc1['lng'],
        loc2['lat'], loc2['lng']
    )
    
    # Calculate center point
    center_lat = (loc1['lat'] + loc2['lat']) / 2
    center_lng = (loc1['lng'] + loc2['lng']) / 2
    
    # Use fixed 50 meter radius for all vehicle locations
    return {
        'center': {'lat': center_lat, 'lng': center_lng},
        'radius_meters': 50,  # Fixed 50 meter radius
        'camera1': loc1,
        'camera2': loc2,
        'first_seen': first_detection['timestamp'],
        'last_seen': last_detection['timestamp']
    }

def process_frame(camera_id, frame):
    """Process a frame for license plate detection"""
    if detector is None or ocr is None:
        # Return empty detections if models aren't loaded
        return []
    
    dets = detector.predict(frame, conf=0.35)
    results = []
    
    for d in dets:
        crop = PlateDetector.crop(frame, d.bbox)
        crop = preprocess_for_ocr(crop)
        text, ocr_conf = ocr.recognize_plate(crop)
        
        if text and len(text) > 0:
            # Skip if vehicle has exited
            if text in vehicle_exits:
                print(f"   ⏭️  [{camera_id}] {text} has exited - skipping detection")
                continue
            
            # Handle timer logic based on camera
            with timer_lock:
                # Check for camera1 second detection BEFORE processing other logic
                # This must be checked first to catch exit condition immediately
                if camera_id == 'camera1':
                    # Get current count BEFORE incrementing
                    current_camera1_count = camera1_detection_count.get(text, 0)
                    # Increment count
                    camera1_detection_count[text] = current_camera1_count + 1
                    camera1_count = camera1_detection_count[text]
                    
                    # CRITICAL: If this is the second detection on camera1, mark as EXIT immediately
                    if camera1_count == 2:
                        # Cancel any active timer
                        if text in vehicle_timers:
                            timer_info = vehicle_timers[text]
                            if 'timer' in timer_info and timer_info['timer']:
                                timer_info['timer'].cancel()
                            del vehicle_timers[text]
                        
                        status = 'exit'
                        vehicle_exits[text] = True
                        location_name = cameras[camera_id]['location'].get('name', camera_id)
                        location_data = cameras[camera_id]['location']
                        print(f"   🚪 [{camera_id}] {text} EXIT detected (second detection on camera1, count={camera1_count}) at {location_name}")
                        
                        # Send exit notification without map (include_location=False)
                        send_telegram_notification(text, camera_id, location_data, event_type='exit', include_location=False)
                        
                        # Clean up tracking so vehicle can be tracked again if it re-enters
                        if text in vehicle_first_seen:
                            del vehicle_first_seen[text]
                        if text in camera1_detection_count:
                            del camera1_detection_count[text]
                        
                        # Mark as exit in status
                        if text not in plate_camera_status:
                            plate_camera_status[text] = {}
                        plate_camera_status[text][camera_id] = 'exit'
                        
                        # Skip creating detection record for exit - return empty results
                        continue
                else:
                    camera1_count = camera1_detection_count.get(text, 0)
                
                if text in vehicle_timers:
                    timer_info = vehicle_timers[text]
                    first_camera = timer_info['first_camera']
                    current_camera = timer_info['current_camera']
                    detection_count = timer_info.get('detection_count', 1)
                    
                    # Case 2: Detected at different camera = MOVEMENT (restart timer silently, no notification)
                    if camera_id != current_camera:
                        # Vehicle moved to different camera - restart timer silently (user has 30s more)
                        old_timer = timer_info.get('timer')
                        if old_timer:
                            old_timer.cancel()
                            print(f"   ⏹️  [{current_camera}] Cancelled previous timer for {text}")
                        
                        status = 'movement'
                        
                        # Update path (only add if not already there)
                        path = timer_info.get('path', [])
                        current_location_name = cameras[camera_id]['location'].get('name', camera_id)
                        if not path or path[-1] != current_location_name:
                            if not path:
                                # Add previous camera location if path is empty
                                prev_location_name = cameras[current_camera]['location'].get('name', current_camera)
                                path.append(prev_location_name)
                            path.append(current_location_name)
                        timer_info['path'] = path
                        
                        # Update current camera and location (CRITICAL: ensure location has lat/lng)
                        timer_info['current_camera'] = camera_id
                        location_data = cameras[camera_id]['location']
                        timer_info['location'] = location_data
                        timer_info['start_time'] = time.time()
                        timer_info['detection_count'] = 1  # Reset count for new camera
                        
                        # Verify location data has coordinates
                        if not location_data or not location_data.get('lat') or not location_data.get('lng'):
                            print(f"   ⚠️  [{camera_id}] WARNING: Location data missing coordinates for {text}")
                            print(f"   ⚠️  Location data: {location_data}")
                        
                        # Start new 30-second timer - will send location notification when expires
                        # Pass a copy of timer_info to avoid reference issues
                        timer = threading.Timer(30.0, on_timer_expire, args=(text, timer_info.copy()))
                        timer.start()
                        timer_info['timer'] = timer
                        vehicle_timers[text] = timer_info  # Update in dictionary to ensure it persists
                        
                        path_str = ' -> '.join(path)
                        location_coords = f"{location_data.get('lat', 'N/A')}, {location_data.get('lng', 'N/A')}"
                        print(f"   🛣️  [{camera_id}] {text} moved to different camera - path: {path_str}")
                        print(f"   ⏱️  [{camera_id}] Restarted 30-second timer for {text} (no notification - user has 30s more)")
                        print(f"   📍 Timer location: {location_data.get('name', camera_id)} ({location_coords})")
                        print(f"   ⏰ Timer will expire in 30 seconds at {time.time() + 30.0:.2f}")
                        print(f"   ℹ️  No notification sent - vehicle detected at new camera, timer restarted")
                        
                        # Do NOT send movement notification here - wait for timer to expire
                        # Timer expiry will send "last_seen" notification with location
                        
                        if text not in plate_camera_status:
                            plate_camera_status[text] = {}
                        plate_camera_status[text][camera_id] = 'movement'
                        
                    # Case 3: Detected at same camera again after movement (restart timer silently)
                    elif camera_id == current_camera:
                        # Vehicle detected again at same camera - restart timer silently (no notification)
                        old_timer = timer_info.get('timer')
                        if old_timer:
                            old_timer.cancel()
                        
                        timer_info['start_time'] = time.time()
                        timer_info['detection_count'] = detection_count + 1
                        status = 'movement'  # Still movement, just updating location
                        
                        # Update location data to ensure it's current
                        timer_info['location'] = cameras[camera_id]['location']
                        timer_info['current_camera'] = camera_id
                        
                        # Restart 30-second timer with updated timer_info
                        timer = threading.Timer(30.0, on_timer_expire, args=(text, timer_info.copy()))
                        timer.start()
                        timer_info['timer'] = timer
                        vehicle_timers[text] = timer_info  # Update in dictionary
                        
                        print(f"   🔄 [{camera_id}] {text} detected again at {current_camera} (count: {timer_info['detection_count']}) - timer restarted silently (no notification)")
                        # Continue to create detection record
                        
                else:
                    # No active timer - check if this is first detection or subsequent detection at different camera
                    is_first_detection = text not in vehicle_first_seen
                    
                    if is_first_detection:
                        # Mark vehicle as seen and record first camera
                        vehicle_first_seen[text] = camera_id
                        
                        # FIRST DETECTION: Only send ENTRY notification if detected on camera1
                        if camera_id == 'camera1':
                            # FIRST DETECTION ON CAMERA1: Send entry notification immediately, then start 30s timer
                            status = 'entry'
                            location_data = cameras[camera_id]['location']
                            print(f"   ✅ [{camera_id}] {text} FIRST DETECTION ON CAMERA1 - sending entry notification immediately, then starting 30s timer")
                            
                            # NOTE: camera1_detection_count is already set in the camera1 check above
                            # No need to set it here again as it's already incremented
                            
                            # Send entry notification immediately WITHOUT location info
                            send_telegram_notification(text, camera_id, location_data, event_type='entry', include_location=False)
                            
                            # Start 30-second timer immediately after first detection
                            # Timer will send last_seen notification if no new detection within 30s
                            timer_info = {
                                'first_camera': camera_id,
                                'current_camera': camera_id,
                                'location': location_data,
                                'start_time': time.time(),
                                'path': [],
                                'detection_count': 1
                            }
                            
                            # Start 30-second timer - will send location notification when timer expires
                            timer = threading.Timer(30.0, on_timer_expire, args=(text, timer_info.copy()))
                            timer.start()
                            timer_info['timer'] = timer
                            vehicle_timers[text] = timer_info
                            
                            location_coords = f"{location_data.get('lat', 'N/A')}, {location_data.get('lng', 'N/A')}"
                            location_name = location_data.get('name', camera_id)
                            print(f"   ⏱️  [{camera_id}] Started 30-second timer for {text} after first detection on camera1")
                            print(f"   📍 Timer location: {location_name} ({location_coords})")
                            print(f"   ⏰ Timer will expire in 30 seconds at {time.time() + 30.0:.2f}")
                            
                            if text not in plate_camera_status:
                                plate_camera_status[text] = {}
                            plate_camera_status[text][camera_id] = 'entry'
                        else:
                            # FIRST DETECTION ON OTHER CAMERA: No entry notification, just start timer for last_seen
                            status = 'movement'
                            location_data = cameras[camera_id]['location']
                            print(f"   📍 [{camera_id}] {text} FIRST DETECTION ON {camera_id} (not camera1) - NO entry notification, starting 30s timer for last_seen")
                            
                            # Start 30-second timer - will send last_seen notification when timer expires
                            timer_info = {
                                'first_camera': camera_id,
                                'current_camera': camera_id,
                                'location': location_data,
                                'start_time': time.time(),
                                'path': [],
                                'detection_count': 1
                            }
                            
                            # Start 30-second timer - will send location notification when timer expires
                            timer = threading.Timer(30.0, on_timer_expire, args=(text, timer_info.copy()))
                            timer.start()
                            timer_info['timer'] = timer
                            vehicle_timers[text] = timer_info
                            
                            location_coords = f"{location_data.get('lat', 'N/A')}, {location_data.get('lng', 'N/A')}"
                            location_name = location_data.get('name', camera_id)
                            print(f"   ⏱️  [{camera_id}] Started 30-second timer for {text} - will send last_seen notification after timer expires")
                            print(f"   📍 Timer location: {location_name} ({location_coords})")
                            print(f"   ⏰ Timer will expire in 30 seconds at {time.time() + 30.0:.2f}")
                            
                            if text not in plate_camera_status:
                                plate_camera_status[text] = {}
                            plate_camera_status[text][camera_id] = 'movement'
                    else:
                        # Vehicle seen before - check if detected at different camera
                        first_camera = vehicle_first_seen[text]
                        
                        if camera_id != first_camera:
                            # DETECTED AT DIFFERENT CAMERA: Start 30-second timer, will send location after timer expires
                            status = 'movement'
                            location_data = cameras[camera_id]['location']
                            
                            # Verify location data has coordinates
                            if not location_data or not location_data.get('lat') or not location_data.get('lng'):
                                print(f"   ⚠️  [{camera_id}] WARNING: Location data missing coordinates for {text}")
                                print(f"   ⚠️  Location data: {location_data}")
                            
                            print(f"   🚗 [{camera_id}] {text} detected at DIFFERENT camera ({first_camera} -> {camera_id}) - starting 30-second timer")
                            
                            # Create timer info dictionary
                            timer_info = {
                                'first_camera': first_camera,
                                'current_camera': camera_id,
                                'location': location_data,
                                'start_time': time.time(),
                                'path': [],
                                'detection_count': 1
                            }
                            
                            # Start 30-second timer - will send location notification when timer expires
                            # Pass a copy to avoid reference issues
                            timer = threading.Timer(30.0, on_timer_expire, args=(text, timer_info.copy()))
                            timer.start()
                            timer_info['timer'] = timer
                            
                            # Store in vehicle_timers dictionary
                            vehicle_timers[text] = timer_info
                            
                            location_coords = f"{location_data.get('lat', 'N/A')}, {location_data.get('lng', 'N/A')}"
                            location_name = location_data.get('name', camera_id)
                            print(f"   ⏱️  [{camera_id}] Started 30-second timer for {text} - will send location after timer expires")
                            print(f"   📍 Timer location: {location_name} ({location_coords})")
                            print(f"   ⏰ Timer will expire in 30 seconds at {time.time() + 30.0:.2f}")
                            
                            if text not in plate_camera_status:
                                plate_camera_status[text] = {}
                            plate_camera_status[text][camera_id] = 'movement'
                        else:
                            # Same camera as first detection - just update status, no timer
                            status = 'entry'
                            if text not in plate_camera_status:
                                plate_camera_status[text] = {}
                            plate_camera_status[text][camera_id] = 'entry'
                            print(f"   🔄 [{camera_id}] {text} detected again at same camera ({camera_id}) - no timer needed")
            
            # Log detection to console
            print(f"   🚗 [{camera_id}] Detected plate: {text} (OCR conf: {ocr_conf:.2f}, Det conf: {d.confidence:.2f})")
            
            # Only create detection record if not exiting (exits are handled above with continue)
            if text not in vehicle_exits:
                # Record detection
                detection_record = {
                    'camera_id': camera_id,
                    'timestamp': timestamp(),
                    'location': cameras[camera_id]['location'],
                    'plate_number': text,
                    'confidence': float(d.confidence),
                    'ocr_confidence': float(ocr_conf),
                    'status': status  # 'entry', 'exit', 'movement', 'last_seen'
                }
                
                # Add path information if available
                if text in vehicle_timers and vehicle_timers[text].get('path'):
                    path_str = ' -> '.join(vehicle_timers[text]['path'])
                    detection_record['path'] = path_str
                
                # Store in history
                if text not in detections_history:
                    detections_history[text] = []
                detections_history[text].append(detection_record)
                
                # Keep only recent detections (last 100 per plate)
                if len(detections_history[text]) > 100:
                    detections_history[text] = detections_history[text][-100:]
                
                results.append({
                    'bbox': list(d.bbox),
                    'plate_number': text,
                    'confidence': float(d.confidence),
                    'ocr_confidence': float(ocr_conf),
                    'status': status,  # Include status in results
                    'location': cameras[camera_id]['location'],  # Include location info
                    'timestamp': detection_record['timestamp']  # Include timestamp
                })
    
    return results

def capture_and_send(camera_id):
    """Capture frames from camera and send to clients"""
    camera = cameras[camera_id]
    cap = camera['cap']
    frame_count = 0
    error_count = 0
    max_errors = 30  # Increased from 10 to be more lenient
    consecutive_errors = 0
    max_consecutive_errors = 5  # Allow some consecutive errors
    
    # Detection state - store latest detections to draw on frames
    latest_detections = []
    detection_lock = threading.Lock()
    
    # Detection processing: only process every N frames for better FPS
    DETECTION_INTERVAL = 5  # Process detection every 5 frames (6 FPS detection, 30 FPS video)
    
    # Limit concurrent detection threads to prevent resource exhaustion
    active_detection_threads = 0
    max_detection_threads = 2
    detection_thread_lock = threading.Lock()
    
    start_time = time.time()
    print(f"   🎬 [{camera_id}] Video capture thread started")
    
    # Give camera a moment to stabilize and read a few initial frames
    time.sleep(0.3)
    initial_frames_read = 0
    for _ in range(3):
        if cap and cap.isOpened():
            ret, _ = cap.read()
            if ret:
                initial_frames_read += 1
        time.sleep(0.1)
    print(f"   📸 [{camera_id}] Read {initial_frames_read}/3 initial frames")
    
    def process_detection_async(frame_copy):
        """Process detection in background without blocking video feed"""
        nonlocal latest_detections, active_detection_threads
        try:
            detections = process_frame(camera_id, frame_copy)
            with detection_lock:
                latest_detections = detections or []
        except Exception as e:
            print(f"   ⚠️  [{camera_id}] Detection error: {e}")
        finally:
            with detection_thread_lock:
                active_detection_threads -= 1
    
    # Store camera index for potential reopening
    camera_index = camera.get('_camera_index', 0)
    
    while camera['active']:
        if cap is None or not cap.isOpened():
            print(f"   ❌ [{camera_id}] Camera not opened, attempting to reopen...")
            # Try to reopen the camera
            try:
                camera_index = camera.get('_camera_index', 0)
                cap = cv2.VideoCapture(camera_index, cv2.CAP_AVFOUNDATION)
                if cap.isOpened():
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        camera['cap'] = cap
                        print(f"   ✅ [{camera_id}] Camera reopened successfully")
                        time.sleep(0.5)  # Give it time to stabilize
                    else:
                        cap.release()
                        cap = None
                        print(f"   ❌ [{camera_id}] Camera reopened but can't read frames")
                        time.sleep(1)
                        continue
                else:
                    print(f"   ❌ [{camera_id}] Failed to reopen camera")
                    time.sleep(1)
                    continue
            except Exception as e:
                print(f"   ❌ [{camera_id}] Error reopening camera: {e}")
                time.sleep(1)
                continue
        
        ret, frame = cap.read()
        if not ret or frame is None or frame.size == 0:
            consecutive_errors += 1
            error_count += 1
            
            if consecutive_errors <= 3:
                # First few errors are normal, just log
                if consecutive_errors == 1:
                    print(f"   ⚠️  [{camera_id}] Frame read failed (attempt {consecutive_errors})")
            else:
                print(f"   ⚠️  [{camera_id}] Failed to read frame (consecutive: {consecutive_errors}, total: {error_count}/{max_errors})")
            
            # Only stop if we have too many consecutive errors OR too many total errors
            if consecutive_errors >= max_consecutive_errors:
                print(f"   ❌ [{camera_id}] Too many consecutive errors ({consecutive_errors}), stopping camera")
                camera['active'] = False
                socketio.emit('error', {'message': f'Camera {camera_id} stopped due to read errors'}, room=request.sid if hasattr(request, 'sid') else None)
                break
            
            if error_count >= max_errors:
                print(f"   ❌ [{camera_id}] Too many total errors ({error_count}), stopping camera")
                camera['active'] = False
                socketio.emit('error', {'message': f'Camera {camera_id} stopped due to too many errors'}, room=request.sid if hasattr(request, 'sid') else None)
                break
            
            time.sleep(0.05)  # Shorter sleep for faster recovery
            continue
        
        # Reset error counts on successful frame read
        if consecutive_errors > 0:
            consecutive_errors = 0
        error_count = 0  # Reset error count on success
        frame_count += 1
        
        # Process detection only every N frames (async to not block video)
        if frame_count % DETECTION_INTERVAL == 0 and detector is not None and ocr is not None:
            # Limit concurrent detection threads
            with detection_thread_lock:
                if active_detection_threads < max_detection_threads:
                    active_detection_threads += 1
                    # Run detection in background thread
                    detection_thread = threading.Thread(
                        target=process_detection_async, 
                        args=(frame.copy(),), 
                        daemon=True
                    )
                    detection_thread.start()
                # If too many threads, skip this detection cycle
        
        # Get latest detections (thread-safe)
        with detection_lock:
            current_detections = latest_detections.copy()
        
        # Draw detections on frame
        for det in current_detections:
            x1, y1, x2, y2 = det['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det['plate_number']} ({det['confidence']:.2f})"
            cv2.putText(frame, label, (x1, max(0, y1 - 10)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        # Encode frame as JPEG (lower quality for better FPS)
        try:
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])  # Reduced from 85
            if buffer is None:
                continue
            
            frame_bytes = base64.b64encode(buffer).decode('utf-8')
            
            # Emit to all connected clients with error handling
            try:
                # Debug: log detections being sent
                if current_detections:
                    for det in current_detections:
                        if 'status' in det:
                            print(f"   📤 [{camera_id}] Sending detection: {det['plate_number']} with status: {det['status']}")
                
                socketio.emit(f'frame_{camera_id}', {
                    'frame': frame_bytes,
                    'detections': current_detections,
                    'timestamp': timestamp()
                }, namespace='/')
            except Exception as emit_error:
                # If no clients connected, this is normal - don't spam logs
                if 'no active clients' not in str(emit_error).lower():
                    print(f"   ⚠️  [{camera_id}] Socket emit error: {emit_error}")
            
            if frame_count % 90 == 0:  # Log every 90 frames (~3 seconds at 30 FPS)
                fps_estimate = frame_count / (time.time() - start_time) if frame_count > 0 else 0
                print(f"   📹 [{camera_id}] Sent {frame_count} frames (~{fps_estimate:.1f} FPS)")
        except Exception as e:
            print(f"   ❌ [{camera_id}] Error encoding/emitting frame: {e}")
            # Continue even if encoding fails - don't crash the thread
            time.sleep(0.01)
        
        # Small sleep to prevent CPU overload and ensure stable connection
        # Adjust sleep based on whether we're getting frames successfully
        if frame_count > 0 and frame_count % 30 == 0:
            # Every 30 frames, check if we need to adjust timing
            elapsed = time.time() - start_time
            if elapsed > 0:
                current_fps = frame_count / elapsed
                if current_fps > 35:
                    time.sleep(0.02)  # Slow down if too fast
                else:
                    time.sleep(0.01)  # Normal speed
        else:
            time.sleep(0.01)  # ~100 FPS max, but camera will limit to its actual FPS
    
    print(f"   🛑 [{camera_id}] Capture thread stopped (total: {frame_count} frames sent)")
    if cap is not None:
        cap.release()
        camera['cap'] = None

@app.route('/')
def index():
    # In production, serve the built React app
    build_dir = Path(__file__).resolve().parent / 'build'
    if build_dir.exists():
        return send_from_directory(build_dir, 'index.html')
    # In development, serve the template
    return render_template('index.html')

# Serve static files from React build directory
@app.route('/static/<path:path>')
def serve_static(path):
    build_dir = Path(__file__).resolve().parent / 'build' / 'static'
    if build_dir.exists():
        return send_from_directory(build_dir, path)
    return '', 404

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    """Get camera status and locations"""
    result = {
        camera_id: {
            'active': camera.get('active', False),
            'location': camera.get('location', {}),
            'image_url': camera.get('image_url'),
            'is_trial': camera.get('is_trial', False)
        }
        for camera_id, camera in cameras.items()
    }
    print(f"📡 [API] GET /api/cameras - Returning camera data:")
    for cam_id, cam_data in result.items():
        loc = cam_data.get('location', {})
        print(f"   {cam_id}: active={cam_data.get('active')}, location={loc}, is_trial={cam_data.get('is_trial', False)}")
    return jsonify(result)

@app.route('/api/cameras/<camera_id>/location', methods=['POST'])
def update_camera_location(camera_id):
    """Update camera location (latitude, longitude, name)"""
    if camera_id not in cameras:
        # Create new camera if it doesn't exist
        cameras[camera_id] = {
            'cap': None,
            'location': {},
            'active': False,
            'is_trial': False
        }
        print(f"📷 [API] Creating new camera: {camera_id}")
    
    data = request.json
    print(f"📍 [API] Updating {camera_id} location: {data}")
    
    new_location = {
        'lat': float(data.get('lat', cameras[camera_id].get('location', {}).get('lat', 0))),
        'lng': float(data.get('lng', cameras[camera_id].get('location', {}).get('lng', 0))),
        'name': data.get('name', cameras[camera_id].get('location', {}).get('name', camera_id))
    }
    
    cameras[camera_id]['location'] = new_location
    print(f"✅ [API] Updated {camera_id} location: {new_location}")
    
    return jsonify({'success': True, 'location': cameras[camera_id]['location']})

@app.route('/api/cameras/<camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """Delete a camera"""
    if camera_id not in cameras:
        return jsonify({'error': 'Camera not found'}), 404
    
    # Stop camera if active
    if cameras[camera_id].get('active'):
        if cameras[camera_id].get('cap'):
            try:
                cameras[camera_id]['cap'].release()
            except:
                pass
        cameras[camera_id]['active'] = False
    
    # Delete trial image if it exists
    if cameras[camera_id].get('is_trial') and cameras[camera_id].get('image_path'):
        image_path = Path(cameras[camera_id]['image_path'])
        if image_path.exists():
            try:
                image_path.unlink()
                print(f"🗑️  Deleted trial image: {image_path}")
            except Exception as e:
                print(f"⚠️  Error deleting image: {e}")
    
    # Remove from cameras dict
    del cameras[camera_id]
    print(f"✅ [API] Deleted camera: {camera_id}")
    return jsonify({'success': True})

@app.route('/api/trial/upload', methods=['POST'])
def upload_trial_image():
    """Upload an image for trial mode"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
    
    camera_id = request.form.get('camera_id')
    name = request.form.get('name', 'Trial Camera')
    lat = float(request.form.get('lat', 0))
    lng = float(request.form.get('lng', 0))
    
    if not camera_id:
        return jsonify({'error': 'Camera ID is required'}), 400
    
    # Check trial camera limit
    trial_count = sum(1 for cam in cameras.values() if cam.get('is_trial', False))
    if trial_count >= 5:
        return jsonify({'error': 'Maximum 5 trial cameras allowed'}), 400
    
    # Save file
    filename = secure_filename(f"{camera_id}_{file.filename}")
    filepath = UPLOAD_FOLDER / filename
    file.save(filepath)
    
    # Create or update camera
    if camera_id not in cameras:
        cameras[camera_id] = {
            'cap': None,
            'location': {},
            'active': False,
            'is_trial': True
        }
    
    cameras[camera_id]['location'] = {
        'lat': lat,
        'lng': lng,
        'name': name
    }
    cameras[camera_id]['is_trial'] = True
    cameras[camera_id]['image_path'] = str(filepath)
    cameras[camera_id]['image_url'] = f'/api/trial/image/{camera_id}'
    
    print(f"✅ [API] Uploaded trial image for {camera_id}: {filepath}")
    return jsonify({
        'success': True,
        'camera_id': camera_id,
        'image_url': cameras[camera_id]['image_url'],
        'location': cameras[camera_id]['location']
    })

@app.route('/api/trial/image/<camera_id>', methods=['GET'])
def get_trial_image(camera_id):
    """Get trial image for a camera"""
    if camera_id not in cameras:
        return jsonify({'error': 'Camera not found'}), 404
    
    if not cameras[camera_id].get('is_trial'):
        return jsonify({'error': 'Not a trial camera'}), 400
    
    image_path = cameras[camera_id].get('image_path')
    if not image_path or not Path(image_path).exists():
        return jsonify({'error': 'Image not found'}), 404
    
    return send_from_directory(UPLOAD_FOLDER, Path(image_path).name)

@app.route('/api/trial/detect', methods=['POST'])
def detect_trial_image():
    """Process trial image for vehicle detection"""
    data = request.json
    camera_id = data.get('camera_id')
    
    if not camera_id:
        return jsonify({'error': 'Camera ID is required'}), 400
    
    if camera_id not in cameras:
        return jsonify({'error': 'Camera not found'}), 404
    
    if not cameras[camera_id].get('is_trial'):
        return jsonify({'error': 'Not a trial camera'}), 400
    
    image_path = cameras[camera_id].get('image_path')
    if not image_path or not Path(image_path).exists():
        return jsonify({'error': 'Image not found'}), 404
    
    # Read image
    frame = cv2.imread(image_path)
    if frame is None:
        return jsonify({'error': 'Failed to read image'}), 400
    
    # Store current detection count before processing
    detection_count_before = {}
    for plate, dets in detections_history.items():
        detection_count_before[plate] = len(dets)
    
    # Process frame for detection (this will trigger notifications if vehicles are registered)
    # process_frame doesn't return anything, it modifies detections_history
    process_frame(camera_id, frame)
    
    # Extract new detections (ones added after processing)
    formatted_detections = []
    for plate_number, dets in detections_history.items():
        if plate_number in detection_count_before:
            # Get new detections (ones added after processing)
            new_dets = dets[detection_count_before[plate_number]:]
        else:
            # All detections are new
            new_dets = dets
        
        # Filter detections for this camera_id
        for det in new_dets:
            if det.get('camera_id') == camera_id:
                formatted_detections.append({
                    'plate_number': plate_number,
                    'confidence': det.get('confidence', 0),
                    'camera_id': camera_id,
                    'timestamp': det.get('timestamp', timestamp()),
                    'location': cameras[camera_id].get('location', {}),
                    'status': det.get('status', 'detected')
                })
    
    print(f"✅ [API] Trial detection for {camera_id}: {len(formatted_detections)} detections")
    return jsonify({
        'success': True,
        'detections': formatted_detections,
        'camera_id': camera_id
    })

@app.route('/api/detections', methods=['GET'])
def get_detections():
    """Get all detection history"""
    return jsonify(detections_history)

@app.route('/api/detections/reset', methods=['POST'])
def reset_detections():
    """Reset all detection history and tracking data"""
    global detections_history, plate_camera_status, vehicle_timers, vehicle_exits, vehicle_first_seen, camera1_detection_count
    
    with timer_lock:
        # Cancel all active timers
        for plate_number, timer_info in list(vehicle_timers.items()):
            if 'timer' in timer_info and timer_info['timer']:
                try:
                    timer_info['timer'].cancel()
                except:
                    pass
        
        # Clear all tracking data
        detections_history.clear()
        plate_camera_status.clear()
        vehicle_timers.clear()
        vehicle_exits.clear()
        vehicle_first_seen.clear()
        camera1_detection_count.clear()
    
    print("🔄 [API] All detections and tracking data reset")
    return jsonify({'success': True, 'message': 'All detections reset successfully'})

@app.route('/api/detections/<plate_number>', methods=['GET'])
def get_plate_detections(plate_number):
    """Get detection history for a specific plate"""
    # Prevent "reset" from being treated as a plate number
    if plate_number == 'reset':
        return jsonify({'error': 'Invalid endpoint. Use POST /api/detections/reset to reset detections.'}), 405
    
    if plate_number not in detections_history:
        return jsonify({'error': 'Plate not found'}), 404
    
    detections = detections_history[plate_number]
    range_info = calculate_vehicle_range(plate_number)
    
    return jsonify({
        'plate_number': plate_number,
        'detections': detections,
        'range': range_info
    })

@app.route('/api/ranges', methods=['GET'])
def get_all_ranges():
    """Get vehicle location ranges for all detected plates"""
    ranges = {}
    for plate_number in detections_history:
        range_info = calculate_vehicle_range(plate_number)
        if range_info:
            ranges[plate_number] = range_info
    
    return jsonify(ranges)

@app.route('/api/timers', methods=['GET'])
def get_active_timers():
    """Get active 30-second timers for vehicles"""
    with timer_lock:
        active_timers = {}
        current_time = time.time()
        for plate_number, timer_info in vehicle_timers.items():
            elapsed = current_time - timer_info['start_time']
            remaining = max(0, 30.0 - elapsed)
            active_timers[plate_number] = {
                'camera_id': timer_info.get('current_camera', timer_info.get('first_camera', 'unknown')),
                'location': timer_info['location'],
                'remaining_seconds': round(remaining, 1),
                'elapsed_seconds': round(elapsed, 1),
                'path': ' -> '.join(timer_info.get('path', [])) if timer_info.get('path') else None
            }
        return jsonify(active_timers)

@socketio.on('connect')
def handle_connect():
    active_clients.add(request.sid)
    client_count = len(active_clients)
    print(f"✅ [CONNECTION] Client connected: {request.sid}")
    print(f"   📊 Total active clients: {client_count}")
    emit('connected', {'message': 'Connected to ALPR server', 'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    active_clients.discard(request.sid)
    client_count = len(active_clients)
    print(f"❌ [CONNECTION] Client disconnected: {request.sid}")
    print(f"   📊 Total active clients: {client_count}")

def list_available_cameras():
    """List all available camera indices with simple naming - Enhanced for external cameras"""
    import platform
    cameras_info = []
    
    print("🔍 [CAMERA] Scanning for available cameras...")
    
    # Try indices 0-15 to find available cameras (increased range for external cameras)
    for i in range(16):
        cap = None
        try:
            # Try multiple backends for better compatibility
            backends_to_try = []
            if platform.system() == 'Darwin':
                # macOS: Try AVFoundation first (best for external cameras), then ANY
                backends_to_try = [cv2.CAP_AVFOUNDATION, cv2.CAP_ANY]
            else:
                backends_to_try = [cv2.CAP_ANY, cv2.CAP_V4L2]
            
            camera_found = False
            for backend in backends_to_try:
                try:
                    cap = cv2.VideoCapture(i, backend)
                    if cap.isOpened():
                        # Set properties to help with initialization
                        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        
                        # Give it more time to initialize (especially for external cameras)
                        time.sleep(0.2)
                        
                        # Try reading multiple frames to ensure stability
                        frames_read = 0
                        valid_frame = None
                        for attempt in range(5):
                            ret, frame = cap.read()
                            if ret and frame is not None and frame.size > 0:
                                frames_read += 1
                                valid_frame = frame
                                if frames_read >= 2:  # Need at least 2 successful reads
                                    break
                            time.sleep(0.05)
                        
                        if valid_frame is not None and frames_read >= 2:
                            # Get camera properties for better identification
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            
                            # Simple naming: Camera 0, Camera 1, etc.
                            camera_name = f"Camera {i}"
                            camera_type = "Built-in" if i == 0 else "External"
                            
                            cameras_info.append({
                                'index': i,
                                'type': camera_type,
                                'name': camera_name,
                                'display_name': camera_name,
                                'resolution': f"{width}x{height}",
                                'backend': backend
                            })
                            print(f"   ✅ Found {camera_name} at index {i} (backend: {backend}, {width}x{height})")
                            camera_found = True
                            break
                        else:
                            cap.release()
                            cap = None
                except Exception as be:
                    if cap:
                        cap.release()
                        cap = None
                    continue
            
            if not camera_found:
                # Last attempt with default backend (no backend specified)
                try:
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        time.sleep(0.2)
                        frames_read = 0
                        valid_frame = None
                        for attempt in range(5):
                            ret, frame = cap.read()
                            if ret and frame is not None and frame.size > 0:
                                frames_read += 1
                                valid_frame = frame
                                if frames_read >= 2:
                                    break
                            time.sleep(0.05)
                        
                        if valid_frame is not None and frames_read >= 2:
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            camera_name = f"Camera {i}"
                            camera_type = "Built-in" if i == 0 else "External"
                            cameras_info.append({
                                'index': i,
                                'type': camera_type,
                                'name': camera_name,
                                'display_name': camera_name,
                                'resolution': f"{width}x{height}",
                                'backend': 'default'
                            })
                            print(f"   ✅ Found {camera_name} at index {i} (default backend, {width}x{height})")
                except Exception as e:
                    pass
                    
        except Exception as e:
            print(f"   ⚠️  Error checking camera {i}: {e}")
        finally:
            if cap is not None:
                cap.release()
                time.sleep(0.1)  # Small delay between camera checks
    
    print(f"   📊 Total cameras found: {len(cameras_info)}")
    if len(cameras_info) == 0:
        print("   ⚠️  No cameras detected! Check:")
        print("      - Camera permissions in System Settings")
        print("      - Camera is not being used by another app")
        print("      - External camera is properly connected")
    return cameras_info

@app.route('/api/cameras/available', methods=['GET'])
def get_available_cameras():
    """Get list of available camera indices with proper naming"""
    cameras_info = list_available_cameras()
    
    print(f"📡 [API] Returning {len(cameras_info)} cameras to frontend")
    
    # Separate built-in and external
    builtin = [c for c in cameras_info if c['type'] == 'Built-in']
    external = [c for c in cameras_info if c['type'] == 'External']
    
    # Return all cameras - built-in first, then external
    # Return ALL external cameras, not just the first one
    result = {
        'builtin': builtin[0] if builtin else None,
        'external': external,  # Return ALL external cameras as array
        'all_cameras': cameras_info  # Also return all for debugging
    }
    
    print(f"   📊 Built-in: {len(builtin)}, External: {len(external)}")
    if len(external) > 0:
        print(f"   📷 External cameras: {[c['index'] for c in external]}")
    return jsonify(result)

@socketio.on('start_camera')
def handle_start_camera(data):
    camera_id = data.get('camera_id')
    camera_index = data.get('camera_index', 0)  # Default to webcam 0
    
    print(f"🎥 [CAMERA] Request to start {camera_id} on camera index {camera_index}")
    
    if camera_id not in cameras:
        error_msg = f'Invalid camera_id: {camera_id}'
        print(f"   ❌ Error: {error_msg}")
        emit('error', {'message': error_msg})
        return
    
    camera = cameras[camera_id]
    
    if camera['active']:
        error_msg = f'{camera_id} is already active'
        print(f"   ⚠️  Warning: {error_msg}")
        emit('error', {'message': error_msg})
        return
    
    # Try different backends for better compatibility with external cameras
    backends = [
        cv2.CAP_AVFOUNDATION,  # macOS native (best for external cameras)
        cv2.CAP_ANY
    ]
    
    cap = None
    for backend in backends:
        try:
            cap = cv2.VideoCapture(camera_index, backend)
            if cap.isOpened():
                # Try to read a frame to confirm it's working
                ret, test_frame = cap.read()
                if ret and test_frame is not None:
                    print(f"[{camera_id}] Camera {camera_index} opened with backend {backend}")
                    break
                else:
                    cap.release()
                    cap = None
        except Exception as e:
            print(f"[{camera_id}] Backend {backend} failed: {e}")
            if cap:
                cap.release()
                cap = None
    
    if cap is None or not cap.isOpened():
        # Last attempt with default backend
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            available = list_available_cameras()
            error_msg = f'Could not open camera {camera_index}. '
            error_msg += f'Available cameras: {available}. '
            error_msg += 'Please check: 1) Camera permissions in System Settings, '
            error_msg += '2) Camera is not being used by another app'
            emit('error', {'message': error_msg})
            return
    
    # Set camera properties for better performance (with error handling)
    try:
        # Lower resolution for USB cameras to improve FPS
        # Built-in cameras can handle higher res, USB cameras benefit from lower
        if camera_index == 0:
            # Built-in camera - standard resolution
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        else:
            # External/USB camera - lower resolution for better FPS
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        
        cap.set(cv2.CAP_PROP_FPS, 30)
        # Small buffer size to reduce latency and get latest frame
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Auto exposure and auto focus can slow things down - disable if possible
        try:
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual exposure
        except:
            pass
    except Exception as e:
        print(f"[{camera_id}] Warning: Could not set some camera properties: {e}")
    
    # Warm up the camera by reading a few frames
    print(f"   🔥 [{camera_id}] Warming up camera...")
    for i in range(5):
        ret, _ = cap.read()
        if ret:
            break
        time.sleep(0.1)
    
    camera['cap'] = cap
    camera['active'] = True
    camera['_camera_index'] = camera_index  # Store index for potential reopening
    
    camera_type = "Built-in" if camera_index == 0 else "External"
    print(f"   ✅ [{camera_id}] {camera_type} Camera (Index {camera_index}) opened successfully")
    print(f"   🎬 Starting video capture thread for {camera_id}...")
    
    # Start capture thread
    thread = threading.Thread(target=capture_and_send, args=(camera_id,), daemon=True)
    thread.start()
    
    success_msg = f'{camera_type} Camera (Index {camera_index}) started successfully'
    print(f"   ✅ [{camera_id}] {success_msg}")
    emit('camera_started', {
        'camera_id': camera_id, 
        'camera_index': camera_index,
        'message': success_msg
    })

@socketio.on('stop_camera')
def handle_stop_camera(data):
    camera_id = data.get('camera_id')
    
    print(f"🛑 [CAMERA] Request to stop {camera_id}")
    
    if camera_id not in cameras:
        error_msg = f'Invalid camera_id: {camera_id}'
        print(f"   ❌ Error: {error_msg}")
        emit('error', {'message': error_msg})
        return
    
    camera = cameras[camera_id]
    camera['active'] = False
    
    if camera['cap'] is not None:
        camera['cap'].release()
        camera['cap'] = None
        print(f"   ✅ [{camera_id}] Camera released and stopped")
    else:
        print(f"   ⚠️  [{camera_id}] Camera was already stopped")
    
    emit('camera_stopped', {'camera_id': camera_id, 'message': 'Camera stopped successfully'})

# Vehicle tracking API endpoints (Redis-based)
@app.route('/api/detections', methods=['POST'])
def handle_detection():
    """
    Handle vehicle detection event.
    
    Request body:
        {
            "camera_id": "camera1",
            "plate": "MH20EE7598",
            "ts": "2025-11-07T03:36:15Z"
        }
    
    Returns:
        JSON response with status and action
    """
    global vehicle_tracker, notifier
    
    if not vehicle_tracker:
        return jsonify({
            "status": "error",
            "msg": "Vehicle tracking service not initialized"
        }), 503
    
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "msg": "No JSON data provided"}), 400
        
        camera_id = data.get('camera_id')
        plate = data.get('plate')
        ts = data.get('ts')
        
        # Validate inputs
        if not camera_id or not plate:
            return jsonify({
                "status": "error",
                "msg": "Missing required fields: camera_id, plate"
            }), 400
        
        # Use current timestamp if not provided
        if not ts:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).isoformat()
        
        # Process detection
        result = vehicle_tracker.on_detect(plate, camera_id, ts)
        
        # Send notification based on action
        if notifier and result.get('action') in ['ENTRY', 'EXIT', 'PARKED']:
            action = result.get('action')
            if action == 'ENTRY':
                notifier.notify_owner(plate, f"detected at {camera_id} - entry", "entry")
            elif action == 'EXIT':
                notifier.notify_owner(plate, f"exit at {camera_id}", "exit")
            elif action == 'PARKED':
                last_cam = result.get('last_seen_camera', camera_id)
                notifier.notify_owner(
                    plate,
                    f"last seen at {last_cam} (near gate) at {ts}",
                    "parked"
                )
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        print(f"❌ Error in detection handler: {e}")
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "msg": str(e)
        }), 500

@app.route('/api/vehicle/<plate>', methods=['GET'])
def get_vehicle_state(plate):
    """Get current vehicle state and path history."""
    global vehicle_tracker
    
    if not vehicle_tracker:
        return jsonify({
            "status": "error",
            "msg": "Vehicle tracking service not initialized"
        }), 503
    
    try:
        vehicle = vehicle_tracker.get_vehicle(plate)
        if not vehicle:
            return jsonify({
                "status": "error",
                "msg": "Vehicle not found"
            }), 404
        
        # Parse path_history from JSON string
        if isinstance(vehicle.get('path_history'), str):
            vehicle['path_history'] = json.loads(vehicle['path_history'])
        
        return jsonify({
            "status": "ok",
            "vehicle": vehicle
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "msg": str(e)
        }), 500

@app.route('/api/camera/<camera_id>', methods=['POST'])
def update_camera_metadata_endpoint(camera_id):
    """Update camera metadata (lat, lon, name)."""
    global vehicle_tracker
    
    if not vehicle_tracker:
        return jsonify({
            "status": "error",
            "msg": "Vehicle tracking service not initialized"
        }), 503
    
    try:
        data = request.json
        lat = float(data.get('lat', 0))
        lon = float(data.get('lng', data.get('lon', 0)))
        name = data.get('name', camera_id)
        
        vehicle_tracker.set_camera_metadata(camera_id, lat, lon, name)
        
        # Also update local cameras dict
        if camera_id in cameras:
            cameras[camera_id]['location'] = {
                'lat': lat,
                'lng': lon,
                'name': name
            }
        
        return jsonify({
            "status": "ok",
            "camera_id": camera_id,
            "location": {"lat": lat, "lng": lon, "name": name}
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "msg": str(e)
        }), 500

@app.route('/api/vehicles/active', methods=['GET'])
def get_active_vehicles_endpoint():
    """List all actively tracked vehicles."""
    global vehicle_tracker
    
    if not vehicle_tracker:
        return jsonify({
            "status": "error",
            "msg": "Vehicle tracking service not initialized"
        }), 503
    
    try:
        vehicles = vehicle_tracker.get_active_vehicles()
        # Parse path_history for each vehicle
        for vehicle in vehicles:
            if isinstance(vehicle.get('path_history'), str):
                vehicle['path_history'] = json.loads(vehicle['path_history'])
        
        return jsonify({
            "status": "ok",
            "count": len(vehicles),
            "vehicles": vehicles
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "msg": str(e)
        }), 500

# Vehicle database API endpoints
@app.route('/api/vehicles', methods=['GET'])
def get_vehicles():
    """Get all registered vehicles"""
    try:
        vehicles = Vehicle.query.all()
        return jsonify({
            'status': 'success',
            'count': len(vehicles),
            'vehicles': [vehicle.to_dict() for vehicle in vehicles]
        })
    except Exception as e:
        print(f"❌ Error fetching vehicles: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/vehicles', methods=['POST'])
def create_vehicle():
    """Create a new vehicle registration"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        phone_number = data.get('phone_number', '').strip()
        vehicle_number = data.get('vehicle_number', '').strip().upper()
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': 'Name is required'
            }), 400
        
        if not phone_number:
            return jsonify({
                'status': 'error',
                'message': 'Phone number is required'
            }), 400
        
        if not vehicle_number:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle number is required'
            }), 400
        
        # Check if vehicle number already exists
        existing_vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number).first()
        if existing_vehicle:
            return jsonify({
                'status': 'error',
                'message': f'Vehicle with number {vehicle_number} already exists'
            }), 400
        
        # Create new vehicle
        vehicle = Vehicle(
            name=name,
            phone_number=phone_number,
            vehicle_number=vehicle_number
        )
        
        db.session.add(vehicle)
        db.session.commit()
        
        print(f"✅ Vehicle registered: {vehicle_number} - {name}")
        
        return jsonify({
            'status': 'success',
            'message': 'Vehicle registered successfully',
            'vehicle': vehicle.to_dict()
        }), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error creating vehicle: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/vehicles/<vehicle_number>', methods=['GET'])
def get_vehicle_by_number(vehicle_number):
    """Get vehicle by vehicle number (plate number)"""
    try:
        vehicle = Vehicle.query.filter_by(vehicle_number=vehicle_number.upper()).first()
        if not vehicle:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'vehicle': vehicle.to_dict()
        })
    except Exception as e:
        print(f"❌ Error fetching vehicle: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/vehicles/<int:vehicle_id>', methods=['DELETE'])
def delete_vehicle(vehicle_id):
    """Delete a vehicle by ID"""
    try:
        vehicle = Vehicle.query.get(vehicle_id)
        if not vehicle:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle not found'
            }), 404
        
        db.session.delete(vehicle)
        db.session.commit()
        
        print(f"✅ Vehicle deleted: {vehicle.vehicle_number}")
        
        return jsonify({
            'status': 'success',
            'message': 'Vehicle deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error deleting vehicle: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Telegram integration endpoints
@app.route('/api/vehicles/<vehicle_number>/telegram', methods=['POST'])
def link_telegram(vehicle_number):
    """Link Telegram chat ID to a vehicle"""
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        chat_id = data.get('telegram_chat_id', '').strip()
        if not chat_id:
            return jsonify({
                'status': 'error',
                'message': 'telegram_chat_id is required'
            }), 400
        
        # Normalize vehicle number
        normalized_plate = vehicle_number.upper().strip()
        
        # Find vehicle
        vehicle = Vehicle.query.filter_by(vehicle_number=normalized_plate).first()
        if not vehicle:
            return jsonify({
                'status': 'error',
                'message': f'Vehicle with number {normalized_plate} not found'
            }), 404
        
        # Update Telegram chat ID
        vehicle.telegram_chat_id = chat_id
        db.session.commit()
        
        print(f"✅ Telegram chat ID linked to {normalized_plate}: {chat_id}")
        
        return jsonify({
            'status': 'success',
            'message': 'Telegram chat ID linked successfully',
            'vehicle': vehicle.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error linking Telegram: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/vehicles/<vehicle_number>/telegram', methods=['DELETE'])
def unlink_telegram(vehicle_number):
    """Unlink Telegram chat ID from a vehicle"""
    try:
        # Normalize vehicle number
        normalized_plate = vehicle_number.upper().strip()
        
        # Find vehicle
        vehicle = Vehicle.query.filter_by(vehicle_number=normalized_plate).first()
        if not vehicle:
            return jsonify({
                'status': 'error',
                'message': f'Vehicle with number {normalized_plate} not found'
            }), 404
        
        # Remove Telegram chat ID
        vehicle.telegram_chat_id = None
        db.session.commit()
        
        print(f"✅ Telegram chat ID unlinked from {normalized_plate}")
        
        return jsonify({
            'status': 'success',
            'message': 'Telegram chat ID unlinked successfully',
            'vehicle': vehicle.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error unlinking Telegram: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/telegram/bot-info', methods=['GET'])
def get_telegram_bot_info():
    """Get Telegram bot information (to verify bot token)"""
    try:
        telegram_service = get_telegram_service()
        
        if not telegram_service.enabled:
            return jsonify({
                'status': 'error',
                'message': 'Telegram service is disabled',
                'enabled': False
            }), 400
        
        bot_info = telegram_service.get_bot_info()
        
        if bot_info:
            return jsonify({
                'status': 'success',
                'enabled': True,
                'bot_info': bot_info
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to get bot information. Check TELEGRAM_BOT_TOKEN.',
                'enabled': True
            }), 500
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/telegram/test/<vehicle_number>', methods=['POST'])
def test_telegram_notification(vehicle_number):
    """Test Telegram notification for a vehicle (for testing purposes)"""
    try:
        # Normalize vehicle number
        normalized_plate = vehicle_number.upper().strip()
        
        # Find vehicle
        vehicle = Vehicle.query.filter_by(vehicle_number=normalized_plate).first()
        if not vehicle:
            return jsonify({
                'status': 'error',
                'message': f'Vehicle with number {normalized_plate} not found'
            }), 404
        
        if not vehicle.telegram_chat_id:
            return jsonify({
                'status': 'error',
                'message': 'Vehicle has no Telegram chat ID linked'
            }), 400
        
        # Get test location (use camera1 location as default)
        test_location = cameras.get('camera1', {}).get('location', {
            'lat': 12.968194,
            'lng': 79.155917,
            'name': 'Test Camera'
        })
        
        # Send test notification
        telegram_service = get_telegram_service()
        if not telegram_service.enabled:
            return jsonify({
                'status': 'error',
                'message': 'Telegram service is disabled'
            }), 400
        
        results = telegram_service.send_vehicle_alert(
            chat_id=vehicle.telegram_chat_id,
            user_name=vehicle.name,
            vehicle_number=normalized_plate,
            camera_location_name=test_location.get('name', 'Test Location'),
            latitude=test_location.get('lat', 0),
            longitude=test_location.get('lng', 0),
            send_location=True
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Test notification sent',
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Starting ALPR Flask Server...")
    print("=" * 60)
    
    # Check if server is already running
    PORT = int(os.getenv("PORT", 7860))  # Default to 7860 for Hugging Face Spaces
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', PORT))
        sock.close()
        if result == 0:
            print(f"\n⚠️  WARNING: Port {PORT} is already in use!")
            print(f"   Another server instance may be running.")
            print(f"   Please stop it first:")
            print(f"   python3 stop_server.py")
            print(f"   or")
            print(f"   pkill -f 'python.*app.py'")
            print(f"\n   Continuing anyway... (this may cause conflicts)")
            print("=" * 60)
    except Exception as e:
        pass  # Ignore socket check errors
    
    # Initialize database first
    init_database()
    # Then initialize models
    init_models()
    
    print(f"\n📡 Server starting on http://localhost:{PORT}")
    print(f"🌐 Web interface: http://localhost:3000 (React)")
    print(f"📡 API endpoint: http://localhost:{PORT}")
    
    # Initialize Telegram bot for user registration
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_enabled = os.getenv('TELEGRAM_ENABLED', 'false').lower() == 'true'
    
    # CRITICAL FIX: Disable Flask's reloader when Telegram bot is enabled
    # Flask's debug mode with reloader creates a subprocess that also starts a bot instance
    # This causes "Conflict: terminated by other getUpdates request" errors
    # Solution: Disable reloader (use_reloader=False) when bot is enabled
    use_reloader = not (telegram_enabled and bot_token)  # Disable reloader if bot enabled
    
    if telegram_enabled and bot_token:
        try:
            print(f"\n🤖 Initializing Telegram Bot...")
            if not use_reloader:
                print(f"   ⚠️  Auto-reload DISABLED (prevents bot conflicts)")
            
            # Start Telegram bot in background thread with Flask app
            telegram_bot = start_bot_thread(bot_token, app)
            if telegram_bot:
                print(f"✅ Telegram Bot: Started (Polling mode)")
                print(f"   Users can register via Telegram bot")
            else:
                print(f"⚠️  Telegram Bot: Failed to start")
        except Exception as e:
            print(f"⚠️  Telegram Bot: Error starting bot: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"ℹ️  Telegram Bot: Disabled (set TELEGRAM_BOT_TOKEN and TELEGRAM_ENABLED=true to enable)")
    
    print("\n" + "=" * 60)
    print("✅ Server ready! Waiting for client connections...")
    if telegram_enabled and bot_token:
        print("ℹ️  Note: Auto-reload is disabled when Telegram bot is enabled")
    print("=" * 60 + "\n")
    
    # Run Flask - reloader is disabled when bot is enabled to prevent conflicts
    socketio.run(app, host='0.0.0.0', port=PORT, debug=True, use_reloader=use_reloader, allow_unsafe_werkzeug=True)

