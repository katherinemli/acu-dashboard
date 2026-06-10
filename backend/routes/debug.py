"""
routes/debug.py - Hidden CLI console (dev/test tool, URL-only at #/debug/cli).

Fires acumon CLI commands and returns cmd_output.txt — same round-trip as
acucli.sh's send_cmd_to_acumon (reset cmd_done, write cmd_input, SIGUSR1, poll
cmd_done, read cmd_output).

v1 is READ-ONLY: only config-show (cat 1) and stats (cat 2) commands are allowed.
Action/destructive commands (operations, reboot, set IP, calib) are rejected.
"""

import re
import time
import subprocess

from flask import Blueprint, jsonify, request

from shared import (
    ACU_CLI_CMD_INPUT,
    ACU_CLI_CMD_OUTPUT,
    ACU_CLI_CMD_DONE,
)

bp = Blueprint('debug', __name__)

# v1 whitelist — read-only only: "1 1".."1 10" (config show), "2 1/4/5/6/7" (stats).
_SAFE_CMD = re.compile(r'^(1 (10|[1-9])|2 [14567])$')


def _tee(path, content):
    """Write content to a /opt/acu/cmd_*.txt file via sudo tee (eureka lacks write perms)."""
    r = subprocess.run(['sudo', '/usr/bin/tee', path],
                       input=content, capture_output=True, text=True, timeout=5)
    return r.returncode == 0


def _read(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception:
        return ''


# ============================================
# Smart upload — content-based file detection (hidden demo, URL-only at
# #/debug/upload). Identifies an uploaded file as a TLE, config.ini, or
# satellites.ini by its CONTENT (not its name). v1 only DETECTS; the frontend
# applies the confirmed file via the existing /api/tle/upload and
# /api/config-mgmt/upload + load-upload endpoints.
# ============================================

# config.ini's section names (lowercased). satellites.ini uses numbered
# [Satellite1], [Satellite2]… sections instead, which is how we tell them apart.
_CONFIG_SECTIONS = {'system', 'network', 'esa', 'location',
                    'advanced', 'sensors', 'server', 'storage'}


def _detect_upload_type(text):
    """Identify an upload by content: 'tle' | 'config' | 'satellite' | 'unknown'."""
    # TLE first — reuse the real parser so malformed junk doesn't false-match.
    try:
        from routes.tle import parse_tle_multi
        if parse_tle_multi(text):
            return 'tle'
    except Exception:
        pass

    sections = [s.strip().lower()
                for s in re.findall(r'^\s*\[([^\]]+)\]\s*$', text, re.M)]
    if any(re.match(r'satellite\d+$', s) for s in sections):
        return 'satellite'
    if any(s in _CONFIG_SECTIONS for s in sections):
        return 'config'

    # Key-based fallback for headerless / partial files.
    if re.search(r'^\s*sat(NoradId|Name)\s*=', text, re.M | re.I):
        return 'satellite'
    if re.search(r'^\s*(acuIp|esaTxIp|curSatId|latDeg)\s*=', text, re.M | re.I):
        return 'config'
    return 'unknown'


def _summarize_upload(ftype, text):
    """Human-readable one-liner describing what was detected, for the preview."""
    if ftype == 'tle':
        try:
            from routes.tle import parse_tle_multi
            sats = parse_tle_multi(text)
            names = ', '.join(f'{p["name"]} ({p["norad_id"]})' for p in sats[:5])
            extra = '' if len(sats) <= 5 else f' +{len(sats) - 5} more'
            return f'{len(sats)} TLE block(s): {names}{extra}'
        except Exception:
            return 'TLE file'
    if ftype == 'satellite':
        names = re.findall(r'^\s*satName\s*=\s*(.+)$', text, re.M | re.I)
        n = len(re.findall(r'^\s*\[satellite\d+\]\s*$', text, re.M | re.I))
        listed = ', '.join(s.strip() for s in names[:6]) if names else ''
        return f'satellites.ini — {n or len(names)} satellite(s){": " + listed if listed else ""}'
    if ftype == 'config':
        sections = re.findall(r'^\s*\[([^\]]+)\]\s*$', text, re.M)
        return f'config.ini — {len(sections)} section(s): {", ".join(sections[:8])}'
    return 'Could not identify this file as a TLE, config.ini, or satellites.ini.'


@bp.route('/api/debug/upload-detect', methods=['POST'])
def debug_upload_detect():
    if 'file' not in request.files:
        return jsonify({'ok': False, 'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename:
        return jsonify({'ok': False, 'error': 'No file selected'}), 400
    try:
        text = f.read().decode('utf-8', errors='replace')
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Could not read file: {e}'}), 400

    ftype = _detect_upload_type(text)
    return jsonify({
        'ok': True,
        'filename': f.filename,
        'type': ftype,
        'summary': _summarize_upload(ftype, text),
    })


@bp.route('/api/debug/cli', methods=['POST'])
def debug_cli():
    cmd = (request.get_json(silent=True) or {}).get('cmd', '').strip()
    if not _SAFE_CMD.match(cmd):
        return jsonify({
            'ok': False,
            'error': 'Only read-only commands allowed: "1 1".."1 10" (config), "2 1/4/5/6/7" (stats).',
        }), 400

    # Round-trip (mirrors acucli.sh send_cmd_to_acumon)
    if not _tee(ACU_CLI_CMD_DONE, '0'):
        return jsonify({'ok': False, 'error': 'failed to reset cmd_done'}), 500
    if not _tee(ACU_CLI_CMD_INPUT, cmd + '\n'):
        return jsonify({'ok': False, 'error': 'failed to write cmd_input'}), 500

    pgrep = subprocess.run(['pgrep', '-x', 'acumon'], capture_output=True, text=True)
    pid = pgrep.stdout.split()
    if not pid:
        return jsonify({'ok': False, 'error': 'acumon not running'}), 500
    sig = subprocess.run(['sudo', '/usr/bin/kill', '-USR1', pid[0]],
                         capture_output=True, text=True, timeout=5)
    if sig.returncode != 0:
        return jsonify({'ok': False, 'error': sig.stderr.strip() or 'signal failed'}), 500

    # Poll cmd_done for completion (acumon writes '1' when done)
    for _ in range(50):  # ~5 s
        if _read(ACU_CLI_CMD_DONE).strip() == '1':
            break
        time.sleep(0.1)
    else:
        return jsonify({'ok': False, 'error': 'timeout waiting for acumon'}), 504

    return jsonify({'ok': True, 'cmd': cmd, 'output': _read(ACU_CLI_CMD_OUTPUT)})
