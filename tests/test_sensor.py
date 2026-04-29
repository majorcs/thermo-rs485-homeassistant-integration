"""Tests for the Thermo RS485 sensor platform."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.thermo_rs485.const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    CONF_TEMPERATURE_UNIT,
    DEFAULT_PORT,
    DOMAIN,
    MODEL,
    PROTOCOL_SERIAL,
    PROTOCOL_TCP,
    TEMPERATURE_UNIT_FAHRENHEIT,
)
from custom_components.thermo_rs485.register_map import SENSOR_DESCRIPTIONS, decode_temperature, decode_humidity


def _sample_registers() -> dict[int, int]:
    """Return a complete register snapshot for tests."""
    return {
        0x0000: 486,    # humidity: 486/10 = 48.6 %RH
        0x0001: 300,    # temperature: 300/10 = 30.0 °C
        0x0100: 1,      # device address
        0x0101: 4,      # baud rate code
        0x0104: 5,      # temperature correction: 5/10 = 0.5 °C
        0x0105: 0,      # humidity correction: 0.0 %RH
    }


async def test_sensor_entities_are_created_and_decoded(hass):
    """The integration should expose decoded sensor values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.20",
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 30,
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=_sample_registers()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.sensor_temperature").state == "30.0"
    assert hass.states.get("sensor.sensor_humidity").state == "48.6"


async def test_temperature_sensor_decodes_negative_values(hass):
    """Temperature entity should correctly decode negative (signed i16) values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.21",
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 30,
        },
    )
    entry.add_to_hass(hass)

    registers = _sample_registers()
    registers[0x0001] = 0xFF9F  # -97 → -9.7 °C

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=registers),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("sensor.sensor_temperature").state == "-9.7"


def test_decode_temperature_handles_negative():
    """decode_temperature should use two's complement for sub-zero values."""
    assert decode_temperature({0x0001: 0xFF9F}) == -9.7
    assert decode_temperature({0x0001: 300}) == 30.0
    assert decode_temperature({0x0001: 0}) == 0.0


def test_decode_humidity_is_always_positive():
    """decode_humidity should always return a non-negative value."""
    assert decode_humidity({0x0000: 486}) == 48.6
    assert decode_humidity({0x0000: 0}) == 0.0
    assert decode_humidity({0x0000: 1000}) == 100.0


async def test_temperature_sensor_displays_fahrenheit_when_configured(hass):
    """Temperature sensor state should be in °F when the temperature_unit option is fahrenheit."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.22",
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 30,
        },
        options={CONF_TEMPERATURE_UNIT: TEMPERATURE_UNIT_FAHRENHEIT},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=_sample_registers()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    temp_state = hass.states.get("sensor.sensor_temperature")
    assert temp_state is not None
    assert temp_state.attributes.get("unit_of_measurement") == "°F"
    # 30 °C → 86 °F
    assert float(temp_state.state) == pytest.approx(86.0, abs=0.1)


async def test_temperature_sensor_defaults_to_celsius(hass):
    """Temperature sensor state should be in °C when no temperature_unit option is set."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.23",
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 30,
        },
        options={},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=_sample_registers()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    temp_state = hass.states.get("sensor.sensor_temperature")
    assert temp_state is not None
    assert temp_state.attributes.get("unit_of_measurement") == "°C"
    assert temp_state.state == "30.0"


async def test_device_info_tcp_shows_protocol_and_host(hass):
    """DeviceInfo model should include 'TCP' and the host for TCP entries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="My Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.30",
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 3,
            CONF_SCAN_INTERVAL: 30,
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=_sample_registers()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    from homeassistant.helpers import device_registry as dr
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(
        identifiers={(DOMAIN, f"tcp:192.0.2.30:{DEFAULT_PORT}:3")}
    )
    assert device is not None
    assert "TCP" in device.model
    assert "192.0.2.30" in device.model
    assert device.serial_number == "3"


async def test_device_info_rtu_shows_protocol_and_port_name(hass):
    """DeviceInfo model should include 'RTU' and the port name (not full path) for serial entries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="My RTU Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_SERIAL,
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            CONF_SLAVE_ID: 5,
            CONF_SCAN_INTERVAL: 30,
            "baudrate": 9600,
            "databits": 8,
            "parity": "N",
            "stopbits": 1,
        },
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=_sample_registers()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    from homeassistant.helpers import device_registry as dr
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(
        identifiers={(DOMAIN, "serial:/dev/ttyUSB0:5")}
    )
    assert device is not None
    assert "RTU" in device.model
    assert "ttyUSB0" in device.model
    assert "/dev" not in device.model
    assert device.serial_number == "5"
