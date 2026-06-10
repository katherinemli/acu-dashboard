#!/usr/bin/env python3
"""
Initialize the telemetry database and fill it with test data.

Architecture:
  - Config lives in config.ini + satellites.ini (managed by config_manager.py)
  - eureka_telemetry.db → Streaming data (antenna, satellite, sensors, pointing, events, logs)
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

BASE_DIR = os.path.dirname(__file__)

TELEMETRY_DB_PATH = os.path.join(BASE_DIR, 'eureka_telemetry.db')
SCHEMA_TELEMETRY_PATH = os.path.join(BASE_DIR, 'schema_telemetry.sql')


def init_db():
    """Create telemetry tables from schema file"""
    conn = sqlite3.connect(TELEMETRY_DB_PATH)
    with open(SCHEMA_TELEMETRY_PATH, 'r') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"✅ Telemetry schema created → {os.path.basename(TELEMETRY_DB_PATH)}")


def populate_realtime_data():
    """Generate historical telemetry for the last 24 hours"""
    conn = sqlite3.connect(TELEMETRY_DB_PATH)
    c = conn.cursor()

    now = datetime.now()

    for minutes_ago in range(0, 24 * 60, 5):
        timestamp = (now - timedelta(minutes=minutes_ago)).strftime('%Y-%m-%d %H:%M:%S')

        base_az = 125 + random.uniform(-5, 5)
        base_el = 45 + random.uniform(-2, 2)

        c.execute('''INSERT INTO antenna (azimuth, elevation, polarization, status, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (round(base_az + random.uniform(-0.5, 0.5), 2),
                   round(base_el + random.uniform(-0.3, 0.3), 2),
                   round(random.uniform(-2, 2), 2),
                   random.choice(['Tracking', 'Tracking', 'Tracking', 'Acquiring']),
                   timestamp))

        c.execute('''INSERT INTO satellite (name, longitude, linkStatus, signal, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  ('SES-14', -47.5,
                   random.choice(['UP', 'UP', 'UP', 'UP', 'DOWN']),
                   round(-65 + random.uniform(-3, 3), 1),
                   timestamp))

        c.execute('''INSERT INTO sensors
                     (gyroX, gyroY, gyroZ, accX, accY, accZ, temperature, pressure, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (round(random.uniform(-0.05, 0.05), 3),
                   round(random.uniform(-0.05, 0.05), 3),
                   round(random.uniform(-0.02, 0.02), 3),
                   round(random.uniform(-0.01, 0.01), 3),
                   round(random.uniform(-0.01, 0.01), 3),
                   round(0.98 + random.uniform(-0.02, 0.02), 3),
                   round(27.65 + random.uniform(-0.15, 0.20), 2),
                   round(100510.0 + random.uniform(-3.0, 3.0), 2),
                   timestamp))

        c.execute('''INSERT INTO pointing (mode, azError, elError, lock, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (random.choice(['Auto', 'Auto', 'Manual']),
                   round(random.uniform(-0.1, 0.1), 3),
                   round(random.uniform(-0.1, 0.1), 3),
                   random.choice([1, 1, 1, 1, 0]),
                   timestamp))

    conn.commit()
    conn.close()
    print("✅ Realtime data generated (24 hours)")


def populate_events():
    """Generate sample events"""
    conn = sqlite3.connect(TELEMETRY_DB_PATH)
    c = conn.cursor()

    events = [
        ('info', 'System started successfully', 'system'),
        ('info', 'Antenna tracking initialized', 'antenna'),
        ('info', 'ESA connection established', 'esa'),
        ('warning', 'Signal strength below threshold', 'satellite'),
        ('error', 'Lost connection to satellite', 'satellite'),
        ('info', 'Attempting reconnection...', 'satellite'),
        ('info', 'Connection restored', 'satellite'),
        ('info', 'Gyroscope calibration complete', 'sensors'),
        ('info', 'Configuration saved', 'system'),
        ('warning', 'High temperature detected: 42C', 'sensors'),
    ]

    now = datetime.now()
    for i, (level, message, source) in enumerate(events):
        timestamp = (now - timedelta(minutes=i * 15)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO events (level, message, source, timestamp)
                     VALUES (?, ?, ?, ?)''', (level, message, source, timestamp))

    conn.commit()
    conn.close()
    print("✅ Sample events inserted")


def populate_logs():
    """Generate sample logs"""
    conn = sqlite3.connect(TELEMETRY_DB_PATH)
    c = conn.cursor()

    logs = [
        ('INF', 'System boot sequence initiated'),
        ('INF', 'Loading configuration from config.ini'),
        ('INF', 'Network interface eth0 configured: 192.168.100.102'),
        ('INF', 'Starting antenna controller service'),
        ('INF', 'Gyroscope calibration complete'),
        ('INF', 'Accelerometer calibration complete'),
        ('INF', 'ESA connection established: 192.168.100.100:5005'),
        ('DBG', 'Antenna position: Az=125.4, El=45.2'),
        ('INF', 'Satellite lock acquired: SES-14'),
        ('WRN', 'Signal level dropping: -68.5 dBm'),
        ('INF', 'Auto-tracking mode enabled'),
        ('DBG', 'Pointing error: Az=0.02, El=0.01'),
        ('INF', 'System ready'),
    ]

    now = datetime.now()
    for i, (level, message) in enumerate(logs):
        timestamp = (now - timedelta(seconds=i * 2)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('''INSERT INTO logs (level, message, timestamp)
                     VALUES (?, ?, ?)''', (level, message, timestamp))

    conn.commit()
    conn.close()
    print("✅ Sample logs inserted")


def main():
    if os.path.exists(TELEMETRY_DB_PATH):
        os.remove(TELEMETRY_DB_PATH)
        print(f"🗑️  Deleted {os.path.basename(TELEMETRY_DB_PATH)}")

    init_db()
    populate_realtime_data()
    populate_events()
    populate_logs()

    print(f"\n🎉 Telemetry database ready: {TELEMETRY_DB_PATH}")

    print("\nRecords per table:")
    conn = sqlite3.connect(TELEMETRY_DB_PATH)
    c = conn.cursor()
    for table in ['antenna', 'satellite', 'sensors', 'pointing', 'events', 'logs']:
        c.execute(f'SELECT COUNT(*) FROM {table}')
        count = c.fetchone()[0]
        print(f"  {table}: {count}")
    conn.close()


if __name__ == '__main__':
    main()