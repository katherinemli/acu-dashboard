"""
routes/config.py - System configuration and config file management.

Endpoints:
    GET  /api/config/sections
    GET  /api/config/<section>
    POST /api/config/<section>

    GET  /api/config-mgmt/files
    GET  /api/config-mgmt/files/backups
    GET  /api/config-mgmt/files/uploads
    POST /api/config-mgmt/load-backup
    POST /api/config-mgmt/upload
    POST /api/config-mgmt/load-upload
    POST /api/config-mgmt/factory-reset
    GET  /api/config-mgmt/download/<category>/<filename>
    DELETE /api/config-mgmt/files/backups/<timestamp>
    DELETE /api/config-mgmt/files/uploads/<filename>
"""

import os
import socket
import struct
import subprocess

from flask import Blueprint, jsonify, request, send_file
from shared import cfg, log_event
from metadata import SECTION_METADATA

bp = Blueprint('config', __name__)


# ============================================
# CONFIGURATION
# ============================================

@bp.route('/api/config/sections')
def get_sections():
    sections = []
    for key, meta in SECTION_METADATA.items():
        sections.append({'key': key, 'title': meta['title']})
    return jsonify(sections)


@bp.route('/api/config/<section>')
def get_config(section):
    if section not in SECTION_METADATA:
        return jsonify({'error': 'Invalid section'}), 404

    data = cfg.get_section(section)
    if data is None:
        return jsonify({'error': 'Invalid section'}), 404

    metadata = SECTION_METADATA[section]
    visible_fields = [f for f in metadata['fields'] if not f.get('hidden', False)]

    return jsonify({
        'title': metadata['title'],
        'fields': visible_fields,
        'data': data
    })


@bp.route('/api/config/<section>', methods=['POST'])
def save_config(section):
    if section not in SECTION_METADATA:
        return jsonify({'error': 'Invalid section'}), 404

    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    editable_keys = [
        f['key'] for f in SECTION_METADATA[section]['fields']
        if not f.get('readonly', False) and not f.get('hidden', False)
    ]
    filtered_data = {k: v for k, v in data.items() if k in editable_keys}

    if not filtered_data:
        return jsonify({'error': 'No valid fields provided'}), 400

    ok = cfg.save_section(section, filtered_data)
    if not ok:
        return jsonify({'error': 'Failed to save configuration'}), 500

    log_event('info', f'Configuration saved: {section}', 'config')
    return jsonify({'status': 'ok', 'message': f'{section} configuration saved'})


# ============================================
# CONFIG MANAGEMENT
# ============================================

@bp.route('/api/config-mgmt/files')
def list_config_files():
    backups = cfg.list_backups()
    uploads = cfg.list_uploads()
    return jsonify({
        'backups': backups,
        'uploads': uploads,
        'active': {
            'config': os.path.basename(cfg.config_path),
            'satellites': os.path.basename(cfg.satellites_path),
            'configDir': cfg.config_dir,
        }
    })


@bp.route('/api/config-mgmt/files/backups')
def list_backup_files():
    return jsonify(cfg.list_backups())


@bp.route('/api/config-mgmt/files/uploads')
def list_uploaded_files():
    return jsonify(cfg.list_uploads())


@bp.route('/api/config-mgmt/load-backup', methods=['POST'])
def load_backup():
    data = request.json or {}
    timestamp = data.get('timestamp', '').strip()
    if not timestamp:
        return jsonify({'error': 'Timestamp is required'}), 400

    ok, result = cfg.load_backup(timestamp)
    if not ok:
        return jsonify({'error': f'Load failed: {result}'}), 404

    log_event('info', f'Backup loaded: {result}', 'config')
    return jsonify({'status': 'ok', 'message': f'Backup loaded: {result}'})


@bp.route('/api/config-mgmt/upload', methods=['POST'])
def upload_config_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400

    ok, result = cfg.upload_file(file.filename, file)
    if not ok:
        return jsonify({'error': f'Upload failed: {result}'}), 400

    log_event('info', f'Config file uploaded: {result}', 'config')
    return jsonify({'status': 'ok', 'message': f'File uploaded: {result}', 'filename': result})


@bp.route('/api/config-mgmt/load-upload', methods=['POST'])
def load_upload():
    data = request.json or {}
    filename = data.get('filename', '').strip()
    if not filename:
        return jsonify({'error': 'Filename is required'}), 400

    file_type = data.get('type', '').strip() or None
    if file_type not in (None, 'config', 'satellite'):
        return jsonify({'error': 'Invalid type'}), 400

    ok, result = cfg.load_upload(filename, file_type)
    if not ok:
        return jsonify({'error': f'Load failed: {result}'}), 404

    log_event('info', f'Uploaded config loaded: {result}', 'config')
    return jsonify({'status': 'ok', 'message': f'Config loaded from upload: {result}'})


@bp.route('/api/config-mgmt/factory-reset', methods=['POST'])
def factory_reset():
    ok, msg = cfg.factory_reset()
    if not ok:
        return jsonify({'error': msg}), 400

    log_event('warning', 'Factory reset performed', 'config')
    return jsonify({'status': 'ok', 'message': msg})


@bp.route('/api/config-mgmt/download/<category>/<filename>')
def download_config_file(category, filename):
    filepath = cfg.get_file_path(category, filename)
    if not filepath:
        return jsonify({'error': 'File not found'}), 404

    return send_file(filepath, as_attachment=True)


@bp.route('/api/config-mgmt/files/backups/<timestamp>', methods=['DELETE'])
def delete_backup_file(timestamp):
    ok = cfg.delete_backup(timestamp)
    if not ok:
        return jsonify({'error': 'Backup not found'}), 404

    log_event('warning', f'Backup deleted: {timestamp}', 'config')
    return jsonify({'status': 'ok', 'message': f'Backup {timestamp} deleted'})


@bp.route('/api/config-mgmt/files/uploads/<filename>', methods=['DELETE'])
def delete_uploaded_file(filename):
    ok = cfg.delete_upload(filename)
    if not ok:
        return jsonify({'error': 'File not found'}), 404

    log_event('warning', f'Uploaded file deleted: {filename}', 'config')
    return jsonify({'status': 'ok', 'message': f'File {filename} deleted'})


# ============================================
# NETWORK CHECK
# ============================================

def _ip_to_int(ip):
    try:
        return struct.unpack('!I', socket.inet_aton(ip))[0]
    except Exception:
        return None

def _same_subnet(ip, mask, gateway):
    ip_int = _ip_to_int(ip)
    mask_int = _ip_to_int(mask)
    gw_int = _ip_to_int(gateway)
    if None in (ip_int, mask_int, gw_int):
        return None
    return (ip_int & mask_int) == (gw_int & mask_int)

@bp.route('/api/network/check', methods=['POST'])
def network_check():
    data = request.json or {}
    gateway = data.get('gateway', '').strip()
    ip = data.get('ip', '').strip()
    mask = data.get('mask', '').strip()

    warnings = []
    subnet_ok = None
    gateway_reachable = None

    if ip and mask and gateway:
        subnet_ok = _same_subnet(ip, mask, gateway)
        if subnet_ok is False:
            warnings.append(f'Gateway {gateway} is not in the {ip}/{mask} subnet')

    if gateway:
        try:
            ret = subprocess.run(
                ['ping', '-c', '2', '-W', '2', gateway],
                capture_output=True, timeout=6
            )
            gateway_reachable = (ret.returncode == 0)
            if not gateway_reachable:
                warnings.append(f'Gateway {gateway} did not respond to ping')
        except Exception:
            gateway_reachable = None

    return jsonify({
        'subnet_ok': subnet_ok,
        'gateway_reachable': gateway_reachable,
        'warnings': warnings
    })