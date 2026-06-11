#!/bin/bash
# Quick start script for Eureka ACU portfolio demo

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="/tmp/eureka-demo"

echo "🛰️  Eureka ACU Portfolio Demo"
echo "================================"
echo "Project: $PROJECT_DIR"
echo "Runtime: $RUNTIME_DIR"
echo ""

# Create runtime directory
mkdir -p "$RUNTIME_DIR"

# Start emulators in background
echo "1️⃣  Starting emulators..."
cd "$PROJECT_DIR/emulators"

python3 modem_sim.py &
MODEM_PID=$!
echo "   Modem simulator (PID $MODEM_PID)"

python3 esa_sim.py &
ESA_PID=$!
echo "   ESA simulator (PID $ESA_PID)"

sleep 1

# Start ACU daemon
echo ""
echo "2️⃣  Starting ACU daemon..."
cd "$PROJECT_DIR/acu-daemon"

python3 acumon.py -d "$RUNTIME_DIR" -f &
ACU_PID=$!
echo "   ACU daemon (PID $ACU_PID)"

sleep 2

# Start backend
echo ""
echo "3️⃣  Starting backend..."
cd "$PROJECT_DIR/backend"

# Setup venv if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

export RUNTIME_DIR="$RUNTIME_DIR"
python3 app.py &
BACKEND_PID=$!
echo "   Backend (PID $BACKEND_PID) → http://localhost:5000"

sleep 2

# Start frontend
echo ""
echo "4️⃣  Starting frontend..."
cd "$PROJECT_DIR/frontend"

npm install -q 2>/dev/null || true
npm run dev &
FRONTEND_PID=$!
echo "   Frontend (PID $FRONTEND_PID) → http://localhost:5173"

echo ""
echo "================================"
echo "✅ All services running!"
echo ""
echo "Open browser: http://localhost:5173"
echo ""
echo "To stop, press Ctrl+C (or kill PIDs: $MODEM_PID $ESA_PID $ACU_PID $BACKEND_PID $FRONTEND_PID)"
echo ""

# Wait for any background job to exit
wait
