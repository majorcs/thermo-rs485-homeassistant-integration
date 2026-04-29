"""Tests for Modbus helpers."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from custom_components.thermo_rs485.const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    build_entry_title,
    build_unique_id,
)
from custom_components.thermo_rs485.modbus import ThermoConnectionParams, ThermoModbusClient, ThermoModbusError
from custom_components.thermo_rs485.register_map import RegisterBlock


class FakeResult:
    """Small fake pymodbus result object."""

    def __init__(self, registers, *, is_error: bool = False) -> None:
        self.registers = registers
        self._is_error = is_error

    def isError(self) -> bool:
        return self._is_error


def test_build_unique_id_for_tcp():
    """TCP IDs should be stable and lower-cased."""
    assert (
        build_unique_id(
            {
                CONF_PROTOCOL: "tcp",
                "host": "EXAMPLE.local",
                "port": 502,
                CONF_SLAVE_ID: 7,
            }
        )
        == "tcp:example.local:502:7"
    )


def test_build_unique_id_for_serial():
    """Serial IDs should include port and slave ID."""
    assert (
        build_unique_id(
            {
                CONF_PROTOCOL: "serial",
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_SLAVE_ID: 2,
            }
        )
        == "serial:/dev/ttyUSB0:2"
    )


def test_build_entry_title_with_custom_name():
    """A custom name should take precedence over the auto-generated title."""
    assert (
        build_entry_title(
            {
                CONF_PROTOCOL: "tcp",
                "host": "192.0.2.1",
                "port": 502,
                CONF_SLAVE_ID: 1,
                CONF_SCAN_INTERVAL: 30,
                "name": "Office",
            }
        )
        == "Office"
    )


def test_build_entry_title_for_serial_default():
    """Serial titles should fall back to a deterministic name."""
    assert (
        build_entry_title(
            {
                CONF_PROTOCOL: "serial",
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_SLAVE_ID: 9,
                CONF_SCAN_INTERVAL: 30,
            }
        )
        == "Thermo RS485 /dev/ttyUSB0 (ID 9)"
    )


def test_connection_params_from_mapping_tcp():
    """ThermoConnectionParams should be constructed from TCP mapping."""
    params = ThermoConnectionParams.from_mapping(
        {
            CONF_PROTOCOL: "tcp",
            "host": "192.0.2.10",
            "port": 502,
            CONF_SLAVE_ID: 1,
        }
    )
    assert params.protocol == "tcp"
    assert params.host == "192.0.2.10"
    assert params.port == 502
    assert params.slave_id == 1


def test_connection_params_from_mapping_serial():
    """ThermoConnectionParams should capture all serial parameters."""
    params = ThermoConnectionParams.from_mapping(
        {
            CONF_PROTOCOL: "serial",
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_SLAVE_ID: 3,
            "baudrate": 4800,
            "databits": 8,
            "parity": "E",
            "stopbits": 2,
        }
    )
    assert params.protocol == "serial"
    assert params.serial_port == "/dev/ttyUSB0"
    assert params.baudrate == 4800
    assert params.parity == "E"
    assert params.stopbits == 2
    assert params.databits == 8


def test_get_client_raises_for_unknown_protocol(hass):
    """An unsupported protocol should raise ThermoModbusError."""
    client = ThermoModbusClient(
        hass,
        ThermoConnectionParams(protocol="mqtt", slave_id=1),
    )
    with pytest.raises(ThermoModbusError):
        client._get_client()


def test_ensure_connected_raises_when_connect_returns_false(hass):
    """A failed connect() call should raise ThermoModbusError."""
    client = ThermoModbusClient(
        hass,
        ThermoConnectionParams(protocol="tcp", host="192.0.2.99", port=502, slave_id=1),
    )
    fake_raw = Mock()
    fake_raw.connect.return_value = False
    client._client = fake_raw
    client._close_sync = Mock()

    with pytest.raises(ThermoModbusError):
        client._ensure_connected()

    client._close_sync.assert_called_once()


def test_read_blocks_sync_combines_registers(hass):
    """Contiguous reads should be flattened into an address map."""
    client = ThermoModbusClient(
        hass,
        ThermoConnectionParams(protocol="tcp", host="192.0.2.10", port=502, slave_id=1),
    )
    fake_client = Mock()
    client._ensure_connected = Mock(return_value=fake_client)
    client._read_registers = Mock(
        side_effect=[
            FakeResult([486, 300]),
            FakeResult([1, 4]),
        ]
    )

    result = client._read_blocks_sync(
        (
            RegisterBlock(start=0x0000, count=2),
            RegisterBlock(start=0x0100, count=2),
        )
    )

    assert result == {
        0x0000: 486,
        0x0001: 300,
        0x0100: 1,
        0x0101: 4,
    }


def test_read_blocks_sync_raises_on_modbus_error(hass):
    """Modbus failures should be surfaced as ThermoModbusError and close the client."""
    client = ThermoModbusClient(
        hass,
        ThermoConnectionParams(protocol="tcp", host="192.0.2.10", port=502, slave_id=1),
    )
    client._ensure_connected = Mock(return_value=Mock())
    client._read_registers = Mock(return_value=FakeResult([], is_error=True))
    client._close_sync = Mock()

    with pytest.raises(ThermoModbusError):
        client._read_blocks_sync((RegisterBlock(start=0x0000, count=2),))

    client._close_sync.assert_called_once()


def test_write_registers_sync_raises_on_modbus_error(hass):
    """Modbus write errors should be surfaced as ThermoModbusError."""
    client = ThermoModbusClient(
        hass,
        ThermoConnectionParams(protocol="tcp", host="192.0.2.10", port=502, slave_id=1),
    )
    client._ensure_connected = Mock(return_value=Mock())
    client._write_registers = Mock(return_value=FakeResult([], is_error=True))
    client._close_sync = Mock()

    with pytest.raises(ThermoModbusError):
        client._write_registers_sync(0x0104, [50])

    client._close_sync.assert_called_once()


def test_read_blocks_sync_wraps_unexpected_exception(hass):
    """Unexpected exceptions from pymodbus should be re-raised as ThermoModbusError."""
    client = ThermoModbusClient(
        hass,
        ThermoConnectionParams(protocol="tcp", host="192.0.2.10", port=502, slave_id=1),
    )
    client._ensure_connected = Mock(return_value=Mock())
    client._read_registers = Mock(side_effect=RuntimeError("unexpected"))
    client._close_sync = Mock()

    with pytest.raises(ThermoModbusError):
        client._read_blocks_sync((RegisterBlock(start=0x0000, count=2),))
