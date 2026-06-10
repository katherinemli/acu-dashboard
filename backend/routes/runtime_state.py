"""
runtime_state.py - Transitional in-memory runtime state for the dashboard.

get_runtime_mode() reads the supervisor mode file written by acumon on every
state transition (/var/log/acu/supervisor_mode). This is the real mode.

_runtime_mode is kept as a fallback for when acumon is not running (e.g.
during calibration, where acumon -c runs as a separate subprocess and the
main daemon is stopped). Calibration routes may call set_runtime_mode() to
keep the UI consistent during that window.
"""

import json

from shared import ACU_SUPERVISOR_MODE_FILE

_runtime_mode = 'idle'

_VALID_MODES = frozenset({
    'init', 'idle', 'calibrating', 'ready',
    'auto_pointing', 'tracking', 'manual_pointing', 'stopped', 'fault', 'unknown',
})

def get_runtime_mode():
    try:
        with open(ACU_SUPERVISOR_MODE_FILE, 'r') as f:
            raw = f.read().strip()
        # New format is JSON {"mode":...}; old format was the bare mode string.
        mode = (json.loads(raw).get('mode', '') if raw.startswith('{') else raw).lower()
        if mode in _VALID_MODES:
            return mode
    except Exception:
        pass
    return _runtime_mode


def set_runtime_mode(mode):
    global _runtime_mode
    _runtime_mode = mode
