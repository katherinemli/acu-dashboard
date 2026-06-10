"""
app.py - Eureka Dashboard entry point.

Registers all blueprints. Business logic lives in routes/.
Shared constants and parsers live in shared.py.
"""

import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS

from shared import cfg, BASE_DIR

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
CORS(app)

# ============================================
# BLUEPRINTS
# ============================================

from routes.status import bp as status_bp
from routes.telemetry import bp as telemetry_bp
from routes.logs import bp as logs_bp
from routes.config import bp as config_bp
from routes.satellites import bp as satellites_bp
from routes.tle import bp as tle_bp
from routes.system import bp as system_bp
from routes.actions import bp as actions_bp
from routes.calibration import bp as calibration_bp
from routes.docs import bp as docs_bp
from routes.debug import bp as debug_bp
from routes.readiness import bp as readiness_bp

app.register_blueprint(status_bp)
app.register_blueprint(telemetry_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(config_bp)
app.register_blueprint(satellites_bp)
app.register_blueprint(tle_bp)
app.register_blueprint(system_bp)
app.register_blueprint(actions_bp)
app.register_blueprint(calibration_bp)
app.register_blueprint(docs_bp)
app.register_blueprint(debug_bp)
app.register_blueprint(readiness_bp)

# ============================================
# CALIBRATION WIRING
# ============================================
# Hook the calibration session manager into the transitional runtime mode
# string and start the watchdog that auto-cancels
# stuck calibrations.

import calibration_session
from routes.runtime_state import set_runtime_mode

calibration_session.set_status_callback(set_runtime_mode)
calibration_session.start_watchdog()

# ============================================
# FRONTEND
# ============================================

@app.route('/')
def serve_frontend():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    try:
        return app.send_static_file(path)
    except Exception:
        return app.send_static_file('index.html')

# ============================================
# MAP TILES (sqlite MBTiles)
# ============================================

import sqlite3
from flask import Response

MBTILES_PATH = os.path.join(BASE_DIR, 'map.mbtiles')
_tile_conn = None

def get_tile_conn():
    global _tile_conn
    if _tile_conn is None:
        _tile_conn = sqlite3.connect(MBTILES_PATH, check_same_thread=False)
    return _tile_conn

@app.route('/api/tiles/<int:z>/<int:x>/<int:y>.png')
def serve_tile(z, x, y):
    try:
        conn = get_tile_conn()
        cursor = conn.execute(
            'SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',
            (z, x, (2**z - 1) - y)
        )
        row = cursor.fetchone()
        if row:
            return Response(row[0], mimetype='image/png',
                          headers={'Cache-Control': 'public, max-age=86400'})
    except Exception as e:
        app.logger.error(f'Tile error {z}/{x}/{y}: {e}')
    return '', 404

# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    port = cfg.get_port()
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    app.run(host=host, port=port, debug=False)
