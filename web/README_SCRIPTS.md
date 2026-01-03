# Server Management Scripts - Usage Guide

## Location
All scripts are in the `web/` directory:
```
alpr_project/
  └── web/
      ├── check_server.py
      ├── stop_server.py
      ├── start_server.py
      ├── run_server.sh
      └── server_manager.sh
```

## How to Run

### Option 1: Change to web directory first (Recommended)
```bash
cd web
python3 check_server.py
python3 stop_server.py
python3 start_server.py
```

### Option 2: Run from project root with path
```bash
# From alpr_project directory
python3 web/check_server.py
python3 web/stop_server.py
python3 web/start_server.py
```

### Option 3: Use full path
```bash
python3 "/Users/parth/Desktop/AI PROJECT/alpr_project/web/check_server.py"
```

## Common Mistakes

### ❌ Wrong: Running from wrong directory
```bash
# You're in alpr_project/ directory
check_server.py  # ❌ Error: command not found
```

### ✅ Correct: Change to web directory
```bash
# From alpr_project/ directory
cd web
python3 check_server.py  # ✅ Works!
```

### ✅ Also Correct: Specify path
```bash
# From alpr_project/ directory
python3 web/check_server.py  # ✅ Works!
```

## Quick Reference

### From Project Root (alpr_project/)
```bash
# Check server
python3 web/check_server.py

# Stop server
python3 web/stop_server.py

# Start server
python3 web/start_server.py
```

### From Web Directory (web/)
```bash
# First, change directory
cd web

# Then run scripts
python3 check_server.py
python3 stop_server.py
python3 start_server.py
```

## Shell Scripts (Must be in web directory)
```bash
cd web
./run_server.sh
./server_manager.sh check
./server_manager.sh stop
./server_manager.sh start
```

## Create Aliases (Optional)

Add to your `~/.zshrc` or `~/.bashrc`:
```bash
# Server management aliases
alias check-server='cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web" && python3 check_server.py'
alias stop-server='cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web" && python3 stop_server.py'
alias start-server='cd "/Users/parth/Desktop/AI PROJECT/alpr_project/web" && python3 start_server.py'
```

Then reload: `source ~/.zshrc`

Now you can run from anywhere:
```bash
check-server
stop-server
start-server
```




