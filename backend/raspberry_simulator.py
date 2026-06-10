#!/usr/bin/env python3
"""
Raspberry Pi Simulator
Generates sensor data for the Eureka Dashboard:
- Inserts data into SQLite Telemetry DB (for /api/overview, /api/realtime/*, /api/stats/*)
- Writes log files (for /api/acu/*)

Usage:
    python3 raspberry_simulator.py

Environment variables:
    EUREKA_TELEMETRY_DB_PATH  - Path to eureka_telemetry.db (default: ./eureka_telemetry.db)
    ACU_LOG_DIR               - Path to log directory (default: /var/log/acu)
"""

import sqlite3
import time
import random
import math
import os
from datetime import datetime

# Paths - configurable via environment
TELEMETRY_DB_PATH = os.environ.get(
    'EUREKA_TELEMETRY_DB_PATH',
    os.path.join(os.path.dirname(__file__), 'eureka_telemetry.db')
)
ACU_LOG_DIR = os.environ.get('ACU_LOG_DIR', '/var/log/acu')

# Log files (same as app.py)
ACU_MSG_LOG = os.path.join(ACU_LOG_DIR, 'acu_msg.log')
ACU_TEMP_PRES_DAT = os.path.join(ACU_LOG_DIR, 'temp_pres.dat')

# Simulated state
state = {
    'azimuth': 125.0,
    'elevation': 45.0,
    'polarization': 0.0,
    'gyroX': 0.0,
    'gyroY': 0.0,
    'gyroZ': 0.0,
    'accX': 0.0,
    'accY': 0.0,
    'accZ': 0.98,
    'temperature': 27.65,
    'pressure': 100510.0,
    'signal': -65.0,
    'lock': 1,
    'link_status': 'UP',
    'antenna_status': 'Tracking',
    'pointing_mode': 'Auto',
    'time': 0
}

def ensure_log_dir():
    """Create log directory if it doesn't exist"""
    if not os.path.exists(ACU_LOG_DIR):
        try:
            os.makedirs(ACU_LOG_DIR, exist_ok=True)
            print(f"📁 Created log directory: {ACU_LOG_DIR}")
            return True
        except PermissionError:
            print(f"⚠️  Cannot create {ACU_LOG_DIR}")
            print(f"   Option 1: sudo mkdir -p {ACU_LOG_DIR} && sudo chown $USER:$USER {ACU_LOG_DIR}")
            print(f"   Option 2: export ACU_LOG_DIR=~/acu-logs")
            return False
    return True

def update_state():
    """Update simulated sensor values"""
    state['time'] += 1
    t = state['time']
    
    # Azimuth: smooth movement 0-360
    state['azimuth'] = 180 + 180 * math.sin(t * 0.05)
    
    # Elevation: oscillates between 15-75
    state['elevation'] = 45 + 30 * math.sin(t * 0.08)
    
    # Polarization: small variation
    state['polarization'] = 5 * math.sin(t * 0.05)
    
    # Gyros: smooth variation
    state['gyroX'] = 0.05 * math.sin(t * 0.15)
    state['gyroY'] = 0.05 * math.cos(t * 0.12)
    state['gyroZ'] = 0.02 * math.sin(t * 0.1)
    
    # Accelerometer
    state['accX'] = random.uniform(-0.01, 0.01)
    state['accY'] = random.uniform(-0.01, 0.01)
    state['accZ'] = 0.98 + random.uniform(-0.02, 0.02)
    
    # Temperature: ~27.5-27.8°C (based on real BMP data)
    state['temperature'] = 27.65 + random.uniform(-0.15, 0.20)
    
    # Pressure: ~100508-100512 Pa (based on real BMP data)
    state['pressure'] = 100510.0 + random.uniform(-3.0, 3.0)
    
    # Signal: moderate variation
    state['signal'] = -65 + 5 * math.sin(t * 0.05)
    
    # Occasional status changes
    if random.random() < 0.02:  # 2% chance
        state['link_status'] = 'DOWN'
        state['antenna_status'] = 'Acquiring'
        state['lock'] = 0
    else:
        state['link_status'] = 'UP'
        state['antenna_status'] = 'Tracking'
        state['lock'] = 1

def insert_db_data():
    """Insert data into telemetry DB tables"""
    conn = sqlite3.connect(TELEMETRY_DB_PATH)
    c = conn.cursor()
    
    # Antenna table
    c.execute('''INSERT INTO antenna (azimuth, elevation, polarization, status)
                 VALUES (?, ?, ?, ?)''',
              (round(state['azimuth'], 2),
               round(state['elevation'], 2),
               round(state['polarization'], 2),
               state['antenna_status']))
    
    # Satellite table
    c.execute('''INSERT INTO satellite (name, longitude, linkStatus, signal)
                 VALUES (?, ?, ?, ?)''',
              ('SES-14', -47.5, state['link_status'], round(state['signal'], 1)))
    
    # Sensors table
    c.execute('''INSERT INTO sensors (gyroX, gyroY, gyroZ, accX, accY, accZ, temperature, pressure)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (round(state['gyroX'], 4),
               round(state['gyroY'], 4),
               round(state['gyroZ'], 4),
               round(state['accX'], 4),
               round(state['accY'], 4),
               round(state['accZ'], 4),
               round(state['temperature'], 2),
               round(state['pressure'], 2)))
    
    # Pointing table
    c.execute('''INSERT INTO pointing (mode, azError, elError, lock)
                 VALUES (?, ?, ?, ?)''',
              (state['pointing_mode'],
               round(random.uniform(-0.1, 0.1), 3),
               round(random.uniform(-0.1, 0.1), 3),
               state['lock']))
    
    conn.commit()
    conn.close()

def write_log_files():
    """Write to ACU log files (same format app.py expects)"""
    timestamp = datetime.now().strftime('%b %d %H:%M:%S')
    
    # temp_pres.dat - format: "Mon DD HH:MM:SS Temperature / Pressure: XX.XX / XXXXX.XX"
    try:
        with open(ACU_TEMP_PRES_DAT, 'a') as f:
            f.write(f"{timestamp} Temperature / Pressure: {state['temperature']:.2f} / {state['pressure']:.2f}\n")
    except IOError:
        pass
    
    # acu_msg.log - general messages
    try:
        with open(ACU_MSG_LOG, 'a') as f:
            # Normal status message
            f.write(f"{timestamp} ACU Status: Az={state['azimuth']:.1f} El={state['elevation']:.1f} Lock={state['lock']}\n")
            
            # Occasional extra messages
            if state['link_status'] == 'DOWN':
                f.write(f"{timestamp} Warning: Link DOWN - attempting reconnection\n")
            if random.random() < 0.05:
                f.write(f"{timestamp} Debug: Signal level {state['signal']:.1f} dBm\n")
    except IOError:
        pass

def trim_log_files(max_lines=1000):
    """Keep log files from growing too large"""
    for filepath in [ACU_MSG_LOG, ACU_TEMP_PRES_DAT]:
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                if len(lines) > max_lines:
                    with open(filepath, 'w') as f:
                        f.writelines(lines[-max_lines:])
        except IOError:
            pass

def main():
    print("🚀 Raspberry Pi Simulator")
    print(f"📁 Telemetry DB: {TELEMETRY_DB_PATH}")
    print(f"📁 Logs: {ACU_LOG_DIR}")
    
    if not os.path.exists(TELEMETRY_DB_PATH):
        print(f"❌ Telemetry database not found: {TELEMETRY_DB_PATH}")
        print("   Run init_db.py first")
        return
    
    if not ensure_log_dir():
        print("⚠️  Cannot write log files, continuing with DB only...")
        write_logs = False
    else:
        write_logs = True
    
    print("\nPress Ctrl+C to stop\n")
    
    iteration = 0
    while True:
        update_state()
        insert_db_data()
        
        if write_logs:
            write_log_files()
        
        # Trim logs every 100 iterations
        iteration += 1
        if iteration % 100 == 0:
            trim_log_files()
        
        # Status line
        status = "🟢" if state['lock'] else "🔴"
        print(f"{status} Az:{state['azimuth']:6.1f}° El:{state['elevation']:5.1f}° "
              f"T:{state['temperature']:.1f}°C P:{state['pressure']:.0f}Pa "
              f"Sig:{state['signal']:.1f}dBm", end='\r')
        
        time.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Simulator stopped")