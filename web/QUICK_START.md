# Quick Start Guide

## Server Management Commands

### 📋 Check Server Status
```bash
cd web
python3 check_server.py
```

### 🛑 Stop Server
```bash
cd web
python3 stop_server.py
```

### 🚀 Start Server
```bash
cd web
python3 start_server.py
```

### 🔄 Restart Server
```bash
cd web
python3 stop_server.py
python3 start_server.py
```

## One-Liners

### Check and Stop if Running
```bash
cd web && python3 check_server.py && python3 stop_server.py
```

### Stop and Start (Restart)
```bash
cd web && python3 stop_server.py && sleep 2 && python3 start_server.py
```

### Full Restart with Check
```bash
cd web && python3 stop_server.py && sleep 2 && python3 check_server.py && python3 start_server.py
```

## Using Shell Scripts

### Simple Start
```bash
cd web
./run_server.sh
```

### Full Management
```bash
cd web
./server_manager.sh check    # Check status
./server_manager.sh stop     # Stop server
./server_manager.sh start    # Start server
./server_manager.sh restart  # Restart server
```

## Manual Method

### Start Server Manually
```bash
cd web
source ../.venv/bin/activate
python app.py
```

### Stop Server Manually
```bash
# Find process
ps aux | grep "python.*app.py"

# Stop it
pkill -f "python.*app.py"

# Or force stop
pkill -9 -f "python.*app.py"
```

## Troubleshooting

### Server Won't Start
1. Check if already running: `python3 check_server.py`
2. Stop existing: `python3 stop_server.py`
3. Check port: `lsof -ti:5002`
4. Try again: `python3 start_server.py`

### Multiple Instances
1. Check: `python3 check_server.py`
2. Stop all: `python3 stop_server.py --force`
3. Verify: `python3 check_server.py`
4. Start: `python3 start_server.py`

### Port Already in Use
```bash
# Find what's using port 5002
lsof -ti:5002

# Kill it
kill -9 $(lsof -ti:5002)

# Or use stop script
python3 stop_server.py --force
```

## Workflow

### Normal Workflow
```bash
# 1. Check if server is running
python3 check_server.py

# 2. If running and you need to restart:
python3 stop_server.py

# 3. Start server
python3 start_server.py
```

### Development Workflow
```bash
# Always check before starting
python3 check_server.py

# If conflict, stop all
python3 stop_server.py

# Start fresh
python3 start_server.py
```

## Notes

- **Always check before starting** to avoid conflicts
- **Only one instance** should run at a time
- **Telegram bot** will conflict if multiple instances run
- **Port 5002** must be free for server to start




