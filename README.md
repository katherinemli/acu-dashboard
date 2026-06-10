# Eureka ACU — Portfolio Demo

This is Katherine's personal portfolio demonstrating her contributions to the **Eureka ACU** (Antenna Control Unit) project — a satellite communication system that runs on Raspberry Pi 5, pointing a flat-panel electronically steerable antenna (ESA) at satellites using GPS, IMU, and modem signals.

## What's Included

### Backend (Flask Python)
- **RESTful API** (`routes/`): Status, telemetry, config management, satellite/TLE management, calibration, logs, actions, debug tools
- **State management**: Supervisor mode tracking, runtime configuration, device health
- **Database**: SQLite telemetry with sensor/antenna/satellite/pointing data
- **File I/O abstraction**: Graceful parsing of ACU log files and sensor data

### Frontend (Vue 3 + Vite)
- **Dashboard** (Overview): Real-time antenna azimuth/elevation, satellite signal, modem lock status, supervisor state
- **Telemetry viewer**: Temperature, pressure, compass (magnetometer), GPS, modem statistics
- **Configuration UI**: Edit INI config files with UI fallbacks
- **Satellite & TLE management**: Upload, activate, manage orbital data
- **Tools panel**: Reboot, firmware upgrade, event logs, CLI console
- **Calibration UI**: Magnetometer calibration flow (read-only in demo)
- **Docs**: In-app manual with screenshots

### ACU Emulator (Python)
- **No hardware or C code** — pure Python simulation
- **Supervisor state machine**: IDLE → READY → AUTO_POINTING → TRACKING (demo cycle every 50s)
- **Synthetic sensor data**: Realistic oscillating azimuth/elevation, temperature, pressure, compass readings
- **All required log files**: `ubx_rmc.dat`, `modem_stats.dat`, `sensors.dat`, `pointing.dat`, etc.
- **SQLite telemetry DB**: Same schema as the real hardware

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- macOS, Linux, or Windows (WSL)

### Quick Start

```bash
cd ~/eurekadekatherine
./demo/run_demo.sh
```

This script will:
1. Create `demo/runtime/` with fake config and runtime data
2. Initialize the telemetry database
3. Start the ACU emulator (writes fake sensor logs)
4. Start the Flask backend on `http://localhost:5000`
5. Start the Vue dev server on `http://localhost:5173`

Open your browser to `http://localhost:5173` and explore the dashboard.

**Stop with Ctrl+C** in the terminal.

## Portfolio Highlights

### Backend Design
- **Modular blueprint architecture**: Separation of concerns (status, telemetry, config, calibration, actions, etc.)
- **Safe file parsing**: Regex-based parsers for NMEA GPS, modem stats, magnetometer sensor data
- **Calibration tracking**: Non-invasive observability around frozen calibration math
- **Configuration hot-reload**: Monitor and manage INI files with schema fallbacks

### Frontend Design
- **Reactive state management**: Pinia store for ACU state, real-time updates
- **Component composition**: Reusable panels, modals, data visualizers
- **Progressive disclosure**: Tools panel contains calibration, logs, CLI, and system actions
- **Responsive layout**: Works on mobile (iPad/tablet) and desktop

### System Architecture
The **supervisor state machine** is the runtime authority:
```
[IDLE] 
  ↓ (calibrated + commanded)
[READY] 
  ↓ (satellite in view)
[AUTO_POINTING] 
  ↓ (locked onto signal)
[TRACKING]
```

The backend/frontend are **support layers only** — they query and display state, send commands via CLI, but do not invent operational decisions. This separation was a key architectural goal.

## Demo Features

### Supervisor Cycling
The emulator cycles through all 4 supervisor states automatically (every 50 seconds) so you can see state transitions in the dashboard.

### Realistic Telemetry
- Antenna azimuth/elevation oscillate smoothly (satellite tracking simulation)
- Temperature/pressure vary within expected ranges
- Compass (magnetometer) generates realistic 3-axis vectors
- Modem occasionally drops lock (2% chance per cycle) to test error handling

### Config Management
The `/api/config` routes let you upload, backup, and restore INI files. In demo mode, edits are written to `demo/runtime/etc/acu/config.ini`.

### Log Viewer
All emulator outputs go to `demo/runtime/var/log/acu/`, and the frontend reads them in real-time for the Logs tab.

## Architecture Notes

### No Hardware Mode
Because the personal portfolio lacks a Raspberry Pi, the **acumon daemon is emulated in Python**:
- All C sensor drivers (ICM20948 IMU, BMP5 barometer, u-blox GPS) are replaced with synthetic data
- The supervisor state machine logic is ported to Python for demonstration
- Pointing math (antenna beam steering) is simulated with smooth sinusoidal movement

The emulator is sufficient to **demonstrate the frontend/backend correctly** and show the supervisor architecture without access to real hardware.

### Separation of Contributions
This portfolio includes:
- ✅ **Katherine**: All backend routes, frontend components, supervisor design
- ✅ **Fake acumon**: Pure Python emulation, no C code
- ❌ **Xiaming's code**: Real C sensor drivers (ICM20948, BMP5, u-blox)
- ❌ **Pablo's code**: Real pointing math (beam steering, TLE propagation, magnetic declination)

## Development

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DEMO_DATA_DIR=../demo/runtime
python3 app.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev    # dev server with HMR
npm run build  # production build to dist/
```

### Emulator
```bash
export DEMO_DATA_DIR=demo/runtime
python3 demo/acumon_emulator.py
```

## File Structure

```
eurekadekatherine/
├── backend/              ← Flask app, routes, database schema
├── frontend/             ← Vue 3 components, stores, router
├── demo/
│   ├── acumon_emulator.py    ← Supervisor emulator (no hardware)
│   ├── run_demo.sh           ← One-liner to start everything
│   ├── fake_data/
│   │   ├── config.ini        ← Sample INI (Paris location)
│   │   ├── satellites.ini    ← Sample satellites (SES-14, ASTRA, etc.)
│   │   └── sensors_cal.json  ← Fake but valid calibration
│   └── runtime/              ← Generated at startup (logs, DB, etc.)
└── README.md
```

## Testing the Demo

### Pages to Explore
1. **Overview** — Real-time antenna position, signal, supervisor state
2. **Stats** — Telemetry: temperature, pressure, compass, modem
3. **Config** — Edit config.ini via UI
4. **Satellites** — Manage satellites (demo data: SES-14, ASTRA, INTELSAT)
5. **Logs** — View all ACU messages and sensor data in real-time
6. **Tools** → Calibration — Browse calibration history (read-only in demo)
7. **Tools** → CLI Console — Send manual commands to acumon

### Expected Behavior
- Antenna azimuth/elevation oscillate between realistic ranges
- Every 50 seconds, supervisor state advances (IDLE → READY → AUTO_POINTING → TRACKING)
- Temperature/pressure wiggle naturally around ~27°C / 100.5 kPa
- Modem occasionally shows "no lock" (transient loss)
- Compass heading rotates smoothly as the system "points" at the satellite

## Known Limitations (Demo Mode)

1. **No real hardware**: Sensor values are synthetic, not from actual IMU/GPS/modem
2. **No actual antenna**: Azimuth/elevation are fake; no real RF lock achieved
3. **No TLE propagation**: Satellite positions don't calculate from real orbital data
4. **Read-only calibration UI**: Calibration history is displayed but cannot be run
5. **Static location**: GPS is hardcoded to Paris for simplicity

These are intentional trade-offs for a portfolio demo on a personal machine without Raspberry Pi hardware.

## License & Attribution

**Eureka ACU** is a collaborative project. This portfolio includes Katherine's architectural and code contributions to demonstrate her expertise in:
- Full-stack web development (Flask + Vue 3)
- System state machine design
- Embedded systems support software
- Real-time telemetry visualization

---

**Questions or feedback?** Open an issue or reach out.

Happy exploring! 🚀
