import os
from flask import Blueprint, jsonify, send_file, abort

bp = Blueprint('docs', __name__)

def _docs_dir():
    candidates = [
        '/opt/eureka/docs',
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docs'),
        os.path.expanduser('~/eureka/manual-gen'),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


@bp.route('/api/docs/content')
def docs_content():
    docs_dir = _docs_dir()
    if not docs_dir:
        return jsonify({'error': 'Documentation not available'}), 404
    manual_path = os.path.join(docs_dir, 'manual.md')
    if not os.path.exists(manual_path):
        return jsonify({'error': 'manual.md not found'}), 404
    with open(manual_path, 'r') as f:
        content = f.read()
    return jsonify({'content': content})


@bp.route('/api/docs/screenshots/<filename>')
def docs_screenshot(filename):
    filename = os.path.basename(filename)
    docs_dir = _docs_dir()
    if not docs_dir:
        abort(404)
    filepath = os.path.join(docs_dir, 'screenshots', filename)
    if not os.path.exists(filepath):
        abort(404)
    return send_file(filepath)
