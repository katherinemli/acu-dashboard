"""
config_manager.py - INI-based configuration management for Eureka Dashboard

Source of truth: config.ini + satellites.ini
Provides: factory reset, auto-backup, file manager

Directory layout:
    {configDir}/
    ├── config.ini          ← active config (source of truth)
    ├── satellites.ini      ← active satellites (source of truth)
    ├── factory/            ← factory defaults (installed by deb)
    │   ├── config.ini
    │   └── satellites.ini
    ├── backup/             ← auto-backups (timestamped, before each change)
    │   ├── 20260206_143022_config.ini
    │   └── 20260206_143022_satellites.ini
    └── upload/             ← uploaded config files
"""

import configparser
import os
import shutil
import glob
import re
from datetime import datetime


class ConfigManager:
    """Manages config.ini + satellites.ini with save/load/backup"""

    # Map API section names → config.ini section names
    SECTION_MAP = {
        'system': 'System',
        'network': 'Network',
        'sensors': 'Sensors',
        'esa': 'Esa',
        'location': 'Location',
        'advanced': 'Advanced',
    }

    # Keys that have underscore prefix in the INI (hidden/internal)
    PREFIXED_KEYS = {'gyroRange', 'accRange'}

    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.config_path = os.path.join(config_dir, 'config.ini')
        self.satellites_path = os.path.join(config_dir, 'satellites.ini')
        self.backup_dir = os.path.join(config_dir, 'backup')
        self.uploads_dir = os.path.join(config_dir, 'upload')
        self.factory_dir = os.path.join(config_dir, 'factory')

        # Ensure directories exist
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.factory_dir, exist_ok=True)

    # ========================================
    # INI READ/WRITE HELPERS
    # ========================================

    def _read_ini(self, filepath):
        """Read an INI file preserving key casing"""
        config = configparser.ConfigParser()
        config.optionxform = str  # preserve case
        if os.path.exists(filepath):
            config.read(filepath)
        return config

    def _write_ini(self, config, filepath):
        """Write config object to INI file"""
        with open(filepath, 'w') as f:
            config.write(f, space_around_delimiters=False)

    def _ini_key(self, key):
        """Convert API key to INI key (add _ prefix for hidden keys)"""
        if key in self.PREFIXED_KEYS:
            return f'_{key}'
        return key

    def _api_key(self, ini_key):
        """Convert INI key to API key (strip _ prefix)"""
        if ini_key.startswith('_'):
            return ini_key[1:]
        if ini_key.startswith('*'):
            return ini_key[1:]
        return ini_key

    # ========================================
    # CONFIG SECTIONS (config.ini)
    # ========================================

    def get_section(self, section):
        """Read a config section, returns dict of key:value"""
        ini_section = self.SECTION_MAP.get(section)
        if not ini_section:
            return None

        config = self._read_ini(self.config_path)

        if not config.has_section(ini_section):
            return {}

        data = {}
        for ini_key, value in config.items(ini_section):
            api_key = self._api_key(ini_key)
            data[api_key] = value
        return data

    def save_section(self, section, data):
        """Update a config section with new values"""
        ini_section = self.SECTION_MAP.get(section)
        if not ini_section:
            return False

        # Auto-backup before change
        self.auto_backup()

        config = self._read_ini(self.config_path)

        if not config.has_section(ini_section):
            config.add_section(ini_section)

        for api_key, value in data.items():
            ini_key = self._ini_key(api_key)
            config.set(ini_section, ini_key, str(value))

        self._write_ini(config, self.config_path)
        return True

    # ========================================
    # SATELLITES (satellites.ini)
    # ========================================

    def get_satellites(self):
        """Read all satellites, returns list of dicts"""
        config = self._read_ini(self.satellites_path)
        satellites = []

        for section in config.sections():
            sat = {}
            for ini_key, value in config.items(section):
                api_key = self._api_key(ini_key)
                sat[api_key] = value
            sat['_section'] = section
            satellites.append(sat)

        return satellites

    def get_active_satellite_id(self):
        """Get the curSatId from config.ini [Satellite] section"""
        config = self._read_ini(self.config_path)
        if config.has_section('Satellite'):
            return config.get('Satellite', 'curSatId', fallback='1')
        return '1'

    def set_active_satellite_id(self, sat_id):
        """Set curSatId in config.ini [Satellite] section"""
        self.auto_backup()
        config = self._read_ini(self.config_path)
        if not config.has_section('Satellite'):
            config.add_section('Satellite')
        config.set('Satellite', 'curSatId', str(sat_id))
        self._write_ini(config, self.config_path)

    def get_satellite_by_id(self, sat_id):
        """Find a satellite by its satId"""
        for sat in self.get_satellites():
            if sat.get('satId') == str(sat_id):
                return sat
        return None

    def create_satellite(self, data):
        """Add a new satellite section"""
        self.auto_backup()
        config = self._read_ini(self.satellites_path)

        # Find next satellite number and ID
        existing_nums = []
        existing_ids = []
        for section in config.sections():
            match = re.match(r'Satellite(\d+)', section)
            if match:
                existing_nums.append(int(match.group(1)))
            sat_id = config.get(section, '*satId', fallback=None)
            if sat_id:
                existing_ids.append(int(sat_id))

        next_num = max(existing_nums, default=0) + 1
        next_id = max(existing_ids, default=0) + 1

        section_name = f'Satellite{next_num}'
        config.add_section(section_name)
        config.set(section_name, '*satId', str(next_id))

        for key, value in data.items():
            if key not in ('satId', '_section'):
                config.set(section_name, key, str(value))

        self._write_ini(config, self.satellites_path)
        return next_id

    def update_satellite(self, sat_id, data):
        """Update an existing satellite by satId"""
        self.auto_backup()
        config = self._read_ini(self.satellites_path)

        target_section = None
        for section in config.sections():
            if config.get(section, '*satId', fallback=None) == str(sat_id):
                target_section = section
                break

        if not target_section:
            return False

        for key, value in data.items():
            if key not in ('satId', '_section'):
                config.set(target_section, key, str(value))

        self._write_ini(config, self.satellites_path)
        return True

    def delete_satellite(self, sat_id):
        """Remove a satellite section by satId"""
        self.auto_backup()
        config = self._read_ini(self.satellites_path)

        target_section = None
        for section in config.sections():
            if config.get(section, '*satId', fallback=None) == str(sat_id):
                target_section = section
                break

        if not target_section:
            return False, 'Satellite not found'

        # Don't allow deleting if it's the only one
        if len(config.sections()) <= 1:
            return False, 'Cannot delete the only satellite'

        # Don't allow deleting the active satellite
        active_id = self.get_active_satellite_id()
        if str(sat_id) == str(active_id):
            return False, 'Cannot delete active satellite. Activate another one first.'

        sat_name = config.get(target_section, 'satName', fallback=f'ID {sat_id}')
        config.remove_section(target_section)
        self._write_ini(config, self.satellites_path)
        return True, sat_name

    def load_backup(self, timestamp_str):
        """Load an auto-backup by its timestamp prefix"""
        config_src = os.path.join(self.backup_dir, f'{timestamp_str}_config.ini')
        sats_src = os.path.join(self.backup_dir, f'{timestamp_str}_satellites.ini')

        if not os.path.exists(config_src) and not os.path.exists(sats_src):
            return False, 'Backup not found'

        # Auto-backup current state first
        self.auto_backup()

        try:
            if os.path.exists(config_src):
                shutil.copy2(config_src, self.config_path)
            if os.path.exists(sats_src):
                shutil.copy2(sats_src, self.satellites_path)
            return True, timestamp_str
        except IOError as e:
            return False, str(e)

    # ========================================
    # FACTORY RESET
    # ========================================

    def factory_reset(self):
        """Restore config.ini and satellites.ini to factory defaults"""
        factory_config = os.path.join(self.factory_dir, 'config.ini')
        factory_sats = os.path.join(self.factory_dir, 'satellites.ini')

        if not os.path.exists(factory_config):
            return False, 'Factory config not found'

        # Auto-backup before reset
        self.auto_backup()

        try:
            shutil.copy2(factory_config, self.config_path)
            if os.path.exists(factory_sats):
                shutil.copy2(factory_sats, self.satellites_path)
            return True, 'Factory defaults restored'
        except IOError as e:
            return False, str(e)

    # ========================================
    # AUTO-BACKUP
    # ========================================

    def auto_backup(self):
        """Create timestamped backup of current config files"""
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')

        try:
            if os.path.exists(self.config_path):
                shutil.copy2(self.config_path, os.path.join(self.backup_dir, f'{ts}_config.ini'))
            if os.path.exists(self.satellites_path):
                shutil.copy2(self.satellites_path, os.path.join(self.backup_dir, f'{ts}_satellites.ini'))

            # Prune old backups (keep last 50 pairs)
            self._prune_backups(max_pairs=50)
            return True
        except IOError:
            return False

    def _prune_backups(self, max_pairs=50):
        """Remove old backups, keeping the most recent max_pairs"""
        timestamps = set()
        for f in os.listdir(self.backup_dir):
            match = re.match(r'(\d{8}_\d{6})_', f)
            if match:
                timestamps.add(match.group(1))

        sorted_ts = sorted(timestamps, reverse=True)
        for old_ts in sorted_ts[max_pairs:]:
            for suffix in ['_config.ini', '_satellites.ini']:
                path = os.path.join(self.backup_dir, f'{old_ts}{suffix}')
                if os.path.exists(path):
                    os.remove(path)

    # ========================================
    # FILE MANAGER
    # ========================================

    def list_backups(self):
        """List auto-backup snapshots"""
        return self._list_dir(self.backup_dir, 'backup')

    def _list_dir(self, directory, category):
        """List config file pairs in a directory"""
        if not os.path.exists(directory):
            return []

        # Group by name prefix
        files = {}
        for fname in os.listdir(directory):
            filepath = os.path.join(directory, fname)
            if not os.path.isfile(filepath):
                continue

            stat = os.stat(filepath)

            # Extract name prefix (everything before _config.ini or _satellites.ini)
            if fname.endswith('_config.ini'):
                prefix = fname[:-len('_config.ini')]
            elif fname.endswith('_satellites.ini'):
                prefix = fname[:-len('_satellites.ini')]
            else:
                continue

            if prefix not in files:
                files[prefix] = {
                    'name': prefix,
                    'category': category,
                    'files': [],
                    'size': 0,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                }
            files[prefix]['files'].append(fname)
            files[prefix]['size'] += stat.st_size
            # Use latest modified
            file_mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            if file_mtime > files[prefix]['modified']:
                files[prefix]['modified'] = file_mtime

        result = sorted(files.values(), key=lambda x: x['modified'], reverse=True)
        return result

    def delete_backup(self, timestamp_str):
        """Delete a backup by timestamp"""
        deleted = False
        for suffix in ['_config.ini', '_satellites.ini']:
            path = os.path.join(self.backup_dir, f'{timestamp_str}{suffix}')
            if os.path.exists(path):
                os.remove(path)
                deleted = True
        return deleted

    def get_file_path(self, category, filename):
        """Get full path to a config file for download"""
        if category == 'backup':
            path = os.path.join(self.backup_dir, filename)
        elif category == 'uploads':
            path = os.path.join(self.uploads_dir, filename)
        elif category == 'active':
            path = os.path.join(self.config_dir, filename)
        else:
            return None

        # Security: ensure path is within expected directory
        real_path = os.path.realpath(path)
        real_config = os.path.realpath(self.config_dir)
        if not real_path.startswith(real_config):
            return None

        if os.path.exists(path) and os.path.isfile(path):
            return path
        return None

    # ========================================
    # UPLOADS
    # ========================================

    def upload_file(self, filename, file_data):
        """Save an uploaded config file to uploads/ directory"""
        filename = self._sanitize_name(filename)
        if not filename:
            return False, 'Invalid filename'

        # Only allow .ini files
        if not filename.endswith('.ini'):
            return False, 'Only .ini files are allowed'

        dest = os.path.join(self.uploads_dir, filename)
        try:
            file_data.save(dest)
            return True, filename
        except IOError as e:
            return False, str(e)

    def list_uploads(self):
        """List uploaded config files"""
        if not os.path.exists(self.uploads_dir):
            return []

        files = []
        for fname in sorted(os.listdir(self.uploads_dir)):
            filepath = os.path.join(self.uploads_dir, fname)
            if not os.path.isfile(filepath) or not fname.endswith('.ini'):
                continue
            stat = os.stat(filepath)
            files.append({
                'name': fname,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            })
        return files

    def load_upload(self, filename, file_type=None):
        """Load an uploaded file as active config.
        file_type: 'config' | 'satellite' — if omitted, falls back to filename heuristic."""
        filename = self._sanitize_name(filename)
        if not filename:
            return False, 'Invalid filename'

        src = os.path.join(self.uploads_dir, filename)
        if not os.path.exists(src):
            return False, 'File not found'

        self.auto_backup()

        try:
            if file_type == 'satellite':
                shutil.copy2(src, self.satellites_path)
            elif file_type == 'config':
                shutil.copy2(src, self.config_path)
            else:
                if 'satellite' in filename.lower():
                    shutil.copy2(src, self.satellites_path)
                else:
                    shutil.copy2(src, self.config_path)
            return True, filename
        except IOError as e:
            return False, str(e)

    def delete_upload(self, filename):
        """Delete an uploaded file"""
        filename = self._sanitize_name(filename)
        if not filename:
            return False
        path = os.path.join(self.uploads_dir, filename)
        if os.path.exists(path) and os.path.isfile(path):
            os.remove(path)
            return True
        return False

    # ========================================
    # UTILITY
    # ========================================

    def _sanitize_name(self, name):
        """Sanitize a snapshot name for safe filesystem use"""
        if not name:
            return None
        # Allow alphanumeric, dash, underscore, dot
        sanitized = re.sub(r'[^\w\-.]', '_', name.strip())
        # Prevent path traversal
        sanitized = sanitized.replace('..', '_')
        return sanitized if sanitized else None

    def get_port(self):
        """Get server port from config.ini"""
        config = self._read_ini(self.config_path)
        if config.has_section('Server'):
            return config.getint('Server', 'port', fallback=8000)
        return 8000

    def get_config_dir_setting(self):
        """Read configDir from [Storage] section if present"""
        config = self._read_ini(self.config_path)
        if config.has_section('Storage'):
            return config.get('Storage', 'configDir', fallback=None)
        return None