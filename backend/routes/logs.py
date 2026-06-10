"""
routes/logs.py - ACU logs and system events.

Endpoints:
    GET  /api/logs
    GET  /api/logs/download
    POST /api/logs/purge
    GET  /api/events
    POST /api/events
"""

import os
import io
import csv
import glob
import zipfile
import subprocess
from datetime import datetime

from flask import Blueprint, jsonify, request, send_file
from shared import (
    get_telemetry_db, log_event,
    read_last_lines, parse_log_line,
    ACU_MSG_LOG, ACU_ERR_LOG,
)

bp = Blueprint('logs', __name__)


@bp.route('/api/logs')
def get_logs():
    limit = request.args.get('limit', 100, type=int)
    log_file = request.args.get('file', 'msg')
    filepath = ACU_ERR_LOG if log_file == 'err' else ACU_MSG_LOG
    lines = read_last_lines(filepath, limit)
    data = [parse_log_line(line) for line in lines]
    return jsonify([d for d in data if d])


def _events_csv():
    """Export the Eureka events table (SQLite, ours only) as CSV text."""
    conn = get_telemetry_db()
    c = conn.cursor()
    c.execute('SELECT timestamp, level, source, message '
              'FROM events ORDER BY timestamp')
    rows = c.fetchall()
    conn.close()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['timestamp', 'level', 'source', 'message'])
    for r in rows:
        w.writerow([r['timestamp'], r['level'], r['source'], r['message']])
    return buf.getvalue()


def _bundle_with_events(zip_path):
    """Build a new ZIP (owned by us) holding the gathered logs plus our events.
    gatherlogs.sh runs via sudo so its ZIP is root-owned — we can read it but
    not append, hence the copy. Best-effort: on any failure, return the
    original log ZIP so the download still works."""
    try:
        full_path = zip_path[:-4] + '-full.zip'
        with zipfile.ZipFile(zip_path, 'r') as src, \
             zipfile.ZipFile(full_path, 'w', zipfile.ZIP_DEFLATED) as dst:
            for name in src.namelist():
                dst.writestr(name, src.read(name))
            dst.writestr('eureka-events.csv', _events_csv())
        return full_path
    except Exception as e:
        log_event('error', f'Could not add events to ZIP: {e}', 'system')
        return zip_path


@bp.route('/api/logs/download')
def download_logs():
    gather_script = '/opt/acu/gatherlogs.sh'

    if not os.path.exists(gather_script):
        return jsonify({'error': 'gatherlogs.sh not found'}), 404

    try:
        zip_path = f'/tmp/tracelogs-acumon-{datetime.now().strftime("%Y-%m-%d-%H%M%S")}.zip'
        result = subprocess.run(
            ['sudo', gather_script, '-f', os.path.basename(zip_path)],
            capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            log_event('error', f'gatherlogs.sh failed: {result.stderr}', 'system')
            return jsonify({'error': 'Failed to generate logs'}), 500

        if not os.path.exists(zip_path):
            return jsonify({'error': 'ZIP file not generated'}), 500

        # Events live only in Eureka's SQLite telemetry DB — gatherlogs.sh (acu
        # side) doesn't know about them, so fold them into the same ZIP here.
        send_path = _bundle_with_events(zip_path)

        log_event('info', 'Logs downloaded as ZIP', 'system')
        return send_file(
            send_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=os.path.basename(zip_path)
        )
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout generating logs'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/logs/purge', methods=['POST'])
def purge_logs():
    errors = []
    purged = []

    for pattern in ['/var/log/acu/*.log', '/var/log/acu/*.dat',
                    '/var/log/acu/*.1', '/var/log/acu/*.gz']:
        for f in glob.glob(pattern):
            try:
                os.truncate(f, 0)
                purged.append(f)
            except Exception as e:
                errors.append(f'{f}: {e}')

    for pattern in ['/var/log/eureka/*.log', '/var/log/eureka/*.1', '/var/log/eureka/*.gz']:
        for f in glob.glob(pattern):
            try:
                os.truncate(f, 0)
                purged.append(f)
            except Exception as e:
                errors.append(f'{f}: {e}')

    # nginx logs are owned by www-data — truncate via sudo
    for pattern in ['/var/log/nginx/*.log', '/var/log/nginx/*.gz']:
        for f in glob.glob(pattern):
            try:
                result = subprocess.run(
                    ['sudo', 'truncate', '-s', '0', f],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    purged.append(f)
                else:
                    errors.append(f'{f}: {result.stderr.strip()}')
            except Exception as e:
                errors.append(f'{f}: {e}')

    try:
        result = subprocess.run(
            ['sudo', 'journalctl', '--vacuum-size=10M'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            purged.append('journalctl')
        else:
            errors.append(f'journalctl: {result.stderr}')
    except Exception as e:
        errors.append(f'journalctl: {e}')

    log_event('info', f'Logs purged: {len(purged)} items', 'system')

    return jsonify({
        'success': len(errors) == 0,
        'purged': len(purged),
        'errors': errors
    })


@bp.route('/api/events')
def get_events():
    level = request.args.get('level', 'all')
    limit = request.args.get('limit', 100, type=int)

    conn = get_telemetry_db()
    c = conn.cursor()

    if level == 'all':
        c.execute('SELECT * FROM events ORDER BY timestamp DESC LIMIT ?', (limit,))
    else:
        c.execute('SELECT * FROM events WHERE level = ? ORDER BY timestamp DESC LIMIT ?', (level, limit))

    events = [dict(row) for row in c.fetchall()]
    conn.close()

    return jsonify(events)


@bp.route('/api/events', methods=['POST'])
def add_event():
    data = request.json
    conn = get_telemetry_db()
    c = conn.cursor()
    c.execute('INSERT INTO events (level, message, source) VALUES (?, ?, ?)',
              (data.get('level', 'info'), data['message'], data.get('source', 'system')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})