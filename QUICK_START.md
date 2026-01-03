# Quick Start Guide - Running the ALPR Web Application

## Option 1: Using the Run Script (Easiest)

Simply run:
```bash
./run_web.sh
```

This will automatically:
- Check and install dependencies
- Start the Flask backend
- Start the React frontend

## Option 2: Manual Setup

### Step 1: Install Python Dependencies

If you don't have a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Or install just the web dependencies:
```bash
pip install flask flask-cors flask-socketio python-socketio eventlet
```

### Step 2: Install Node.js Dependencies

```bash
cd web
npm install
cd ..
```

### Step 3: Configure Google Maps API (Optional but Recommended)

Create `web/.env` file:
```bash
cd web
echo "REACT_APP_API_URL=http://localhost:5000" > .env
echo "REACT_APP_GOOGLE_MAPS_API_KEY=YOUR_KEY_HERE" >> .env
cd ..
```

Get your API key from: https://console.cloud.google.com/google/maps-apis

### Step 4: Start the Application

**Terminal 1 - Backend:**
```bash
cd web
python3 app.py
```

**Terminal 2 - Frontend:**
```bash
cd web
npm start
```

### Step 5: Open Browser

Navigate to: **http://localhost:3000**

## Troubleshooting

### Python Module Errors
```bash
# Try with --user flag
pip3 install --user flask flask-cors flask-socketio python-socketio eventlet

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Node.js Errors
```bash
cd web
rm -rf node_modules package-lock.json
npm install
```

### Port Already in Use
```bash
# Kill process on port 5000 (backend)
lsof -ti:5000 | xargs kill -9

# Kill process on port 3000 (frontend)
lsof -ti:3000 | xargs kill -9
```

### Camera Not Working
- Make sure camera permissions are granted
- Try different camera indices (0, 1, 2) in the Control Panel
- Check if camera is being used by another application

### Maps Not Showing
- Add Google Maps API key to `web/.env`
- Make sure Maps JavaScript API is enabled in Google Cloud Console

## What You'll See

1. **Control Panel**: Start/stop cameras and configure locations
2. **Camera Views**: Real-time video feeds from your cameras
3. **Map View**: Google Maps showing camera locations and vehicle ranges
4. **Detection List**: All detected license plates with timestamps

## Need Help?

Check the detailed documentation:
- `WEB_SETUP.md` - Complete setup and architecture guide
- `web/README.md` - Frontend-specific documentation
- `README.md` - Main project documentation


