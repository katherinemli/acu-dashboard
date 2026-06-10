"""
routes/calibration.py - HTTP endpoints for calibration.

Thin: validate input, delegate to calibration_session for state and to
calibration_math for the fit. No business logic lives here.

Endpoints:

    Compass:
        POST /api/calibration/compass/start
        GET  /api/calibration/compass/progress
        POST /api/calibration/compass/stop
        POST /api/calibration/compass/cancel
        GET  /api/calibration/compass/status
        GET  /api/calibration/compass/result

    Gyro:
        POST /api/calibration/gyro/start
        GET  /api/calibration/gyro/progress
        POST /api/calibration/gyro/capture
        POST /api/calibration/gyro/stop
        POST /api/calibration/gyro/cancel
        GET  /api/calibration/gyro/result

    Accel:
        POST /api/calibration/accel/start
        GET  /api/calibration/accel/progress
        POST /api/calibration/accel/capture
        POST /api/calibration/accel/stop
        POST /api/calibration/accel/cancel
        GET  /api/calibration/accel/result

The /cancel endpoints must always return quickly and be safe to call
when no session exists (used by beforeunload / visibilitychange).
"""

import os
import json
import time
import threading

import numpy as np

from flask import Blueprint, jsonify, request

from shared import (
    log_event,
    SENSORS_CAL_FILE,
    CALIB_HISTORY_DIR,
)
import calibration_session as session_mod
import calibration_math as math_mod


bp = Blueprint('calibration', __name__)

MIN_ACCEL_CAPTURE_WINDOWS = 6
MIN_GYRO_CAPTURE_WINDOWS = 1

_fit_result = None
_fit_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Calibration session history (read-only). Lists past session records written
# to CALIB_HISTORY_DIR as JSON. Pure observability around the frozen math —
# this endpoint never reads or writes calibration state.
# ---------------------------------------------------------------------------

@bp.route('/api/calibration/history')
def calibration_history():
    """Return past calibration session records, newest first."""
    sessions = []
    try:
        names = [n for n in os.listdir(CALIB_HISTORY_DIR) if n.endswith('.json')]
    except FileNotFoundError:
        names = []
    for name in names:
        path = os.path.join(CALIB_HISTORY_DIR, name)
        try:
            with open(path, 'r') as f:
                rec = json.load(f)
            if not isinstance(rec, dict):
                rec = {'data': rec}
        except Exception as e:
            sessions.append({'file': name, 'status': 'UNREADABLE', 'error': str(e)})
            continue
        rec['file'] = name
        sessions.append(rec)
    # Newest first — prefer the record timestamp, fall back to the filename.
    sessions.sort(key=lambda r: str(r.get('timestamp', r.get('file', ''))), reverse=True)
    return jsonify({'sessions': sessions, 'count': len(sessions)})


# ---------------------------------------------------------------------------
# Calibration session history (write). Records every finished/cancelled session
# as one JSON file. All fields are deterministic — derived from data the frozen
# fit / session already produced; nothing is inferred. WMM-expected field and a
# quality score are intentionally omitted (defining them would be a design
# choice, not a deterministic fact). Observability only; never touches the math.
# ---------------------------------------------------------------------------

CALIB_HISTORY_KEEP = 20  # retain the most recent N session records


def _prune_calib_history():
    """Keep only the most recent CALIB_HISTORY_KEEP records. Filenames are
    timestamp-sortable, so reverse sort puts newest first. Best-effort."""
    try:
        files = sorted(
            (n for n in os.listdir(CALIB_HISTORY_DIR) if n.endswith('.json')),
            reverse=True,
        )
        for old in files[CALIB_HISTORY_KEEP:]:
            os.remove(os.path.join(CALIB_HISTORY_DIR, old))
    except Exception:
        pass


def _saved_cal(sensor):
    """Read the just-written sensors_cal.json record for one sensor."""
    try:
        with open(SENSORS_CAL_FILE, 'r') as f:
            return json.load(f).get(sensor, {})
    except Exception:
        return {}


def _safe_coverage(s):
    """Session coverage state, or None — never raises (cancel must stay safe)."""
    try:
        return s.update_coverage()
    except Exception:
        return None


def _record_calib_session(sensor, status, started_at, *,
                          captured=None, saved=None, raw_coverage=None,
                          live_state=None, error=None):
    """Write one calib_history record from already-computed, deterministic data."""
    now = time.time()
    sid = time.strftime('%Y%m%d_%H%M%S', time.gmtime(started_at or now))
    rec = {
        'session_id': sid,
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now)),
        'sensor': sensor,
        'status': status,
    }
    if started_at:
        rec['duration_s'] = round(now - started_at)

    if saved:
        for k in ('coverage', 'sectors_hit', 'sectors_total',
                  'field_strength_ut', 'fit_error_pct', 'hard_iron_ut'):
            if k in saved:
                rec[k] = saved[k]
        kept = saved.get('sample_count')
        if captured is not None and kept is not None:
            rejected = max(0, captured - kept)
            rec['samples'] = {'captured': captured, 'kept': kept, 'rejected': rejected}
            if sensor == 'compass' and rejected > 0:
                rec['rejection_reasons'] = {'magnitude_out_of_range_22_67_uT': rejected}
        if raw_coverage is not None:
            rec['diagnostics'] = {'live_coverage': round(raw_coverage, 3)}
    elif live_state:
        rec['coverage'] = round(live_state.get('coverage', 0) or 0, 3)
        if live_state.get('sectors_hit') is not None:
            rec['sectors_hit'] = live_state['sectors_hit']
            rec['sectors_total'] = math_mod.COVERAGE_TOTAL_SECTORS
        if live_state.get('samples') is not None:
            rec['samples'] = {'captured': live_state['samples']}
        if live_state.get('window_count'):
            rec['capture_windows'] = live_state['window_count']

    if error is not None:
        rec['error'] = str(error)

    try:
        os.makedirs(CALIB_HISTORY_DIR, exist_ok=True)
        path = os.path.join(CALIB_HISTORY_DIR, f'calib_{sensor}_{sid}.json')
        with open(path, 'w') as f:
            json.dump(rec, f, indent=2)
        _prune_calib_history()
    except Exception as e:
        log_event('warning', f'calib_history write failed: {e}', 'calibration')


# ---------------------------------------------------------------------------
# Status thresholds
# ---------------------------------------------------------------------------

_MIN_COVERAGE = 0.70
_MIN_SAMPLES = 50
_MAX_AGE_DAYS = 30


# =========================================================================
# HELPERS
# =========================================================================

def _check_stability(session):
    """Return True if recent samples are suitable for capture.
    Gyro: rotating (non-zero values). Accel: still (low variance)."""
    if session.sensor == 'gyro':
        samples = session._reader.snapshot_gyro_samples()
        if len(samples) < 5:
            return False
        recent = samples[-10:]
        arr = np.array(recent, dtype=np.float64)
        mag = float(np.mean(np.abs(arr)))
        return bool(mag > 30.0)
    elif session.sensor == 'accel':
        samples = session._reader.snapshot_accel_samples()
        if len(samples) < 5:
            return False
        recent = samples[-10:]
        arr = np.array(recent, dtype=np.float64)
        var = float(np.var(arr, axis=0).sum())
        return bool(var < 500.0)
    else:
        return True


def _extract_sensor_samples(samples_full, sensor):
    """Extract the correct 3-tuple from the 10-tuple based on sensor type."""
    if sensor == 'compass':
        return [(t[6], t[7], t[8]) for t in samples_full]
    elif sensor == 'gyro':
        return [(t[3], t[4], t[5]) for t in samples_full]
    else:  # accel
        return [(t[0], t[1], t[2]) for t in samples_full]


# =========================================================================
# COMPASS
# =========================================================================

@bp.route('/api/calibration/compass/start', methods=['POST'])
def compass_start():
    s, err, status = session_mod.start_stream('compass')
    if s is None:
        return jsonify({'status': 'error', 'error': err}), status
    return jsonify({'status': 'ok', 'sensor': 'compass'})


@bp.route('/api/calibration/compass/progress')
def compass_progress():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'compass':
        return jsonify({'status': 'error',
                        'error': 'No compass calibration in progress'}), 409

    s.touch()
    state = s.update_coverage()

    elapsed = time.time() - s.started_at if s.started_at else 0
    auto_stop_ready = state['coverage'] >= 0.95

    reader_status = s._reader.get_status()
    waiting_for_acumon = reader_status.get('waiting_for_start', False)

    return jsonify({
        'status': 'ok',
        'samples': state['samples'],
        'coverage': round(state['coverage'], 3),
        'sectors_hit': state['sectors_hit'],
        'sectors_total': math_mod.COVERAGE_TOTAL_SECTORS,
        'elapsed_seconds': round(elapsed, 1),
        'auto_stop_ready': auto_stop_ready,
        'last_reading': state['last_reading'],
        'waiting_for_acumon': waiting_for_acumon,
    })


@bp.route('/api/calibration/compass/stop', methods=['POST'])
def compass_stop():
    global _fit_result
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'compass':
        return jsonify({'status': 'error',
                        'error': 'No compass calibration in progress'}), 409

    samples_full, _started_at = s.stop()
    samples = _extract_sensor_samples(samples_full, 'compass')

    if len(samples) < 20:
        log_event('warning',
                  f'Compass calibration aborted: only {len(samples)} samples',
                  'calibration')
        return jsonify({
            'status': 'error',
            'error': f'Too few samples: {len(samples)}. Keep moving the unit longer.',
        }), 400

    def _run_fit():
        global _fit_result
        try:
            calib_output = math_mod.run_ellipsoid_calibration('compass', samples)
            n, coverage, sectors_hit = math_mod.compute_coverage(samples)
            with _fit_lock:
                _fit_result = {
                    'status': 'ok',
                    'sensor': 'compass',
                    'samples': n,
                    'coverage': coverage,
                    'calib_output': calib_output,
                }
            log_event('info',
                      f'Compass calibration finished ({n} samples, coverage {coverage:.0%})',
                      'calibration')
            _record_calib_session('compass', 'APPLIED', _started_at,
                                  captured=len(samples), saved=_saved_cal('compass'),
                                  raw_coverage=coverage)
        except Exception as e:
            log_event('error', f'Compass fit failed: {e}', 'calibration')
            with _fit_lock:
                _fit_result = {
                    'status': 'error',
                    'error': str(e),
                    'reset': True,
                }
            _record_calib_session('compass', 'FAILED', _started_at,
                                  captured=len(samples), error=e)

    with _fit_lock:
        _fit_result = None
    threading.Thread(target=_run_fit, daemon=True).start()

    return jsonify({
        'status': 'ok',
        'state': 'calculating',
        'samples': len(samples),
    })


@bp.route('/api/calibration/compass/cancel', methods=['POST'])
def compass_cancel():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'compass':
        return jsonify({'status': 'ok', 'note': 'no active compass session'})
    _record_calib_session('compass', 'CANCELLED', s.started_at,
                          live_state=_safe_coverage(s))
    s.cancel(reason='user')
    return jsonify({'status': 'ok'})


@bp.route('/api/calibration/compass/result')
def compass_result():
    global _fit_result
    with _fit_lock:
        if _fit_result is None:
            return jsonify({'state': 'calculating'})
        result = _fit_result
        _fit_result = None
    return jsonify({'state': 'done', **result})


@bp.route('/api/calibration/compass/status')
def compass_status():
    if not os.path.exists(SENSORS_CAL_FILE):
        return jsonify({'state': 'not_calibrated',
                        'message': 'No calibration file found'})

    try:
        with open(SENSORS_CAL_FILE, 'r') as f:
            cal = json.load(f)
    except Exception as e:
        return jsonify({'state': 'poor',
                        'message': f'Cannot read calibration file: {e}'})

    compass_cal = cal.get('compass', cal)
    if not compass_cal.get('valid', False):
        return jsonify({'state': 'poor',
                        'message': 'Calibration file exists but is marked invalid'})

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
        return jsonify({'state': 'poor', 'message': ', '.join(reasons),
                        'calibration': compass_cal})
    return jsonify({'state': 'good', 'message': 'Calibrated',
                    'calibration': compass_cal})


# =========================================================================
# GYRO
# =========================================================================

@bp.route('/api/calibration/gyro/start', methods=['POST'])
def gyro_start():
    s, err, status = session_mod.start_stream('gyro')
    if s is None:
        return jsonify({'status': 'error', 'error': err}), status
    return jsonify({'status': 'ok', 'sensor': 'gyro'})


@bp.route('/api/calibration/gyro/progress')
def gyro_progress():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'gyro':
        return jsonify({'status': 'error',
                        'error': 'No gyro calibration in progress'}), 409

    s.touch()
    state = s.update_coverage()

    elapsed = time.time() - s.started_at if s.started_at else 0
    is_stable = bool(_check_stability(s))

    return jsonify({
        'status': 'ok',
        'samples': state['samples'],
        'coverage': round(state['coverage'], 3),
        'sectors_hit': state['sectors_hit'],
        'sectors_total': math_mod.COVERAGE_TOTAL_SECTORS,
        'elapsed_seconds': round(elapsed, 1),
        'last_reading': state['last_reading'],
        'is_stable': is_stable,
        'captures': state['window_count'],
        'capturing': state['capturing'],
    })


@bp.route('/api/calibration/gyro/capture', methods=['POST'])
def gyro_capture():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'gyro':
        return jsonify({'status': 'error',
                        'error': 'No gyro calibration in progress'}), 409

    result = s.capture()
    return jsonify({'status': 'ok', **result})


@bp.route('/api/calibration/gyro/stop', methods=['POST'])
def gyro_stop():
    global _fit_result
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'gyro':
        return jsonify({'status': 'error',
                        'error': 'No gyro calibration in progress'}), 409

    if getattr(s, '_capturing_window', False):
        return jsonify({
            'status': 'error',
            'error': 'Stop the current capture window before calculating.',
        }), 400

    closed_windows = len(getattr(s, '_capture_windows', []))
    if closed_windows < MIN_GYRO_CAPTURE_WINDOWS:
        return jsonify({
            'status': 'error',
            'error': 'Need at least 1 capture window. Hold the unit still and click Capture.',
        }), 400

    samples_full, _started_at = s.stop()
    gyro_raw = s._extract_window_raw_points(samples_full)

    if len(gyro_raw) == 0:
        log_event('warning', 'Gyro calibration aborted: no samples in capture windows',
                  'calibration')
        return jsonify({
            'status': 'error',
            'error': 'No samples found in capture windows. Hold the unit still during capture.',
        }), 400

    def _run_fit():
        global _fit_result
        try:
            calib_output = math_mod.run_gyro_calibration(gyro_raw)
            n, coverage, sectors_hit = math_mod.compute_coverage(gyro_raw)
            with _fit_lock:
                _fit_result = {
                    'status': 'ok',
                    'sensor': 'gyro',
                    'samples': len(gyro_raw),
                    'coverage': coverage,
                    'calib_output': calib_output,
                }
            log_event('info',
                      f'Gyro calibration finished ({len(gyro_raw)} raw samples)',
                      'calibration')
            _record_calib_session('gyro', 'APPLIED', _started_at,
                                  captured=len(gyro_raw), saved=_saved_cal('gyro'),
                                  raw_coverage=coverage)
        except Exception as e:
            log_event('error', f'Gyro fit failed: {e}', 'calibration')
            with _fit_lock:
                _fit_result = {
                    'status': 'error',
                    'error': str(e),
                    'reset': True,
                }
            _record_calib_session('gyro', 'FAILED', _started_at,
                                  captured=len(gyro_raw), error=e)

    with _fit_lock:
        _fit_result = None
    threading.Thread(target=_run_fit, daemon=True).start()

    return jsonify({
        'status': 'ok',
        'state': 'calculating',
        'samples': len(gyro_raw),
    })


@bp.route('/api/calibration/gyro/cancel', methods=['POST'])
def gyro_cancel():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'gyro':
        return jsonify({'status': 'ok', 'note': 'no active gyro session'})
    _record_calib_session('gyro', 'CANCELLED', s.started_at,
                          live_state=_safe_coverage(s))
    s.cancel(reason='user')
    return jsonify({'status': 'ok'})


@bp.route('/api/calibration/gyro/result')
def gyro_result():
    global _fit_result
    with _fit_lock:
        if _fit_result is None:
            return jsonify({'state': 'calculating'})
        result = _fit_result
        _fit_result = None
    return jsonify({'state': 'done', **result})


# =========================================================================
# ACCEL
# =========================================================================

@bp.route('/api/calibration/accel/start', methods=['POST'])
def accel_start():
    s, err, status = session_mod.start_stream('accel')
    if s is None:
        return jsonify({'status': 'error', 'error': err}), status
    return jsonify({'status': 'ok', 'sensor': 'accel'})


@bp.route('/api/calibration/accel/progress')
def accel_progress():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'accel':
        return jsonify({'status': 'error',
                        'error': 'No accel calibration in progress'}), 409

    s.touch()
    state = s.update_coverage()

    elapsed = time.time() - s.started_at if s.started_at else 0
    is_stable = bool(_check_stability(s))

    return jsonify({
        'status': 'ok',
        'samples': state['samples'],
        'coverage': round(state['coverage'], 3),
        'sectors_hit': state['sectors_hit'],
        'sectors_total': math_mod.COVERAGE_TOTAL_SECTORS,
        'elapsed_seconds': round(elapsed, 1),
        'last_reading': state['last_reading'],
        'is_stable': is_stable,
        'captures': state['window_count'],
        'capturing': state['capturing'],
    })


@bp.route('/api/calibration/accel/capture', methods=['POST'])
def accel_capture():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'accel':
        return jsonify({'status': 'error',
                        'error': 'No accel calibration in progress'}), 409

    result = s.capture()
    return jsonify({'status': 'ok', **result})


@bp.route('/api/calibration/accel/stop', methods=['POST'])
def accel_stop():
    global _fit_result
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'accel':
        return jsonify({'status': 'error',
                        'error': 'No accel calibration in progress'}), 409

    if getattr(s, '_capturing_window', False):
        return jsonify({
            'status': 'error',
            'error': 'Stop the current capture window before calculating.',
        }), 400

    closed_windows = len(getattr(s, '_capture_windows', []))
    if closed_windows < MIN_ACCEL_CAPTURE_WINDOWS:
        return jsonify({
            'status': 'error',
            'error': f'Need at least {MIN_ACCEL_CAPTURE_WINDOWS} windows. Only got {closed_windows}. '
                     f'Capture more positions.',
        }), 400

    samples_full, _started_at = s.stop()
    samples_3d = s._extract_window_raw_points(samples_full)

    if len(samples_3d) < math_mod.MIN_SAMPLES_10EIG:
        log_event('warning',
                  f'Accel calibration aborted: only {len(samples_3d)} raw samples '
                  f'(need {math_mod.MIN_SAMPLES_10EIG})',
                  'calibration')
        return jsonify({
            'status': 'error',
            'error': (
                f'Only {len(samples_3d)} raw samples collected '
                f'(need at least {math_mod.MIN_SAMPLES_10EIG}). '
                f'Hold each position for longer or add more capture windows.'
            ),
        }), 400

    def _run_fit():
        global _fit_result
        try:
            calib_output = math_mod.run_ellipsoid_calibration('accel', samples_3d)
            n, coverage, sectors_hit = math_mod.compute_coverage(samples_3d)
            with _fit_lock:
                _fit_result = {
                    'status': 'ok',
                    'sensor': 'accel',
                    'samples': n,
                    'coverage': coverage,
                    'calib_output': calib_output,
                }
            log_event('info',
                      f'Accel calibration finished ({n} raw samples, coverage {coverage:.0%})',
                      'calibration')
            _record_calib_session('accel', 'APPLIED', _started_at,
                                  captured=len(samples_3d), saved=_saved_cal('accel'),
                                  raw_coverage=coverage)
        except Exception as e:
            log_event('error', f'Accel fit failed: {e}', 'calibration')
            with _fit_lock:
                _fit_result = {
                    'status': 'error',
                    'error': str(e),
                    'reset': True,
                }
            _record_calib_session('accel', 'FAILED', _started_at,
                                  captured=len(samples_3d), error=e)

    with _fit_lock:
        _fit_result = None
    threading.Thread(target=_run_fit, daemon=True).start()

    return jsonify({
        'status': 'ok',
        'state': 'calculating',
        'samples': len(samples_3d),
    })


@bp.route('/api/calibration/accel/cancel', methods=['POST'])
def accel_cancel():
    s = session_mod.get_active_session()
    if s is None or s.sensor != 'accel':
        return jsonify({'status': 'ok', 'note': 'no active accel session'})
    _record_calib_session('accel', 'CANCELLED', s.started_at,
                          live_state=_safe_coverage(s))
    s.cancel(reason='user')
    return jsonify({'status': 'ok'})


@bp.route('/api/calibration/accel/result')
def accel_result():
    global _fit_result
    with _fit_lock:
        if _fit_result is None:
            return jsonify({'state': 'calculating'})
        result = _fit_result
        _fit_result = None
    return jsonify({'state': 'done', **result})
