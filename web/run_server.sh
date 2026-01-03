#!/bin/bash
# Simple script to run the server
# Usage: ./run_server.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Server..."
echo ""

# Check if server is already running
if pgrep -f "python.*app.py" > /dev/null; then
    echo "⚠️  Server is already running!"
    echo ""
    echo "To check status:"
    echo "  python3 check_server.py"
    echo ""
    echo "To stop server:"
    echo "  python3 stop_server.py"
    exit 1
fi

# Check if port is in use
if lsof -ti:5002 > /dev/null 2>&1; then
    echo "⚠️  Port 5002 is already in use!"
    echo ""
    echo "To stop processes using port 5002:"
    echo "  python3 stop_server.py"
    exit 1
fi

# Find and activate virtual environment
if [ -d "../.venv" ]; then
    echo "🐍 Activating virtual environment: ../.venv"
    source ../.venv/bin/activate
elif [ -d "venv" ]; then
    echo "🐍 Activating virtual environment: venv"
    source venv/bin/activate
else
    echo "⚠️  Virtual environment not found, using system Python"
fi

# Start server
echo ""
echo "🚀 Starting Flask server..."
echo "=" * 60
echo ""

python app.py




