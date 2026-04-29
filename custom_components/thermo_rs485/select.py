"""Select platform for writable Thermo RS485 configuration registers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BAUDRATE_OPTIONS, BAUD_RATE_TO_CODE, CODE_TO_BAUD_RATE, DOMAIN
from .coordinator import ThermoDataUpdateCoordinator
from .entity import ThermoCoordinatorEntity

# Human-readable option labels in display order, matching BAUDRATE_OPTIONS.
BAUD_RATE_OPTION_LABELS: tuple[str, ...] = tuple(f"{br} bps" for br in BAUDRATE_OPTIONS)


@dataclass(frozen=True, kw_only=True)
class ThermoSelectDescription(SelectEntityDescription):
    """Description for a writable Thermo RS485 select entity."""

    register: int


SELECT_DESCRIPTIONS: tuple[ThermoSelectDescription, ...] = (
    ThermoSelectDescription(
        key="baud_rate",
        name="Baud rate",
        register=0x0101,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:serial-port",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Thermo RS485 select entities from a config entry."""
    coordinator: ThermoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(ThermoSelect(coordinator, description) for description in SELECT_DESCRIPTIONS)


class ThermoSelect(ThermoCoordinatorEntity, SelectEntity):
    """Representation of a writable Thermo RS485 select register."""

    entity_description: ThermoSelectDescription
    _attr_options: list[str] = list(BAUD_RATE_OPTION_LABELS)

    def __init__(
        self,
        coordinator: ThermoDataUpdateCoordinator,
        description: ThermoSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_unique_id}_select_{description.key}"

    @property
    def current_option(self) -> str | None:
        """Return the currently active baud rate as a human-readable label."""
        if not self.coordinator.data:
            return None
        code = self.coordinator.data.get(self.entity_description.register)
        if code is None:
            return None
        baud_rate = CODE_TO_BAUD_RATE.get(int(code))
        if baud_rate is None:
            return None
        return f"{baud_rate} bps"

    async def async_select_option(self, option: str) -> None:
        """Write the selected baud rate code to the device register.

        NOTE: Changing the baud rate on the device will cause the serial
        connection to disconnect. The host-side serial port configuration
        must be updated to match the new baud rate before communication
        can resume.
        """
        try:
            baud_rate = int(option.split()[0])
            code = BAUD_RATE_TO_CODE[baud_rate]
        except (ValueError, KeyError) as err:
            raise HomeAssistantError(f"Invalid baud rate option: {option!r}") from err
        try:
            await self.coordinator.async_write_register(self.entity_description.register, code)
        except Exception as err:
            raise HomeAssistantError(str(err)) from err
