# Commands to Run Backend and Frontend

## Prerequisites
1. **Activate virtual environment** (if not already activated):
   ```bash
   cd "/Users/parth/Desktop/AI PROJECT/alpr_project"
   source .venv/bin/activate
   ```

2. **Ensure Redis is running**:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

---

## 🖥️ Backend (Flask + Socket.IO)

**Terminal 1 - Backend:**
```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web"
source "../.venv/bin/activate"
python app.py
```

**Backend will run on:** `http://localhost:5002`

**Expected output:**
```
📦 Loading YOLO detector from ...
✅ Detector loaded successfully
📦 Loading OCR models (PaddleOCR/EasyOCR)...
✅ OCR loaded successfully
✅ Vehicle tracking service initialized (Redis-based)
✅ Timer worker started
 * Running on http://127.0.0.1:5002
```

---

## 🎨 Frontend (React)

**Terminal 2 - Frontend:**
```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web"
npm start
```

**Frontend will run on:** `http://localhost:5004` (or 5001 if 5004 is busy)

**Expected output:**
```
Compiled successfully!
You can now view alpr-frontend in the browser.
  Local:            http://localhost:5004
```

---

## 🚀 Quick Start (One-Liners)

**Backend:**
```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web" && source "../.venv/bin/activate" && python app.py
```

**Frontend:**
```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web" && npm start
```

---

## 📋 Running in Background

**Backend (background):**
```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web"
source "../.venv/bin/activate"
nohup python app.py > backend.log 2>&1 &
```

**Frontend (background):**
```bash
cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web"
nohup npm start > frontend.log 2>&1 &
```

---

## 🛑 Stopping Services

**Stop Backend:**
```bash
pkill -f "python app.py"
```

**Stop Frontend:**
```bash
pkill -f "react-scripts"
```

**Stop Both:**
```bash
pkill -f "python app.py" && pkill -f "react-scripts"
```

---

## ✅ Verify Services Are Running

```bash
# Check backend
lsof -ti:5002 && echo "✅ Backend running" || echo "❌ Backend not running"

# Check frontend
lsof -ti:5004 && echo "✅ Frontend running" || echo "❌ Frontend not running"

# Check Redis
redis-cli ping && echo "✅ Redis running" || echo "❌ Redis not running"
```

---

## 🔧 Troubleshooting

**Backend won't start:**
- Check if port 5002 is already in use: `lsof -ti:5002`
- Kill existing process: `pkill -f "python app.py"`
- Ensure virtual environment is activated
- Check Redis is running: `redis-cli ping`

**Frontend won't start:**
- Check if port 5004/5001 is already in use
- Kill existing process: `pkill -f "react-scripts"`
- Clear npm cache: `npm cache clean --force`
- Reinstall dependencies: `npm install`

**Redis connection errors:**
- Start Redis: `brew services start redis` (macOS)
- Or: `redis-server` (if installed manually)
- Verify: `redis-cli ping` should return `PONG`





