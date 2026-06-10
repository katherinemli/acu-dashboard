-- ============================================
-- EUREKA DASHBOARD - Telemetry & Event Database Schema
-- High-frequency writes: streaming data, logs, events
-- ============================================

-- Antenna Data
CREATE TABLE IF NOT EXISTS antenna (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    azimuth REAL,
    elevation REAL,
    polarization REAL,
    status TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Satellite Data
CREATE TABLE IF NOT EXISTS satellite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    longitude REAL,
    linkStatus TEXT,
    signal REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Sensors Data
CREATE TABLE IF NOT EXISTS sensors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gyroX REAL,
    gyroY REAL,
    gyroZ REAL,
    accX REAL,
    accY REAL,
    accZ REAL,
    temperature REAL,
    pressure REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Pointing Data
CREATE TABLE IF NOT EXISTS pointing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT,
    azError REAL,
    elError REAL,
    lock INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- LOGS & EVENTS
-- ============================================

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,  -- info, warning, error
    message TEXT NOT NULL,
    source TEXT DEFAULT 'system',
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL,  -- INF, WRN, ERR, DBG
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_antenna_timestamp ON antenna(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_satellite_timestamp ON satellite(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sensors_timestamp ON sensors(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_pointing_timestamp ON pointing(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_level ON events(level);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC);