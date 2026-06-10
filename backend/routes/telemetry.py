"""
routes/telemetry.py - Real-time telemetry data from Acumon .dat files.

Endpoints:
    GET /api/telemetry/overview
    GET /api/telemetry/temp-pres
    GET /api/telemetry/temp-pres/history
    GET /api/telemetry/compass
    GET /api/telemetry/gps
    GET /api/telemetry/modem
"""

import json
import math
import re
from datetime import datetime

from flask import Blueprint, jsonify, request
from shared import (
    read_last_line, read_last_lines,
    parse_temp_pres, parse_ubx_gga,
    parse_pointing_dat, parse_modem_stats,
    is_modem_stale,
    ACU_TEMP_PRES_DAT, ACU_UBX_GGA_DAT,
    ACU_POINTING_DAT, ACU_MODEM_STATS_DAT,
    ACU_SENSORS_DAT, ACU_ORIENTATION_DAT, SENSORS_CAL_FILE,
)

_ORIENTATION_RE = re.compile(
    r'time \d+, yaw (-?[\d.]+), pitch (-?[\d.]+), roll (-?[\d.]+)'
)
_ORIENTATION_TS_RE = re.compile(r'^(\d{4} \w+ \d+ \d+:\d+:\d+)')
_ORIENTATION_STALE_SECS = 120

_MAG_SYNC_RE = re.compile(
    r'SYNC\s+\d+\|(-?\d+),(-?\d+),(-?\d+)\|(-?\d+),(-?\d+),(-?\d+)\|(-?\d+),(-?\d+),(-?\d+)'
)
_MAG_SENSITIVITY_UT = 0.15  # µT per raw count (AK09916 in 16-bit continuous mode)


_COMPASS_LIVE_FILE = '/dev/shm/acu_compass_live'


def _read_mag_line():
    """Return the best available raw SYNC line: RAM live file first, sensors.dat as fallback."""
    try:
        with open(_COMPASS_LIVE_FILE) as f:
            line = f.read().strip()
        if line:
            return line
    except OSError:
        pass
    return read_last_line(ACU_SENSORS_DAT)


def _get_mag_data():
    """Return (mag_heading_deg, field_ut, pitch, roll) from the live RAM file or sensors.dat.

    Heading and field strength both use calibrated µT values (hard + soft iron applied).
    Falls back to uncalibrated raw counts if cal file is missing or invalid.
    """
    line = _read_mag_line()
    if not line:
        return None, None
    m = _MAG_SYNC_RE.search(line)
    if not m:
        return None, None

    ax = float(int(m.group(1))); ay = float(int(m.group(2))); az = float(int(m.group(3)))

    # Convert raw counts to µT
    mx = float(int(m.group(7))) * _MAG_SENSITIVITY_UT
    my = float(int(m.group(8))) * _MAG_SENSITIVITY_UT
    mz = float(int(m.group(9))) * _MAG_SENSITIVITY_UT

    # Apply hard/soft iron calibration — improves both heading accuracy and field magnitude
    try:
        with open(SENSORS_CAL_FILE) as f:
            cal = json.load(f)
        c = cal.get('compass', {})
        if c.get('valid'):
            hi = c.get('hard_iron_ut', [0, 0, 0])
            si = c.get('inv_soft_iron', [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
            cx = mx - hi[0]; cy = my - hi[1]; cz = mz - hi[2]
            mx = si[0][0]*cx + si[0][1]*cy + si[0][2]*cz
            my = si[1][0]*cx + si[1][1]*cy + si[1][2]*cz
            mz = si[2][0]*cx + si[2][1]*cy + si[2][2]*cz
    except Exception:
        pass

    # Tilt-compensated heading from calibrated values (matches ant.c get_magnetic_bearing())
    pitch = math.atan2(ax, math.sqrt(ay*ay + az*az))
    roll  = math.atan2(ay, math.sqrt(ax*ax + az*az))
    mx_c = mx * math.cos(pitch) + mz * math.sin(pitch)
    my_c = mx * math.sin(roll) * math.sin(pitch) + my * math.cos(roll) - mz * math.sin(roll) * math.cos(pitch)
    heading = math.degrees(math.atan2(-my_c, mx_c))
    if heading < 0:
        heading += 360.0

    field_ut = math.sqrt(mx*mx + my*my + mz*mz)

    return round(heading, 1), round(field_ut, 1), pitch, roll

bp = Blueprint('telemetry', __name__)


@bp.route('/api/telemetry/overview')
def get_overview():
    # Prefer the most recent SCAN/PEAK line — BASE is written at the start of
    # each ~40-second outer loop and sits as the last line most of the time,
    # making it look like the antenna never moves to modem_sim and the dashboard.
    pointing_dat = {}
    for line in reversed(read_last_lines(ACU_POINTING_DAT, 15)):
        parsed = parse_pointing_dat(line)
        if parsed:
            if parsed['type'] in ('scan', 'peak', 'manual'):
                pointing_dat = parsed
                break
            if not pointing_dat:
                pointing_dat = parsed  # BASE or not_visible fallback

    modem_line = read_last_line(ACU_MODEM_STATS_DAT)
    modem_raw = parse_modem_stats(modem_line)
    modem = modem_raw if (modem_raw and not is_modem_stale(modem_raw)) else {}

    return jsonify({
        'pointing_dat': pointing_dat,
        'modem': modem
    })


@bp.route('/api/telemetry/temp-pres')
def get_temp_pres():
    line = read_last_line(ACU_TEMP_PRES_DAT)
    data = parse_temp_pres(line)
    if data:
        return jsonify(data)
    return jsonify({'error': 'No data available'}), 404


@bp.route('/api/telemetry/temp-pres/history')
def get_temp_pres_history():
    limit = request.args.get('limit', 50, type=int)
    lines = read_last_lines(ACU_TEMP_PRES_DAT, limit)
    data = [parse_temp_pres(line) for line in lines]
    return jsonify([d for d in data if d])


@bp.route('/api/telemetry/compass')
def get_compass():
    """
    Returns heading (true north) as computed by acumon with WMM declination applied.
    Only reports available=True when the orientation file has a recent line.
    Always includes mag_heading and field_ut from the sensor stream regardless of availability.
    """
    mag_heading, field_ut, live_pitch, live_roll = _get_mag_data()

    line = read_last_line(ACU_ORIENTATION_DAT)
    yaw, pitch, roll, available = None, live_pitch, live_roll, False

    if line:
        m = _ORIENTATION_RE.search(line)
        if m:
            yaw = float(m.group(1))
            # Only override live pitch/roll with orientation.dat values if live is unavailable
            if live_pitch is None:
                pitch = float(m.group(2))
                roll  = float(m.group(3))
            ts_m = _ORIENTATION_TS_RE.match(line)
            if ts_m:
                try:
                    now = datetime.now()
                    ts = datetime.strptime(ts_m.group(1), '%Y %b %d %H:%M:%S')
                    available = (now - ts).total_seconds() <= _ORIENTATION_STALE_SECS
                except ValueError:
                    pass

    if yaw is None and live_pitch is None:
        return jsonify({'heading': None, 'pitch': None, 'roll': None, 'available': False,
                        'mag_heading': mag_heading, 'field_ut': field_ut})

    return jsonify({
        'heading': yaw, 'pitch': pitch, 'roll': roll, 'available': available,
        'mag_heading': mag_heading, 'field_ut': field_ut,
    })


@bp.route('/api/telemetry/gps')
def get_gps():
    line = read_last_line(ACU_UBX_GGA_DAT)
    data = parse_ubx_gga(line)
    if data:
        return jsonify(data)
    return jsonify({'error': 'No data available'}), 404


@bp.route('/api/telemetry/modem')
def get_modem():
    line = read_last_line(ACU_MODEM_STATS_DAT)
    data = parse_modem_stats(line)
    if data and not is_modem_stale(data):
        return jsonify(data)
    return jsonify({'error': 'No data available'}), 404