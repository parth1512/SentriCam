#!/usr/bin/env python3
"""
Stop all server and bot instances
"""
import subprocess
import sys
import time
import signal

def stop_server_instances(force=False):
    """Stop all server and bot instances"""
    print("=" * 60)
    print("🛑 STOPPING SERVER INSTANCES")
    print("=" * 60)
    
    stopped = []
    failed = []
    
    # Find all app.py processes
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python.*app.py"],
            capture_output=True,
            text=True
        )
        app_processes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        app_processes = [p for p in app_processes if p]
    except:
        app_processes = []
    
    # Find all standalone bot processes
    try:
        result = subprocess.run(
            ["pgrep", "-f", "run_telegram_bot"],
            capture_output=True,
            text=True
        )
        bot_processes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        bot_processes = [p for p in bot_processes if p]
    except:
        bot_processes = []
    
    all_processes = app_processes + bot_processes
    
    if not all_processes:
        print("\n✅ No server processes found to stop")
        return 0
    
    print(f"\n📋 Found {len(all_processes)} process(es) to stop:")
    for pid in all_processes:
        try:
            result = subprocess.run(
                ["ps", "-p", pid, "-o", "pid,command"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    print(f"   - PID {pid}: {lines[1]}")
        except:
            print(f"   - PID {pid}")
    
    # Stop processes
    print("\n🛑 Stopping processes...")
    for pid in all_processes:
        try:
            if force:
                # Force kill (SIGKILL)
                subprocess.run(["kill", "-9", pid], check=True, timeout=5)
                print(f"   ✅ Force killed PID {pid}")
            else:
                # Try graceful shutdown first (SIGTERM)
                subprocess.run(["kill", "-TERM", pid], check=True, timeout=5)
                print(f"   ✅ Sent SIGTERM to PID {pid}")
            stopped.append(pid)
        except subprocess.TimeoutExpired:
            print(f"   ⚠️  Timeout stopping PID {pid}, trying force kill...")
            try:
                subprocess.run(["kill", "-9", pid], check=True, timeout=5)
                stopped.append(pid)
                print(f"   ✅ Force killed PID {pid}")
            except:
                failed.append(pid)
                print(f"   ❌ Failed to kill PID {pid}")
        except Exception as e:
            failed.append(pid)
            print(f"   ❌ Error stopping PID {pid}: {e}")
    
    # Wait a moment for processes to stop
    if stopped:
        print("\n⏳ Waiting for processes to stop...")
        time.sleep(2)
    
    # Verify processes are stopped
    still_running = []
    for pid in stopped:
        try:
            result = subprocess.run(
                ["ps", "-p", pid],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                still_running.append(pid)
        except:
            pass
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"✅ Stopped: {len(stopped) - len(still_running)}")
    if still_running:
        print(f"⚠️  Still running: {len(still_running)}")
        print(f"   PIDs: {', '.join(still_running)}")
        print("   Try running with --force flag")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        print(f"   PIDs: {', '.join(failed)}")
    
    # Check port 5002
    try:
        result = subprocess.run(
            ["lsof", "-ti:5002"],
            capture_output=True,
            text=True
        )
        port_processes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        port_processes = [p for p in port_processes if p]
        if port_processes:
            print(f"\n⚠️  Port 5002 still in use by: {', '.join(port_processes)}")
            print("   These processes may need to be stopped manually")
    except:
        pass
    
    if still_running or failed:
        return 1
    return 0

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Stop all server instances')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force kill processes (SIGKILL)')
    args = parser.parse_args()
    
    exit_code = stop_server_instances(force=args.force)
    sys.exit(exit_code)




