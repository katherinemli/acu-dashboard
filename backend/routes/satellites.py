"""
routes/satellites.py - Satellite configuration management.

Endpoints:
    GET    /api/satellites
    GET    /api/satellites/fields
    GET    /api/satellites/active
    GET    /api/satellites/<id>
    POST   /api/satellites
    PUT    /api/satellites/<id>
    DELETE /api/satellites/<id>
    POST   /api/satellites/<id>/activate
"""

import os

from flask import Blueprint, jsonify, request
from shared import cfg, log_event
from metadata import SATELLITE_FIELDS
from routes.tle import (
    TLE_LIBRARY_DIR,
    parse_tle, _get_tle_age_days,
    _set_active_tle_symlink, _auto_activate_tle_for_satellite,
)

bp = Blueprint('satellites', __name__)


@bp.route('/api/satellites')
def get_satellites():
    satellites = cfg.get_satellites()
    active_id = cfg.get_active_satellite_id()

    result = []
    for sat in satellites:
        sat_data = {k: v for k, v in sat.items() if k != '_section'}
        sat_data['id'] = sat.get('satId', '')
        sat_data['active'] = 1 if str(sat.get('satId', '')) == str(active_id) else 0

        norad = str(sat.get('satNoradId', '')).strip()
        tle_status = 'missing'
        tle_age_days = None
        if norad:
            lib_path = os.path.join(TLE_LIBRARY_DIR, f'{norad}.tle')
            if os.path.exists(lib_path):
                try:
                    with open(lib_path, 'r') as f:
                        text = f.read()
                    parsed, _ = parse_tle(text)
                    if parsed:
                        tle_age_days = _get_tle_age_days(parsed)
                        tle_status = 'ready' if (tle_age_days is not None and tle_age_days <= 14) else 'stale'
                except Exception:
                    pass

        sat_data['tle_status'] = tle_status
        sat_data['tle_age_days'] = tle_age_days
        result.append(sat_data)

    result.sort(key=lambda x: (-x['active'], x.get('satName', '')))
    return jsonify(result)


@bp.route('/api/satellites/fields')
def get_satellite_fields():
    return jsonify({
        'title': 'Satellite Configuration',
        'fields': SATELLITE_FIELDS
    })


@bp.route('/api/satellites/active')
def get_active_satellite():
    active_id = cfg.get_active_satellite_id()
    sat = cfg.get_satellite_by_id(active_id)
    if sat:
        sat_data = {k: v for k, v in sat.items() if k != '_section'}
        sat_data['id'] = sat.get('satId', '')
        sat_data['active'] = 1
        return jsonify(sat_data)
    return jsonify({})


@bp.route('/api/satellites/<int:sat_id>')
def get_satellite(sat_id):
    sat = cfg.get_satellite_by_id(sat_id)
    if not sat:
        return jsonify({'error': 'Satellite not found'}), 404
    sat_data = {k: v for k, v in sat.items() if k != '_section'}
    sat_data['id'] = sat.get('satId', '')
    active_id = cfg.get_active_satellite_id()
    sat_data['active'] = 1 if str(sat_id) == str(active_id) else 0
    return jsonify(sat_data)


@bp.route('/api/satellites', methods=['POST'])
def create_satellite():
    data = request.json
    if not data or not data.get('satName'):
        return jsonify({'error': 'satName is required'}), 400

    valid_keys = [f['key'] for f in SATELLITE_FIELDS]
    filtered_data = {k: v for k, v in data.items() if k in valid_keys}

    new_id = cfg.create_satellite(filtered_data)
    log_event('info', f'Satellite created: {data.get("satName")}', 'satellite')
    return jsonify({'status': 'ok', 'id': new_id, 'message': 'Satellite created'})


@bp.route('/api/satellites/<int:sat_id>', methods=['PUT'])
def update_satellite(sat_id):
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    valid_keys = [f['key'] for f in SATELLITE_FIELDS]
    filtered_data = {k: v for k, v in data.items() if k in valid_keys}

    if not filtered_data:
        return jsonify({'error': 'No valid fields provided'}), 400

    ok = cfg.update_satellite(sat_id, filtered_data)
    if not ok:
        return jsonify({'error': 'Satellite not found'}), 404

    log_event('info', f'Satellite updated: ID {sat_id}', 'satellite')
    return jsonify({'status': 'ok', 'message': 'Satellite updated'})


@bp.route('/api/satellites/<int:sat_id>', methods=['DELETE'])
def delete_satellite(sat_id):
    ok, msg = cfg.delete_satellite(sat_id)
    if not ok:
        return jsonify({'error': msg}), 400

    log_event('warning', f'Satellite deleted: {msg}', 'satellite')
    return jsonify({'status': 'ok', 'message': 'Satellite deleted'})


@bp.route('/api/satellites/<int:sat_id>/activate', methods=['POST'])
def activate_satellite(sat_id):
    sat = cfg.get_satellite_by_id(sat_id)
    if not sat:
        return jsonify({'error': 'Satellite not found'}), 404

    sat_name = sat.get('satName', f'ID {sat_id}')
    cfg.set_active_satellite_id(sat_id)

    norad = str(sat.get('satNoradId', '')).strip()
    tle_linked = False
    tle_warning = None
    if norad:
        lib_path = os.path.join(TLE_LIBRARY_DIR, f'{norad}.tle')
        if os.path.exists(lib_path):
            _set_active_tle_symlink(lib_path)
            tle_linked = True
        else:
            tle_warning = f'No TLE available for NORAD {norad}. Upload one in TLE Management.'

    log_event('info',
              f'Satellite activated: {sat_name} (TLE {"linked" if tle_linked else "missing"})',
              'satellite')
    return jsonify({
        'status': 'ok',
        'message': f'Satellite {sat_name} activated',
        'tle_linked': tle_linked,
        'tle_warning': tle_warning
    })