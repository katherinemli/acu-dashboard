# Eureka ACU — Portfolio Demo 🛰️

Katherine's personal portfolio demonstrating full-stack embedded systems architecture: **Eureka ACU** is a satellite antenna control system running on Raspberry Pi 5. This demo showcases her contributions to the supervisor state machine, operational dashboards, and real-time telemetry processing.

**⭐ Key Contributions:**
- Supervisor state machine (operational authority)
- Backend API & configuration management  
- Vue 3 dashboard with real-time satellite tracking
- Integration of GPS, IMU, and modem signals
- Calibration pipeline design

## What's Included

### acu-daemon/ (Python)
Simplified daemon demonstrating:
- **Supervisor State Machine**: `INIT → IDLE → READY → AUTO_POINTING → TRACKING → FAULT`
- **Pointing Control**: Smooth beam steering with target tracking
- **Sensor Simulation**: Temperature, pressure, compass, GPS  
- **Telemetry Logging**: Writes `.dat` files (`pointing.dat`, `sensors.dat`, `modem_stats.dat`)
- **Configuration**: INI file parsing and hot-reload

### emulators/ (Python)
Hardware simulators so the system works standalone:
- **modem_sim.py**: GPS receiver → NMEA RMC sentences on port 10001
- **esa_sim.py**: Antenna controller → AMIP protocol on port 5005

### backend/ (Flask)
RESTful API + database:
- **Status & telemetry**: Real-time dashboard data
- **Configuration**: Read/write INI files
- **Logs**: Stream ACU messages and sensor data  
- **Actions**: Manual pointing commands
- **Database**: SQLite (same schema as production)

### frontend/ (Vue 3 + Vite)
Operational dashboard:
- **Map**: Leaflet satellite tracking visualization
- **Telemetry**: Real-time sensor graphs
- **Status**: Supervisor state, modem/antenna health
- **Config**: Edit system parameters
- **Logs**: Live message browser
- **Manual Control**: Azimuth/elevation nudge commands

## Quick Start

### Prerequisites
```bash
python3 --version  # 3.8+
node --version     # 16+
```

### Run Everything (One Command!)

```bash
cd ~/eurekadekatherine
./run-demo.sh
```

This starts:
1. Modem simulator (GPS, port 10001)
2. ESA simulator (antenna, port 5005)
3. ACU daemon (pointing control, logs)
4. Flask backend (port 5000)
5. Vue dev server (port 5173)

Open **http://localhost:5173** and watch the system run through a demo cycle (~10 seconds).

**Stop with Ctrl+C**

## Architecture Highlights

### Supervisor State Machine (acumon.py)
**Design**: Centralized operational authority with guarded state transitions.

```
┌─────┐
│INIT │
└──┬──┘
   ↓ (hw initialized)
┌─────┐  
│IDLE │ ← return point
└──┬──┘  
   ↓ (hw ok + calibrated)
┌───────┐
│READY  │
└──┬────┘
   ↓ (satellite in range)
┌──────────────┐
│AUTO_POINTING │
└──┬───────────┘
   ↓ (signal locked)
┌─────────┐
│TRACKING │
└─────────┘
```

Each transition is guarded:
- `READY`: requires modem_ok, esa_ok, calibrated
- `AUTO_POINTING`: valid from READY or TRACKING
- `TRACKING`: valid from AUTO_POINTING
- `FAULT`: reachable from any state

### Backend (Flask Routes)
- `/api/status` — supervisor state, pointing (az/el), hardware health
- `/api/telemetry` — real-time sensor data (temp, pressure, compass, GPS)
- `/api/logs` — stream ACU messages and errors
- `/api/actions/manual-*` — pointing control commands

### Frontend (Vue Components)
- **StatusPanel**: Supervisor state visual indicator
- **MapView**: Leaflet satellite position + beam vector
- **TelemetryChart**: Real-time sensor graphs
- **LogViewer**: Scrolling message stream

## Demo Behavior

The daemon auto-cycles through states (~1 cycle per 10 seconds):
1. **Boot** (INIT) — load config, init hardware
2. **Ready** (IDLE → READY) — modem + antenna online
3. **Scan** (AUTO_POINTING) — search for satellite
4. **Lock** (TRACKING) — smooth beam tracking
5. **Stop** (→ IDLE) — manual shutdown command

Antenna position, sensor values, and logs update live in the dashboard.

## File Structure

```
eurekadekatherine/
├── run-demo.sh              ← Start everything with one command
├── acu-daemon/
│   └── acumon.py            ← Supervisor state machine + pointing control
├── emulators/
│   ├── modem_sim.py         ← GPS/NMEA simulator (port 10001)
│   └── esa_sim.py           ← Antenna AMIP simulator (port 5005)
├── backend/
│   ├── app.py               ← Flask entry + blueprint registration
│   ├── routes/              ← API endpoints (status, telemetry, config, actions)
│   ├── models/              ← Database schema + state management
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue          ← Root layout
│   │   ├── components/      ← Dashboard panels (Map, Status, Telemetry, etc.)
│   │   └── router/
│   ├── vite.config.js
│   └── package.json
├── sample-data/             ← Example config, .dat files (future)
└── README.md
```

## Manual Development

### Start daemon only
```bash
cd acu-daemon
python3 acumon.py -d /tmp/eureka -f
```

### Start backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export RUNTIME_DIR=/tmp/eureka
python3 app.py  # http://localhost:5000
```

### Start frontend
```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

### Start individual emulators
```bash
python3 emulators/modem_sim.py   # port 10001
python3 emulators/esa_sim.py     # port 5005
```

## Design Notes

### Why Python for acumon?
The production system runs C on Raspberry Pi. For the portfolio demo, Python was chosen to:
- **Show architecture** without hardware constraints
- **Keep it simple** — focus on supervisor logic, not driver details
- **Match the stack** with backend/frontend for cohesion
- **Easier to modify** for interview discussions

### Supervisor Authority
The daemon is the sole authority for:
- Mode transitions (IDLE ↔ READY ↔ AUTO_POINTING ↔ TRACKING)
- Pointing control (beam steering, safety limits)
- Operational state

Backend and frontend are **read-only consumers** — they observe state via REST APIs and send commands, but never invent decisions. This design was critical in the production migration.

### Integration Points
1. **Daemon ↔ Backend**: Filesystem polling (`/tmp/eureka/var/log/acu/*.dat`)
2. **Backend ↔ Frontend**: REST + WebSocket (planned)
3. **Emulators ↔ Daemon**: TCP sockets (modem on 10001, antenna on 5005)

## Known Limitations

- **No real GPS**: Uses synthetic Paris location
- **No real antenna**: Pointing is simulated smooth oscillation
- **No calibration**: Sensor calibration math is frozen (read-only)
- **Single-user**: No authentication (demo only)

---

**Katherine Liberona Irarrazabal** — katherine.lib.ira@gmail.com  
Portfolio: Full-stack embedded systems, real-time state machines, satellite communications  
[GitHub](https://github.com) | [LinkedIn](https://linkedin.com)

🛰️ Happy exploring!
