"""Base entity for the Thermo RS485 integration."""

from __future__ import annotations

import os

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_PROTOCOL,
    CONF_SERIAL_PORT,
    CONF_SLAVE_ID,
    DOMAIN,
    MODEL,
    PROTOCOL_TCP,
)
from .coordinator import ThermoDataUpdateCoordinator


def _build_model(entry_data: dict) -> str:
    """Build a model string that includes protocol and physical connection."""
    protocol = str(entry_data[CONF_PROTOCOL])
    if protocol == PROTOCOL_TCP:
        host = str(entry_data[CONF_HOST])
        return f"{MODEL} (TCP · {host})"
    # Serial / RTU — show only the last path component (e.g. ttyUSB0)
    port_name = os.path.basename(str(entry_data[CONF_SERIAL_PORT]))
    return f"{MODEL} (RTU · {port_name})"


class ThermoCoordinatorEntity(CoordinatorEntity[ThermoDataUpdateCoordinator]):
    """Base class for all Thermo RS485 entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ThermoDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_unique_id)},
            name=coordinator.entry.title,
            manufacturer=None,
            model=_build_model(coordinator.entry.data),
            serial_number=str(int(coordinator.entry.data[CONF_SLAVE_ID])),
        )
