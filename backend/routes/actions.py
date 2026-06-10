"""
routes/actions.py - User-initiated actions: reboot, upgrade.

Calibration endpoints have moved to routes/calibration.py.

Endpoints:
    POST /api/actions/reboot
    POST /api/actions/upgrade
    GET  /api/actions/upgrade/status

    GET  /api/acu/sensor-health
"""

import os
import re
import shutil
import subprocess

from flask import Blueprint, jsonify, request
from shared import (
    log_event, get_telemetry_db,
    ACU_MSG_LOG, ACU_SENSORS_DAT, ACU_CLI_CMD_INPUT, read_last_lines,
)

bp = Blueprint('actions', __name__)


def _write_cmd(content):
    """Write to cmd_input.txt via sudo tee (eureka user lacks direct write perms). Returns (ok, error_str)."""
    result = subprocess.run(
        ['sudo', '/usr/bin/tee', ACU_CLI_CMD_INPUT],
        input=content,
        capture_output=True, text=True, timeout=5
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or 'tee failed'
    return True, None


def _signal_acumon():
    """Send SIGUSR1 to acumon. Returns (ok, error_str)."""
    pgrep = subprocess.run(['pgrep', '-x', 'acumon'], capture_output=True, text=True)
    pid = pgrep.stdout.strip()
    if not pid:
        return False, 'acumon not running'
    result = subprocess.run(
        ['sudo', '/usr/bin/kill', '-USR1', pid.split()[0]],
        capture_output=True, text=True, timeout=5
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or 'kill failed'
    return True, None


# ============================================
# REBOOT & UPGRADE
# ============================================

@bp.route('/api/actions/stop-pointing', methods=['POST'])
def stop_pointing():
    ok, err = _write_cmd('4 1\n')
    if not ok:
        return jsonify({'status': 'error', 'error': f'Failed to write command: {err}'}), 500

    ok, err = _signal_acumon()
    if not ok:
        return jsonify({'status': 'error', 'error': err}), 500

    log_event('info', 'Operator requested stop pointing', 'operator')
    return jsonify({'status': 'ok', 'message': 'Stop command sent'})


@bp.route('/api/actions/manual-mode', methods=['POST'])
def manual_mode():
    ok, err = _write_cmd('4 2\n')
    if not ok:
        return jsonify({'status': 'error', 'error': f'Failed to write command: {err}'}), 500

    ok, err = _signal_acumon()
    if not ok:
        return jsonify({'status': 'error', 'error': err}), 500

    log_event('info', 'Operator entered manual pointing', 'operator')
    return jsonify({'status': 'ok', 'message': 'Manual pointing command sent'})


@bp.route('/api/actions/manual-exit', methods=['POST'])
def manual_exit():
    ok, err = _write_cmd('4 3\n')
    if not ok:
        return jsonify({'status': 'error', 'error': f'Failed to write command: {err}'}), 500

    ok, err = _signal_acumon()
    if not ok:
        return jsonify({'status': 'error', 'error': err}), 500

    log_event('info', 'Operator exited manual pointing', 'operator')
    return jsonify({'status': 'ok', 'message': 'Manual exit command sent'})


@bp.route('/api/actions/manual-goto', methods=['POST'])
def manual_goto():
    data = request.get_json(silent=True) or {}
    az = data.get('az', 0.0)
    el = data.get('el', 0.0)

    az_tenths = round(float(az) * 10)
    el_tenths = round(float(el) * 10)

    ok, err = _write_cmd(f'4 5 {az_tenths} {el_tenths}\n')
    if not ok:
        return jsonify({'status': 'error', 'error': f'Failed to write command: {err}'}), 500

    ok, err = _signal_acumon()
    if not ok:
        return jsonify({'status': 'error', 'error': err}), 500

    return jsonify({'status': 'ok'})


@bp.route('/api/actions/manual-nudge', methods=['POST'])
def manual_nudge():
    data = request.get_json(silent=True) or {}
    daz = data.get('az', 0.0)
    del_ = data.get('el', 0.0)

    az_tenths = round(float(daz) * 10)
    el_tenths = round(float(del_) * 10)

    ok, err = _write_cmd(f'4 4 {az_tenths} {el_tenths}\n')
    if not ok:
        return jsonify({'status': 'error', 'error': f'Failed to write command: {err}'}), 500

    ok, err = _signal_acumon()
    if not ok:
        return jsonify({'status': 'error', 'error': err}), 500

    return jsonify({'status': 'ok'})


@bp.route('/api/actions/resume-pointing', methods=['POST'])
def resume_pointing():
    ok, err = _write_cmd('4 7\n')
    if not ok:
        return jsonify({'status': 'error', 'error': f'Failed to write command: {err}'}), 500

    ok, err = _signal_acumon()
    if not ok:
        return jsonify({'status': 'error', 'error': err}), 500

    log_event('info', 'Operator requested resume pointing', 'operator')
    return jsonify({'status': 'ok', 'message': 'Resume command sent'})


@bp.route('/api/actions/reboot', methods=['POST'])
def reboot():
    reboot_type = request.json.get('type', 'soft')

    conn = get_telemetry_db()
    c = conn.cursor()
    c.execute('INSERT INTO events (level, message, source) VALUES (?, ?, ?)',
              ('warning', f'User ADMIN requested a system {reboot_type} reboot from the web interface', 'system'))
    c.execute('INSERT INTO logs (level, message) VALUES (?, ?)',
              ('INF', f'User ADMIN requested a system {reboot_type} reboot from the web interface'))
    conn.commit()
    conn.close()

    try:
        if reboot_type == 'hard':
            subprocess.Popen(
                ['sudo', '/usr/sbin/shutdown', '-r', '+0'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return jsonify({'status': 'ok', 'message': 'Hard reboot initiated'})
        else:
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', 'acumon'],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                log_event('error', f'Soft reboot failed: {result.stderr.strip()}', 'system')
                return jsonify({'status': 'error', 'error': result.stderr.strip()}), 500
            return jsonify({'status': 'ok', 'message': 'Soft reboot initiated (acumon restarted)'})
    except Exception as e:
        log_event('error', f'Reboot failed: {str(e)}', 'system')
        return jsonify({'status': 'error', 'error': str(e)}), 500


@bp.route('/api/actions/upgrade', methods=['POST'])
def upgrade():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f = request.files['file']
    if not f.filename.endswith('.deb'):
        return jsonify({'error': 'Only .deb files are accepted'}), 400

    deb_path = f'/tmp/{f.filename}'
    f.save(deb_path)

    try:
        if os.path.exists(ACU_MSG_LOG):
            shutil.copy2(ACU_MSG_LOG, '/var/log/eureka/acu_msg.log.bak')
    except Exception as e:
        log_event('warning', f'Log backup failed: {e}', 'system')

    try:
        with open('/tmp/eureka-upgrade.deb-path', 'w') as fp:
            fp.write(deb_path)
        open('/tmp/eureka-upgrade.trigger', 'w').close()
    except Exception as e:
        return jsonify({'error': f'Failed to trigger upgrade: {e}'}), 500

    log_event('info', f'Firmware upgrade initiated: {f.filename}', 'system')
    return jsonify({'status': 'ok', 'message': 'Upgrade started'})


@bp.route('/api/actions/upgrade/status')
def upgrade_status():
    return jsonify({'state': 'idle', 'message': 'Service running', 'error': None})


# ============================================
# SENSOR HEALTH (used by calibration UI gate)
# ============================================
#
# acumon writes one SYNC line per iteration containing all 3 sensors atomically:
#     May 04 14:07:48 SYNC <ts_us>|ax,ay,az|gx,gy,gz|mx,my,mz
#
# Finding the most recent SYNC line tells us about all 3 sensors at once.

_SENSOR_STALE_SECS = 30
_SENSOR_TIMESTAMP_RE = re.compile(r'^(\d{4} \w+ \d+ \d+:\d+:\d+)')


def _parse_sensor_timestamp(line):
    from datetime import datetime
    m = _SENSOR_TIMESTAMP_RE.match(line)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), '%Y %b %d %H:%M:%S')
    except ValueError:
        return None


@bp.route('/api/acu/sensor-health')
def get_sensor_health():
    from datetime import datetime
    lines = read_last_lines(ACU_SENSORS_DAT, 20)
    now = datetime.now()

    last_sync_ts = None
    for line in reversed(lines):
        if ' SYNC ' in line:
            last_sync_ts = _parse_sensor_timestamp(line)
            if last_sync_ts is not None:
                break

    if last_sync_ts is None:
        sensor_status = {'ok': False, 'age_s': None}
    else:
        age = (now - last_sync_ts).total_seconds()
        sensor_status = {'ok': age <= _SENSOR_STALE_SECS, 'age_s': round(age, 1)}

    # All 3 sensors share the same SYNC line, so all 3 get the same status.
    result = {
        'gyro': sensor_status,
        'accel': sensor_status,
        'compass': sensor_status,
    }

    return jsonify({'sensors': result, 'all_ok': sensor_status['ok']})

@bp.route('/api/actions/tx-mute', methods=['POST'])
def toggle_tx_mute():
    ok, err = _write_cmd('4 6\n')
    if not ok:
        return jsonify({'status': 'error', 'error': f'Failed to write command: {err}'}), 500

    ok, err = _signal_acumon()
    if not ok:
        return jsonify({'status': 'error', 'error': err}), 500

    log_event('info', 'Operator toggled permanent TX mute', 'operator')
    return jsonify({'status': 'ok', 'message': 'TX mute toggle sent'})