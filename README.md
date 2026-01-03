# ANPR (Automatic Number Plate Recognition) – Research-Grade Implementation

This repository implements an academically structured ANPR pipeline inspired by the paper "Real-Time Vehicle Number Plate Detection and Recognition Using YOLOv5 and OCR" while using the latest Ultralytics YOLO (YOLOv11) for detection and PaddleOCR/EasyOCR for recognition.

## Features
- YOLOv11-based plate detection (pretrained, fine-tuned)
- OCR via PaddleOCR with EasyOCR fallback
- Reproducible 70/20/10 dataset splitting with seed
- Preprocessing and augmentation (resize, normalize, blur, rotation, brightness, flip, zoom, perspective)
- Training and validation logging, plots
- Evaluation: mAP@0.5, mAP@0.5:0.95, Precision, Recall, F1, OCR accuracy (if GT available)
- Inference pipeline returning JSON
- Optional webcam demo and lightweight dashboard
- **🌐 React.js Web Interface**: Real-time dual-camera tracking with Leaflet.js maps
- **📍 Geolocation Tracking**: Track vehicles between cameras with GPS coordinates and range estimation
- **⏱️ Timestamp Recording**: Automatic timestamp and location logging for each detection
- **🚗 Production Vehicle Tracking**: Redis-based state management with deterministic tracking logic
- **📊 Path Recording**: Track vehicle movement between cameras with full path history
- **🔔 Notifications**: Pluggable notification system (Telegram, Webhooks)
- **📝 Structured Logging**: JSON event logs for all tracking events

## Project Structure
```
alpr_project/
  data/
    images/{train,val,test}
    labels/{train,val,test}
    data.yaml
  src/
    split_dataset.py
    augmentations.py
    train_detector.py
    detector.py
    ocr_reader.py
    detect_and_ocr.py
    evaluate.py
    utils.py
    webcam_demo.py
  results/
    plots/
    metrics.json
    sample_outputs/
  web/
    app.py                    # Flask backend with WebSocket support
    src/                      # React.js frontend source
      components/             # React components (CameraView, MapView, etc.)
      App.js
    public/
    templates/
      index.html
    package.json
    README.md                 # Web frontend documentation
  weights/
  requirements.txt

  VEHICLE_TRACKING.md         # Vehicle tracking system documentation
  web/
    services/
      vehicle_tracker.py      # Redis-based vehicle tracking service
      notifier.py             # Notification service
      timer_worker.py         # Background timer worker
    tests/
      test_tracking.py        # Unit and integration tests
  logs/
    vehicle_events.log        # Structured event logs (rotating)
  README.md
```

## Setup
1. Python 3.10+ recommended
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. **Start Redis** (required for vehicle tracking):
```bash
# Install and start Redis locally
# macOS:
brew install redis
brew services start redis

# Linux:
sudo apt-get install redis-server
sudo systemctl start redis
```
4. Ensure PyTorch uses Apple MPS on macOS (M1/M2). YOLO will use `device="mps"` automatically in scripts.
5. **Configure environment variables** (optional, for notifications):
```bash
# Create .env file or set environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379
export TRACKER_WINDOW_SECONDS=30
export ENTRY_CAMERA=camera1

# Notification settings (optional)
export NOTIFY_WEBHOOK=https://your-webhook-url.com/notify
export TELEGRAM_BOT_TOKEN=your_token
export TELEGRAM_CHAT_ID=your_chat_id
```

## Data
Place or point the splitter to your source dataset. This project expects YOLO-format images and labels. The splitter will build the following structure with a reproducible 70/20/10 split under `alpr_project/data`.

If you have ground-truth plate texts for OCR accuracy, provide a CSV at `alpr_project/data/gt_plates.csv` with columns: `filename,text`.

## Usage
- Split dataset:
```bash
python src/split_dataset.py --source-root "<path-to-source-dataset-root>" --seed 42
```
- Train detector (YOLOv11):
```bash
python src/train_detector.py --epochs 100 --model yolo11s.pt --imgsz 640 --device mps
```
- Evaluate detector + OCR:
```bash
python src/evaluate.py --device mps
```
- Inference (single image):
```bash
python src/detect_and_ocr.py --image "/path/to/image.jpg" --device mps
```
- Webcam demo:
```bash
python src/webcam_demo.py --device mps
```
- **Web Interface (Phase 2)**:
```bash
# Install web dependencies
cd web
npm install

# Set up environment variables (create .env file)
# Add your Google Maps API key: REACT_APP_GOOGLE_MAPS_API_KEY=your_key

# Start Flask backend (in one terminal)
cd web
python app.py

# Start React frontend (in another terminal)
cd web
npm start
```
Access the web interface at `http://localhost:3000`

**Web Interface Features:**
- Real-time video feeds from 2 cameras
- Automatic license plate detection and OCR
- Timestamp recording for each detection
- GPS geolocation tracking for each camera
- Vehicle location range calculation (when detected in both cameras)
- Google Maps integration showing vehicle position estimates
- Interactive detection history and route visualization

See `web/README.md` for detailed web interface documentation.

## Vehicle Tracking System

The system includes a production-ready, Redis-based vehicle tracking service with deterministic state management.

### Quick Start

1. **Start Redis**:
   ```bash
   # Start Redis locally
   redis-server

2. **Test the detection endpoint**:
   ```bash
   curl -X POST http://localhost:5002/api/detections \
     -H "Content-Type: application/json" \
     -d '{
       "camera_id": "camera1",
       "plate": "MH20EE7598",
       "ts": "2025-11-07T03:36:15Z"
     }'
   ```

3. **Query vehicle state**:
   ```bash
   curl http://localhost:5002/api/vehicle/MH20EE7598
   ```

4. **List active vehicles**:
   ```bash
   curl http://localhost:5002/api/vehicles/active
   ```

### Features

- **30-second tracking windows** (configurable via `TRACKER_WINDOW_SECONDS`)
- **Path recording**: Tracks vehicle movement between cameras
- **Deterministic state machine**: ENTERED → MOVING → PARKED/EXITED
- **Redis-based**: Concurrency-safe, scalable across multiple instances
- **Structured logging**: All events logged to `logs/vehicle_events.log`
- **Notifications**: Pluggable system for Telegram, WhatsApp, webhooks

### API Endpoints

- `POST /api/detections` - Submit vehicle detection
- `GET /api/vehicle/:plate` - Get vehicle state and path
- `GET /api/vehicles/active` - List all active vehicles
- `POST /api/camera/:id` - Update camera metadata

See [VEHICLE_TRACKING.md](VEHICLE_TRACKING.md) for complete documentation.

### Running Tests

```bash
cd web
pytest tests/test_tracking.py -v
```

## Notes
- If OCR ground truth is unavailable, OCR accuracy is skipped and reported as `null`.
- All metrics and plots are saved to `results/`.



