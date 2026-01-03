# ALPR Web Interface - Quick Start Guide

## Overview

The web interface provides a real-time dual-camera license plate tracking system with geolocation visualization using Google Maps. When a vehicle's license plate is detected in Camera 1 and then in Camera 2, the system calculates the estimated location range where the vehicle is located.

## Architecture

### Backend (Flask)
- **Flask + Socket.IO**: Real-time bidirectional communication
- **OpenCV**: Camera capture and video processing
- **YOLOv11**: License plate detection
- **PaddleOCR/EasyOCR**: Text recognition from detected plates
- **Geolocation Calculation**: Haversine formula for distance calculation between camera locations

### Frontend (React)
- **React.js**: UI framework
- **Socket.IO Client**: Real-time data streaming
- **Google Maps API**: Interactive map visualization
- **Canvas API**: Video frame rendering

## How It Works

1. **Camera Setup**:
   - Each camera has a GPS location (latitude, longitude) and a name
   - Cameras can be started/stopped independently
   - Video feeds are processed frame-by-frame

2. **Detection Process**:
   - Each frame is passed through YOLOv11 for plate detection
   - Detected plates are cropped and processed with OCR
   - When a plate is detected, the system records:
     - License plate number
     - Timestamp
     - Camera ID
     - Camera location (GPS coordinates)
     - Detection confidence

3. **Tracking Logic**:
   - All detections are stored in history
   - When a plate appears in Camera 1: Record timestamp and location
   - When the same plate appears in Camera 2: Record timestamp and location
   - System calculates the estimated range where the vehicle is located

4. **Range Calculation**:
   - Uses the Haversine formula to calculate distance between camera locations
   - Creates a circle with:
     - Center: Midpoint between the two camera locations
     - Radius: Half the distance between cameras
   - If only one camera detects the plate, uses a small radius (50m) around that camera

5. **Visualization**:
   - Camera locations shown as blue markers on the map
   - Vehicle ranges shown as colored circles
   - Detection history displayed in a list with timestamps
   - Click on a vehicle to highlight it on the map

## Setup Instructions

### Prerequisites
1. **Python 3.10+** with all dependencies from `requirements.txt`
2. **Node.js 16+** and npm
3. **Google Maps API Key** (free tier available)

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Install Node.js Dependencies
```bash
cd web
npm install
```

Or use the setup script:
```bash
cd web
chmod +x setup.sh
./setup.sh
```

### Step 3: Configure Google Maps API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Maps JavaScript API**
4. Create an API Key
5. (Recommended) Restrict the API key to your domain/IP for security

### Step 4: Create Environment File

Create `web/.env`:
```
REACT_APP_API_URL=http://localhost:5000
REACT_APP_GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

### Step 5: Start the System

**Terminal 1 - Backend:**
```bash
cd web
python app.py
```
You should see:
```
Models loaded successfully
Starting ALPR Flask server...
Access the web interface at http://localhost:5000
```

**Terminal 2 - Frontend:**
```bash
cd web
npm start
```
The React app will open at `http://localhost:3000`

## Usage

1. **Configure Camera Locations**:
   - Click "📍 Location" button for each camera
   - Enter latitude, longitude, and camera name
   - Click "💾 Save Location"

2. **Start Cameras**:
   - Click "▶ Start (Cam 0)" or "▶ Start (Cam 1)" for each camera
   - The camera index depends on your system:
     - 0 = First connected webcam
     - 1 = Second connected webcam
     - Adjust based on your hardware

3. **Monitor Detections**:
   - License plates will appear highlighted in the video feeds
   - Detection list will populate with detected vehicles
   - Map will show vehicle location ranges

4. **Track Vehicles**:
   - When a plate is detected in both cameras, a range circle appears on the map
   - Click on a vehicle in the detection list to highlight it
   - View timestamps and route information

## API Endpoints

### REST API
- `GET /api/cameras` - Get camera status and locations
- `POST /api/cameras/<camera_id>/location` - Update camera location
- `GET /api/detections` - Get all detection history
- `GET /api/detections/<plate_number>` - Get specific plate information
- `GET /api/ranges` - Get all vehicle location ranges

### WebSocket Events
- `start_camera` - Start a camera stream
- `stop_camera` - Stop a camera stream
- `frame_camera1` - Video frame from camera 1
- `frame_camera2` - Video frame from camera 2

## Troubleshooting

### Maps Not Showing
- Verify Google Maps API key in `.env`
- Check browser console for API errors
- Ensure Maps JavaScript API is enabled in Google Cloud Console
- Check API key restrictions

### Camera Not Starting
- Make sure camera is not used by another application
- Try different camera indices (0, 1, 2, etc.)
- Check system permissions for camera access
- Review backend logs for errors

### No Detections
- Verify weights file exists: `weights/plate_detector.pt`
- Check camera feed is active and showing video
- Adjust detection confidence threshold in `app.py` (default: 0.35)
- Ensure good lighting and plate visibility

### Connection Issues
- Verify Flask backend is running on port 5000
- Check `REACT_APP_API_URL` in `.env`
- Ensure no firewall blocking ports 5000/3000
- Check CORS settings in backend

## Customization

### Adjust Detection Confidence
Edit `web/app.py`, line ~32:
```python
dets = detector.predict(frame, conf=0.35)  # Lower = more detections
```

### Change Camera FPS
Edit `web/app.py`, line ~175:
```python
time.sleep(0.033)  # ~30 FPS (lower value = higher FPS)
```

### Update Default Camera Locations
Edit `web/app.py`, lines ~30-33:
```python
'camera1': {'cap': None, 'location': {'lat': YOUR_LAT, 'lng': YOUR_LNG, 'name': 'Camera 1'}, 'active': False},
```

## Performance Tips

- Reduce video resolution for better performance
- Use lower FPS if system is slow
- Limit detection history size (currently 100 per plate)
- Use GPU acceleration if available (change `device="mps"` to `device="cuda"` on NVIDIA)

## Security Notes

- **Never commit `.env` file** with API keys
- Restrict Google Maps API key in production
- Use HTTPS in production
- Implement authentication for production deployments
- Validate camera inputs and API requests

## Next Steps

- Add authentication/authorization
- Implement database for persistent storage
- Add export functionality (CSV, JSON)
- Create admin dashboard
- Add email/SMS alerts for specific plates
- Implement plate matching algorithms (fuzzy matching)
- Add analytics and reporting


