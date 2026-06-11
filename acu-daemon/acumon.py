#!/usr/bin/env python3
"""
Eureka ACU — Simplified Python Daemon
Demonstrates supervisor state machine, pointing control, and sensor integration.
Real hardware would run in C on Raspberry Pi; this is a portfolio showcase.
"""

import os
import time
import json
import math
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path

# ============================================================================
# State Machine
# ============================================================================

class ACUState(Enum):
    INIT = "INIT"
    IDLE = "IDLE"
    READY = "READY"
    AUTO_POINTING = "AUTO_POINTING"
    TRACKING = "TRACKING"
    FAULT = "FAULT"


class ACUDaemon:
    """Supervisor state machine and operational control."""

    def __init__(self, runtime_dir=None):
        self.runtime_dir = Path(runtime_dir or "/var/lib/eureka")
        self.log_dir = self.runtime_dir / "var/log/acu"
        self.config_dir = self.runtime_dir / "etc/acu"

        # Create directories
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.state = ACUState.INIT
        self.lock = threading.Lock()

        # Hardware status
        self.modem_ok = False
        self.esa_ok = False
        self.compass_ok = False
        self.calibrated = False

        # Pointing state
        self.azimuth = 0.0
        self.elevation = 30.0
        self.target_az = 0.0
        self.target_el = 30.0

        # Sensor data (fake)
        self.temperature = 27.0
        self.pressure = 100.5
        self.compass = [0.0, 0.0, 50.0]  # 3-axis magnetometer
        self.gps_lat = 48.8566
        self.gps_lon = 2.3522

        self._init_logs()
        self._load_config()

    def _init_logs(self):
        """Create log files."""
        self.msg_log = self.log_dir / "acu_msg.log"
        self.err_log = self.log_dir / "acu_err.log"
        self.pointing_dat = self.log_dir / "pointing.dat"
        self.sensors_dat = self.log_dir / "sensors.dat"
        self.modem_dat = self.log_dir / "modem_stats.dat"

        for f in [self.msg_log, self.err_log]:
            if not f.exists():
                f.touch()

    def _load_config(self):
        """Load config.ini (simplified)."""
        cfg_path = self.config_dir / "config.ini"
        if not cfg_path.exists():
            # Create minimal config
            cfg_path.write_text("""[Location]
latitude=48.8566
longitude=2.3522
altitude=35

[Satellites]
active=SES-14

[Sensors]
gyroRange=2000
magRange=4900

[Antenna]
minElevation=10
maxElevation=90
""")

    def log_msg(self, msg):
        """Log informational message."""
        now = datetime.now().isoformat()
        line = f"[{now}] {msg}\n"
        self.msg_log.write_text(self.msg_log.read_text() + line)
        print(f"[ACU] {msg}")

    def log_err(self, msg):
        """Log error message."""
        now = datetime.now().isoformat()
        line = f"[{now}] ERROR: {msg}\n"
        self.err_log.write_text(self.err_log.read_text() + line)
        print(f"[ACU ERROR] {msg}")

    def write_telemetry(self):
        """Write current sensor data to .dat files."""
        # Pointing data
        pointing_line = f"{datetime.now().isoformat()} AZ={self.azimuth:.1f} EL={self.elevation:.1f} STATE={self.state.value}\n"
        self.pointing_dat.write_text(self.pointing_dat.read_text() + pointing_line)

        # Sensor data
        mag_norm = math.sqrt(sum(x**2 for x in self.compass))
        sensor_line = f"{datetime.now().isoformat()} TEMP={self.temperature:.2f} PRES={self.pressure:.2f} MAG_NORM={mag_norm:.1f}\n"
        self.sensors_dat.write_text(self.sensors_dat.read_text() + sensor_line)

        # Modem data
        modem_line = f"{datetime.now().isoformat()} LOCKED={'Y' if self.modem_ok else 'N'} SIGNAL=85\n"
        self.modem_dat.write_text(self.modem_dat.read_text() + modem_line)

    def transition(self, new_state, reason=""):
        """State machine transition with guards."""
        with self.lock:
            old_state = self.state

            # Transition rules
            if new_state == ACUState.READY:
                if self.modem_ok and self.esa_ok and self.calibrated:
                    self.state = new_state
                    self.log_msg(f"→ READY: {reason}")
                    return True
                else:
                    self.log_err(f"Cannot enter READY: modem={self.modem_ok}, esa={self.esa_ok}, cal={self.calibrated}")
                    return False

            elif new_state == ACUState.AUTO_POINTING:
                if self.state in [ACUState.READY, ACUState.TRACKING]:
                    self.state = new_state
                    self.log_msg(f"→ AUTO_POINTING: {reason}")
                    return True

            elif new_state == ACUState.TRACKING:
                if self.state == ACUState.AUTO_POINTING:
                    self.state = new_state
                    self.log_msg(f"→ TRACKING: {reason}")
                    return True

            elif new_state == ACUState.IDLE:
                self.state = new_state
                self.log_msg(f"→ IDLE: {reason}")
                return True

            elif new_state == ACUState.FAULT:
                self.state = new_state
                self.log_err(f"FAULT: {reason}")
                return True

            return False

    def pointing_loop(self):
        """Main pointing control loop (runs in thread)."""
        while True:
            with self.lock:
                # Update synthetic sensor data
                self.temperature += (0.1 * (25 - self.temperature) + (0.5 - 0.5 * 2))
                self.pressure = 100.5 + 0.2 * math.sin(time.time() / 20)

                # Compass rotates with pointing angle
                angle_rad = math.radians(self.azimuth)
                self.compass = [
                    40 * math.cos(angle_rad),
                    40 * math.sin(angle_rad),
                    20
                ]

                # Smooth pointing movement
                if abs(self.azimuth - self.target_az) > 0.5:
                    self.azimuth += (self.target_az - self.azimuth) * 0.05
                if abs(self.elevation - self.target_el) > 0.5:
                    self.elevation += (self.target_el - self.elevation) * 0.05

                self.write_telemetry()

            time.sleep(0.5)

    def supervisor_loop(self):
        """State machine automation (simplified for demo)."""
        cycle = 0
        while True:
            cycle += 1

            with self.lock:
                # Simulate hardware ready (after a few seconds)
                if cycle == 2:
                    self.modem_ok = True
                    self.esa_ok = True
                    self.calibrated = True
                    self.log_msg("Hardware initialized")

                # State transitions for demo
                if self.state == ACUState.INIT and cycle >= 2:
                    self.transition(ACUState.IDLE, "boot complete")

                elif self.state == ACUState.IDLE and cycle >= 3:
                    self.transition(ACUState.READY, "hw ready")

                elif self.state == ACUState.READY and cycle >= 4:
                    self.transition(ACUState.AUTO_POINTING, "scanning")
                    # Set target satellite position
                    self.target_az = 45.0
                    self.target_el = 35.0

                elif self.state == ACUState.AUTO_POINTING and cycle >= 6:
                    self.transition(ACUState.TRACKING, "locked")
                    self.log_msg("Satellite lock acquired")

                elif self.state == ACUState.TRACKING and cycle >= 10:
                    self.transition(ACUState.IDLE, "manual stop")

            time.sleep(1)

    def run(self):
        """Start daemon (supervisor + pointing threads)."""
        self.log_msg("ACU Daemon started")

        # Start threads
        sup_thread = threading.Thread(target=self.supervisor_loop, daemon=True)
        pnt_thread = threading.Thread(target=self.pointing_loop, daemon=True)

        sup_thread.start()
        pnt_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.log_msg("Shutdown requested")
            self.transition(ACUState.IDLE, "shutdown")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Eureka ACU Daemon (Python demo)")
    parser.add_argument("-d", "--datadir", default="/tmp/eureka", help="Runtime data directory")
    parser.add_argument("-f", "--foreground", action="store_true", help="Run in foreground")
    args = parser.parse_args()

    daemon = ACUDaemon(runtime_dir=args.datadir)
    daemon.run()
