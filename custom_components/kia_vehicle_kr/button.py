"""Button entities for Kia Developers."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KiaConfigEntry
from .entity import KiaVehicleEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KiaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Kia buttons."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        KiaRefreshButton(coordinator, vehicle_id)
        for vehicle_id in coordinator.vehicle_ids
    )


class KiaRefreshButton(KiaVehicleEntity, ButtonEntity):
    """Request an immediate Kia data refresh."""

    _attr_translation_key = "refresh"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator, vehicle_id: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, vehicle_id)
        self._attr_unique_id = f"{vehicle_id}_refresh"

    async def async_press(self) -> None:
        """Refresh all selected vehicles."""
        await self.coordinator.async_request_refresh()

