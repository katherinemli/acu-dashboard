"""
calibration_session.py - Calibration session state management.

This module owns the runtime state of an in-progress calibration. It
guarantees that:

    1. At most one calibration runs at a time across all 3 sensors.
       (single-user assumption -- one browser, one ACU, one user)

    2. While a calibration is active, acumon is in high-frequency mode.
       When it ends (stop / cancel / watchdog), acumon is returned to
       normal frequency.

    3. If the frontend disappears (tab closed, network lost, user navigates
       away) without sending /cancel, a background watchdog auto-cancels
       after a timeout.

Session type:

    StreamSession  -- compass, gyro, accel; samples accumulate continuously.
                      Compass: user rotates freely, coverage is automatic.
                      Gyro/Accel: user toggles Capture/Stop Capture to mark
                      windows. On stop, window means are extracted and
                      passed to the 10-EIG ellipsoid fit.
                      All timestamps use CLOCK_MONOTONIC from icm_main.c.
                      Watchdog: 20s since last /progress poll.

Acceptable state transitions:

    idle --start--> active --stop or cancel--> idle
                       |
                       +--watchdog timeout--> idle

There is no resume. If a session ends for any reason, the next start is fresh.

Public API:
    get_active_session()           -> Session or None
    start_stream(sensor)           -> (ok, error_msg, http_status)
    start_watchdog()               -> call once at app startup
"""

import time
import threading

import numpy as np

from shared import log_event
from sensor_readers import get_reader
from calibration_acumon import set_calib_mode
import calibration_math as math_mod


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STREAM_WATCHDOG_TIMEOUT_S = 20      # 20s without /progress poll
WATCHDOG_CHECK_INTERVAL_S = 5       # how often the watchdog thread wakes up


# ---------------------------------------------------------------------------
# Module-global state
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_active_session = None

_status_callback = None


def set_status_callback(fn):
    """Register a callback that receives the new ACU status string when a
    session starts or ends."""
    global _status_callback
    _status_callback = fn


def _notify_status(status):
    if _status_callback is not None:
        try:
            _status_callback(status)
        except Exception as e:
            log_event('warning', f'Status callback failed: {e}', 'calibration')


def get_active_session():
    """Return the currently-active session, or None."""
    with _lock:
        return _active_session


# ---------------------------------------------------------------------------
# Base session class
# ---------------------------------------------------------------------------

class CalibrationSession:
    """Base class. Subclasses implement sensor-specific logic but share
    lifecycle (start/stop/cancel/watchdog)."""

    SENSOR = None
    WATCHDOG_TIMEOUT_S = STREAM_WATCHDOG_TIMEOUT_S

    def __init__(self):
        self.sensor = self.SENSOR
        self.started_at = None
        self.last_activity_at = None
        self.error = None
        self._reader = get_reader(self.sensor)
        if self._reader is None:
            raise ValueError(f'No reader for sensor {self.sensor!r}')

    # ----- lifecycle -----

    def start(self):
        """Acquire global session slot, enable acumon calib mode, start
        recording. Returns (ok, error_msg)."""
        global _active_session
        with _lock:
            if _active_session is not None:
                return False, (
                    f'{_active_session.sensor} calibration already in progress'
                )
            _active_session = self

        ok, msg = set_calib_mode(True)
        if not ok:
            with _lock:
                _active_session = None
            return False, f'Could not enable acumon calib mode: {msg}'

        try:
            self._reader.start_recording()
            self.started_at = time.time()
            self.last_activity_at = self.started_at
            self._on_started()
        except Exception as e:
            set_calib_mode(False)
            with _lock:
                _active_session = None
            return False, f'Failed to start reader: {e}'

        _notify_status('calibration')
        log_event(
            'info',
            f'{self.sensor} calibration started ({self.__class__.__name__})',
            'calibration',
        )
        return True, ''

    def stop(self):
        """Stop recording, disable acumon calib mode, return samples.
        Returns (samples_full, started_at). Releases the session slot."""
        samples_full, started_at = self._reader.stop_recording()
        ok, msg = set_calib_mode(False)
        self._release_slot()
        if not ok:
            log_event(
                'warning',
                f'{self.sensor} session ended but acumon calib mode disable failed: {msg}',
                'calibration',
            )
        return samples_full, started_at

    def cancel(self, reason='user'):
        """Drop samples, disable acumon calib mode, release slot."""
        self._reader.cancel_recording()
        ok, msg = set_calib_mode(False)
        self._release_slot()
        if not ok:
            log_event(
                'error',
                f'{self.sensor} cancel ({reason}): acumon calib disable failed: {msg}',
                'calibration',
            )
        else:
            log_event(
                'info',
                f'{self.sensor} calibration cancelled ({reason})',
                'calibration',
            )

    def _release_slot(self):
        global _active_session
        with _lock:
            if _active_session is self:
                _active_session = None
        _notify_status('idle')

    # ----- watchdog -----

    def is_inactive(self):
        if self.last_activity_at is None:
            return False
        return (time.time() - self.last_activity_at) > self.WATCHDOG_TIMEOUT_S

    def touch(self):
        self.last_activity_at = time.time()

    # ----- subclass hook -----

    def _on_started(self):
        pass


# ---------------------------------------------------------------------------
# Stream session -- compass / gyro / accel
# ---------------------------------------------------------------------------

class StreamSession(CalibrationSession):
    """Continuous-sample session for all three sensors.

    Compass: samples accumulate while the user rotates. Coverage is
    tracked incrementally via icosahedron sectors. Stop runs the
    10-EIG ellipsoid fit on all magnetometer samples.

    Gyro: user toggles Capture to mark static windows. On stop, all raw
    samples from closed windows are collected and passed to
    run_gyro_calibration (simple zero-bias mean — ellipsoid fit does not
    apply to angular-rate data).

    Accel: user toggles Capture to mark quiet positions. On stop, all raw
    samples from closed windows are collected into a flat point cloud and
    passed to the 10-EIG ellipsoid fit (requires >150 points; raw cloud
    instead of per-window means ensures sufficient density).

    All timestamps use CLOCK_MONOTONIC from icm_main.c for consistent
    window boundaries.

    Maintains incremental coverage state so /progress polls run in O(K)
    where K is the number of samples that arrived since the last poll,
    instead of O(N) where N is the total accumulated.

    All coverage state lives in the session object only. No disk, no
    globals. When the session is released (stop/cancel/watchdog) the
    state goes with it -- next calibration starts fresh."""

    WATCHDOG_TIMEOUT_S = STREAM_WATCHDOG_TIMEOUT_S

    def __init__(self, sensor):
        if sensor not in ('compass', 'gyro', 'accel'):
            raise ValueError(f'StreamSession does not support {sensor!r}')
        self.SENSOR = sensor
        self._capture_windows = []     # list of (start_ts, end_ts)
        self._capturing_window = False
        self._window_start = 0
        super().__init__()
        self._sectors_hit = set()
        self._last_processed_index = 0
        self._centroid = None
        self._last_reading = None

    def _on_started(self):
        self._sectors_hit = set()
        self._last_processed_index = 0
        self._centroid = None
        self._last_reading = None
        self._capture_windows = []
        self._capturing_window = False
        self._window_start = 0

    def capture(self):
        """Toggle capture window using CLOCK_MONOTONIC timestamps.

        If no window is open, opens one (records start timestamp).
        If a window is open, closes it (records end timestamp) and
        stores the (start, end) pair.

        Returns dict with current state and number of closed windows."""
        samples = self._reader.snapshot_samples()
        ts = samples[-1][9] if samples else 0

        if self._capturing_window:
            self._capture_windows.append((self._window_start, ts))
            self._capturing_window = False
            self.touch()
            return {
                'state': 'idle',
                'captures': len(self._capture_windows),
            }
        else:
            self._window_start = ts
            self._capturing_window = True
            self.touch()
            return {
                'state': 'capturing',
                'captures': len(self._capture_windows),
            }

    def _extract_window_means(self, samples_full):
        """For gyro/accel: compute the per-axis mean of each closed window.

        samples_full is a list of 10-tuples from the reader where index 9
        is the CLOCK_MONOTONIC timestamp in microseconds. Returns a list
        of (x, y, z) tuples, one per closed window."""
        if not self._capture_windows:
            return []

        points = []
        for t_start, t_end in self._capture_windows:
            window = [s for s in samples_full if t_start <= s[9] <= t_end]
            if window:
                arr = np.array(window, dtype=np.float64)
                if self.SENSOR == 'accel':
                    points.append((
                        float(arr[:, 0].mean()),
                        float(arr[:, 1].mean()),
                        float(arr[:, 2].mean()),
                    ))
                else:
                    points.append((
                        float(arr[:, 3].mean()),
                        float(arr[:, 4].mean()),
                        float(arr[:, 5].mean()),
                    ))
        return points

    def _extract_window_raw_points(self, samples_full):
        """For gyro/accel: collect every raw sample from all closed windows.

        Returns a flat list of (x, y, z) tuples covering all SYNC samples
        that fall inside any closed capture window. Accel uses indices 0-2,
        gyro uses indices 3-5 from the 10-tuple."""
        if not self._capture_windows:
            return []

        col = 0 if self.SENSOR == 'accel' else 3
        points = []
        for t_start, t_end in self._capture_windows:
            for s in samples_full:
                if t_start <= s[9] <= t_end:
                    points.append((s[col], s[col + 1], s[col + 2]))
        return points

    def update_coverage(self):
        """Process any new samples since the last call; update the running
        sectors_hit set and centroid. Returns a dict with everything the
        /progress endpoint needs."""
        if self.SENSOR == 'gyro':
            all_samples = self._reader.snapshot_gyro_samples()
        elif self.SENSOR == 'accel':
            all_samples = self._reader.snapshot_accel_samples()
        else:
            all_samples = self._reader.snapshot_mag_samples()

        n_total = len(all_samples)

        if n_total >= 2:
            arr_full = np.asarray(all_samples, dtype=np.float64)
            self._centroid = (arr_full.max(axis=0) + arr_full.min(axis=0)) / 2.0
        else:
            arr_full = None
            self._centroid = None

        if n_total > self._last_processed_index and self._centroid is not None:
            new_arr = np.asarray(
                all_samples[self._last_processed_index:],
                dtype=np.float64,
            )
            keep = np.all(np.abs(new_arr) <= math_mod.RAW_SAMPLE_LIMIT, axis=1)
            new_clean = new_arr[keep]

            if new_clean.shape[0] > 0:
                centered = new_clean - self._centroid
                norms = np.linalg.norm(centered, axis=1, keepdims=True)
                # Reject samples whose centered norm is within 10% of the field
                # magnitude. In calib mode (NUM_TO_AVERAGE_CALIB=1) raw sensor
                # noise reaches ~35 units; 10% of the ~460-580 unit field gives
                # a floor well above noise but well below any real rotation.
                # Confirmed against three units with live calib-mode data.
                noise_floor = float(np.linalg.norm(self._centroid)) * 0.10
                valid = (norms.squeeze(-1) >= noise_floor)
                if valid.any():
                    safe_norms = np.where(norms < noise_floor, 1.0, norms)
                    normed = centered / safe_norms
                    dots = normed @ math_mod.CENTROIDS_NP.T
                    nearest = np.argmax(dots, axis=1)
                    self._sectors_hit.update(int(i) for i in nearest[valid])

            self._last_processed_index = n_total

        if self.SENSOR == 'gyro':
            latest = self._reader.get_latest_gyro()
        elif self.SENSOR == 'accel':
            latest = self._reader.get_latest_accel()
        else:
            latest = self._reader.get_latest_mag()

        if latest is not None:
            lx, ly, lz, _ts = latest
            self._last_reading = {'x': lx, 'y': ly, 'z': lz}

        sectors_hit = len(self._sectors_hit)
        coverage = sectors_hit / math_mod.COVERAGE_TOTAL_SECTORS

        return {
            'samples': n_total,
            'sectors_hit': sectors_hit,
            'coverage': coverage,
            'centroid': self._centroid,
            'last_reading': self._last_reading,
            'samples_array': arr_full,
            'capturing': self._capturing_window,
            'window_count': len(self._capture_windows),
        }


# ---------------------------------------------------------------------------
# Public start helpers
# ---------------------------------------------------------------------------

def start_stream(sensor):
    """Start a stream calibration session for the given sensor.
    Returns (session, error_msg, http_status)."""
    try:
        s = StreamSession(sensor)
    except ValueError as e:
        return None, str(e), 400
    ok, msg = s.start()
    if not ok:
        status = 409 if 'already in progress' in msg else 500
        return None, msg, status
    return s, '', 200


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

_watchdog_thread = None
_watchdog_running = False


def _watchdog_loop():
    log_event('info', 'Calibration watchdog started', 'calibration')
    while _watchdog_running:
        try:
            session = get_active_session()
            if session is not None and session.is_inactive():
                log_event(
                    'warning',
                    f'Watchdog timeout: cancelling {session.sensor} calibration '
                    f'(no activity for >{session.WATCHDOG_TIMEOUT_S}s)',
                    'calibration',
                )
                try:
                    session.cancel(reason='watchdog timeout')
                except Exception as e:
                    log_event(
                        'error',
                        f'Watchdog cancel failed: {e}',
                        'calibration',
                    )
        except Exception as e:
            log_event('error', f'Watchdog loop error: {e}', 'calibration')
        time.sleep(WATCHDOG_CHECK_INTERVAL_S)


def start_watchdog():
    global _watchdog_thread, _watchdog_running
    if _watchdog_thread is not None and _watchdog_thread.is_alive():
        return
    _watchdog_running = True
    _watchdog_thread = threading.Thread(target=_watchdog_loop, daemon=True)
    _watchdog_thread.start()