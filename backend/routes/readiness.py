"""
routes/readiness.py - Pointing-readiness criteria for the dashboard.

Reads /var/log/acu/readiness.json (written by acumon's supervisor) and returns
the 6 criteria from all_readiness_ok() — calibration, sensors, tle, location,
esa, modem — each with a plain-language reason, so the operator sees exactly
what is blocking AUTO pointing instead of guessing.
"""

import os
import json

from flask import Blueprint, jsonify

from shared import SENSORS_CAL_FILE, ACU_SUPERVISOR_MODE_FILE

bp = Blueprint('readiness', __name__)

# Consolidated into the existing supervisor_mode file (mode + flags, as JSON) —
# no extra files; acumon's supervisor is the single source of these flags.
READINESS_FILE = ACU_SUPERVISOR_MODE_FILE

_LABELS = {
    'calibration': 'Cal', 'sensors': 'Sen', 'tle': 'Tle',
    'location': 'Loc', 'esa': 'Esa', 'modem': 'Modem',
}

# Plain reason shown when a criterion is NOT met.
_WHY_NOT = {
    'sensors': 'No fresh IMU data — magnetometer/accel not reporting.',
    'tle': 'No active TLE, or the satellite is below the horizon.',
    'location': 'No GPS fix and no manual location override.',
    'esa': 'ESA TX/RX not connected/initialized — check the ESA link (state should reach SET BEAM).',
    'modem': 'No modem connection from the configured modemIp.',
}


def _calibration_reason():
    """Verbose calibration detail from sensors_cal.json — always show the numbers
    (a low field vs the local geomagnetic field, or low coverage, is exactly what
    operators need to see and could not before)."""
    try:
        with open(SENSORS_CAL_FILE) as f:
            c = json.load(f).get('compass', {})
    except Exception:
        return False, 'No calibration file — run a compass calibration.'
    if not c.get('valid'):
        return False, 'Calibration file present but invalid — re-run.'
    parts = []
    if c.get('field_strength_ut') is not None:
        parts.append(f"field {c['field_strength_ut']} µT")
    if c.get('coverage') is not None:
        parts.append(f"coverage {round(c['coverage'] * 100)}%")
    if c.get('fit_error_pct') is not None:
        parts.append(f"fit err {c['fit_error_pct']}%")
    if c.get('expires_at'):
        parts.append(f"expires {c['expires_at'][:10]}")
    return True, 'Calibrated (' + ', '.join(parts) + ').' if parts else 'Calibrated.'


@bp.route('/api/readiness')
def readiness():
    if not os.path.exists(READINESS_FILE):
        return jsonify({'available': False,
                        'message': 'acumon has not reported readiness yet'})
    try:
        with open(READINESS_FILE) as f:
            r = json.load(f)
    except Exception as e:
        return jsonify({'available': False, 'message': f'unreadable: {e}'})

    criteria = []
    for key in ('calibration', 'sensors', 'tle', 'location', 'esa', 'modem'):
        ok = bool(r.get(key))
        if key == 'calibration':
            cal_ok, reason = _calibration_reason()
            ok = ok and cal_ok
        else:
            reason = 'OK' if ok else _WHY_NOT.get(key, 'Not ready.')
        criteria.append({'key': key, 'label': _LABELS[key], 'ok': ok, 'reason': reason})

    return jsonify({
        'available': True,
        'mode': r.get('mode'),
        'ready': all(c['ok'] for c in criteria),
        'criteria': criteria,
    })
