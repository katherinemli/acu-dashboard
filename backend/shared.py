"""
shared.py - Constants, helpers and parsers shared across all blueprints.

Every route module imports from here. Nothing else should be imported
from app.py directly.
"""

import os
import re
import sqlite3
import configparser
from datetime import datetime

from config_manager import ConfigManager

# ============================================
# PATHS & INITIALIZATION
# ============================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Support demo mode via DEMO_DATA_DIR env var
_DEMO_ROOT = os.environ.get('DEMO_DATA_DIR', '')

def _resolve_path(default_path):
    """If DEMO_DATA_DIR is set, rebase path under it; otherwise return default."""
    if not _DEMO_ROOT:
        return default_path
    rel = default_path.lstrip('/')
    return os.path.join(_DEMO_ROOT, rel)

TELEMETRY_DB_PATH = _resolve_path('/var/lib/eureka/eureka_telemetry.db')

# Config directory resolution:
# 1. Look for config.ini at ../../../config/ (deb install layout)
# 2. Fall back to config.ini in same dir as app.py (dev/local)
# 3. Override with [Storage] configDir if present
_bootstrap_ini = os.path.join(BASE_DIR, '..', '..', '..', 'config', 'config.ini')
if not os.path.exists(_bootstrap_ini):
    _bootstrap_ini = os.path.join(BASE_DIR, 'config.ini')

_bootstrap_config = configparser.ConfigParser()
_bootstrap_config.optionxform = str
if os.path.exists(_bootstrap_ini):
    _bootstrap_config.read(_bootstrap_ini)

CONFIG_DIR = os.path.dirname(os.path.abspath(_bootstrap_ini)) if os.path.exists(_bootstrap_ini) else BASE_DIR

if _bootstrap_config.has_section('Storage'):
    _custom_dir = _bootstrap_config.get('Storage', 'configDir', fallback=None)
    if _custom_dir and os.path.isdir(_custom_dir):
        CONFIG_DIR = _custom_dir

# If in demo mode, point to demo config dir
if _DEMO_ROOT:
    CONFIG_DIR = _resolve_path('/etc/acu')

cfg = ConfigManager(CONFIG_DIR)

# TLE
TLE_DIR = os.path.join(CONFIG_DIR, 'tle')
os.makedirs(TLE_DIR, exist_ok=True)
TLE_ACTIVE_LINK = os.path.join(TLE_DIR, 'active.tle')

# Calibration session history — informational records of past calibration runs.
# Observability only: written around the frozen calibration math, never by it.
CALIB_HISTORY_DIR = os.path.join(CONFIG_DIR, 'calib_history')
os.makedirs(CALIB_HISTORY_DIR, exist_ok=True)

# ACU log file paths
ACU_LOG_DIR = _resolve_path('/var/log/acu')
ACU_MSG_LOG = os.path.join(ACU_LOG_DIR, 'acu_msg.log')
ACU_ERR_LOG = os.path.join(ACU_LOG_DIR, 'acu_err.log')
ACU_SENSORS_DAT = os.path.join(ACU_LOG_DIR, 'sensors.dat')
ACU_TEMP_PRES_DAT = os.path.join(ACU_LOG_DIR, 'temp_pres.dat')
ACU_UBX_RMC_DAT = os.path.join(ACU_LOG_DIR, 'ubx_rmc.dat')
ACU_UBX_GGA_DAT = os.path.join(ACU_LOG_DIR, 'ubx_gga.dat')
ACU_MODEM_STATS_DAT = os.path.join(ACU_LOG_DIR, 'modem_stats.dat')
ACU_POINTING_DAT = os.path.join(ACU_LOG_DIR, 'pointing.dat')
ACU_ORIENTATION_DAT = os.path.join(ACU_LOG_DIR, 'acu_orientation.dat')
ACU_SUPERVISOR_MODE_FILE = os.path.join(ACU_LOG_DIR, 'supervisor_mode')
SENSORS_CAL_FILE = _resolve_path('/etc/acu/sensors_cal.json')
ACU_CLI_CMD_INPUT  = _resolve_path('/opt/acu/cmd_input.txt')
ACU_CLI_CMD_OUTPUT = _resolve_path('/opt/acu/cmd_output.txt')
ACU_CLI_CMD_DONE   = _resolve_path('/opt/acu/cmd_done.txt')

# Modem data is considered stale after this many seconds
MODEM_STALE_SECS = 30  # confirm with manager

# ============================================
# DB HELPER
# ============================================

def get_telemetry_db():
    conn = sqlite3.connect(TELEMETRY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_event(level, message, source='system'):
    try:
        conn = get_telemetry_db()
        c = conn.cursor()
        c.execute('INSERT INTO events (level, message, source) VALUES (?, ?, ?)',
                  (level, message, source))
        conn.commit()
        conn.close()
    except Exception:
        pass

# ============================================
# FILE HELPERS
# ============================================

def read_last_lines(filepath, n=50):
    try:
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r') as f:
            lines = f.readlines()
            return [line.strip() for line in lines[-n:] if line.strip()]
    except Exception:
        return []

def read_last_line(filepath):
    lines = read_last_lines(filepath, 1)
    return lines[0] if lines else None

# ============================================
# PARSERS
# ============================================

def parse_temp_pres(line):
    if not line:
        return None
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) Temperature / Pressure: ([\d.]+) /\s+([\d.]+)',
        line
    )
    if match:
        return {
            'timestamp': match.group(1),
            'temperature': float(match.group(2)),
            'pressure': float(match.group(3))
        }
    return None

def parse_ubx_rmc(line):
    if not line:
        return None
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) date (\d*) time ([\d.]*) '
        r'lat (-?[\d.]+) lon (-?[\d.]+) '
        r'st (\w?) mode (\w?) nav_st (\w?)',
        line
    )
    if match:
        return {
            'timestamp': match.group(1),
            'date': match.group(2),
            'time': match.group(3),
            'lat': round(float(match.group(4)), 6),
            'lon': round(float(match.group(5)), 6),
            'status': match.group(6),
            'mode': match.group(7),
            'nav_status': match.group(8)
        }
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) date (\d+) time ([\d.]+) '
        r'lat ([\d.]+) ([NS]) lon ([\d.]+) ([EW]) '
        r'st (\w) mode (\w) nav_st (\w)',
        line
    )
    if match:
        raw_lat = float(match.group(4))
        lat_deg = int(raw_lat / 100)
        lat_min = raw_lat - lat_deg * 100
        lat = lat_deg + lat_min / 60.0
        if match.group(5) == 'S':
            lat = -lat
        raw_lon = float(match.group(6))
        lon_deg = int(raw_lon / 100)
        lon_min = raw_lon - lon_deg * 100
        lon = lon_deg + lon_min / 60.0
        if match.group(7) == 'W':
            lon = -lon
        return {
            'timestamp': match.group(1),
            'date': match.group(2),
            'time': match.group(3),
            'lat': round(lat, 6),
            'lon': round(lon, 6),
            'status': match.group(8),
            'mode': match.group(9),
            'nav_status': match.group(10)
        }
    return None

def parse_ubx_gga(line):
    if not line:
        return None
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) time ([\d.]*) '
        r'lat (-?[\d.]+) lon (-?[\d.]+) '
        r'qual (\d+) (?:num_)?sat (\d+) alt ([\d.]*)M?',
        line
    )
    if match:
        alt_str = match.group(7)
        return {
            'timestamp': match.group(1),
            'time': match.group(2),
            'lat': round(float(match.group(3)), 6),
            'lon': round(float(match.group(4)), 6),
            'quality': int(match.group(5)),
            'satellites': int(match.group(6)),
            'altitude': float(alt_str) if alt_str else 0.0
        }
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) time ([\d.]+) '
        r'lat ([\d.]+) ([NS]) lon ([\d.]+) ([EW]) '
        r'qual (\d+) (?:num_)?sat (\d+) alt ([\d.]+)',
        line
    )
    if match:
        raw_lat = float(match.group(3))
        lat_deg = int(raw_lat / 100)
        lat_min = raw_lat - lat_deg * 100
        lat = lat_deg + lat_min / 60.0
        if match.group(4) == 'S':
            lat = -lat
        raw_lon = float(match.group(5))
        lon_deg = int(raw_lon / 100)
        lon_min = raw_lon - lon_deg * 100
        lon = lon_deg + lon_min / 60.0
        if match.group(6) == 'W':
            lon = -lon
        return {
            'timestamp': match.group(1),
            'time': match.group(2),
            'lat': round(lat, 6),
            'lon': round(lon, 6),
            'quality': int(match.group(7)),
            'satellites': int(match.group(8)),
            'altitude': float(match.group(9))
        }
    return None


def parse_modem_stats(line):
    if not line:
        return None
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) LOCK (\d+), RF (-?[\d.]+), C/N ([\d.]+), MOD (\d+)(?:, TXMUTE (\d+))?',
        line
    )
    if match:
        lock_val = int(match.group(2))
        mod_val = int(match.group(5))
        txmute_val = match.group(6)
        return {
            'timestamp': match.group(1),
            'lock_raw': lock_val,
            'demod_lock': lock_val == 7,
            'rf_level': float(match.group(3)),
            'cn_level': float(match.group(4)),
            'mod_raw': mod_val,
            'tx_enabled': mod_val == 1,
            'perm_tx_mute': txmute_val == '1' if txmute_val else False
        }
    return None

def parse_log_line(line):
    if not line:
        return None
    match = re.match(r'(\d{4} \w+ \d+ \d+:\d+:\d+) (.+)', line)
    if match:
        message = match.group(2)
        level = 'INF'
        lower_msg = message.lower()
        if 'error' in lower_msg or 'fail' in lower_msg:
            level = 'ERR'
        elif 'warn' in lower_msg:
            level = 'WRN'
        elif 'exit' in lower_msg or 'signal' in lower_msg:
            level = 'WRN'
        elif 'debug' in lower_msg:
            level = 'DBG'
        return {
            'timestamp': match.group(1),
            'level': level,
            'message': message
        }
    lower = line.lower()
    level = 'ERR' if ('error' in lower or 'fail' in lower) else 'WRN' if 'warn' in lower else 'INF'
    return {'timestamp': '', 'level': level, 'message': line}

def parse_pointing_dat(line):
    if not line:
        return None
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) time \d+, (SCAN|PEAK|MANUAL): '
        r'az (-?[\d.]+), el (-?[\d.]+), '
        r'off_az (-?[\d.]+), off_el (-?[\d.]+), '
        r'phi (\d+), theta (\d+), '
        r'pol_skew (-?[\d.]+), cycle (\d+)'
        r'(?:, sat_el (-?[\d.]+))?',
        line
    )
    if match:
        d = {
            'type': match.group(2).lower(),
            'timestamp': match.group(1),
            'azimuth': float(match.group(3)),
            'elevation': float(match.group(4)),
            'offset_az': float(match.group(5)),
            'offset_el': float(match.group(6)),
            'phi': int(match.group(7)),
            'theta': int(match.group(8)),
            'pol_skew': float(match.group(9)),
            'cycle': int(match.group(10))
        }
        if match.group(11) is not None:
            d['sat_el'] = float(match.group(11))
        return d
    match = re.match(
        r'(\d{4} \w+ \d+ \d+:\d+:\d+) time \d+, BASE: '
        r'(?:base_)?el (-?[\d.]+), (?:base_)?az (-?[\d.]+), '
        r'pol_skew (-?[\d.]+)'
        r'(?:, sat_el (-?[\d.]+))?',
        line
    )
    if match:
        d = {
            'type': 'base',
            'timestamp': match.group(1),
            'elevation': float(match.group(2)),
            'azimuth': float(match.group(3)),
            'pol_skew': float(match.group(4))
        }
        if match.group(5) is not None:
            d['sat_el'] = float(match.group(5))
        return d
    match = re.match(r'(\d{4} \w+ \d+ \d+:\d+:\d+) .*, BASE: SAT NOT VISIBLE', line)
    if match:
        return {
            'type': 'not_visible',
            'timestamp': match.group(1)
        }
    return None

# ============================================
# MODEM STALENESS
# ============================================

def is_modem_stale(modem):
    """Returns True if modem data is older than MODEM_STALE_SECS."""
    if not modem:
        return True
    try:
        now = datetime.now()
        ts = datetime.strptime(modem["timestamp"], '%Y %b %d %H:%M:%S')
        return (now - ts).total_seconds() > MODEM_STALE_SECS
    except Exception:
        return True