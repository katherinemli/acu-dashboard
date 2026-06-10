"""
routes/system.py - System info, stats, history, and network.

Endpoints:
    GET  /api/system/device-info
    GET  /api/system/time
    GET  /api/system/version
    POST /api/system/set-time
    GET  /api/stats/sensors
    GET  /api/stats/antenna
    GET  /api/history/<table>
    GET  /api/network/eth0/stats
"""

import os
import shutil
import subprocess
import time
from datetime import datetime

from flask import Blueprint, jsonify, request
from shared import cfg, get_telemetry_db

bp = Blueprint('system', __name__)


@bp.route('/api/system/time')
def get_system_time():
    now = datetime.now()
    return jsonify({
        'iso': now.strftime('%Y-%m-%dT%H:%M:%S'),
        'unix_ms': int(now.timestamp() * 1000),
    })


@bp.route('/api/system/device-info')
def get_device_info():
    info = {}

    try:
        info['name'] = cfg.get('system', 'acuName', fallback='ACU')
    except Exception:
        info['name'] = 'ACU'

    try:
        with open('/proc/uptime') as f:
            secs = int(float(f.read().split()[0]))
            days, rem = divmod(secs, 86400)
            hours, rem = divmod(rem, 3600)
            mins, s = divmod(rem, 60)
            info['uptime'] = f"{days} d  {hours}:{mins:02d}:{s:02d}"
    except Exception:
        info['uptime'] = '-'

    info['current_time'] = datetime.now().strftime('%a %b %d %H:%M:%S %Z %Y')

    try:
        res = subprocess.run(['dpkg', '-l', 'eureka'], capture_output=True, text=True, timeout=5)
        for line in res.stdout.splitlines():
            if line.startswith('ii') and 'eureka' in line:
                info['version'] = line.split()[2]
                break
        else:
            info['version'] = 'unknown'
    except Exception:
        info['version'] = 'unknown'

    try:
        with open('/proc/meminfo') as f:
            mem = {}
            for line in f:
                parts = line.split()
                mem[parts[0].rstrip(':')] = int(parts[1])
            total = mem.get('MemTotal', 1)
            avail = mem.get('MemAvailable', 0)
            info['memory_pct'] = round((1 - avail / total) * 100)
    except Exception:
        info['memory_pct'] = None

    try:
        def read_cpu_stat():
            with open('/proc/stat') as f:
                parts = f.readline().split()
                return [int(x) for x in parts[1:9]]

        s1 = read_cpu_stat()
        time.sleep(0.5)
        s2 = read_cpu_stat()
        delta = [b - a for a, b in zip(s1, s2)]
        total = sum(delta)
        idle = delta[3] + delta[4]
        info['cpu_pct'] = round((1 - idle / total) * 100, 1) if total > 0 else 0
    except Exception:
        info['cpu_pct'] = None

    try:
        usage = shutil.disk_usage('/')
        info['disk_pct'] = round(usage.used / usage.total * 100)
    except Exception:
        info['disk_pct'] = None

    # --- log2ram ---
    try:
        df = subprocess.run(['df', '/var/log'], capture_output=True, text=True, timeout=3)
        parts = df.stdout.strip().splitlines()[-1].split()
        info['log2ram_mounted'] = parts[0] == 'log2ram'
        info['log2ram_pct'] = int(parts[4].rstrip('%'))
    except Exception:
        info['log2ram_mounted'] = False
        info['log2ram_pct'] = None

    try:
        svc = subprocess.run(['systemctl', 'is-active', 'log2ram'],
                             capture_output=True, text=True, timeout=3)
        info['log2ram_service'] = svc.stdout.strip()
    except Exception:
        info['log2ram_service'] = 'unknown'

    pct = info.get('log2ram_pct') or 0
    info['log2ram_ok'] = (
        info['log2ram_mounted'] and
        info['log2ram_service'] == 'active' and
        pct < 95
    )

    # --- logrotate ---
    try:
        mtime = os.stat('/var/lib/logrotate/status').st_mtime
        age_h = int((time.time() - mtime) / 3600)
        info['logrotate_age_h'] = age_h
    except FileNotFoundError:
        info['logrotate_age_h'] = None
    except Exception:
        info['logrotate_age_h'] = None

    info['logrotate_cron'] = os.path.exists('/etc/cron.d/acu-logrotate')

    large_files = []
    for log_dir in ('/var/log/acu', '/var/log/eureka', '/var/log/nginx'):
        try:
            for fn in os.listdir(log_dir):
                fp = os.path.join(log_dir, fn)
                if os.path.isfile(fp):
                    mb = os.path.getsize(fp) // (1024 * 1024)
                    if mb >= 100:
                        large_files.append({'name': fn, 'mb': mb})
        except Exception:
            pass
    info['logrotate_large'] = large_files

    age_h = info['logrotate_age_h']
    info['logrotate_ok'] = (
        age_h is not None and
        age_h < 25 and
        info['logrotate_cron'] and
        len(large_files) == 0
    )

    return jsonify(info)


@bp.route('/api/system/set-time', methods=['POST'])
def set_system_time():
    from flask import request as req
    data = req.get_json(force=True) or {}
    dt_str = data.get('datetime', '').strip()

    try:
        datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        return jsonify({'error': 'Invalid datetime format. Expected YYYY-MM-DDTHH:MM:SS'}), 400

    dt_for_cmd = dt_str.replace('T', ' ')
    try:
        # Ignore failure — NTP may already be disabled (non-fatal)
        subprocess.run(['sudo', '/usr/bin/timedatectl', 'set-ntp', '0'],
                       timeout=5)
        subprocess.run(['sudo', '/usr/bin/timedatectl', 'set-time', dt_for_cmd],
                       check=True, timeout=5)
        return jsonify({'ok': True, 'time_set': dt_for_cmd})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f'timedatectl failed: {e}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/system/version')
def get_version():
    try:
        result = subprocess.run(['dpkg', '-l', 'eureka'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.startswith('ii') and 'eureka' in line:
                parts = line.split()
                version = parts[2] if len(parts) > 2 else 'unknown'
                return jsonify({'version': version, 'build': '', 'date': ''})
    except Exception:
        pass
    return jsonify({'version': 'unknown', 'build': '', 'date': ''})


@bp.route('/api/stats/sensors')
def get_stats_sensors():
    minutes = request.args.get('minutes', 60, type=int)
    conn = get_telemetry_db()
    c = conn.cursor()
    c.execute(f'''
        SELECT
            strftime('%Y-%m-%d %H:%M:00', timestamp) as time,
            ROUND(AVG(temperature), 2) as temperature,
            ROUND(AVG(pressure), 2) as pressure
        FROM sensors
        WHERE timestamp > datetime('now', '-{minutes} minutes')
        GROUP BY strftime('%Y-%m-%d %H:%M', timestamp)
        ORDER BY time ASC
    ''')
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(data)


@bp.route('/api/stats/antenna')
def get_stats_antenna():
    minutes = request.args.get('minutes', 60, type=int)
    conn = get_telemetry_db()
    c = conn.cursor()
    c.execute(f'''
        SELECT
            strftime('%Y-%m-%d %H:%M:00', timestamp) as time,
            ROUND(AVG(azimuth), 2) as azimuth,
            ROUND(AVG(elevation), 2) as elevation
        FROM antenna
        WHERE timestamp > datetime('now', '-{minutes} minutes')
        GROUP BY strftime('%Y-%m-%d %H:%M', timestamp)
        ORDER BY time ASC
    ''')
    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(data)


@bp.route('/api/history/<table>')
def get_history(table):
    valid_tables = ['antenna', 'satellite', 'sensors', 'pointing']
    if table not in valid_tables:
        return jsonify({'error': 'Invalid table'}), 404

    hours = request.args.get('hours', 24, type=int)
    field = request.args.get('field', None)

    conn = get_telemetry_db()
    c = conn.cursor()

    if field:
        c.execute(f'''SELECT timestamp, {field} as value FROM {table}
                      WHERE timestamp > datetime('now', '-{hours} hours')
                      ORDER BY timestamp ASC''')
    else:
        c.execute(f'''SELECT * FROM {table}
                      WHERE timestamp > datetime('now', '-{hours} hours')
                      ORDER BY timestamp ASC''')

    data = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(data)


@bp.route('/api/network/eth0/stats')
def get_eth0_stats():
    stats_dir = '/sys/class/net/eth0/statistics'
    fields = [
        'rx_packets', 'rx_bytes', 'rx_errors', 'rx_dropped', 'rx_over_errors',
        'tx_packets', 'tx_bytes', 'tx_errors', 'tx_dropped', 'tx_over_errors',
        'collisions'
    ]
    stats = {}
    for field in fields:
        try:
            with open(os.path.join(stats_dir, field)) as f:
                stats[field] = int(f.read().strip())
        except Exception:
            stats[field] = None
    return jsonify(stats)