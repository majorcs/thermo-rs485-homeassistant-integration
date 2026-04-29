"""Number platform for writable Thermo RS485 configuration registers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ThermoDataUpdateCoordinator
from .entity import ThermoCoordinatorEntity


@dataclass(frozen=True, kw_only=True)
class ThermoNumberDescription(NumberEntityDescription):
    """Description for a writable Thermo RS485 number entity."""

    register: int
    signed: bool = False


def _decode_register(data: dict[int, int], address: int, scale: int, signed: bool) -> float | None:
    """Decode a single register to a native value."""
    if address not in data:
        return None
    raw = int(data[address])
    if signed and raw >= 0x8000:
        raw -= 0x10000
    return round(raw / scale, 1) if scale != 1 else int(raw)


def _encode_register(value: float, scale: int, signed: bool) -> int:
    """Encode a native value to a raw u16 register word."""
    raw = int(round(value * scale))
    if signed and raw < 0:
        raw += 0x10000
    return raw & 0xFFFF


NUMBER_DESCRIPTIONS: tuple[ThermoNumberDescription, ...] = (
    ThermoNumberDescription(
        key="device_address",
        name="Device address",
        register=0x0100,
        native_min_value=1,
        native_max_value=247,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    ThermoNumberDescription(
        key="temperature_correction",
        name="Temperature correction",
        register=0x0104,
        native_min_value=-99.9,
        native_max_value=99.9,
        native_step=0.1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:thermometer-lines",
        signed=True,
    ),
    ThermoNumberDescription(
        key="humidity_correction",
        name="Humidity correction",
        register=0x0105,
        native_min_value=-99.9,
        native_max_value=99.9,
        native_step=0.1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:water-percent",
        signed=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up writable Thermo RS485 number entities from a config entry."""
    coordinator: ThermoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(ThermoNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS)


class ThermoNumber(ThermoCoordinatorEntity, NumberEntity):
    """Representation of a writable Thermo RS485 configuration register."""

    entity_description: ThermoNumberDescription

    def __init__(self, coordinator: ThermoDataUpdateCoordinator, description: ThermoNumberDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_unique_id}_number_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current register value."""
        if not self.coordinator.data:
            return None
        scale = 10 if self.entity_description.signed else 1
        return _decode_register(
            self.coordinator.data,
            self.entity_description.register,
            scale,
            self.entity_description.signed,
        )

    async def async_set_native_value(self, value: float) -> None:
        """Write the provided value to the device register."""
        scale = 10 if self.entity_description.signed else 1
        raw = _encode_register(value, scale, self.entity_description.signed)

        try:
            await self.coordinator.async_write_register(self.entity_description.register, raw)
        except Exception as err:
            raise HomeAssistantError(str(err)) from err
