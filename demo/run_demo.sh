#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_ROOT="${SCRIPT_DIR}/runtime"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Eureka Dashboard Demo"
echo "================================"

# Create runtime directories
echo "📁 Creating runtime directories..."
mkdir -p "$DEMO_ROOT/var/log/acu"
mkdir -p "$DEMO_ROOT/etc/acu"
mkdir -p "$DEMO_ROOT/var/lib/eureka"

# Copy fake config data
echo "📋 Copying fake config files..."
cp "$SCRIPT_DIR/fake_data/config.ini" "$DEMO_ROOT/etc/acu/"
cp "$SCRIPT_DIR/fake_data/satellites.ini" "$DEMO_ROOT/etc/acu/"
cp "$SCRIPT_DIR/fake_data/sensors_cal.json" "$DEMO_ROOT/etc/acu/"

# Export demo mode
export DEMO_DATA_DIR="$DEMO_ROOT"

# Initialize backend database if needed
if [ ! -f "$DEMO_ROOT/eureka_telemetry.db" ]; then
    echo "🗄️  Initializing telemetry database..."
    cd "$REPO_ROOT/backend"
    python3 init_db.py
    cd - > /dev/null
fi

# Start emulator in background
echo "🤖 Starting ACU Emulator..."
python3 "$SCRIPT_DIR/acumon_emulator.py" &
EMULATOR_PID=$!
echo "   PID: $EMULATOR_PID"

# Start backend in background
echo "🔧 Starting Flask backend..."
cd "$REPO_ROOT/backend"

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt 2>/dev/null || echo "   (requirements already installed)"

# Set env for Flask
export DEMO_DATA_DIR="$DEMO_ROOT"
export FLASK_ENV=development

python3 app.py &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"
sleep 2

cd - > /dev/null

# Start frontend dev server
echo "🎨 Starting Vue frontend..."
cd "$REPO_ROOT/frontend"

if [ ! -d "node_modules" ]; then
    echo "   Installing npm dependencies (this may take a minute)..."
    npm install -q
fi

export DEMO_DATA_DIR="$DEMO_ROOT"
npm run dev

# Cleanup on exit
trap "kill $EMULATOR_PID $BACKEND_PID 2>/dev/null; echo '✅ Demo stopped'" EXIT
