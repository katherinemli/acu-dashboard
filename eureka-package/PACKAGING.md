# Eureka ACU — DEB Packaging

Production-ready Debian package for Eureka ACU daemon + backend.

## Building

```bash
cd eureka-package
./make_deb.sh
```

Creates: `eureka-acu_1.0.0_amd64.deb`

## Installation

```bash
sudo dpkg -i eureka-acu_1.0.0_amd64.deb
sudo apt-get install -f  # Fix any missing dependencies
```

## What's Included

### Package Structure
```
/opt/eureka/
├── acu-daemon/          ← Supervisor daemon
├── backend/             ← Flask API
├── frontend/dist/       ← Vue 3 build (optional)
└── venv/                ← Python virtual env (created at install)

/etc/systemd/system/
├── eureka-daemon.service
└── eureka-backend.service

/var/lib/eureka/        ← Runtime data (state.json, etc.)
/var/log/eureka/        ← Logs
```

### Services

Start automatically on boot:
```bash
sudo systemctl start eureka-daemon
sudo systemctl start eureka-backend
```

View logs:
```bash
sudo journalctl -u eureka-daemon -f
sudo journalctl -u eureka-backend -f
```

## Installation Scripts

### postinst (after installation)
- Creates `eureka` service user
- Sets up Python venv
- Creates log/runtime directories
- Enables systemd services
- Prints setup instructions

### prerm (before removal)
- Stops services
- Disables systemd units

### postrm (after removal)
- Removes installation directory (if `purge`)
- Removes runtime data
- Removes service user

## Security

Systemd hardening:
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=strict`
- `ProtectHome=yes`
- Runs as unprivileged `eureka` user

## Dependencies

Checked automatically by `dpkg`:
- python3 >= 3.8
- python3-pip
- python3-venv
- systemd

## Uninstall

Remove package:
```bash
sudo apt-get remove eureka-acu
```

Completely purge (removes all data):
```bash
sudo apt-get purge eureka-acu
```

---

**Katherine Liberona** · Full-stack embedded systems packaging example
