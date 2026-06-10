#!/usr/bin/env python3
"""
ACU Supervisor Emulator

Simulates the complete acumon daemon for portfolio/demo:
- Writes all flat log files that backend reads (ubx_rmc.dat, modem_stats.dat, sensors.dat, etc.)
- Manages supervisor state machine (IDLE → READY → AUTO_POINTING → TRACKING)
- Populates SQLite telemetry DB
- No hardware, no C code — pure Python simulation

Environment:
    DEMO_DATA_DIR - Root for all data paths; if set, redirects /var/log/acu, /etc/acu, etc.
"""

import sqlite3
import time
import random
import math
import os
import json
from datetime import datetime
from pathlib import Path

# Config
DEMO_DATA_DIR = os.environ.get('DEMO_DATA_DIR', '')

def _resolve_path(default):
    if not DEMO_DATA_DIR:
        return default
    return os.path.join(DEMO_DATA_DIR, default.lstrip('/'))

# Paths
TELEMETRY_DB_PATH = _resolve_path('/var/lib/eureka/eureka_telemetry.db')
ACU_LOG_DIR = _resolve_path('/var/log/acu')
CONFIG_DIR = _resolve_path('/etc/acu')

DB_FILE = TELEMETRY_DB_PATH
ACU_MSG_LOG = os.path.join(ACU_LOG_DIR, 'acu_msg.log')
ACU_TEMP_PRES_DAT = os.path.join(ACU_LOG_DIR, 'temp_pres.dat')
ACU_UBX_RMC_DAT = os.path.join(ACU_LOG_DIR, 'ubx_rmc.dat')
ACU_UBX_GGA_DAT = os.path.join(ACU_LOG_DIR, 'ubx_gga.dat')
ACU_MODEM_STATS_DAT = os.path.join(ACU_LOG_DIR, 'modem_stats.dat')
ACU_SENSORS_DAT = os.path.join(ACU_LOG_DIR, 'sensors.dat')
ACU_POINTING_DAT = os.path.join(ACU_LOG_DIR, 'pointing.dat')
ACU_ORIENTATION_DAT = os.path.join(ACU_LOG_DIR, 'acu_orientation.dat')
ACU_SUPERVISOR_MODE_FILE = os.path.join(ACU_LOG_DIR, 'supervisor_mode')
COMPASS_LIVE_FILE = '/dev/shm/acu_compass_live'

# Supervisor state machine
SUPERVISOR_STATES = ['IDLE', 'READY', 'AUTO_POINTING', 'TRACKING']

class State:
    def __init__(self):
        self.time = 0
        self.azimuth = 125.0
        self.elevation = 45.0
        self.polarization = 0.0
        self.gyroX = 0.0
        self.gyroY = 0.0
        self.gyroZ = 0.0
        self.accX = 0.0
        self.accY = 0.0
        self.accZ = 0.98
        self.magX = 0
        self.magY = 0
        self.magZ = 0
        self.temperature = 27.65
        self.pressure = 100510.0
        self.signal = -65.0
        self.modem_lock = 1
        self.link_status = 'UP'
        self.antenna_status = 'Tracking'
        self.supervisor_state = 'IDLE'
        self.supervisor_cycle = 0
        self.heading = 0.0

state = State()

def ensure_dirs():
    for d in [ACU_LOG_DIR, CONFIG_DIR, os.path.dirname(TELEMETRY_DB_PATH)]:
        Path(d).mkdir(parents=True, exist_ok=True)

def get_timestamp():
    return datetime.now().strftime('%Y %b %d %H:%M:%S')

def update_state():
    """Update simulated sensor values"""
    state.time += 1
    t = state.time

    # Azimuth: smooth movement 0-360
    state.azimuth = 180 + 180 * math.sin(t * 0.05)

    # Elevation: oscillates between 15-75
    state.elevation = 45 + 30 * math.sin(t * 0.08)

    # Polarization
    state.polarization = 5 * math.sin(t * 0.05)

    # Heading (compass)
    state.heading = (180 + 90 * math.sin(t * 0.03)) % 360

    # Gyros: smooth variation
    state.gyroX = 0.05 * math.sin(t * 0.15)
    state.gyroY = 0.05 * math.cos(t * 0.12)
    state.gyroZ = 0.02 * math.sin(t * 0.1)

    # Accelerometer
    state.accX = random.uniform(-0.01, 0.01)
    state.accY = random.uniform(-0.01, 0.01)
    state.accZ = 0.98 + random.uniform(-0.02, 0.02)

    # Magnetometer (raw counts, AK09916)
    state.magX = int(1000 + 500 * math.sin(t * 0.05))
    state.magY = int(500 + 300 * math.cos(t * 0.08))
    state.magZ = int(2000 + 200 * math.sin(t * 0.03))

    # Temperature
    state.temperature = 27.65 + random.uniform(-0.15, 0.20)

    # Pressure
    state.pressure = 100510.0 + random.uniform(-3.0, 3.0)

    # Signal
    state.signal = -65 + 5 * math.sin(t * 0.05)

    # Occasional status changes (2% chance)
    if random.random() < 0.02:
        state.link_status = 'DOWN'
        state.antenna_status = 'Acquiring'
        state.modem_lock = 0
    else:
        state.link_status = 'UP'
        state.antenna_status = 'Tracking'
        state.modem_lock = 1

    # Supervisor state machine: cycle through states slowly (every 50 iterations = ~50s per state)
    state.supervisor_cycle += 1
    if state.supervisor_cycle >= 50:
        state.supervisor_cycle = 0
        state_idx = (SUPERVISOR_STATES.index(state.supervisor_state) + 1) % len(SUPERVISOR_STATES)
        state.supervisor_state = SUPERVISOR_STATES[state_idx]

def write_supervisor_mode():
    """Write supervisor state to file"""
    try:
        with open(ACU_SUPERVISOR_MODE_FILE, 'w') as f:
            f.write(state.supervisor_state)
    except Exception as e:
        print(f"Error writing supervisor_mode: {e}")

def write_temp_pres():
    """Write temp/pressure log"""
    try:
        ts = get_timestamp()
        with open(ACU_TEMP_PRES_DAT, 'a') as f:
            f.write(f"{ts} Temperature / Pressure: {state.temperature:.2f} / {state.pressure:.2f}\n")
    except Exception:
        pass

def write_gps_rmc():
    """Write GPS RMC sentence (NMEA-like)"""
    try:
        ts = get_timestamp()
        # Format: "YYYY Mon DD HH:MM:SS date XXXXXXXX time HHmmss.ss lat DD.DDDDDD lon DD.DDDDDD st A mode A nav_st A"
        # Fixed to Paris for demo
        with open(ACU_UBX_RMC_DAT, 'a') as f:
            f.write(f"{ts} date 20260610 time 120000.00 lat 48.860000 lon 2.350000 st A mode A nav_st A\n")
    except Exception:
        pass

def write_gps_gga():
    """Write GPS GGA sentence"""
    try:
        ts = get_timestamp()
        # GGA format with quality, satellites, altitude
        with open(ACU_UBX_GGA_DAT, 'a') as f:
            f.write(f"{ts} time 120000.00 lat 48.860000 lon 2.350000 qual 2 num_sat 12 alt 35.5\n")
    except Exception:
        pass

def write_modem_stats():
    """Write modem stats line"""
    try:
        ts = get_timestamp()
        # LOCK level (0-7), RF power, C/N, MOD type, optional TXMUTE
        with open(ACU_MODEM_STATS_DAT, 'a') as f:
            lock_level = 7 if state.modem_lock else 0
            f.write(f"{ts} LOCK {lock_level}, RF 12, C/N 8.5, MOD 3\n")
    except Exception:
        pass

def write_sensors_dat():
    """Write IMU sensors.dat with SYNC line (the compass live file)"""
    try:
        ts = get_timestamp()
        # SYNC timestamp|accX|accY|accZ|gyroX|gyroY|gyroZ|magX|magY|magZ
        # Raw counts: acc in mG, gyro in deg/s, mag in raw counts
        with open(ACU_SENSORS_DAT, 'a') as f:
            acc_x_raw = int(state.accX * 1000)
            acc_y_raw = int(state.accY * 1000)
            acc_z_raw = int(state.accZ * 1000)
            gyro_x_raw = int(state.gyroX * 100)
            gyro_y_raw = int(state.gyroY * 100)
            gyro_z_raw = int(state.gyroZ * 100)
            f.write(f"SYNC {state.time}|{acc_x_raw},{acc_y_raw},{acc_z_raw}|"
                   f"{gyro_x_raw},{gyro_y_raw},{gyro_z_raw}|"
                   f"{state.magX},{state.magY},{state.magZ}\n")
    except Exception:
        pass

def write_compass_live():
    """Write compass live file (same format as sensors.dat, for live compass reading)"""
    try:
        # /dev/shm might not exist in demo mode, so skip if path doesn't allow it
        Path(COMPASS_LIVE_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(COMPASS_LIVE_FILE, 'w') as f:
            acc_x_raw = int(state.accX * 1000)
            acc_y_raw = int(state.accY * 1000)
            acc_z_raw = int(state.accZ * 1000)
            gyro_x_raw = int(state.gyroX * 100)
            gyro_y_raw = int(state.gyroY * 100)
            gyro_z_raw = int(state.gyroZ * 100)
            f.write(f"SYNC {state.time}|{acc_x_raw},{acc_y_raw},{acc_z_raw}|"
                   f"{gyro_x_raw},{gyro_y_raw},{gyro_z_raw}|"
                   f"{state.magX},{state.magY},{state.magZ}\n")
    except Exception:
        pass

def write_pointing_dat():
    """Write pointing.dat with current position"""
    try:
        ts = get_timestamp()
        # BASE format: "YYYY Mon DD HH:MM:SS time XXXXX, BASE: base_el -XX.XX, base_az XXX.XX, pol_skew X.XX"
        with open(ACU_POINTING_DAT, 'a') as f:
            f.write(f"{ts} time {state.time}, BASE: base_el {state.elevation:.2f}, base_az {state.azimuth:.2f}, pol_skew {state.polarization:.2f}\n")
    except Exception:
        pass

def write_orientation_dat():
    """Write orientation.dat with heading"""
    try:
        ts = get_timestamp()
        # Format: "YYYY Mon DD HH:MM:SS heading X.XX"
        with open(ACU_ORIENTATION_DAT, 'a') as f:
            f.write(f"{ts} heading {state.heading:.2f}\n")
    except Exception:
        pass

def write_acu_msg_log():
    """Write ACU message log"""
    try:
        ts = get_timestamp()
        with open(ACU_MSG_LOG, 'a') as f:
            f.write(f"{ts} ACU Supervisor: state={state.supervisor_state} Az={state.azimuth:.1f} El={state.elevation:.1f} Lock={state.modem_lock}\n")
            if state.link_status == 'DOWN':
                f.write(f"{ts} Warning: Modem link DOWN\n")
    except Exception:
        pass

def insert_db_data():
    """Insert into telemetry DB"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        # antenna table
        c.execute('''INSERT INTO antenna (azimuth, elevation, polarization, status)
                     VALUES (?, ?, ?, ?)''',
                  (round(state.azimuth, 2),
                   round(state.elevation, 2),
                   round(state.polarization, 2),
                   state.antenna_status))

        # satellite table
        c.execute('''INSERT INTO satellite (name, longitude, linkStatus, signal)
                     VALUES (?, ?, ?, ?)''',
                  ('SES-14', -47.5, state.link_status, round(state.signal, 1)))

        # sensors table
        c.execute('''INSERT INTO sensors (gyroX, gyroY, gyroZ, accX, accY, accZ, temperature, pressure)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                  (round(state.gyroX, 4),
                   round(state.gyroY, 4),
                   round(state.gyroZ, 4),
                   round(state.accX, 4),
                   round(state.accY, 4),
                   round(state.accZ, 4),
                   round(state.temperature, 2),
                   round(state.pressure, 2)))

        # pointing table
        c.execute('''INSERT INTO pointing (mode, azError, elError, lock)
                     VALUES (?, ?, ?, ?)''',
                  (state.supervisor_state,
                   round(random.uniform(-0.1, 0.1), 3),
                   round(random.uniform(-0.1, 0.1), 3),
                   state.modem_lock))

        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB error: {e}")

def trim_logs(max_lines=2000):
    """Trim log files to prevent unbounded growth"""
    for filepath in [ACU_MSG_LOG, ACU_TEMP_PRES_DAT, ACU_UBX_RMC_DAT, ACU_UBX_GGA_DAT,
                     ACU_MODEM_STATS_DAT, ACU_SENSORS_DAT, ACU_POINTING_DAT, ACU_ORIENTATION_DAT]:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                if len(lines) > max_lines:
                    with open(filepath, 'w') as f:
                        f.writelines(lines[-max_lines:])
        except Exception:
            pass

def main():
    print("🚀 ACU Supervisor Emulator (Demo Portfolio)")
    print(f"📁 Log dir: {ACU_LOG_DIR}")
    print(f"📁 Config dir: {CONFIG_DIR}")
    print(f"📁 DB: {DB_FILE}")
    print(f"🔄 Supervisor states: IDLE → READY → AUTO_POINTING → TRACKING (cycle every 50s)\n")

    ensure_dirs()

    iteration = 0
    try:
        while True:
            update_state()

            # Write all log files
            write_supervisor_mode()
            write_temp_pres()
            write_gps_rmc()
            write_gps_gga()
            write_modem_stats()
            write_sensors_dat()
            write_compass_live()
            write_pointing_dat()
            write_orientation_dat()
            write_acu_msg_log()
            insert_db_data()

            # Trim logs every 100 iterations
            iteration += 1
            if iteration % 100 == 0:
                trim_logs()

            # Status indicator
            status = "🟢" if state.modem_lock else "🔴"
            print(f"{status} {state.supervisor_state:13} | "
                  f"Az:{state.azimuth:6.1f}° El:{state.elevation:5.1f}° "
                  f"T:{state.temperature:.1f}°C P:{state.pressure:.0f}Pa "
                  f"Hdg:{state.heading:6.1f}°", end='\r')

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  ACU Emulator stopped")

if __name__ == '__main__':
    main()
