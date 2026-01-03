#!/bin/bash
# Start React frontend development server

echo "============================================================"
echo "🚀 STARTING REACT FRONTEND"
echo "============================================================"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ Error: node_modules not found!"
    echo "   Please install dependencies first:"
    echo "   npm install"
    exit 1
fi

# Check if backend is running
echo "🔍 Checking backend server..."
if curl -s http://localhost:5002 > /dev/null 2>&1; then
    echo "✅ Backend server is running on port 5002"
else
    echo "⚠️  Warning: Backend server is not running on port 5002"
    echo "   Frontend will not be able to connect to backend"
    echo "   Start backend with: python3 start_server.py"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🌐 Starting React development server..."
echo "   Frontend will be available at: http://localhost:5001"
echo "   Backend API: http://localhost:5002"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Start React dev server
npm start




