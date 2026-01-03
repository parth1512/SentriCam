#!/bin/bash
# Server Management Script
# Usage: ./server_manager.sh [check|stop|start|restart]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

case "$1" in
    check)
        echo "🔍 Checking server instances..."
        python3 check_server.py
        ;;
    stop)
        echo "🛑 Stopping all server instances..."
        python3 stop_server.py
        ;;
    stop-force)
        echo "🛑 Force stopping all server instances..."
        python3 stop_server.py --force
        ;;
    start)
        echo "🚀 Starting server..."
        # Check if already running
        if pgrep -f "python.*app.py" > /dev/null; then
            echo "⚠️  Server is already running!"
            echo "   Use './server_manager.sh check' to see running instances"
            echo "   Use './server_manager.sh stop' to stop before starting"
            exit 1
        fi
        
        # Activate virtual environment and start
        if [ -d "../.venv" ]; then
            source ../.venv/bin/activate
        elif [ -d "venv" ]; then
            source venv/bin/activate
        fi
        
        python app.py
        ;;
    restart)
        echo "🔄 Restarting server..."
        python3 stop_server.py
        sleep 2
        echo "🚀 Starting server..."
        if [ -d "../.venv" ]; then
            source ../.venv/bin/activate
        elif [ -d "venv" ]; then
            source venv/bin/activate
        fi
        python app.py
        ;;
    *)
        echo "Usage: $0 {check|stop|stop-force|start|restart}"
        echo ""
        echo "Commands:"
        echo "  check       - Check if server instances are running"
        echo "  stop        - Stop all server instances gracefully"
        echo "  stop-force  - Force stop all server instances"
        echo "  start       - Start the server"
        echo "  restart     - Stop and start the server"
        exit 1
        ;;
esac




