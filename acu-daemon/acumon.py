#!/usr/bin/env python3
"""
Eureka ACU — Simplified Python Daemon
Writes a single JSON state file that cycles through the supervisor state machine.
Backend & frontend read this file and display real-time data.
"""

import os
import time
import json
import math
from datetime import datetime
from enum import Enum
from pathlib import Path

class ACUState(Enum):
    IDLE = "IDLE"
    READY = "READY"
    AUTO_POINTING = "AUTO_POINTING"
    TRACKING = "TRACKING"


class ACUDaemon:
    """Simple daemon that updates a JSON state file."""

    def __init__(self, runtime_dir=None):
        self.runtime_dir = Path(runtime_dir or "/tmp/eureka")
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.runtime_dir / "state.json"

        self.state = ACUState.IDLE
        self.azimuth = 0.0
        self.elevation = 30.0
        self.temperature = 27.0
        self.modem_lock = False
        self.esa_ok = False
        self.cycle = 0

    def write_state(self):
        """Write current state to JSON file."""
        data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "state": self.state.value,
            "azimuth": round(self.azimuth, 2),
            "elevation": round(self.elevation, 2),
            "temperature": round(self.temperature, 2),
            "modem_lock": self.modem_lock,
            "esa_ok": self.esa_ok,
        }
        self.state_file.write_text(json.dumps(data, indent=2))

    def run(self):
        """Main daemon loop."""
        print("[ACU] Starting daemon...")

        while True:
            self.cycle += 1

            # State machine cycle: IDLE → READY → AUTO_POINTING → TRACKING → (repeat)
            if self.cycle == 1:
                self.state = ACUState.IDLE
                self.modem_lock = False
                self.esa_ok = False
                print("[ACU] → IDLE")

            elif self.cycle == 3:
                self.state = ACUState.READY
                self.modem_lock = True
                self.esa_ok = True
                print("[ACU] → READY (hw ok)")

            elif self.cycle == 5:
                self.state = ACUState.AUTO_POINTING
                self.azimuth = 0.0
                self.elevation = 20.0
                print("[ACU] → AUTO_POINTING")

            elif self.cycle == 7:
                self.state = ACUState.TRACKING
                print("[ACU] → TRACKING (locked)")

            elif self.cycle >= 11:
                self.cycle = 0  # Reset for next iteration
                continue

            # Smooth pointing movement during tracking
            if self.state == ACUState.TRACKING:
                # Oscillate around target
                self.azimuth = 45.0 + 20.0 * math.sin(self.cycle / 3.0)
                self.elevation = 35.0 + 5.0 * math.cos(self.cycle / 3.0)

            # Temperature variation
            self.temperature = 27.0 + 2.0 * math.sin(self.cycle / 5.0)

            self.write_state()
            print(f"[ACU] {self.state.value} | AZ={self.azimuth:.1f}° EL={self.elevation:.1f}° T={self.temperature:.1f}°C")

            time.sleep(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Eureka ACU Daemon (simplified)")
    parser.add_argument("-d", "--datadir", default="/tmp/eureka", help="Runtime data directory")
    parser.add_argument("-f", "--foreground", action="store_true", help="Run in foreground")
    args = parser.parse_args()

    daemon = ACUDaemon(runtime_dir=args.datadir)
    daemon.run()
