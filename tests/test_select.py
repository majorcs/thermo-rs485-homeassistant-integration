"""Tests for the Thermo RS485 baud rate select entity."""

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
from custom_components.thermo_rs485.select import BAUD_RATE_OPTION_LABELS


def _sample_registers() -> dict[int, int]:
    """Return a complete register snapshot for tests."""
    return {
        0x0000: 486,
        0x0001: 300,
        0x0100: 1,
        0x0101: 4,   # baud rate code 4 → 9600 bps
        0x0104: 5,
        0x0105: 0,
    }


def _make_entry(host: str) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Sensor",
        data={
            CONF_PROTOCOL: PROTOCOL_TCP,
            CONF_HOST: host,
            CONF_PORT: DEFAULT_PORT,
            CONF_SLAVE_ID: 1,
            CONF_SCAN_INTERVAL: 30,
        },
    )


async def test_baud_rate_select_entity_is_created(hass):
    """A baud_rate select entity should be exposed after setup."""
    entry = _make_entry("192.0.2.40")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=_sample_registers()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("select.sensor_baud_rate")
    assert state is not None
    assert state.state == "9600 bps"


async def test_baud_rate_select_options_match_all_baud_rates(hass):
    """The select entity should offer all supported baud rate options."""
    entry = _make_entry("192.0.2.41")
    entry.add_to_hass(hass)

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=_sample_registers()),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("select.sensor_baud_rate")
    assert state is not None
    assert list(state.attributes["options"]) == list(BAUD_RATE_OPTION_LABELS)


async def test_baud_rate_select_write_through_coordinator(hass):
    """Selecting a baud rate option should write the correct code to the register."""
    entry = _make_entry("192.0.2.42")
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
        "select",
        "select_option",
        {"entity_id": "select.sensor_baud_rate", "option": "19200 bps"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # 19200 bps → code 6
    coordinator.async_write_register.assert_awaited_once_with(0x0101, 6)
    assert hass.states.get("select.sensor_baud_rate").state == "19200 bps"


async def test_baud_rate_select_all_codes_decode_correctly(hass):
    """Every baud rate code 1–6 should decode to its correct human-readable label."""
    expected = {1: "1200 bps", 2: "2400 bps", 3: "4800 bps", 4: "9600 bps", 5: "14400 bps", 6: "19200 bps"}

    for code, label in expected.items():
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=f"Sensor {code}",
            unique_id=f"tcp:192.0.2.{50 + code}:502:{code}",
            data={
                CONF_PROTOCOL: PROTOCOL_TCP,
                CONF_HOST: f"192.0.2.{50 + code}",
                CONF_PORT: DEFAULT_PORT,
                CONF_SLAVE_ID: code,
                CONF_SCAN_INTERVAL: 30,
            },
        )
        entry.add_to_hass(hass)
        regs = _sample_registers()
        regs[0x0101] = code

        with patch(
            "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
            new=AsyncMock(return_value=regs),
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        state = hass.states.get(f"select.sensor_{code}_baud_rate")
        assert state is not None, f"Missing entity for code {code}"
        assert state.state == label


async def test_baud_rate_select_unknown_code_returns_unknown(hass):
    """An unmapped register code should result in an unknown state."""
    entry = _make_entry("192.0.2.60")
    entry.add_to_hass(hass)

    regs = _sample_registers()
    regs[0x0101] = 0  # code 0 is not in the mapping

    with patch(
        "custom_components.thermo_rs485.modbus.ThermoModbusClient.async_read_blocks",
        new=AsyncMock(return_value=regs),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get("select.sensor_baud_rate")
    assert state is not None
    assert state.state == "unknown"
