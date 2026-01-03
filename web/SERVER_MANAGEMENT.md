# Server Management Guide

## Quick Commands

### Check Server Status
```bash
cd web
python3 check_server.py
```
**Or:** `./server_manager.sh check`

### Stop All Servers
```bash
cd web
python3 stop_server.py
```
**Force stop:** `python3 stop_server.py --force`  
**Or:** `./server_manager.sh stop` or `./server_manager.sh stop-force`

### Start Server
```bash
cd web
python3 start_server.py
```
**Or:** `./run_server.sh` or `./server_manager.sh start`

### Restart Server
```bash
cd web
python3 stop_server.py && python3 start_server.py
```
**Or:** `./server_manager.sh restart`

## Manual Commands

### Check Running Processes
```bash
# Check for app.py processes
ps aux | grep "python.*app.py" | grep -v grep

# Check for bot processes
ps aux | grep "run_telegram_bot" | grep -v grep

# Check port 5002
lsof -ti:5002
```

### Stop Processes Manually
```bash
# Stop gracefully (SIGTERM)
pkill -f "python.*app.py"
pkill -f "run_telegram_bot"

# Force stop (SIGKILL)
pkill -9 -f "python.*app.py"
pkill -9 -f "run_telegram_bot"

# Stop by PID
kill <PID>
kill -9 <PID>  # Force kill
```

## Scripts Available

1. **check_server.py** - Check if server instances are running
2. **stop_server.py** - Stop all server instances
3. **server_manager.sh** - Combined management script

## Exit Codes

- **0** - Success / No processes running
- **1** - One process running (OK)
- **2** - Multiple processes running (CONFLICT)

## Common Issues

### Multiple Instances Running
If you see multiple processes:
```bash
# Check status
python3 check_server.py

# Stop all
python3 stop_server.py

# Verify stopped
python3 check_server.py
```

### Port 5002 In Use
If port is still in use after stopping:
```bash
# Find process using port
lsof -ti:5002

# Kill it
kill -9 $(lsof -ti:5002)
```

### Process Won't Stop
Use force stop:
```bash
python3 stop_server.py --force
```

## Best Practices

1. **Always check before starting:**
   ```bash
   python3 check_server.py
   ```

2. **Stop properly before restarting:**
   ```bash
   python3 stop_server.py
   # Wait a moment
   python app.py
   ```

3. **Use the management script:**
   ```bash
   ./server_manager.sh restart
   ```

4. **Never run multiple instances** - Telegram bot will conflict!

