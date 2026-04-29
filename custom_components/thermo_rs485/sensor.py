"""Sensor platform for the Thermo RS485 integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ThermoDataUpdateCoordinator
from .entity import ThermoCoordinatorEntity
from .register_map import SENSOR_DESCRIPTIONS, ThermoSensorDescription


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Thermo RS485 sensors from a config entry."""
    coordinator: ThermoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(ThermoSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS)


class ThermoSensor(ThermoCoordinatorEntity, SensorEntity):
    """Representation of a Thermo RS485 sensor."""

    entity_description: ThermoSensorDescription

    def __init__(self, coordinator: ThermoDataUpdateCoordinator, description: ThermoSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device_unique_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the decoded sensor value."""
        if not self.coordinator.data:
            return None
        return self.entity_description.decoder(self.coordinator.data)
