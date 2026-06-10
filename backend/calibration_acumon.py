"""
calibration_acumon.py - Wrapper around acumon's CLI command protocol for
toggling calibration mode (high-frequency sensor logging).

acumon writes to /var/log/acu/sensors.dat at a normal rate by default. When
we send the 'calib mode on' command, it ramps the write frequency way up so
we get enough samples to do a proper fit.

The CLI protocol is:
    1. write '0' to ACU_CLI_CMD_DONE  (reset done flag)
    2. write command string to ACU_CLI_CMD_INPUT
    3. SIGUSR1 (kill -10) the acumon process
    4. poll ACU_CLI_CMD_DONE for '1' (with timeout)
    5. read result from ACU_CLI_CMD_OUTPUT

The CLI params for calib mode are: [3, 1, 1] to enable, [3, 1, 0] to disable.

This module exposes one function: set_calib_mode(enabled). It retries on
failure because the consequence of a missed disable is acumon staying in
high-freq mode forever — that's the whole reason the watchdog exists.
"""

import time
import subprocess

from shared import (
    log_event,
    ACU_CLI_CMD_INPUT, ACU_CLI_CMD_OUTPUT, ACU_CLI_CMD_DONE,
)


_RETRY_COUNT = 3
_RETRY_DELAY_S = 0.2
_CMD_TIMEOUT_S = 5


def _send_cli_command(params, timeout=_CMD_TIMEOUT_S):
    """Send a command to acumon via the cmd_input.txt / SIGUSR1 protocol.
    Returns (ok: bool, output_or_error: str)."""
    cmd_str = ' '.join(str(p) for p in params)
    try:
        # Reset done flag
        subprocess.run(
            ['sudo', 'tee', ACU_CLI_CMD_DONE],
            input='0\n', capture_output=True, text=True, timeout=3,
        )
        # Write command
        subprocess.run(
            ['sudo', 'tee', ACU_CLI_CMD_INPUT],
            input=cmd_str + '\n', capture_output=True, text=True, timeout=3,
        )
        # Find acumon PID(s)
        pgrep = subprocess.run(
            ['pgrep', '-x', 'acumon'],
            capture_output=True, text=True, timeout=3,
        )
        if pgrep.returncode != 0 or not pgrep.stdout.strip():
            return False, 'acumon process not found'

        # Signal each PID
        for pid in pgrep.stdout.strip().split('\n'):
            subprocess.run(['sudo', 'kill', '-10', pid.strip()], timeout=3)

        # Wait for done flag
        start = time.time()
        while time.time() - start < timeout:
            try:
                with open(ACU_CLI_CMD_DONE, 'r') as f:
                    if f.read().strip() == '1':
                        try:
                            with open(ACU_CLI_CMD_OUTPUT, 'r') as out:
                                return True, out.read()
                        except FileNotFoundError:
                            return True, ''
            except FileNotFoundError:
                pass
            time.sleep(0.2)

        return False, f'timeout waiting for acumon (>{timeout}s)'
    except subprocess.TimeoutExpired:
        return False, 'subprocess timeout'
    except Exception as e:
        return False, f'{type(e).__name__}: {e}'


def set_calib_mode(enabled):
    """Tell acumon to enter (True) or exit (False) calibration mode.

    Retries up to _RETRY_COUNT times. Returns (ok: bool, msg: str).

    Logs at info on success, warning on individual retry failures, error if
    all attempts fail (only matters in practice for the disable path: if we
    can't disable calib mode, acumon stays in high-frequency forever).
    """
    params = [3, 1, 1 if enabled else 0]
    action = 'enter' if enabled else 'exit'
    last_msg = ''

    for attempt in range(1, _RETRY_COUNT + 1):
        ok, msg = _send_cli_command(params)
        if ok:
            log_event(
                'info',
                f'Acumon calib mode {"enabled" if enabled else "disabled"}'
                + (f' (attempt {attempt})' if attempt > 1 else ''),
                'calibration',
            )
            return True, msg
        last_msg = msg
        log_event(
            'warning',
            f'Failed to {action} acumon calib mode (attempt {attempt}/{_RETRY_COUNT}): {msg}',
            'calibration',
        )
        if attempt < _RETRY_COUNT:
            time.sleep(_RETRY_DELAY_S)

    # All attempts exhausted
    log_event(
        'error',
        f'Could not {action} acumon calib mode after {_RETRY_COUNT} attempts. '
        + ('acumon is STILL IN HIGH-FREQUENCY MODE — manual intervention may be required.'
           if not enabled else 'Calibration cannot start.'),
        'calibration',
    )
    return False, last_msg
