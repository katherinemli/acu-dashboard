"""
routes/status.py - System status polled by App.vue every 5 seconds.

Endpoints:
    GET /api/status

This endpoint still returns legacy badge fields used by the current
frontend, but it now also exposes lower-inference facts so the UI can
gradually stop relying on backend-invented semantics.
"""

import os
import json
import time
import socket

from flask import Blueprint, jsonify
from shared import (
    cfg,
    read_last_line, parse_ubx_rmc, parse_modem_stats, is_modem_stale,
    ACU_UBX_RMC_DAT, ACU_MODEM_STATS_DAT, SENSORS_CAL_FILE,
)
from routes.runtime_state import get_runtime_mode

bp = Blueprint('status', __name__)

# Calibration thresholds (must match actions.py)
_MIN_COVERAGE = 0.70
_MIN_SAMPLES = 50


def _get_lan_status():
    try:
        with open('/sys/class/net/eth0/operstate', 'r') as f:
            state = f.read().strip()
        return 'up' if state == 'up' else 'down'
    except Exception:
        return 'unknown'


def _get_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return 'ACU'


def _get_gps_facts():
    line = read_last_line(ACU_UBX_RMC_DAT)
    data = parse_ubx_rmc(line)
    gps_valid = bool(data and data.get('status') == 'A')
    return {
        'valid': gps_valid,
        'raw': data,
        'badge': 'locked' if gps_valid else 'no_lock',
    }


def _get_modem_facts():
    modem_line = read_last_line(ACU_MODEM_STATS_DAT)
    modem_raw = parse_modem_stats(modem_line)
    stale = not (modem_raw and not is_modem_stale(modem_raw))

    if stale:
        return {
            'present': False,
            'fresh': False,
            'demod_lock': None,
            'tx_enabled': None,
            'rf_level': None,
            'cn_level': None,
            'lock_badge': 'unknown',
            'transmit_badge': 'unknown',
            'signal_badge': 'unknown',
            'signal_value': None,
            'raw': modem_raw,
        }

    demod_lock = bool(modem_raw['demod_lock'])
    tx_enabled = bool(modem_raw['tx_enabled'])
    rf_level = modem_raw['rf_level']

    return {
        'present': True,
        'fresh': True,
        'demod_lock': demod_lock,
        'tx_enabled': tx_enabled,
        'rf_level': rf_level,
        'cn_level': modem_raw['cn_level'],
        'lock_badge': 'locked' if demod_lock else 'unlocked',
        'transmit_badge': 'on' if tx_enabled else 'off',
        'signal_badge': 'good' if demod_lock else 'bad',
        'signal_value': f"{rf_level} dBm",
        'raw': modem_raw,
    }


def _get_compass_calib_info():
    """Return (state, message) for the header badge."""
    if not os.path.exists(SENSORS_CAL_FILE):
        return 'not_calibrated', 'No calibration file found'

    try:
        with open(SENSORS_CAL_FILE, 'r') as f:
            cal = json.load(f)
    except Exception as e:
        return 'poor', f'Cannot read calibration file: {e}'

    # Support both old flat format (compass at root) and new per-sensor format
    compass_cal = cal.get('compass', cal)

    if not compass_cal.get('valid', False):
        return 'poor', 'Calibration file exists but is marked invalid'

    reasons = []
    coverage = compass_cal.get('coverage', 0)
    samples = compass_cal.get('sample_count', 0)

    if coverage < _MIN_COVERAGE:
        reasons.append(f'low coverage ({coverage:.0%})')
    if samples < _MIN_SAMPLES:
        reasons.append(f'few samples ({samples})')

    try:
        expires_at = compass_cal.get('expires_at', '')
        if expires_at:
            exp_time = time.strptime(expires_at, '%Y-%m-%dT%H:%M:%SZ')
            if time.time() > time.mktime(exp_time):
                reasons.append('expired')
    except Exception:
        pass

    if reasons:
        return 'poor', ', '.join(reasons)
    return 'good', 'Calibrated'


@bp.route('/api/status')
def get_status():
    loc_data = cfg.get_section('location') or {}
    gps_override_enabled = loc_data.get('SiteLocOverride', '0') == '1'
    gps_facts = _get_gps_facts()
    modem_facts = _get_modem_facts()

    compass_state, compass_msg = _get_compass_calib_info()
    runtime_mode = get_runtime_mode()

    return jsonify({
        'name': _get_hostname(),
        'model': 'ESA-ACU',
        'lan': _get_lan_status(),
        'gps': 'manual' if gps_override_enabled else gps_facts['badge'],
        'tracking': runtime_mode,
        'transmit': modem_facts['transmit_badge'],
        'lock': modem_facts['lock_badge'],
        'signal': modem_facts['signal_badge'],
        'signal_value': modem_facts['signal_value'],
        'compass_calibration': compass_state,
        'compass_calibration_msg': compass_msg,
        'facts': {
            'runtime_mode': runtime_mode,
            'runtime_mode_source': 'acumon_supervisor_file',
            'gps_override_enabled': gps_override_enabled,
            'gps_valid': gps_facts['valid'],
            'modem_present': modem_facts['present'],
            'modem_fresh': modem_facts['fresh'],
            'modem_demod_lock': modem_facts['demod_lock'],
            'modem_tx_enabled': modem_facts['tx_enabled'],
            'modem_rf_level': modem_facts['rf_level'],
            'modem_cn_level': modem_facts['cn_level'],
            'perm_tx_mute': modem_facts.get('raw', {}).get('perm_tx_mute', False) if modem_facts.get('raw') else False,
        }
    })
