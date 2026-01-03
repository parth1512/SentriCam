"""
================================================================================
REMEMBER: Activate your Python virtual environment before running this script!
================================================================================
Example: source venv/bin/activate
Or:      conda activate your_env_name
================================================================================

Performance Test Script for SentriCam Project

This script measures key performance metrics for Table 4: Performance Evaluation.

IMPORTANT NOTE:
- The 'Page Load Time (React App)' metric CANNOT be measured by this script.
- To measure Page Load Time, use:
  * Chrome DevTools -> Lighthouse tab (run a performance audit)
  * Chrome DevTools -> Network tab (check the "Load" time)
  * Or use browser performance APIs in your React application

This script measures:
1. AI Pipeline processing time (per frame)
2. Database Match query time
3. Telegram API call round-trip time
4. End-to-End Backend Alert Latency
"""

import time
import sqlite3
import os
import requests
import random
import string
import sys
from pathlib import Path
import cv2
import numpy as np

# Load environment variables from .env file (if available)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, will use environment variables only

# ============================================================================
# CONFIGURATION: Adjust these paths as needed
# ============================================================================
# Name of your YOLO weights file (should be in the same directory as this script)
YOLO_WEIGHTS_FILE = "best.pt"

# ============================================================================
# Add src directory to path (for importing detector and OCR)
# Looks for src folder in the same directory as this script, or parent directory
# ============================================================================
script_dir = Path(__file__).resolve().parent
# Try same directory first, then parent directory
src_paths = [
    script_dir / "src",
    script_dir.parent / "src"
]
for src_path in src_paths:
    if src_path.exists() and (src_path / "detector.py").exists():
        sys.path.insert(0, str(src_path))
        break

# Try to import your actual models (optional - will fall back to mock if not available)
try:
    from detector import PlateDetector
    from ocr_reader import OCR
    from augmentations import preprocess_for_ocr
    MODELS_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: Could not import detector/OCR modules. Using mock values.")
    MODELS_AVAILABLE = False
    PlateDetector = None
    OCR = None
    preprocess_for_ocr = None


# Global variables for models (loaded once)
_detector = None
_ocr = None


def load_models():
    """
    Load YOLOv11 detector and OCR models.
    Call this once before running performance tests.
    
    Returns:
        tuple: (detector, ocr) or (None, None) if models unavailable
    """
    global _detector, _ocr
    
    if not MODELS_AVAILABLE:
        return None, None
    
    # Check if models are already loaded
    if _detector is not None and _ocr is not None:
        return _detector, _ocr
    
    try:
        # Find the weights file - check multiple locations
        script_dir = Path(__file__).resolve().parent
        possible_paths = [
            script_dir / YOLO_WEIGHTS_FILE,  # Same directory as script
            script_dir.parent / YOLO_WEIGHTS_FILE,  # Parent directory
            script_dir.parent / "anpr_project" / YOLO_WEIGHTS_FILE,  # anpr_project subdirectory
        ]
        
        weights_path = None
        for path in possible_paths:
            if path.exists():
                weights_path = path
                break
        
        if weights_path is None:
            print(f"   ⚠️  Weights file '{YOLO_WEIGHTS_FILE}' not found in:")
            for path in possible_paths:
                print(f"      - {path}")
            print(f"   ⚠️  Using mock values.")
            return None, None
        
        print(f"📦 Loading YOLOv11 detector from {weights_path}...")
        _detector = PlateDetector(weights_path=str(weights_path), device="mps")
        print("   ✅ Detector loaded")
        
        print("📦 Loading OCR models...")
        _ocr = OCR()
        print("   ✅ OCR loaded")
        
        return _detector, _ocr
        
    except Exception as e:
        print(f"   ⚠️  Error loading models: {e}")
        print("   ⚠️  Using mock values instead")
        return None, None


def generate_vehicle_number(index=None):
    """
    Generate a random vehicle number for testing.
    
    Args:
        index (int, optional): If provided, ensures uniqueness by incorporating index
        
    Returns:
        str: Vehicle number in format like "ABC1234" or "XY12"
    """
    if index is not None:
        # Use index to ensure uniqueness while maintaining realistic format
        # Format: 2-3 letters + 4-5 digit number (ensures 10,000+ combinations)
        letters = ''.join(random.choices(string.ascii_uppercase, k=random.randint(2, 3)))
        # Use index padded to ensure uniqueness
        numbers = f"{index:05d}"  # 5 digits ensures 100,000 combinations
        return f"{letters}{numbers}"
    else:
        # Format: 2-3 letters followed by 2-4 numbers (e.g., "ABC1234", "XY12")
        letters = ''.join(random.choices(string.ascii_uppercase, k=random.randint(2, 3)))
        numbers = ''.join(random.choices(string.digits, k=random.randint(2, 4)))
        return f"{letters}{numbers}"


def ai_pipeline_mock(frame=None):
    """
    Measure YOLOv11 + Hybrid OCR pipeline processing time.
    
    If models are loaded, uses actual model.predict() code.
    Otherwise, simulates 35-45ms processing time.
    
    Args:
        frame (np.ndarray, optional): Test frame/image. If None, creates a dummy frame.
    
    Returns:
        float: Processing time in milliseconds
    """
    global _detector, _ocr
    
    # Load models if not already loaded
    if _detector is None or _ocr is None:
        _detector, _ocr = load_models()
    
    # If models are available, use REAL measurements
    if _detector is not None and _ocr is not None and MODELS_AVAILABLE:
        # Create a test frame if none provided (640x480 dummy image)
        if frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # Add some noise to make it more realistic
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # MEASURE ACTUAL PROCESSING TIME
        start_time = time.time()
        
        # Step 1: YOLOv11 detection
        dets = _detector.predict(frame, conf=0.35)
        
        # Step 2: OCR on detected plates
        for d in dets:
            crop = PlateDetector.crop(frame, d.bbox)
            crop = preprocess_for_ocr(crop)
            text, ocr_conf = _ocr.recognize_plate(crop)
        
        end_time = time.time()
        processing_time_ms = (end_time - start_time) * 1000
        
        return processing_time_ms
    
    else:
        # FALLBACK: Simulate processing time between 35-45ms
        processing_time_ms = random.uniform(35, 45)
        time.sleep(processing_time_ms / 1000)  # Convert ms to seconds for sleep
        return processing_time_ms


def setup_test_database():
    """
    Create a test SQLite database with 10,000 dummy vehicle records.
    
    Returns:
        str: Path to the database file
    """
    db_path = "test_vehicles.db"
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Users table with indexed VehicleNumber
    cursor.execute("""
        CREATE TABLE Users (
            VehicleNumber TEXT PRIMARY KEY,
            UserName TEXT
        )
    """)
    
    # Create index on VehicleNumber (though PRIMARY KEY already creates an index)
    cursor.execute("CREATE INDEX idx_vehicle_number ON Users(VehicleNumber)")
    
    # Insert 10,000 dummy records
    print("Creating test database with 10,000 vehicle records...")
    records = []
    for i in range(10000):
        # Generate unique vehicle number using index to guarantee uniqueness
        vehicle_number = generate_vehicle_number(index=i)
        user_name = f"User_{i+1}"
        records.append((vehicle_number, user_name))
    
    cursor.executemany("INSERT INTO Users (VehicleNumber, UserName) VALUES (?, ?)", records)
    conn.commit()
    
    print(f"✓ Database created: {db_path}")
    print(f"✓ Total records: {len(records)}")
    
    conn.close()
    return db_path


def database_match_test(db_path):
    """
    Measure the actual time to perform an indexed SELECT query.
    
    This function queries for a vehicle number near the end of the table
    to simulate a realistic lookup scenario.
    
    Args:
        db_path (str): Path to the SQLite database
        
    Returns:
        float: Query time in milliseconds
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get a vehicle number near the end of the table (around record 9500)
    cursor.execute("SELECT VehicleNumber FROM Users LIMIT 1 OFFSET 9500")
    result = cursor.fetchone()
    
    if not result:
        # Fallback: get any vehicle number
        cursor.execute("SELECT VehicleNumber FROM Users LIMIT 1")
        result = cursor.fetchone()
    
    test_vehicle_number = result[0] if result else "TEST123"
    
    # Measure the query time
    start_time = time.time()
    cursor.execute("SELECT UserName FROM Users WHERE VehicleNumber = ?", (test_vehicle_number,))
    result = cursor.fetchone()
    end_time = time.time()
    
    query_time_ms = (end_time - start_time) * 1000
    
    conn.close()
    
    return query_time_ms, test_vehicle_number


def telegram_api_test(bot_token=None):
    """
    Measure the round-trip time of a Telegram Bot API call.
    
    Uses the 'getMe' method which is a simple endpoint that doesn't require
    any parameters and returns basic bot information.
    
    Args:
        bot_token (str, optional): Telegram bot token. If None, user will be prompted.
        
    Returns:
        tuple: (api_time_ms, success) - API call time in milliseconds and success status
    """
    if not bot_token:
        print("\n" + "="*60)
        print("Telegram API Test")
        print("="*60)
        try:
            bot_token = input("Enter your Telegram BOT_TOKEN (or press Enter to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            # Handle non-interactive environments
            bot_token = ""
            print("⏭️  No input available, skipping Telegram API test")
    
    if not bot_token:
        print("⏭️  Skipping Telegram API test (no token provided)")
        return None, False
    
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        end_time = time.time()
        
        api_time_ms = (end_time - start_time) * 1000
        
        if response.status_code == 200:
            return api_time_ms, True
        else:
            print(f"⚠️  API call failed with status code: {response.status_code}")
            return api_time_ms, False
            
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Error during Telegram API call: {str(e)}")
        return None, False


def end_to_end_alert_latency_test(db_path, bot_token=None):
    """
    Simulate the full alert workflow and measure total latency.
    
    Workflow:
    1. AI Pipeline processing (mock)
    2. Database Match query (real)
    3. Telegram API call (real, if token provided)
    
    Args:
        db_path (str): Path to the SQLite database
        bot_token (str, optional): Telegram bot token
        
    Returns:
        dict: Dictionary containing all timing results
    """
    print("\n" + "="*60)
    print("End-to-End Alert Latency Test")
    print("="*60)
    
    total_start_time = time.time()
    
    # Step 1: AI Pipeline
    print("\n1. Running AI Pipeline...")
    ai_time = ai_pipeline_mock()
    
    # Step 2: Database Match
    print("2. Running Database Match query...")
    db_time, vehicle_number = database_match_test(db_path)
    
    # Step 3: Telegram API Call
    print("3. Running Telegram API call...")
    telegram_time, telegram_success = telegram_api_test(bot_token)
    
    total_end_time = time.time()
    total_latency_ms = (total_end_time - total_start_time) * 1000
    
    # Check if real models were used
    global _detector, _ocr
    using_real_models = (_detector is not None and _ocr is not None and MODELS_AVAILABLE)
    
    results = {
        'ai_pipeline_ms': ai_time,
        'database_match_ms': db_time,
        'telegram_api_ms': telegram_time if telegram_success else None,
        'total_latency_ms': total_latency_ms,
        'telegram_success': telegram_success,
        'using_real_models': using_real_models
    }
    
    return results


def print_results(results):
    """
    Print all performance results in a friendly, formatted way.
    
    Args:
        results (dict): Dictionary containing timing results
    """
    print("\n" + "="*60)
    print("PERFORMANCE TEST RESULTS")
    print("="*60)
    
    print(f"\n🤖 AI Pipeline (per frame):")
    print(f"   {results['ai_pipeline_ms']:.2f} ms")
    if results.get('using_real_models', False):
        print(f"   ✅ Using REAL YOLOv11 + OCR models")
    else:
        print(f"   ⚠️  Using MOCK values (models not loaded)")
        print(f"   💡 To get real measurements, ensure models are available")
    
    print(f"\n💾 Database Match:")
    print(f"   {results['database_match_ms']:.2f} ms")
    print(f"   (Indexed SELECT query on 10,000 records)")
    
    print(f"\n📱 Telegram API Call:")
    if results['telegram_api_ms'] is not None:
        print(f"   {results['telegram_api_ms']:.2f} ms")
        print(f"   (Round-trip time to Telegram Bot API)")
    else:
        print(f"   Skipped (no token provided)")
    
    print(f"\n⚡ End-to-End Backend Alert Latency:")
    print(f"   {results['total_latency_ms']:.2f} ms")
    print(f"   (AI Pipeline + Database Match + Telegram API)")
    
    print("\n" + "="*60)
    print("\n📊 Summary for Table 4:")
    print(f"   • AI Pipeline: {results['ai_pipeline_ms']:.2f} ms")
    print(f"   • Database Match: {results['database_match_ms']:.2f} ms")
    if results['telegram_api_ms'] is not None:
        print(f"   • Telegram API: {results['telegram_api_ms']:.2f} ms")
    print(f"   • End-to-End Latency: {results['total_latency_ms']:.2f} ms")
    print(f"   • Page Load Time: Measure using Lighthouse/Network tab in browser DevTools")
    print("="*60 + "\n")


def main():
    """Main function to run all performance tests."""
    print("="*60)
    print("SentriCam Performance Test Suite")
    print("="*60)
    print("\nThis script will measure:")
    print("  1. AI Pipeline processing time")
    print("  2. Database Match query time (real)")
    print("  3. Telegram API call time (real)")
    print("  4. End-to-End Backend Alert Latency")
    print("\n" + "="*60)
    
    # Try to load models (optional - will use mock if unavailable)
    print("\n📦 Attempting to load AI models...")
    detector, ocr = load_models()
    using_real_models = (detector is not None and ocr is not None)
    if using_real_models:
        print("   ✅ Models loaded - will use REAL measurements")
    else:
        print("   ⚠️  Models not available - will use MOCK values")
    
    # Setup test database
    print("\n📦 Setting up test database...")
    db_path = setup_test_database()
    
    # Get bot token from environment variable or prompt user
    print("\n" + "="*60)
    print("Telegram Bot Token")
    print("="*60)
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    
    if bot_token:
        print("✅ Found TELEGRAM_BOT_TOKEN in environment variables")
    else:
        print("ℹ️  TELEGRAM_BOT_TOKEN not found in environment variables")
        try:
            bot_token = input("Enter your Telegram BOT_TOKEN (or press Enter to skip Telegram test): ").strip()
        except (EOFError, KeyboardInterrupt):
            # Handle non-interactive environments
            bot_token = ""
            print("⏭️  No input available, skipping Telegram test")
    
    if not bot_token:
        print("⏭️  Telegram API test will be skipped")
    
    # Run individual tests
    print("\n" + "="*60)
    print("Running Individual Tests")
    print("="*60)
    
    # Test 1: AI Pipeline
    print("\n1️⃣  Testing AI Pipeline...")
    ai_time = ai_pipeline_mock()
    model_type = "REAL models" if using_real_models else "MOCK values"
    print(f"   ✓ AI Pipeline: {ai_time:.2f} ms ({model_type})")
    
    # Test 2: Database Match
    print("\n2️⃣  Testing Database Match...")
    db_time, vehicle_number = database_match_test(db_path)
    print(f"   ✓ Database Match: {db_time:.2f} ms")
    print(f"   ✓ Tested with vehicle: {vehicle_number}")
    
    # Test 3: Telegram API
    print("\n3️⃣  Testing Telegram API...")
    telegram_time, telegram_success = telegram_api_test(bot_token)
    if telegram_success:
        print(f"   ✓ Telegram API: {telegram_time:.2f} ms")
    else:
        print(f"   ⏭️  Telegram API: Skipped")
    
    # Run end-to-end test
    results = end_to_end_alert_latency_test(db_path, bot_token)
    results['using_real_models'] = using_real_models  # Pass the flag to results
    
    # Print final results
    print_results(results)
    
    # Cleanup option
    print("="*60)
    try:
        cleanup = input("Delete test database? (y/n): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        # Handle non-interactive environments - keep database by default
        cleanup = 'n'
        print("⏭️  No input available, keeping test database")
    if cleanup == 'y':
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✓ Deleted {db_path}")
    else:
        print(f"✓ Database kept at: {db_path}")
    
    print("\n✅ Performance testing complete!")


if __name__ == "__main__":
    main()

