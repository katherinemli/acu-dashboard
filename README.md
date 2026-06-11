# Eureka ACU — Portfolio Demo 🛰️

Katherine's full-stack portfolio showcasing a **satellite antenna control system**. This is a simplified but complete demo of real operational architecture: supervisor state machine (daemon), REST backend, and Vue 3 dashboard.

**What She Built:**
- Supervisor state machine (operational authority)
- REST API for system status & control
- Real-time Vue 3 dashboard  
- Configuration management
- Production-ready architecture patterns

## Architecture

**Three-layer system:**
1. **Daemon** (`acu-daemon/`) — State machine, writes `state.json` every ~1 sec
2. **Backend** (`backend/`) — Flask API reads state.json, exposes `/api/status`, `/api/telemetry`
3. **Frontend** (`frontend/`) — Vue 3 dashboard polls backend, displays real-time data

No external hardware or complex emulators — just **clean separation of concerns**.

## Quick Start

### Prerequisites
```bash
python3 --version  # 3.8+
node --version     # 16+
```

### Run
```bash
./run-demo.sh
```

Opens:
- **Frontend**: http://localhost:5173 (dashboard)
- **Backend**: http://localhost:5000/api/status (raw data)

Daemon cycles through: `IDLE → READY → AUTO_POINTING → TRACKING` (repeats every ~10 sec).

**Stop:** Ctrl+C

## File Structure
```
eurekadekatherine/
├── acu-daemon/acumon.py     ← Supervisor (writes state.json)
├── backend/                  ← Flask API (reads state.json)
├── frontend/                 ← Vue 3 dashboard
├── sample-data/              ← Example configs
└── run-demo.sh              ← Start everything
```

## How It Works

### Daemon (`acu-daemon/acumon.py`)
Cycles through supervisor states every ~10 seconds, writes JSON:
```json
{
  "timestamp": "2026-06-11T10:30:45Z",
  "state": "TRACKING",
  "azimuth": 45.2,
  "elevation": 32.1,
  "temperature": 27.3,
  "modem_lock": true,
  "esa_ok": true
}
```

### Backend (`backend/app.py`)
Reads `state.json` every ~500ms, serves REST:
- `GET /api/status` — current state
- `GET /api/telemetry` — sensor data (temp, modem lock, etc.)

### Frontend (`frontend/`)
Polls backend every second, renders:
- Supervisor state (IDLE/READY/AUTO_POINTING/TRACKING)
- Real-time azimuth/elevation gauge
- Temperature, modem lock status
- Cycle counter

**No delays, no fuss — just data flow: Daemon → File → Backend → API → Frontend**

## Development

### Daemon only
```bash
cd acu-daemon && python3 acumon.py -d /tmp/eureka -f
```

### Backend only
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export RUNTIME_DIR=/tmp/eureka
python3 app.py
```

### Frontend only
```bash
cd frontend && npm install && npm run dev
```

## Key Design Decisions

1. **Single source of truth**: Daemon writes JSON, backend reads JSON → no sync issues
2. **No emulators**: Real behavior lives in the daemon, not fake hardware sims
3. **REST-first**: Frontend-agnostic API (works with any frontend framework)
4. **Stateless backend**: Reads from file, no in-process state
5. **Production patterns**: This architecture mirrors the real Eureka ACU system

## Tech Stack

| Layer | Tech |
|-------|------|
| Daemon | Python 3 (stdlib only) |
| Backend | Flask, SQLite |
| Frontend | Vue 3, Vite, Leaflet |
| Data | JSON + SQLite |

---

**Katherine Liberona Irarrazabal** · katherine.lib.ira@gmail.com

🛰️
