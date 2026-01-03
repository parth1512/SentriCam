# ALPR Web Frontend

React.js frontend for the Automatic License Plate Recognition (ALPR) system with real-time vehicle tracking and geolocation.

## Features

- 🎥 **Dual Camera Display**: Real-time video feeds from two cameras
- 🚗 **License Plate Detection**: Automatic detection and OCR recognition
- 📍 **Geolocation Tracking**: Track vehicles between cameras with GPS coordinates
- 🗺️ **Google Maps Integration**: Visualize vehicle location ranges on an interactive map
- ⏱️ **Timestamp Tracking**: Record when plates are detected at each camera
- 📊 **Detection History**: View all detected vehicles and their routes

## Setup

### Prerequisites

- Node.js 16+ and npm
- Python 3.10+ with Flask backend running
- Google Maps API key (for map visualization)

### Installation

1. Install dependencies:
```bash
cd web
npm install
```

2. Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
```

3. Edit `.env` and add your Google Maps API key:
```
REACT_APP_API_URL=http://localhost:5000
REACT_APP_GOOGLE_MAPS_API_KEY=your_actual_api_key_here
```

### Getting a Google Maps API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the "Maps JavaScript API"
4. Create credentials (API Key)
5. Copy the API key to your `.env` file

**Note**: Make sure to restrict your API key in production for security.

## Running the Application

### Development Mode

1. Start the Flask backend (from project root):
```bash
cd web
python app.py
```

2. In a separate terminal, start the React frontend:
```bash
cd web
npm start
```

The app will open at `http://localhost:3000`

### Production Build

```bash
npm run build
```

The built files will be in the `build/` directory.

## Usage

1. **Start Cameras**: Use the Control Panel to start Camera 1 and Camera 2
   - You can select camera index (0 for first webcam, 1 for second, etc.)
   - Set camera locations (latitude, longitude, and name)

2. **View Feeds**: The camera feeds will display in real-time with detected license plates highlighted

3. **Track Vehicles**: 
   - When a plate is detected in both cameras, the system calculates the vehicle's estimated range
   - The range is displayed on the Google Maps view
   - Click on a vehicle in the detection list to highlight it on the map

4. **Monitor Detections**: The detection list shows:
   - All detected license plates
   - Timestamps (first seen, last seen)
   - Estimated location range
   - Route information (which cameras detected the vehicle)

## API Endpoints

The frontend communicates with the Flask backend via:

- **WebSocket**: Real-time video frames and detections (`socket.io`)
- **REST API**: 
  - `GET /api/cameras` - Get camera status
  - `POST /api/cameras/<id>/location` - Update camera location
  - `GET /api/detections` - Get all detections
  - `GET /api/detections/<plate>` - Get specific plate detections
  - `GET /api/ranges` - Get vehicle location ranges

## Project Structure

```
web/
├── src/
│   ├── components/
│   │   ├── CameraView.js      # Camera feed display
│   │   ├── MapView.js         # Google Maps integration
│   │   ├── DetectionList.js   # Vehicle detection list
│   │   └── ControlPanel.js    # Camera controls
│   ├── App.js                 # Main application
│   └── index.js               # Entry point
├── public/                    # Static assets
├── app.py                     # Flask backend
└── package.json               # Dependencies
```

## Troubleshooting

### Maps Not Loading
- Verify your Google Maps API key is correct in `.env`
- Check that the Maps JavaScript API is enabled in Google Cloud Console
- Check browser console for API errors

### Cameras Not Starting
- Make sure cameras are connected and not being used by another application
- Try different camera indices (0, 1, 2, etc.)
- Check backend logs for error messages

### Connection Issues
- Verify Flask backend is running on port 5000
- Check `REACT_APP_API_URL` in `.env` matches your backend URL
- Ensure CORS is properly configured in the backend

## License

Same as the main ALPR project.


