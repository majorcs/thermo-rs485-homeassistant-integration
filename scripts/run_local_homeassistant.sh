#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${CONFIG_DIR:-$ROOT_DIR/.manual-homeassistant}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.manual-homeassistant-venv}"
SERIAL_PORT="${SERIAL_PORT:-/dev/ttyUSB0}"
SCAN_INTERVAL="${SCAN_INTERVAL:-30}"
SLAVE_ID="${SLAVE_ID:-1}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8123}"
HA_VERSION="${HA_VERSION:-2026.3.4}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--install-only] [--stop]

Starts a local Home Assistant instance for manual testing of this integration.
Checks for an already-running instance and offers to stop it first.

Options:
  --install-only  Set up the environment without starting Home Assistant
  --stop          Stop a running instance and exit

Environment overrides:
  CONFIG_DIR      Home Assistant config directory
  VENV_DIR        Virtualenv directory for Home Assistant
  SERIAL_PORT     Serial device path (default: /dev/ttyUSB0)
  SCAN_INTERVAL   Polling interval in seconds (default: 30)
  SLAVE_ID        Modbus slave ID (default: 1)
  HOST            Home Assistant bind host (default: 127.0.0.1)
  PORT            Home Assistant HTTP port (default: 8123)
  HA_VERSION      Home Assistant version to install (default: ${HA_VERSION})
EOF
}

INSTALL_ONLY=0
STOP_ONLY=0
if [[ "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--install-only" ]]; then
  INSTALL_ONLY=1
elif [[ "${1:-}" == "--stop" ]]; then
  STOP_ONLY=1
elif [[ $# -gt 0 ]]; then
  usage >&2
  exit 1
fi

command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || {
  echo "python3 is required" >&2
  exit 1
}
PYTHON=$(command -v python3 2>/dev/null || command -v python)

# Stop any already-running HA instance tracked by our lock file.
stop_running_instance() {
  local lock_path="$CONFIG_DIR/.ha_run.lock"
  if [[ ! -f "$lock_path" ]]; then
    return 0
  fi

  "$PYTHON" - <<'PY' "$lock_path"
import json, os, signal, sys
from pathlib import Path

lock_path = Path(sys.argv[1])
try:
    payload = json.loads(lock_path.read_text(encoding="utf-8"))
except (json.JSONDecodeError, FileNotFoundError):
    sys.exit(0)

pid = payload.get("pid")
if not isinstance(pid, int):
    sys.exit(0)

try:
    os.kill(pid, signal.SIGTERM)
    print(f"Sent SIGTERM to running instance (PID {pid}).")
except ProcessLookupError:
    pass
except PermissionError:
    print(f"No permission to stop PID {pid}.", file=sys.stderr)

lock_path.unlink(missing_ok=True)
PY
}

stop_running_instance

if [[ "$STOP_ONLY" -eq 1 ]]; then
  echo "Stopped any running instance."
  exit 0
fi

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --quiet --upgrade pip
python -m pip install --quiet "homeassistant==${HA_VERSION}"

mkdir -p "$CONFIG_DIR/custom_components" "$CONFIG_DIR/.storage"

# Symlink the integration into the config directory.
if [[ -L "$CONFIG_DIR/custom_components/thermo_rs485" || -e "$CONFIG_DIR/custom_components/thermo_rs485" ]]; then
  rm -rf "$CONFIG_DIR/custom_components/thermo_rs485"
fi
ln -s "$ROOT_DIR/custom_components/thermo_rs485" "$CONFIG_DIR/custom_components/thermo_rs485"

cat >"$CONFIG_DIR/configuration.yaml" <<EOF
default_config:

homeassistant:
  name: Thermo RS485 Manual Test
  latitude: 0
  longitude: 0
  elevation: 0
  unit_system: metric
  time_zone: UTC

http:
  server_host: ${HOST}
  server_port: ${PORT}

logger:
  default: info
  logs:
    custom_components.thermo_rs485: debug
    pymodbus: info
EOF

for file in automations.yaml scripts.yaml scenes.yaml; do
  if [[ ! -f "$CONFIG_DIR/$file" ]]; then
    printf '[]\n' >"$CONFIG_DIR/$file"
  fi
done

# Pre-populate a serial config entry so the integration loads automatically.
"$PYTHON" - <<'PY' "$CONFIG_DIR" "$SERIAL_PORT" "$SLAVE_ID" "$SCAN_INTERVAL"
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

config_dir = Path(sys.argv[1])
serial_port = sys.argv[2]
slave_id = int(sys.argv[3])
scan_interval = int(sys.argv[4])

storage_path = config_dir / ".storage" / "core.config_entries"
unique_id = f"serial:{serial_port}:{slave_id}"
title = f"Thermo RS485 {serial_port} (ID {slave_id})"
entry_data = {
    "protocol": "serial",
    "serial_port": serial_port,
    "baudrate": 9600,
    "databits": 8,
    "parity": "N",
    "stopbits": 1,
    "slave_id": slave_id,
    "scan_interval": scan_interval,
}

payload = {
    "version": 1,
    "minor_version": 1,
    "key": "core.config_entries",
    "data": {"entries": []},
}

if storage_path.exists():
    with storage_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload.setdefault("data", {})
    payload["data"].setdefault("entries", [])

entries = payload["data"]["entries"]
for entry in entries:
    if entry.get("domain") == "thermo_rs485" and entry.get("unique_id") == unique_id:
        entry["title"] = title
        entry["data"] = entry_data
        entry["options"] = {}
        entry["version"] = 1
        entry["minor_version"] = 1
        break
else:
    entries.append(
        {
            "created_at": None,
            "data": entry_data,
            "disabled_by": None,
            "discovery_keys": {},
            "domain": "thermo_rs485",
            "entry_id": uuid.uuid4().hex,
            "minor_version": 1,
            "modified_at": None,
            "options": {},
            "pref_disable_new_entities": None,
            "pref_disable_polling": False,
            "source": "user",
            "subentries": [],
            "title": title,
            "unique_id": unique_id,
            "version": 1,
        }
    )

with storage_path.open("w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY

echo "Prepared Home Assistant config in: $CONFIG_DIR"
echo "Thermo RS485 serial test entry: $SERIAL_PORT (slave ID $SLAVE_ID, scan interval ${SCAN_INTERVAL}s)"
echo "Open http://${HOST}:${PORT} after startup."

if [[ "$INSTALL_ONLY" -eq 1 ]]; then
  exit 0
fi

exec python -m homeassistant --config "$CONFIG_DIR"
