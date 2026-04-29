"""Register catalog for the Thermo RS485 integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.helpers.entity import EntityCategory


@dataclass(frozen=True, slots=True)
class RegisterBlock:
    """Contiguous Modbus register block."""

    start: int
    count: int


RegisterData = dict[int, int]
RegisterDecoder = Callable[[RegisterData], int | float | None]


@dataclass(frozen=True, kw_only=True)
class ThermoSensorDescription(SensorEntityDescription):
    """Extended description for Thermo RS485 registers."""

    register: int
    decoder: RegisterDecoder
    entity_registry_enabled_default: bool = True


# Read all measurement and configuration registers in three contiguous blocks.
READ_BLOCKS: tuple[RegisterBlock, ...] = (
    RegisterBlock(start=0x0000, count=2),   # humidity + temperature
    RegisterBlock(start=0x0100, count=2),   # device address + baud rate code
    RegisterBlock(start=0x0104, count=2),   # temperature correction + humidity correction
)


def _u16(data: RegisterData, address: int) -> int:
    return data[address]


def _i16(data: RegisterData, address: int) -> int:
    """Decode a signed 16-bit integer from a raw u16 register value."""
    raw = data[address]
    return raw if raw < 0x8000 else raw - 0x10000


def decode_humidity(data: RegisterData) -> float:
    """Decode humidity: raw u16 / 10 → %RH."""
    return round(_u16(data, 0x0000) / 10.0, 1)


def decode_temperature(data: RegisterData) -> float:
    """Decode temperature: signed i16 / 10 → °C."""
    return round(_i16(data, 0x0001) / 10.0, 1)


SENSOR_DESCRIPTIONS: tuple[ThermoSensorDescription, ...] = (
    ThermoSensorDescription(
        key="humidity",
        name="Humidity",
        register=0x0000,
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        decoder=decode_humidity,
        icon="mdi:water-percent",
    ),
    ThermoSensorDescription(
        key="temperature",
        name="Temperature",
        register=0x0001,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        decoder=decode_temperature,
    ),
)
