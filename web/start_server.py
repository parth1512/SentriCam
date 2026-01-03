#!/usr/bin/env python3
"""
Start the server
"""
import subprocess
import sys
import os
from pathlib import Path

def check_port_in_use(port):
    """Check if a port is in use"""
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0
    except:
        return False

def start_server():
    """Start the Flask server"""
    print("=" * 60)
    print("🚀 STARTING SERVER")
    print("=" * 60)
    
    # Check if server is already running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*app.py"],
            capture_output=True,
            text=True
        )
        existing_processes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        existing_processes = [p for p in existing_processes if p]
        
        if existing_processes:
            print(f"\n⚠️  CONFLICT: Server is already running!")
            print(f"   Found {len(existing_processes)} process(es): {', '.join(existing_processes)}")
            print("\n   This will cause Telegram bot conflicts!")
            print("\n   Please stop the existing server first:")
            print("   python3 stop_server.py")
            print("\n   Or check status:")
            print("   python3 check_server.py")
            print("\n   Or use the safe starter:")
            print("   python3 check_and_start_server.py")
            return 1
    except Exception as e:
        print(f"⚠️  Could not check for existing processes: {e}")
    
    # Check if port 5002 is in use
    if check_port_in_use(5002):
        print(f"\n⚠️  Port 5002 is already in use!")
        print(f"   Another process may be using the port.")
        print("\n   Please stop the process(es) first:")
        print("   python3 stop_server.py")
        print("\n   Or check what's using the port:")
        print("   lsof -ti:5002")
        return 1
    
    # Get script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Find virtual environment
    venv_paths = [
        script_dir.parent / ".venv",
        script_dir / "venv",
        Path.home() / ".venv"
    ]
    
    venv_path = None
    for path in venv_paths:
        if path.exists() and (path / "bin" / "activate").exists():
            venv_path = path
            break
    
    # Prepare command
    app_path = script_dir / "app.py"
    if not app_path.exists():
        print(f"\n❌ Error: app.py not found in {script_dir}")
        return 1
    
    print(f"\n📁 Working directory: {script_dir}")
    if venv_path:
        print(f"🐍 Virtual environment: {venv_path}")
    else:
        print("⚠️  Virtual environment not found, using system Python")
    
    print(f"\n🚀 Starting server...")
    print("=" * 60)
    print("")
    
    # Start server
    try:
        if venv_path:
            # Activate venv and run
            python_exe = venv_path / "bin" / "python3"
            if not python_exe.exists():
                python_exe = venv_path / "bin" / "python"
            
            if python_exe.exists():
                os.execv(str(python_exe), [str(python_exe), str(app_path)])
            else:
                print("❌ Python executable not found in virtual environment")
                return 1
        else:
            # Use system Python
            os.execv(sys.executable, [sys.executable, str(app_path)])
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = start_server()
    sys.exit(exit_code)

