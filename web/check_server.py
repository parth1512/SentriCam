#!/usr/bin/env python3
"""
Check if server instances are running
"""
import subprocess
import sys
import os

def check_server_instances():
    """Check for running server and bot instances"""
    print("=" * 60)
    print("🔍 CHECKING SERVER INSTANCES")
    print("=" * 60)
    
    # Check for app.py processes
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
    
    # Check for standalone bot processes
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
    
    # Get detailed process info
    all_processes = []
    for pid in app_processes + bot_processes:
        try:
            result = subprocess.run(
                ["ps", "-p", pid, "-o", "pid,etime,command"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    all_processes.append({
                        'pid': pid,
                        'info': lines[1]
                    })
        except:
            pass
    
    # Check port 5002
    try:
        result = subprocess.run(
            ["lsof", "-ti:5002"],
            capture_output=True,
            text=True
        )
        port_processes = result.stdout.strip().split('\n') if result.stdout.strip() else []
        port_processes = [p for p in port_processes if p]
    except:
        port_processes = []
    
    # Display results
    print(f"\n📊 Server Processes: {len(app_processes)}")
    if app_processes:
        print("   PIDs:", ", ".join(app_processes))
        for proc in all_processes:
            if proc['pid'] in app_processes:
                print(f"   - {proc['info']}")
    else:
        print("   ✅ No server processes running")
    
    print(f"\n🤖 Bot Processes: {len(bot_processes)}")
    if bot_processes:
        print("   PIDs:", ", ".join(bot_processes))
        for proc in all_processes:
            if proc['pid'] in bot_processes:
                print(f"   - {proc['info']}")
    else:
        print("   ✅ No standalone bot processes running")
    
    print(f"\n🔌 Port 5002: {'In Use' if port_processes else 'Free'}")
    if port_processes:
        print("   PIDs using port:", ", ".join(port_processes))
    
    # Summary
    total_processes = len(app_processes) + len(bot_processes)
    print("\n" + "=" * 60)
    if total_processes == 0:
        print("✅ No server instances running")
        return 0
    elif total_processes == 1:
        print("✅ One server instance running (OK)")
        return 1
    else:
        print(f"⚠️  {total_processes} server instances running (CONFLICT!)")
        print("   You should stop all but one instance")
        return 2

if __name__ == '__main__':
    exit_code = check_server_instances()
    sys.exit(exit_code)




