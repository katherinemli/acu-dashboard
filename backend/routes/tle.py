"""
routes/tle.py - TLE file management (library, history, upload, activate).

Architecture:
    tle/
    ├── active.tle       ← symlink to library/{norad}.tle (C reads this)
    ├── library/         ← one file per NORAD ID: {norad}.tle
    └── history/         ← raw uploaded files with timestamps

Endpoints:
    GET    /api/tle/active
    GET    /api/tle/inventory
    GET    /api/tle/history
    GET    /api/tle/files
    POST   /api/tle/upload
    POST   /api/tle/upload-text
    POST   /api/tle/activate
    GET    /api/tle/match-status
    GET    /api/tle/download/<filename>
    GET    /api/tle/library/<norad_id>
    PUT    /api/tle/library/<norad_id>
    DELETE /api/tle/library/<norad_id>
    DELETE /api/tle/files/<filename>
"""

import os
import re
import shutil
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request, send_file
from shared import cfg, log_event, TLE_DIR, TLE_ACTIVE_LINK

bp = Blueprint('tle', __name__)

# ============================================
# TLE DIRECTORY STRUCTURE
# ============================================

TLE_LIBRARY_DIR = os.path.join(TLE_DIR, 'library')
TLE_HISTORY_DIR = os.path.join(TLE_DIR, 'history')
os.makedirs(TLE_LIBRARY_DIR, exist_ok=True)
os.makedirs(TLE_HISTORY_DIR, exist_ok=True)


# ============================================
# TLE HELPERS (used by satellites.py too)
# ============================================

def _tle_checksum(line):
    """Standard TLE mod-10 checksum of columns 1-68 ('-' counts as 1)."""
    total = 0
    for c in line[:68]:
        if c.isdigit():
            total += int(c)
        elif c == '-':
            total += 1
    return total % 10


def _parse_one_tle(name, line1, line2):
    if not line1.startswith('1 ') or not line2.startswith('2 '):
        return None, 'Lines must start with "1 " and "2 "'
    if len(line1) < 69 or len(line2) < 69:
        return None, f'TLE lines too short (line1={len(line1)}, line2={len(line2)}, need 69)'

    # Integrity: the mod-10 checksum the TLE format carries in column 69.
    for n, line in ((1, line1), (2, line2)):
        if line[68].isdigit() and int(line[68]) != _tle_checksum(line):
            return None, f'Line {n} checksum mismatch (got {line[68]}, expected {_tle_checksum(line)})'

    try:
        norad_id = line1[2:7].strip()
        if norad_id != line2[2:7].strip():
            return None, f'NORAD mismatch: line 1 ({norad_id}) vs line 2 ({line2[2:7].strip()})'
        intl_designator = line1[9:17].strip()
        epoch_year = int(line1[18:20])
        epoch_day = float(line1[20:32])
        full_year = 2000 + epoch_year if epoch_year < 57 else 1900 + epoch_year
        epoch_dt = datetime(full_year, 1, 1) + timedelta(days=epoch_day - 1)
        epoch_str = epoch_dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        inclination = float(line2[8:16].strip())
        raan = float(line2[17:25].strip())
        eccentricity = float('0.' + line2[26:33].strip())
        arg_perigee = float(line2[34:42].strip())
        mean_anomaly = float(line2[43:51].strip())
        mean_motion = float(line2[52:63].strip())
        rev_number = int(line2[63:68].strip())
    except (ValueError, IndexError) as e:
        return None, f'Failed to parse TLE fields: {e}'

    # Physically-impossible values (rejects numeric garbage, not odd-but-real orbits).
    if not 0.0 <= inclination <= 180.0:
        return None, f'Inclination {inclination} outside [0, 180]'
    if not (0.0 <= raan <= 360.0 and 0.0 <= arg_perigee <= 360.0 and 0.0 <= mean_anomaly <= 360.0):
        return None, 'Angle (RAAN / arg perigee / mean anomaly) outside [0, 360]'
    if not 0.0 < mean_motion < 20.0:
        return None, f'Mean motion {mean_motion} outside (0, 20) rev/day'

    raw = f'{name}\n{line1}\n{line2}'
    return {
        'name': name,
        'norad_id': norad_id,
        'intl_designator': intl_designator,
        'epoch': epoch_str,
        'epoch_iso': epoch_dt.isoformat() + 'Z',
        'inclination': inclination,
        'raan': raan,
        'eccentricity': eccentricity,
        'arg_perigee': arg_perigee,
        'mean_anomaly': mean_anomaly,
        'mean_motion': mean_motion,
        'rev_number': rev_number,
        'raw': raw
    }, None


def parse_tle_multi(text):
    """Parse one or more TLE blocks. Returns list of parsed dicts."""
    lines = [l.rstrip() for l in text.strip().splitlines() if l.strip()]
    results = []
    i = 0
    while i < len(lines):
        if (i + 2 < len(lines)
                and not lines[i].startswith('1 ')
                and not lines[i].startswith('2 ')
                and lines[i + 1].startswith('1 ')
                and lines[i + 2].startswith('2 ')):
            parsed, err = _parse_one_tle(lines[i].strip(), lines[i + 1], lines[i + 2])
            if parsed:
                results.append(parsed)
            i += 3
            continue
        if (i + 1 < len(lines)
                and lines[i].startswith('1 ')
                and lines[i + 1].startswith('2 ')):
            norad = lines[i][2:7].strip()
            parsed, err = _parse_one_tle(f'NORAD-{norad}', lines[i], lines[i + 1])
            if parsed:
                results.append(parsed)
            i += 2
            continue
        i += 1
    return results


def parse_tle(text):
    """Parse a single TLE. Returns (dict, err)."""
    results = parse_tle_multi(text)
    if results:
        return results[0], None
    return None, 'Invalid TLE format'


def _save_to_library(parsed):
    """Save parsed TLE to library/{norad_id}.tle."""
    filepath = os.path.join(TLE_LIBRARY_DIR, f'{parsed["norad_id"]}.tle')
    with open(filepath, 'w') as f:
        f.write(parsed['raw'])
    return filepath


def _set_active_tle_symlink(library_path):
    """Point active.tle symlink to a library file."""
    try:
        if os.path.islink(TLE_ACTIVE_LINK) or os.path.exists(TLE_ACTIVE_LINK):
            os.remove(TLE_ACTIVE_LINK)
        os.symlink(library_path, TLE_ACTIVE_LINK)
    except OSError:
        shutil.copy2(library_path, TLE_ACTIVE_LINK)


def _auto_activate_tle_for_satellite():
    """If active satellite has a TLE in library, point active.tle there."""
    active_sat_id = cfg.get_active_satellite_id()
    sat = cfg.get_satellite_by_id(active_sat_id) if active_sat_id else None
    if not sat:
        return False
    norad = str(sat.get('satNoradId', '')).strip()
    if not norad:
        return False
    lib_path = os.path.join(TLE_LIBRARY_DIR, f'{norad}.tle')
    if os.path.exists(lib_path):
        _set_active_tle_symlink(lib_path)
        return True
    return False


def _get_tle_age_days(parsed):
    """Calculate age of TLE in days from its epoch."""
    try:
        epoch_str = parsed['epoch_iso'].rstrip('Z')
        epoch_dt = datetime.fromisoformat(epoch_str).replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - epoch_dt
        return max(0, delta.days)
    except Exception:
        return None


def _diagnose_tle(text):
    """Best-effort specific reason when nothing parsed, for the upload error."""
    lines = [l.rstrip() for l in text.strip().splitlines() if l.strip()]
    for i in range(len(lines) - 1):
        if lines[i].startswith('1 ') and lines[i + 1].startswith('2 '):
            _, err = _parse_one_tle('probe', lines[i], lines[i + 1])
            if err:
                return f'Invalid TLE: {err}'
    return 'No valid TLE blocks found in file'


def _process_tle_upload(text, orig_filename=None, activate=True):
    """Process uploaded TLE text: save to history + library, auto-activate.
    activate=False stages to the library only (no active.tle change) — used by
    the smart-upload flow where activation is a separate, explicit step."""
    all_parsed = parse_tle_multi(text)
    if not all_parsed:
        raise ValueError(_diagnose_tle(text))

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    if orig_filename:
        safe_name = re.sub(r'[^a-zA-Z0-9_\-.]', '_', orig_filename).strip('_')
    else:
        first_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', all_parsed[0]['name']).strip('_') or 'tle'
        safe_name = f'{first_name}.tle'
    history_filename = f'{ts}_{safe_name}'
    if not history_filename.endswith('.tle'):
        history_filename += '.tle'
    history_path = os.path.join(TLE_HISTORY_DIR, history_filename)

    with open(history_path, 'w') as f:
        f.write(text)

    configured_norad_ids = set()
    for sat in cfg.get_satellites():
        nid = str(sat.get('satNoradId', '')).strip()
        if nid:
            configured_norad_ids.add(nid)

    updated = []
    new = []
    for parsed in all_parsed:
        norad = parsed['norad_id']
        existed = os.path.exists(os.path.join(TLE_LIBRARY_DIR, f'{norad}.tle'))
        _save_to_library(parsed)
        entry = {
            'name': parsed['name'],
            'norad_id': norad,
            'has_config': norad in configured_norad_ids,
            'age_days': _get_tle_age_days(parsed)
        }
        if existed:
            updated.append(entry)
        else:
            new.append(entry)

    activated = _auto_activate_tle_for_satellite() if activate else None

    return {
        'total': len(all_parsed),
        'updated': updated,
        'new': new,
        'errors': 0,
        'auto_activated': activated,
        'history_file': history_filename
    }, history_filename


def _migrate_legacy_tle_files():
    """One-time migration: move loose .tle files from TLE_DIR root into history/."""
    if not os.path.isdir(TLE_DIR):
        return
    for fn in os.listdir(TLE_DIR):
        if fn == 'active.tle':
            continue
        fp = os.path.join(TLE_DIR, fn)
        if not os.path.isfile(fp) or not fn.endswith('.tle'):
            continue
        dest = os.path.join(TLE_HISTORY_DIR, fn)
        if not os.path.exists(dest):
            try:
                shutil.move(fp, dest)
            except Exception:
                shutil.copy2(fp, dest)
                os.remove(fp)
        else:
            os.remove(fp)
        try:
            with open(dest, 'r') as f:
                text = f.read()
            for parsed in parse_tle_multi(text):
                _save_to_library(parsed)
        except Exception:
            pass


_migrate_legacy_tle_files()


# ============================================
# ENDPOINTS
# ============================================

@bp.route('/api/tle/active')
def get_active_tle():
    if not os.path.exists(TLE_ACTIVE_LINK):
        return jsonify(None)
    try:
        with open(TLE_ACTIVE_LINK, 'r') as f:
            text = f.read()
        parsed, err = parse_tle(text)
        if err:
            return jsonify(None)
        parsed['age_days'] = _get_tle_age_days(parsed)
        return jsonify(parsed)
    except Exception:
        return jsonify(None)


@bp.route('/api/tle/inventory')
def get_tle_inventory():
    if not os.path.isdir(TLE_LIBRARY_DIR):
        return jsonify([])

    sat_by_norad = {}
    active_sat_id = cfg.get_active_satellite_id()
    for sat in cfg.get_satellites():
        nid = str(sat.get('satNoradId', '')).strip()
        if nid:
            sat_by_norad[nid] = {
                'name': sat.get('satName', ''),
                'id': sat.get('satId', ''),
                'active': str(sat.get('satId', '')) == str(active_sat_id)
            }

    active_norad = None
    if os.path.exists(TLE_ACTIVE_LINK):
        try:
            active_real = os.path.realpath(TLE_ACTIVE_LINK)
            active_norad = os.path.splitext(os.path.basename(active_real))[0]
        except Exception:
            pass

    inventory = []
    for fn in sorted(os.listdir(TLE_LIBRARY_DIR)):
        if not fn.endswith('.tle'):
            continue
        fp = os.path.join(TLE_LIBRARY_DIR, fn)
        norad = os.path.splitext(fn)[0]
        try:
            with open(fp, 'r') as f:
                text = f.read()
            parsed, err = parse_tle(text)
            if not parsed:
                continue
        except Exception:
            continue

        age = _get_tle_age_days(parsed)
        sat_info = sat_by_norad.get(norad)
        inventory.append({
            'norad_id': norad,
            'name': parsed['name'],
            'epoch': parsed['epoch'],
            'epoch_iso': parsed['epoch_iso'],
            'age_days': age,
            'is_active': norad == active_norad,
            'has_config': sat_info is not None,
            'satellite_name': sat_info['name'] if sat_info else None,
            'is_active_satellite': sat_info['active'] if sat_info else False,
        })

    inventory.sort(key=lambda x: (
        not x['is_active_satellite'],
        not x['has_config'],
        x['name']
    ))
    return jsonify(inventory)


@bp.route('/api/tle/history')
def list_tle_history():
    if not os.path.isdir(TLE_HISTORY_DIR):
        return jsonify([])

    files = []
    for fn in sorted(os.listdir(TLE_HISTORY_DIR), reverse=True):
        if not fn.endswith('.tle') and not fn.endswith('.txt'):
            continue
        fp = os.path.join(TLE_HISTORY_DIR, fn)
        if not os.path.isfile(fp):
            continue
        sat_count = 0
        try:
            with open(fp, 'r') as f:
                text = f.read()
            sat_count = len(parse_tle_multi(text))
        except Exception:
            pass
        stat = os.stat(fp)
        files.append({
            'filename': fn,
            'uploaded_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'size': stat.st_size,
            'satellite_count': sat_count
        })
    return jsonify(files)


@bp.route('/api/tle/files')
def list_tle_files():
    """Backward compat — returns history files."""
    return list_tle_history()


@bp.route('/api/tle/upload', methods=['POST'])
def upload_tle_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    text = file.read().decode('utf-8', errors='replace')
    # Optional: stage to library without changing active.tle (smart-upload flow).
    activate = request.form.get('activate', 'true').lower() != 'false'
    try:
        summary, filename = _process_tle_upload(text, file.filename, activate=activate)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    n_new = len(summary['new'])
    n_updated = len(summary['updated'])
    log_event('info',
              f'TLE file uploaded: {summary["total"]} satellites '
              f'({n_new} new, {n_updated} updated)', 'tle')
    return jsonify({
        'status': 'ok',
        'message': f'{summary["total"]} satellites processed ({n_new} new, {n_updated} updated)',
        'summary': summary
    })


@bp.route('/api/tle/upload-text', methods=['POST'])
def upload_tle_text():
    data = request.json or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No TLE text provided'}), 400

    try:
        summary, filename = _process_tle_upload(text)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    n_new = len(summary['new'])
    n_updated = len(summary['updated'])
    log_event('info',
              f'TLE text pasted: {summary["total"]} satellites '
              f'({n_new} new, {n_updated} updated)', 'tle')
    return jsonify({
        'status': 'ok',
        'message': f'{summary["total"]} satellites processed ({n_new} new, {n_updated} updated)',
        'summary': summary
    })


@bp.route('/api/tle/activate', methods=['POST'])
def activate_tle():
    data = request.json or {}

    norad_id = data.get('norad_id', '').strip()
    if norad_id:
        lib_path = os.path.join(TLE_LIBRARY_DIR, f'{norad_id}.tle')
        if not os.path.exists(lib_path):
            return jsonify({'error': f'No TLE in library for NORAD {norad_id}'}), 404
        _set_active_tle_symlink(lib_path)
        log_event('info', f'TLE activated: NORAD {norad_id}', 'tle')
        return jsonify({'status': 'ok', 'message': f'TLE activated: NORAD {norad_id}'})

    filename = data.get('filename', '').strip()
    if not filename:
        return jsonify({'error': 'norad_id or filename required'}), 400

    filepath = os.path.join(TLE_HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        filepath = os.path.join(TLE_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    try:
        with open(filepath, 'r') as f:
            text = f.read()
        parsed_list = parse_tle_multi(text)
        if not parsed_list:
            return jsonify({'error': 'No valid TLE in file'}), 400
        for p in parsed_list:
            _save_to_library(p)
        if len(parsed_list) == 1:
            lib_path = os.path.join(TLE_LIBRARY_DIR, f'{parsed_list[0]["norad_id"]}.tle')
            _set_active_tle_symlink(lib_path)
        else:
            _auto_activate_tle_for_satellite()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    log_event('info', f'TLE activated from history: {filename}', 'tle')
    return jsonify({'status': 'ok', 'message': f'TLE activated: {filename}'})


@bp.route('/api/tle/match-status')
def get_tle_match_status():
    active_sat_id = cfg.get_active_satellite_id()
    sat = cfg.get_satellite_by_id(active_sat_id) if active_sat_id else None

    sat_norad = str(sat.get('satNoradId', '')).strip() if sat else ''
    sat_name = sat.get('satName', '') if sat else ''

    tle_norad = ''
    tle_name = ''
    tle_age = None
    if os.path.exists(TLE_ACTIVE_LINK):
        try:
            with open(TLE_ACTIVE_LINK, 'r') as f:
                text = f.read()
            parsed, err = parse_tle(text)
            if parsed:
                tle_norad = str(parsed.get('norad_id', '')).strip()
                tle_name = parsed.get('name', '')
                tle_age = _get_tle_age_days(parsed)
        except Exception:
            pass

    has_satellite = bool(sat_norad)
    has_tle = bool(tle_norad)
    match = has_satellite and has_tle and sat_norad == tle_norad
    library_available = os.path.exists(
        os.path.join(TLE_LIBRARY_DIR, f'{sat_norad}.tle')
    ) if sat_norad else False

    warning = None
    if not has_satellite and not has_tle:
        warning = 'No active satellite or TLE configured'
    elif not has_satellite:
        warning = 'No active satellite configured'
    elif not has_tle and library_available:
        _auto_activate_tle_for_satellite()
        match = True
    elif not has_tle:
        warning = f'No TLE available for satellite {sat_name} (NORAD {sat_norad})'
    elif not match:
        if library_available:
            _auto_activate_tle_for_satellite()
            match = True
        else:
            warning = (
                f'TLE NORAD ID ({tle_norad}, {tle_name}) does not match '
                f'active satellite {sat_name} (NORAD {sat_norad})'
            )

    return jsonify({
        'match': match,
        'warning': warning,
        'satellite': {'name': sat_name, 'norad_id': sat_norad} if has_satellite else None,
        'tle': {'name': tle_name, 'norad_id': tle_norad, 'age_days': tle_age} if has_tle else None,
        'library_available': library_available,
    })


@bp.route('/api/tle/download/<filename>')
def download_tle(filename):
    filepath = os.path.join(TLE_HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        filepath = os.path.join(TLE_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    return send_file(filepath, as_attachment=True)


@bp.route('/api/tle/library/<norad_id>', methods=['GET'])
def get_library_tle(norad_id):
    filepath = os.path.join(TLE_LIBRARY_DIR, f'{norad_id}.tle')
    if not os.path.exists(filepath):
        return jsonify({'error': 'Not found'}), 404
    try:
        with open(filepath, 'r') as f:
            text = f.read()
        parsed, err = parse_tle(text)
        if not parsed:
            return jsonify({'error': err}), 400
        parsed['age_days'] = _get_tle_age_days(parsed)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/api/tle/library/<norad_id>', methods=['PUT'])
def update_library_tle(norad_id):
    data = request.json or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'No TLE text provided'}), 400

    parsed_list = parse_tle_multi(text)
    if not parsed_list:
        return jsonify({'error': 'Invalid TLE format'}), 400

    parsed = parsed_list[0]
    if parsed['norad_id'] != str(norad_id):
        return jsonify({
            'error': f'NORAD ID mismatch: TLE has {parsed["norad_id"]}, expected {norad_id}'
        }), 400

    _save_to_library(parsed)
    _auto_activate_tle_for_satellite()
    log_event('info', f'TLE manually edited: {parsed["name"]} (NORAD {norad_id})', 'tle')
    return jsonify({'status': 'ok', 'parsed': parsed})


@bp.route('/api/tle/library/<norad_id>', methods=['DELETE'])
def delete_library_tle(norad_id):
    filepath = os.path.join(TLE_LIBRARY_DIR, f'{norad_id}.tle')
    if not os.path.exists(filepath):
        return jsonify({'error': 'Not found'}), 404

    if os.path.exists(TLE_ACTIVE_LINK):
        try:
            if os.path.realpath(filepath) == os.path.realpath(TLE_ACTIVE_LINK):
                return jsonify({'error': 'Cannot delete the active TLE'}), 400
        except Exception:
            pass

    os.remove(filepath)
    log_event('warning', f'TLE deleted from library: NORAD {norad_id}', 'tle')
    return jsonify({'status': 'ok', 'message': f'TLE NORAD {norad_id} deleted'})


@bp.route('/api/tle/files/<filename>', methods=['DELETE'])
def delete_tle_file(filename):
    if filename == 'active.tle':
        return jsonify({'error': 'Cannot delete active reference'}), 400

    filepath = os.path.join(TLE_HISTORY_DIR, filename)
    if not os.path.exists(filepath):
        filepath = os.path.join(TLE_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    os.remove(filepath)
    log_event('warning', f'TLE history file deleted: {filename}', 'tle')
    return jsonify({'status': 'ok', 'message': f'TLE {filename} deleted'})