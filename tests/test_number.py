"""Tests for writable Thermo RS485 number entities."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.thermo_rs485.const import (
    CONF_PROTOCOL,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    DEFAULT_PORT,
    DOMAIN,
    PROTOCOL_TCP,
)
from custom_components.thermo_rs485.number import _decode_register, _encode_register


def _sample_registers() -> dict[int, int]:
    """Return a complete register snapshot for tests."""
    return {
        0x0000: 486,
        0x0001: 300,
        0x0100: 1,      # device address: 1
        0x0101: 4,      # baud rate code: 4 (9600 bps)
        0x0104: 50,     # temperature correction: 50/10 = 5.0 °C
        0x0105: 0xFF9C, # humidity correction: (0xFF9C - 0x10000)/10 = -10.0 %RH
    }


async def test_number_entities_are_created_with_live_values(hass):
    """Writable configuration registers should be exposed as number entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.30",
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

    device_address = hass.states.get("number.sensor_device_address")
    baud_rate_code = hass.states.get("number.sensor_baud_rate_code")
    temp_correction = hass.states.get("number.sensor_temperature_correction")
    hum_correction = hass.states.get("number.sensor_humidity_correction")

    assert device_address is not None
    assert device_address.state == "1.0"

    assert baud_rate_code is not None
    assert baud_rate_code.state == "4.0"

    assert temp_correction is not None
    assert temp_correction.state == "5.0"
    assert temp_correction.attributes["unit_of_measurement"] == "°C"

    assert hum_correction is not None
    assert hum_correction.state == "-10.0"
    assert hum_correction.attributes["unit_of_measurement"] == "%"


async def test_number_entity_write_through_coordinator(hass):
    """Setting a number entity should write the correct register value."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.31",
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 30,
        },
    )
    entry.add_to_hass(hass)

    registers = _sample_registers()

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=registers),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async def _write_side_effect(address: int, value: int) -> None:
        updated = dict(coordinator.data)
        updated[address] = value
        coordinator.async_set_updated_data(updated)

    coordinator.async_write_register = AsyncMock(side_effect=_write_side_effect)

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.sensor_device_address", "value": 5},
        blocking=True,
    )
    await hass.async_block_till_done()

    coordinator.async_write_register.assert_awaited_once_with(0x0100, 5)
    assert hass.states.get("number.sensor_device_address").state == "5.0"


async def test_signed_correction_write_negative_value(hass):
    """Negative correction values should be encoded as unsigned two's complement."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: "192.0.2.32",
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 30,
        },
    )
    entry.add_to_hass(hass)

    registers = _sample_registers()

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=registers),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async def _write_side_effect(address: int, value: int) -> None:
        updated = dict(coordinator.data)
        updated[address] = value
        coordinator.async_set_updated_data(updated)

    coordinator.async_write_register = AsyncMock(side_effect=_write_side_effect)

    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": "number.sensor_temperature_correction", "value": -5.0},
        blocking=True,
    )
    await hass.async_block_till_done()

    # -5.0 °C × 10 = -50 → two's complement u16 = 65486 (0xFFCE)
    coordinator.async_write_register.assert_awaited_once_with(0x0104, 0xFFCE)
    assert hass.states.get("number.sensor_temperature_correction").state == "-5.0"


def test_decode_register_unsigned():
    """Unsigned registers should be decoded without sign extension."""
    assert _decode_register({0x0100: 5}, 0x0100, 1, signed=False) == 5.0
    assert _decode_register({0x0101: 4}, 0x0101, 1, signed=False) == 4.0


def test_decode_register_signed_positive():
    """Positive signed values below 0x8000 should decode unchanged."""
    assert _decode_register({0x0104: 100}, 0x0104, 10, signed=True) == 10.0


def test_decode_register_signed_negative():
    """Values >= 0x8000 should be interpreted as negative signed i16."""
    assert _decode_register({0x0104: 0xFFCE}, 0x0104, 10, signed=True) == -5.0


def test_decode_register_returns_none_when_address_missing():
    """Missing register address should return None."""
    assert _decode_register({}, 0x0104, 10, signed=True) is None


def test_encode_register_positive():
    """Positive values should encode without adjustment."""
    assert _encode_register(10.0, 10, signed=True) == 100


def test_encode_register_negative():
    """Negative values should encode as two's complement u16."""
    assert _encode_register(-5.0, 10, signed=True) == 0xFFCE
