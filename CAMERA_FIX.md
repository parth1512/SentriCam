# Camera Not Working - Troubleshooting Guide

## Common Issues and Solutions

### 1. Camera Permission Issue (macOS)
**Error:** `OpenCV: not authorized to capture video`

**Solution:**
1. Open **System Settings** (or System Preferences on older macOS)
2. Go to **Privacy & Security** → **Camera**
3. Make sure your terminal app (Terminal/iTerm) has camera access enabled
4. If running from IDE, grant camera access to that application too
5. Restart the backend after granting permissions

### 2. Camera Already in Use
**Error:** Camera opens but shows no video

**Solution:**
- Close other applications using the camera (Zoom, FaceTime, Photo Booth, etc.)
- Restart the backend

### 3. Wrong Camera Index
**Solution:**
- Try different camera indices: 0, 1, 2, etc.
- Use the Control Panel to test different camera indices
- Check available cameras: `python3 -c "import cv2; [print(f'Camera {i}: {cv2.VideoCapture(i).isOpened()}') for i in range(5)]"`

### 4. Missing Weights File
**Error:** `Weights file missing`

**Solution:**
- The app will still run but detection won't work
- Train the model first: `python src/train_detector.py`
- Or download pre-trained weights to `weights/plate_detector.pt`

## Quick Fix Commands

```bash
# Check camera availability
cd /Users/parth/Desktop/AI\ PROJECT/alpr_project
source venv/bin/activate
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera 0:', cap.isOpened()); cap.release()"

# Restart backend
lsof -ti:5000 | xargs kill -9
cd web
python app.py
```

## Testing Camera in Browser

1. Open http://localhost:5001
2. Go to Control Panel
3. Click "📍 Location" and set camera location
4. Try "▶ Start (Cam 0)" first
5. If that doesn't work, try "▶ Start (Cam 1)"
6. Check browser console for WebSocket errors
7. Check backend logs: `tail -f /tmp/alpr_backend.log`

## Grant Camera Permissions (macOS Terminal)

```bash
# This requires manual action in System Settings
# Terminal → System Settings → Privacy & Security → Camera → Enable Terminal
```


