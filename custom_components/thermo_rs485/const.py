"""Constants for the Thermo RS485 integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, Platform

DOMAIN = "thermo_rs485"
PLATFORMS: tuple[Platform, ...] = (Platform.SENSOR, Platform.NUMBER, Platform.SELECT)

CONF_PROTOCOL = "protocol"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_DATABITS = "databits"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"
CONF_SLAVE_ID = "slave_id"

DEFAULT_NAME = "Thermo RS485"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_SLAVE_ID = 1
DEFAULT_BAUDRATE = 9600
DEFAULT_DATABITS = 8
DEFAULT_PARITY = "N"
DEFAULT_STOPBITS = 1
DEFAULT_TIMEOUT = 3.0

PROTOCOL_TCP = "tcp"
PROTOCOL_SERIAL = "serial"
SUPPORTED_PROTOCOLS = (PROTOCOL_TCP, PROTOCOL_SERIAL)

MANUFACTURER = "Thermo RS485"
MODEL = "Thermo RS485 T&H Sensor"
VERSION = "2026.04.29.1"

BAUDRATE_OPTIONS = [1200, 2400, 4800, 9600, 14400, 19200]
PARITY_OPTIONS = ["N", "E", "O"]
STOPBITS_OPTIONS = [1, 2]
DATABITS_OPTIONS = [7, 8]

# Baud rate ↔ register code translation (register 0x0101)
BAUD_RATE_TO_CODE: dict[int, int] = {
    1200: 1,
    2400: 2,
    4800: 3,
    9600: 4,
    14400: 5,
    19200: 6,
}
CODE_TO_BAUD_RATE: dict[int, int] = {v: k for k, v in BAUD_RATE_TO_CODE.items()}

# Temperature unit option for the options flow
CONF_TEMPERATURE_UNIT = "temperature_unit"
TEMPERATURE_UNIT_CELSIUS = "celsius"
TEMPERATURE_UNIT_FAHRENHEIT = "fahrenheit"
DEFAULT_TEMPERATURE_UNIT = TEMPERATURE_UNIT_CELSIUS


def build_unique_id(data: dict[str, object]) -> str:
    """Build a stable config entry unique ID."""
    protocol = str(data[CONF_PROTOCOL])
    slave_id = int(data[CONF_SLAVE_ID])

    if protocol == PROTOCOL_TCP:
        host = str(data[CONF_HOST]).strip().lower()
        port = int(data[CONF_PORT])
        return f"{protocol}:{host}:{port}:{slave_id}"

    serial_port = str(data[CONF_SERIAL_PORT]).strip()
    return f"{protocol}:{serial_port}:{slave_id}"


def build_entry_title(data: dict[str, object]) -> str:
    """Build a friendly config entry title."""
    custom_name = str(data.get(CONF_NAME, "")).strip()
    if custom_name:
        return custom_name

    protocol = str(data[CONF_PROTOCOL])
    slave_id = int(data[CONF_SLAVE_ID])
    if protocol == PROTOCOL_TCP:
        return f"{DEFAULT_NAME} {data[CONF_HOST]}:{data[CONF_PORT]} (ID {slave_id})"

    return f"{DEFAULT_NAME} {data[CONF_SERIAL_PORT]} (ID {slave_id})"
