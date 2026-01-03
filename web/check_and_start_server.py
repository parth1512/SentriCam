#!/usr/bin/env python3
"""
Safe server starter - checks for conflicts before starting
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

def check_server_running():
    """Check if server is already running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*app.py"],
            capture_output=True,
            text=True
        )
        processes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        processes = [p for p in processes if p]
        return len(processes) > 0, processes
    except:
        return False, []

def main():
    print("=" * 60)
    print("🔍 CHECKING SERVER STATUS")
    print("=" * 60)
    
    # Check for running processes
    is_running, pids = check_server_running()
    port_in_use = check_port_in_use(5002)
    
    if is_running:
        print(f"\n⚠️  Server is already running!")
        print(f"   Found {len(pids)} process(es): {', '.join(pids)}")
        print(f"\n   Options:")
        print(f"   1. Stop existing server: python3 stop_server.py")
        print(f"   2. Check status: python3 check_server.py")
        print(f"   3. Force stop: python3 stop_server.py --force")
        return 1
    
    if port_in_use:
        print(f"\n⚠️  Port 5002 is already in use!")
        print(f"   Another process may be using the port.")
        print(f"   Please check: lsof -ti:5002")
        return 1
    
    print("\n✅ No conflicts detected")
    print("🚀 Starting server...")
    print("=" * 60 + "\n")
    
    # Get script directory
    script_dir = Path(__file__).resolve().parent
    os.chdir(script_dir)
    
    # Find virtual environment
    venv_paths = [
        script_dir.parent / ".venv",
        script_dir / "venv",
    ]
    
    venv_path = None
    for path in venv_paths:
        if path.exists() and (path / "bin" / "activate").exists():
            venv_path = path
            break
    
    # Prepare command
    app_path = script_dir / "app.py"
    if not app_path.exists():
        print(f"❌ Error: app.py not found in {script_dir}")
        return 1
    
    # Start server
    try:
        if venv_path:
            python_exe = venv_path / "bin" / "python3"
            if not python_exe.exists():
                python_exe = venv_path / "bin" / "python"
            
            if python_exe.exists():
                os.execv(str(python_exe), [str(python_exe), str(app_path)])
            else:
                print("❌ Python executable not found in virtual environment")
                return 1
        else:
            os.execv(sys.executable, [sys.executable, str(app_path)])
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)




