#!/bin/bash

# ALPR Web Application Runner
# This script starts both the Flask backend and React frontend

cd "$(dirname "$0")"

echo "🚀 Starting ALPR Web Application..."
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "✅ Found virtual environment"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "✅ Found virtual environment"
    source .venv/bin/activate
else
    echo "⚠️  No virtual environment found. Using system Python."
    echo "   (Consider creating one: python3 -m venv venv)"
fi

# Check Python dependencies
echo "📦 Checking Python dependencies..."
python3 -c "import flask, flask_cors, flask_socketio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Python dependencies missing. Installing..."
    pip3 install --user flask flask-cors flask-socketio python-socketio eventlet 2>/dev/null || {
        echo "⚠️  Installation failed. Please install manually:"
        echo "   pip3 install flask flask-cors flask-socketio python-socketio eventlet"
    }
fi

# Check Node dependencies
echo "📦 Checking Node dependencies..."
if [ ! -d "web/node_modules" ]; then
    echo "❌ Node modules missing. Installing..."
    cd web
    npm install
    cd ..
fi

echo ""
echo "🔧 Starting Flask backend..."
cd web
python3 app.py &
BACKEND_PID=$!
cd ..

echo "⏳ Waiting for backend to start..."
sleep 3

echo ""
echo "⚛️  Starting React frontend..."
cd web
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Application started!"
echo "   - Backend PID: $BACKEND_PID"
echo "   - Frontend PID: $FRONTEND_PID"
echo ""
echo "🌐 Access the application at: http://localhost:3000"
echo "📡 Backend API at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop both servers..."

# Wait for user interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait


