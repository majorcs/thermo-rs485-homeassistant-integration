"""Sensor platform for the Thermo RS485 integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TEMPERATURE_UNIT,
    DEFAULT_TEMPERATURE_UNIT,
    DOMAIN,
    TEMPERATURE_UNIT_FAHRENHEIT,
)
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
    async_add_entities(ThermoSensor(coordinator, description, entry) for description in SENSOR_DESCRIPTIONS)


class ThermoSensor(ThermoCoordinatorEntity, SensorEntity):
    """Representation of a Thermo RS485 sensor."""

    entity_description: ThermoSensorDescription

    def __init__(
        self,
        coordinator: ThermoDataUpdateCoordinator,
        description: ThermoSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{coordinator.device_unique_id}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Sync entity registry temperature unit when entity is first added or reloaded."""
        await super().async_added_to_hass()
        if self.entity_description.device_class == SensorDeviceClass.TEMPERATURE:
            self._sync_temperature_unit()

    def _sync_temperature_unit(self) -> None:
        """Update the entity registry display unit to match the configured option."""
        unit_option = self._entry.options.get(CONF_TEMPERATURE_UNIT, DEFAULT_TEMPERATURE_UNIT)
        target_unit = (
            UnitOfTemperature.FAHRENHEIT
            if unit_option == TEMPERATURE_UNIT_FAHRENHEIT
            else UnitOfTemperature.CELSIUS
        )
        registry = er.async_get(self.hass)
        if entity_entry := registry.async_get(self.entity_id):
            current_unit = entity_entry.options.get("sensor", {}).get("unit_of_measurement")
            if current_unit != target_unit:
                registry.async_update_entity_options(
                    self.entity_id, "sensor", {"unit_of_measurement": target_unit}
                )

    @property
    def native_value(self) -> float | None:
        """Return the decoded sensor value in its native unit (always °C for temperature)."""
        if not self.coordinator.data:
            return None
        return self.entity_description.decoder(self.coordinator.data)
