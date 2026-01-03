# Frontend Troubleshooting Guide

## Problem: Frontend Not Working

### Common Causes

1. **Frontend server is not running**
   - The React dev server must be running separately from the backend
   - Frontend runs on port 5001
   - Backend runs on port 5002

2. **Backend server is not running**
   - Frontend cannot connect to backend API
   - Backend must be running on port 5002

3. **Dependencies not installed**
   - React dependencies must be installed with `npm install`

4. **Port conflicts**
   - Port 5001 or 5002 may be in use by another process

## Quick Fix

### Step 1: Check Backend Status
```bash
cd web
python3 check_server.py
```

If backend is not running:
```bash
python3 start_server.py
```

### Step 2: Start Frontend
```bash
cd web
npm start
```

Or use the convenience script:
```bash
cd web
./start_frontend.sh
```

### Step 3: Verify
1. Backend should be running on: http://localhost:5002
2. Frontend should be running on: http://localhost:5001
3. Open browser to: http://localhost:5001

## Detailed Troubleshooting

### Issue: "Cannot connect to server"

**Symptoms:**
- Frontend loads but shows "Disconnected" status
- "Connect" button doesn't work
- Console shows connection errors

**Solutions:**

1. **Check if backend is running:**
   ```bash
   curl http://localhost:5002
   ```
   Should return HTML or JSON response.

2. **Check backend logs:**
   ```bash
   # Look for "Server ready" message
   # Check for any error messages
   ```

3. **Check CORS settings:**
   - Backend should have CORS enabled
   - Check `app.py` for `CORS(app)` configuration

4. **Check firewall/network:**
   - Make sure port 5002 is accessible
   - Check if firewall is blocking connections

### Issue: "npm start fails"

**Symptoms:**
- Error when running `npm start`
- "Port 5001 already in use"
- Module not found errors

**Solutions:**

1. **Install dependencies:**
   ```bash
   cd web
   npm install
   ```

2. **Check if port 5001 is in use:**
   ```bash
   lsof -ti:5001
   ```
   If something is using the port:
   ```bash
   kill -9 $(lsof -ti:5001)
   ```

3. **Clear npm cache:**
   ```bash
   npm cache clean --force
   npm install
   ```

4. **Delete node_modules and reinstall:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

### Issue: "Frontend loads but API calls fail"

**Symptoms:**
- Frontend UI loads
- But vehicle data, cameras, etc. don't load
- Console shows 404 or CORS errors

**Solutions:**

1. **Check API_BASE_URL:**
   - In `App.js`, `API_BASE_URL` should be `http://localhost:5002`
   - Or set `REACT_APP_API_URL=http://localhost:5002` in `.env` file

2. **Check backend API endpoints:**
   ```bash
   curl http://localhost:5002/api/vehicles
   curl http://localhost:5002/api/cameras
   ```
   Should return JSON data.

3. **Check proxy configuration:**
   - `package.json` has `"proxy": "http://localhost:5002"`
   - This helps with API requests in development

### Issue: "Socket.io connection fails"

**Symptoms:**
- Frontend connects but Socket.io doesn't work
- Real-time updates don't appear
- Console shows Socket.io errors

**Solutions:**

1. **Check Socket.io configuration:**
   - Backend should have Socket.io enabled
   - Check `app.py` for `socketio` initialization

2. **Check Socket.io version compatibility:**
   - Backend: `python-socketio`
   - Frontend: `socket.io-client`
   - Versions should be compatible

3. **Check WebSocket support:**
   - Socket.io falls back to polling if WebSocket fails
   - Check browser console for connection method

## Running Both Servers

### Option 1: Two Terminal Windows

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

### Option 2: Background Process

**Backend (background):**
```bash
cd web
python3 start_server.py &
```

**Frontend:**
```bash
cd web
npm start
```

### Option 3: Use Screen/Tmux

**Start screen session:**
```bash
screen -S alpr
```

**Start backend:**
```bash
cd web
python3 start_server.py
```

**Press `Ctrl+A` then `D` to detach**

**Start new terminal, start frontend:**
```bash
cd web
npm start
```

## Verifying Everything Works

1. **Backend is running:**
   - Check: http://localhost:5002
   - Should see Flask response or API endpoint

2. **Frontend is running:**
   - Check: http://localhost:5001
   - Should see React app interface

3. **Backend API works:**
   ```bash
   curl http://localhost:5002/api/vehicles
   ```
   Should return JSON with vehicles array

4. **Socket.io works:**
   - Open browser console
   - Should see "✅ Connected to server"
   - Click "Connect" button if needed

5. **Frontend can fetch data:**
   - Open browser DevTools → Network tab
   - Check for successful API requests
   - Check for Socket.io connection

## Common Error Messages

### "Failed to fetch"
- **Cause:** Backend is not running or not accessible
- **Fix:** Start backend server

### "Network Error"
- **Cause:** CORS issue or backend not accessible
- **Fix:** Check CORS configuration, check backend is running

### "Cannot GET /"
- **Cause:** Backend route not found
- **Fix:** Check backend routes in `app.py`

### "Module not found"
- **Cause:** Dependencies not installed
- **Fix:** Run `npm install`

### "Port already in use"
- **Cause:** Another process using the port
- **Fix:** Kill the process or use a different port

## Still Not Working?

1. **Check logs:**
   - Backend logs: Check terminal where backend is running
   - Frontend logs: Check browser console (F12)
   - Network logs: Check browser DevTools → Network tab

2. **Check versions:**
   ```bash
   node --version  # Should be 16+
   npm --version   # Should be 8+
   python3 --version  # Should be 3.10+
   ```

3. **Restart everything:**
   ```bash
   # Stop all processes
   python3 stop_server.py
   killall node
   
   # Start fresh
   python3 start_server.py
   # In another terminal:
   npm start
   ```

4. **Check environment:**
   - Make sure you're in the correct directory (`web/`)
   - Make sure virtual environment is activated (for backend)
   - Make sure dependencies are installed (both backend and frontend)

## Quick Checklist

- [ ] Backend server is running (port 5002)
- [ ] Frontend server is running (port 5001)
- [ ] Dependencies installed (`npm install`)
- [ ] Backend dependencies installed (virtual environment activated)
- [ ] No port conflicts
- [ ] Browser can access http://localhost:5001
- [ ] Browser can access http://localhost:5002
- [ ] Socket.io connection established
- [ ] API calls are successful
- [ ] No console errors

## Getting Help

If nothing works:
1. Check all logs (backend and frontend)
2. Check browser console for errors
3. Check network tab for failed requests
4. Verify backend and frontend are on correct ports
5. Try restarting both servers
6. Try clearing browser cache
7. Try different browser




