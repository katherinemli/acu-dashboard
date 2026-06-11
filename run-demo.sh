#!/bin/bash
# Quick start: Eureka ACU portfolio demo (no emulators, just daemon + backend + frontend)

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="/tmp/eureka-demo"

mkdir -p "$RUNTIME_DIR"

echo "🛰️  Eureka ACU — Portfolio Demo"
echo "=================================="
echo ""

# 1. ACU Daemon
echo "1️⃣  Starting ACU daemon..."
cd "$PROJECT_DIR/acu-daemon"
python3 acumon.py -d "$RUNTIME_DIR" -f &
ACU_PID=$!
echo "   Daemon (PID $ACU_PID) → $RUNTIME_DIR/state.json"
sleep 1

# 2. Backend
echo ""
echo "2️⃣  Starting backend..."
cd "$PROJECT_DIR/backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi
export RUNTIME_DIR="$RUNTIME_DIR"
export DEMO_DATA_DIR="$RUNTIME_DIR"
python3 app.py &
BACKEND_PID=$!
echo "   Backend (PID $BACKEND_PID) → http://localhost:8000"
sleep 2

# 3. Frontend
echo ""
echo "3️⃣  Starting frontend..."
cd "$PROJECT_DIR/frontend"
npm install -q 2>/dev/null || true
npm run dev &
FRONTEND_PID=$!
echo "   Frontend (PID $FRONTEND_PID) → http://localhost:5173"

echo ""
echo "=================================="
echo "✅ Ready!"
echo ""
echo "Open: http://localhost:5173"
echo "Backend: http://localhost:8000/api/status"
echo ""
echo "Ctrl+C to stop (PIDs: $ACU_PID $BACKEND_PID $FRONTEND_PID)"
echo ""

wait
