"""
sensor_readers.py - Tail-reader for /var/log/acu/sensors.dat.

acumon writes one line per iteration in SYNC format:
    SYNC 1765432100|12345,-456,7890|-12345,6789,1234|5678,9012,1234

Fields:
    timestamp_us: monotonic microseconds
    ax,ay,az: accel raw counts (int16)
    gx,gy,gz: gyro raw counts (int16)
    mx,my,mz: mag raw counts (int16)

The reader runs a daemon thread following the file from EOF. It exposes:
    - get_latest() -> (ax,ay,az, gx,gy,gz, mx,my,mz, timestamp_us) or None
    - get_latest_accel() -> (ax,ay,az, timestamp_us) or None
    - get_latest_gyro() -> (gx,gy,gz, timestamp_us) or None
    - get_latest_mag() -> (mx,my,mz, timestamp_us) or None
    - start_recording() -> begin accumulating samples
    - stop_recording() -> stop, return (samples_list, started_at)
    - cancel_recording() -> stop, drop samples
    - snapshot_samples() -> read-only copy of current samples
    - snapshot_mag_samples() -> mag-only 3-tuples for compass fit
    - snapshot_accel_samples() -> accel-only 3-tuples
    - snapshot_gyro_samples() -> gyro-only 3-tuples
    - get_status() -> dict with recording flag, sample count, etc.

Control flow (high-freq mode) is managed by calibration_acumon.py via the
CLI protocol. SyncReader does NOT parse CAL_START/CAL_STOP — those are
human-readable annotations in sensors.dat. The backend trusts the CLI
handshake (set_calib_mode returns ok=True) to know when to start recording.
"""

import os
import re
import time
import threading

from shared import ACU_SENSORS_DAT


# ---------------------------------------------------------------------------
# Regex for SYNC lines
# ---------------------------------------------------------------------------
# Format: SYNC timestamp|ax,ay,az|gx,gy,gz|mx,my,mz
_SYNC_LINE_RE = re.compile(
    r'SYNC\s+(\d+)\|(-?\d+),(-?\d+),(-?\d+)\|(-?\d+),(-?\d+),(-?\d+)\|(-?\d+),(-?\d+),(-?\d+)'
)


# ---------------------------------------------------------------------------
# SyncReader - single source of truth for all sensors
# ---------------------------------------------------------------------------

class SyncReader:
    """Tails sensors.dat, parses SYNC lines, stores the latest complete sample
    and (when recording) accumulates samples."""

    def __init__(self, path=ACU_SENSORS_DAT):
        self.path = path
        self._lock = threading.Lock()

        # Latest complete reading + timestamp
        self.latest = None  # (ax,ay,az, gx,gy,gz, mx,my,mz, timestamp_us)
        self.latest_at = None  # time.time() when read

        # Recording state
        self.recording = False
        self.recording_started_at = None
        self.samples = []  # list of (ax,ay,az, gx,gy,gz, mx,my,mz, timestamp_us)

        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    # ----- thread / file following -----

    def _watch(self):
        while True:
            try:
                self._follow_file()
            except Exception as e:
                print(f'[SyncReader] error: {e}', flush=True)
                time.sleep(1)

    def _follow_file(self):
        while not os.path.exists(self.path):
            time.sleep(1)
        with open(self.path, 'r') as f:
            f.seek(0, os.SEEK_END)
            inode = os.fstat(f.fileno()).st_ino
            while True:
                line = f.readline()
                if line:
                    self._process_line(line)
                    continue
                time.sleep(0.1)
                try:
                    if os.stat(self.path).st_ino != inode:
                        break  # file rotated, reopen
                except FileNotFoundError:
                    break

    def _process_line(self, line):
        m = _SYNC_LINE_RE.search(line.strip())
        if not m:
            return

        try:
            timestamp_us = int(m.group(1))
            ax = int(m.group(2))
            ay = int(m.group(3))
            az = int(m.group(4))
            gx = int(m.group(5))
            gy = int(m.group(6))
            gz = int(m.group(7))
            mx = int(m.group(8))
            my = int(m.group(9))
            mz = int(m.group(10))
        except ValueError:
            return

        now = time.time()
        sample = (ax, ay, az, gx, gy, gz, mx, my, mz, timestamp_us)

        with self._lock:
            self.latest = sample
            self.latest_at = now
            if self.recording:
                self.samples.append(sample)

    # ----- public API -----

    def get_latest(self):
        """Return the latest complete sample or None.
        Returns: (ax, ay, az, gx, gy, gz, mx, my, mz, timestamp_us)"""
        with self._lock:
            return self.latest

    def get_latest_accel(self):
        """Return the latest accel reading with its timestamp.
        Returns: (ax, ay, az, timestamp_us) or None"""
        with self._lock:
            if self.latest is None:
                return None
            return (self.latest[0], self.latest[1], self.latest[2], self.latest[9])

    def get_latest_gyro(self):
        """Return the latest gyro reading with its timestamp.
        Returns: (gx, gy, gz, timestamp_us) or None"""
        with self._lock:
            if self.latest is None:
                return None
            return (self.latest[3], self.latest[4], self.latest[5], self.latest[9])

    def get_latest_mag(self):
        """Return the latest mag reading with its timestamp.
        Returns: (mx, my, mz, timestamp_us) or None"""
        with self._lock:
            if self.latest is None:
                return None
            return (self.latest[6], self.latest[7], self.latest[8], self.latest[9])

    def get_latest_with_age(self):
        """Return the latest sample and its age in seconds.
        Returns: (sample, age_seconds) or (None, None)"""
        with self._lock:
            if self.latest is None:
                return None, None
            return self.latest, time.time() - self.latest_at

    def start_recording(self):
        """Start accumulating samples.
        
        The caller (calibration_session) must have already confirmed that
        acumon is in high-freq mode via the CLI protocol. We trust that
        handshake and start recording immediately."""
        with self._lock:
            self.samples = []
            self.recording = True
            self.recording_started_at = time.time()

    def stop_recording(self):
        """Stop accumulating, return collected samples and start time.
        Returns: (samples_list, started_at)"""
        with self._lock:
            self.recording = False
            samples = list(self.samples)
            started_at = self.recording_started_at
            self.recording_started_at = None
            return samples, started_at

    def cancel_recording(self):
        """Stop accumulating and discard collected samples."""
        with self._lock:
            self.recording = False
            self.samples = []
            self.recording_started_at = None

    def snapshot_samples(self):
        """Return a copy of currently accumulated samples."""
        with self._lock:
            return list(self.samples)

    def snapshot_mag_samples(self):
        """Return mag-only samples as 3-tuples (mx, my, mz) for compass fit.

        The internal 10-tuple layout is opaque to callers — they only see
        the magnetic field components needed for ellipsoid fitting, as
        required by AN4246 / MotionCal (raw magnetometer in sensor frame)."""
        with self._lock:
            return [(s[6], s[7], s[8]) for s in self.samples]

    def snapshot_accel_samples(self):
        """Return accel-only samples as 3-tuples (ax, ay, az).

        Reserved for AN4246 orientation filter (selecting magnetometer
        samples at significantly different roll/pitch angles) and for
        tilt compensation in runtime heading calculation."""
        with self._lock:
            return [(s[0], s[1], s[2]) for s in self.samples]

    def snapshot_gyro_samples(self):
        """Return gyro-only samples as 3-tuples (gx, gy, gz).

        Reserved for future gyro calibration (bias estimation from
        static samples)."""
        with self._lock:
            return [(s[3], s[4], s[5]) for s in self.samples]

    def get_status(self):
        """Return dict with current status."""
        with self._lock:
            return {
                'recording': self.recording,
                'sample_count': len(self.samples),
                'latest': self.latest,
                'latest_at': self.latest_at,
                'started_at': self.recording_started_at,
            }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

sync_reader = SyncReader()


def get_reader(sensor=None):
    """Return the SyncReader singleton.
    sensor parameter is ignored for backward compatibility."""
    return sync_reader