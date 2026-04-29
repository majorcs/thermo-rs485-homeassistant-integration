"""Base entity for the Thermo RS485 integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ThermoDataUpdateCoordinator


class ThermoCoordinatorEntity(CoordinatorEntity[ThermoDataUpdateCoordinator]):
    """Base class for all Thermo RS485 entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ThermoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_unique_id)},
            name=coordinator.entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )
