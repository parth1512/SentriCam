# How to Start the Frontend

## Quick Start

The frontend is a **separate server** that must be running alongside the backend.

### Step 1: Check Backend is Running
```bash
cd web
python3 check_server.py
```

You should see: `✅ One server instance running`

### Step 2: Start Frontend

**Option A: Using npm directly**
```bash
cd web
npm start
```

**Option B: Using the convenience script**
```bash
cd web
./start_frontend.sh
```

### Step 3: Open Browser
- Frontend will open automatically at: **http://localhost:5001**
- Or manually open: http://localhost:5001

## Important Notes

1. **Two servers required:**
   - Backend: Port 5002 (Flask + Telegram bot)
   - Frontend: Port 5001 (React app)

2. **Both must be running:**
   - Backend handles API requests and Socket.io
   - Frontend provides the web interface

3. **Start order:**
   - Start backend first: `python3 start_server.py`
   - Then start frontend: `npm start`

## Troubleshooting

### "Port 5001 already in use"
```bash
# Kill the process using port 5001
kill -9 $(lsof -ti:5001)
# Then start again
npm start
```

### "Cannot connect to server"
- Make sure backend is running on port 5002
- Check: `curl http://localhost:5002`
- Start backend: `python3 start_server.py`

### "Module not found"
```bash
# Install dependencies
cd web
npm install
```

### Frontend loads but shows "Disconnected"
- Click the "🔌 Connect" button in the UI
- Or refresh the page

## Running in Development

You need **two terminal windows**:

**Terminal 1 (Backend):**
```bash
cd web
python3 start_server.py
```

**Terminal 2 (Frontend):**
```bash
cd web
npm start
```

## What You Should See

### Backend (Terminal 1):
```
✅ Server ready! Waiting for client connections...
✅ Telegram Bot: Started (Polling mode)
 * Running on http://127.0.0.1:5002
```

### Frontend (Terminal 2):
```
Compiled successfully!
You can now view alpr-frontend in the browser.
  Local:            http://localhost:5001
```

### Browser:
- React app loads at http://localhost:5001
- Status shows "Connected" (or click "Connect" button)
- You can see cameras, vehicles, and maps

## Stopping

### Stop Frontend:
- Press `Ctrl+C` in the terminal where `npm start` is running

### Stop Backend:
- Press `Ctrl+C` in the terminal where backend is running
- Or use: `python3 stop_server.py`

## Need More Help?

See `FRONTEND_TROUBLESHOOTING.md` for detailed troubleshooting guide.




